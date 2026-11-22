"""Take sumo-gui screenshots of the simulation for the README.

Taxis are coloured by what they are doing:
    blue   picking up or carrying a passenger
    dark gray idle
    orange driving to a charger
Background traffic is light gray.
    green  charging
    red    waiting in a charger line
Charging stations are marked and labelled.

    python experiments/make_screenshots.py --scenario attack --controller TrustAll --at 2.0
(on a machine without a display, run it under xvfb-run)
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "sim"))
import etaxi_env  # noqa: E402
import traci  # noqa: E402

COLORS = {"to_pickup": (30, 120, 230, 255), "to_dropoff": (30, 120, 230, 255), "idle": (60, 60, 60, 255),
          "to_charger": (245, 130, 0, 255), "charging": (20, 175, 120, 255), "queued": (230, 50, 40, 255),
          "verifying": (150, 80, 210, 255), "dead": (0, 0, 0, 255)}
SETTINGS = os.path.join(ROOT, "sim", "gui_settings.xml")


def write_settings():
    with open(SETTINGS, "w") as f:
        f.write("""<viewsettings>
  <scheme name="report">
    <background backgroundColor="white" showGrid="0"/>
    <edges laneEdgeMode="0" laneShowBorders="0" showLinkDecals="0" showRails="0" hideConnectors="1"
           widthExaggeration="1.2" streetName_show="0">
      <colorScheme name="uniform"><entry color="200,200,200"/></colorScheme>
    </edges>
    <vehicles vehicleMode="0" vehicleQuality="2" vehicle_minSize="1" vehicle_exaggeration="%EXAG%"
              showBlinker="0" vehicle_constantSize="1">
      <colorScheme name="given vehicle/type/route color"/>
    </vehicles>
    <pois poiName_show="1" poiName_size="%FONT%" poiName_color="0,0,0" poi_exaggeration="1"/>
    <junctions junctionMode="0" drawShape="0" drawCrossingsAndWalkingareas="0" junction_exaggeration="0.5"/>
  </scheme>
</viewsettings>""")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="attack")
    ap.add_argument("--controller", default="TrustAll")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--at", type=float, nargs="+", default=[2.0], help="hours at which to take shots")
    ap.add_argument("--views", nargs="+", default=["overview", "target"])
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "figures", "sumo"))
    a, rest = ap.parse_known_args()
    os.makedirs(a.out, exist_ok=True)
    env_args = etaxi_env.parse(["--scenario", a.scenario, "--controller", a.controller, "--seed", str(a.seed),
                                "--hours", str(max(a.at) + 0.02), "--gui",
                                "--out", os.path.join(ROOT, "results", "screenshot_runs")] + rest)
    env = etaxi_env.Env(env_args)
    shot_times = {int(h * 3600) for h in a.at}
    xs = [p[0] for p in env.center.values()]
    ys = [p[1] for p in env.center.values()]
    overview = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
    target = env.st[etaxi_env.TARGET]["xy"]
    state = {"started": False, "pending": None}

    def hook(e, now):
        if not state["started"]:
            for name, s in e.st.items():
                x, y = s["xy"]
                traci.poi.add(name, x, y + 25, (40, 40, 40, 255), "charging station", 102, width=30, height=30)
            traci.gui.setSchema("View #0", "report")
            traci.vehicletype.setColor("DEFAULT_VEHTYPE", (215, 215, 215, 255))
            state["started"] = True
        if now % 5 == 0:
            for vid, t in e.taxis.items():
                try:
                    traci.vehicle.setColor(vid, COLORS.get(t["state"], (0, 0, 0, 255)))
                except traci.TraCIException:
                    pass
        if state["pending"] is not None:
            # the screenshot is written after the view has been redrawn for this step
            state["pending"] = None
        if now in shot_times:
            for view in a.views:
                if view == "overview":
                    traci.gui.setOffset("View #0", *overview)
                    traci.gui.setZoom("View #0", 130)
                else:
                    traci.gui.setOffset("View #0", target[0] - 20, target[1] - 25)
                    traci.gui.setZoom("View #0", 2600)
                name = f"{a.scenario}_{a.controller}_{view}_h{now / 3600:.1f}.png"
                traci.gui.screenshot("View #0", os.path.join(a.out, name))
                traci.simulationStep()     # screenshots are taken when the next step is drawn
                print("saved", name, flush=True)

    env.step_hook = hook
    env.stagger_queue = True
    print(env.run())


if __name__ == "__main__":
    font, exag = 90, 1.6
    write_settings()
    s = open(SETTINGS).read().replace("%EXAG%", str(exag)).replace("%FONT%", str(font))
    open(SETTINGS, "w").write(s)
    main()
