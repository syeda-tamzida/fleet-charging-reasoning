"""Small SUMO test scenario: an electric taxi fleet in Oakland / Strip District /
Lawrenceville / Bloomfield (Pittsburgh), with 4 charging stations.

SUMO moves the vehicles through traffic. This file plays everything else:
ride requests, dispatch, batteries, charging plugs and queues, the charging
network's status reports, and the four test situations:

  normal      reports are accurate; public EVs occasionally use a plug
  congestion  from --event-start, public EVs come and go at the Strip District
              station every 3 minutes (1-3 of 3 plugs busy). Reports stay
              accurate, but can be out of date by the time a taxi arrives.
  fault       from --event-start, the Strip District report freezes at its
              last value (stale data, no malice)
  attack      from --event-start, the network reports the Strip District
              station as "all plugs free, no queue" and every other station
              as "full, 4 waiting" (network-wide false data that herds the fleet)
  local_attack  only the Strip District report is falsified ("all plugs free");
              the other stations report honestly

The charging decision is delegated to a controller from reasoning/controllers.py.
"""
import argparse
import csv
import json
import math
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
try:
    import sumo  # pip package eclipse-sumo; preferred over any older SUMO install
    os.environ["SUMO_HOME"] = sumo.SUMO_HOME
except ImportError:
    pass
sys.path.insert(0, os.path.join(os.environ["SUMO_HOME"], "tools"))
import sumolib  # noqa: E402
import traci  # noqa: E402
import traci.constants as tc  # noqa: E402

from reasoning.controllers import CONTROLLERS  # noqa: E402

STATIONS = [("Strip District", 40.4520, -79.9840), ("Oakland", 40.4445, -79.9490),
            ("Bloomfield", 40.4610, -79.9500), ("Lawrenceville", 40.4660, -79.9610)]
TARGET = "Strip District"


def parse(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scenario", choices=["normal", "congestion", "fault", "attack", "local_attack"], default="attack")
    ap.add_argument("--controller", choices=list(CONTROLLERS), default="Reasoning")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--hours", type=float, default=3.0)
    ap.add_argument("--event-start", type=float, default=1.0, help="hours")
    ap.add_argument("--taxis", type=int, default=40)
    ap.add_argument("--demand", type=float, default=120, help="ride requests per hour")
    ap.add_argument("--plugs", type=int, default=3)
    ap.add_argument("--battery", type=float, default=30.0)
    ap.add_argument("--kwh-per-km", type=float, default=0.2)
    ap.add_argument("--charge-kw", type=float, default=50.0)
    ap.add_argument("--go-charge", type=float, default=0.30)
    ap.add_argument("--min-dispatch", type=float, default=0.15)
    ap.add_argument("--background", type=float, default=8.0, help="seconds between background cars, 0 = none")
    ap.add_argument("--gui", action="store_true")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(HERE), "results", "runs"))
    return ap.parse_args(argv)


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


