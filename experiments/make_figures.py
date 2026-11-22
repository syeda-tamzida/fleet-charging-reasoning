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
CTRLS = ["TrustAll", "CUSUM", "CUSUM+", "Reasoning", "Reasoning+EVSI"]
CCOL = {"TrustAll": "#8a8984", "CUSUM": "#2a78d6", "CUSUM+": "#6250d6", "Reasoning": "#eb6834",
        "Reasoning+EVSI": "#1baf7a", "Reasoning+EVSI-solo": "#9bd8bf"}
SCN = {"normal": "Normal", "congestion": "Congestion", "fault": "Reporting fault", "attack": "Network attack",
       "local_attack": "Local attack", "subtle_attack": "Subtle attack*", "intermittent_attack": "On/off attack*",
       "outage": "Charger outage*"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": INK2,
                     "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2})


def style(ax):
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def belief_figure(seed=1):
    scen = list(SCN)
    fig, axs = plt.subplots(2, 4, figsize=(17, 6.6), sharey=True)
    axs = axs.ravel()
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
    for i in (0, 4):
        axs[i].set_ylabel(f"Belief about {TARGET}")
    axs[0].text(1.04, 0.45, "event\nstarts", color=INK2, fontsize=8)
    h, l = axs[3].get_legend_handles_labels()
    fig.legend(h, l, frameon=False, loc="lower center", ncol=5, fontsize=9.5)
    fig.suptitle("What the fleet believes about the Strip District station and the whole reporting network "
                 "(Reasoning, day 1; * = never used for calibration)",
                 x=0.01, ha="left", color=INK, fontweight="bold")
    fig.tight_layout(rect=(0, 0.05, 1, 0.95))
    fig.savefig(os.path.join(OUT, "beliefs.png"), dpi=160)


def outcome_figure():
    df = pd.DataFrame([json.load(open(f)) for f in glob.glob(os.path.join(RUNS, "summary_*.json"))])
    scen = ["normal", "fault", "attack", "local_attack", "subtle_attack", "intermittent_attack", "outage"]
    fig, axs = plt.subplots(1, 2, figsize=(17, 4.4), gridspec_kw={"width_ratios": [2.6, 1]})
    ax = axs[0]
    w = 0.16
    for i, c in enumerate(CTRLS):
        sub = [df[(df.scenario == s) & (df.controller == c)] for s in scen]
        x = np.arange(len(scen)) + (i - 2) * w
        ax.bar(x, [d.charging_loss_h.mean() for d in sub], width=w * 0.92, color=CCOL[c], label=c,
               yerr=[d.charging_loss_h.std() for d in sub], error_kw=dict(ecolor=INK2, lw=0.8, capsize=2))
    ax.set_xticks(range(len(scen)))
    ax.set_xticklabels([SCN[s] for s in scen], fontsize=9)
    ax.set_ylabel("Taxi-hours per day")
    ax.set_title("Fleet charging loss: driving to a charger + waiting in line + waiting for a check "
                 "(mean ± sd over 6 days; * held out)", loc="left", color=INK, fontsize=11)
    ax.legend(frameon=False, ncol=5, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.1))
    ax = axs[1]
    att = ["attack", "local_attack", "subtle_attack", "intermittent_attack"]
    marks = {"attack": "o", "local_attack": "^", "subtle_attack": "s", "intermittent_attack": "D"}
    cs = ["CUSUM", "Reasoning", "Reasoning+EVSI"]
    for i, c in enumerate(cs):
        for j, s in enumerate(att):
            d = df[(df.controller == c) & (df.scenario == s)]
            v = d.alarm_min_after_event.dropna()
            ax.scatter(np.full(len(v), i + (j - 1.5) * 0.18), v, color=CCOL[c], s=22, zorder=3,
                       marker=marks[s], edgecolor="white", linewidth=0.5)
            ax.text(i + (j - 1.5) * 0.18, -9, f"{len(v)}", ha="center", fontsize=7, color=INK2)
    ax.set_xticks(range(len(cs)))
    ax.set_xticklabels(cs, fontsize=9)
    ax.set_ylim(-14, None)
    ax.set_ylabel("Minutes after attack starts")
    ax.set_title("Attack alarms (● network ▲ local ■ subtle ◆ on/off;\nnumbers = days with an alarm, of 6)",
                 loc="left", color=INK, fontsize=10)
    for ax in axs:
        style(ax)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "outcomes.png"), dpi=160)


def sweep_figure():
    f = os.path.join(ROOT, "results", "verification_sweep.csv")
    if not os.path.exists(f):
        return
    sw = pd.read_csv(f)
    scen = ["fault", "outage", "subtle_attack", "intermittent_attack"]
    fig, axs = plt.subplots(1, 2, figsize=(13, 3.8))
    for c, ls in (("Reasoning+EVSI", "-"), ("Reasoning+EVSI-solo", "--")):
        for s in scen:
            d = sw[(sw.controller == c) & (sw.scenario == s)].sort_values("verify_min")
            col = {"fault": "#eda100", "outage": "#eb6834", "subtle_attack": "#6250d6",
                   "intermittent_attack": "#2a78d6"}[s]
            lab = SCN[s] if c == "Reasoning+EVSI" else None
            axs[0].plot(d.verify_min, d.checks_per_day, ls, color=col, marker="o", ms=4, label=lab)
            axs[1].plot(d.verify_min, d.loss_vs_no_checks_h, ls, color=col, marker="o", ms=4, label=lab)
    axs[0].set_ylabel("Checks per day")
    axs[1].set_ylabel("Change in charging loss vs.\nno checks (taxi-hours/day)")
    axs[1].axhline(0, color=INK2, lw=0.8)
    for ax in axs:
        ax.set_xlabel("Cost of one check (minutes the taxi waits)")
        style(ax)
    axs[0].set_title("How often the fleet checks (solid: answer shared by the fleet; dashed: one taxi only)",
                     loc="left", color=INK, fontsize=10)
    axs[1].set_title("Does checking pay off? (below 0 = yes)", loc="left", color=INK, fontsize=10)
    axs[0].legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "verification_sweep.png"), dpi=160)


if __name__ == "__main__":
    belief_figure()
    outcome_figure()
    sweep_figure()
    print("saved to", OUT)
