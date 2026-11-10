"""Ten alternative 'lab' sets for the film opening (music-video look). Each takes the LAB collection; the pergola is untouched."""
import math
import numpy as np
import bpy, mathutils
from film_lib import *   # noqa
from film_stage import mat_wet_floor, mat_matte, _nodes


def em(name, col, s): return mat_emission(name, (*col, 1), s)


def area(coll, name, loc, size, energy, color, target):
    L = bpy.data.lights.new(name, "AREA"); L.shape = "RECTANGLE"; L.size, L.size_y = size; L.energy = energy; L.color = color
    ob = bpy.data.objects.new(name, L); ob.location = loc
    ob.rotation_euler = mathutils.Vector(np.array(target) - np.array(loc)).to_track_quat("-Z", "Y").to_euler(); link(ob, coll); return ob


def spot(coll, name, loc, energy, color, target, angle=26, blend=0.3, soft=0.15):
    L = bpy.data.lights.new(name, "SPOT"); L.energy = energy; L.color = color; L.spot_size = math.radians(angle); L.spot_blend = blend; L.shadow_soft_size = soft
    ob = bpy.data.objects.new(name, L); ob.location = loc
    ob.rotation_euler = mathutils.Vector(np.array(target) - np.array(loc)).to_track_quat("-Z", "Y").to_euler(); link(ob, coll); return ob


def beam(coll, name, loc, target, angle, length, color, strength):
    """Noise-free visible light cone (additive, camera-only)."""
    import bmesh
    d = mathutils.Vector(np.array(target) - np.array(loc)).normalized(); L = float(length)
    rad = math.tan(math.radians(angle) / 2) * L
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=False, segments=48, radius1=0.02, radius2=rad, depth=L)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    m = bpy.data.materials.new(name); nt = _nodes(m)
    o = nt.nodes.new("ShaderNodeOutputMaterial"); ad = nt.nodes.new("ShaderNodeAddShader"); tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    e = nt.nodes.new("ShaderNodeEmission"); e.inputs["Color"].default_value = (*color, 1)
    lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.5
    inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
    pw = nt.nodes.new("ShaderNodeMath"); pw.operation = "POWER"; pw.inputs[1].default_value = 2.2
    tc = nt.nodes.new("ShaderNodeTexCoord"); sp = nt.nodes.new("ShaderNodeSeparateXYZ")
    gr = nt.nodes.new("ShaderNodeMapRange"); gr.inputs[1].default_value = -L / 2; gr.inputs[2].default_value = L / 2; gr.inputs[3].default_value = 1.0; gr.inputs[4].default_value = 0.05
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; sc2 = nt.nodes.new("ShaderNodeMath"); sc2.operation = "MULTIPLY"; sc2.inputs[1].default_value = strength
    nt.links.new(lw.outputs["Facing"], inv.inputs[1]); nt.links.new(inv.outputs[0], pw.inputs[0])
    nt.links.new(tc.outputs["Object"], sp.inputs[0]); nt.links.new(sp.outputs["Z"], gr.inputs[0])
    nt.links.new(pw.outputs[0], mul.inputs[0]); nt.links.new(gr.outputs[0], mul.inputs[1]); nt.links.new(mul.outputs[0], sc2.inputs[0]); nt.links.new(sc2.outputs[0], e.inputs["Strength"])
    nt.links.new(tr.outputs[0], ad.inputs[0]); nt.links.new(e.outputs[0], ad.inputs[1]); nt.links.new(ad.outputs[0], o.inputs[0])
    me.materials.append(m)
    ob = bpy.data.objects.new(name, me); ob.location = tuple(np.array(loc) + np.array(d) * L / 2)
    ob.rotation_euler = d.to_track_quat("Z", "Y").to_euler(); link(ob, coll)
    for k in ("visible_diffuse", "visible_glossy", "visible_shadow", "visible_volume_scatter"): setattr(ob, k, False)
    return ob


def room(coll, size=(120, 120, 40), mat=None, floor_mat=None, ceil=True):
    mat = mat or mat_matte("room_black", (0, 0, 0, 1), 1.0)
    W, D, H = size
    box("R_floor", (W * 3, D * 3, 0.4), (0, 0, -0.2), floor_mat or mat, coll, 0, 0)
    for n, sz, lc in (("b", (W, 0.5, H), (0, D / 2, H / 2)), ("f", (W, 0.5, H), (0, -D / 2, H / 2)), ("l", (0.5, D, H), (-W / 2, 0, H / 2)), ("r", (0.5, D, H), (W / 2, 0, H / 2))):
        box(f"R_w{n}", sz, lc, mat, coll, 0, 0)
    if ceil: box("R_ceil", (W, D, 0.4), (0, 0, H), mat, coll, 0, 0)


