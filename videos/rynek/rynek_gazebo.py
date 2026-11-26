"""RIVON gazebo with a FLAT roof, built from exact RIVON STEP meshes (Stopa feet, Trojak corner connectors) + 90x90 timber.
Assembly / quick disassembly / re-assembly are animated with lifecycle() spans. Plus the folding parasols the gazebos replace."""
import math, random
from mathutils import Vector, Matrix
from rynek_core import *

W = 3.0                     # post centre-to-centre
POST = 0.09                 # 90x90 timber
POST_H = 2.40
RH = 0.15                   # joist height
OVER = 0.45                 # roof overhang beyond the beam ring
_stl = {}


def build_materials_gaz():
    M['rivon'] = pbr("rivon_black", (0.012, 0.012, 0.013), rough=0.42, spec=0.55, coat=0.15, bevel=0.0012)     # RAL 9005 powder coat
    M['timber'] = pbr("timber_post", (0.8, 0.6, 0.4), tex="olive_veneer_diff_2k.jpg", tex_rough="olive_veneer_rough_2k.exr",
                      tex_bump="olive_veneer_disp_2k.png", tile=0.8, bump=0.2, rough=0.55, bevel=0.003, vary=0.1, mult=(1.0, 0.88, 0.7))
    M['joist'] = pbr("timber_joist", (0.7, 0.5, 0.3), tex="teak_veneer_diff_2k.jpg", tex_rough="teak_veneer_rough_2k.exr",
                     tex_bump="teak_veneer_disp_2k.png", tile=0.8, bump=0.15, rough=0.55, bevel=0.003, vary=0.12, mult=(0.78, 0.72, 0.64))
    M['lining'] = pbr("deck_lining", (0.7, 0.5, 0.3), tex="teak_veneer_diff_2k.jpg", tex_rough="teak_veneer_rough_2k.exr",
                      tex_bump="teak_veneer_disp_2k.png", tile=0.35, bump=0.15, rough=0.5, bevel=0.0, mult=(0.98, 0.95, 0.9))
    M['membrane'] = procedural("roof_membrane", (0.07, 0.07, 0.075), (0.11, 0.11, 0.115), scale=30, rough=0.75, bump=0.1, spec=0.3)
    M['zinc'] = pbr("zinc", (0.55, 0.57, 0.6), rough=0.35, metal=0.9, bevel=0.002, grime=0.3)
    M['fascia'] = pbr("fascia_anthracite", (0.05, 0.055, 0.06), rough=0.4, bevel=0.003, grime=0.3)
    M['canopy_a'] = parasol_fabric((0.9, 0.84, 0.68), (0.74, 0.34, 0.24))
    M['canopy_b'] = parasol_fabric((0.9, 0.86, 0.78), (0.18, 0.3, 0.42))
    M['pole'] = pbr("pole", (0.03, 0.03, 0.035), rough=0.45, metal=0.7, bevel=0.002)
    M['pweight'] = pbr("weight", (0.35, 0.34, 0.32), rough=0.9, bevel=0.01)


def parasol_fabric(c1, c2):
    m, nt, bsdf = mat_new("parasol_fabric")
    from rynek_core import _math, _mix
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Object'], sep.inputs['Vector'])
    at = _math(nt, 'ARCTAN2', sep.outputs['Y'], sep.outputs['X'])
    k = _math(nt, 'FLOOR', _math(nt, 'MULTIPLY', _math(nt, 'ADD', at, math.pi), 16.0 / (2 * math.pi)))
    f = _math(nt, 'MODULO', k, 2.0)
    col = _mix(nt, c1, c2, f)
    nt.links.new(col, bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 0.92; bsdf.inputs['Sheen Weight'].default_value = 0.6
    return m


# ------------------------------------------------------------------ RIVON connectors (exact STEP meshes) -------
def import_stl(name):
    if name in _stl: return _stl[name]
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=os.path.join(CAD, name + ".stl"))
    new = [o for o in bpy.data.objects if o not in before][0]
    me = new.data
    me.transform(Matrix.Scale(0.001, 4))             # mm -> m
    bpy.data.objects.remove(new, do_unlink=True)
    me.name = "RIVON_" + name
    me.materials.append(M['rivon'])
    for p in me.polygons: p.use_smooth = False
    me.update()
    _stl[name] = me
    return me


