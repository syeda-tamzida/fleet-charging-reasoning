"""Multi-hypothesis Bayesian filter for charging-station information reliability.

For every station j the fleet keeps a belief over four explanations of what
it sees:

    N  normal       reports are accurate; small mismatches come from plugs
                    being taken while a taxi drives there
    C  congestion   reports are accurate but the station is busy and changes
                    fast, so mismatches are more frequent and reports show low
                    availability
    F  fault        the report is stale or frozen (communication/reporting
                    failure): mismatches in both directions, reports stop changing
    A  attack       reports are deliberately falsified: large over-reports
                    ("all plugs free" while a line is waiting), extreme values,
                    reports stop changing

The belief is a hidden Markov model (HMM) filter:

    predict:  b_t(k) = sum_l T(l -> k) b_{t-1}(l)          (explanations can change)
    update:   b_t(k) proportional to P(o_t | k) b_t(k)      (Bayes' rule)

Two kinds of observation o_t update the belief:

  1. arrival / verification  the fleet compares the reported availability with
                             what a taxi actually finds (discrepancy D, and
                             whether the report was an extreme value)
  2. report stream           every 10 minutes: did the reported value change, and
                             is it "jammed" (no plug free, 3 or more waiting)?

"Model inadequacy" is measured by the predictive probability of each
observation under the current belief,

    P(o_t | history) = sum_k P(o_t | k) b_t(k),

and tracked as an exponentially weighted average of the surprise -log P.
When the average surprise stays high, none of the four explanations fits the
data and the controller switches to conservative decisions.

All likelihood numbers are explicit (see the tables below). The default values
are hand-set assumptions. If reasoning/likelihoods.json exists (written by
experiments/calibrate.py), the N, C, F and A rows are replaced by values
estimated on calibration days (seeds 101-102) of the *training* situations
only: normal, congestion, fault, and the two "all plugs free" attacks. The
stealthy attacks and the charger outage are never used for calibration, so the
test on them checks whether the model transfers to situations it has not seen.

A verification (phone call, station camera, a fleet vehicle nearby) is an
imperfect observation Y of the same discrepancy: it is right with probability
VERIFY_ACCURACY and otherwise uninformative,

    P(Y = y | k) = q * P_DISC[k][y] + (1 - q) / 3.
"""
import json
import math
import os

HYPS = ("N", "C", "F", "A")

# P(discrepancy bin | hypothesis). D = reported availability - observed availability
# (availability = free plugs - waiting vehicles). Bins: D <= 0, D == 1, D >= 2.
#   N: calibrated on simulated normal days (seeds 101-102): 0.94 / 0.06 / 0.00,
#      smoothed so no outcome has zero probability.
#   C: assumption (too few calibration arrivals at a congested station): accurate
#      reports, but plugs are taken more often while a taxi drives there.
#   F, A: assumptions that encode the definitions in the module docstring.
P_DISC = {
    "N": (0.92, 0.07, 0.01),
    "C": (0.80, 0.15, 0.05),
    "F": (0.45, 0.30, 0.25),
    "A": (0.10, 0.20, 0.70),
}
# P(report is an extreme value | hypothesis). Extreme = "all plugs free and no
# queue" or "no plug free and a long queue (>= 3)". N calibrated: 0.30.
P_EXTREME = {"N": 0.30, "C": 0.10, "F": 0.30, "A": 0.90}
# P(report is "jammed" = no plug free and >= 3 waiting | hypothesis), used in the
# 10-minute report checks. N calibrated: 0.00 in 192 normal reports (smoothed to 0.01).
# Under A, a station is either shown as "all free" or as "jammed".
P_JAMMED = {"N": 0.01, "C": 0.05, "F": 0.05, "A": 0.50}
# P(report value changed during the last 10 minutes | hypothesis).
# N calibrated: 0.62. C calibrated at the congested station: 0.62.
P_CHANGED = {"N": 0.62, "C": 0.62, "F": 0.05, "A": 0.05}

VERIFY_ACCURACY = 0.8   # probability that a verification returns the true availability

# Replace the hand-set rows by calibrated ones when experiments/calibrate.py has run.
CALIBRATED = False
_cal = os.path.join(os.path.dirname(os.path.abspath(__file__)), "likelihoods.json")
if os.path.exists(_cal) and os.environ.get("HAND_SET_LIKELIHOODS") != "1":
    _c = json.load(open(_cal))
    P_DISC = {k: tuple(v) for k, v in _c["P_DISC"].items()}
    P_EXTREME, P_JAMMED, P_CHANGED = _c["P_EXTREME"], _c["P_JAMMED"], _c["P_CHANGED"]
    CALIBRATED = True

PRIOR = {"N": 0.90, "C": 0.05, "F": 0.03, "A": 0.02}
STAY = 0.995          # per-minute probability that the explanation stays the same


def disc_bin(d):
    return 0 if d <= 0 else (1 if d == 1 else 2)


def arrival_likelihood(reported_avail, observed_avail, report_extreme):
    d = disc_bin(reported_avail - observed_avail)
    return {k: P_DISC[k][d] * (P_EXTREME[k] if report_extreme else 1 - P_EXTREME[k]) for k in HYPS}


def verify_likelihood(y_bin, q=VERIFY_ACCURACY):
    """P(verification result falls in discrepancy bin y | hypothesis)."""
    return {k: q * P_DISC[k][y_bin] + (1 - q) / 3 for k in HYPS}


def stream_likelihood(changed, jammed):
    return {k: (P_CHANGED[k] if changed else 1 - P_CHANGED[k]) *
            (P_JAMMED[k] if jammed else 1 - P_JAMMED[k]) for k in HYPS}


class StationBelief:
    """Independent filter for one station (the 'Reasoning-Indep' variant)."""
    def __init__(self, surprise_alpha=0.3):
        self.b = dict(PRIOR)
        self.surprise = 0.0          # EWMA of -log predictive probability
        self.alpha = surprise_alpha
        self.n_obs = 0

    # -- predict step: once per minute --------------------------------------
    def predict(self):
        switch = (1 - STAY) / (len(HYPS) - 1)
        old = self.b
        self.b = {k: sum(old[l] * (STAY if l == k else switch) for l in HYPS) for k in HYPS}

    # -- update step --------------------------------------------------------
    def _update(self, lik):
        pred = sum(lik[k] * self.b[k] for k in HYPS)
        post = {k: lik[k] * self.b[k] / pred for k in HYPS}
        self.b = post
        s = -math.log(max(pred, 1e-12))
        self.surprise = (1 - self.alpha) * self.surprise + self.alpha * s
        self.n_obs += 1
        return pred

    def observe_arrival(self, reported_avail, observed_avail, report_extreme):
        return self._update(arrival_likelihood(reported_avail, observed_avail, report_extreme))

    def observe_stream(self, changed, jammed=False):
        return self._update(stream_likelihood(changed, jammed))

    def observe_verification(self, reported_avail, observed_avail):
        return self._update(verify_likelihood(disc_bin(reported_avail - observed_avail)))

    # -- summaries ------------------------------------------------------------
    def reliable(self):
        """Probability that the report can be used as is (normal or congestion)."""
        return self.b["N"] + self.b["C"]

    def entropy(self):
        return -sum(p * math.log(p) for p in self.b.values() if p > 0)

    def inadequate(self, threshold):
        """None of the explanations fits: average surprise is high."""
        return self.n_obs >= 3 and self.surprise > threshold
