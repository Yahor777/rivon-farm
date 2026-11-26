"""RIVON video #4 - Stary Rynek w Poznaniu: restaurant swaps its folding parasols for RIVON gazebos (flat roof).
Procedural Blender scene. See NOTES.md. Coordinates: X along the facade row (camera looks +X), Y across (+Y = facades), Z up."""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rynek_core import *
import rynek_town as T
import rynek_people as P
import rynek_gazebo as Z
FPS, NFR = 30, 960

def setup_render(w=1080, h=1920, spp=64):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w, h, 100
    sc.render.fps = FPS; sc.frame_start = 1; sc.frame_end = NFR
    sc.cycles.samples = spp; sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.015
    sc.cycles.use_denoising = True; sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    sc.cycles.max_bounces = 6; sc.cycles.diffuse_bounces = 3; sc.cycles.glossy_bounces = 3
    sc.cycles.transmission_bounces = 3; sc.cycles.sample_clamp_indirect = 8
    sc.view_settings.view_transform = 'AgX'
    try: sc.view_settings.look = 'Medium High Contrast'
    except Exception: pass
    sc.view_settings.exposure = -0.3

def build_world():
    sc = bpy.context.scene
    w = bpy.data.worlds.new("sky"); sc.world = w; w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    d = Vector((-0.5, -0.75, 0.42)).normalized()          # direction to the sun: low, warm, coming from the street side
    sky = nt.nodes.new('ShaderNodeTexSky'); sky.sky_type = 'MULTIPLE_SCATTERING'
    sky.sun_elevation = math.asin(d.z); sky.sun_rotation = math.atan2(d.y, d.x) % (2 * math.pi); sky.sun_disc = False
    sky.air_density = 1.0; sky.aerosol_density = 1.3; sky.ozone_density = 1.2
    # camera rays see the real sky, every other ray gets a warm-tinted copy: warm bounce light instead of blue fill
    lp = nt.nodes.new('ShaderNodeLightPath')
    tint = nt.nodes.new('ShaderNodeMix'); tint.data_type = 'RGBA'; tint.blend_type = 'MULTIPLY'; tint.inputs[0].default_value = 1.0
    tint.inputs[7].default_value = (1.0, 0.8, 0.58, 1)
    nt.links.new(sky.outputs['Color'], tint.inputs[6])
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    nt.links.new(lp.outputs['Is Camera Ray'], mix.inputs[0])
    nt.links.new(tint.outputs[2], mix.inputs[6]); nt.links.new(sky.outputs['Color'], mix.inputs[7])
    bg = nt.nodes.new('ShaderNodeBackground'); bg.inputs['Strength'].default_value = 0.42
    out = nt.nodes.new('ShaderNodeOutputWorld')
    nt.links.new(mix.outputs[2], bg.inputs['Color']); nt.links.new(bg.outputs['Background'], out.inputs['Surface'])
    sun = bpy.data.lights.new("sun", 'SUN'); sun.energy = 4.6; sun.angle = math.radians(1.6); sun.color = (1.0, 0.77, 0.5)
    so = bpy.data.objects.new("sun", sun); sc.collection.objects.link(so)
    so.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    return so


def build_camera():
    sc = bpy.context.scene
    cam = bpy.data.cameras.new("cam"); cam.lens = 26; cam.clip_start = 0.05; cam.clip_end = 900
    co = bpy.data.objects.new("cam", cam); sc.collection.objects.link(co); sc.camera = co
    tgt = bpy.data.objects.new("cam_target", None); sc.collection.objects.link(tgt)
    cam.dof.use_dof = True; cam.dof.focus_object = tgt; cam.dof.aperture_fstop = 3.4
    tc = co.constraints.new('TRACK_TO'); tc.target = tgt; tc.track_axis = 'TRACK_NEGATIVE_Z'; tc.up_axis = 'UP_Y'
    return co, tgt

