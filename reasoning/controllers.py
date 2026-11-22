"""Charging-station choice for an electric taxi fleet with possibly unreliable data.

Every controller answers one question for one low-battery taxi:
"Where should this taxi charge, or should we first check a station?"

The environment calls, in order:
    on_minute(now, reports)            every minute, with what the charging
                                       network reports for each station
    decide(taxi, stations, now)        -> ("go", j) or ("verify", j)
    on_observation(j, rep, obs, ext)   when a taxi arrives at station j, or a
                                       verification of j finishes
    alarm_time / diagnosis()           for evaluation only

Controllers
    TrustAll      uses the reported availability as is (what fleets do today)
    Threshold     trusts reports until 3 large mismatches in 30 min, then
                  ignores all reports (the first prototype's detector)
    Cusum         CUSUM change detection on the mismatch stream; ignores all
                  reports after the alarm
    Reasoning     the proposed method: per-station multi-hypothesis filter,
                  inadequacy check, expected-cost decisions over explanations,
                  battery-aware risk, hedging, and value-of-information
                  verification
"""
import math

from .hypotheses import HYPS, StationBelief
from .network import NetworkBelief, StationView


def wait_minutes(avail, plugs, session_min):
    """Expected wait to start charging when `avail` = free plugs - vehicles waiting.

    A simple queue approximation: no wait if a plug is free, otherwise each
    vehicle ahead adds a share of one charging session per plug.
    """
    if avail > 0:
        return 0.0
    return (1 - avail) * session_min / plugs


class Base:
    name = "base"

    def __init__(self, plugs, session_min=25.0, speed_mps=7.0):
        self.plugs = plugs
        self.session_min = session_min
        self.speed = speed_mps
        self.reports = {}
        self.alarm_time = None

    def travel_min(self, taxi_xy, st):
        return math.hypot(taxi_xy[0] - st["xy"][0], taxi_xy[1] - st["xy"][1]) / self.speed / 60.0

    def reported_avail(self, j, st):
        free, queue = self.reports[j]
        return free - queue - st["enroute"]

    def own_avail(self, st):
        """Availability the fleet can estimate without the charging network."""
        return self.plugs - 0.5 - st["fleet_charging"] - st["fleet_queued"] - st["enroute"]

    def on_minute(self, now, reports):
        self.reports = reports

    def on_observation(self, j, reported_avail, observed_avail, extreme, now):
        pass

    def diagnosis(self):
        return {}


class TrustAll(Base):
    name = "TrustAll"

    def decide(self, taxi, stations, now):
        cost = {j: self.travel_min(taxi["xy"], st) +
                wait_minutes(self.reported_avail(j, st), self.plugs, self.session_min)
                for j, st in stations.items()}
        return ("go", min(cost, key=cost.get))


class _DistrustAfterAlarm(Base):
    def decide(self, taxi, stations, now):
        cost = {}
        for j, st in stations.items():
            a = self.own_avail(st) if self.alarm_time is not None else self.reported_avail(j, st)
            cost[j] = self.travel_min(taxi["xy"], st) + wait_minutes(a, self.plugs, self.session_min)
        return ("go", min(cost, key=cost.get))


class Threshold(_DistrustAfterAlarm):
    name = "Threshold"

    def __init__(self, plugs, k=3, window_s=1800, **kw):
        super().__init__(plugs, **kw)
        self.k, self.window, self.times = k, window_s, []

    def on_observation(self, j, rep, obs, extreme, now):
        if rep - obs >= 2 and self.alarm_time is None:
            self.times = [t for t in self.times if now - t <= self.window] + [now]
            if len(self.times) >= self.k:
                self.alarm_time = now


class Cusum(_DistrustAfterAlarm):
    """CUSUM on x = 1 if the report over-stated availability (D >= 1)."""
    name = "CUSUM"

    def __init__(self, plugs, p0=0.06, p1=0.6, h=4.0, **kw):   # p0 calibrated on normal days
        super().__init__(plugs, **kw)
        self.l1 = math.log(p1 / p0)
        self.l0 = math.log((1 - p1) / (1 - p0))
        self.h, self.S = h, 0.0

    def on_observation(self, j, rep, obs, extreme, now):
        x = 1 if rep - obs >= 1 else 0
        self.S = max(0.0, self.S + (self.l1 if x else self.l0))
        if self.S > self.h and self.alarm_time is None:
            self.alarm_time = now


