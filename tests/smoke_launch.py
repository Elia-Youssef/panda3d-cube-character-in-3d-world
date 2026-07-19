"""Minimal offscreen launch probe: construct the app and step a few frames.

Confirms the project imports and builds with no traceback under a headless buffer
(the cheapest possible "does it start" check). Run:  python tests/smoke_launch.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PROJECT)

from panda3d.core import loadPrcFileData, ClockObject
loadPrcFileData("", "window-type offscreen")
loadPrcFileData("", "audio-library-name null")
loadPrcFileData("", "clock-mode non-real-time")

import main


def run():
    app = main.CubeWorldApp()
    ClockObject.getGlobalClock().setDt(1.0 / 60.0)
    for _ in range(10):
        app.taskMgr.step()
    app.destroy()
    print("smoke_launch OK: app built, stepped 10 frames and shut down without errors")


if __name__ == "__main__":
    run()