def world(color, strength=1.0):
    w = bpy.data.worlds.new("labw"); w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (*color, 1); w.node_tree.nodes["Background"].inputs["Strength"].default_value = strength
    return w


def grad_mat(name, stops, axis="Z", lo=0.0, hi=14.0, strength=2.0):
    m = bpy.data.materials.new(name); nt = _nodes(m)
    o = nt.nodes.new("ShaderNodeOutputMaterial"); e = nt.nodes.new("ShaderNodeEmission"); nt.links.new(e.outputs[0], o.inputs[0])
    tc = nt.nodes.new("ShaderNodeTexCoord"); sp = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object" if False else "Generated"], sp.inputs[0])
    cr = nt.nodes.new("ShaderNodeValToRGB"); el = cr.color_ramp.elements
    el[0].position = stops[0][0]; el[0].color = (*stops[0][1], 1); el[1].position = stops[-1][0]; el[1].color = (*stops[-1][1], 1)
    for p, c in stops[1:-1]: x = el.new(p); x.color = (*c, 1)
    nt.links.new(sp.outputs[axis], cr.inputs[0]); nt.links.new(cr.outputs[0], e.inputs[0]); e.inputs["Strength"].default_value = strength
    return m


def plane(coll, name, p00, p10, p11, p01, mat):
    me = bpy.data.meshes.new(name); me.from_pydata([p00, p10, p11, p01], [], [(0, 1, 2, 3)]); me.update(); me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); link(ob, coll)
    me.uv_layers.new(name="UVMap"); return ob


# ============================================================================================ the ten variants
def v1_white_cyc(c):
    white = mat_matte("cyc_white", (0.82, 0.83, 0.85, 1), 0.9)
    fl = mat_matte("cyc_floor", (0.55, 0.56, 0.58, 1), 0.28)
    room(c, (60, 60, 24), white, fl)
    for i, x in enumerate((-9, -3, 3, 9)):
        area(c, f"soft{i}", (x, 2, 11), (6, 6), 2600, (1, 1, 1), (0, 0, 1))
    area(c, "front", (4, -14, 3.2), (8, 4), 900, (1, 0.96, 0.9), (0, 0, 1.5))
    return dict(world=(0.02, 0.02, 0.025), exp=-0.3)


def v2_spot_void(c):
    room(c, (240, 240, 60), None, mat_wet_floor())
    spot(c, "SPOT_top", (0.0, 0.0, 15), 52000, (1.0, 0.97, 0.9), (0, 0, 0), 22, 0.25, 0.25)
    beam(c, "BEAM_top", (0.0, 0.0, 15), (0, 0, 0), 22, 15.0, (1.0, 0.97, 0.92), 0.32)
    spot(c, "rim", (-9, 10, 5), 9000, (0.5, 0.7, 1.0), (0, 0, 1.6), 20, 0.4)
    return dict(world=(0, 0, 0), exp=0.0)


def v3_neon_frame(c):
    room(c, (240, 240, 60), None, mat_wet_floor())
    cy = em("neon_cyan", (0.2, 0.9, 1.0), 14.0); pk = em("neon_pink", (1.0, 0.15, 0.55), 12.0)
    def rect(name, cx, cy_, w, d, z, t, m):
        for i, (sx, sy, lx, ly) in enumerate(((w, t, 0, d / 2), (w, t, 0, -d / 2), (t, d, w / 2, 0), (t, d, -w / 2, 0))):
            box(f"{name}{i}", (sx, sy, t), (cx + lx, cy_ + ly, z), m, c, 0, 0.01)
    rect("nf", 0, 0, 10.5, 12.5, 0.04, 0.09, cy)
    rect("nm", 0, 0, 12.5, 14.5, 0.04, 0.09, pk)
    rect("nt", 0, 0, 8.5, 10.5, 6.5, 0.12, cy)
    for k, (x, y) in enumerate(((5.2, 6.2), (-5.2, 6.2), (5.2, -6.2), (-5.2, -6.2))):
        box(f"ns{k}", (0.1, 0.1, 6.5), (x * 0.81, y * 0.84, 3.25), cy, c, 0, 0.01)
    area(c, "ring_c", (0, 0, 6.2), (8, 10), 2200, (0.3, 0.85, 1.0), (0, 0, 0)); area(c, "ring_p", (0, -9, 0.6), (12, 1.2), 1600, (1.0, 0.25, 0.6), (0, 0, 1.4))
    return dict(world=(0, 0, 0), exp=0.0)