def surroundings():
    """close the square on every side (no empty horizon): east + west rows, a second taller rank behind the far row, church tower, trees"""
    keys = list(T.WALLS); gabs = ['tri', 'ogee', 'step', 'flat', 'ogee', 'tri']
    ys = 5.0; i = 0
    while ys > -75:                                   # east row, facade faces -X
        w = 6.4 + (i * 7 % 5) * 0.7
        T.kamienica("east%d" % i, (140.0, ys), -math.pi / 2, w, 3 + (i % 3), keys[(i * 3 + 1) % len(keys)], gabs[i % 6], seed=700 + i, ground='shop')
        ys -= w; i += 1
    ys = -75.0; i = 0
    while ys < 5.0:                                   # west row, facade faces +X
        w = 6.4 + (i * 5 % 5) * 0.7
        T.kamienica("west%d" % i, (-44.0, ys), math.pi / 2, w, 3 + (i % 3), keys[(i * 5 + 2) % len(keys)], gabs[(i + 2) % 6], seed=800 + i, ground='shop')
        ys += w; i += 1
    x = -44.0; i = 0
    while x < 145:                                    # second rank behind the far row (taller)
        w = 7.0 + (i * 3 % 4) * 0.8
        T.kamienica("far2_%d" % i, (x + w, -76.0), math.pi, w, 5 + (i % 2), keys[(i * 7 + 3) % len(keys)], gabs[(i + 1) % 6], seed=900 + i, ground='shop')
        x += w; i += 1
    T.church_tower(100.0, -80.0); T.church_tower(-20.0, -86.0, 30.0)
    for k in range(16):                               # big trees in front of the far row
        T.big_tree(-30 + k * 9.5, -56.5 + (k % 3) * 0.8, 1.0 + 0.2 * (k % 4))
    for k in range(7):
        T.big_tree(131.0 + (k % 2) * 1.2, -2.0 - k * 9.5, 1.1)


def build_town():
    T.build_materials_town()
    box("paving", (600, 600, 0.3), (60, -120, -0.15), M['cobble'], grain=False)
    box("terrace", (80, 4.6, 0.03), (24, 2.7, 0.0), M['slabs'], grain=False)
    # restaurant row, facing -Y (y = 5), x from -40 to 135
    row = [(-40, 8.0, 4, 'cream', 'ogee'), (-32, 6.6, 3, 'salmon', 'tri'), (-25.4, 7.4, 4, 'mint', 'step'), (-18, 7.0, 4, 'ochre', 'flat'),
           (-11, 6.2, 3, 'blue', 'tri'), (-4.8, 8.2, 4, 'rose', 'ogee'),
           (3.4, 7.4, 4, 'yellow', 'tri'), (10.8, 6.4, 4, 'teal', 'ogee'), (17.2, 8.6, 4, 'salmon', 'step'), (25.8, 7.0, 3, 'cream', 'ogee'),
           (32.8, 6.2, 4, 'sage', 'tri'), (39.0, 8.0, 4, 'apricot', 'flat'), (47.0, 6.8, 4, 'blue', 'ogee'), (53.8, 7.4, 3, 'rose', 'tri'),
           (61.2, 7.0, 4, 'mint', 'step'), (68.2, 8.4, 4, 'ochre', 'ogee'), (76.6, 6.6, 4, 'lilac', 'tri'), (83.2, 7.8, 3, 'cream', 'flat'),
           (91.0, 7.0, 4, 'salmon', 'ogee'), (98.0, 8.2, 4, 'yellow', 'tri'), (106.2, 6.8, 4, 'teal', 'step'), (113.0, 7.6, 4, 'terra', 'ogee'),
           (120.6, 7.0, 3, 'grey', 'tri'), (127.6, 8.0, 4, 'white', 'ogee')]
    for i, (x0, w, fl, wl, gb) in enumerate(row):
        gr = 'arcade' if (i % 5 == 2) else 'shop'
        T.kamienica("row%d" % i, (x0, 5.0), 0.0, w, fl, wl, gb, seed=100 + i, ground=gr, lit=(0 <= x0 <= 40), awning=(gr == 'shop' and 0 <= x0 <= 45))
    # far row (y=-62, facing +Y)
    far = [(-30 + i * 7.3, 6.8 + (i % 3) * 0.6, 3 + (i % 2), T.WALLS and list(T.WALLS)[(i * 5) % len(T.WALLS)], ['tri', 'ogee', 'step', 'flat'][i % 4]) for i in range(20)]
    for i, (x0, w, fl, wl, gb) in enumerate(far):
        T.kamienica("far%d" % i, (x0 + w, -62.0), math.pi, w, fl, wl, gb, seed=300 + i, ground='shop')
    surroundings()
    T.ratusz((57.0, -8.0), -math.pi / 2)
    # Domki Budnicze: arcaded little houses behind the Ratusz
    x = 78.0
    for i, (w, wl, gb) in enumerate([(5.0, 'salmon', 'ogee'), (4.6, 'mint', 'tri'), (5.2, 'yellow', 'ogee'), (4.8, 'blue', 'step'), (5.0, 'rose', 'ogee')]):
        T.kamienica("budnik%d" % i, (x + w, -22.0), math.pi, w, 2, wl, gb, seed=500 + i, ground='arcade')
        x += w
    T.fountain(36.0, -17.0); T.pillory(50.0, -24.0)
    T.market_stalls()

