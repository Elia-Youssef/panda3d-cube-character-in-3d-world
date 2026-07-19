"""End-to-end logic tests for Cube Character in a 3D World (headless / offscreen).

Builds the real CubeWorldApp in an offscreen window with a fixed delta time, then
exercises the complete movement, physics, collision, camera, and reset behavior:

  * scene wiring: player cube, ground (+ collision), sky, lights, >= 3 obstacle cubes
  * each of W / A / S / D moves the player the correct direction
  * movement accelerates (the first frame moves far less than steady speed)
  * gravity pulls an unsupported player down
  * a jump arcs up and falls back to the ground
  * ground collision: a player dropped from height settles on the ground, never below
  * obstacle collision: driving into an obstacle is blocked (no pass-through)
  * the chase camera follows the player and stays behind + above it
  * movement is frame-rate independent (same distance at 60 vs 30 fps)
  * R is a pure reset: no node / task / HUD growth, player returns to start

Run:  python tests/test_logic.py     Exit 0 = all passed.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PROJECT)

from panda3d.core import loadPrcFileData
loadPrcFileData("", "window-type offscreen")
loadPrcFileData("", "audio-library-name null")
loadPrcFileData("", "clock-mode non-real-time")

from panda3d.core import ClockObject, Point3, GeomVertexReader
from direct.interval.IntervalGlobal import ivalMgr
from direct.showbase.MessengerGlobal import messenger
import config
import main


def cube_corners_present(np, half):
    """True if the box mesh has vertices at all 8 true cube corners (+/- half on
    each axis). Guards against a collapsed mesh (e.g. faces flattened onto the
    centre planes) that still has correct collision and bounds."""
    geom = np.node().getGeom(0)
    reader = GeomVertexReader(geom.getVertexData(), "vertex")
    pts = []
    while not reader.isAtEnd():
        v = reader.getData3()
        pts.append((v.getX(), v.getY(), v.getZ()))
    corners = [(sx * half, sy * half, sz * half)
               for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    for c in corners:
        if not any(abs(c[0] - p[0]) < 1e-3 and abs(c[1] - p[1]) < 1e-3
                   and abs(c[2] - p[2]) < 1e-3 for p in pts):
            return False
    return True

RESULTS = []
FIXED_DT = 1.0 / 60.0


def check(label, ok, detail=""):
    RESULTS.append(bool(ok))
    line = ("PASS" if ok else "FAIL") + "  " + label
    if detail:
        line += "   [" + detail + "]"
    print(line)


def count_nodes(np):
    return 1 + sum(count_nodes(c) for c in np.getChildren())


def set_keys(app, w=False, a=False, s=False, d=False):
    app.keys["w"] = w
    app.keys["a"] = a
    app.keys["s"] = s
    app.keys["d"] = d


def steps(app, n):
    for _ in range(n):
        app.taskMgr.step()


def place(app, x, y, z):
    """Hard-place the player at rest (used to set up a specific scenario)."""
    app.player.node.setPos(x, y, z)
    app.player.vx = app.player.vy = app.player.vz = 0.0


def run():
    app = main.CubeWorldApp()
    clock = ClockObject.getGlobalClock()
    clock.setDt(FIXED_DT)
    steps(app, 2)

    start = Point3(*config.PLAYER_START)

    # ---------------------------------------------------------- A. scene wiring
    check("App is a ShowBase", isinstance(app, main.ShowBase))
    check("Player cube node exists", not app.player.cube.isEmpty())
    check("Player cube mesh is a real solid cube (8 corners present)",
          cube_corners_present(app.player.cube, config.PLAYER_HALF))
    obstacle_box = app.world.obstacles[0].find("**/+GeomNode")
    check("Obstacle cube mesh is a real solid cube (8 corners present)",
          cube_corners_present(obstacle_box, config.OBSTACLE_HALF))
    check("Ground slab exists", not app.world.ground.isEmpty())
    check("Ground has a collision plane node",
          not app.world.ground_collision.isEmpty())
    check("Sky box exists", not app.world.sky.isEmpty())
    check("A directional light is attached",
          len(app.render.findAllMatches("**/+DirectionalLight")) >= 1)
    check("An ambient light is attached",
          len(app.render.findAllMatches("**/+AmbientLight")) >= 1)
    check("At least 3 obstacle cubes exist", len(app.world.obstacles) >= 3,
          "{} obstacles".format(len(app.world.obstacles)))
    obstacles_have_collision = all(
        not o.find("**/+CollisionNode").isEmpty() for o in app.world.obstacles)
    check("Every obstacle has a collision solid", obstacles_have_collision)
    check("Player starts resting on the ground (feet at ground top)",
          abs((app.player.node.getZ() - config.PLAYER_HALF) - config.GROUND_TOP_Z) < 1e-6
          and app.player.grounded)

    # --------------------------------------------------- B. directional movement
    def move_displacement(w=False, a=False, s=False, d=False, frames=30):
        app.reset()
        steps(app, 1)
        p0 = app.player.node.getPos()
        set_keys(app, w=w, a=a, s=s, d=d)
        steps(app, frames)
        set_keys(app)
        return app.player.node.getPos() - p0

    df = move_displacement(w=True)
    check("W moves the player forward (+Y dominant)",
          df.getY() > 1.0 and abs(df.getY()) > abs(df.getX()),
          "d=({:.2f},{:.2f})".format(df.getX(), df.getY()))
    db = move_displacement(s=True)
    check("S moves the player backward (-Y dominant)",
          db.getY() < -1.0 and abs(db.getY()) > abs(db.getX()),
          "d=({:.2f},{:.2f})".format(db.getX(), db.getY()))
    dl = move_displacement(a=True)
    check("A moves the player left (-X dominant)",
          dl.getX() < -1.0 and abs(dl.getX()) > abs(dl.getY()),
          "d=({:.2f},{:.2f})".format(dl.getX(), dl.getY()))
    dr = move_displacement(d=True)
    check("D moves the player right (+X dominant)",
          dr.getX() > 1.0 and abs(dr.getX()) > abs(dr.getY()),
          "d=({:.2f},{:.2f})".format(dr.getX(), dr.getY()))

    # Exercise the actual Panda3D event bindings, not only the internal key dict.
    def event_displacement(key, frames=30):
        app.reset()
        steps(app, 1)
        p0 = app.player.node.getPos()
        messenger.send(key)
        steps(app, frames)
        messenger.send(key + "-up")
        return app.player.node.getPos() - p0

    event_directions = {
        "w": (1, event_displacement("w").getY()),
        "s": (-1, event_displacement("s").getY()),
        "a": (-1, event_displacement("a").getX()),
        "d": (1, event_displacement("d").getX()),
    }
    for key, (sign, displacement) in event_directions.items():
        check("{} press/release events drive movement".format(key.upper()),
              displacement * sign > 1.0, "displacement={:.2f}".format(displacement))

    app.reset()
    steps(app, 2)
    messenger.send("space")
    steps(app, 2)
    check("Space event launches the player upward",
          not app.player.grounded and app.player.vz > 0.0
          and app.player.node.getZ() > config.PLAYER_START[2],
          "z={:.2f} vz={:.2f}".format(app.player.node.getZ(), app.player.vz))

    # ------------------------------------------------- C. acceleration (no snap)
    app.reset()
    set_keys(app, w=True)
    steps(app, 1)
    v_after_1 = app.player.vy
    first_frame_speed = abs(v_after_1)
    steps(app, 40)
    steady_speed = abs(app.player.vy)
    set_keys(app)
    check("Movement accelerates (first frame is well below top speed)",
          first_frame_speed < 0.5 * config.MOVE_SPEED and first_frame_speed > 0.0,
          "v1={:.2f} vmax={:.1f}".format(first_frame_speed, config.MOVE_SPEED))
    check("Movement reaches near top speed when held",
          steady_speed > 0.9 * config.MOVE_SPEED,
          "steady={:.2f} of {:.1f}".format(steady_speed, config.MOVE_SPEED))
    check("Releasing keys decelerates the player toward a stop",
          (lambda: (steps(app, 30) or abs(app.player.vy) < 0.5))(),
          "vy={:.2f}".format(app.player.vy))

    # ------------------------------------------------------------- D. gravity
    app.reset()
    place(app, 0.0, 0.0, 8.0)
    app.player.grounded = False
    set_keys(app)
    z_before = app.player.node.getZ()
    steps(app, 8)
    check("Gravity pulls an unsupported player down",
          app.player.node.getZ() < z_before - 0.2 and app.player.vz < 0.0,
          "dz={:.2f} vz={:.2f}".format(app.player.node.getZ() - z_before, app.player.vz))

    # -------------------------------------------------------------- E. jump arc
    app.reset()
    steps(app, 2)
    base_z = app.player.node.getZ()
    app.player.jump()
    rose = False
    peak = base_z
    for _ in range(180):
        app.taskMgr.step()
        z = app.player.node.getZ()
        peak = max(peak, z)
        if z > base_z + 0.5:
            rose = True
        if rose and app.player.grounded:
            break
    check("A jump arcs up", rose and peak > base_z + 0.8,
          "peak rise {:.2f}".format(peak - base_z))
    check("Gravity returns the player to the ground after the jump",
          app.player.grounded and abs(app.player.node.getZ() - base_z) < 0.05,
          "z={:.3f} base={:.3f}".format(app.player.node.getZ(), base_z))

    # ----------------------------------------- F. ground collision (no fall-through)
    def drop_test(from_z, initial_vz, frames=400):
        app.reset()
        place(app, 0.0, 0.0, from_z)
        app.player.grounded = False
        app.player.vz = initial_vz
        set_keys(app)
        low = 999.0
        for _ in range(frames):
            app.taskMgr.step()
            low = min(low, app.player.node.getZ() - config.PLAYER_HALF)
        return app.player.node.getZ(), low

    # ordinary drop
    rest_z, min_feet = drop_test(12.0, -40.0)
    check("A dropped player settles on the ground (not through it)",
          abs(rest_z - start.getZ()) < 0.05 and app.player.grounded,
          "rest z={:.3f}".format(rest_z))
    check("The player never dips below the ground surface",
          min_feet > config.GROUND_TOP_Z - 0.001, "min feet z={:.4f}".format(min_feet))

    # extreme: a tall free fall and a brutal downward shove must NOT tunnel
    rest_hi, min_hi = drop_test(200.0, 0.0, frames=900)
    check("A tall free fall still lands on the ground (no tunneling)",
          abs(rest_hi - start.getZ()) < 0.05 and min_hi > config.GROUND_TOP_Z - 0.001,
          "rest={:.3f} min feet={:.4f}".format(rest_hi, min_hi))
    rest_sh, min_sh = drop_test(3.0, -200.0)
    check("A brutal downward shove cannot pass through the ground",
          abs(rest_sh - start.getZ()) < 0.05 and min_sh > config.GROUND_TOP_Z - 0.001,
          "rest={:.3f} min feet={:.4f}".format(rest_sh, min_sh))

    # ------------------------------------------ G. obstacle collision (no pass-through)
    ox, oy = config.OBSTACLE_POSITIONS[0]
    app.reset()
    place(app, ox, oy - 7.0, config.PLAYER_START[2])  # line up south of the obstacle
    near_face = oy - config.OBSTACLE_HALF
    set_keys(app, w=True)                              # drive straight at it
    steps(app, 240)
    set_keys(app)
    final_y = app.player.node.getY()
    check("Driving into an obstacle is blocked (player stops before its face)",
          final_y < near_face and final_y > oy - 7.0,
          "y={:.2f} face={:.2f}".format(final_y, near_face))
    check("The player does not tunnel through to the far side of the obstacle",
          final_y < oy, "y={:.2f} obstacle_y={:.2f}".format(final_y, oy))

    # Approach every cube from each axial face. This protects the complete obstacle
    # layout instead of proving only one collision from one direction.
    approach_specs = (
        (0.0, -4.0, {"w": True}, "south"),
        (0.0, 4.0, {"s": True}, "north"),
        (-4.0, 0.0, {"d": True}, "west"),
        (4.0, 0.0, {"a": True}, "east"),
    )
    clearances = []
    for obstacle_index, (ox, oy) in enumerate(config.OBSTACLE_POSITIONS):
        for dx, dy, held, face in approach_specs:
            app.reset()
            place(app, ox + dx, oy + dy, config.PLAYER_START[2])
            set_keys(app, **held)
            steps(app, 120)
            set_keys(app)
            if dx:
                clearance = abs(app.player.node.getX() - ox)
            else:
                clearance = abs(app.player.node.getY() - oy)
            clearances.append((obstacle_index, face, clearance))
    expected_clearance = config.OBSTACLE_HALF + config.PLAYER_SPHERE_RADIUS
    bad_clearances = [(index, face, value) for index, face, value in clearances
                      if value < expected_clearance - 0.02 or value > expected_clearance + 0.08]
    check("All four axial faces of every obstacle block the player",
          not bad_clearances,
          "{} approaches; bad={}".format(len(clearances), bad_clearances))

    # Obstacle tops participate in the floor channel, and stepping off returns the
    # player to the ground instead of leaving it suspended.
    ox, oy = config.OBSTACLE_POSITIONS[0]
    app.reset()
    place(app, ox, oy, 8.0)
    app.player.grounded = False
    steps(app, 180)
    obstacle_rest_z = (config.GROUND_TOP_Z + 2.0 * config.OBSTACLE_HALF
                       + config.PLAYER_HALF)
    check("A player dropped onto an obstacle lands on its top",
          app.player.grounded and abs(app.player.node.getZ() - obstacle_rest_z) < 0.05,
          "z={:.3f} expected={:.3f}".format(app.player.node.getZ(), obstacle_rest_z))
    set_keys(app, d=True)
    steps(app, 120)
    set_keys(app)
    check("Walking off an obstacle top returns the player to the ground",
          app.player.grounded
          and abs(app.player.node.getZ() - config.PLAYER_START[2]) < 0.05,
          "z={:.3f}".format(app.player.node.getZ()))

    # --------------------------------------------------------- H. camera follow
    app.reset()
    cam0 = app.camera.getPos()
    set_keys(app, d=True)        # move right (+X)
    steps(app, 60)
    set_keys(app)
    cam1 = app.camera.getPos()
    p = app.player.node.getPos()
    check("Camera follows the player (tracks +X movement)",
          cam1.getX() > cam0.getX() + 0.5 and cam1.getX() > 0.3,
          "cam x {:.2f} -> {:.2f}".format(cam0.getX(), cam1.getX()))
    check("Camera stays behind the player (-Y) and above it (+Z)",
          cam1.getY() < p.getY() and cam1.getZ() > p.getZ(),
          "cam=({:.1f},{:.1f},{:.1f}) p=({:.1f},{:.1f},{:.1f})".format(
              cam1.getX(), cam1.getY(), cam1.getZ(), p.getX(), p.getY(), p.getZ()))

    # the top of the view must point above the horizon so the sky shows above the land
    import math as _math
    app.reset()
    steps(app, 2)
    forward = app.camera.getQuat(app.render).getForward()
    forward_pitch = _math.asin(max(-1.0, min(1.0, forward.getZ())))
    half_vfov = _math.radians(app.camLens.getFov()[1] / 2.0)
    top_of_view = forward_pitch + half_vfov
    check("Sky is visible above the land (view frustum reaches above the horizon)",
          top_of_view > _math.radians(2.0),
          "top of view = {:.1f} deg".format(_math.degrees(top_of_view)))

    # ----------------------------------------- H2. confined to the visible ground
    limit = config.GROUND_HALF - config.PLAYER_HALF
    app.reset()
    set_keys(app, d=True, w=True)        # drive diagonally toward a corner forever
    steps(app, 1500)
    set_keys(app)
    px = app.player.node.getX()
    py = app.player.node.getY()
    check("Player cannot walk off the visible ground (X stays within the slab)",
          px <= limit + 1e-3, "x={:.2f} limit={:.2f}".format(px, limit))
    check("Player cannot walk off the visible ground (Y stays within the slab)",
          py <= limit + 1e-3, "y={:.2f} limit={:.2f}".format(py, limit))
    check("Player is still grounded at the world boundary",
          app.player.grounded and abs(app.player.node.getZ() - start.getZ()) < 0.05,
          "z={:.3f}".format(app.player.node.getZ()))

    # ------------------------------------------------- I. frame-rate independence
    def distance_over_one_second(fps):
        app.reset()
        clock.setDt(1.0 / fps)
        steps(app, 1)
        y0 = app.player.node.getY()
        set_keys(app, w=True)
        steps(app, fps)          # one simulated second
        set_keys(app)
        d = app.player.node.getY() - y0
        clock.setDt(FIXED_DT)
        return d

    fps_values = (120, 60, 30, 20, 15, 10, 5)
    distances = {fps: distance_over_one_second(fps) for fps in fps_values}
    movement_spread = ((max(distances.values()) - min(distances.values()))
                       / max(distances.values()))
    check("Movement remains stable from 120 down to 5 fps",
          movement_spread < 0.03,
          "{} spread={:.1%}".format(
              ", ".join("{}:{:.2f}".format(fps, distances[fps]) for fps in fps_values),
              movement_spread))

    def airborne_height_after(fps, seconds, jump=False):
        app.reset()
        place(app, 0.0, 0.0, 8.0 if not jump else config.PLAYER_START[2])
        app.player.grounded = jump
        if jump:
            app.player.jump()
        else:
            app.player.grounded = False
        clock.setDt(1.0 / fps)
        steps(app, int(round(seconds * fps)))
        height = app.player.node.getZ()
        clock.setDt(FIXED_DT)
        return height

    fall_heights = {fps: airborne_height_after(fps, 0.4) for fps in fps_values}
    fall_spread = max(fall_heights.values()) - min(fall_heights.values())
    check("Gravity remains stable from 120 down to 5 fps",
          fall_spread < 0.08,
          "{} spread={:.3f}".format(
              ", ".join("{}:{:.2f}".format(fps, fall_heights[fps]) for fps in fps_values),
              fall_spread))

    jump_heights = {fps: airborne_height_after(fps, 0.2, jump=True)
                    for fps in fps_values}
    jump_spread = max(jump_heights.values()) - min(jump_heights.values())
    check("Jump integration remains stable from 120 down to 5 fps",
          jump_spread < 0.08 and min(jump_heights.values()) > config.PLAYER_START[2] + 1.0,
          "{} spread={:.3f}".format(
              ", ".join("{}:{:.2f}".format(fps, jump_heights[fps]) for fps in fps_values),
              jump_spread))

    def obstacle_contact_at_fps(fps):
        app.reset()
        place(app, ox, oy - 4.0, config.PLAYER_START[2])
        clock.setDt(1.0 / fps)
        set_keys(app, w=True)
        steps(app, 2 * fps)
        set_keys(app)
        final = app.player.node.getY()
        clock.setDt(FIXED_DT)
        return final

    collision_positions = {fps: obstacle_contact_at_fps(fps) for fps in (60, 10, 5)}
    collision_spread = max(collision_positions.values()) - min(collision_positions.values())
    check("Obstacle collision remains stable at 60, 10 and 5 fps",
          collision_spread < 0.05 and max(collision_positions.values()) < oy,
          "{} spread={:.3f}".format(collision_positions, collision_spread))

    # -------------------------------------------------------- J. reset purity
    app.reset()
    set_keys(app)
    steps(app, 3)
    nodes_before = count_nodes(app.render)
    a2d_before = count_nodes(app.aspect2d)
    tasks_before = len(app.taskMgr.getAllTasks())
    events_before = tuple(sorted(app.getAllAccepting()))
    colliders_before = app.ctrav.getNumColliders()
    collider_nodes_before = tuple(app.ctrav.getCollider(index)
                                  for index in range(colliders_before))
    handlers_before = tuple(type(app.ctrav.getHandler(collider)).__name__
                            for collider in collider_nodes_before)
    collision_nodes_before = list(app.render.findAllMatches("**/+CollisionNode"))
    solids_before = sum(node.node().getNumSolids() for node in collision_nodes_before)
    intervals_before = ivalMgr.getNumIntervals()
    for _ in range(50):
        app.reset()
        app.taskMgr.step()
    # roam around (including a jump and a fall onto an obstacle) then reset again
    set_keys(app, w=True, d=True)
    steps(app, 40)
    app.player.jump()
    steps(app, 40)
    set_keys(app)
    for _ in range(50):
        app.reset()
        app.taskMgr.step()
    nodes_after = count_nodes(app.render)
    a2d_after = count_nodes(app.aspect2d)
    tasks_after = len(app.taskMgr.getAllTasks())
    events_after = tuple(sorted(app.getAllAccepting()))
    colliders_after = app.ctrav.getNumColliders()
    collider_nodes_after = tuple(app.ctrav.getCollider(index)
                                 for index in range(colliders_after))
    handlers_after = tuple(type(app.ctrav.getHandler(collider)).__name__
                           for collider in collider_nodes_after)
    collision_nodes_after = list(app.render.findAllMatches("**/+CollisionNode"))
    solids_after = sum(node.node().getNumSolids() for node in collision_nodes_after)
    intervals_after = ivalMgr.getNumIntervals()
    check("No render-node growth after repeated resets",
          nodes_after == nodes_before, "{} -> {}".format(nodes_before, nodes_after))
    check("No HUD (aspect2d) growth after repeated resets",
          a2d_after == a2d_before, "{} -> {}".format(a2d_before, a2d_after))
    check("No task growth after repeated resets",
          tasks_after == tasks_before, "{} -> {}".format(tasks_before, tasks_after))
    check("No accepted-event growth after repeated resets",
          events_after == events_before,
          "{} -> {}".format(len(events_before), len(events_after)))
    check("No collision-collider or handler growth after repeated resets",
          colliders_after == colliders_before and handlers_after == handlers_before,
          "{} -> {} colliders".format(colliders_before, colliders_after))
    check("No collision-node or solid growth after repeated resets",
          len(collision_nodes_after) == len(collision_nodes_before)
          and solids_after == solids_before,
          "nodes {} -> {}; solids {} -> {}".format(
              len(collision_nodes_before), len(collision_nodes_after),
              solids_before, solids_after))
    check("No interval growth after repeated resets",
          intervals_after == intervals_before,
          "{} -> {}".format(intervals_before, intervals_after))
    app.reset()
    check("Reset returns the player to the exact start position",
          (app.player.node.getPos() - start).length() < 1e-6)
    check("Reset releases every held movement input", not any(app.keys.values()))

    passed = sum(1 for r in RESULTS if r)
    total = len(RESULTS)
    print("\n{} / {} checks passed".format(passed, total))
    app.destroy()
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(run())
