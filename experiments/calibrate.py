"""Estimate the normal (N) and congestion (C) likelihoods from simulated calibration days.

N: all stations on normal days. C: the Strip District station after the
congestion starts (hour 1) on congestion days. Calibration seeds (101, 102)
are different from the test seeds, so the test results are not tuned to them.
"""
import glob
import pandas as pd

def disc_stats(files, station=None, t_min=0):
    d = pd.concat(pd.read_csv(f) for f in files)
    if station:
        d = d[(d.station == station) & (d.t >= t_min)]
    b = pd.cut(d.D, [-99, 0, 1, 99], labels=["D<=0", "D=1", "D>=2"]).value_counts(normalize=True).sort_index()
    return len(d), b.round(3).to_dict(), round(d.extreme.mean(), 3)

def change_rate(files, station=None, t_min=0):
    out = []
    for f in files:
        r = pd.read_csv(f)
        if station:
            r = r[r.station == station]
        for _, g in r.groupby("station"):
            g = g.sort_values("t")
            ch = (g[["free", "queue"]].diff().abs().sum(axis=1) > 0)[g.t > max(t_min, g.t.min())]
            out.extend(ch.tolist())
    return round(sum(out) / len(out), 3), len(out)

base = "results/calibration"
print("NORMAL (N)    n, P(D bins), P(extreme):", disc_stats(glob.glob(f"{base}/discrepancies_normal_*.csv")))
print("NORMAL (N)    P(report changed in 10 min):", change_rate(glob.glob(f"{base}/reports_normal_*.csv")))
print("CONGESTION(C) n, P(D bins), P(extreme):",
      disc_stats(glob.glob(f"{base}/discrepancies_congestion_*.csv"), "Strip District", 3600))
print("CONGESTION(C) P(report changed in 10 min):",
      change_rate(glob.glob(f"{base}/reports_congestion_*.csv"), "Strip District", 3600))
