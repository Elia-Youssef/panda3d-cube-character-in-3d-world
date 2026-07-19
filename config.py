"""Cube Character in a 3D World - tunable constants.

Every value the rest of the project depends on lives here as a named constant, so
the world layout, the movement feel, the camera and the colours can all be tuned
in one place without touching the gameplay logic. No engine objects are created in
this module; it only holds plain numbers, tuples and collision bit masks.

Colours are (r, g, b, a) with each channel in 0..1. Panda3D is Z-up: +Z is up,
+Y points into the scene (away from the chase camera) and +X points to the right.
"""

from panda3d.core import BitMask32

# -- Window -------------------------------------------------------------------
WINDOW_TITLE = "Cube Character in a 3D World"
WIN_SIZE = (1280, 720)

# -- Palette (all solid colours; no textures) ---------------------------------
SKY_COLOR = (0.53, 0.74, 0.96, 1.0)      # plain blue sky
GROUND_COLOR = (0.46, 0.41, 0.34, 1.0)   # earthy ground, distinct from player / obstacles
PLAYER_COLOR = (1.0, 0.85, 0.10, 1.0)    # yellow player cube
OBSTACLE_COLOR = (0.16, 0.70, 0.24, 1.0) # green obstacle cubes

# -- Lighting -----------------------------------------------------------------
AMBIENT_COLOR = (0.45, 0.46, 0.50, 1.0)        # soft fill so shadowed faces are not black
SUN_COLOR = (0.85, 0.83, 0.74, 1.0)            # the directional "sun"
SUN_HPR = (-35.0, -55.0, 0.0)                  # heading / pitch / roll of the sun light

# -- Ground plane -------------------------------------------------------------
GROUND_HALF = 120.0      # half-width of the visible ground square (X and Y); large
                         # enough that the player cannot walk off the visible slab
GROUND_THICK = 0.5       # thickness of the ground slab; its top sits at Z = 0
GROUND_TOP_Z = 0.0       # world height of the walkable ground surface

# -- Sky box ------------------------------------------------------------------
SKY_HALF = 300.0         # half-extent of the surrounding sky box

# -- Player cube --------------------------------------------------------------
PLAYER_HALF = 0.5                 # half-size of the player cube (a 1 x 1 x 1 cube)
PLAYER_START = (0.0, 0.0, GROUND_TOP_Z + PLAYER_HALF)  # rests on the ground at the origin
PLAYER_SPHERE_RADIUS = 0.5        # wall-collision sphere radius (fits the cube)

# -- Movement (velocity based, with acceleration) -----------------------------
MOVE_SPEED = 9.0         # top horizontal speed in units / second
ACCEL = 7.0              # how quickly velocity eases toward the target (per second)
DECEL = 9.0              # how quickly velocity eases back to zero on release (per second)

# -- Gravity + jump -----------------------------------------------------------
GRAVITY = -26.0          # downward acceleration in units / second^2
JUMP_SPEED = 10.0        # upward velocity applied at the moment of a jump
LAND_TOLERANCE = 0.05    # how close to a surface counts as landing on it
PHYSICS_STEP = 1.0 / 60.0  # maximum simulation slice; prevents low-FPS tunneling
MAX_FRAME_DT = 0.25        # bound catch-up after a long pause or debugger stop
RAY_ORIGIN_HEIGHT = 6.0  # the floor ray starts this far above the player centre, so a
                         # fast fall cannot drop the ray origin below the ground

# -- Third-person chase camera ------------------------------------------------
# A fairly low, gently angled chase view: high enough to see over the obstacles,
# low enough that the horizon (and the sky above it) stays in frame.
CAM_BACK = 13.0          # how far behind the player (along -Y) the camera sits
CAM_HEIGHT = 4.5         # how far above the player the camera sits
CAM_LOOK_UP = 1.5        # the camera aims at this height above the player's base
CAM_SMOOTH = 6.0         # follow smoothing (higher = snappier, lower = laggier)
CAM_FOV = 60.0
CAM_NEAR = 0.1
CAM_FAR = 800.0          # far enough to contain the sky box

# -- Obstacle cubes (>= 3 required; four placed around the start) --------------
OBSTACLE_HALF = 1.0      # half-size of each obstacle cube (a 2 x 2 x 2 cube)
# (x, y) ground positions; each cube rests on the ground (its centre Z is derived).
OBSTACLE_POSITIONS = (
    (5.0, 7.0),
    (-6.0, 9.0),
    (7.0, -3.0),
    (-5.0, -6.0),
)

# -- Collision bit masks ------------------------------------------------------
# Two separate channels so walls (horizontal pusher) never fight the floor (ray):
MASK_GROUND = BitMask32.bit(0)    # surfaces the player can stand on (ground + obstacle tops)
MASK_OBSTACLE = BitMask32.bit(1)  # solid sides the player is pushed out of (obstacles)
