"""Cube Character in a 3D World - a small third-person template (run: python main.py).

A yellow cube character moves around a lit 3D world with WASD, jumps with Space
under gravity, and is blocked by green obstacle cubes. A third-person camera follows
the cube and an on-screen panel lists the controls. Everything is built from
constructed, solid-coloured geometry: no external models, textures, audio or fonts.

Modules (leaf first): config (constants) -> geometry (boxes, sky, lights, camera)
-> world (ground, sky, obstacles) -> player (the cube + physics) -> main (this file,
which wires them together, runs one update task and follows the player).
"""

import os

from direct.showbase.ShowBase import ShowBase
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import (
    WindowProperties, ClockObject, CollisionTraverser, Filename, Point3,
    TextNode, loadPrcFile, loadPrcFileData,
)

# Load Config.prc from next to this file (cwd-independent) and name the window
# before it opens, so python main.py works from any working directory.
_HERE = os.path.dirname(os.path.abspath(__file__))
_PRC = os.path.join(_HERE, "Config.prc")
if os.path.exists(_PRC):
    loadPrcFile(Filename.fromOsSpecific(_PRC))

import config
import geometry
from world import World
from player import Player

loadPrcFileData("", "window-title " + config.WINDOW_TITLE)


class CubeWorldApp(ShowBase):
    """The application: builds the world and player, follows the chase camera,
    draws the controls overlay, runs one per-frame update task and owns the reset."""

    def __init__(self):
        ShowBase.__init__(self)

        self.clock = ClockObject.getGlobalClock()
        self.setBackgroundColor(*config.SKY_COLOR)  # fallback behind the sky box
        self._setup_window()

        # Per-pixel lighting makes the directional light shade the boxes cleanly.
        self.render.setShaderAuto()
        geometry.setup_camera(self)

        # One traverser, traversed by hand inside the single update task below, keeps
        # simulation order deterministic across interactive and automated runs.
        self.ctrav = CollisionTraverser("cube-world")

        self.world = World(self.render)
        self.player = Player(self.render, self.ctrav)

        self.keys = {"w": False, "a": False, "s": False, "d": False}
        self._bind_input()
        self._build_hud()

        self._snap_camera()  # frame the player on the very first frame

        # The one and only per-frame task; reset never adds another.
        self.taskMgr.add(self.update, "cube-update")

    # -- setup helpers ---------------------------------------------------------
    def _setup_window(self):
        """Title the window, including offscreen runs without requestProperties."""
        if hasattr(self.win, "requestProperties"):
            props = WindowProperties()
            props.setTitle(config.WINDOW_TITLE)
            props.setSize(config.WIN_SIZE[0], config.WIN_SIZE[1])
            self.win.requestProperties(props)

    def _bind_input(self):
        """Hold-to-move keys, plus jump, reset and quit."""
        for key in ("w", "a", "s", "d"):
            self.accept(key, self._set_key, [key, True])
            self.accept(key + "-up", self._set_key, [key, False])
        self.accept("space", self.player.jump)
        self.accept("r", self.reset)
        self.accept("escape", self.userExit)

    def _set_key(self, key, value):
        self.keys[key] = value

    def _build_hud(self):
        """On-screen instructions for the movement and jump controls."""
        text = ("Controls\n"
                "W - forward    S - backward\n"
                "A - left    D - right\n"
                "Space - jump\n"
                "R - reset    Esc - quit")
        self.hud = OnscreenText(
            text=text, parent=self.a2dTopLeft, align=TextNode.ALeft,
            pos=(0.06, -0.10), scale=0.055, fg=(1, 1, 1, 1),
            shadow=(0, 0, 0, 0.6), mayChange=False)

    # -- reset -----------------------------------------------------------------
    def reset(self):
        """Return the player to the start and re-frame the camera. Creates no new
        nodes, tasks or widgets, so it is safe to call repeatedly."""
        for key in self.keys:
            self.keys[key] = False
        self.player.reset()
        self._snap_camera()

    # -- camera ----------------------------------------------------------------
    def _camera_target(self):
        """Where the camera wants to sit: behind (-Y) and above the player."""
        p = self.player.node.getPos()
        return Point3(p.getX(), p.getY() - config.CAM_BACK, p.getZ() + config.CAM_HEIGHT)

    def _look_point(self):
        p = self.player.node.getPos()
        return Point3(p.getX(), p.getY(), p.getZ() + config.CAM_LOOK_UP)

    def _snap_camera(self):
        """Place the camera at its target immediately (no smoothing)."""
        self.camera.setPos(self._camera_target())
        self.camera.lookAt(self._look_point())

    def _follow_camera(self, dt):
        """Ease the camera toward its target each frame so it trails the player."""
        current = self.camera.getPos()
        target = self._camera_target()
        blend = min(1.0, config.CAM_SMOOTH * dt)
        self.camera.setPos(current + (target - current) * blend)
        self.camera.lookAt(self._look_point())

    # -- per-frame -------------------------------------------------------------
    def _physics_step(self, dt):
        """Advance one short simulation slice and resolve every collision channel."""
        self.player.update(dt, self.keys)   # movement + gravity integration
        self.ctrav.traverse(self.render)    # pusher (walls) + floor ray fill
        self.player.resolve_floor()         # rest on the nearest surface below
        self.player.confine_to_bounds()     # keep the player on the visible ground
        self._follow_camera(dt)             # chase camera trails the player

    def step(self, dt):
        """Advance by elapsed time using bounded slices for stable low-FPS physics.

        Every slice is small enough for reliable collision handling, while consuming
        the full frame time keeps movement, gravity and camera motion from slowing at
        low frame rates. Only extreme pauses are capped to avoid a catch-up spiral.
        """
        remaining = max(0.0, min(float(dt), config.MAX_FRAME_DT))
        while remaining > 0.0:
            slice_dt = min(remaining, config.PHYSICS_STEP)
            self._physics_step(slice_dt)
            remaining -= slice_dt

    def update(self, task):
        self.step(self.clock.getDt())
        return task.cont


if __name__ == "__main__":
    CubeWorldApp().run()
