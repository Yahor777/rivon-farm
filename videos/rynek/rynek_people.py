"""Furniture, table settings, seated guests and walkers for the Rynek scene."""
import math, random
from mathutils import Vector
from rynek_core import *

SKIN = [(0.86, 0.66, 0.54), (0.78, 0.56, 0.43), (0.92, 0.74, 0.62), (0.62, 0.42, 0.31), (0.7, 0.5, 0.38), (0.95, 0.8, 0.7)]
HAIR = [(0.04, 0.03, 0.025), (0.2, 0.11, 0.06), (0.5, 0.33, 0.14), (0.72, 0.58, 0.32), (0.42, 0.42, 0.44), (0.1, 0.06, 0.04), (0.33, 0.14, 0.07)]
CLOTH = [(0.1, 0.16, 0.3), (0.55, 0.1, 0.1), (0.86, 0.83, 0.75), (0.17, 0.34, 0.24), (0.8, 0.58, 0.2), (0.1, 0.1, 0.12), (0.82, 0.48, 0.52),
         (0.22, 0.5, 0.62), (0.9, 0.9, 0.9), (0.3, 0.3, 0.34), (0.62, 0.7, 0.35), (0.35, 0.2, 0.45), (0.9, 0.45, 0.2), (0.7, 0.72, 0.78)]
PANTS = [(0.1, 0.12, 0.2), (0.07, 0.07, 0.08), (0.32, 0.26, 0.2), (0.55, 0.48, 0.38), (0.2, 0.22, 0.3), (0.4, 0.15, 0.15), (0.16, 0.3, 0.22)]


def build_materials_people():
    M['skin'] = [pbr("skin%d" % i, c, rough=0.5, bevel=0.0, sss=0.3, spec=0.45, vary=0.05) for i, c in enumerate(SKIN)]
    M['hair'] = [pbr("hair%d" % i, c, rough=0.45, bevel=0.0, spec=0.6, vary=0.08) for i, c in enumerate(HAIR)]
    M['top'] = [pbr("top%d" % i, c, rough=0.88, bevel=0.0, sheen=0.3, vary=0.08) for i, c in enumerate(CLOTH)]
    M['pants'] = [pbr("pants%d" % i, c, rough=0.85, bevel=0.0, vary=0.08) for i, c in enumerate(PANTS)]
    M['shoe'] = [pbr("shoe%d" % i, c, rough=0.4, bevel=0.0) for i, c in enumerate([(0.05, 0.04, 0.035), (0.28, 0.15, 0.08), (0.8, 0.8, 0.78), (0.35, 0.05, 0.05)])]
    M['eye'] = pbr("eye", (0.02, 0.016, 0.014), rough=0.2, bevel=0.0, spec=0.8)
    M['lip'] = pbr("lip", (0.62, 0.3, 0.28), rough=0.5, bevel=0.0)
    M['chair'] = pbr("bentwood", (0.25, 0.13, 0.07), tex="wood_model_dom_2_1.jpg", tile=0.8, rough=0.38, bevel=0.003, vary=0.12, coat=0.3)
    M['seat'] = pbr("rattan_seat", (0.55, 0.38, 0.2), tex="teak_veneer_diff_2k.jpg", tile=0.5, rough=0.6, bevel=0.002, vary=0.1)
    M['tabletop'] = pbr("tabletop", (0.6, 0.4, 0.25), tex="teak_veneer_diff_2k.jpg", tex_rough="teak_veneer_rough_2k.exr",
                        tex_bump="teak_veneer_disp_2k.png", tile=0.9, bump=0.15, rough=0.5, bevel=0.003, vary=0.06)
    M['cloth_w'] = pbr("tablecloth", (0.93, 0.91, 0.86), rough=0.95, bevel=0.0, sheen=0.5)
    M['cloth_c'] = [pbr("tablecloth_c%d" % i, c, rough=0.95, bevel=0.0, sheen=0.4) for i, c in enumerate([(0.55, 0.12, 0.12), (0.2, 0.3, 0.42), (0.86, 0.8, 0.62)])]
    M['ceramic'] = pbr("ceramic", (0.92, 0.91, 0.88), rough=0.15, bevel=0.0, spec=0.8)
    M['glassware'] = pbr("glassware", (0.9, 0.95, 1.0), rough=0.02, spec=1.0, metal=0.15, bevel=0.0)
    M['drink'] = [pbr("drink%d" % i, c, rough=0.1, bevel=0.0, emit=c, emit_str=0.2) for i, c in enumerate([(0.7, 0.55, 0.1), (0.45, 0.05, 0.08), (0.9, 0.35, 0.05), (0.6, 0.42, 0.1)])]
    M['bottle'] = pbr("bottle", (0.04, 0.12, 0.05), rough=0.1, bevel=0.0, spec=0.9)
    M['food'] = [pbr("food%d" % i, c, rough=0.6, bevel=0.0) for i, c in enumerate([(0.6, 0.35, 0.15), (0.3, 0.45, 0.12), (0.7, 0.2, 0.1), (0.85, 0.7, 0.4)])]
    M['bread'] = pbr("bread", (0.62, 0.42, 0.2), rough=0.8, bevel=0.0)
    M['pedestal'] = pbr("pedestal", (0.03, 0.03, 0.035), rough=0.4, metal=0.6, bevel=0.003)


