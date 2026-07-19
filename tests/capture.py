"""Capture a fresh screenshot set for a reviewed visual check.

Drives the real app through Panda3D input events and saves six gameplay states in
a new, caller-selected directory. The directory must not already exist,
which protects retained evidence from accidental overwrites.

Run from the repository root:
    python -B tests/capture.py --output-dir tests/_screens/<new-name>
"""

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PROJECT)

from panda3d.core import loadPrcFileData, Filename, ClockObject, Point3
from direct.showbase.MessengerGlobal import messenger
loadPrcFileData("", "window-type offscreen")
loadPrcFileData("", "audio-library-name null")
loadPrcFileData("", "clock-mode non-real-time")

import config
import main


def run(output_dir):
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir)

    app = main.CubeWorldApp()
    clock = ClockObject.getGlobalClock()
    clock.setDt(1.0 / 60.0)
    shots = []

    def steps(n):
        for _ in range(n):
            app.taskMgr.step()

    def grab(name):
        steps(2)
        path = os.path.join(output_dir, name)
        saved = app.win.saveScreenshot(Filename.fromOsSpecific(path))
        if not saved or not os.path.isfile(path) or os.path.getsize(path) == 0:
            raise RuntimeError("Screenshot was not written: " + path)
        shots.append(name)

    # Opening view: yellow player, four green obstacles, ground, sky and HUD.
    app.reset()
    steps(4)
    grab("initial.png")

    # Active movement while the chase camera follows.
    app.reset()
    messenger.send("w")
    messenger.send("d")
    steps(24)
    messenger.send("w-up")
    messenger.send("d-up")
    grab("active.png")

    # Jump from the open start area so the player silhouette remains unobstructed.
    app.reset()
    messenger.send("space")
    steps(12)
    grab("jump.png")

    # Verified collision contact against the south face of obstacle zero.
    ox, oy = config.OBSTACLE_POSITIONS[0]
    app.reset()
    app.player.node.setPos(ox, oy - 4.0, config.PLAYER_START[2])
    messenger.send("w")
    steps(120)
    messenger.send("w-up")
    contact_y = oy - config.OBSTACLE_HALF - config.PLAYER_SPHERE_RADIUS
    if abs(app.player.node.getY() - contact_y) > 0.08:
        raise AssertionError("Player did not reach verified obstacle contact")
    grab("obstacle-contact.png")

    # World-edge confinement under sustained diagonal input.
    app.reset()
    limit = config.GROUND_HALF - config.PLAYER_HALF
    app.player.node.setPos(limit - 2.0, limit - 2.0, config.PLAYER_START[2])
    messenger.send("w")
    messenger.send("d")
    steps(120)
    messenger.send("w-up")
    messenger.send("d-up")
    if abs(app.player.node.getX() - limit) > 0.01 or abs(app.player.node.getY() - limit) > 0.01:
        raise AssertionError("Player did not stop at the visible world boundary")
    grab("boundary.png")

    # Reset through its bound event after active movement.
    messenger.send("a")
    steps(20)
    messenger.send("r")
    steps(2)
    if (app.player.node.getPos() - Point3(*config.PLAYER_START)).length() > 1e-6:
        raise AssertionError("Reset screenshot state is not at the start position")
    grab("reset.png")

    app.destroy()
    print("Saved screenshots to {}: {}".format(output_dir, ", ".join(shots)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True,
                        help="New directory for the reviewed PNG set")
    args = parser.parse_args()
    run(args.output_dir)