def v4_loft_sun(c):
    conc = mat_matte("loft_wall", (0.14, 0.135, 0.13, 1), 0.85)
    fl = mat_matte("loft_floor", (0.1, 0.1, 0.105, 1), 0.28)
    W, D, H = 50, 40, 12
    box("L_floor", (W + 20, D + 20, 0.4), (0, 0, -0.2), fl, c, 0, 0); box("L_ceil", (W, D, 0.4), (0, 0, H), conc, c, 0, 0)
    for n, sz, lc in (("b", (W, 0.5, H), (0, D / 2, H / 2)), ("f", (W, 0.5, H), (0, -D / 2, H / 2)), ("r", (0.5, D, H), (W / 2, 0, H / 2))):
        box(f"L_w{n}", sz, lc, conc, c, 0, 0)
    # left wall with five tall windows (real openings) + outside sky panel
    wx = -W / 2; wins = [-12, -6, 0, 6, 12]
    prev = -D / 2
    for i, wy in enumerate(wins):
        a, b = wy - 1.5, wy + 1.5
        box(f"L_wp{i}", (0.5, a - prev, H), (wx, (a + prev) / 2, H / 2), conc, c, 0, 0); prev = b
        box(f"L_wlow{i}", (0.5, 3.0, 1.2), (wx, wy, 0.6), conc, c, 0, 0); box(f"L_whi{i}", (0.5, 3.0, 3.2), (wx, wy, H - 1.6), conc, c, 0, 0)
        for k in (-1, 0, 1): box(f"L_mull{i}_{k}", (0.12, 0.08, 7.6), (wx, wy + k * 1.0, 5.0), mat_matte("mull", (0.01, 0.01, 0.012, 1), 0.5), c, 0, 0)
    box("L_wlast", (0.5, D / 2 - prev, H), (wx, (D / 2 + prev) / 2, H / 2), conc, c, 0, 0)
    sky = em("loft_sky", (0.75, 0.88, 1.0), 6.0)
    plane(c, "sky", (wx - 6, -30, -2), (wx - 6, 30, -2), (wx - 6, 30, 22), (wx - 6, -30, 22), sky)
    s = bpy.data.lights.new("sun", "SUN"); s.energy = 8.0; s.color = (1.0, 0.9, 0.75); s.angle = math.radians(1.2)
    so = bpy.data.objects.new("loft_sun", s); so.rotation_euler = (math.radians(58), 0, math.radians(-72)); link(so, c)
    area(c, "fill", (14, -14, 9), (12, 12), 700, (0.8, 0.88, 1.0), (0, 0, 1))
    return dict(world=(0, 0, 0), exp=0.1)


def v5_led_tubes(c):
    room(c, (140, 140, 40), None, mat_wet_floor())
    tube = em("tube", (0.7, 0.92, 1.0), 16.0)
    for i, x in enumerate((-10, -5, 0, 5, 10)):
        box(f"tube{i}", (0.16, 34, 0.08), (x, 0, 9.0), tube, c, 0, 0)
        area(c, f"tl{i}", (x, 0, 8.9), (0.5, 22), 1100, (0.6, 0.85, 1.0), (x, 0, 0))
    for i, x in enumerate((-24, -8, 8, 24)): box(f"col{i}", (1.6, 1.6, 38), (x, 30, 19), mat_matte("col", (0.03, 0.035, 0.04, 1), 0.7), c, 0, 0.02)
    spot(c, "key", (8.5, -9.5, 7.5), 9000, (1.0, 0.78, 0.55), (0, 0, 1.6), 24, 0.3)
    return dict(world=(0, 0, 0), exp=0.0)


def v6_sunset_backlight(c):
    room(c, (240, 240, 60), None, mat_wet_floor())
    g = grad_mat("sunset", [(0.0, (1.0, 0.55, 0.12)), (0.45, (0.9, 0.2, 0.1)), (1.0, (0.08, 0.02, 0.1))], "Z", strength=3.2)
    plane(c, "sunset_wall", (-30, 18, 0), (30, 18, 0), (30, 18, 14), (-30, 18, 14), g).data.uv_layers  # generated coords along Z
    area(c, "back_glow", (0, 16, 4), (24, 8), 9000, (1.0, 0.5, 0.2), (0, 0, 1.5))
    spot(c, "front_fill", (7, -9, 4), 2600, (0.45, 0.6, 1.0), (0, 0, 1.6), 30, 0.5)
    beam(c, "beam_l", (-14, 16, 8), (0, 0, 1), 16, 22.0, (1.0, 0.5, 0.2), 0.12); beam(c, "beam_r", (14, 16, 8), (0, 0, 1), 16, 22.0, (1.0, 0.5, 0.2), 0.12)
    return dict(world=(0, 0, 0), exp=0.1)