RIGS = {}


def _head_mesh(mb, r, female, hc, pivot, yaw):
    """head with nose, eyes, brows, ears, mouth hint and hair; absolute coordinates, turned by yaw around pivot"""
    kw = dict(pivot=pivot, rot_z=yaw)
    mb.ellipsoid('skin', hc, (0.1, 0.085, 0.115), 2, **kw)
    mb.ellipsoid('skin', (hc[0] + 0.095, 0, hc[2] - 0.02), (0.025, 0.017, 0.03), 1, **kw)                      # nose
    mb.ellipsoid('lip', (hc[0] + 0.085, 0, hc[2] - 0.062), (0.014, 0.034, 0.008), 1, **kw)                    # mouth
    for sy in (-1, 1):
        mb.ellipsoid('eye', (hc[0] + 0.084, sy * 0.036, hc[2] + 0.014), (0.011, 0.01, 0.013), 1, **kw)
        mb.ellipsoid('hair', (hc[0] + 0.082, sy * 0.037, hc[2] + 0.04), (0.012, 0.026, 0.006), 1, **kw)       # brows
        mb.ellipsoid('skin', (hc[0] - 0.005, sy * 0.093, hc[2] - 0.004), (0.017, 0.01, 0.03), 1, **kw)         # ears
    style = r.choice(('short', 'short', 'long', 'bun', 'cap', 'bald' if not female else 'long', 'fringe'))
    if style != 'bald':
        mb.ellipsoid('hair', (hc[0] - 0.02, 0, hc[2] + 0.034), (0.108, 0.094, 0.098), 2, **kw)
    if style in ('fringe', 'long'):
        mb.ellipsoid('hair', (hc[0] + 0.05, 0, hc[2] + 0.075), (0.06, 0.088, 0.04), 1, **kw)
    if style == 'long':
        mb.ellipsoid('hair', (hc[0] - 0.06, 0, hc[2] - 0.12), (0.075, 0.105, 0.2), 2, **kw)
    if style == 'bun':
        mb.ellipsoid('hair', (hc[0] - 0.08, 0, hc[2] + 0.12), (0.05, 0.05, 0.05), 1, **kw)


