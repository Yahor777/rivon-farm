"""RIVON: THE STORM - timeline v2 (1050 frames, 35 s, 30 fps). Every frame renders stateless: frame -> shot + local t
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
  M final    886-1050  slow pull-back: the rain thins, the sun breaks through onto the pergola; end card in post
"""
import math, os, json
from pathlib import Path
import bpy
from mathutils import Vector, Matrix

SHOTS = [("wide", 1, 75), ("glass", 76, 135), ("wind", 136, 210), ("storm", 211, 315), ("dropfall", 316, 390),
         ("freeze", 391, 435), ("conn1", 436, 510), ("conn2", 511, 585), ("conn3", 586, 645), ("pergola", 646, 735),
         ("splash", 736, 810), ("rain_under", 811, 885), ("final", 886, 1050)]
NF = 1050; LIGHTS_ON = 716
FRAME = None; T = 0.5
PERGOLA_SHOTS = ("macro", "s09", "conn1", "conn2", "conn3", "pergola", "rain_under", "final", "splash")
# new shot cameras: loc, target, lens, fstop, focus
CAMS = {"wind":  ((1.55, -2.45, 1.16), (-0.05, -0.25, 0.86), 40, 4.0, 2.4),
        # conn1: from inside and below the corner - both socket mouths visible, storm sky behind
        "conn1": ((0.72, -1.97, 2.50), (1.68, -2.93, 2.82), 45, 3.2, 1.38),
        # conn2: from inside, above the roof plane: rafter ends coming down into the Mocowanie saddles, one after another
        "conn2": ((1.12, -1.22, 3.48), (1.57, -0.96, 2.96), 50, 2.8, 0.74),
        # conn3: from the lawn - the frame lands on the post, the house behind
        "conn3": ((2.80, -4.10, 2.20), (1.70, -2.95, 2.52), 70, 4.0, 1.62)}
