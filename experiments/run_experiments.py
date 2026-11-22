"""Run every scenario x controller x seed in parallel and collect the summaries.

    python experiments/run_experiments.py --seeds 1 2 3 4 5 6 --workers 2
    # verification-cost sweep (held-out and outage scenarios)
    python experiments/run_experiments.py --verify-min 1 --out results/sweep/verify1 \
        --scenarios fault outage subtle_attack intermittent_attack --controllers Reasoning+EVSI Reasoning+EVSI-solo
"""
import argparse
import itertools
import json
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENARIOS = ["normal", "congestion", "fault", "attack", "local_attack",
             "subtle_attack", "intermittent_attack", "outage"]
CONTROLLERS = ["TrustAll", "CUSUM", "CUSUM+", "Reasoning", "Reasoning+EVSI"]


def run(job):
    sc, ctrl, seed, out, hours, vmin = job
    tag = f"{sc}_{ctrl}_seed{seed}"
    if os.path.exists(os.path.join(out, f"summary_{tag}.json")):
        return tag, "cached"
    r = subprocess.run([sys.executable, os.path.join(ROOT, "sim", "etaxi_env.py"), "--scenario", sc,
                        "--controller", ctrl, "--seed", str(seed), "--hours", str(hours), "--verify-min", str(vmin), "--out", out],
                       capture_output=True, text=True)
    return tag, "ok" if r.returncode == 0 else r.stderr[-500:]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--hours", type=float, default=3.0)
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "runs"))
    ap.add_argument("--verify-min", type=float, default=3.0)
    ap.add_argument("--scenarios", nargs="+", default=SCENARIOS)
    ap.add_argument("--controllers", nargs="+", default=CONTROLLERS)
    a = ap.parse_args()
    SC, CT = a.scenarios, a.controllers
    os.makedirs(a.out, exist_ok=True)
    # one run per seed first, so the background-traffic file is created once per seed
    first = [(SC[0], CT[0], s, a.out, a.hours, a.verify_min) for s in a.seeds]
    rest = [(sc, c, s, a.out, a.hours, a.verify_min) for s, sc, c in itertools.product(a.seeds, SC, CT)
            if (sc, c) != (SC[0], CT[0])]
    with ProcessPoolExecutor(a.workers) as ex:
        for tag, status in ex.map(run, first):
            print(tag, status, flush=True)
        for tag, status in ex.map(run, rest):
            print(tag, status, flush=True)