def seated_person(prefix, parent, r):
    """seated guest, faces local +X, origin = centre of the seat on the floor. Separate torso / head / arms so they can move."""
    female = r.random() < 0.5
    mats = {'skin': r.choice(M['skin']), 'hair': r.choice(M['hair']), 'top': r.choice(M['top']), 'bottom': r.choice(M['pants']),
            'shoe': r.choice(M['shoe']), 'glassware': M['glassware'], 'drink': r.choice(M['drink']), 'eye': M['eye'], 'lip': M['lip']}
    lean = r.uniform(-0.04, 0.1)
    yaw = r.uniform(-0.45, 0.45)
    TP = Vector((0.0, 0.0, 0.57))
    root = empty(prefix, parent=parent)
    low = MB()
    for sy in (-1, 1):
        hip = (0.0, sy * 0.09, 0.56); knee = (0.42, sy * (0.10 + r.uniform(0, 0.05)), 0.53); ank = (0.47 + r.uniform(-0.04, 0.08), sy * 0.11, 0.09)
        if female and r.random() < 0.4:
            low.tube('skin', knee, ank, 0.05, 0.036); low.tube('bottom', hip, knee, 0.085, 0.07)
        else:
            low.tube('bottom', hip, knee, 0.085, 0.065); low.tube('bottom', knee, ank, 0.062, 0.048)
        low.ellipsoid('shoe', (ank[0] + 0.06, ank[1], 0.045), (0.12, 0.05, 0.04), 1)
    low.ellipsoid('bottom', (0.0, 0, 0.57), (0.15, 0.19, 0.105), 2)
    if female and r.random() < 0.5:
        low.ellipsoid('bottom', (0.16, 0, 0.58), (0.26, 0.22, 0.085), 2)
    low.emit(prefix + "_lo", mats, parent=root, smooth=True)
    torso_e = empty(prefix + "_torso", tuple(TP), parent=root)
    tb = MB()
    tb.ellipsoid('top', (-0.02 - lean * 0.2, 0, 0.88), (0.15, 0.205, 0.27), 2, tilt=lean)
    tb.ellipsoid('top', (-0.02 + lean * 0.5, 0, 1.06), (0.1, 0.25 if not female else 0.22, 0.1), 2)
    neck_top = Vector((0.0 + lean * 0.7, 0, 1.2))
    tb.tube('skin', (0.0 + lean * 0.5, 0, 1.1), tuple(neck_top), 0.047, 0.044)
    tb.ellipsoid('top', (0.01 + lean * 0.6, 0, 1.17), (0.06, 0.07, 0.03), 1)                                    # collar
    tb.emit(prefix + "_tb", mats, parent=torso_e, loc=tuple(-TP), smooth=True)
    head_e = empty(prefix + "_head", tuple(neck_top - TP), parent=torso_e)
    hc = (0.015 + lean * 0.8, 0, 1.31)
    hb = MB(); _head_mesh(hb, r, female, hc, tuple(neck_top), yaw)
    hb.emit(prefix + "_hd", mats, parent=head_e, loc=tuple(-neck_top), smooth=True)
    arms = []
    for sy in (-1, 1):
        sh = Vector((-0.02 + lean * 0.5, sy * (0.235 if not female else 0.2), 1.04))
        sh_e = empty(prefix + "_sh", tuple(sh - TP), parent=torso_e)
        ab = MB()
        ab.ellipsoid('top', tuple(sh), (0.065, 0.065, 0.065), 1)
        pose = r.choice(('rest', 'rest', 'glass', 'gesture', 'rest2'))
        if pose == 'glass' and sy == 1 or (pose == 'glass' and r.random() < 0.3):
            elb = (0.17, sy * 0.25, 0.95); hand = (0.31, sy * 0.13, 1.07)
        elif pose == 'gesture':
            elb = (0.2, sy * 0.3, 0.9); hand = (0.38, sy * 0.24, 1.0)
        elif pose == 'rest2':
            elb = (0.1, sy * 0.3, 0.82); hand = (0.3, sy * 0.1, 0.8)
        else:
            elb = (0.14, sy * 0.27, 0.82); hand = (0.40, sy * 0.17, 0.795)
        long_sleeve = r.random() < 0.55
        ab.tube('top', tuple(sh), elb, 0.052, 0.045)
        ab.tube('top' if long_sleeve else 'skin', elb, hand, 0.043, 0.032)
        ab.ellipsoid('skin', (hand[0] + 0.03, hand[1], hand[2]), (0.055, 0.03, 0.026), 1)
        if pose == 'glass':
            ab.tube('glassware', (hand[0] + 0.03, hand[1], hand[2] - 0.05), (hand[0] + 0.03, hand[1], hand[2] + 0.07), 0.032, 0.036, 10, caps=False)
            ab.tube('drink', (hand[0] + 0.03, hand[1], hand[2] - 0.03), (hand[0] + 0.03, hand[1], hand[2] + 0.035), 0.028, 0.032, 8, caps=False)
        ab.emit(prefix + "_ar", mats, parent=sh_e, loc=tuple(-sh), smooth=True)
        arms.append((sy, sh_e, pose))
    RIGS[root.name] = {'torso': torso_e, 'head': head_e, 'arms': arms, 'lean': lean}
    return root