class Reasoning(Base):
    """Proposed controller (network-level filter by default; see ReasoningIndep).

    For station j with belief b_j(k) over explanations k in {N, C, F, A}:

      wait under each explanation
        W_j(N) = wait(reported availability)
        W_j(C) = wait(reported availability) + congestion margin
        W_j(F) = W_j(A) = wait(fleet's own estimate) + uncertainty penalty

      expected cost      E_j = travel_j + sum_k b_j(k) W_j(k)
      battery-aware risk R_j = E_j + lambda(SOC) * (max_k W_j(k) - sum_k b_j(k) W_j(k))
                         (a nearly empty taxi cannot afford to be wrong)
      inadequacy         if no explanation fits station j (high surprise),
                         use the conservative wait max_k W_j(k)
      hedging            if j is probably unreliable (P(N)+P(C) < 0.5), do not
                         send more than `hedge_cap` taxis there at once

    Verify or go: value of information for the best station j*,
        EVPI = min_a sum_k b(k) L(a, k)  -  sum_k b(k) min_a L(a, k),
    where L(a, k) is the cost of choosing station a if j*'s true explanation is
    k. If EVPI exceeds the cost of checking (the taxi waits `verify_min`), the
    fleet verifies j* first (e.g. a call to the site, a camera, or a fleet
    vehicle already there) and then decides with the new observation.
    """
    name = "Reasoning"

    def __init__(self, plugs, congestion_margin=3.0, uncertainty_pen=5.0, risk_low=1.0, risk_high=0.3,
                 low_soc=0.2, hedge_cap=2, verify_min=3.0, verify_cooldown_s=900,
                 inadequacy_threshold=2.0, alarm_p=0.7, network=True, **kw):
        super().__init__(plugs, **kw)
        self.network = network
        self.net = None
        self.cm, self.up = congestion_margin, uncertainty_pen
        self.risk_low, self.risk_high, self.low_soc = risk_low, risk_high, low_soc
        self.hedge_cap, self.verify_min = hedge_cap, verify_min
        self.cooldown, self.inad_thr, self.alarm_p = verify_cooldown_s, inadequacy_threshold, alarm_p
        self.beliefs = {}
        self.last_value = {}
        self.last_change_check = 0
        self.last_verified = {}
        self.history = []
        self.n_verify = 0

    def _b(self, j):
        if j not in self.beliefs:
            self.beliefs[j] = StationView(self.net, j) if self.network else StationBelief()
        return self.beliefs[j]

    @staticmethod
    def jammed(r):
        return r[0] == 0 and r[1] >= 3

    def on_minute(self, now, reports):
        super().on_minute(now, reports)
        if self.network and self.net is None:
            self.net = NetworkBelief(sorted(reports))
        if self.network:
            self.net.predict()
        else:
            for j in reports:
                self._b(j).predict()
        if now - self.last_change_check >= 600:
            for j, r in reports.items():
                if j in self.last_value:
                    changed = r != self.last_value[j]
                    if self.network:
                        self.net.observe_stream(j, changed, self.jammed(r))
                    else:
                        self._b(j).observe_stream(changed, self.jammed(r))
                self.last_value[j] = r
            self.last_change_check = now
        for j, b in self.beliefs.items():
            if self.alarm_time is None and b.b["A"] > self.alarm_p:
                self.alarm_time = now
        if now % 300 == 0:
            for j in reports:
                self._b(j)
            row = {"t": now, **{f"{j}|{k}": round(b.b[k], 4) for j, b in self.beliefs.items() for k in HYPS},
                   **{f"{j}|surprise": round(b.surprise, 3) for j, b in self.beliefs.items()}}
            if self.network:
                row["network|compromised"] = round(self.net.p_compromised(), 4)
            self.history.append(row)

    def on_observation(self, j, rep, obs, extreme, now):
        if self.network:
            self.net.observe_arrival(j, rep, obs, extreme)
        else:
            self._b(j).observe_arrival(rep, obs, extreme)

    def _waits(self, j, st):
        w_rep = wait_minutes(self.reported_avail(j, st), self.plugs, self.session_min)
        w_own = wait_minutes(self.own_avail(st), self.plugs, self.session_min) + self.up
        return {"N": w_rep, "C": w_rep + self.cm, "F": w_own, "A": w_own}

    def _cost(self, j, st, taxi, cap):
        b = self._b(j)
        w = self._waits(j, st)
        worst = max(w.values())
        exp_w = worst if b.inadequate(self.inad_thr) else sum(b.b[k] * w[k] for k in HYPS)
        lam = self.risk_low if taxi["soc_frac"] < self.low_soc else self.risk_high
        c = self.travel_min(taxi["xy"], st) + exp_w + lam * (worst - exp_w)
        if b.reliable() < 0.5 and st["enroute"] >= self.hedge_cap:
            c += 1e3
        return c, w

    def decide(self, taxi, stations, now):
        costs, waits = {}, {}
        for j, st in stations.items():
            costs[j], waits[j] = self._cost(j, st, taxi, self.hedge_cap)
        best = min(costs, key=costs.get)
        # value of (perfect) information about the best station's explanation
        if now - self.last_verified.get(best, -1e9) >= self.cooldown:
            b = self._b(best).b
            travel = self.travel_min(taxi["xy"], stations[best])
            others = {j: c for j, c in costs.items() if j != best}
            def loss(a, k):
                return travel + waits[best][k] if a == best else others[a]
            actions = [best] + list(others)
            ev_now = min(sum(b[k] * loss(a, k) for k in HYPS) for a in actions)
            ev_info = sum(b[k] * min(loss(a, k) for a in actions) for k in HYPS)
            if ev_now - ev_info > self.verify_min:
                self.last_verified[best] = now
                self.n_verify += 1
                return ("verify", best)
        return ("go", best)

    def diagnosis(self):
        d = {j: {k: round(b.b[k], 3) for k in HYPS} | {"surprise": round(b.surprise, 2)}
             for j, b in self.beliefs.items()}
        if self.network and self.net is not None:
            d["network"] = {"P_compromised": round(self.net.p_compromised(), 3)}
        return d