def stopa(loc):
    ob = new_obj("RIVON_Stopa", import_stl("Stopa"), None, (loc[0] - 0.05, loc[1] - 0.05, loc[2] + 0.002))
    return ob


def trojak(post_c, top_z, corner):
    """Trojak turned upside down (socket over the post top, arms +X/+Y), rotated 90 deg per corner"""
    ob = new_obj("RIVON_Trojak", import_stl("Trojak"), None)
    Rz = Matrix.Rotation(corner * math.pi / 2, 4, 'Z'); Rx = Matrix.Rotation(math.pi, 4, 'X')
    off = Vector((0.05, -0.05, 0.098))
    ob.matrix_world = Matrix.Translation((post_c[0], post_c[1], top_z)) @ Rz @ Matrix.Translation(-off) @ Rx
    loc = ob.matrix_world.to_translation(); rot = ob.matrix_world.to_euler()
    ob.location = loc; ob.rotation_euler = rot
    return ob


# ------------------------------------------------------------------ one long gazebo ---------------------------
# ONE continuous structure: rows of posts every 3.0 m. End columns carry Trojak corner connectors, every intermediate post
# carries a Trojnik 2D boczny (socket on the post, T above: long bar = the rail line, side arm = cross beam). Post top is at the
# same height for both connectors, so all beam axes line up (post top - 48 mm). One continuous flat roof made of 3 m cassettes.
WX = 3.0                    # column pitch (along the zone)
WY = 3.7                    # post centre-to-centre across the zone
PH = {'stopa': (0, 14, 3), 'post': (14, 22, 4), 'con': (44, 22, 4), 'beam': (70, 24, 6), 'moc': (122, 10, 0), 'raft': (130, 16, 2), 'roof': (160, 26, 0)}
LIGHTS_AT = 192


def _asm(a, s, key, i):
    off, dur, stag = PH[key]
    t_in = int(round(a + (off + i * stag) * s)); return t_in, t_in + max(5, int(round(dur * s)))


def _dis(d, key, i):
    base = {'roof': (0, 26, 0), 'beam': (16, 18, 5), 'con': (40, 18, 4), 'post': (52, 22, 4)}[key]
    t0 = d + base[0] + i * base[2]; return t0, t0 + base[1]


def trojnik(post_c, base_z, side):
    """Trojnik 2D boczny: vertical socket (CAD z -150..0, post axis at CAD (50,150)) under a horizontal T (bar along CAD Y, open ends 200 mm
    from the axis; side arm along CAD +X, open end 150 mm from the axis). The post runs up to the inner ceiling (CAD z=98).
    base_z = world z of CAD z=0. bar -> world X, arm toward +Y (side=+1) or -Y (side=-1)."""
    ob = new_obj("RIVON_Trojnik", import_stl("Trojnik"), None)
    th = -math.pi / 2 if side > 0 else math.pi / 2
    ob.matrix_world = Matrix.Translation((post_c[0], post_c[1], base_z)) @ Matrix.Rotation(th, 4, 'Z') @ Matrix.Translation((-0.05, -0.15, 0.0))
    loc = ob.matrix_world.to_translation(); rot = ob.matrix_world.to_euler()
    ob.location = loc; ob.rotation_euler = rot
    return ob


