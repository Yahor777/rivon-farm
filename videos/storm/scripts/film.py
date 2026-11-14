"""RIVON: THE STORM - the 600-frame timeline (20 s, 30 fps). Every frame is rendered stateless: frame number ->
base shot + local time t in [0,1] -> camera move, weather parameters, animation of the things that move.
  f   1- 90  wide        sunny terrace, slow push-in
  f  91-150  glass       wine glass, pier and sea behind; the light starts to fade
  f 151-210  s01         gust: the napkin lifts off the table, leaves run over the deck
  f 211-240  storm       the shelf cloud rolls in over the sea
  f 241-270  freeze      the first drop falls towards the wine and stops 4.5 mm above it - time freezes
  f 271-330  macro       frozen time: the corner - post, Trojak, beams slide in
  f 331-420  pergola     rafters, glazing bars, glass; then the warm lights come on
  f 421-470  rain_under  time resumes: downpour outside, dry and warm under the roof
  f 471-510  splash      the one drop that was already under the roof lands in the wine
  f 511-600  final       the rain thins, the sun breaks through onto the pergola; logo + slogan in post
"""
import math, os
import bpy
from mathutils import Vector

SHOTS = [("wide", 1, 90), ("glass", 91, 150), ("s01", 151, 210), ("storm", 211, 240), ("freeze", 241, 270),
         ("macro", 271, 330), ("pergola", 331, 420), ("rain_under", 421, 470), ("splash", 471, 510), ("final", 511, 600)]
FRAME = None; T = 1.0


def shot_of(f):
    for name, a, b in SHOTS:
        if a <= f <= b:
            return name, (f - a) / max(1, b - a)
    raise ValueError(f)


def ease(t):
    t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)


def set_frame(f):
    """returns the base shot; stores FRAME / T and exports the per-frame weather parameters"""
    global FRAME, T
    FRAME = f; shot, T = shot_of(f)
    os.environ["WX_SEED"] = str(1000 + f)                       # new rain every frame (1/50 s exposures are uncorrelated)
    os.environ["SEA_TIME"] = str(f / 30.0)
    if shot == "storm":
        os.environ["CB_X"] = str(7400 - 2700 * ease(T))          # the front arrives
        os.environ["CB_DENS"] = str(0.022 + 0.013 * ease(T))
    if shot == "glass":
        os.environ["HDRI_STRENGTH"] = str(22.3 * (1.0 - 0.35 * ease((T - 0.45) / 0.55)))   # first cloud shadow
    if shot == "s01":
        os.environ["HDRI_STRENGTH"] = str(22.3 * 0.62)
    if shot == "final":
        os.environ["BREAK_SUN"] = str(34.0 * ease(T / 0.55))
        os.environ["RAIN_N"] = str(int(40000 * (1 - 0.85 * ease(T / 0.7))))
    return shot


def lights_on(shot):
    if FRAME is None:
        return shot in ("pergola", "rain_under", "final", "splash")
    return FRAME >= 398


def move_camera(shot):
    """slow, smooth, single-direction moves (no shake) relative to the approved still cameras; t=1 for wide/final is
    the approved still, for the others the still sits at mid-move"""
    if FRAME is None:
        return
    cam = bpy.context.scene.camera; e = ease(T); k = e - {"wide": 1.0, "final": 0.0}.get(shot, 0.5)
    fwd = cam.matrix_world.to_3x3() @ Vector((0, 0, -1)); right = cam.matrix_world.to_3x3() @ Vector((1, 0, 0))
    up = Vector((0, 0, 1))
    mv = {"wide": fwd * 1.6, "glass": right * 0.012 + fwd * 0.015, "s01": right * 0.35, "storm": fwd * 0.5 + up * 0.05,
          "freeze": right * 0.012, "macro": right * 0.16 + up * 0.03, "pergola": up * 0.55 - fwd * 0.9,
          "rain_under": -fwd * 0.35, "splash": fwd * 0.0, "final": -fwd * 1.3 + up * 0.25}[shot]
    cam.location = Vector(cam.location) + mv * k
    if shot in ("macro", "pergola"):                           # keep looking at the subject while moving
        tgt = {"macro": Vector((1.72, -3.02, 2.56)), "pergola": Vector((0.0, 0.2, 1.75))}[shot]
        cam.rotation_euler = (tgt - Vector(cam.location)).to_track_quat("-Z", "Y").to_euler()


