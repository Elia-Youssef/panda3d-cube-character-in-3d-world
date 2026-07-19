"""Static source checks for project structure and code quality (no window).

Reads the project's source as text and confirms its structural conventions:

  * only constructed geometry + solid colours (no external model/texture/audio/font)
  * all tunables live as named constants in config.py (no magic numbers in logic)
  * movement and gravity scale by the frame delta time (frame-rate independence)
  * exactly one per-frame update task, added in __init__ and never in reset
  * the controls are bound (W/A/S/D held, Space jump, R reset, Esc quit)
  * the two collision channels are wired (horizontal pusher + floor ray)
  * house style: no em dashes or hidden characters

Run:  python tests/test_static.py     Exit 0 = all passed.
"""

import ast
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, ".."))

MODULES = ("config.py", "geometry.py", "world.py", "player.py", "main.py")
SRC = {}
for name in MODULES:
    with open(os.path.join(PROJECT, name), "r", encoding="utf-8") as fh:
        SRC[name] = fh.read()
ALL = "\n".join(SRC.values())

AUTHORED_FILES = MODULES + ("Config.prc", "requirements.txt", "README.md", ".gitignore")
AUTHORED = {}
for name in AUTHORED_FILES:
    with open(os.path.join(PROJECT, name), "r", encoding="utf-8") as fh:
        AUTHORED[name] = fh.read()
AUTHORED_TEXT = "\n".join(AUTHORED.values())

RESULTS = []


def check(label, ok, detail=""):
    RESULTS.append(bool(ok))
    print(("PASS" if ok else "FAIL") + "  " + label + (("   [" + detail + "]") if detail else ""))


# -- asset-free: no external model/texture/audio/font loads --------------------
banned = [r"loadModel\s*\(", r"loadTexture\s*\(", r"loadSfx\s*\(",
          r"loadMusic\s*\(", r"loadFont\s*\(", r"\.egg", r"\.bam",
          r"\.png", r"\.jpg", r"\.wav", r"\.ogg", r"\.ttf"]
hits = [b for b in banned if re.search(b, ALL)]
check("No external asset loads (models/textures/audio/fonts)", not hits,
      "found: " + ", ".join(hits) if hits else "none")
check("Geometry is built procedurally (GeomVertexData in geometry.py)",
      "GeomVertexData" in SRC["geometry.py"])
check("Per-face normals are written (lit geometry)",
      'GeomVertexWriter(vdata, "normal")' in SRC["geometry.py"])

# -- house style: no em dashes / hidden characters -----------------------------
banned_codepoints = {
    "\u2014": "em dash",
    "\u200b": "zero-width space",
    "\u00a0": "non-breaking space",
    "\u00ad": "soft hyphen",
    "\ufeff": "byte-order mark",
    "\u200d": "zero-width joiner",
}
bad_chars = [label for char, label in banned_codepoints.items() if char in AUTHORED_TEXT]
check("No em dashes or hidden characters in public project text", not bad_chars,
      "found: " + ", ".join(bad_chars) if bad_chars else "none")

# -- named constants in config.py (no magic numbers in the logic) --------------
required_consts = (
    "WINDOW_TITLE", "SKY_COLOR", "GROUND_COLOR", "PLAYER_COLOR", "OBSTACLE_COLOR",
    "AMBIENT_COLOR", "SUN_COLOR", "GROUND_HALF", "GROUND_TOP_Z", "SKY_HALF",
    "PLAYER_HALF", "PLAYER_START", "PLAYER_SPHERE_RADIUS", "MOVE_SPEED", "ACCEL",
    "DECEL", "GRAVITY", "JUMP_SPEED", "PHYSICS_STEP", "MAX_FRAME_DT",
    "RAY_ORIGIN_HEIGHT", "CAM_BACK", "CAM_HEIGHT", "CAM_SMOOTH", "OBSTACLE_HALF",
    "OBSTACLE_POSITIONS", "MASK_GROUND", "MASK_OBSTACLE",
)
for const in required_consts:
    check("config defines {}".format(const),
          re.search(r"^" + const + r"\s*=", SRC["config.py"], re.M) is not None)

# Evaluate only the named obstacle tuple, rather than counting unrelated pairs.
config_tree = ast.parse(SRC["config.py"], filename="config.py")
positions = ()
for statement in config_tree.body:
    if (isinstance(statement, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "OBSTACLE_POSITIONS"
                    for target in statement.targets)):
        positions = ast.literal_eval(statement.value)
        break
check("OBSTACLE_POSITIONS lists at least 3 cubes", len(positions) >= 3,
      "{} obstacle positions found".format(len(positions)))

# -- colours are the right hues ------------------------------------------------
def rgba(name):
    m = re.search(name + r"\s*=\s*\(([^)]*)\)", SRC["config.py"])
    return [float(x) for x in m.group(1).split(",")] if m else None