def mocowanie(xr, y_face, z_anchor, d):
    """RIVON Mocowanie belek 2 (exact STEP mesh): plate screwed flat to the inner face of the rail, channel runs into the span (direction d = +-Y),
    channel floor 98 mm below the plate top. CAD x -> world -Z, CAD z -> d, CAD y -> -d x ... (right-handed). CAD anchor (50,55,-2) = plate centre on the rail face."""
    ob = new_obj("RIVON_Mocowanie", import_stl("Mocowanie"), None)
    c = (-1.0, 0.0, 0.0) if d > 0 else (1.0, 0.0, 0.0)
    R = Matrix([[0.0, c[0], 0.0], [0.0, 0.0, d], [-1.0, 0.0, 0.0]])       # columns: cadx->-Z, cady->c, cadz->(0,d,0)
    M4 = R.to_4x4()
    ob.matrix_world = Matrix.Translation((xr, y_face, z_anchor)) @ M4 @ Matrix.Translation((-0.05, -0.055, 0.002))
    loc = ob.matrix_world.to_translation(); rot = ob.matrix_world.to_euler()
    ob.location = loc; ob.rotation_euler = rot
    return ob


def structure(x0, nbays, cy, assemblies, dismantle=None):
    """columns k=0..nbays at x0+k*WX. assemblies: list of (start, speed, stagger per column). dismantle: (start, stagger)."""
    topz = POST_H + 0.002
    arm_z = topz - 0.048
    yf, yb = cy - WY / 2, cy + WY / 2
    cols = [x0 + k * WX for k in range(nbays + 1)]

    def a_of(k, n):       # (start, speed) of column k in assembly n; an assembly may be a callable k -> (start, speed)
        if callable(assemblies[n]): return assemblies[n](k)
        a0, s, st = assemblies[n]; return a0 + k * st, s

    def bay_of(k, n):     # a bay (rails, rafters, roof) follows whichever of its two columns is built later
        A, B = a_of(k, n), a_of(k + 1, n); return A if A[0] >= B[0] else B

    def d_of(k):
        if dismantle is None: return None
        return dismantle[0] + min(k, nbays - 1) * dismantle[1] + (dismantle[1] if k == nbays else 0)

    def spans(key, i, k, off_in, bay_phase=False):
        sp = []
        for n in range(len(assemblies)):
            a, s = a_of(k, n)
            t_in, t_land = _asm(a, s, key, i)
            if dismantle is not None and n == 0:
                o0, o1 = _dis(d_of(k), key, i); sp.append((t_in, t_land, o0, o1, off_in, off_in))
            else: sp.append((t_in, t_land, None, None, off_in, off_in))
        return sp
    for k, x in enumerate(cols):
        corner = (k == 0 or k == nbays)
        for ri, (y, side) in enumerate(((yf, +1), (yb, -1))):
            i = ri
            s_ = stopa((x, y, 0))
            a, sp = a_of(k, 0); t_in, t_land = _asm(a, sp, 'stopa', i)
            lifecycle([s_], s_.location, [(t_in, t_land, None, None, (0, 0, 1.7), (0, 0, 1.7))])
            ph = POST_H
            p = box("post", (POST, POST, ph), (x, y, ph / 2 + 0.002), M['timber'])
            lifecycle([p], p.location, spans('post', i, k, (0, 0, 2.4)))
            if corner:
                ci = (0 if (k == 0 and side > 0) else 1 if (k == nbays and side > 0) else 2 if k == nbays else 3)
                c_ = trojak((x, y), topz, ci)
            else:
                c_ = trojnik((x, y), topz - 0.098, side)
            lifecycle([c_], c_.location, spans('con', i, k, (0, 0, 1.5)))
        # cross beam between front and back connector of this column (engaged in the Trojnik side arms / Trojak arms)
        ec = 0.15 if corner else 0.047
        cb = between("cross", (x, yf + ec, arm_z), (x, yb - ec, arm_z), (POST, POST), M['timber'])
        lifecycle([cb], cb.location, spans('beam', 2, k, (1.0 if k < nbays else -1.0, 0, 0.55)))
    # rails and roof cassettes per bay (timed with the column at the far end of the bay so the connectors exist first)
    for k in range(nbays):
        xa, xb = cols[k], cols[k + 1]
        for ri, y in enumerate((yf, yb)):
            e0 = 0.15 if k == 0 else 0.047; e1 = 0.15 if k == nbays - 1 else 0.047
            bm_ = between("rail", (xa + e0, y, arm_z), (xb - e1, y, arm_z), (POST, POST), M['timber'])
            side = -1.0 if ri == 0 else 1.0
            sp = []
            for n in range(len(assemblies)):
                a, s = bay_of(k, n); t_in, t_land = _asm(a, s, 'beam', 3 + ri)
                if dismantle is not None and n == 0:
                    o0, o1 = _dis(d_of(k), 'beam', ri); sp.append((t_in, t_land, o0, o1, (0, side * 0.9, 0.55), (0, side * 0.9, 0.55)))
                else: sp.append((t_in, t_land, None, None, (0, side * 0.9, 0.55), (0, side * 0.9, 0.55)))
            lifecycle([bm_], bm_.location, sp)
        rail_top = arm_z + POST / 2                      # = topz - 0.003
        cx = (xa + xb) / 2
        # --- rafters 45x98 hang between the rails in RIVON Mocowanie belek saddles, top flush with the rail top (nothing sticks out above)
        yin_f, yin_b = yf + POST / 2, yb - POST / 2
        z_anchor = rail_top - 0.050
        rlen = (yin_b - yin_f) - 0.004
        n_raf = 6
        for i in range(n_raf):
            xr = cx + (-1.25 + 0.5 * i)
            pair = []
            for ri, (yface, d) in enumerate(((yin_f, +1), (yin_b, -1))):
                mo = mocowanie(xr, yface, z_anchor, d)
                sp = []
                for n in range(len(assemblies)):
                    a_, s_ = bay_of(k, n); t_in, t_land = _asm(a_, s_, 'moc', i + ri * 0)
                    sp.append((t_in + i, t_land + i, None, None, (0, d * 0.5, 0.0), (0, d * 0.5, 0.0)))
                lifecycle([mo], mo.location, sp)
            rf = box("rafter", (0.045, rlen, 0.098), (xr, cy, rail_top - 0.049), M['joist'])
            sp = []
            for n in range(len(assemblies)):
                a_, s_ = bay_of(k, n); t_in, t_land = _asm(a_, s_, 'raft', i)
                sp.append((t_in, t_land, None, None, (0, 0, 1.3), (0, 0, 1.3)))
            lifecycle([rf], rf.location, sp)
        # --- roof cassette on top: lining deck + membrane + zinc upstands + fascia (sits directly on rails and rafters)
        zr = rail_top
        root = empty("roof%d" % k, (cx, cy, zr))
        ox0 = 0.45 if k == 0 else 0.0; ox1 = 0.45 if k == nbays - 1 else 0.0
        hyr = WY / 2 + 0.30
        lo, hi = -WX / 2 - ox0, WX / 2 + ox1; xm = (lo + hi) / 2; lx = hi - lo
        kids = []
        kids.append(box("deck", (lx, 2 * hyr, 0.022), (xm, 0, 0.011), M['lining'], parent=root))
        kids.append(box("membrane", (lx + 0.004, 2 * hyr + 0.02, 0.01), (xm, 0, 0.027), M['membrane'], parent=root, grain=False))
        for sgn in (-1, 1):
            kids.append(box("edge", (lx, 0.045, 0.098), (xm, sgn * (hyr - 0.0225), -0.049), M['joist'], parent=root))
            kids.append(box("fascia", (lx, 0.025, 0.24), (xm, sgn * (hyr + 0.0125), -0.035), M['fascia'], parent=root))
            kids.append(box("upstand", (lx, 0.03, 0.05), (xm, sgn * (hyr - 0.015), 0.057), M['zinc'], parent=root))
        if k == 0:
            kids.append(box("fascia", (0.025, 2 * hyr + 0.05, 0.24), (lo - 0.0125, 0, -0.035), M['fascia'], parent=root))
            kids.append(box("upstand", (0.03, 2 * hyr, 0.05), (lo + 0.015, 0, 0.057), M['zinc'], parent=root))
            kids.append(box("edge", (0.045, 2 * hyr, 0.098), (lo + 0.0225, 0, -0.049), M['joist'], parent=root))
        if k == nbays - 1:
            kids.append(box("fascia", (0.025, 2 * hyr + 0.05, 0.24), (hi + 0.0125, 0, -0.035), M['fascia'], parent=root))
            kids.append(box("upstand", (0.03, 2 * hyr, 0.05), (hi - 0.015, 0, 0.057), M['zinc'], parent=root))
            kids.append(box("edge", (0.045, 2 * hyr, 0.098), (hi - 0.0225, 0, -0.049), M['joist'], parent=root))
            kids.append(box("spout", (0.06, 0.12, 0.04), (hi - 0.03, -hyr + 0.06, 0.06), M['zinc'], parent=root))
        sp = []
        for n in range(len(assemblies)):
            a_, s_ = bay_of(k, n); t_in, t_land = _asm(a_, s_, 'roof', 0)
            sp.append((t_in, t_land, None, None, (0, 0, 1.8), (0, 0, 1.8)))
        lifecycle(kids, (cx, cy, zr), sp, root=root)
        # festoon bulbs and a pendant lamp for this bay
        lights = []
        for sgn in (-1, 1):
            for t in range(1, 11):
                u = t / 11.0; xx = -WX / 2 + 0.1 + (WX - 0.2) * u; sag = 0.14 * 4 * u * (1 - u)
                lights.append(ball("bulb", 0.03, (cx + xx, cy + sgn * (WY / 2 - 0.12), topz - 0.16 - sag), M['bulbmat'], seg=8, rings=6))
        lights.append(cyl("cable", 0.004, 0.5, (cx, cy, topz - 0.25), M['iron'], seg=6))
        sh = cyl("shade", 0.22, 0.14, (cx, cy, topz - 0.55), M['zinc'], seg=20, r2=0.07, cap=False); sh.rotation_euler = (math.pi, 0, 0)
        lights.append(sh); lights.append(ball("pendant_bulb", 0.05, (cx, cy, topz - 0.6), M['bulbmat'], seg=10, rings=6))
        for o in lights: key_vis(o, 0, False)
        for n in range(len(assemblies)):
            a, s = bay_of(k, n)
            for o in lights: key_vis(o, int(round(a + LIGHTS_AT * s)), True)
            if dismantle is not None and n == 0:
                for o in lights: key_vis(o, d_of(k), False)