def drop_offset(shot):
    """extra height of the hero drop above its frozen position (m)"""
    if FRAME is None or shot != "freeze":
        return 0.0
    u = min(1.0, T / 0.5)                                      # falls for the first half, then hangs
    return 0.022 * (1 - u) ** 2


def splash_u(shot):
    """None = drop still falling (returns via drop height), else crown phase 0..1.6"""
    if FRAME is None:
        return 0.55
    return (T - 0.18) / 0.45


def assemble():
    """Frozen-time assembly, f 271-405. Each part flies in along a short straight path and stops (ease-out); parts whose
    turn has not come are not rendered."""
    if FRAME is None:
        return
    f = FRAME
    def window(name, x, y):
        s = (math.sin(x * 12.9898 + y * 78.233) * 43758.5453) % 1.0      # stable per-part stagger
        if name.startswith(("INST_STOPA",)):            return 262 + 4 * s, 10, Vector((0, 0, 1.2))
        if name.startswith("POST"):                     return 268 + 6 * s, 14, Vector((0, 0, 2.8))
        if name.startswith("INST_TROJAK"):              return 284 + 5 * s, 12, Vector((0, 0, 0.9))
        if name.startswith("BEAM_LONG"):                return 296 + 6 * s, 16, Vector((0, 1.6 if x < 0 else -1.6, 0.25))
        if name.startswith("BEAM_END"):                 return 302 + 6 * s, 16, Vector((1.4 if y < 0 else -1.4, 0, 0.25))
        if name.startswith(("INST_MOCOW",)):            return 322 + 14 * s, 10, Vector((0, 0, 0.7))
        if name.startswith("RAFTER"):                   return 338 + 22 * s, 14, Vector((0, 0, 1.3))
        if name.startswith("SCREW"):                    return 300 + 60 * s, 8, Vector((0, 0, 0.12))
        if name.startswith(("GLAZING_BAR",)):           return 364 + 10 * s, 12, Vector((0, 0, 1.0))
        if name.startswith(("SHEET_glass",)):           return 376 + 10 * s, 14, Vector((0, 0, 1.2))
        if name.startswith(("GLAZING",)):               return 388 + 6 * s, 10, Vector((0, 0, 0.8))
        return 260, 1, Vector((0, 0, 0))
    c = bpy.data.collections.get("PERGOLA")
    if not c:
        return
    bpy.context.view_layer.update()                          # fresh objects: matrix_world must be valid for the bounds
    root = bpy.data.objects.get("PERGOLA_ROOT")
    units = [o for o in c.all_objects if (o.parent is None and o.name != "PERGOLA_ROOT") or o.parent == root]
    hidden = 0
    for o in units:
        bb = [o.matrix_world @ Vector(v) for v in o.bound_box] if o.type == "MESH" else [o.matrix_world.translation]
        cx = sum(v.x for v in bb) / len(bb); cy = sum(v.y for v in bb) / len(bb)
        t0, dur, off = window(o.name, cx, cy)
        u = (f - t0) / dur
        if u <= 0:
            for x in [o] + list(o.children_recursive):
                x.hide_render = True
            hidden += 1
        elif u < 1:
            k = (1 - u) ** 3                                    # ease-out: arrives fast, settles
            o.location = Vector(o.location) + off * k           # PERGOLA_ROOT is an identity parent
    return hidden


def wind():
    """f 151-210: the gust takes the napkin and pushes the fallen leaves over the deck"""
    if FRAME is None or not (151 <= FRAME <= 210):
        return
    t = T
    n = bpy.data.objects.get("napkin")
    if n is not None:
        u = max(0.0, (t - 0.25) / 0.75)                         # starts sliding at t=0.25
        n.location = Vector(n.location) + Vector((-0.9 * u * u, 1.3 * u * u, 0.02 * u + 0.75 * u ** 3))
        n.rotation_euler = (1.9 * u * u, 0.8 * u, n.rotation_euler.z + 2.4 * u)
    for o in bpy.data.objects:
        if o.name.startswith("leaf_") and o.type == "MESH":
            s = (hash(o.name) % 100) / 100.0
            u = max(0.0, t - 0.15 * s)
            o.location = Vector(o.location) + Vector((-1.6 * u * (0.6 + s), 2.2 * u * (0.5 + s), 0.03 * abs(math.sin(9 * u + 6 * s))))
            o.rotation_euler.z += 5 * u * (0.5 + s); o.rotation_euler.x += 2.5 * u * s