def chair_mb(mb):
    """bentwood bistro chair at local origin, seat centre; back at -X"""
    mb.box('chair', (0, 0, 0.455), (0.44, 0.42, 0.03), uvm=1.0)
    mb.box('seat', (0, 0, 0.472), (0.38, 0.37, 0.012), uvm=1.0)
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.tube('chair', (sx * 0.17, sy * 0.17, 0.0), (sx * 0.19, sy * 0.19, 0.44), 0.014, 0.018, 8, caps=False)
    for sy in (-1, 1):
        mb.tube('chair', (-0.19, sy * 0.18, 0.44), (-0.22, sy * 0.17, 0.92), 0.016, 0.014, 8, caps=False)
    mb.box('chair', (-0.22, 0, 0.9), (0.025, 0.37, 0.05))
    mb.box('chair', (-0.215, 0, 0.72), (0.02, 0.3, 0.03))
    mb.box('chair', (0.0, 0, 0.18), (0.36, 0.02, 0.02)); mb.box('chair', (0.0, 0, 0.18), (0.02, 0.36, 0.02))


def table_group(g, cx, cy, guests=True, R=0.9, n=8, seed=0):
    """round table with cloth, place settings, chairs and (optionally) seated guests. returns (guest_roots, root)"""
    r = random.Random(900 + g * 13 + seed)
    root = empty("table%d" % g, (cx, cy, 0))
    mb = MB()
    mats = {'tabletop': M['tabletop'], 'cloth': r.choice([M['cloth_w'], M['cloth_w']] + M['cloth_c']), 'pedestal': M['pedestal'],
            'ceramic': M['ceramic'], 'glassware': M['glassware'], 'bottle': M['bottle'], 'bread': M['bread'], 'chair': M['chair'],
            'seat': M['seat'], 'leaf': M['leaf'], 'flower': M['flower_r'], 'flower2': M['flower_w'], 'wine': M['drink'][1], 'water': M['drink'][0],
            'food0': M['food'][0], 'food1': M['food'][1], 'food2': M['food'][2], 'food3': M['food'][3], 'iron': M['iron']}
    mb.tube('pedestal', (0, 0, 0.02), (0, 0, 0.72), 0.05, 0.045, 12, caps=False)
    _cyl(mb, 'pedestal', 0.0, 0.0, 0.0, 0.025, 0.36, 24)
    _cyl(mb, 'tabletop', 0.0, 0.0, 0.715, 0.76, 0.87, 48)
    if r.random() < 0.75:
        _cyl(mb, 'cloth', 0.0, 0.0, 0.759, 0.77, 0.92, 48)                  # cloth top
        _cyl(mb, 'cloth', 0.0, 0.0, 0.52, 0.76, 0.915, 48, r1=0.935)        # drape
    chairs = []
    for k in range(n):
        a = k * 2 * math.pi / n + r.uniform(-0.05, 0.05)
        ca, sa = math.cos(a), math.sin(a)
        px, py = ca * 1.1, sa * 1.1
        cm = MB()
        chair_mb(cm)
        cm.emit("chair%d_%d" % (g, k), mats, parent=root, loc=(px, py, 0), rot=(0, 0, a + math.pi), smooth=False)
        # place setting
        sx, sy = ca * 0.58, sa * 0.58
        _cyl(mb, 'ceramic', sx, sy, 0.764, 0.772, 0.125, 24)
        _cyl(mb, 'ceramic', sx, sy, 0.772, 0.776, 0.07, 20)
        food = r.choice(('food0', 'food1', 'food2', 'food3'))
        if guests and r.random() < 0.8:
            mb.ellipsoid(food, (sx, sy, 0.78), (0.06, 0.05, 0.02), 1)
            mb.ellipsoid(r.choice(('food1', 'food2')), (sx + 0.02, sy - 0.02, 0.79), (0.03, 0.03, 0.015), 1)
        for sd, ln in ((-1, 0.16), (1, 0.16)):                                # fork and knife
            fx = sx + (-sa) * sd * 0.17; fy = sy + ca * sd * 0.17
            mb.box('iron', (fx, fy, 0.763), (0.012, ln, 0.004), rot_z=a + math.pi / 2 + math.pi / 2 * 0)
        gx, gy = ca * 0.62 + (-sa) * 0.15, sa * 0.62 + ca * 0.15
        mb.tube('glassware', (gx, gy, 0.762), (gx, gy, 0.86), 0.03, 0.037, 10, caps=False)
        mb.tube('wine' if r.random() < 0.5 else 'water', (gx, gy, 0.77), (gx, gy, 0.82), 0.027, 0.033, 8, caps=False)
        mb.tube('glassware', (gx, gy, 0.75), (gx, gy, 0.765), 0.012, 0.012, 6, caps=False)
        if guests:
            chairs.append((px, py, a))
    # centre of the table: flowers, bottle, bread basket, candle
    mb.tube('glassware', (0, 0, 0.762), (0, 0, 0.9), 0.045, 0.055, 12, caps=False)
    for i in range(9):
        aa = i * 0.7; rr_ = 0.035 + 0.02 * (i % 3)
        mb.blob('leaf', (math.cos(aa) * rr_, math.sin(aa) * rr_, 0.93 + 0.03 * (i % 3)), 0.04, 1)
        mb.blob(r.choice(('flower', 'flower2', 'flower')), (math.cos(aa + 1) * 0.05, math.sin(aa + 1) * 0.05, 0.99 + 0.02 * (i % 4)), 0.028, 0)
    mb.tube('bottle', (0.22, 0.12, 0.762), (0.22, 0.12, 0.98), 0.04, 0.04, 10, caps=False)
    mb.tube('bottle', (0.22, 0.12, 0.96), (0.22, 0.12, 1.04), 0.016, 0.016, 8)
    mb.ellipsoid('bread', (-0.2, -0.16, 0.8), (0.09, 0.09, 0.04), 1)
    mb.tube('bottle', (-0.22, 0.2, 0.762), (-0.22, 0.2, 0.93), 0.036, 0.036, 10, caps=False)
    mb.emit("tbl%d" % g, mats, parent=root, smooth=False)
    ppl = []
    if guests:
        for k, (px, py, a) in enumerate(chairs):
            holder = empty("seat%d_%d" % (g, k), (px, py, 0), (0, 0, a + math.pi), parent=root)
            p = seated_person("guest%d_%d" % (g, k), holder, r)
            p.location = (-0.03, 0, 0.0)
            ppl.append(holder)
    return ppl, root


