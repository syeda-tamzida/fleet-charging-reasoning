"""Summarize all runs into results/summary_table.csv and results/summary_table.md."""
import glob
import json
import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = "Strip District"
ORDER_S = ["normal", "congestion", "fault", "attack", "local_attack"]
ORDER_C = ["TrustAll", "Threshold", "CUSUM", "CUSUM+", "Reasoning-Indep", "Reasoning"]


def load(folder):
    rows = []
    for f in glob.glob(os.path.join(folder, "summary_*.json")):
        d = json.load(open(f))
        fb = d.pop("final_belief", {}) or {}
        tb = fb.get(TARGET)
        d["target_diagnosis"] = max("NCFA", key=lambda k: tb[k]) if tb else None
        d["target_P_attack"] = tb["A"] if tb else None
        d["P_network_compromised"] = fb.get("network", {}).get("P_compromised")
        # honest stations the controller stopped trusting (local attack: the 3 other stations)
        others = [v for k, v in fb.items() if k not in (TARGET, "network")]
        if d["controller"].startswith("Reasoning"):
            d["distrusted_other_stations"] = sum(v["A"] + v["F"] > 0.5 for v in others)
        elif d["controller"] in ("CUSUM", "CUSUM+", "Threshold"):
            d["distrusted_other_stations"] = 3 if d["attack_alarm"] else 0
        else:
            d["distrusted_other_stations"] = 0
        rows.append(d)
    return pd.DataFrame(rows)


def table(df):
    g = df.groupby(["scenario", "controller"])
    t = pd.DataFrame({
        "runs": g.size(),
        "mean_wait_min": g.mean_wait_min.mean().round(2),
        "p90_wait_min": g.p90_wait_min.mean().round(2),
        "taxi_h_queued": g.taxi_hours_queued.mean().round(2),
        "taxi_h_queued_sd": g.taxi_hours_queued.std().round(2),
        "taxi_h_verifying": g.taxi_hours_verifying.mean().round(2),
        "served_pct": g.served_pct.mean().round(1),
        "attack_alarms": g.attack_alarm.sum().astype(int).astype(str) + "/" + g.size().astype(str),
        "alarm_delay_min": g.alarm_min_after_event.mean().round(1),
        "verifications": g.verifications.mean().round(1),
        "other_stations_distrusted": g.distrusted_other_stations.mean().round(1),
    }).reset_index()
    diag = (df[df.controller.str.startswith("Reasoning")].groupby(["scenario", "controller"]).target_diagnosis
            .agg(lambda s: "".join(sorted(s.dropna()))))
    t["Strip_diagnoses"] = t.apply(lambda r: diag.get((r.scenario, r.controller), ""), axis=1)
    t["scenario"] = pd.Categorical(t.scenario, ORDER_S)
    t["controller"] = pd.Categorical(t.controller, ORDER_C)
    return t.sort_values(["scenario", "controller"])


if __name__ == "__main__":
    df = load(os.path.join(ROOT, "results", "runs"))
    df.to_csv(os.path.join(ROOT, "results", "all_runs.csv"), index=False)
    t = table(df)
    t.to_csv(os.path.join(ROOT, "results", "summary_table.csv"), index=False)
    with open(os.path.join(ROOT, "results", "summary_table.md"), "w") as f:
        f.write(t.to_markdown(index=False))
    print(t.to_string(index=False))