class ReasoningIndep(Reasoning):
    """Ablation: the same reasoning, but each station is filtered independently
    (no shared network state)."""
    name = "Reasoning-Indep"

    def __init__(self, plugs, **kw):
        super().__init__(plugs, network=False, **kw)


class _FixedBelief:
    def __init__(self, k):
        self.b = {h: (1.0 if h == k else 0.0) for h in HYPS}
        self.surprise, self.n_obs = 0.0, 0

    def reliable(self):
        return self.b["N"] + self.b["C"]

    def inadequate(self, threshold):
        return False


class CusumPlus(Reasoning):
    """Fairness baseline: CUSUM detection + the same decision rule as Reasoning
    (expected cost, battery-aware risk, hedging). Before the CUSUM alarm every
    station is believed normal; after it, every station is believed attacked.
    This separates the value of the reasoning from the value of the decision rule."""
    name = "CUSUM+"

    def __init__(self, plugs, **kw):
        super().__init__(plugs, network=False, **kw)
        self.cusum = Cusum(plugs)

    def on_minute(self, now, reports):
        Base.on_minute(self, now, reports)

    def on_observation(self, j, rep, obs, extreme, now):
        self.cusum.on_observation(j, rep, obs, extreme, now)
        if self.alarm_time is None and self.cusum.alarm_time is not None:
            self.alarm_time = self.cusum.alarm_time

    def _b(self, j):
        return _FixedBelief("A" if self.alarm_time is not None else "N")

    def diagnosis(self):
        return {}


CONTROLLERS = {c.name: c for c in (TrustAll, Threshold, Cusum, CusumPlus, ReasoningIndep, Reasoning)}