NMOD = 9
MOD_X0 = 11.0
COL_X0 = MOD_X0 - 1.5
MOD_Y = 2.5
MOD_X = [MOD_X0 + c * Z.WX for c in range(NMOD)]
TEAR = [124, 116, 128, 108, 132, 100, 120, 90, 82]       # frame each parasol is ripped off (index = module)
def SCHED(k):
    """column k (x = COL_X0 + 3k). The east end bay (columns NMOD, NMOD-1, ~10 % of the zone) is built first, slowly, for the
    macro shots; then the rest assembles westwards in a fast wave while the camera trucks along the front."""
    if k >= NMOD - 1: return (150, 1.8)
    return (540 + (NMOD - 2 - k) * 28, 0.35)


ASSEM = [SCHED]                   # built once, stays up
DISM = None

CAM_KEYS = [  # frame, camera location, look-at target, f-stop -- sampled with a C1 spline (no sudden turns)
    (0,   (42.5, -4.2, 1.8),  (29.0, 2.6, 1.9), 5.0),          # gale on the terrace: parasols torn away, leaves flying
    (70,  (41.8, -3.7, 1.75), (30.0, 2.4, 1.8), 5.0),
    (135, (39.8, -2.2, 1.25), (34.0, 1.6, 0.9), 3.6),
    (178, (37.75, -0.65, 0.5), (36.5, 0.65, 0.25), 2.0),       # macro: Stopa placed
    (212, (37.7, -0.6, 0.6),  (36.5, 0.65, 0.4), 2.0),        # post slides into the Stopa
    (255, (37.6, -0.55, 2.1), (36.5, 0.65, 2.36), 2.0),        # Trojak lowered onto the post
    (292, (37.6, -0.55, 2.3), (36.5, 0.65, 2.38), 2.0),
    (335, (38.5, -1.15, 2.65), (35.6, 1.0, 2.35), 2.4),        # beams enter the Trojak / Trojnik
    (378, (37.1, -0.15, 2.8), (35.0, 3.4, 2.25), 2.4),         # Mocowanie belek on the rails, rafters drop in
    (420, (36.4, 0.0, 2.88), (34.4, 3.3, 2.2), 2.4),
    (450, (38.6, -2.4, 3.0),  (35.0, 2.5, 2.4), 3.2),          # roof cassette lands, lights on
    (500, (36.5, -5.2, 2.3),  (34.0, 2.5, 1.8), 4.5),          # pull back
    (545, (33.5, -5.6, 1.7), (33.5, 2.5, 1.55), 5.6),          # truck along the front, perpendicular to the gazebo
    (640, (23.3, -5.6, 1.7), (23.3, 2.5, 1.55), 5.6),
    (740, (12.6, -5.6, 1.7), (12.6, 2.5, 1.55), 5.6),
    (830, (7.5, -7.0, 2.1),   (13.5, 2.5, 1.6), 5.6),          # ease out and turn gently to look along the finished terrace
    (959, (4.5, -7.5, 3.2),   (20.0, 2.5, 1.7), 6.0),
]


