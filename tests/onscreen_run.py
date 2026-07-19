"""Real-window probe using the same application and window configuration as main.py.

Opens an actual 1280x720 render window like a human launch, drives a short scripted
session (move and jump), renders a couple of seconds of frames, then quits cleanly.
Confirms the windowed launch path, rendering and shutdown raise no traceback.

Run:  python tests/onscreen_run.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PROJECT)

import main
from direct.showbase.MessengerGlobal import messenger


def run():
    app = main.CubeWorldApp()
    start = app.player.node.getPos()
    state = {"started": False, "jumped": False, "released": False,
             "peak_z": start.getZ()}

    def driver(task):
        # Drive the real event bindings in a visible window. Use elapsed time rather
        # than frame counts because an uncapped render loop can run very quickly.
        if not state["started"]:
            messenger.send("w")
            messenger.send("d")
            state["started"] = True
        if task.time >= 0.5 and not state["jumped"]:
            messenger.send("space")
            state["jumped"] = True
        if task.time >= 1.5 and not state["released"]:
            messenger.send("w-up")
            messenger.send("d-up")
            state["released"] = True
        state["peak_z"] = max(state["peak_z"], app.player.node.getZ())
        if task.time >= 3.0:
            displacement = app.player.node.getPos() - start
            assert displacement.getX() > 1.0 and displacement.getY() > 1.0
            assert state["peak_z"] > start.getZ() + 0.8
            assert app.player.grounded
            assert not app.keys["w"] and not app.keys["d"]
            # Print before userExit, which raises SystemExit and does not return.
            print("onscreen_run OK: real window, bound input events, jump, landing and clean exit")
            app.userExit()
        return task.cont

    app.taskMgr.add(driver, "onscreen-driver")
    app.run()


if __name__ == "__main__":
    run()
