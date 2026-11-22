"""Figures for the README (results/figures/*.png)."""
import glob
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, "results", "runs")
OUT = os.path.join(ROOT, "results", "figures")
os.makedirs(OUT, exist_ok=True)
TARGET = "Strip District"

INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e5e1"
HCOL = {"N": "#2a78d6", "C": "#1baf7a", "F": "#eda100", "A": "#eb6834"}
HNAME = {"N": "Normal", "C": "Congestion", "F": "Reporting fault", "A": "Attack"}
CTRLS = ["TrustAll", "CUSUM", "CUSUM+", "Reasoning-Indep", "Reasoning"]
CCOL = {"TrustAll": "#8a8984", "CUSUM": "#2a78d6", "CUSUM+": "#6250d6", "Reasoning-Indep": "#1baf7a",
        "Reasoning": "#eb6834"}
SCN = {"normal": "Normal", "congestion": "Congestion", "fault": "Reporting fault", "attack": "Network attack",
       "local_attack": "Local attack"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": INK2,
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2})


def style(ax):
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def belief_figure(seed=1):
    scen = ["normal", "congestion", "fault", "attack", "local_attack"]
    fig, axs = plt.subplots(1, 5, figsize=(18, 3.7), sharey=True)
    for ax, sc in zip(axs, scen):
        b = pd.read_csv(os.path.join(RUNS, f"beliefs_{sc}_Reasoning_seed{seed}.csv"))
        for k in "NCFA":
            ax.plot(b.t / 3600, b[f"{TARGET}|{k}"], color=HCOL[k], lw=2, label=HNAME[k])
        if "network|compromised" in b:
            ax.plot(b.t / 3600, b["network|compromised"], color=INK, lw=1.4, ls=":", label="Network compromised")
        ax.axvline(1, color=INK2, lw=1, ls="--")
        ax.set_title(f"{SCN[sc]} day", loc="left", color=INK, fontsize=11)
        ax.set_xlabel("Hour")
        ax.set_ylim(0, 1.02)
        style(ax)
    axs[0].set_ylabel(f"Belief about {TARGET}")
    axs[0].text(1.04, 0.45, "event\nstarts", color=INK2, fontsize=8)
    h, l = axs[-2].get_legend_handles_labels()
    fig.legend(h, l, frameon=False, loc="lower center", ncol=5, fontsize=9.5)
    fig.suptitle("What the fleet believes is happening at the Strip District station, and whether the whole "
                 "reporting network is compromised (Reasoning controller, day 1)",
                 x=0.01, ha="left", color=INK, fontweight="bold")
    fig.tight_layout(rect=(0, 0.07, 1, 0.92))
    fig.savefig(os.path.join(OUT, "beliefs.png"), dpi=160)


def outcome_figure():
    df = pd.DataFrame([json.load(open(f)) for f in glob.glob(os.path.join(RUNS, "summary_*.json"))])
    scen = ["attack", "local_attack", "fault", "congestion"]
    fig, axs = plt.subplots(1, 2, figsize=(16, 4.2), gridspec_kw={"width_ratios": [2.2, 1]})
    ax = axs[0]
    w = 0.16
    for i, c in enumerate(CTRLS):
        m = [df[(df.scenario == s) & (df.controller == c)].taxi_hours_queued.mean() for s in scen]
        sd = [df[(df.scenario == s) & (df.controller == c)].taxi_hours_queued.std() for s in scen]
        x = np.arange(len(scen)) + (i - 2) * w
        ax.bar(x, m, width=w * 0.92, color=CCOL[c], label=c, yerr=sd, error_kw=dict(ecolor=INK2, lw=0.8, capsize=2))
    ax.set_xticks(range(len(scen)))
    ax.set_xticklabels([SCN[s] for s in scen])
    ax.set_ylabel("Taxi-hours in charger lines")
    ax.set_title("Fleet time lost in charger lines (mean ± sd over days)", loc="left", color=INK, fontsize=11)
    ax.legend(frameon=False, ncol=5, fontsize=9, loc="upper right")
    ax = axs[1]
    att = df[df.scenario.isin(["attack", "local_attack"])]
    for i, c in enumerate(CTRLS[1:]):
        for j, s in enumerate(["attack", "local_attack"]):
            v = att[(att.controller == c) & (att.scenario == s)].alarm_min_after_event.dropna()
            ax.scatter(np.full(len(v), i + (j - 0.5) * 0.25), v, color=CCOL[c], s=22, zorder=3,
                       marker="o" if s == "attack" else "^", edgecolor="white", linewidth=0.5)
    ax.set_xticks(range(4))
    ax.set_xticklabels(CTRLS[1:], fontsize=9)
    ax.set_ylabel("Minutes after attack starts")
    ax.set_title("Time to detect (● network, ▲ local attack)", loc="left", color=INK, fontsize=11)
    for ax in axs:
        style(ax)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "outcomes.png"), dpi=160)


if __name__ == "__main__":
    belief_figure()
    outcome_figure()
    print("saved to", OUT)
