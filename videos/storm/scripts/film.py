"""RIVON: THE STORM - timeline v2 (990 frames, 33 s, 30 fps). Every frame renders stateless: frame -> shot + local t
-> camera move, weather, animation. Camera grammar (one distinct, motivated move per shot, never repeated back to back):
  A wide       1- 75  slow dolly-in on the terrace (establishing)
  B glass     76-135  lateral slide with parallax + rack focus pier -> glass
  C wind     136-210  locked-off low camera at table height: all motion is in the frame (napkin = cloth sim, leaves)
  D storm    211-315  tripod, slow tilt-up from the sea to the shelf cloud creeping in
  E dropfall 316-390  high-speed-camera look: tracking the first drop down from the sky to the glass
  F freeze   391-435  macro: the drop decelerates and stops 4.5 mm above the wine; everything stops
  G conn1    436-510  slow arc: the Trojak is lowered onto the post, seats, two screws drive in
  H conn2    511-585  from inside, above: the beams are lowered onto the Trojak plates, settle; screws
  I conn3    586-645  the rafter comes down into the Mocowanie belek; screws
  J pergola  646-735  crane-up wide: glazing bars and glass go on, then the warm light comes on
  K splash   736-810  over the rim, looking down: time resumes, the one drop lands (crater, crown, jet)
  L rain     811-885  under the roof, slow pull-back: the downpour starts outside, dry and warm inside
  M final    886-990  slow pull-back: the rain thins, the sun breaks through onto the pergola; end card in post
"""
import math, os, json
from pathlib import Path
import bpy
from mathutils import Vector, Matrix

SHOTS = [("wide", 1, 75), ("glass", 76, 135), ("wind", 136, 210), ("storm", 211, 315), ("dropfall", 316, 390),
         ("freeze", 391, 435), ("conn1", 436, 510), ("conn2", 511, 585), ("conn3", 586, 645), ("pergola", 646, 735),
         ("splash", 736, 810), ("rain_under", 811, 885), ("final", 886, 990)]
NF = 990; LIGHTS_ON = 716
FRAME = None; T = 0.5
PERGOLA_SHOTS = ("macro", "s09", "conn1", "conn2", "conn3", "pergola", "rain_under", "final", "splash")
# new shot cameras: loc, target, lens, fstop, focus
CAMS = {"wind":  ((1.55, -2.45, 1.16), (-0.05, -0.25, 0.86), 40, 4.0, 2.4),
        "conn1": ((2.62, -3.98, 2.12), (1.72, -3.02, 2.56), 70, 5.6, 1.38),
        "conn2": ((0.70, -2.15, 3.02), (1.68, -2.97, 2.60), 50, 5.6, 1.33),
        "conn3": ((0.95, -1.02, 2.47), (1.60, -0.43, 2.67), 60, 5.6, 0.9)}
WEATHER = {"storm": "storm", "dropfall": "storm", "freeze": "freeze", "macro": "freeze", "conn1": "freeze", "conn2": "freeze",
           "conn3": "freeze", "pergola": "freeze", "splash": "freeze", "rain_under": "rain", "final": "clearing"}


def shot_of(f):
    for name, a, b in SHOTS:
        if a <= f <= b:
            return name, (f - a) / max(1, b - a)
    raise ValueError(f)


def ease(t):
    t = max(0.0, min(1.0, t)); return t * t * (3 - 2 * t)


def set_frame(f):
    global FRAME, T
    FRAME = f; shot, T = shot_of(f)
    os.environ["WX_SEED"] = str(1000 + f); os.environ["SEA_TIME"] = str(f / 30.0)
    if shot == "glass":
        os.environ["HDRI_STRENGTH"] = str(22.3 * (1.0 - 0.30 * ease((T - 0.5) / 0.5)))    # the first cloud edge
    if shot == "wind":
        os.environ["HDRI_STRENGTH"] = str(22.3 * (0.70 - 0.12 * ease(T)))
    if shot == "storm":
        os.environ["CB_X"] = str(5700 - 900 * T)                    # the front creeps: 900 m in 3.5 s of screen time
        os.environ["CB_DENS"] = str(0.030 + 0.005 * T)
        os.environ["WEATHER_EV"] = str(1.25 - 0.4 * ease(T))        # daylight goes as the cloud takes the sky
    if shot == "rain_under":
        os.environ["RAIN_N"] = str(int(8000 + 132000 * ease(T / 0.6)))
    if shot == "final":
        os.environ["BREAK_SUN"] = str(34.0 * ease(T / 0.5)); os.environ["RAIN_N"] = str(int(60000 * (1 - 0.9 * ease(T / 0.6))))
    return shot


