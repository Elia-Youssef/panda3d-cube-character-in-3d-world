"""Cube Character in a 3D World - the static world.

Builds everything the player moves around in: the lit ground plane (visible slab
plus an infinite collision plane so the player can never fall through), the plain
sky box, and the green obstacle cubes (each a visible box plus a collision box the
player is blocked by and can stand on). All geometry comes from geometry.make_box;
all sizes, colours and positions come from config.
"""

from panda3d.core import (
    CollisionNode, CollisionPlane, CollisionBox, Plane, Vec3, Point3,
)

import config
import geometry


class World:
    """The ground, sky, lighting and obstacle cubes (the non-player scene)."""

    def __init__(self, render):
        self.root = render.attachNewNode("world")

        # Sky and lights first so the rest of the scene is lit and framed.
        self.sky = geometry.build_sky(render)
        self.ambient_np, self.sun_np = geometry.setup_lighting(render)

        self._build_ground()
        self.obstacles = []
        self._build_obstacles()

    # -- ground ----------------------------------------------------------------
    def _build_ground(self):
        """A wide visible ground slab whose top sits at Z = GROUND_TOP_Z, plus an
        infinite collision plane at that height so the player always has a floor."""
        half = (config.GROUND_HALF, config.GROUND_HALF, config.GROUND_THICK / 2.0)
        top_center_z = config.GROUND_TOP_Z - config.GROUND_THICK / 2.0
        self.ground = geometry.make_box(
            self.root, "ground", half, (0, 0, top_center_z), config.GROUND_COLOR)

        plane = CollisionPlane(Plane(Vec3(0, 0, 1), Point3(0, 0, config.GROUND_TOP_Z)))
        cnode = CollisionNode("ground_collision")
        cnode.addSolid(plane)
        # Ground is a floor only: the downward ray detects it, the wall pusher ignores it.
        cnode.setIntoCollideMask(config.MASK_GROUND)
        self.ground_collision = self.root.attachNewNode(cnode)

    # -- obstacles -------------------------------------------------------------
    def _build_obstacles(self):
        """Place the green obstacle cubes from config. Each carries a collision box
        on both the obstacle mask (a wall the pusher blocks) and the ground mask
        (its top is a surface the player can land on)."""
        h = config.OBSTACLE_HALF
        center_z = config.GROUND_TOP_Z + h
        for index, (x, y) in enumerate(config.OBSTACLE_POSITIONS):
            holder = self.root.attachNewNode("obstacle_{}".format(index))
            holder.setPos(x, y, center_z)
            geometry.make_box(holder, "obstacle_box_{}".format(index),
                              (h, h, h), (0, 0, 0), config.OBSTACLE_COLOR)

            cnode = CollisionNode("obstacle_collision_{}".format(index))
            cnode.addSolid(CollisionBox(Point3(0, 0, 0), h, h, h))
            cnode.setIntoCollideMask(config.MASK_OBSTACLE | config.MASK_GROUND)
            holder.attachNewNode(cnode)
            self.obstacles.append(holder)