def v7_white_ceiling_box(c):
    wall = mat_matte("box_wall", (0.01, 0.014, 0.022, 1), 0.9)
    fl = mat_matte("box_floor", (0.02, 0.026, 0.04, 1), 0.38)
    W, D, H = 40, 40, 14
    box("B_floor", (W, D, 0.4), (0, 0, -0.2), fl, c, 0, 0)
    for n, sz, lc in (("b", (W, 0.5, H), (0, D / 2, H / 2)), ("f", (W, 0.5, H), (0, -D / 2, H / 2)), ("l", (0.5, D, H), (-W / 2, 0, H / 2)), ("r", (0.5, D, H), (W / 2, 0, H / 2))):
        box(f"B_w{n}", sz, lc, wall, c, 0, 0)
    # ceiling is one huge white luminous sheet with a dark frame (as in the reference)
    box("B_frame", (W, D, 0.4), (0, 0, H + 0.2), wall, c, 0, 0)
    plane(c, "B_sheet", (-W / 2, -D / 2, H), (W / 2, -D / 2, H), (W / 2, D / 2, H), (-W / 2, D / 2, H), em("ceil_white", (1, 1, 1), 3.0)).data.flip_normals() if False else None
    me = bpy.data.meshes.new("B_sheet"); me.from_pydata([(-W / 2 + 3, -D / 2 + 3, H - 0.02), (-W / 2 + 3, D / 2 - 3, H - 0.02), (W / 2 - 3, D / 2 - 3, H - 0.02), (W / 2 - 3, -D / 2 + 3, H - 0.02)], [], [(0, 1, 2, 3)]); me.update()
    me.materials.append(em("ceil_white", (1, 1, 1), 3.0)); ob = bpy.data.objects.new("B_sheet", me); link(ob, c)
    area(c, "ceil_light", (0, 0, H - 0.1), (30, 30), 14000, (0.95, 0.97, 1.0), (0, 0, 0))
    return dict(world=(0, 0, 0), exp=-0.2)


def v8_gradient_stage(c):
    room(c, (240, 240, 60), None, mat_wet_floor())
    g = grad_mat("cyc_grad", [(0.0, (0.0, 0.7, 0.8)), (0.35, (0.05, 0.12, 0.8)), (0.7, (0.45, 0.05, 0.7)), (1.0, (0.03, 0.0, 0.1))], "Z", strength=2.6)
    # curved cyclorama: strips on a quarter circle behind the pergola
    R = 22.0; n = 24
    for i in range(n):
        a0 = math.radians(-70 + 140 * i / n); a1 = math.radians(-70 + 140 * (i + 1) / n)
        p = lambda a, z: (R * math.sin(a), R * math.cos(a), z)
        plane(c, f"cyc{i}", p(a0, 0), p(a1, 0), p(a1, 16), p(a0, 16), g)
    spot(c, "rim_l", (-10, 8, 6), 12000, (0.8, 0.9, 1.0), (0, 0, 1.7), 20, 0.4); spot(c, "rim_r", (10, 8, 6), 12000, (1.0, 0.8, 0.95), (0, 0, 1.7), 20, 0.4)
    spot(c, "key", (7, -10, 6), 9000, (1.0, 0.92, 0.8), (0, 0, 1.6), 22, 0.4)
    return dict(world=(0, 0, 0), exp=0.1)