# ------------------------------------------------------------------ parasols ------------------------------------
def parasol(cx, cy, fabric):
    R = 1.45; ztop = 2.78; zrim = 2.12
    segs = 16; rings = 5
    me = bpy.data.meshes.new("canopy"); bm = bmesh.new()
    apex = bm.verts.new((0, 0, ztop))
    grid = []
    for k in range(1, rings + 1):
        ring = []
        rr = R * k / rings
        zz = zrim + (ztop - zrim) * (1 - (k / rings) ** 2.0)
        for i in range(segs):
            a = 2 * math.pi * i / segs
            sc = 0.07 if (k == rings and i % 2 == 1) else 0.0
            ring.append(bm.verts.new((rr * math.cos(a), rr * math.sin(a), zz + sc - 0.03 * (k / rings) * (1 if i % 2 == 1 else 0))))
        grid.append(ring)
    for i in range(segs):
        bm.faces.new((apex, grid[0][(i + 1) % segs], grid[0][i]))
    for k in range(rings - 1):
        for i in range(segs):
            j = (i + 1) % segs
            bm.faces.new((grid[k][i], grid[k][j], grid[k + 1][j], grid[k + 1][i]))
    skirt = [bm.verts.new((v.co.x, v.co.y, v.co.z - 0.14)) for v in grid[-1]]
    for i in range(segs):
        j = (i + 1) % segs
        bm.faces.new((grid[-1][i], grid[-1][j], skirt[j], skirt[i]))
    bm.normal_update()
    uv = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for l in f.loops: l[uv].uv = (l.vert.co.x, l.vert.co.y)
    bm.to_mesh(me); bm.free()
    set_smooth(me)
    ob = new_obj("parasol_canopy", me, fabric, (cx, cy, 0))
    ob.shape_key_add(name="open"); clo = ob.shape_key_add(name="closed")
    for idx, v in enumerate(me.vertices):
        p = v.co.copy(); rad = math.hypot(p.x, p.y); a = math.atan2(p.y, p.x)
        newr = 0.045 + 0.05 * (rad / R)
        ang_f = 1.0 + 0.1 * math.sin(a * 8)
        newz = ztop - (rad / R) * 1.55 + (0.07 if (abs(math.sin(a * 4)) < 0.3 and rad > R * 0.95) else 0)
        clo.data[idx].co = (newr * ang_f * math.cos(a), newr * ang_f * math.sin(a), newz)
    clo.value = 0.0
    pole = cyl("pole", 0.026, 2.78, (cx, cy, 1.39), M['pole'], seg=12)
    cap = cyl("pole_cap", 0.02, 0.18, (cx, cy, 2.86), M['pole'], seg=8)
    base = cyl("pbase", 0.38, 0.07, (cx, cy, 0.035), M['pole'], seg=28)
    weight = ball("pweight", 0.2, (cx, cy, 0.1), M['pweight'], scale=(1.6, 1.6, 0.3))
    return ob, [ob, pole, cap, base, weight], clo