def lights_on(shot):
    if FRAME is None:
        return shot in ("pergola", "rain_under", "final", "splash")
    return FRAME >= LIGHTS_ON


def look(cam, tgt):
    cam.rotation_euler = (Vector(tgt) - Vector(cam.location)).to_track_quat("-Z", "Y").to_euler()


def move_camera(shot):
    if FRAME is None:
        return
    cam = bpy.context.scene.camera; e = ease(T); k = e - 0.5; mw = cam.matrix_world.to_3x3()
    fwd = mw @ Vector((0, 0, -1)); right = mw @ Vector((1, 0, 0)); up = Vector((0, 0, 1)); L0 = Vector(cam.location)
    if shot == "wide":
        cam.location = L0 + (fwd * 0.6 + up * 0.04) * e                 # starts on the approved still
    elif shot == "glass":                                               # slide + rack focus (pier sharp -> glass sharp)
        cam.location = L0 + right * 0.07 * k
        cam.data.dof.aperture_fstop = 3.2
        cam.data.dof.focus_distance = 0.30 + (26.0 - 0.30) * (1 - ease((T - 0.25) / 0.5)) ** 3
    elif shot == "wind":
        cam.location = L0 + fwd * 0.10 * e                              # almost locked off: an imperceptible creep
    elif shot == "storm":                                               # tripod tilt-up
        look(cam, (40.0, 3.5, 2.5 + 12.5 * ease(T)))
    elif shot == "freeze":
        cam.location = L0 + right * 0.010 * k
    elif shot in ("conn1", "conn2", "conn3"):                           # slow arc around the connector
        tgt = Vector(CAMS[shot][1]); r = L0 - tgt
        ang = {"conn1": 0.22, "conn2": -0.18, "conn3": 0.16}[shot] * k
        cam.location = tgt + Matrix.Rotation(ang, 3, "Z") @ r + up * 0.05 * k; look(cam, tgt)
    elif shot == "pergola":                                             # crane up while pulling back
        cam.location = L0 + up * 0.7 * e - fwd * 0.8 * e; look(cam, (0.0, 0.2, 1.75 + 0.35 * e))
    elif shot == "rain_under":
        cam.location = L0 - fwd * 0.30 * e
    elif shot == "final":
        cam.location = L0 + (-fwd * 1.2 + up * 0.22) * e


# ----------------------------------------------------------------------------------------------- the drop
def drop_state(shot, wine_top):
    """(z of the hero drop centre, visible) for this frame. Frozen position = wine_top + 4.5 mm (+ radius)."""
    zf = wine_top + 0.0045
    if FRAME is None:
        return zf, shot != "splash"
    if shot == "dropfall":                      # 2.6 m of fall seen through a high-speed camera, constant slow-mo speed
        return zf + 0.035 + 2.6 * (1 - T), True
    if shot == "freeze":                        # last 3.5 cm: decelerates to a stop at t = 0.6
        u = min(1.0, T / 0.6); return zf + 0.035 * (1 - u) ** 2.2, True
    if shot == "splash":                        # resumes: 4.5 mm in the first 12 % of the shot, then it is in the wine
        u = T / 0.12; return zf - 0.0045 * min(1.0, u) ** 2 - 0.0002, u < 1.0
    return zf, shot in ("conn1", "conn2", "conn3", "pergola")


def splash_time(shot):
    """seconds of real time since contact, shown ~22x slowed (None before contact)"""
    if FRAME is None:
        return 0.012
    if shot != "splash" or T < 0.12:
        return None
    return (T - 0.12) / 0.88 * 0.11                # 0..110 ms over the remaining 2.2 s of screen time


# ----------------------------------------------------------------------------------------------- assembly
def _fasteners():
    p = Path(__file__).resolve().parents[2] / "rivon_film" / "layout.json"
    return json.load(open(p))["fasteners"]