LENS = [(0, 26), (120, 28), (178, 55), (292, 50), (335, 40), (420, 34), (450, 30), (500, 24), (545, 20), (830, 20), (959, 22)]


def _spline(keys, f):
    """C1 cubic Hermite through (frame, value) knots; tangents from neighbours (Catmull-Rom with real times), zero at the ends"""
    import numpy as np
    ts = [k[0] for k in keys]
    if f <= ts[0]: return np.array(keys[0][1], float)
    if f >= ts[-1]: return np.array(keys[-1][1], float)
    i = max(j for j in range(len(ts) - 1) if ts[j] <= f)
    P = [np.array(k[1], float) for k in keys]
    def tan(j):
        if j == 0 or j == len(ts) - 1: return P[j] * 0
        return (P[j + 1] - P[j - 1]) / (ts[j + 1] - ts[j - 1])
    h = ts[i + 1] - ts[i]; u = (f - ts[i]) / h
    h00 = 2 * u ** 3 - 3 * u ** 2 + 1; h10 = u ** 3 - 2 * u ** 2 + u; h01 = -2 * u ** 3 + 3 * u ** 2; h11 = u ** 3 - u ** 2
    return h00 * P[i] + h10 * h * tan(i) + h01 * P[i + 1] + h11 * h * tan(i + 1)


def animate_camera(co, tgt):
    L = [(k[0], k[1]) for k in CAM_KEYS]; Tg = [(k[0], k[2]) for k in CAM_KEYS]; Fs = [(k[0], (k[3],)) for k in CAM_KEYS]
    for f in range(0, NFR):
        co.location = tuple(_spline(L, f)); co.keyframe_insert('location', frame=f)
        tgt.location = tuple(_spline(Tg, f)); tgt.keyframe_insert('location', frame=f)
        co.data.dof.aperture_fstop = float(_spline(Fs, f)[0]); co.data.dof.keyframe_insert('aperture_fstop', frame=f)
        co.data.lens = float(_spline([(k, (v,)) for k, v in LENS], f)[0]); co.data.keyframe_insert('lens', frame=f)
    for ob in (co, tgt, co.data):
        ad = ob.animation_data
        if not (ad and ad.action): continue
        try: fcs = list(ad.action.fcurves)
        except Exception:
            fcs = [fc for layer in ad.action.layers for strip in layer.strips for cb in strip.channelbags for fc in cb.fcurves]
        for fc in fcs:
            for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'


def build_restaurant():
    P.build_materials_people(); Z.build_materials_gaz()
    tables = []
    for c, cx in enumerate(MOD_X):
        if c == 0:
            service_bay(cx)
        else:
            P.table_group(c, cx, MOD_Y, guests=False); tables.append((cx, MOD_Y))
        fabric = M['canopy_a'] if c % 2 == 0 else M['canopy_b']
        ob, parts, clo = Z.parasol(cx, MOD_Y, fabric)
        Z.animate_parasol(ob, parts, clo, TEAR[c], seed=c)
    Z.wind_debris(170, 45, 0, 165, ((14.0, 44.0), (-14.0, 4.5)), tables=tables)
    Z.structure(COL_X0, NMOD, MOD_Y, ASSEM, DISM)