pc = rgba("PLAYER_COLOR")
oc = rgba("OBSTACLE_COLOR")
check("PLAYER_COLOR reads as yellow (high R+G, low B)",
      pc is not None and pc[0] > 0.6 and pc[1] > 0.6 and pc[2] < 0.4, str(pc))
check("OBSTACLE_COLOR reads as green (G dominant)",
      oc is not None and oc[1] > 0.5 and oc[0] < oc[1] and oc[2] < oc[1], str(oc))

# -- delta-time movement and gravity -------------------------------------------
check("main reads the global clock delta (getDt)", "getDt()" in SRC["main.py"])
check("player integrates movement by dt (vx * dt)",
      re.search(r"self\.vx\s*\*\s*dt", SRC["player.py"]) is not None)
check("gravity scales by dt (GRAVITY * dt)",
      re.search(r"GRAVITY\s*\*\s*dt", SRC["player.py"]) is not None)
check("Frame time is consumed through bounded physics substeps",
      "PHYSICS_STEP" in SRC["main.py"] and "while remaining > 0.0" in SRC["main.py"])
check("Extreme catch-up is bounded (MAX_FRAME_DT)", "MAX_FRAME_DT" in SRC["main.py"])

# -- single update task, added in __init__, not in reset -----------------------
adds = len(re.findall(r"taskMgr\.add\(", ALL))
check("Exactly one taskMgr.add in the whole project", adds == 1, "{} add(s)".format(adds))
init_pos = SRC["main.py"].find("def __init__")
reset_pos = SRC["main.py"].find("def reset")
add_pos = SRC["main.py"].find("taskMgr.add(")
check("taskMgr.add is in __init__, before def reset",
      0 < init_pos < add_pos < reset_pos)

# -- input bindings ------------------------------------------------------------
check("Space is bound to the jump",
      re.search(r'accept\(\s*["\']space["\']\s*,\s*self\.player\.jump', SRC["main.py"]) is not None)
check("R is bound to the reset",
      re.search(r'accept\(\s*["\']r["\']\s*,\s*self\.reset', SRC["main.py"]) is not None)
check("Escape has a clean quit path",
      "self.userExit" in SRC["main.py"])
check("main.py has a protected entry point",
      re.search(r'^if __name__ == ["\']__main__["\']:', SRC["main.py"], re.M) is not None)
for key in ("w", "a", "s", "d"):
    check("Movement key '{}' is bound (hold + release)".format(key),
          ('"' + key + '"' in SRC["main.py"] or "'" + key + "'" in SRC["main.py"]))

# -- collision wiring ----------------------------------------------------------
check("Pusher pushes horizontally only (setHorizontal(True))",
      "setHorizontal(True)" in SRC["player.py"])
check("Player has a wall sphere and a floor ray",
      "CollisionSphere" in SRC["player.py"] and "CollisionRay" in SRC["player.py"])
check("Ground has an infinite collision plane",
      "CollisionPlane" in SRC["world.py"])
check("Obstacles have collision boxes",
      "CollisionBox" in SRC["world.py"])
check("Jump is gated on being grounded",
      re.search(r"if\s+self\.grounded", SRC["player.py"]) is not None)
check("Floor ray starts above the player (RAY_ORIGIN_HEIGHT)",
      "RAY_ORIGIN_HEIGHT" in SRC["player.py"])
check("resolve_floor has a hard ground backstop (cannot end below ground)",
      "ground_rest_z" in SRC["player.py"])
gh = re.search(r"GROUND_HALF\s*=\s*([\d.]+)", SRC["config.py"])
check("Visible ground is large enough to not walk off (GROUND_HALF >= 100)",
      gh is not None and float(gh.group(1)) >= 100.0,
      "GROUND_HALF={}".format(gh.group(1) if gh else "?"))
check("Player is confined to the visible ground (confine_to_bounds defined + called)",
      "def confine_to_bounds" in SRC["player.py"]
      and "confine_to_bounds()" in SRC["main.py"])

# -- no unused imports left behind ---------------------------------------------
check("No unused Vec3 import in geometry.py",
      ("Vec3" not in SRC["geometry.py"]) or
      (len(re.findall(r"\bVec3\b", SRC["geometry.py"])) > 1))
check("No unused Vec4 import in main.py",
      ("Vec4" not in SRC["main.py"]) or
      (len(re.findall(r"\bVec4\b", SRC["main.py"])) > 1))

# -- comments / docstrings ------------------------------------------------------
for name in MODULES:
    check("{} opens with a docstring".format(name), SRC[name].lstrip().startswith('"""'))
comment_lines = sum(1 for line in ALL.splitlines() if line.strip().startswith("#"))
check("Source is well commented (>= 20 comment lines)", comment_lines >= 20,
      "{} comment lines".format(comment_lines))

passed = sum(1 for r in RESULTS if r)
print("\n{} / {} static checks passed".format(passed, len(RESULTS)))
sys.exit(0 if passed == len(RESULTS) else 1)
