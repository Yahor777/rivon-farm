"""Five bright daylight sets for the RIVON film (v2).  Pergola sits at the world origin (long axis = Y, posts at x +-1.7, y +-2.95,
beam/rafter top z = 2.597).  Every set has its own house, yard and use-case; the light follows the garden scene of the truck video
(saturated blue sky, hard warm sun, rich lawn).  Each builder returns dict(world, exp, car, sun=(elev, azim, W/m2, rgb))."""
import math
import numpy as np
import bpy
from film_lib import *   # noqa
import film_envs as E
import film_sets as FS
import film_props as P
from film_stage import mat_matte, _nodes

SUN_WARM = (1.0, 0.86, 0.68)


# ------------------------------------------------------------------------------------------------ sky + lawn + deck + roof
def sky_world(strength=1.0, clouds=0.5, seed=0.0):
    """Truck-video sky: saturated blue ramp by elevation (horizon pale -> zenith deep) with a few flat clouds."""
    w = bpy.data.worlds.new("sky_set"); w.use_nodes = True; nt = w.node_tree; nt.nodes.clear()
    L = nt.links.new; N = nt.nodes.new
    out = N("ShaderNodeOutputWorld"); bg = N("ShaderNodeBackground"); tc = N("ShaderNodeTexCoord"); nrm = N("ShaderNodeVectorMath"); nrm.operation = "NORMALIZE"
    sep = N("ShaderNodeSeparateXYZ"); neg = N("ShaderNodeMath"); neg.operation = "MULTIPLY"; neg.inputs[1].default_value = 1.0; cl = N("ShaderNodeClamp")
    L(tc.outputs["Generated"], nrm.inputs[0]); L(nrm.outputs[0], sep.inputs[0]); L(sep.outputs["Z"], neg.inputs[0]); L(neg.outputs[0], cl.inputs[0])
    cr = N("ShaderNodeValToRGB"); L(cl.outputs[0], cr.inputs[0])
    cr.color_ramp.elements[0].position = 0.0; cr.color_ramp.elements[0].color = (0.50, 0.70, 0.96, 1)
    e = cr.color_ramp.elements.new(0.12); e.color = (0.15, 0.40, 0.93, 1)
    cr.color_ramp.elements[2].position = 0.6; cr.color_ramp.elements[2].color = (0.035, 0.17, 0.82, 1)
    # flat cloud deck projected onto a plane above the viewer
    d = N("ShaderNodeMath"); d.operation = "ADD"; d.inputs[1].default_value = 0.22; L(cl.outputs[0], d.inputs[0])
    px = N("ShaderNodeMath"); px.operation = "DIVIDE"; py = N("ShaderNodeMath"); py.operation = "DIVIDE"
    L(sep.outputs["X"], px.inputs[0]); L(d.outputs[0], px.inputs[1]); L(sep.outputs["Y"], py.inputs[0]); L(d.outputs[0], py.inputs[1])
    cb = N("ShaderNodeCombineXYZ"); L(px.outputs[0], cb.inputs["X"]); L(py.outputs[0], cb.inputs["Y"]); cb.inputs["Z"].default_value = seed
    nz = N("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.7; nz.inputs["Detail"].default_value = 6.0; nz.inputs["Roughness"].default_value = 0.6; L(cb.outputs[0], nz.inputs["Vector"])
    mr = N("ShaderNodeMapRange"); mr.inputs[1].default_value = 0.52; mr.inputs[2].default_value = 0.72; L(nz.outputs["Fac"], mr.inputs[0])
    fade = N("ShaderNodeMapRange"); fade.inputs[1].default_value = 0.03; fade.inputs[2].default_value = 0.22; L(cl.outputs[0], fade.inputs[0])
    mul = N("ShaderNodeMath"); mul.operation = "MULTIPLY"; L(mr.outputs[0], mul.inputs[0]); L(fade.outputs[0], mul.inputs[1])
    mul2 = N("ShaderNodeMath"); mul2.operation = "MULTIPLY"; mul2.inputs[1].default_value = clouds; L(mul.outputs[0], mul2.inputs[0])
    mx = N("ShaderNodeMix"); mx.data_type = "RGBA"; mx.inputs[7].default_value = (1.0, 1.0, 1.0, 1); L(mul2.outputs[0], mx.inputs[0]); L(cr.outputs[0], mx.inputs[6])
    bg.inputs["Strength"].default_value = strength; L(mx.outputs[2], bg.inputs[0]); L(bg.outputs[0], out.inputs[0]); return w


def lawn_rich():
    def mk():
        m = bpy.data.materials.new("lawn_rich"); nt = _nodes(m); o = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(b.outputs[0], o.inputs[0])
        tc = nt.nodes.new("ShaderNodeTexCoord")
        n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 0.28; n1.inputs["Detail"].default_value = 6.0
        n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 70.0; n2.inputs["Detail"].default_value = 4.0
        for n in (n1, n2): nt.links.new(tc.outputs["Object"], n.inputs[0])
        mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "FLOAT"; mx.inputs[0].default_value = 0.3; nt.links.new(n1.outputs["Fac"], mx.inputs[2]); nt.links.new(n2.outputs["Fac"], mx.inputs[3])
        cr = nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].position = 0.3; cr.color_ramp.elements[1].position = 0.7
        cr.color_ramp.elements[0].color = (0.022, 0.075, 0.008, 1); cr.color_ramp.elements[1].color = (0.075, 0.2, 0.022, 1)
        nt.links.new(mx.outputs[0], cr.inputs[0]); nt.links.new(cr.outputs[0], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.9
        bm = nt.nodes.new("ShaderNodeBump"); bm.inputs["Strength"].default_value = 0.8; bm.inputs["Distance"].default_value = 0.04
        nt.links.new(n2.outputs["Fac"], bm.inputs["Height"]); nt.links.new(bm.outputs[0], b.inputs["Normal"])
        return m
    return FS.cached("lawn_rich", mk)


def blade_mat():
    def mk():
        m = bpy.data.materials.new("blade"); nt = _nodes(m); o = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(b.outputs[0], o.inputs[0])
        tc = nt.nodes.new("ShaderNodeTexCoord"); sp = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sp.inputs[0])
        nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.6; nz.inputs["Detail"].default_value = 3.0; nt.links.new(tc.outputs["Object"], nz.inputs[0])
        h = nt.nodes.new("ShaderNodeMapRange"); h.inputs[1].default_value = 0.0; h.inputs[2].default_value = 0.12; nt.links.new(sp.outputs["Z"], h.inputs[0])
        cr = nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (0.018, 0.065, 0.006, 1); cr.color_ramp.elements[1].color = (0.16, 0.34, 0.035, 1)
        mix = nt.nodes.new("ShaderNodeMath"); mix.operation = "ADD"; nt.links.new(h.outputs[0], mix.inputs[0]); nt.links.new(nz.outputs["Fac"], mix.inputs[1])
        sc_ = nt.nodes.new("ShaderNodeMath"); sc_.operation = "MULTIPLY"; sc_.inputs[1].default_value = 0.6; nt.links.new(mix.outputs[0], sc_.inputs[0])
        nt.links.new(sc_.outputs[0], cr.inputs[0]); nt.links.new(cr.outputs[0], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.55
        b.inputs["Subsurface Weight"].default_value = 0.0
        return m
    return FS.cached("blade", mk)


def grass(coll, cx, cy, hx, hy, n, seed=1, excl=(), hmin=0.05, hmax=0.13):
    """Thousands of single-triangle blades (one merged mesh) so that the lawn shows real grass in the foreground."""
    rng = np.random.default_rng(seed)
    pts = rng.uniform([-hx, -hy], [hx, hy], (int(n * 1.5), 2)) + np.array([cx, cy])
    keep = np.ones(len(pts), bool)
    for (x0, x1, y0, y1) in excl: keep &= ~((pts[:, 0] > x0) & (pts[:, 0] < x1) & (pts[:, 1] > y0) & (pts[:, 1] < y1))
    pts = pts[keep][:n]; m = len(pts)
    h = rng.uniform(hmin, hmax, m); a = rng.uniform(0, 2 * math.pi, m); la = rng.uniform(0, 2 * math.pi, m); lean = rng.uniform(0.1, 0.8, m) * h
    w = 0.0055
    V = np.zeros((m, 3, 3))
    V[:, 0, 0] = pts[:, 0] - w * np.sin(a); V[:, 0, 1] = pts[:, 1] + w * np.cos(a)
    V[:, 1, 0] = pts[:, 0] + w * np.sin(a); V[:, 1, 1] = pts[:, 1] - w * np.cos(a)
    V[:, 2, 0] = pts[:, 0] + lean * np.cos(la); V[:, 2, 1] = pts[:, 1] + lean * np.sin(la); V[:, 2, 2] = h
    F = np.arange(3 * m).reshape(m, 3)
    me = mesh_from_arrays("grass_blades", V.reshape(-1, 3), F, False); me.materials.append(blade_mat())
    ob = bpy.data.objects.new("grass_blades", me); link(ob, coll); return ob


def deck_mat(tint=1.0, key="deck"):
    def mk():
        m = bpy.data.materials.new(key); nt = _nodes(m); o = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(b.outputs[0], o.inputs[0])
        tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1.3, 70.0, 6.0); nt.links.new(tc.outputs["Object"], mp.inputs[0])
        nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.0; nz.inputs["Detail"].default_value = 5.0; nz.inputs["Roughness"].default_value = 0.65; nt.links.new(mp.outputs[0], nz.inputs[0])
        cr = nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].position = 0.35; cr.color_ramp.elements[1].position = 0.65
        cr.color_ramp.elements[0].color = (0.10 * tint, 0.052 * tint, 0.024 * tint, 1); cr.color_ramp.elements[1].color = (0.22 * tint, 0.12 * tint, 0.055 * tint, 1)
        nt.links.new(nz.outputs["Fac"], cr.inputs[0]); nt.links.new(cr.outputs[0], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.5
        bm = nt.nodes.new("ShaderNodeBump"); bm.inputs["Strength"].default_value = 0.5; bm.inputs["Distance"].default_value = 0.004; nt.links.new(nz.outputs["Fac"], bm.inputs["Height"]); nt.links.new(bm.outputs[0], b.inputs["Normal"])
        return m
    return FS.cached(key, mk)


def deck(coll, x0, x1, y0, y1, seed=3, bw=0.145, gap=0.007, z=0.0):
    """Composite/teak decking: boards run along x, random staggered lengths, dark gap base underneath (real board gaps)."""
    rng = np.random.default_rng(seed)
    FS._pad(coll, f"deck_base_{seed}", (x1 - x0, y1 - y0), ((x0 + x1) / 2, (y0 + y1) / 2), mat_matte("deck_gap", (0.01, 0.008, 0.006, 1), 1.0), z - 0.0)
    groups = [[] for _ in range(4)]; nrow = int((y1 - y0) / (bw + gap))
    for r in range(nrow):
        yc = y0 + (r + 0.5) * (bw + gap); x = x0 - rng.uniform(0, 2.2)
        while x < x1:
            L = rng.uniform(1.8, 3.2); xa, xb = max(x, x0), min(x + L - 0.01, x1)
            if xb - xa > 0.05: groups[rng.integers(0, 4)].append(FS.box_part(((xa + xb) / 2, yc, z + 0.015), (xb - xa, bw, 0.03)))
            x += L
    for i, g in enumerate(groups):
        if g: FS.merged(f"deck_{seed}_{i}", g, deck_mat(0.8 + 0.12 * i, f"deck{i}"), coll, False)


def pergola_roof(coll, color=(0.045, 0.047, 0.052), rough=0.45, ribs=True, over=0.38, name="roof"):
    """Standing-seam metal sheets lying on top of beams/rafters (z 2.600); lives in the set, the pergola itself is untouched."""
    g = P.G(coll, name, bevel=0.004); mat = simple(f"{name}_sheet", (*color, 1), rough, 0.55, 0.5)
    g.box((0, 0, 2.620), (3.494 + 2 * over, 5.994 + 2 * over, 0.04), mat)
    if ribs:
        for x in np.arange(-1.7 - over + 0.25, 1.7 + over - 0.1, 0.42): g.box((x, 0, 2.652), (0.035, 5.994 + 2 * over, 0.028), mat)
    g.box((0, -(2.997 + over), 2.60), (3.494 + 2 * over, 0.05, 0.1), mat); g.box((0, 2.997 + over, 2.60), (3.494 + 2 * over, 0.05, 0.1), mat)
    g.flush()


def shrubs(coll, pts, seed=0, h=0.7, r=0.5, flowers=None):
    """Clumps of low foliage (many small noisy blobs) with optional blossoms."""
    g = P.G(coll, f"shrubs_{seed}"); rng = np.random.default_rng(abs(int(seed)))
    for i, (x, y) in enumerate(pts):
        for k in range(7):
            a = rng.uniform(0, 6.28); rr = rng.uniform(0, r * 0.7)
            g.blob((x + rr * math.cos(a), y + rr * math.sin(a), h * 0.26 + rng.uniform(-.02, .12) * h), r * rng.uniform(.32, .5), "leaf", seed * 100 + i * 7 + k, (1, 1, h / r * 0.6), 0.22)
        if flowers:
            for k in range(26):
                a = rng.uniform(0, 6.28); rr = rng.uniform(0.0, r * .85); g.blob((x + rr * math.cos(a), y + rr * math.sin(a), h * 0.55 + rng.uniform(0, h * .3)), 0.035, flowers, seed + k, (1, 1, 0.8), 0.2)
    g.flush()


def _horizon(coll, seed, n=70, r0=55, r1=95, kind="broad"): return FS._horizon(coll, seed, n, r0, r1, kind)
_pad = FS._pad


def base_ground(coll, mat=None, blades=(0, 0, 9, 9, 120000, 1), excl=()):
    FS.ground(coll, mat or lawn_rich())
    if blades: grass(coll, blades[0], blades[1], blades[2], blades[3], blades[4], blades[5], excl)


# ================================================================================================ 1 CARPORT (house without garage, car under the pergola by the driveway)
def set_carport(coll):
    excl = [(-3.2, 3.2, -25, 3.8), (-8, -3.2, -1.3, 0.3), (-17, -7.5, -6, 10)]
    base_ground(coll, blades=(-2, 2, 9.5, 10.5, 150000, 11), excl=excl)
    _horizon(coll, 11)
    drive = FS.paving((0.5, 0.5, 0.52), 0.55, "drive")
    _pad(coll, "driveway", (6.4, 28.0), (0, -10.2), drive, 0.0)
    _pad(coll, "path", (4.8, 1.5), (-5.6, -0.5), FS.paving((0.55, 0.53, 0.5), 0.6, "pathst"), 0.0)
    box("kerb_l", (0.14, 28.0, 0.1), (-3.27, -10.2, 0.05), mat_matte("kerb", (0.6, 0.6, 0.6, 1), 0.8), coll, 0, 0.01); box("kerb_r", (0.14, 28.0, 0.1), (3.27, -10.2, 0.05), mat_matte("kerb", (0.6, 0.6, 0.6, 1), 0.8), coll, 0, 0.01)
    _pad(coll, "road", (240, 9.0), (0, -28.5), FS.asphalt(), -0.05); _pad(coll, "pavement", (240, 2.4), (0, -22.6), FS.paving((0.62, 0.6, 0.57), 0.6, "pave"), 0.0)
    FS.house_modern(coll, (-12.3, 1.5), 90, "villa", cladding=(0.5, 0.36, 0.25), plaster_col=(0.92, 0.91, 0.88), garage=False)
    shrubs(coll, [(-7.0, y) for y in (-3.4, -2.3, 1.8, 2.9, 4.0, 5.1)], 1, 0.75, 0.45, "pink")
    shrubs(coll, [(-7.0, y) for y in (-1.6, 0.6)], 2, 0.5, 0.35, "yellow")
    FS.slat_fence(coll, (12.5, -22), (12.5, 10), 1.8, (0.58, 0.42, 0.28), "fenceR"); FS.hedge(coll, (-7.5, 10.0), (12.5, 10.0), 2.0, 1.1)
    FS.slat_fence(coll, (-7.5, -22), (-7.5, -9), 1.6, (0.58, 0.42, 0.28), "fenceL")
    bases = FS.tree_meshes(coll, 21, "broad", 2)
    for p, s in (((-9.5, 12.5), 1.0), ((11.0, 5.0), 0.95), ((19.0, -12.0), 0.9), ((-3.0, 17.0), 1.1), ((16, 12), 1.2), ((-20, -8), 1.2), ((3.5, 13), 0.9)): FS.place_tree(coll, bases, (p[0], p[1], 0), p[0], s)
    for p in ((-8, -26.0), (19, -19.5)): FS.place_tree(coll, bases, (p[0], p[1], 0), 1.0, 0.7)
    shrubs(coll, [(4.6, -2.6), (4.9, -3.6)], 7, 0.45, 0.4, "violet")
    g = P.G(coll, "carport_props", bevel=0.01)
    for y in (-4.0, -8.0, -12.0, -16.0):       # driveway bollard lights
        for x in (-3.0, 3.0): g.cyl((x, y, 0.3), 0.04, 0.6, "blacksteel", 10); g.cyl((x, y, 0.62), 0.05, 0.06, "lantern", 10)
    g.box((5.6, 6.0, 0.55), (0.62, 0.62, 1.1), "graphite"); g.box((5.6, 6.0, 1.12), (0.66, 0.66, 0.05), "charcoal")      # wheelie bin
    P.potted(g, -7.3, -1.0, 0.7, 0.45, "tall", 5); P.potted(g, -7.3, 0.0, 0.7, 0.45, "tall", 6)
    g.flush()
    pergola_roof(coll, (0.30, 0.31, 0.33), 0.5)
    cyl("lamp_pole", 0.07, 6.0, (-12, -21.4, 3.0), mat_matte("pole", (0.1, 0.1, 0.11, 1), 0.4), coll, 12)
    return dict(world=sky_world(1.6, 0.45, 1.0), exp=0.35, car=True, sun=(44, -28, 7.6, SUN_WARM))


def set_yard(coll):
    """carport yard laid out for a 360-degree orbit (camera radius ~9.5 m): nothing taller than 1.2 m inside r = 10.5 m.
    The pergola keeps its own assembled roof (profiled sheets) - no extra roof here."""
    excl = [(-3.2, 3.2, -25, 3.8), (-12.6, -3.2, -1.3, 0.3), (-22.5, -12.6, -6, 10)]
    base_ground(coll, blades=(-2, 2, 9.5, 10.5, 150000, 11), excl=excl)
    _horizon(coll, 11)
    drive = FS.paving((0.5, 0.5, 0.52), 0.55, "drive")
    _pad(coll, "driveway", (6.4, 28.0), (0, -10.2), drive, 0.0)
    _pad(coll, "path", (9.4, 1.5), (-7.9, -0.5), FS.paving((0.55, 0.53, 0.5), 0.6, "pathst"), 0.0)
    box("kerb_l", (0.14, 28.0, 0.1), (-3.27, -10.2, 0.05), mat_matte("kerb", (0.6, 0.6, 0.6, 1), 0.8), coll, 0, 0.01); box("kerb_r", (0.14, 28.0, 0.1), (3.27, -10.2, 0.05), mat_matte("kerb", (0.6, 0.6, 0.6, 1), 0.8), coll, 0, 0.01)
    _pad(coll, "road", (240, 9.0), (0, -28.5), FS.asphalt(), -0.05); _pad(coll, "pavement", (240, 2.4), (0, -22.6), FS.paving((0.62, 0.6, 0.57), 0.6, "pave"), 0.0)
    FS.house_modern(coll, (-17.5, 1.5), 90, "villa", cladding=(0.5, 0.36, 0.25), plaster_col=(0.92, 0.91, 0.88), garage=False)
    shrubs(coll, [(-12.2, y) for y in (-3.4, -2.3, 1.8, 2.9, 4.0, 5.1)], 1, 0.75, 0.45, "pink")
    shrubs(coll, [(-12.2, y) for y in (-1.6, 0.6)], 2, 0.5, 0.35, "yellow")
    FS.slat_fence(coll, (14.0, -22), (14.0, 13), 1.8, (0.58, 0.42, 0.28), "fenceR"); FS.hedge(coll, (-12.0, 13.0), (14.0, 13.0), 2.0, 1.1)
    FS.slat_fence(coll, (-12.0, -22), (-12.0, -9), 1.6, (0.58, 0.42, 0.28), "fenceL")
    bases = FS.tree_meshes(coll, 21, "broad", 2)
    for p, s in (((-10.5, 15.5), 1.0), ((16.5, 5.0), 0.95), ((19.0, -12.0), 0.9), ((-3.0, 18.5), 1.1), ((17, 15), 1.2), ((-20, -10), 1.2), ((4.5, 16.5), 0.9)): FS.place_tree(coll, bases, (p[0], p[1], 0), p[0], s)
    for p in ((-8, -26.0), (19, -19.5)): FS.place_tree(coll, bases, (p[0], p[1], 0), 1.0, 0.7)
    shrubs(coll, [(5.6, -2.6), (5.9, -3.6)], 7, 0.45, 0.4, "violet")
    g = P.G(coll, "carport_props", bevel=0.01)
    for y in (-4.0, -8.0, -12.0, -16.0):       # driveway bollard lights
        for x in (-3.0, 3.0): g.cyl((x, y, 0.3), 0.04, 0.6, "blacksteel", 10); g.cyl((x, y, 0.62), 0.05, 0.06, "lantern", 10)
    g.box((5.6, 6.0, 0.55), (0.62, 0.62, 1.1), "graphite"); g.box((5.6, 6.0, 1.12), (0.66, 0.66, 0.05), "charcoal")      # wheelie bin
    P.potted(g, -12.5, -1.0, 0.7, 0.45, "tall", 5); P.potted(g, -12.5, 0.0, 0.7, 0.45, "tall", 6)
    g.flush()
    cyl("lamp_pole", 0.07, 6.0, (-12, -21.4, 3.0), mat_matte("pole", (0.1, 0.1, 0.11, 1), 0.4), coll, 12)
    return dict(world=sky_world(2.4, 0.35, 1.0), exp=0.6, car=True, sun=(50, -38, 9.5, (1.0, 0.9, 0.76)))   # bright sunny noon, sun on the camera side for most of the orbit



# ================================================================================================ 2 BARBECUE (garden party: dining table, small kitchen, mangal, fire pit)
def set_barbecue(coll):
    excl = [(-4.8, 4.8, -4.6, 5.6), (-11, 11, 9.5, 20)]
    base_ground(coll, blades=(0, 2, 11, 11, 150000, 12), excl=excl)
    _horizon(coll, 12)
    _pad(coll, "patio", (9.4, 10.0), (0, 0.5), FS.paving((0.6, 0.57, 0.5), 0.6, "patio"), 0.0)
    FS.house_traditional(coll, (0.0, 17.0), 0, (0.93, 0.9, 0.84), (0.22, 0.2, 0.21), 10.5, 8.4, 2, 40, key="farm")
    _pad(coll, "walk", (1.5, 5.0), (0, 8.5), FS.paving((0.55, 0.52, 0.46), 0.6, "patio"), 0.0)
    FS.slat_fence(coll, (-10.5, -14), (-10.5, 12.0), 1.75, (0.5, 0.36, 0.24), "fL"); FS.slat_fence(coll, (10.5, -14), (10.5, 12.0), 1.75, (0.5, 0.36, 0.24), "fR")
    bases = FS.tree_meshes(coll, 22, "broad", 3)
    for p, s in (((-8.0, 7.0), 0.7), ((8.5, 6.5), 0.7), ((13.5, 9), 1.1), ((-13, 7), 1.15), ((0, 28), 1.2), ((-16, -9), 1.2)): FS.place_tree(coll, bases, (p[0], p[1], 0), p[0] * 2.0, s)
    for k in range(3):
        box(f"bed{k}", (2.2, 0.9, 0.38), (8.0, -4.0 + k * 1.4, 0.19), FS.timber((0.5, 0.35, 0.22), 1.0, "bedw"), coll, 0, 0.01)
        box(f"soil{k}", (2.1, 0.8, 0.02), (8.0, -4.0 + k * 1.4, 0.37), mat_matte("soil", (0.025, 0.018, 0.012, 1), 1.0), coll, 0, 0)
    g = P.G(coll, "bbq_props", bevel=0.006)
    # dining table under the pergola: 3 chairs a side + one at each end
    P.trestle_table(g, 0, -0.1, 3.0, 0.95, 0.76, "y", "teak")
    for i, y in enumerate((-1.1, -0.1, 0.9)):
        P.dining_chair(g, -0.78, y, -math.pi / 2); P.dining_chair(g, 0.78, y, math.pi / 2)
    P.dining_chair(g, 0, -1.9, 0.0); P.dining_chair(g, 0, 1.7, math.pi)
    for y in (-1.1, -0.1, 0.9):
        for sx in (-0.3, 0.3): P.plate(g, sx, y, 0.785)
        P.glass_(g, -0.18, y + 0.14, 0.785); P.glass_(g, 0.18, y - 0.14, 0.785)
    P.bowl(g, 0.0, 0.5, 0.785, 0.17, "leaf", 1); P.bowl(g, 0.0, -0.7, 0.785, 0.15, "lemon", 2); P.bottle(g, 0.1, -0.2, 0.785); P.bottle(g, -0.08, 0.1, 0.785)
    g.box((0, 0.1, 0.795), (0.4, 0.22, 0.02), "wood_light"); g.box((0.02, 0.12, 0.815), (0.3, 0.12, 0.025), "bread")
    g.flush()
    # small kitchen beside the pergola (+x side), fronts facing the table
    k = P.G(coll, "bbq_kitchen", loc=(2.62, 0.0, 0.0), rot=math.pi / 2, bevel=0.006)
    P.kitchen_run(k, -2.4, 0, 4.8)
    P.sink_unit(k, -1.5, 0); P.hob_unit(k, -0.15, 0); P.grill_unit(k, 1.0, 0); P.fridge(k, 2.75, 0)
    k.box((0, -0.34, 1.25), (4.8, 0.1, 1.1), "stone_dark")
    for i in range(5): k.box((-1.9 + i * 0.35, 0.1, 0.92), (0.1, 0.1, 0.07), "terra") if i < 3 else k.cyl((-1.9 + i * 0.35, 0.1, 0.92), 0.05, 0.08, "steel", 12)
    k.flush()
    # fire pit with four chairs + mangal + kettle grill
    f = P.G(coll, "bbq_fire", bevel=0.006)
    P.fire_pit(f, -4.1, -0.4)
    for ang in (100, 165, 235, 305): a = math.radians(ang); P.adirondack(f, -4.1 + 1.55 * math.cos(a), -0.4 + 1.55 * math.sin(a), a + math.pi / 2)
    P.mangal(f, 3.9, -3.3, 0.0); P.kettle_grill(f, 5.0, -2.6)
    f.box((3.9, -4.1, 0.37), (0.9, 0.5, 0.74), "oak"); P.plate(f, 3.7, -4.1, 0.745, 0.15); P.bowl(f, 4.1, -4.1, 0.745, 0.14, "meat", 3)
    P.potted(f, 1.95, -3.2, 0.55, 0.5, "shrub", 4)
    f.flush()
    shrubs(coll, [(-3.2, -3.8), (-2.6, -4.3)], 9, 0.45, 0.4, "yellow")
    E.string_lights(coll, 3)
    return dict(world=sky_world(1.0, 0.5, 4.0), exp=0.15, car=False, sun=(40, 250, 7.2, SUN_WARM))



# ================================================================================================ 3 SUMMER KITCHEN (roofed kitchen + dining, yard entertainment next to it)
def set_kitchen(coll):
    excl = [(-3.3, 9.7, -4.5, 4.5)]
    base_ground(coll, blades=(-1, 0, 11, 11, 150000, 13), excl=excl)
    _horizon(coll, 13, 60)
    _pad(coll, "terrace", (13.0, 9.0), (3.2, 0.0), FS.paving((0.66, 0.58, 0.46), 0.7, "limestone"), 0.0)
    FS.house_traditional(coll, (13.8, 0.0), -90, (0.95, 0.88, 0.72), (0.52, 0.22, 0.13), 10.5, 8.4, 2, 30, shutters=(0.1, 0.3, 0.22), key="stucco")
    box("wall_low", (0.4, 9.0, 0.7), (-3.55, 0.0, 0.35), FS.paving((0.6, 0.55, 0.48), 0.8, "stonewall"), coll, 0, 0.02)
    cyp = FS.tree_meshes(coll, 31, "columnar", 3)
    for p, s in (((9.0, 6.2), 0.75), ((9.0, -6.4), 0.7), ((-9.0, 8.0), 0.65), ((-10.0, -8.0), 0.7)): FS.place_tree(coll, cyp, (p[0], p[1], 0), p[0], s)
    bases = FS.tree_meshes(coll, 32, "broad", 2)
    for p, s in (((-9, -11), 0.75), ((-8.5, 14.0), 0.8), ((12, 16), 1.1), ((10, -17), 1.1), ((-16, 2), 1.3), ((0, 20), 1.0)): FS.place_tree(coll, bases, (p[0], p[1], 0), p[0], s)
    FS.slat_fence(coll, (-12, -12), (-12, 14), 1.8, (0.55, 0.42, 0.3), "fK")
    pergola_roof(coll, (0.42, 0.17, 0.1), 0.5, True)
    shrubs(coll, [(-2.4, -4.6), (-1.6, -4.9)], 11, 0.45, 0.4, "violet")
    g = P.G(coll, "kit_props", bevel=0.006)
    # kitchen run along the back end of the pergola (front faces -y toward the table)
    k = P.G(coll, "kit_run", loc=(0.0, 2.47, 0.0), rot=math.pi, bevel=0.006)
    P.kitchen_run(k, -1.6, 0, 3.2, cab="cream", top="stone_dark"); P.sink_unit(k, -1.0, 0); P.hob_unit(k, -0.15, 0); P.grill_unit(k, 0.95, 0)
    k.box((0, -0.33, 1.25), (3.3, 0.06, 1.0), "white")
    k.box((0, -0.18, 1.62), (3.2, 0.24, 0.04), "oak")
    for i in range(6): k.cyl((-1.3 + i * 0.5, -0.2, 1.7), 0.045, 0.14, "ceramic", 12)
    for i in range(3): P.potted(k, -1.0 + i * 0.45, -0.2, 0.0, 0.0, "shrub", i) if False else k.blob((-0.7 + i * 0.5, -0.2, 1.74), 0.08, "leaf", i, (1, 1, 0.9), 0.3)
    k.flush()
    # dining table + 6 chairs, laid for lunch
    P.trestle_table(g, 0, -0.9, 2.4, 0.9, 0.76, "y", "teak")
    for y in (-1.7, -0.9, -0.1): P.dining_chair(g, -0.76, y, -math.pi / 2, "wood_white"); P.dining_chair(g, 0.76, y, math.pi / 2, "wood_white")
    for y in (-1.7, -0.9, -0.1):
        for sx in (-0.3, 0.3): P.plate(g, sx, y, 0.785)
        P.glass_(g, -0.12, y + 0.14, 0.785); P.glass_(g, 0.12, y - 0.14, 0.785)
    P.bowl(g, 0.0, -0.4, 0.785, 0.18, "lemon", 5); P.bowl(g, 0.0, -1.4, 0.785, 0.17, "leaf", 6); P.bottle(g, 0.08, -0.9, 0.785); P.bottle(g, -0.08, -0.65, 0.785, 0.3, "white")
    # pizza oven outside the +x beam, opening faces the table
    o = P.G(coll, "kit_oven", loc=(3.0, 0.6, 0.0), rot=math.pi / 2, bevel=0.006); P.pizza_oven(o, 0, 0); o.flush()
    # yard entertainment on the lawn beside the terrace: volleyball net, trampoline, sunbeds
    e = P.G(coll, "kit_fun", bevel=0.006)
    P.volleyball_net(e, -2.0, 9.5, 6.0, 0.0); e.cyl((-1.0, 8.2, 0.11), 0.11, 0.22, "ball", 14)
    P.trampoline(e, -6.4, 2.8, 1.5)
    P.sunbed(e, -6.2, -0.6, 0.15); P.sunbed(e, -5.2, -0.8, 0.0)
    P.potted(e, -3.55, 3.8, 0.7, 0.5, "tall", 1); P.potted(e, -3.55, -3.8, 0.7, 0.5, "tall", 2); P.potted(e, -2.0, -3.2, 0.6, 0.5, "olive", 3)
    e.flush(); g.flush()
    E.string_lights(coll, 3)
    return dict(world=sky_world(1.0, 0.5, 8.0), exp=0.15, car=False, sun=(50, 300, 7.2, SUN_WARM))


# ================================================================================================ 4 LOUNGE (roofed pergola on a timber deck by the pool)
def set_lounge(coll):
    excl = [(-11.5, 11.5, -9.5, 20)]
    base_ground(coll, blades=(0, 6, 15, 15, 120000, 14), excl=excl)
    _horizon(coll, 14, 60)
    deck(coll, -11, 11, -9, 7, 3)
    deck(coll, -11, -4.0, 7, 16.4, 4); deck(coll, 4.0, 11, 7, 16.4, 5)
    _pad(coll, "patio_back", (22, 3.2), (0, 18.0), FS.paving((0.72, 0.7, 0.66), 0.7, "travertine"), 0.0)
    tile = mat_matte("pool_tile", (0.28, 0.5, 0.58, 1), 0.3)
    box("pool_floor", (7.0, 9.0, 0.1), (0, 11.7, -1.4), tile, coll, 0, 0)
    for nme, size, loc in (("pw1", (0.1, 9.0, 1.4), (-3.5, 11.7, -0.7)), ("pw2", (0.1, 9.0, 1.4), (3.5, 11.7, -0.7)), ("pw3", (7.0, 0.1, 1.4), (0, 7.2, -0.7)), ("pw4", (7.0, 0.1, 1.4), (0, 16.2, -0.7))): box(nme, size, loc, tile, coll, 0, 0)
    def water():
        m = bpy.data.materials.new("pool_water"); nt = _nodes(m); o = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(b.outputs[0], o.inputs[0])
        b.inputs["Base Color"].default_value = (0.35, 0.8, 0.9, 1); b.inputs["Roughness"].default_value = 0.02; b.inputs["Transmission Weight"].default_value = 0.92; b.inputs["IOR"].default_value = 1.33
        tc = nt.nodes.new("ShaderNodeTexCoord"); n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 3.0; n.inputs["Detail"].default_value = 3.0; nt.links.new(tc.outputs["Object"], n.inputs[0])
        bm = nt.nodes.new("ShaderNodeBump"); bm.inputs["Strength"].default_value = 0.06; bm.inputs["Distance"].default_value = 0.02; nt.links.new(n.outputs["Fac"], bm.inputs["Height"]); nt.links.new(bm.outputs[0], b.inputs["Normal"])
        return m
    box("pool_water", (6.9, 8.9, 0.02), (0, 11.7, -0.12), FS.cached("water2", water), coll, 0, 0)
    cop = mat_matte("coping", (0.85, 0.85, 0.83, 1), 0.5)
    for nme, size, loc in (("cp1", (0.45, 9.9, 0.06), (-3.72, 11.7, 0.03)), ("cp2", (0.45, 9.9, 0.06), (3.72, 11.7, 0.03)), ("cp3", (7.9, 0.45, 0.06), (0, 6.98, 0.03)), ("cp4", (7.9, 0.45, 0.06), (0, 16.42, 0.03))): box(nme, size, loc, cop, coll, 0, 0.01)
    FS.house_modern(coll, (0.0, 24.0), 0, "villa2", cladding=(0.5, 0.38, 0.27), plaster_col=(0.86, 0.86, 0.84), garage=False)
    bases = FS.tree_meshes(coll, 41, "broad", 3)
    for p, s in (((-12.5, 4.0), 0.8), ((12.5, 8.0), 0.85), ((-13, 14), 0.9), ((13.5, 17), 1.0), ((-6, 33), 1.4), ((10, 31), 1.4), ((-17, -4), 1.1)): FS.place_tree(coll, bases, (p[0], p[1], 0), p[0], s)
    FS.slat_fence(coll, (-12.5, -9.5), (-12.5, 18), 1.9, (0.4, 0.3, 0.22), "fL"); FS.slat_fence(coll, (12.5, -9.5), (12.5, 18), 1.9, (0.4, 0.3, 0.22), "fR")
    pergola_roof(coll, (0.78, 0.76, 0.7), 0.5, True)
    g = P.G(coll, "lng_props", bevel=0.01)
    P.potted(g, 3.4, -3.2, 0.75, 0.6, "tall", 21); P.potted(g, 4.3, -2.2, 0.6, 0.5, "olive", 22); P.potted(g, 2.4, -3.6, 0.5, 0.45, "shrub", 23)
    g.box((0.1, 0.55, 0.008), (2.7, 3.5, 0.016), "cream" if False else "lgrey")   # rug
    P.sofa(g, -1.2, 0.55, 3, -math.pi / 2, "cream", "graphite", ("terra", "teal", "mustard"))
    P.armchair(g, 1.15, 1.7, math.pi / 2, "cream"); P.armchair(g, 1.15, -0.55, math.pi / 2, "cream")
    P.coffee_table(g, -0.05, 0.55, 0.7, 1.1, 0.4); g.cyl((-0.05, 0.5, 0.48), 0.1, 0.1, "ceramic", 16); g.blob((-0.05, 0.5, 0.58), 0.1, "leaf", 4, (1, 1, 1), 0.3); g.box((0.0, 0.85, 0.44), (0.28, 0.2, 0.03), "red"); g.box((0.0, 0.2, 0.44), (0.28, 0.2, 0.03), "mustard")
    P.round_table(g, 1.2, 0.58, 0.28, 0.5); g.cyl((1.2, 0.58, 0.64), 0.07, 0.14, "lantern", 12)
    g.cyl((-1.9, 2.3, 0.85), 0.012, 1.7, "blacksteel", 8); g.ell((-1.9, 2.3, 1.72), 0.2, "lantern", (1, 1, 0.8), 14, 6)          # floor lamp
    P.potted(g, 1.4, 2.35, 0.7, 0.55, "tall", 1); P.potted(g, -1.4, -2.4, 0.7, 0.55, "olive", 2); P.potted(g, 1.4, -2.4, 0.6, 0.5, "shrub", 3)
    # sunbeds + parasol on the pool deck, planters
    for x, y, r in ((-6.8, 9.4, 0.08), (-6.8, 11.0, -0.05), (-6.8, 12.6, 0.1)): P.sunbed(g, x, y, math.pi / 2 + r, "white")
    P.parasol(g, -8.3, 11.0, 2.6, 1.7, "cream"); P.round_table(g, -7.8, 11.0, 0.27, 0.5)
    for x, y, r in ((6.8, 9.8, 0.1), (6.8, 11.4, -0.08)): P.sunbed(g, x, y, -math.pi / 2 + r, "white")
    for k_, x in enumerate(np.linspace(-9.5, 9.5, 6)): P.potted(g, x, 4.8, 0.6, 0.45, "shrub", k_ + 10)
    for x in (-3.4, 3.4): P.potted(g, x, 17.6, 0.7, 0.5, "olive", int(x * 3))
    g.flush()
    E.string_lights(coll, 4)
    return dict(world=sky_world(1.0, 0.4, 3.0), exp=0.15, car=False, sun=(32, 25, 7.2, (1.0, 0.82, 0.6)))


# ================================================================================================ 5 CAFE (commercial terrace: guests, counter, parasols)
def set_cafe(coll):
    FS.ground(coll, FS.paving((0.9, 0.86, 0.8), 0.6, "cityfloor"))
    _horizon(coll, 15, 40, 60, 100)
    cob = FS.paving((1.15, 1.05, 0.9), 0.7, "terrace_pav")
    _pad(coll, "terrace", (38, 15.5), (0, -0.25), cob, 0.0)
    _pad(coll, "sidewalk", (240, 4.6), (0, -10.3), FS.paving((1.0, 0.95, 0.88), 0.6, "pave"), 0.0)
    _pad(coll, "road", (240, 9.0), (0, -17.2), FS.asphalt(), -0.05); box("curb2", (240, 0.18, 0.15), (0, -12.7, -0.03), FS.paving((0.7, 0.7, 0.7), 0.8, "curb"), coll, 0, 0.01)
    blds = [(-6.8, 6.0, 3, (0.78, 0.56, 0.42), (0.28, 0.14, 0.1), None, (0.15, 0.3, 0.2), False),
            (0.0, 7.0, 3, (0.92, 0.88, 0.76), (0.45, 0.2, 0.14), ((0.1, 0.35, 0.28), (0.95, 0.95, 0.92)), None, True),
            (6.9, 6.2, 4, (0.62, 0.72, 0.78), (0.3, 0.15, 0.11), None, None, False),
            (-13.4, 6.4, 3, (0.9, 0.78, 0.55), (0.28, 0.14, 0.1), None, (0.4, 0.15, 0.12), False),
            (13.4, 6.3, 3, (0.78, 0.5, 0.45), (0.5, 0.25, 0.18), None, None, False),
            (-19.6, 6.6, 3, (0.7, 0.62, 0.5), (0.3, 0.14, 0.1), None, None, False), (19.8, 6.4, 3, (0.85, 0.8, 0.7), (0.3, 0.14, 0.1), None, None, False)]
    for i, (x, w, fl, pc, rc, aw, sh, shop) in enumerate(blds):
        FS.townhouse(coll, (x, 13.0), 0, w, 11.0, fl, pc, rc, f"th{i}", 4.1, shop or i in (2, 4), sh, aw)
    bases = FS.tree_meshes(coll, 51, "broad", 2)
    for p, s in (((-10.5, -10.0), 0.55), ((10.5, -10.0), 0.55), ((-3.0, -10.0), 0.5), ((22, -4), 0.9), ((-24, 2), 0.95)): FS.place_tree(coll, bases, (p[0], p[1], 0), p[0], s)
    pergola_roof(coll, (0.04, 0.05, 0.045), 0.5, True)
    g = P.G(coll, "cafe_props", bevel=0.006)
    pl = foliage = FS.foliage_mat("boxwood", (0.02, 0.07, 0.02), (0.07, 0.17, 0.04), 2.5)
    for k, x in enumerate(np.linspace(-15, 15, 11)):
        if abs(x) < 1.0: continue
        g.box((x, -7.6, 0.2), (1.3, 0.6, 0.4), "stone_dark"); g.box((x, -7.6, 0.55), (1.2, 0.5, 0.4), pl)
    # --- under the pergola: 4 bistro tables with guests, serving counter at the back
    tabs = [(-0.85, -1.85), (0.85, -1.85), (-0.85, -0.25), (0.85, -0.25)]
    guests = [("teal", "denim", "skin1", "hair_br", False), ("terra", "grey", "skin2", "hair_dk", True), ("white", "denim", "skin1", "hair_bl", True), ("olive", "lgrey", "skin2", "hair_dk", False),
              ("mustard", "denim", "skin1", "hair_dk", False), ("grey", "grey", "skin1", "hair_bl", True), ("pink", "denim", "skin2", "hair_br", True), ("blue", "lgrey", "skin1", "hair_br", False)]
    gi = 0
    for ti, (tx, ty) in enumerate(tabs):
        P.round_table(g, tx, ty, 0.4, 0.74); P.cup(g, tx - 0.1, ty - 0.05, 0.76); P.cup(g, tx + 0.1, ty + 0.08, 0.76); P.plate(g, tx, ty - 0.18, 0.765, 0.1); g.box((tx + 0.02, ty - 0.18, 0.79), (0.1, 0.05, 0.03), "bread")
        for side in (-1, 1):
            cx, cy = tx, ty + side * 0.62; rot = math.pi if side == 1 else 0.0
            P.bistro_chair(g, cx, cy, rot, "wicker")
            if gi < len(guests) and ti != 3 or (ti == 3 and side == 1 and gi < len(guests)):
                sh, pa, sk, ha, lh = guests[gi]; P.person(g, cx, cy - (0.0), rot, sh, pa, sk, ha, True, lh); gi += 1
    # counter: 3.2 m run with espresso machine, cake display, cups
    k = P.G(coll, "cafe_counter", loc=(0.0, 2.45, 0.0), rot=math.pi, bevel=0.006)
    P.kitchen_run(k, -1.6, 0, 3.2, 0.64, cab="graphite", top="oak")
    k.box((-0.9, 0.0, 1.04), (0.5, 0.4, 0.34), "steel"); k.box((-0.9, 0.0, 0.92), (0.55, 0.45, 0.04), "blacksteel")
    k.box((0.55, 0.05, 1.0), (1.0, 0.45, 0.26), "ceramic"); k.box((0.55, 0.05, 1.0), (0.96, 0.41, 0.22), "bread" if False else "cream")
    for i in range(5): k.cyl((0.2 + i * 0.18, 0.05, 1.0), 0.06, 0.05, "terra", 12)
    for i in range(4): P.cup(k, 0.1 + i * 0.12, 0.28, 0.86)
    k.box((0, -0.33, 1.3), (3.3, 0.06, 1.0), "stone_dark"); k.flush()
    for i in range(3):
        x = -0.9 + i * 0.9; P.stool(g, x, 1.7) if hasattr(P, "stool") else None
    g.flush()
    # --- terrace beyond the pergola: parasol tables with guests (the cafe's real seating, much larger than the pergola)
    h = P.G(coll, "cafe_terrace", bevel=0.006)
    spots = [(-7.0, -3.2), (4.8, -3.2), (-8.0, -0.6), (8.0, -0.4), (-11.5, -3.0), (11.6, -3.2), (-4.8, 2.4), (4.9, 2.2), (-8.2, 3.6), (8.3, 3.8), (-12.5, 1.0), (12.4, 0.8)]
    gg = [("teal", "denim", "skin1", "hair_br", False), ("terra", "grey", "skin2", "hair_dk", True), ("white", "denim", "skin1", "hair_bl", True), ("olive", "lgrey", "skin2", "hair_dk", False)]
    for i, (x, y) in enumerate(spots):
        h.cyl((x, y, 1.25), 0.025, 2.5, "blacksteel", 8); h.add(P.ell_p((x, y, 2.45), 1.45, (1, 1, 0.16), 24, 5, zmin=0.0), "cream" if i % 3 else "terra", True)
        P.round_table(h, x, y, 0.4, 0.74); P.cup(h, x - 0.1, y, 0.76); P.cup(h, x + 0.12, y + 0.05, 0.76); P.plate(h, x, y - 0.17, 0.765, 0.1)
        for side in (-1, 1):
            rot = math.pi if side == 1 else 0.0; cx, cy = x, y + side * 0.6
            P.bistro_chair(h, cx, cy, rot, "wicker")
            if (i + (side > 0)) % 2 == 0 and i < 10: sh, pa, sk, ha, lh = gg[(i + side) % 4]; P.person(h, cx, cy, rot, sh, pa, sk, ha, True, lh)
    for x in (-2.3, 2.3): P.potted(h, x, 2.4, 0.7, 0.5, "shrub", int(abs(x) * 5))
    h.flush()
    E.string_lights(coll, 5)
    return dict(world=sky_world(1.0, 0.5, 5.0), exp=0.15, car=False, sun=(46, 300, 7.2, SUN_WARM))


SETS = {"yard": set_yard, "carport": set_carport, "barbecue": set_barbecue, "kitchen": set_kitchen, "lounge": set_lounge, "commercial": set_cafe}