def animate_parasol(ob, parts, clo, f_tear, seed=0, wind=(0.0, -1.0)):
    """gale: the open parasol rocks harder and harder, leans with the wind, is ripped off its base and tumbles away out of frame.
    canopy + pole + cap fly together (pivot at the foot of the pole); base and weight stay."""
    import random as _r; rr = _r.Random(seed * 31 + 7); ph = rr.uniform(0, 6.28)
    canopy, pole, cap, base, weight = parts
    for p in (pole, cap):
        mw = p.matrix_world.copy(); p.parent = canopy; p.matrix_parent_inverse = canopy.matrix_world.inverted(); p.matrix_world = mw
    clo.value = 0.0
    x0, y0 = canopy.location.x, canopy.location.y
    wx, wy = wind
    for fr in range(0, int(f_tear) + 1, 3):
        g_ = min(1.0, fr / max(1.0, f_tear)) ** 1.4
        amp = 0.03 + 0.09 * g_; lean = 0.03 + 0.2 * g_
        rx = -wy * lean + amp * math.sin(fr * 0.71 + ph); ry = wx * lean + amp * 0.7 * math.sin(fr * 0.53 + ph * 1.7)
        key_rot(canopy, fr, (rx, ry, 0.02 * math.sin(fr * 0.3 + ph)))
        key_loc(canopy, fr, (x0, y0, 0.0))
    # ripped off: accelerate downwind, climb like a kite, tumble
    dist = rr.uniform(18, 26); climb = rr.uniform(3.5, 6.5); side = rr.uniform(-2.5, 2.5)
    spin = rr.uniform(1.5, 3.0) * rr.choice((-1, 1)); flip = rr.uniform(1.8, 2.8)
    T = 54
    for i in range(0, T + 1, 3):
        u = i / T; e = u * u * (1.3 - 0.3 * u)
        x = x0 + wx * dist * e + side * e * e + 0.25 * math.sin(i * 0.4 + ph) * u
        y = y0 + wy * dist * e
        z = climb * (u ** 1.2) + 0.15 * math.sin(i * 0.5 + ph) * u
        rx = -wy * (0.25 + flip * e); ry = wx * (0.25 + flip * e) + 0.4 * math.sin(i * 0.33 + ph) * u
        key_loc(canopy, f_tear + i, (x, y, z)); key_rot(canopy, f_tear + i, (rx, ry, spin * e))
    for p in (canopy, pole, cap):
        key_vis(p, 0, True); key_vis(p, f_tear + T + 1, False)