def assemble():
    """Frozen-time assembly without people: every part comes down vertically as if lowered by a crane, decelerates,
    touches, and settles with a 4 mm damped bounce. Order is the real one: Stopa + posts stand, Trojak onto the post,
    long beams (with their Mocowanie belek already screwed on) onto the Trojak plates, end beams, rafters into the
    Mocowanie, glazing bars, glass. Screws spin in after their part has landed."""
    if FRAME is None:
        return None
    f = FRAME
    c = bpy.data.collections.get("PERGOLA")
    if not c:
        return None
    bpy.context.view_layer.update()
    root = bpy.data.objects.get("PERGOLA_ROOT")
    def st(x):                                           # stable 0..1 stagger from a number
        return (math.sin(x * 12.9898) * 43758.5453) % 1.0
    def window(name, x, y, z):
        if name.startswith(("INST_STOPA", "POST")):  return None
        if name.startswith("INST_TROJAK"):           return 446 + 4 * st(x + y), 28, 1.3
        if name.startswith(("BEAM_LONG", "INST_MOCOW")):  return 515 + (0 if x > 0 else 5), 34, 2.3
        if name.startswith("BEAM_END"):              return 540 + (0 if y < 0 else 4), 30, 2.3
        if name.startswith("RAFTER"):                return 592 + 26 * (y + 3.0) / 6.0, 28, 1.9
        if name.startswith("GLAZING_BAR"):           return 650 + 16 * (y + 3.2) / 6.4, 26, 2.0
        if name.startswith("SHEET_glass"):           return 676 + 16 * (y + 3.2) / 6.4, 28, 2.2
        if name.startswith("GLAZING"):               return 702 + 5 * st(x), 12, 0.8
        return None
    units = [o for o in c.all_objects if ((o.parent is None and o.name != "PERGOLA_ROOT") or o.parent == root) and not o.name.startswith("SCREW")]
    hidden = 0
    for o in units:
        bb = [o.matrix_world @ Vector(v) for v in o.bound_box] if o.type == "MESH" else [o.matrix_world.translation]
        cx, cy, cz = (sum(getattr(v, a) for v in bb) / len(bb) for a in "xyz")
        w = window(o.name, cx, cy, cz)
        if w is None:
            continue
        t0, dur, h0 = w; u = (f - t0) / dur
        if u <= 0:
            for x in [o] + list(o.children_recursive):
                x.hide_render = True
            hidden += 1
        elif u < 1:
            o.location = Vector(o.location) + Vector((0, 0, h0 * (1 - u) ** 1.8))
        else:
            tau = (f - t0 - dur) / 30.0
            o.location = Vector(o.location) + Vector((0, 0, 0.004 * math.exp(-tau * 9.0) * abs(math.cos(tau * 24.0))))
    # screws
    fast = _fasteners(); troj = [o.matrix_world.translation.copy() for o in units if o.name.startswith("INST_TROJAK")]
    for i, fz in enumerate(fast):
        ob = bpy.data.objects.get(f"SCREW_{i:03d}")
        if ob is None:
            continue
        p = Vector(fz["pos_mm"]) * 0.001; ax = Vector(fz["axis_to_timber"]).normalized()
        dT = min(((p - t).length for t in troj), default=9.0)
        if p.z < 0.6:
            continue                                              # Stopa screws: already in
        if dT < 0.5 and p.z < 2.52:   t0 = 476 + 22 * st(i * 1.7)   # Trojak -> post
        elif dT < 0.6:                t0 = 556 + 24 * st(i * 1.7)   # beams -> Trojak plates
        else:                         t0 = 618 + 24 * st(i * 1.7)   # rafters -> Mocowanie
        u = (f - t0) / 10.0
        if u <= 0:
            ob.hide_render = True; hidden += 1
        elif u < 1:
            ob.location = Vector(ob.location) - ax * 0.045 * (1 - u)
            ob.rotation_euler.rotate(Matrix.Rotation(-14.0 * math.pi * (1 - u), 3, ax))
    return hidden