def v9_podium_truss(c):
    room(c, (240, 240, 60), None, mat_matte("v9_floor", (0.012, 0.012, 0.015, 1), 0.55))
    glass = mat_matte("podium", (0.003, 0.003, 0.004, 1), 0.03)
    cyl("podium", 5.2, 0.3, (0, 0, 0.15), glass, c, 96, bevel=0.01)
    steel = mat_matte("truss", (0.05, 0.05, 0.055, 1), 0.4)
    R = 8.0
    for i in range(14):
        a = 2 * math.pi * i / 14; x, y = R * math.cos(a), R * math.sin(a)
        box(f"can{i}", (0.3, 0.3, 0.45), (x, y, 8.0), steel, c, a, 0.02)
        spot(c, f"sp{i}", (x, y, 7.7), 2600, (1.0, 0.96, 0.9), (0, 0, 1.2), 14, 0.35, 0.08)
        beam(c, f"bm{i}", (x, y, 7.7), (0, 0, 1.2), 14, 11.0, (1.0, 0.96, 0.9), 0.1)
    # floating dust sparks
    rng = np.random.default_rng(7); sm = em("spark", (1, 0.95, 0.85), 30.0)
    for i in range(160):
        sphere(f"sp_{i}", 0.018, (rng.uniform(-7, 7), rng.uniform(-7, 7), rng.uniform(0.3, 7)), sm, c, 6)
    return dict(world=(0, 0, 0), exp=0.1)


def v10_grid(c):
    room(c, (240, 240, 60), None, mat_matte("gridfloor", (0.004, 0.01, 0.025, 1), 0.3))
    # glowing grid lines drawn as thin boxes
    ln = em("grid_line", (0.1, 0.8, 1.0), 9.0)
    for i in range(-20, 21):
        box(f"gx{i}", (0.035, 80, 0.01), (i * 2.0, 0, 0.005), ln, c, 0, 0); box(f"gy{i}", (80, 0.035, 0.01), (0, i * 2.0, 0.005), ln, c, 0, 0)
    g = grad_mat("horizon", [(0.0, (0.1, 0.8, 1.0)), (0.12, (0.02, 0.2, 0.5)), (1.0, (0.0, 0.0, 0.01))], "Z", strength=2.2)
    R = 40.0
    for i in range(36):
        a0 = 2 * math.pi * i / 36; a1 = 2 * math.pi * (i + 1) / 36
        p = lambda a, z: (R * math.sin(a), R * math.cos(a), z)
        plane(c, f"hz{i}", p(a0, 0), p(a1, 0), p(a1, 18), p(a0, 18), g)
    area(c, "top", (0, 0, 10), (14, 14), 1500, (0.55, 0.85, 1.0), (0, 0, 0))
    spot(c, "key", (8.5, -9.5, 7.5), 9000, (1.0, 0.82, 0.62), (0, 0, 1.6), 24, 0.3)
    return dict(world=(0, 0, 0), exp=0.1)


VARIANTS = [("01 white studio", v1_white_cyc), ("02 spotlight void", v2_spot_void), ("03 neon frames", v3_neon_frame), ("04 loft sunlight", v4_loft_sun),
            ("05 LED tubes hall", v5_led_tubes), ("06 sunset backlight", v6_sunset_backlight), ("07 white ceiling box", v7_white_ceiling_box),
            ("08 gradient stage", v8_gradient_stage), ("09 podium + spots", v9_podium_truss), ("10 neon grid", v10_grid)]


def v5b_tubes_dark_floor(c):
    """Owner choice: variant 5 (LED-tube hall) with the dark wet floor of variant 2."""
    fl = mat_wet_floor(); fl.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.0015, 0.002, 0.003, 1)
    room(c, (140, 140, 40), None, fl)
    tube = em("tube", (0.72, 0.92, 1.0), 16.0)
    for i, x in enumerate((-10, -5, 0, 5, 10)):
        box(f"tube{i}", (0.16, 34, 0.08), (x, 0, 9.0), tube, c, 0, 0)
        area(c, f"tl{i}", (x, 0, 8.9), (0.5, 22), 260, (0.6, 0.85, 1.0), (x, 0, 0))
    for i, x in enumerate((-24, -8, 8, 24)): box(f"col{i}", (1.6, 1.6, 38), (x, 30, 19), mat_matte("col", (0.03, 0.035, 0.04, 1), 0.7), c, 0, 0.02)
    spot(c, "key", (8.5, -9.5, 7.5), 9000, (1.0, 0.78, 0.55), (0, 0, 1.6), 24, 0.3)
    spot(c, "rim_cold", (-9.0, 10.0, 6.5), 7000, (0.45, 0.7, 1.0), (0, 0, 1.8), 22, 0.35)
    beam(c, "BEAM_key", (8.5, -9.5, 7.5), (0, 0, 1.6), 17, 17.0, (1.0, 0.72, 0.45), 0.10)
    beam(c, "BEAM_rim", (-9.0, 10.0, 6.5), (0, 0, 1.8), 16, 15.0, (0.35, 0.62, 1.0), 0.10)
    return dict(world=(0, 0, 0), exp=0.0)


VARIANTS.append(("05b tubes + dark floor", v5b_tubes_dark_floor))