def wind_debris(n_leaf, n_paper, f0, f1, box, wind=(0.0, -1.0), seed=3, tables=()):
    """leaves, paper scraps and napkins carried by the gale across the frame (keyed paths with gusty turbulence)"""
    import random as _r; rr = _r.Random(seed)
    leaf_me = bpy.data.meshes.new("leaf"); bm = bmesh.new()
    pts = [(0.0, -0.045, 0), (0.03, -0.02, 0.004), (0.035, 0.015, 0.0), (0.0, 0.05, 0.003), (-0.035, 0.015, 0.0), (-0.03, -0.02, 0.004)]
    vs = [bm.verts.new(p) for p in pts]; bm.faces.new(vs); bm.to_mesh(leaf_me); bm.free()
    paper_me = bpy.data.meshes.new("paper"); bm = bmesh.new()
    vs = [bm.verts.new(p) for p in ((-0.09, -0.12, 0), (0.09, -0.12, 0.01), (0.09, 0.12, -0.01), (-0.09, 0.12, 0.012))]; bm.faces.new(vs); bm.to_mesh(paper_me); bm.free()
    nap_me = bpy.data.meshes.new("napkin"); bm = bmesh.new()
    N = 4; grid = [[bm.verts.new(((i / N - 0.5) * 0.36, (j / N - 0.5) * 0.36, 0.03 * math.sin(i * 1.4) * math.cos(j * 1.1))) for j in range(N + 1)] for i in range(N + 1)]
    for i in range(N):
        for j in range(N): bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
    bm.to_mesh(nap_me); bm.free(); set_smooth(nap_me)
    leaf_mats = [pbr("leaf_%d" % i, c, rough=0.7, bevel=0.0) for i, c in enumerate(((0.55, 0.28, 0.06), (0.7, 0.45, 0.08), (0.42, 0.2, 0.08), (0.35, 0.4, 0.1), (0.75, 0.6, 0.15)))]
    paper_m = pbr("paper_scrap", (0.85, 0.83, 0.78), rough=0.8, bevel=0.0)
    wx, wy = wind
    (xa, xb), (ya, yb) = box
    items = [('leaf', leaf_me, None) for _ in range(n_leaf)] + [('paper', paper_me, paper_m) for _ in range(n_paper)] + [('napkin', nap_me, paper_m) for _ in tables]
    for idx, (kind, me, mat) in enumerate(items):
        ob = new_obj("debris_" + kind, me, mat if mat else rr.choice(leaf_mats))
        if kind == 'napkin':
            tx, ty = tables[idx - n_leaf - n_paper]
            p0 = Vector((tx + rr.uniform(-0.4, 0.4), ty + rr.uniform(-0.4, 0.4), 0.78)); t0 = rr.randint(f0 + 15, f1 - 60); speed = rr.uniform(5, 8)
            z_lift = rr.uniform(1.0, 2.5)
            key_vis(ob, 0, True)
            key_loc(ob, 0, tuple(p0)); key_rot(ob, 0, (0, 0, rr.uniform(0, 6.28))); key_loc(ob, t0, tuple(p0))
        else:
            low = rr.random() < 0.45
            p0 = Vector((rr.uniform(xa, xb), yb - rr.uniform(0, 4), rr.uniform(0.05, 0.4) if low else rr.uniform(0.5, 4.5)))
            t0 = rr.randint(f0, f1 - 40); speed = rr.uniform(6, 11) if kind == 'leaf' else rr.uniform(5, 9); z_lift = rr.uniform(-0.3, 1.2)
            key_vis(ob, 0, False); key_vis(ob, max(1, t0 - 1), False); key_vis(ob, t0, True)
        span = int((yb - ya + 6) / speed * 30); ph = rr.uniform(0, 6.28)
        sr = (rr.uniform(4, 12), rr.uniform(4, 12), rr.uniform(2, 8))
        for i in range(0, span + 1, 3):
            s = i / 30.0
            gust = 1.0 + 0.35 * math.sin(s * 2.3 + ph)
            d = speed * s * gust
            x = p0.x + wx * d + 0.5 * math.sin(s * 3.1 + ph); y = p0.y + wy * d + 0.3 * math.sin(s * 2.6 + ph * 1.3)
            z = max(0.01, p0.z + z_lift * min(1.0, s) + 0.45 * math.sin(s * 4.0 + ph) * (0.4 if p0.z < 0.5 else 1.0))
            key_loc(ob, t0 + i, (x, y, z)); key_rot(ob, t0 + i, (sr[0] * s + ph, sr[1] * s, sr[2] * s))
        key_vis(ob, t0 + span + 1, False)