WEATHER = {"storm": "storm", "dropfall": "storm", "freeze": "storm", "macro": "freeze", "conn1": "freeze", "conn2": "freeze",
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
    os.environ["WX_SEED"] = str(1000 + f); # time stops with the drop (F_STOP) and starts again when it lands (745): the sea stands still in between
    os.environ["SEA_TIME"] = str((min(f, F_STOP) if f < 745 else f - (745 - F_STOP)) / 30.0)
    if WEATHER.get(shot) == "freeze":
        os.environ["RAIN_N"] = "60000"
    if shot == "glass":
        os.environ["HDRI_STRENGTH"] = str(22.3 * (1.0 - 0.30 * ease((T - 0.5) / 0.5)))    # the first cloud edge
    if shot == "wind":
        os.environ["HDRI_STRENGTH"] = str(22.3 * (0.70 - 0.12 * ease(T)))
    if shot == "storm":
        os.environ["CB_GROW"] = str(0.06 + 0.94 * ease(T))                        # the cloud does not arrive: it builds up over the sea
        os.environ["WEATHER_EV"] = str(1.25 - 0.30 * ease(T))       # daylight softens as the cloud takes the sky
        if os.environ.get("SKY_PHOTO", "1") == "1":                 # photographed storm sky condensing out of the sunny one
            # the front takes the visible sky over the first 3/4 of the shot, the rest of the dome (and the sun) at the end
            _m = 0.27 * ease(min(1.0, T / 0.8)) + 0.73 * ease(max(0.0, min(1.0, (T - 0.72) / 0.28)))
            os.environ["SKY_MIX"] = str(_m)
            os.environ["WEATHER_EV"] = str(float(os.environ.get("EV0", -0.35)) + float(os.environ.get("EV1", 1.25)) * ease(min(1.0, _m / 0.27)))
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
    elif shot in ("conn1", "conn2", "conn3"):                           # slow arc around the connector
        tgt = Vector(CAMS[shot][1]); r = L0 - tgt
        if shot == "conn1":                                             # slow arc under the corner
            cam.location = tgt + Matrix.Rotation(0.16 * k, 3, "Z") @ r + up * 0.07 * k; look(cam, tgt)
        elif shot == "conn2":                                           # truck sideways, focus follows the landing rafters
            cam.location = L0 + fwd * 0.08 * e
            cam.data.dof.focus_distance = 0.74 - 0.06 * e
        else:                                                           # push in on the landing, rising a little
            cam.location = L0 + fwd * 0.22 * e + right * 0.05 * e; look(cam, tgt)   # level: frozen drops must not drift down
    elif shot == "pergola":                                             # level truck sideways while pulling back: with the
        # old crane-up the frozen drops near the lens slid DOWN the frame by parallax and read as slowly falling rain
        cam.location = L0 + right * float(os.environ.get("PG_TRUCK", -1.0)) * e - fwd * 0.6 * e; look(cam, (0.0, 0.2, 1.75 + 0.15 * e))
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
    if shot == "dropfall":                      # enters the frame at real speed (a streak), then time itself slows down
        return zf + drop_height(), True
    if shot == "freeze":
        return zf + drop_height(), True
    if shot == "splash":                        # resumes: 4.5 mm in the first 12 % of the shot, then it is in the wine
        u = T / 0.12; return zf - 0.0045 * min(1.0, u) ** 2 - 0.0002, u < 1.0
    return zf, shot in ("conn1", "conn2", "conn3", "pergola")


# The drop keeps its speed all the way down. Only in the last 24 cm, while the camera pushes in on it, time itself runs
# down to a stop (speed V0 * (1-u)^P, so there is no jerk at the start of the push and it ends exactly at rest).
F_C, F_STOP, V0, P_SLOW = 372, 420, 0.6, 3.0


def push_u():
    """0..1: the push-in / time running down"""
    return 0.0 if FRAME is None else max(0.0, min(1.0, (FRAME - F_C) / float(F_STOP - F_C)))


def drop_height():
    """height of the hero drop above its frozen position, m"""
    H = V0 * (F_STOP - F_C) / 30.0 / (P_SLOW + 1)
    if FRAME <= F_C:
        return H + V0 * (F_C - FRAME) / 30.0
    return H * (1 - push_u()) ** (P_SLOW + 1)


def drop_speed():
    return V0 * (1 - push_u()) ** P_SLOW


def drop_stretch(shot):
    """z scale of the 4.6 mm drop: motion blur of a 1/60 s shutter while it still moves at real speed"""
    if FRAME is None or shot not in ("dropfall", "freeze"):
        return 0.86
    return max(0.86, drop_speed() / 60.0 / 0.0046)


def exposure_add(shot):
    base = {"macro": 1.0, "conn1": 0.55, "conn2": 0.55, "conn3": 0.6, "freeze": 0.3, "dropfall": 0.5, "splash": 0.25}.get(shot, 0.0)
    if shot == "pergola":                       # dusk before the lights come on, then the lamps carry the frame
        base = 0.90 if FRAME is None else 0.90 - 0.75 * ease((FRAME - LIGHTS_ON) / 16.0)
    if shot in ("dropfall", "freeze") and FRAME is not None:
        base = 0.7 + 0.5 * ease(push_u()) - 1.5 * (1.0 - ease((FRAME - 358) / 24.0))   # stopped down while the lens looks into the bright sky
    return base


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


FRAME_H = 0.40                                    # the roof frame is put together this high above the post tops


def _crane(u):                                    # 1 -> 0, slow start, long deceleration
    u = min(1.0, max(0.0, u)); return (1 - u) ** 2 * (1 + 2 * u)


def _push(u):                                     # 1 -> 0, a part pushed home at steady speed, stopping on the seat
    u = min(1.0, max(0.0, u)); return (1 - u) ** 1.35


def _settle(f, t_land, amp=0.003):
    tau = (f - t_land) / 30.0
    return amp * math.exp(-tau * 9.0) * abs(math.cos(tau * 24.0)) if tau >= 0 else 0.0


def rafter_t0(i):                                 # the row starts at the saddle in front of the conn2 camera
    return 516 + 5 * (i - 3) if i >= 3 else 558 + 5 * (2 - i)


def assemble():
    """Frozen-time assembly without people, in the order that is physically possible with the real parts. The Trojak is
    three closed square sockets, so timber can only enter it along its own axis:
      conn1  436-510  corner Trojaks are pushed onto the ends of the end beam (along x); the far U (long beams with their
                      Mocowanie, far end beam, far Trojaks) slides in along y; screws spin in
      conn2  511-585  rafters are lowered from above into the open Mocowanie saddles, one after another; screws
      conn3  586-645  the finished frame comes down as one piece: the Trojak post sockets swallow the post tops; screws
      pergola 646+    glazing bars, glass, trims come down onto the frame
    All of it happens FRAME_H above the posts until the frame lands."""
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
    T_LAND = 618
    frame_dz = FRAME_H * _crane((f - 592) / 26.0) + _settle(f, T_LAND, 0.0035)
    slide_y = 0.62 * _push((f - 462) / 24.0) + (_settle(f, 486, 0.0015) if f < 592 else 0.0)
    def offset(name, x, y):
        """(offset vector, hidden) of a frame part"""
        if name.startswith(("INST_STOPA", "POST")):
            return None
        if name.startswith("INST_TROJAK"):
            near = y < 0
            dx = (1 if x > 0 else -1) * 0.46 * _push((f - 438) / 22.0) if near else 0.0
            return Vector((dx, 0 if near else slide_y, frame_dz)), False
        if name.startswith("BEAM_END"):
            return Vector((0, 0 if y < 0 else slide_y, frame_dz)), False
        if name.startswith(("BEAM_LONG", "INST_MOCOW")):
            return Vector((0, slide_y, frame_dz)), False
        if name.startswith("RAFTER"):
            i = round((y + 2.4) / 0.48); t0 = rafter_t0(i); u = (f - t0) / 20.0
            return Vector((0, 0, frame_dz + 0.45 * _crane(u) + _settle(f, t0 + 20, 0.003))), f < t0 - 12
        w = None
        if name.startswith("GLAZING_BAR"):   w = (650 + 16 * (y + 3.2) / 6.4, 26, 2.0)
        elif name.startswith("SHEET_glass"): w = (676 + 16 * (y + 3.2) / 6.4, 28, 2.2)
        elif name.startswith("GLAZING"):     w = (702 + 5 * st(x), 12, 0.8)
        if w is None:
            return Vector((0, 0, frame_dz)), False
        t0, dur, h0 = w; u = (f - t0) / dur
        return Vector((0, 0, h0 * _crane(u) + _settle(f, t0 + dur, 0.004))), u <= 0
    units = [o for o in c.all_objects if ((o.parent is None and o.name != "PERGOLA_ROOT") or o.parent == root) and not o.name.startswith("SCREW")]
    hidden = 0; troj = []
    for o in units:
        bb = [o.matrix_world @ Vector(v) for v in o.bound_box] if o.type == "MESH" else [o.matrix_world.translation]
        cx, cy = (sum(getattr(v, a) for v in bb) / len(bb) for a in "xy")
        if o.name.startswith("INST_TROJAK"):
            troj.append(o.matrix_world.translation.copy())
        r = offset(o.name, cx, cy)
        if r is None:
            continue
        if r[1]:
            for x in [o] + list(o.children_recursive):
                x.hide_render = True
            hidden += 1
        else:
            o.location = Vector(o.location) + r[0]
    # screws: spin in along their own axis once the parts they join are seated; they ride with the frame until it lands
    fast = _fasteners()
    for i, fz in enumerate(fast):
        ob = bpy.data.objects.get(f"SCREW_{i:03d}")
        if ob is None:
            continue
        p = Vector(fz["pos_mm"]) * 0.001; ax = Vector(fz["axis_to_timber"]).normalized()
        dT = min(((p - t).length for t in troj), default=9.0); slide = 0.0
        if p.z < 0.6:
            continue                                              # Stopa screws: already in
        if dT < 0.5 and p.z < 2.52:   t0 = 622 + 16 * st(i * 1.7); ride = 0.0        # Trojak -> post, after the landing
        elif dT < 0.6:                t0 = 489 + 16 * st(i * 1.7); ride = frame_dz   # beams -> Trojak
        elif abs(ax.x) > 0.7:         t0 = -99; ride = frame_dz; slide = slide_y     # Mocowanie -> long beam: pre-fitted
        else:                         t0 = 546 + 32 * st(i * 1.7); ride = frame_dz   # rafters in the saddles
        u = (f - t0) / 10.0
        if u <= 0:
            ob.hide_render = True; hidden += 1
            continue
        ob.location = Vector(ob.location) + Vector((0, slide, ride))
        if u < 1:
            ob.location = Vector(ob.location) - ax * 0.045 * (1 - u)
            ob.rotation_euler.rotate(Matrix.Rotation(-14.0 * math.pi * (1 - u), 3, ax))
    return hidden


def hero_light(shot):
    """Product lighting for the connector close-ups: black powder coat only reads through its highlights, so a soft
    cool kicker from behind and a broad soft key from the camera side (as a gap of bright sky would give)."""
    if shot not in ("conn1", "conn2", "conn3"):
        return
    import os
    cam = bpy.context.scene.camera; tgt = Vector(CAMS[shot][1])
    d = Vector(cam.location) - tgt; d.z = 0; d.normalize(); side = Vector((-d.y, d.x, 0))
    k = float(os.environ.get("HERO_W", 0.22))
    def area(name, loc, size, watts, col):
        L = bpy.data.lights.new(name, "AREA"); L.shape = "RECTANGLE"; L.size = size[0]; L.size_y = size[1]; L.energy = watts * k; L.color = col
        o = bpy.data.objects.new(name, L); bpy.context.scene.collection.objects.link(o); o.location = loc; look(o, tgt)
        o.visible_camera = False
    area("hero_key",  tgt + d * 1.5 + side * 1.3 + Vector((0, 0, 0.9)), (1.6, 1.0), 260, (1.0, 0.97, 0.93))
    area("hero_rim",  tgt - d * 1.3 - side * 0.9 + Vector((0, 0, 1.1)), (1.4, 0.35), 520, (0.86, 0.93, 1.0))
    area("hero_edge", tgt - d * 0.4 + side * 1.6 + Vector((0, 0, -0.15)), (0.3, 1.2), 160, (0.90, 0.95, 1.0))


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