def service_bay(cx):
    """first bay: flowers + service console (keeps the assembly close-ups free of faces)"""
    mb = MB(); mats = {'wood': M['wood_dark'], 'leaf': M['leaf'], 'fr': M['flower_r'], 'fp': M['flower_p'], 'fw': M['flower_w'], 'zinc': M['zinc'], 'top': M['tabletop']}
    r = random.Random(77)
    mb.box('wood', (0, 0.9, 0.45), (2.2, 0.55, 0.9)); mb.box('top', (0, 0.9, 0.93), (2.3, 0.62, 0.05))
    mb.box('zinc', (0.5, 0.9, 1.1), (0.4, 0.3, 0.3))
    for sx in (-1, 1):
        mb.box('wood', (sx * 0.95, -0.6, 0.35), (0.9, 0.6, 0.7))
    mb.emit("service", mats, loc=(cx, MOD_Y, 0), smooth=False)
    fm = MB(); fmats = {'leaf': M['leaf'], 'fr': M['flower_r'], 'fp': M['flower_p'], 'fw': M['flower_w']}
    for sx in (-1, 1):
        for _ in range(90):
            fm.blob('leaf', (sx * 0.95 + r.uniform(-0.4, 0.4), -0.6 + r.uniform(-0.25, 0.25), 0.8 + r.uniform(0, 0.32)), r.uniform(0.06, 0.1), 2)
        for _ in range(50):
            fm.blob(r.choice(('fr', 'fr', 'fp', 'fw')), (sx * 0.95 + r.uniform(-0.4, 0.4), -0.6 + r.uniform(-0.25, 0.25), 1.0 + r.uniform(0, 0.28)), 0.035, 1)
    fm.emit("service_fl", fmats, loc=(cx, MOD_Y, 0), smooth=True)


def crowd(rr):
    """people on the square: walkers on straight paths for the whole film, chatting groups, tourists"""
    def free(x, y):
        if 54 < x < 69.5 and -43 < y < -5: return False                  # Ratusz
        if math.hypot(x - 36, y + 17) < 4.5 or math.hypot(x - 50, y + 24) < 2.5: return False
        if 76 < x < 104 and -27 < y < -14: return False                  # Domki Budnicze
        return True
    n = 0; tries = 0
    while n < 85 and tries < 2500:
        tries += 1
        x0 = rr.uniform(0, 78); y0 = rr.uniform(-36, -7.5)
        ang = rr.choice([0, math.pi, math.pi / 2, -math.pi / 2, 0.4, math.pi - 0.4, -0.5]) + rr.uniform(-0.2, 0.2)
        sp = rr.uniform(1.05, 1.45); ln = sp * NFR / 30.0
        x1, y1 = x0 + math.cos(ang) * ln, y0 + math.sin(ang) * ln
        if not (-5 < x1 < 100 and -44 < y1 < -5.5): continue
        ok = all(free(x0 + (x1 - x0) * t / 10, y0 + (y1 - y0) * t / 10) for t in range(11))
        if not ok: continue
        P.walker("walker%d" % n, rr, (x0, y0), (x1, y1), 0, NFR); n += 1
    m = 0; tries = 0
    while m < 22 and tries < 600:
        tries += 1
        cx, cy = rr.uniform(2, 75), rr.uniform(-36, -7.8)
        if not free(cx, cy) or any(abs(cx - sx) < 6 and abs(cy - sy) < 5 for sx, sy in T.STALLS): continue
        k = rr.randint(2, 5)
        for i in range(k):
            a = 2 * math.pi * i / k + rr.uniform(-0.2, 0.2)
            P.standing_person("grp%d_%d" % (m, i), rr, (cx + math.cos(a) * 0.8, cy + math.sin(a) * 0.8, 0), a + math.pi)
        m += 1


def build(w=1080, h=1920, spp=64, full=True):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    setup_render(w, h, spp); build_world(); build_town()
    co, tgt = build_camera()
    if full:
        build_restaurant(); animate_camera(co, tgt); finalize_anim()
    return co, tgt