def _cyl(mb, key, x, y, z0, z1, r, seg=24, r1=None):
    """vertical cylinder at (x,y) from z0 to absolute z1, top radius r, bottom radius r1"""
    b = mb.bm(key); uv = b.loops.layers.uv.verify()
    rb = r if r1 is None else r1
    lo = [b.verts.new((x + rb * math.cos(2 * math.pi * i / seg), y + rb * math.sin(2 * math.pi * i / seg), z0)) for i in range(seg)]
    hi = [b.verts.new((x + r * math.cos(2 * math.pi * i / seg), y + r * math.sin(2 * math.pi * i / seg), z1)) for i in range(seg)]
    fs = [b.faces.new((lo[i], lo[(i + 1) % seg], hi[(i + 1) % seg], hi[i])) for i in range(seg)]
    fs.append(b.faces.new(lo[::-1])); fs.append(b.faces.new(hi))
    for f in fs:
        for l in f.loops: l[uv].uv = (l.vert.co.x, l.vert.co.y) if abs(f.normal.z) > 0.9 else (math.atan2(l.vert.co.y - y, l.vert.co.x - x) * rb, l.vert.co.z)


def _animate_arm(sh_e, sy, pose, f0, f1, r, base=(0.0, 0.0, 0.0), lively=1.0):
    """arm events: rests, sips/raises, talking gestures (keyed rotation of the shoulder pivot; negative ry lifts the hand)"""
    bx, by, bz = base
    t = f0 + r.randint(0, 80)
    key_rot(sh_e, f0, base)
    while t < f1:
        kind = r.choices(('sip', 'gest', 'rest'), weights=(2, 3, 2))[0]
        if kind == 'rest':
            t += int(r.uniform(30, 90) / lively); continue
        if t > f1 - 60: break
        key_rot(sh_e, t, base)
        if kind == 'sip':
            up = r.uniform(0.9, 1.25)
            key_rot(sh_e, t + 14, (bx, by - up, bz - sy * 0.15)); key_rot(sh_e, t + 42, (bx, by - up, bz - sy * 0.15))
            key_rot(sh_e, t + 58, base); t += 58 + int(r.uniform(20, 70) / lively)
        else:
            up = r.uniform(0.35, 0.7); n = r.randint(3, 6)
            key_rot(sh_e, t + 10, (bx, by - up, bz))
            for i in range(n):
                key_rot(sh_e, t + 10 + 7 * (i + 1), (bx + sy * 0.18 * (1 if i % 2 == 0 else -1), by - up + 0.2 * (1 if i % 2 == 0 else -1), bz - sy * 0.12 * (1 if i % 2 == 0 else -1)))
            te = t + 10 + 7 * (n + 1)
            key_rot(sh_e, te + 12, base); t = te + 12 + int(r.uniform(20, 70) / lively)


