"""Combine sumo-gui screenshots into labelled figures for the README."""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.patches import Patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "results", "figures", "sumo")
INK = "#0b0b0b"
LEGEND = [("Picking up / carrying a passenger", "#1e78e6"), ("Idle", "#3c3c3c"), ("Driving to a charger", "#f58200"),
          ("Charging", "#14af78"), ("Waiting in a charger line", "#e63228"), ("Other traffic", "#d7d7d7")]
handles = [Patch(facecolor=c, edgecolor="none", label=l) for l, c in LEGEND]


def crop(img, top=0, bottom=40):
    return img[top:img.shape[0] - bottom, :, :]


fig, axs = plt.subplots(1, 2, figsize=(16, 4.9))
for ax, (ctrl, title) in zip(axs, [("TrustAll", "No defense: a line of taxis (red) waits behind the chargers"),
                                   ("Reasoning", "With the reasoning controller: no line, taxis sent elsewhere")]):
    ax.imshow(crop(mpimg.imread(os.path.join(D, f"attack_{ctrl}_target_h2.0.png"))))
    ax.set_title(title, loc="left", color=INK, fontsize=12)
    ax.axis("off")
fig.legend(handles=handles, loc="lower center", ncol=6, frameon=False, fontsize=10)
fig.suptitle("Network attack, day 1, hour 2: the Strip District charging station in sumo-gui",
             x=0.01, ha="left", color=INK, fontweight="bold", fontsize=13)
fig.tight_layout(rect=(0, 0.06, 1, 0.94))
fig.savefig(os.path.join(ROOT, "results", "figures", "sumo_attack_station.png"), dpi=130)

fig, ax = plt.subplots(figsize=(11, 8.4))
ax.imshow(crop(mpimg.imread(os.path.join(D, "attack_TrustAll_overview_h2.0.png")))[:, 200:1430])
ax.axis("off")
ax.set_title("The simulated area in sumo-gui: 40 e-taxis and 4 charging stations\n(network attack, no defense, hour 2)", loc="left", color=INK, fontsize=11.5)
fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False, fontsize=10)
fig.tight_layout(rect=(0, 0.08, 1, 1))
fig.savefig(os.path.join(ROOT, "results", "figures", "sumo_overview.png"), dpi=130)
print("ok")