# ----------------------------------------------------------------------------------------------- wind
def wind():
    """C: a real gust. The napkin is a cloth simulation (30x30 grid, linen weight) on the table under a wind force that
    ramps up; it is stepped from the start of the shot to this frame, so every frame is reproducible."""
    if FRAME is None or shot_of(FRAME)[0] != "wind":
        return
    n = FRAME - 136                                         # local frame 0..74
    old = bpy.data.objects.get("napkin")
    if old is not None:
        loc = old.matrix_world.translation.copy(); rz = old.rotation_euler.z; mat = old.data.materials[0] if old.data.materials else None
        old.hide_render = True
        bpy.ops.mesh.primitive_grid_add(x_subdivisions=32, y_subdivisions=32, size=0.30, location=(loc.x, loc.y, loc.z + 0.010))
        nk = bpy.context.object; nk.name = "napkin_cloth"; nk.rotation_euler.z = rz
        for v in nk.data.vertices:                           # a napkin never lies dead flat: soft waves and a raised
            x, y = v.co.x / 0.15, v.co.y / 0.15              # windward edge - that is what the gust gets under
            v.co.z = 0.004 * math.sin(3.1 * x + 1.0) * math.cos(2.3 * y) + 0.022 * max(0.0, (x - y) * 0.5 - 0.25) ** 1.5
        if mat:
            nk.data.materials.append(mat)
        cm = nk.modifiers.new("cloth", "CLOTH"); cs = cm.settings
        cs.quality = 8; cs.mass = 0.3; cs.air_damping = 1.4   # (Blender's damping is not mass-scaled: a physically light
        # cloth freezes in the air, so the default vertex mass stays and the gust is given as acceleration)
        cs.tension_stiffness = 2; cs.compression_stiffness = 2; cs.shear_stiffness = 1; cs.bending_stiffness = 0.002
        cs.tension_damping = 1; cs.compression_damping = 1
        cs.shear_stiffness = 6; cs.bending_stiffness = 0.08; cm.collision_settings.use_self_collision = True
        cm.collision_settings.self_distance_min = 0.002; cm.collision_settings.distance_min = 0.002
        sol = nk.modifiers.new("thick", "SOLIDIFY"); sol.thickness = 0.0012
        ss = nk.modifiers.new("ss", "SUBSURF"); ss.levels = ss.render_levels = 1
        for o in bpy.data.objects:                           # the table top and the plates stop the cloth
            if o.type == "MESH" and o.name.startswith(("top_", "plate_")):
                if not any(m.type == "COLLISION" for m in o.modifiers):
                    o.modifiers.new("col", "COLLISION")
                o.collision.thickness_outer = 0.002; o.collision.cloth_friction = 0.5
        bpy.ops.object.effector_add(type="WIND", location=(loc.x + 1.2, loc.y - 1.6, loc.z - 0.05))
        w = bpy.context.object; w.name = "gust"; d = Vector((-0.55, 0.78, 0.30)).normalized()
        w.rotation_euler = d.to_track_quat("Z", "Y").to_euler(); w.field.flow = 0.0; w.field.noise = 3.0; w.field.seed = 7
        sc = bpy.context.scene; sc.frame_start = 1; sc.frame_end = 80; cm.point_cache.frame_start = 1; cm.point_cache.frame_end = 80
        for fr, sv in ((1, 0.0), (12, 0.0), (20, 300.0), (28, 1200.0), (40, 600.0), (52, 1600.0), (80, 1200.0)):   # lull, gust, lull, stronger gust
            w.field.strength = sv; w.keyframe_insert("field.strength", frame=fr)
        # Blender's cloth wind only presses along the face normals (a flat cloth would just hover), so the drag that
        # carries the napkin downwind is given as a horizontal component of gravity following the same gust curve
        for fr, sv, lift in ((1, 0.0, 0.0), (12, 0.0, 0.0), (20, 1.5, 2.0), (28, 7.0, 11.5), (40, 3.0, 5.0), (52, 9.0, 11.0), (80, 7.0, 6.0)):
            sc.gravity = (d.x * sv, d.y * sv, -9.81 + lift); sc.keyframe_insert("gravity", frame=fr)   # drag + lift of the gust
        for fr in range(1, n + 2):
            sc.frame_set(fr)
        dg = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(nk.evaluated_get(dg))
        baked = bpy.data.objects.new("napkin_flying", me); baked.matrix_world = nk.matrix_world.copy()
        nk.users_collection[0].objects.link(baked); me.shade_smooth()
        bpy.data.objects.remove(nk, do_unlink=True); bpy.data.objects.remove(w, do_unlink=True)
        sc.frame_set(1); sc.animation_data_clear(); sc.gravity = (0, 0, -9.81)
    t = T
    for o in bpy.data.objects:                               # fallen leaves skitter over the deck in the gusts
        if o.name.startswith("leaf_") and o.type == "MESH":
            s = (hash(o.name) % 100) / 100.0
            u = ease(max(0.0, (t - 0.22 - 0.2 * s) / 0.6))
            o.location = Vector(o.location) + Vector((-1.5 * u * (0.5 + s), 2.1 * u * (0.5 + s), 0.02 * abs(math.sin(14 * u + 6 * s))))
            o.rotation_euler.z += 7 * u * (0.5 + s); o.rotation_euler.x += 3.0 * u * s