def _animate_head_torso(torso_e, head_e, f0, f1, r, torso_base=(0, 0, 0), yaw_range=0.55, lively=1.0):
    ph = r.uniform(0, 6.28); sp = r.uniform(0.1, 0.2)
    tx, ty, tz = torso_base
    for f in range(f0, f1 + 1, 10):
        key_rot(torso_e, f, (tx + 0.02 * math.sin(ph + f * sp * 0.7), ty + 0.045 * math.sin(ph + f * sp), tz + 0.05 * math.sin(ph * 1.3 + f * sp * 0.5)))
    t = f0; yaw = 0.0; nod = 0.0
    key_rot(head_e, f0, (0, 0, 0))
    while t < f1:
        nyaw = r.uniform(-yaw_range, yaw_range); nnod = r.uniform(-0.08, 0.12)
        key_rot(head_e, t, (0, nod, yaw)); key_rot(head_e, t + 9, (0, nnod, nyaw))
        hold = int(r.uniform(25, 90) / lively)
        if r.random() < 0.25:                                                 # laughing / nodding: quick bobs
            for i in range(5): key_rot(head_e, t + 9 + hold // 2 + 3 * i, (0.05 * (1 if i % 2 else -1), nnod + 0.1 * (1 if i % 2 else -0.3), nyaw))
        key_rot(head_e, t + 9 + hold, (0, nnod, nyaw))
        t += 9 + hold; yaw, nod = nyaw, nnod


def animate_guests(holders, f0, f1, r):
    """lively conversation: head turns toward neighbours, nods/laughs, torso sways, arms sip / gesture"""
    for h in holders:
        for ch in h.children:
            rig = RIGS.get(ch.name)
            if not rig: continue
            _animate_head_torso(rig['torso'], rig['head'], f0, f1, r, torso_base=(0, rig['lean'] * 0.5, 0))
            for sy, sh_e, pose in rig['arms']:
                _animate_arm(sh_e, sy, pose, f0, f1, r)


def hide_until(obs, f):
    for o in obs:
        key_vis(o, 0, False); key_vis(o, f, True)


# ------------------------------------------------------------------ standing / walking people -----------------------
def _body_mats(r):
    return {'skin': r.choice(M['skin']), 'hair': r.choice(M['hair']), 'top': r.choice(M['top']), 'bottom': r.choice(M['pants']),
            'shoe': r.choice(M['shoe']), 'eye': M['eye'], 'lip': M['lip']}


def _upper_parts(r, female, mats, lean=0.0):
    """returns (torso MB, head MB, neck pivot): standing figure, origin at the feet, facing +X"""
    tb = MB(); hb = MB(); piv = (0.01, 0, 1.62)
    tb.ellipsoid('bottom', (0, 0, 0.95), (0.14, 0.18, 0.1), 2)
    if female and r.random() < 0.45:
        tb.tube('bottom', (0, 0, 0.98), (0.0, 0, 0.55), 0.2, 0.25, 12, caps=False)
    tb.ellipsoid('top', (0, 0, 1.22), (0.15, 0.2 if not female else 0.18, 0.3), 2, tilt=lean)
    tb.ellipsoid('top', (0, 0, 1.45), (0.1, 0.25 if not female else 0.22, 0.1), 2)
    tb.tube('skin', (0, 0, 1.5), piv, 0.047, 0.044)
    tb.ellipsoid('top', (0.01, 0, 1.58), (0.06, 0.07, 0.03), 1)
    _head_mesh(hb, r, female, (0.02, 0, 1.74), piv, r.uniform(-0.3, 0.3))
    return tb, hb, piv


def standing_person(prefix, r, loc, yaw, parent=None, f1=900):
    """standing figure that chats: head looks around, one arm gestures, torso sways"""
    mats = _body_mats(r); female = r.random() < 0.5
    root = empty(prefix, loc, (0, 0, yaw), parent)
    low = MB()
    for sy in (-1, 1):
        low.tube('bottom', (0, sy * 0.09, 0.92), (0.02, sy * 0.1, 0.48), 0.085, 0.065)
        low.tube('bottom', (0.02, sy * 0.1, 0.48), (0.0, sy * 0.1, 0.07), 0.062, 0.048)
        low.ellipsoid('shoe', (0.06, sy * 0.1, 0.04), (0.12, 0.05, 0.04), 1)
    low.emit(prefix + "_lo", mats, parent=root, smooth=True)
    TP = Vector((0, 0, 0.93))
    torso_e = empty(prefix + "_t", tuple(TP), parent=root)
    tb, hb, piv = _upper_parts(r, female, mats)
    tb.emit(prefix + "_tb", mats, parent=torso_e, loc=tuple(-TP), smooth=True)
    head_e = empty(prefix + "_h", (piv[0], piv[1], piv[2] - TP.z), parent=torso_e)
    hb.emit(prefix + "_hd", mats, parent=head_e, loc=(-piv[0], -piv[1], -piv[2]), smooth=True)
    arms = []
    for sy in (-1, 1):
        sh = Vector((0, sy * 0.225, 1.43)); sh_e = empty(prefix + "_s", tuple(sh - TP), parent=torso_e)
        ab = MB(); pose = r.choice(('down', 'down', 'phone', 'gest'))
        if pose == 'phone' and sy == 1: el = (0.14, sy * 0.26, 1.18); hd = (0.26, sy * 0.1, 1.4)
        elif pose == 'gest': el = (0.16, sy * 0.3, 1.2); hd = (0.32, sy * 0.22, 1.32)
        else: el = (0.0, sy * 0.28, 1.15); hd = (0.04, sy * 0.28, 0.9)
        ab.tube('top', tuple(sh), el, 0.052, 0.045); ab.tube('top' if r.random() < 0.5 else 'skin', el, hd, 0.043, 0.032)
        ab.ellipsoid('skin', (hd[0] + 0.02, hd[1], hd[2]), (0.05, 0.03, 0.03), 1)
        ab.emit(prefix + "_a", mats, parent=sh_e, loc=tuple(-sh), smooth=True)
        arms.append((sy, sh_e, pose))
    _animate_head_torso(torso_e, head_e, 0, f1, r, yaw_range=0.7, lively=1.1)
    for sy, sh_e, pose in arms:
        _animate_arm(sh_e, sy, pose, 0, f1, r, lively=1.1)
    return root


def walker(prefix, r, p0, p1, f0, f1):
    """walking figure from p0 to p1 between frames f0..f1: bobbing, counter-rotating torso, swinging legs and bent arms, head glances"""
    mats = _body_mats(r); female = r.random() < 0.5
    p0 = Vector((p0[0], p0[1], 0.0)); p1 = Vector((p1[0], p1[1], 0.0)); d = p1 - p0
    yaw = math.atan2(d.y, d.x)
    root = empty(prefix, (p0.x, p0.y, 0), (0, 0, yaw))
    TP = Vector((0, 0, 0.93))
    torso_e = empty(prefix + "_t", tuple(TP), parent=root)
    tb, hb, piv = _upper_parts(r, female, mats, lean=0.05)
    tb.emit(prefix + "_tb", mats, parent=torso_e, loc=tuple(-TP), smooth=True)
    head_e = empty(prefix + "_h", (piv[0], piv[1], piv[2] - TP.z), parent=torso_e)
    hb.emit(prefix + "_hd", mats, parent=head_e, loc=(-piv[0], -piv[1], -piv[2]), smooth=True)
    legs = []; arms = []
    for sy in (-1, 1):
        hip = empty(prefix + "_hp", (0, sy * 0.09, 0.93), parent=root)
        lm = MB()
        lm.tube('bottom', (0, 0, 0), (0.0, 0, -0.45), 0.085, 0.065); lm.tube('bottom', (0, 0, -0.45), (0.0, 0, -0.86), 0.062, 0.048)
        lm.ellipsoid('shoe', (0.05, 0, -0.9), (0.12, 0.05, 0.04), 1)
        lm.emit(prefix + "_l", mats, parent=hip, smooth=True); legs.append((sy, hip))
        sh = empty(prefix + "_s", (0, sy * 0.225, 1.43 - TP.z), parent=torso_e)
        am = MB(); long_s = r.random() < 0.5
        am.tube('top', (0, 0, 0), (0.03, sy * 0.02, -0.27), 0.052, 0.045)
        am.tube('top' if long_s else 'skin', (0.03, sy * 0.02, -0.27), (0.15, sy * 0.03, -0.5), 0.043, 0.032)
        am.ellipsoid('skin', (0.17, sy * 0.03, -0.54), (0.045, 0.03, 0.055), 1)
        am.emit(prefix + "_a", mats, parent=sh, smooth=True); arms.append((sy, sh))
    ph = r.uniform(0, 6.28); look = [r.uniform(-0.6, 0.6) for _ in range(40)]
    for f in range(f0, f1 + 1, 5):
        t = (f - f0) / (f1 - f0)
        w = 2 * math.pi * (f - f0) / 28.0 + ph
        key_loc(root, f, (p0.lerp(p1, t).x, p0.lerp(p1, t).y, 0.022 * abs(math.sin(w))))
        for sy, h in legs: h.rotation_euler = (0, 0.55 * sy * math.sin(w), 0); h.keyframe_insert('rotation_euler', frame=f)
        for sy, s_ in arms: s_.rotation_euler = (0, -0.5 * sy * math.sin(w), 0); s_.keyframe_insert('rotation_euler', frame=f)
        key_rot(torso_e, f, (0.03 * math.sin(2 * w), 0.04, 0.1 * math.sin(w)))
        key_rot(head_e, f, (0.02 * math.sin(2 * w), 0, look[((f - f0) // 60) % 40] * min(1.0, abs(math.sin((f - f0) / 60.0 * math.pi)) * 2.0) - 0.1 * math.sin(w)))
    return root