class Env:
    def __init__(self, a):
        self.a = a
        self.rng = random.Random(a.seed)
        self.net = sumolib.net.readNet(os.path.join(HERE, "oak.net.xml"))
        scc = set(open(os.path.join(HERE, "scc_edges.txt")).read().split())
        self.edges = [e for e in self.net.getEdges()
                      if e.getID() in scc and e.getLength() > 25 and self.lane(e) is not None]
        self.center = {e.getID(): self.mid(e) for e in self.edges}
        self.cap = a.battery
        self.T = int(a.hours * 3600)
        self.event_t = int(a.event_start * 3600)
        self.st = {}
        for name, lat, lon in STATIONS:
            x, y = self.net.convertLonLat2XY(lon, lat)
            e = min(self.edges, key=lambda e: dist(self.center[e.getID()], (x, y)))
            self.st[name] = dict(edge=e.getID(), xy=self.center[e.getID()], fleet=set(), queue=[],
                                 public=0, enroute=set())
        self.ctrl = CONTROLLERS[a.controller](a.plugs, session_min=0.55 * self.cap / a.charge_kw * 60)
        self.taxis, self.requests, self.pending, self.log = {}, [], [], []
        self.queue_seconds = 0
        self.verify_seconds = 0
        self.stranded = set()
        self.frozen_report = None
        self.disc_log = []    # discrepancy observations, for calibration
        self.report_log = []  # reported values every 10 minutes, for calibration

    # --- helpers --------------------------------------------------------------
    @staticmethod
    def lane(e):
        for i, l in enumerate(e.getLanes()):
            if l.allows("passenger"):
                return i
        return None

    @staticmethod
    def mid(e):
        return sumolib.geomhelper.positionAtShapeOffset(e.getShape(), e.getLength() / 2)

    def stop_pos(self, edge):
        return max(1.0, self.net.getEdge(edge).getLength() - 5.0)

    def go(self, vid, edge):
        t = self.taxis[vid]
        try:
            if traci.vehicle.getStopState(vid) & 1:
                traci.vehicle.resume(vid)
            for _ in range(len(traci.vehicle.getStops(vid))):
                try:
                    traci.vehicle.replaceStop(vid, 0, "")
                except traci.TraCIException:
                    break
            traci.vehicle.changeTarget(vid, edge)
            traci.vehicle.setStop(vid, edge, pos=self.stop_pos(edge), laneIndex=self.lane(self.net.getEdge(edge)),
                                  duration=1e7, flags=tc.STOP_PARKING)
            t["target"] = edge
            return True
        except traci.TraCIException:
            t["target"] = None
            return False

    def arrived(self, vid):
        t = self.taxis[vid]
        return t["target"] is not None and t["road"] == t["target"] and t["stop"] & 1

    # --- truth and reports ------------------------------------------------------
    def true_free(self, s):
        return max(0, self.a.plugs - s["public"] - len(s["fleet"]))

    def true_report(self, s):
        return (self.true_free(s), len(s["queue"]))

    def reports(self, now):
        sc = self.a.scenario
        rep = {}
        for name, s in self.st.items():
            r = self.true_report(s)
            if now >= self.event_t and sc == "attack":
                r = (self.a.plugs, 0) if name == TARGET else (0, 4)
            if now >= self.event_t and sc == "local_attack" and name == TARGET:
                r = (self.a.plugs, 0)
            if now >= self.event_t and sc == "fault" and name == TARGET:
                if self.frozen_report is None:
                    self.frozen_report = r
                r = self.frozen_report
            rep[name] = r
        return rep

    def is_extreme(self, r):
        return (r[0] == self.a.plugs and r[1] == 0) or (r[0] == 0 and r[1] >= 3)

    def observe(self, name, now, rep_now):
        """What a taxi (or a verification) finds at station `name`, fed to the controller."""
        s = self.st[name]
        r = rep_now[name]
        reported_avail = r[0] - r[1]
        observed_avail = self.true_free(s) - len(s["queue"])
        self.ctrl.on_observation(name, reported_avail, observed_avail, self.is_extreme(r), now)
        self.disc_log.append((now, name, reported_avail - observed_avail, int(self.is_extreme(r))))

    def public_update(self, now, rng):
        for name, s in self.st.items():
            room = self.a.plugs - len(s["fleet"])
            if self.a.scenario == "congestion" and name == TARGET and now >= self.event_t:
                # busy and fast-changing: public EVs come and go every 3 minutes, so an
                # accurate report can be out of date by the time a taxi arrives
                want = rng.choice([1, 2, 3, 3])
            elif self.a.scenario == "congestion" and now >= self.event_t and now % 900 != 0:
                continue          # other stations keep their normal 15-minute rhythm
            else:
                want = 1 if rng.random() < 0.3 else 0
            s["public"] = max(0, min(want, room))

    # --- main loop -----------------------------------------------------------------
    def background(self):
        if self.a.background <= 0:
            return None
        folder = os.path.join(os.path.dirname(HERE), "results", "background")
        os.makedirs(folder, exist_ok=True)
        out = os.path.join(folder, f"bg_seed{self.a.seed}_h{self.a.hours}_p{self.a.background}.rou.xml")
        if not os.path.exists(out):
            tmp = out.replace(".rou.xml", f".{os.getpid()}.tmp")   # parallel runs must not share a temp file
            subprocess.run([sys.executable, os.path.join(os.environ["SUMO_HOME"], "tools", "randomTrips.py"),
                            "-n", os.path.join(HERE, "oak.net.xml"), "-e", str(self.T), "-p", str(self.a.background),
                            "--seed", str(self.a.seed), "--fringe-factor", "5", "--min-distance", "500",
                            "--validate", "-o", tmp + ".trips.xml", "-r", tmp + ".rou.xml"],
                           check=True, capture_output=True)
            os.replace(tmp + ".rou.xml", out)
            os.remove(tmp + ".trips.xml")
        return out

    def run(self):
        os.makedirs(self.a.out, exist_ok=True)
        bg = self.background()
        cmd = [sumolib.checkBinary("sumo-gui" if self.a.gui else "sumo"), "-n", os.path.join(HERE, "oak.net.xml"),
               "--step-length", "1", "--no-step-log", "--duration-log.disable", "--no-warnings",
               "--time-to-teleport", "120", "--ignore-junction-blocker", "20", "--ignore-route-errors",
               "--device.rerouting.probability", "1", "--device.rerouting.period", "60", "--seed", str(self.a.seed)]
        if bg:
            cmd += ["-r", bg]
        traci.start(cmd)
        traci.vehicletype.copy("DEFAULT_VEHTYPE", "etaxi")
        traci.vehicletype.setColor("etaxi", (0, 200, 255, 255))
        for i in range(self.a.taxis):
            vid = f"etaxi{i}"
            e = self.rng.choice(self.edges).getID()
            traci.route.add("r_" + vid, [e])
            traci.vehicle.add(vid, "r_" + vid, typeID="etaxi", departPos="0", departLane="best")
            traci.vehicle.setStop(vid, e, pos=self.stop_pos(e), laneIndex=self.lane(self.net.getEdge(e)),
                                  duration=1e7, flags=tc.STOP_PARKING)
            traci.vehicle.subscribe(vid, [tc.VAR_DISTANCE, tc.VAR_ROAD_ID, tc.VAR_STOPSTATE, tc.VAR_POSITION])
            self.taxis[vid] = dict(state="idle", soc=self.rng.uniform(0.2, 0.6) * self.cap, odo=None, target=e,
                                   road=None, stop=0, xy=self.center[e], req=None, station=None, verify_until=None,
                                   verify_station=None)
        t, rate = 0.0, self.a.demand / 3600.0
        while True:
            t += self.rng.expovariate(rate)
            if t >= self.T:
                break
            while True:
                o, d = self.rng.choice(self.edges), self.rng.choice(self.edges)
                if 800 < dist(self.center[o.getID()], self.center[d.getID()]) < 4000:
                    break
            self.requests.append(dict(t=int(t), o=o.getID(), d=d.getID(), xy=self.center[o.getID()],
                                      status="waiting", pickup=None))
        it = iter(self.requests)
        nxt = next(it, None)
        prng = random.Random(self.a.seed + 1000)
        rep = self.reports(0)

        for now in range(self.T):
            traci.simulationStep()
            subs = traci.vehicle.getAllSubscriptionResults()
            for vid, tx in self.taxis.items():
                r = subs.get(vid)
                if not r:
                    continue
                tx["road"], tx["stop"], tx["xy"] = r[tc.VAR_ROAD_ID], r[tc.VAR_STOPSTATE], r[tc.VAR_POSITION]
                odo = r[tc.VAR_DISTANCE]
                if odo >= 0:
                    if tx["odo"] is not None and odo > tx["odo"]:
                        tx["soc"] -= (odo - tx["odo"]) / 1000.0 * self.a.kwh_per_km
                    tx["odo"] = odo
                if tx["soc"] <= 0 and tx["state"] != "dead":
                    tx["soc"] = 0
                    tx["state"] = "dead"
                    self.stranded.add(vid)
            congested = self.a.scenario == "congestion" and now >= self.event_t
            if now % 900 == 0 or (congested and now % 180 == 0):
                self.public_update(now, prng)
            if now % 60 == 0:
                rep = self.reports(now)
                self.ctrl.on_minute(now, rep)
                if now % 600 == 0:
                    self.report_log.extend((now, n, r[0], r[1]) for n, r in rep.items())
            while nxt is not None and nxt["t"] <= now:
                self.pending.append(nxt)
                nxt = next(it, None)

            for vid, tx in self.taxis.items():
                st = tx["state"]
                if st == "to_pickup" and self.arrived(vid):
                    tx["req"]["pickup"] = now
                    self.go(vid, tx["req"]["d"])
                    tx["state"] = "to_dropoff"
                elif st == "to_dropoff" and self.arrived(vid):
                    tx["req"]["status"] = "served"
                    tx["req"] = None
                    tx["state"] = "idle"
                elif st == "to_charger" and self.arrived(vid):
                    self.arrive_station(vid, now, rep)
                elif st == "charging":
                    tx["soc"] = min(self.cap, tx["soc"] + self.a.charge_kw / 3600.0)
                    if tx["soc"] >= 0.8 * self.cap:
                        self.leave_station(vid)
                elif st == "queued":
                    self.queue_seconds += 1
                elif st == "verifying":
                    self.verify_seconds += 1
                    if now >= tx["verify_until"]:
                        self.observe(tx["verify_station"], now, rep)
                        tx["state"] = "idle"
                        self.charge_decision(vid, now, allow_verify=False)
                if tx["state"] == "idle" and tx["soc"] < self.a.go_charge * self.cap:
                    self.charge_decision(vid, now)
                if tx["state"] in ("to_pickup", "to_dropoff", "to_charger") and tx["target"] is None:
                    tgt = (tx["req"]["o"] if tx["state"] == "to_pickup" else tx["req"]["d"]
                           if tx["state"] == "to_dropoff" else self.st[tx["station"]]["edge"])
                    self.go(vid, tgt)
            if now % 5 == 0:
                self.dispatch(now)
            if now % 60 == 0:
                self.snapshot(now)
        traci.close()
        return self.summary()

    def station_view(self):
        return {n: dict(xy=s["xy"], enroute=len(s["enroute"]), fleet_charging=len(s["fleet"]),
                        fleet_queued=len(s["queue"])) for n, s in self.st.items()}

    def charge_decision(self, vid, now, allow_verify=True):
        tx = self.taxis[vid]
        taxi = dict(xy=tx["xy"], soc_frac=tx["soc"] / self.cap)
        action, name = self.ctrl.decide(taxi, self.station_view(), now)
        if action == "verify" and allow_verify:
            tx.update(state="verifying", verify_until=now + int(self.ctrl.verify_min * 60), verify_station=name)
            return
        if action == "verify":
            action = "go"
        if self.go(vid, self.st[name]["edge"]):
            tx.update(state="to_charger", station=name)
            self.st[name]["enroute"].add(vid)

    def arrive_station(self, vid, now, rep):
        tx = self.taxis[vid]
        s = self.st[tx["station"]]
        s["enroute"].discard(vid)
        self.observe(tx["station"], now, rep)
        if self.true_free(s) > 0 and not s["queue"]:
            s["fleet"].add(vid)
            tx["state"] = "charging"
        else:
            s["queue"].append(vid)
            tx["state"] = "queued"

    def leave_station(self, vid):
        tx = self.taxis[vid]
        s = self.st[tx["station"]]
        s["fleet"].discard(vid)
        tx.update(state="idle", station=None)
        while s["queue"] and self.true_free(s) > 0:
            n = s["queue"].pop(0)
            s["fleet"].add(n)
            self.taxis[n]["state"] = "charging"

    def dispatch(self, now):
        still = []
        idle = [v for v, t in self.taxis.items()
                if t["state"] == "idle" and t["soc"] >= self.a.min_dispatch * self.cap]
        for q in self.pending:
            if now - q["t"] > 900:
                q["status"] = "lost"
                continue
            if not idle:
                still.append(q)
                continue
            vid = min(idle, key=lambda v: dist(self.taxis[v]["xy"], q["xy"]))
            if dist(self.taxis[vid]["xy"], q["xy"]) > 4000 or not self.go(vid, q["o"]):
                still.append(q)
                continue
            idle.remove(vid)
            self.taxis[vid].update(state="to_pickup", req=q)
            q["status"] = "assigned"
        self.pending = still

    def snapshot(self, now):
        states = [t["state"] for t in self.taxis.values()]
        row = dict(t=now, idle=states.count("idle"), busy=states.count("to_pickup") + states.count("to_dropoff"),
                   to_charger=states.count("to_charger"), queued=states.count("queued"),
                   charging=states.count("charging"), verifying=states.count("verifying"),
                   waiting_requests=len(self.pending))
        for n, s in self.st.items():
            row["queue_" + n] = len(s["queue"])
        self.log.append(row)

    def summary(self):
        waits = sorted((q["pickup"] - q["t"]) / 60 for q in self.requests if q["pickup"] is not None)
        n = len(self.requests)
        c = self.ctrl
        alarm = c.alarm_time
        res = dict(scenario=self.a.scenario, controller=c.name, seed=self.a.seed, requests=n,
                   served_pct=round(100 * sum(q["status"] == "served" for q in self.requests) / n, 1),
                   mean_wait_min=round(sum(waits) / len(waits), 2),
                   p90_wait_min=round(waits[int(0.9 * (len(waits) - 1))], 2),
                   taxi_hours_queued=round(self.queue_seconds / 3600, 2),
                   taxi_hours_verifying=round(self.verify_seconds / 3600, 2),
                   max_queue_target=max(r["queue_" + TARGET] for r in self.log),
                   stranded=len(self.stranded),
                   attack_alarm=alarm is not None,
                   alarm_min_after_event=round((alarm - self.event_t) / 60, 1) if alarm is not None else None,
                   verifications=getattr(c, "n_verify", 0),
                   final_belief=c.diagnosis())
        tag = f"{self.a.scenario}_{c.name}_seed{self.a.seed}"
        with open(os.path.join(self.a.out, f"summary_{tag}.json"), "w") as f:
            json.dump(res, f, indent=1)
        with open(os.path.join(self.a.out, f"timeseries_{tag}.csv"), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(self.log[0]))
            w.writeheader()
            w.writerows(self.log)
        if getattr(c, "history", None):
            with open(os.path.join(self.a.out, f"beliefs_{tag}.csv"), "w", newline="") as f:
                keys = sorted({k for h in c.history for k in h}, key=lambda k: (k != "t", k))
                w = csv.DictWriter(f, fieldnames=keys)
                w.writeheader()
                w.writerows(c.history)
        with open(os.path.join(self.a.out, f"discrepancies_{tag}.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["t", "station", "D", "extreme"])
            w.writerows(self.disc_log)
        with open(os.path.join(self.a.out, f"reports_{tag}.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["t", "station", "free", "queue"])
            w.writerows(self.report_log)
        return res


if __name__ == "__main__":
    out = Env(parse()).run()
    out.pop("final_belief", None)
    print(json.dumps(out))
