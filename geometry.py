"""Cube Character in a 3D World - procedural building blocks.

Every visible object is a solid-coloured box built here in code, so the project
loads no external models, textures, audio or fonts. `make_box` constructs a cube
with correct per-face normals so the directional light shades it properly; the sky
and the lighting / camera setup are thin helpers on top.

Panda3D is Z-up. A box is built centred on the origin and then positioned by the
caller, so the same geometry serves the player, the obstacles, the ground slab and
the surrounding sky box.
"""

from panda3d.core import (
    GeomVertexFormat, GeomVertexData, GeomVertexWriter, Geom, GeomTriangles,
    GeomNode, AmbientLight, DirectionalLight, Vec4,
)

import config

# The six faces of a cube, each as (normal, u_axis, v_axis) with u x v = normal so
# the four generated corners wind counter-clockwise seen from outside (front-facing).
_FACES = (
    ((1, 0, 0), (0, 1, 0), (0, 0, 1)),    # +X
    ((-1, 0, 0), (0, 0, 1), (0, 1, 0)),   # -X
    ((0, 1, 0), (0, 0, 1), (1, 0, 0)),    # +Y
    ((0, -1, 0), (1, 0, 0), (0, 0, 1)),   # -Y
    ((0, 0, 1), (1, 0, 0), (0, 1, 0)),    # +Z
    ((0, 0, -1), (0, 1, 0), (1, 0, 0)),   # -Z
)


def _axis_half(axis, half):
    """The half-extent of the box along a unit axis vector (X/Y/Z pick-out)."""
    return half[0] * abs(axis[0]) + half[1] * abs(axis[1]) + half[2] * abs(axis[2])


def make_box(parent, name, half, pos, color, light_off=False, two_sided=False):
    """Build a solid-coloured box of half-extents `half` centred at `pos`.

    `half` is (hx, hy, hz); the box spans pos +/- half on each axis. Per-face
    normals are baked in so lighting shades each face; the colour is written as a
    vertex colour. Returns the box NodePath.
    """
    fmt = GeomVertexFormat.getV3n3c4()
    vdata = GeomVertexData(name, fmt, Geom.UHStatic)
    vdata.setNumRows(24)
    vwriter = GeomVertexWriter(vdata, "vertex")
    nwriter = GeomVertexWriter(vdata, "normal")
    cwriter = GeomVertexWriter(vdata, "color")

    tris = GeomTriangles(Geom.UHStatic)
    base = 0
    for normal, u, v in _FACES:
        hn = _axis_half(normal, half)
        hu = _axis_half(u, half)
        hv = _axis_half(v, half)
        # push the face out along its normal, then walk the four corners CCW from
        # outside: -u-v, +u-v, +u+v, -u+v (so the six faces enclose the cube).
        for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            x = normal[0] * hn + u[0] * hu * su + v[0] * hv * sv
            y = normal[1] * hn + u[1] * hu * su + v[1] * hv * sv
            z = normal[2] * hn + u[2] * hu * su + v[2] * hv * sv
            vwriter.addData3(x, y, z)
            nwriter.addData3(normal[0], normal[1], normal[2])
            cwriter.addData4(color[0], color[1], color[2], color[3])
        tris.addVertices(base + 0, base + 1, base + 2)
        tris.addVertices(base + 0, base + 2, base + 3)
        base += 4

    geom = Geom(vdata)
    geom.addPrimitive(tris)
    gnode = GeomNode(name)
    gnode.addGeom(geom)

    box = parent.attachNewNode(gnode)
    box.setPos(pos[0], pos[1], pos[2])
    if two_sided:
        box.setTwoSided(True)
    if light_off:
        box.setLightOff()
    return box


def build_sky(render):
    """A large box around the whole scene, flat-shaded in the sky colour.

    It is unlit (so it reads as an even sky), two-sided (the camera sits inside
    it), and drawn in the background bin without writing depth so the world always
    renders in front of it. Returns the sky NodePath.
    """
    half = (config.SKY_HALF, config.SKY_HALF, config.SKY_HALF)
    sky = make_box(render, "sky", half, (0, 0, 0), config.SKY_COLOR,
                   light_off=True, two_sided=True)
    sky.setBin("background", 0)
    sky.setDepthWrite(False)
    return sky


def setup_lighting(render):
    """Attach soft ambient fill plus one directional 'sun' so the world is well lit.

    Returns (ambient_np, sun_np) so the caller could tweak them later.
    """
    ambient = AmbientLight("ambient")
    ambient.setColor(Vec4(*config.AMBIENT_COLOR))
    ambient_np = render.attachNewNode(ambient)
    render.setLight(ambient_np)

    sun = DirectionalLight("sun")
    sun.setColor(Vec4(*config.SUN_COLOR))
    sun_np = render.attachNewNode(sun)
    sun_np.setHpr(*config.SUN_HPR)
    render.setLight(sun_np)
    return ambient_np, sun_np


def setup_camera(app):
    """Disable the default mouse camera and set the lens; the per-frame follow in
    main.py positions the camera behind and above the player each update."""
    app.disableMouse()
    app.camLens.setFov(config.CAM_FOV)
    app.camLens.setNear(config.CAM_NEAR)
    app.camLens.setFar(config.CAM_FAR)
