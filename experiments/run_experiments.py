"""Run every scenario x controller x seed in parallel and collect the summaries.

    python experiments/run_experiments.py --seeds 1 2 3 --workers 4
"""
import argparse
import itertools
import json
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENARIOS = ["normal", "congestion", "fault", "attack", "local_attack"]
CONTROLLERS = ["TrustAll", "CUSUM", "CUSUM+", "Reasoning-Indep", "Reasoning"]


def run(job):
    sc, ctrl, seed, out, hours = job
    tag = f"{sc}_{ctrl}_seed{seed}"
    if os.path.exists(os.path.join(out, f"summary_{tag}.json")):
        return tag, "cached"
    r = subprocess.run([sys.executable, os.path.join(ROOT, "sim", "etaxi_env.py"), "--scenario", sc,
                        "--controller", ctrl, "--seed", str(seed), "--hours", str(hours), "--out", out],
                       capture_output=True, text=True)
    return tag, "ok" if r.returncode == 0 else r.stderr[-500:]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--hours", type=float, default=3.0)
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "runs"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    # one run per seed first, so the background-traffic file is created once per seed
    first = [(SCENARIOS[0], CONTROLLERS[0], s, a.out, a.hours) for s in a.seeds]
    rest = [(sc, c, s, a.out, a.hours) for s, sc, c in itertools.product(a.seeds, SCENARIOS, CONTROLLERS)
            if (sc, c) != (SCENARIOS[0], CONTROLLERS[0])]
    with ProcessPoolExecutor(a.workers) as ex:
        for tag, status in ex.map(run, first):
            print(tag, status, flush=True)
        for tag, status in ex.map(run, rest):
            print(tag, status, flush=True)
