"""Cube Character in a 3D World - the player.

The yellow cube the user drives. Movement is velocity based with smooth
acceleration (it eases up to speed and coasts to a stop, never snapping). Gravity
constantly pulls the cube down; Space launches a jump that arcs up and falls back.

Collision uses two separated channels (see config's bit masks):
  * a CollisionSphere driven by a horizontal-only CollisionHandlerPusher, so the
    obstacle cubes block the player in X / Y without ever shoving it vertically;
  * a downward CollisionRay read from a CollisionHandlerQueue, which finds the
    nearest surface below (the ground, or an obstacle top) so the player rests on
    it, lands from a jump, and never falls through the world.
"""

import math

from panda3d.core import (
    CollisionNode, CollisionSphere, CollisionRay, CollisionHandlerPusher,
    CollisionHandlerQueue, BitMask32,
)

import config
import geometry


class Player:
    """The yellow cube character: movement, gravity, jumping and collision."""

    def __init__(self, render, traverser):
        self.render = render
        self.node = render.attachNewNode("player")

        # The visible yellow cube, centred on the player node.
        self.cube = geometry.make_box(
            self.node, "player_cube",
            (config.PLAYER_HALF, config.PLAYER_HALF, config.PLAYER_HALF),
            (0, 0, 0), config.PLAYER_COLOR)

        # Wall channel: a sphere pushed out of obstacles, horizontally only.
        sphere = CollisionNode("player_sphere")
        sphere.addSolid(CollisionSphere(0, 0, 0, config.PLAYER_SPHERE_RADIUS))
        sphere.setFromCollideMask(config.MASK_OBSTACLE)
        sphere.setIntoCollideMask(BitMask32.allOff())
        self.sphere_np = self.node.attachNewNode(sphere)

        self.pusher = CollisionHandlerPusher()
        self.pusher.setHorizontal(True)  # obstacles never push the player up or down
        self.pusher.addCollider(self.sphere_np, self.node)
        traverser.addCollider(self.sphere_np, self.pusher)

        # Floor channel: a ray from well above the player straight down to the
        # nearest surface. Starting high (RAY_ORIGIN_HEIGHT) means even a very fast
        # fall cannot drop the ray origin below the ground and miss it.
        ray = CollisionNode("player_ray")
        ray.addSolid(CollisionRay(0, 0, config.RAY_ORIGIN_HEIGHT, 0, 0, -1))
        ray.setFromCollideMask(config.MASK_GROUND)
        ray.setIntoCollideMask(BitMask32.allOff())
        self.ray_np = self.node.attachNewNode(ray)

        self.floor_queue = CollisionHandlerQueue()
        traverser.addCollider(self.ray_np, self.floor_queue)

        # Motion state.
        self.vx = 0.0
        self.vy = 0.0
        self.vz = 0.0
        self.grounded = True
        self.reset()

    # -- state -----------------------------------------------------------------
    def reset(self):
        """Return the player to the start position and clear all motion. Creates
        no new nodes, tasks or handlers (safe to call any number of times)."""
        self.node.setPos(*config.PLAYER_START)
        self.vx = 0.0
        self.vy = 0.0
        self.vz = 0.0
        self.grounded = True

    def jump(self):
        """Launch a jump, but only when standing on a surface (no mid-air jumps)."""
        if self.grounded:
            self.vz = config.JUMP_SPEED
            self.grounded = False

    # -- per-frame -------------------------------------------------------------
    def update(self, dt, keys):
        """Advance horizontal movement (with acceleration) and gravity by dt.

        Collision resolution happens after this, once the traverser has run; see
        resolve_floor. `keys` is a dict of held movement keys (w / a / s / d).
        """
        # Desired direction from held keys, normalised so diagonals are not faster.
        ix = (1.0 if keys.get("d") else 0.0) - (1.0 if keys.get("a") else 0.0)
        iy = (1.0 if keys.get("w") else 0.0) - (1.0 if keys.get("s") else 0.0)
        length = math.hypot(ix, iy)
        if length > 0.0:
            ix /= length
            iy /= length

        target_vx = ix * config.MOVE_SPEED
        target_vy = iy * config.MOVE_SPEED

        # Ease velocity toward the target: accelerate when steering, decelerate when
        # released, so motion ramps smoothly instead of snapping on or off.
        rate = config.ACCEL if length > 0.0 else config.DECEL
        blend = min(1.0, rate * dt)
        self.vx += (target_vx - self.vx) * blend
        self.vy += (target_vy - self.vy) * blend

        # Gravity is a constant downward acceleration, integrated into vz.
        self.vz += config.GRAVITY * dt

        # Integrate position from velocity (frame-rate independent via dt).
        self.node.setPos(
            self.node.getX() + self.vx * dt,
            self.node.getY() + self.vy * dt,
            self.node.getZ() + self.vz * dt,
        )

    def resolve_floor(self):
        """Rest the player on the nearest surface below after the traverser has run.

        The flat ground is always available as a floor (GROUND_TOP_Z); an obstacle
        top detected by the downward ray can raise the floor locally. When the player
        is falling and its feet reach that surface, snap to it, zero vertical velocity
        and mark the player grounded; otherwise it is airborne. A final hard clamp
        guarantees the player can never end a frame below the ground, whatever the
        fall speed.
        """
        # The infinite flat ground is the baseline floor everywhere.
        surface_z = config.GROUND_TOP_Z
        self.floor_queue.sortEntries()
        if self.floor_queue.getNumEntries() > 0:
            nearest = self.floor_queue.getEntry(0).getSurfacePoint(self.render).getZ()
            surface_z = max(surface_z, nearest)

        feet_z = self.node.getZ() - config.PLAYER_HALF
        if self.vz <= 0.0 and feet_z <= surface_z + config.LAND_TOLERANCE:
            self.node.setZ(surface_z + config.PLAYER_HALF)
            self.vz = 0.0
            self.grounded = True
        else:
            self.grounded = False

        # Absolute backstop: never let a frame end with the player below the ground.
        ground_rest_z = config.GROUND_TOP_Z + config.PLAYER_HALF
        if self.node.getZ() < ground_rest_z:
            self.node.setZ(ground_rest_z)
            if self.vz < 0.0:
                self.vz = 0.0
            self.grounded = True

    def confine_to_bounds(self):
        """Keep the player on the visible ground slab via an invisible boundary at
        the slab edge, so it can never walk off into empty space. Outward velocity
        is arrested at the wall so the cube stops cleanly instead of pressing on."""
        limit = config.GROUND_HALF - config.PLAYER_HALF
        x = self.node.getX()
        y = self.node.getY()
        if x > limit:
            x = limit
            self.vx = min(self.vx, 0.0)
        elif x < -limit:
            x = -limit
            self.vx = max(self.vx, 0.0)
        if y > limit:
            y = limit
            self.vy = min(self.vy, 0.0)
        elif y < -limit:
            y = -limit
            self.vy = max(self.vy, 0.0)
        self.node.setX(x)
        self.node.setY(y)
