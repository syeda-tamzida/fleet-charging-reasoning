"""Estimate the likelihood tables from calibration days and write reasoning/likelihoods.json.

Calibration uses only the *training* situations, on seeds (101, 102) that are
never used for testing, with the TrustAll controller (it does not react, so the
data do not depend on the method being tested):

    N  every station on normal days
    C  the Strip District station after the congestion starts
    F  the Strip District station after its report freezes (fault days)
    A  every station after a network-wide attack starts, and the Strip District
       station after a local attack starts (both are "all plugs free" attacks)

The stealthy attacks (subtle_attack, intermittent_attack) and the charger
outage are never used here: they are the held-out test of whether the model
transfers to situations it was not fitted to.

Each probability is a Bayesian estimate that shrinks towards the hand-set value
with M pseudo-observations, p = (count + M * p_hand) / (n + M), and is kept
at least FLOOR, so that a few observations cannot make any outcome impossible.

    python experiments/calibrate.py --run      # simulate the calibration days, then fit
    python experiments/calibrate.py            # fit from existing calibration runs
"""
import argparse
import glob
import json
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["HAND_SET_LIKELIHOODS"] = "1"          # read the hand-set values as the prior
from reasoning import hypotheses as H  # noqa: E402

OUT = os.path.join(ROOT, "results", "calibration")
SEEDS = [101, 102]
TRAIN = ["normal", "congestion", "fault", "attack", "local_attack"]
TARGET, EVENT = "Strip District", 3600
M, FLOOR = 5.0, 0.01


def simulate(job):
    sc, seed = job
    r = subprocess.run([sys.executable, os.path.join(ROOT, "sim", "etaxi_env.py"), "--scenario", sc,
                        "--controller", "TrustAll", "--seed", str(seed), "--out", OUT],
                       capture_output=True, text=True)
    return sc, seed, r.returncode


def select(kind, sc, hyp):
    d = pd.concat(pd.read_csv(f).assign(day=f) for f in glob.glob(f"{OUT}/{kind}_{sc}_TrustAll_seed*.csv"))
    if hyp == "N":
        return d
    d = d[d.t >= EVENT]
    return d if (hyp == "A" and sc == "attack") else d[d.station == TARGET]


def changes(r):
    out = []
    for _, g in r.groupby(["day", "station"]):
        g = g.sort_values("t")
        ch = (g[["free", "queue"]].diff().abs().sum(axis=1) > 0).iloc[1:]
        out += ch.tolist()
    return out


def shrink(count, n, p_hand):
    return max(FLOOR, (count + M * p_hand) / (n + M))


def fit():
    sources = {"N": ["normal"], "C": ["congestion"], "F": ["fault"], "A": ["attack", "local_attack"]}
    res = {"P_DISC": {}, "P_EXTREME": {}, "P_JAMMED": {}, "P_CHANGED": {}, "n": {}}
    for k, scs in sources.items():
        d = pd.concat(select("discrepancies", sc, k) for sc in scs)
        r = pd.concat(select("reports", sc, k) for sc in scs)
        bins = d.D.apply(H.disc_bin)
        disc = [shrink((bins == b).sum(), len(d), H.P_DISC[k][b]) for b in range(3)]
        res["P_DISC"][k] = [round(x / sum(disc), 3) for x in disc]
        res["P_EXTREME"][k] = round(shrink(d.extreme.sum(), len(d), H.P_EXTREME[k]), 3)
        ch = changes(r)
        res["P_CHANGED"][k] = round(min(1 - FLOOR, shrink(sum(ch), len(ch), H.P_CHANGED[k])), 3)
        jam = ((r["free"] == 0) & (r["queue"] >= 3))
        res["P_JAMMED"][k] = round(min(1 - FLOOR, shrink(jam.sum(), len(r), H.P_JAMMED[k])), 3)
        res["n"][k] = {"arrivals": int(len(d)), "report_checks": int(len(r))}
    res["note"] = ("fitted by experiments/calibrate.py on seeds 101-102 of " + ", ".join(TRAIN) +
                   f"; shrinkage M={M} towards the hand-set values, floor {FLOOR}")
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.run:
        os.makedirs(OUT, exist_ok=True)
        with ProcessPoolExecutor(2) as ex:
            for sc, seed, rc in ex.map(simulate, [(sc, s) for sc in TRAIN for s in SEEDS]):
                print(sc, seed, "ok" if rc == 0 else "FAILED")
    res = fit()
    with open(os.path.join(ROOT, "reasoning", "likelihoods.json"), "w") as f:
        json.dump(res, f, indent=1)
    rows = [{"hyp": k, "P(D<=0)": res["P_DISC"][k][0], "P(D=1)": res["P_DISC"][k][1], "P(D>=2)": res["P_DISC"][k][2],
             "P(extreme)": res["P_EXTREME"][k], "P(jammed)": res["P_JAMMED"][k], "P(changed)": res["P_CHANGED"][k],
             **res["n"][k]} for k in H.HYPS]
    print(pd.DataFrame(rows).to_string(index=False))
