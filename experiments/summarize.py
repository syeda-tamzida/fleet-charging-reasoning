"""Summarize all runs into results/summary_table.{csv,md}, paired comparisons and the verification sweep.

Main measure: fleet charging loss = taxi-hours driving to a charger + waiting in
a charger line + waiting for a verification. Counting all three avoids a
controller looking better on queues only because it moved the delay elsewhere
(longer drives, or checks).
"""
import glob
import json
import os

import numpy as np
import pandas as pd
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = "Strip District"
ORDER_S = ["normal", "congestion", "fault", "attack", "local_attack", "subtle_attack", "intermittent_attack", "outage"]
HELD_OUT = {"subtle_attack", "intermittent_attack", "outage"}
ORDER_C = ["TrustAll", "Threshold", "CUSUM", "CUSUM+", "Reasoning-Indep", "Reasoning", "Reasoning+EVSI",
           "Reasoning+EVSI-solo"]
LOCAL = {"local_attack", "subtle_attack", "intermittent_attack"}


def load(folder):
    rows = []
    for f in glob.glob(os.path.join(folder, "summary_*.json")):
        d = json.load(open(f))
        fb = d.pop("final_belief", {}) or {}
        d.pop("verify_log", None)
        tb = fb.get(TARGET)
        d["target_diagnosis"] = max("NCFA", key=lambda k: tb[k]) if tb else None
        d["P_network_compromised"] = fb.get("network", {}).get("P_compromised")
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
        "days": g.size(),
        "charging_loss_h": g.charging_loss_h.mean().round(2),
        "loss_sd": g.charging_loss_h.std().round(2),
        "driving_h": g.taxi_hours_to_charger.mean().round(2),
        "queued_h": g.taxi_hours_queued.mean().round(2),
        "verifying_h": g.taxi_hours_verifying.mean().round(2),
        "checks_per_day": g.verifications.mean().round(1),
        "mean_wait_min": g.mean_wait_min.mean().round(2),
        "served_pct": g.served_pct.mean().round(1),
        "attack_alarms": g.attack_alarm.sum().astype(int).astype(str) + "/" + g.size().astype(str),
        "alarm_delay_min": g.alarm_min_after_event.mean().round(1),
        "honest_stations_distrusted": g.distrusted_other_stations.mean().round(1),
    }).reset_index()
    diag = (df[df.controller.str.startswith("Reasoning")].groupby(["scenario", "controller"]).target_diagnosis
            .agg(lambda s: "".join(sorted(s.dropna()))))
    t["Strip_diagnoses"] = t.apply(lambda r: diag.get((r.scenario, r.controller), ""), axis=1)
    t["scenario"] = pd.Categorical(t.scenario, ORDER_S)
    t["controller"] = pd.Categorical(t.controller, ORDER_C)
    return t.sort_values(["scenario", "controller"])


def paired(df, a, b, col="charging_loss_h"):
    """Mean of (a - b) over the same days, with a 95% t interval. Negative = a loses less."""
    out = []
    for sc in ORDER_S:
        x = df[(df.scenario == sc) & (df.controller == a)].set_index("seed")[col]
        y = df[(df.scenario == sc) & (df.controller == b)].set_index("seed")[col]
        d = (x - y).dropna()
        if len(d) < 2:
            continue
        half = stats.t.ppf(0.975, len(d) - 1) * d.std(ddof=1) / np.sqrt(len(d))
        out.append(dict(scenario=sc, comparison=f"{a} - {b}", days=len(d), mean_diff_h=round(d.mean(), 2),
                        ci95_low=round(d.mean() - half, 2), ci95_high=round(d.mean() + half, 2),
                        days_a_better=int((d < 0).sum())))
    return pd.DataFrame(out)


def sweep(main):
    rows = []
    for f in sorted(glob.glob(os.path.join(ROOT, "results", "sweep", "verify*"))):
        rows.append(load(f))
    if not rows:
        return None
    s = pd.concat(rows + [main[main.controller.isin(["Reasoning+EVSI", "Reasoning"]) &
                               main.scenario.isin(["fault", "outage", "subtle_attack", "intermittent_attack"])]])
    s.loc[s.controller == "Reasoning", "verify_min"] = np.nan
    base = s[s.controller == "Reasoning"].set_index(["scenario", "seed"]).charging_loss_h
    s = s[s.controller != "Reasoning"].copy()
    s["loss_vs_no_checks_h"] = s.apply(lambda r: r.charging_loss_h - base[(r.scenario, r.seed)], axis=1)
    g = s.groupby(["controller", "verify_min", "scenario"])
    return pd.DataFrame({"checks_per_day": g.verifications.mean().round(1),
                         "verifying_h": g.taxi_hours_verifying.mean().round(2),
                         "charging_loss_h": g.charging_loss_h.mean().round(2),
                         "loss_vs_no_checks_h": g.loss_vs_no_checks_h.mean().round(2),
                         "days_better_than_no_checks": g.loss_vs_no_checks_h.apply(lambda x: f"{(x < 0).sum()}/{len(x)}")
                         }).reset_index()


if __name__ == "__main__":
    R = os.path.join(ROOT, "results")
    df = load(os.path.join(R, "runs"))
    df.to_csv(os.path.join(R, "all_runs.csv"), index=False)
    t = table(df)
    t.to_csv(os.path.join(R, "summary_table.csv"), index=False)
    p = pd.concat([paired(df, "Reasoning", "CUSUM"), paired(df, "Reasoning", "CUSUM+"),
                   paired(df, "Reasoning+EVSI", "Reasoning"), paired(df, "Reasoning", "TrustAll")])
    p.to_csv(os.path.join(R, "paired_differences.csv"), index=False)
    sw = sweep(df)
    with open(os.path.join(R, "summary_table.md"), "w") as f:
        f.write("## Per scenario and controller (mean over days; hours are taxi-hours per 3-hour day)\n\n")
        f.write(t.to_markdown(index=False))
        f.write("\n\n## Paired differences in charging loss (same days; negative = first controller loses less)\n\n")
        f.write(p.to_markdown(index=False))
        if sw is not None:
            sw.to_csv(os.path.join(R, "verification_sweep.csv"), index=False)
            f.write("\n\n## Verification-cost sweep (loss_vs_no_checks_h: change vs. Reasoning without checks)\n\n")
            f.write(sw.to_markdown(index=False))
    print(t.to_string(index=False))
    print(p.to_string(index=False))
    if sw is not None:
        print(sw.to_string(index=False))
