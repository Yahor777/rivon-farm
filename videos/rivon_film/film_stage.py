"""Music-video lab (refs: dark hangar, wet black floor, floating LED wall, haze, blue-teal, robot camera arm).
Built from primitives in bpy, real-world proportions. The pergola is never touched."""
import math
import numpy as np
import bpy, mathutils
from film_lib import *   # noqa


def _nodes(m):
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear(); return nt


def mat_wet_floor():
    m = bpy.data.materials.new("stage_wet_floor"); nt = _nodes(m)
    out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs[0], out.inputs[0])
    b.inputs["Base Color"].default_value = (0.006, 0.008, 0.012, 1); b.inputs["Specular IOR Level"].default_value = 0.8
    b.inputs["Coat Weight"].default_value = 0.6; b.inputs["Coat Roughness"].default_value = 0.02
    tc = nt.nodes.new("ShaderNodeTexCoord")
    # large puddle-like patches (very smooth) over lightly rough polished concrete
    n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 0.22; n.inputs["Detail"].default_value = 5.0; n.inputs["Roughness"].default_value = 0.55
    nt.links.new(tc.outputs["Object"], n.inputs[0])
    r = nt.nodes.new("ShaderNodeMapRange"); r.inputs[1].default_value = 0.40; r.inputs[2].default_value = 0.62
    r.inputs[3].default_value = 0.30; r.inputs[4].default_value = 0.025
    nt.links.new(n.outputs["Fac"], r.inputs[0])
    # fine micro variation + seams of 4x4 m floor panels
    n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 6.0; n2.inputs["Detail"].default_value = 6.0
    nt.links.new(tc.outputs["Object"], n2.inputs[0])
    add = nt.nodes.new("ShaderNodeMath"); add.operation = "ADD"; add.inputs[1].default_value = 0.0
    nt.links.new(r.outputs[0], add.inputs[0])
    mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY_ADD"; mul.inputs[1].default_value = 0.08
    nt.links.new(n2.outputs["Fac"], mul.inputs[0]); nt.links.new(add.outputs[0], mul.inputs[2])
    brick = nt.nodes.new("ShaderNodeTexBrick"); brick.inputs["Scale"].default_value = 0.25; brick.inputs["Mortar Size"].default_value = 0.004
    brick.inputs["Brick Width"].default_value = 1.0; brick.inputs["Row Height"].default_value = 1.0; brick.offset = 0.0
    brick.inputs["Mortar Smooth"].default_value = 0.2
    nt.links.new(tc.outputs["Object"], brick.inputs[0])
    seam = nt.nodes.new("ShaderNodeMath"); seam.operation = "MULTIPLY"; seam.inputs[1].default_value = 0.35
    nt.links.new(brick.outputs["Fac"], seam.inputs[0])       # Fac = 1 on mortar in "Fac" output? (mortar -> 0); handled via invert below
    inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
    nt.links.new(brick.outputs["Fac"], inv.inputs[1])
    seam2 = nt.nodes.new("ShaderNodeMath"); seam2.operation = "MULTIPLY_ADD"; seam2.inputs[1].default_value = 0.4
    nt.links.new(inv.outputs[0], seam2.inputs[0]); nt.links.new(mul.outputs[0], seam2.inputs[2])
    nt.links.new(seam2.outputs[0], b.inputs["Roughness"])
    return m


def mat_matte(name, col, rough=0.8):
    m = bpy.data.materials.new(name); nt = _nodes(m)
    out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(b.outputs[0], out.inputs[0])
    b.inputs["Base Color"].default_value = col; b.inputs["Roughness"].default_value = rough
    return m


def mat_led(strength=9.0):
    """Pixel-mosaic video wall: big luminous blocks over a fine pixel grid, cyan -> white."""
    m = bpy.data.materials.new("stage_led_wall"); nt = _nodes(m)
    out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission"); nt.links.new(em.outputs[0], out.inputs[0])
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1 / 0.09, 1 / 0.09, 1 / 0.09)   # 9 cm LED pixels
    nt.links.new(tc.outputs["Object"], mp.inputs[0])
    fl = nt.nodes.new("ShaderNodeVectorMath"); fl.operation = "FLOOR"; nt.links.new(mp.outputs[0], fl.inputs[0])
    wn = nt.nodes.new("ShaderNodeTexWhiteNoise"); wn.noise_dimensions = "3D"; nt.links.new(fl.outputs[0], wn.inputs[0])
    big = nt.nodes.new("ShaderNodeTexNoise"); big.inputs["Scale"].default_value = 0.55; big.inputs["Detail"].default_value = 6.0; big.inputs["Roughness"].default_value = 0.62
    nt.links.new(tc.outputs["Object"], big.inputs[0])
    blocks = nt.nodes.new("ShaderNodeMapRange"); blocks.inputs[1].default_value = 0.30; blocks.inputs[2].default_value = 0.75
    nt.links.new(big.outputs["Fac"], blocks.inputs[0])
    px = nt.nodes.new("ShaderNodeMath"); px.operation = "MULTIPLY_ADD"; px.inputs[1].default_value = 0.65; px.inputs[2].default_value = 0.35
    nt.links.new(wn.outputs["Value"], px.inputs[0])
    lvl = nt.nodes.new("ShaderNodeMath"); lvl.operation = "MULTIPLY"; nt.links.new(blocks.outputs[0], lvl.inputs[0]); nt.links.new(px.outputs[0], lvl.inputs[1])
    cr = nt.nodes.new("ShaderNodeValToRGB")
    cr.color_ramp.elements[0].position = 0.02; cr.color_ramp.elements[0].color = (0.002, 0.01, 0.03, 1)
    cr.color_ramp.elements[1].position = 0.9; cr.color_ramp.elements[1].color = (0.55, 0.9, 1.0, 1)
    mid = cr.color_ramp.elements.new(0.45); mid.color = (0.05, 0.33, 0.85, 1)
    nt.links.new(lvl.outputs[0], cr.inputs[0]); nt.links.new(cr.outputs[0], em.inputs[0]); em.inputs["Strength"].default_value = strength
    return m


def seg(coll, name, p0, p1, r, mat, seg_n=24):
    p0 = mathutils.Vector(p0); p1 = mathutils.Vector(p1); d = p1 - p0
    rot = d.to_track_quat("Z", "Y").to_euler()
    return cyl(name, r, d.length, tuple((p0 + p1) / 2), mat, coll, seg_n, rot=rot)


def robot_arm(coll, base, yaw, mats):
    """6-axis industrial arm with a cine camera on a welded fixture table. Local frame: +x forward, z up; yaw about z."""
    bx, by = base; c, s = math.cos(yaw), math.sin(yaw)
    L = lambda x, y, z: (bx + x * c - y * s, by + x * s + y * c, z)
    steel, blue, dark, black = mats["steel"], mats["robot"], mats["rdark"], mats["black"]
    box("rb_table", (2.6, 2.6, 0.5), L(0, 0, 0.25), steel, coll, yaw, 0.01)
    for i in range(-5, 6):                               # fixture-table hole grid (M16 on 100 mm pitch)
        for j in range(-5, 6):
            if (i + j) % 2 == 0: cyl(f"rb_h{i}_{j}", 0.018, 0.004, L(i * 0.22, j * 0.22, 0.502), black, coll, 10)
    # truss gussets on the front edge
    for k, yy in enumerate((-0.9, 0.9)):
        box(f"rb_gus{k}", (0.1, 0.05, 0.5), L(1.3 + 0.05, yy, 0.5), steel, coll, yaw, 0.004)
    cyl("rb_base", 0.46, 0.18, L(0, 0, 0.59), dark, coll, 40, bevel=0.01)
    cyl("rb_turret", 0.36, 0.55, L(0, 0, 0.95), blue, coll, 40, bevel=0.012)
    S = L(0.0, 0.0, 1.30); E = L(-0.12, 0.0, 2.85); W = L(1.85, 0.0, 2.55)
    sphere("rb_j2", 0.26, S, blue, coll, 32); cyl("rb_j2_cap", 0.2, 0.62, S, dark, coll, 32, rot=(math.pi / 2, 0, yaw))
    seg(coll, "rb_lower", S, E, 0.19, blue, 32); sphere("rb_j3", 0.23, E, blue, coll, 32)
    cyl("rb_j3_cap", 0.17, 0.52, E, dark, coll, 32, rot=(math.pi / 2, 0, yaw))
    seg(coll, "rb_upper", E, W, 0.16, blue, 32); sphere("rb_j4", 0.19, W, blue, coll, 32)
    T = L(2.25, 0.0, 2.4)
    seg(coll, "rb_wrist", W, T, 0.1, dark, 24)
    box("rb_cam", (0.42, 0.2, 0.24), L(2.4, 0.0, 2.34), black, coll, yaw, 0.012)
    cyl("rb_lens", 0.085, 0.3, L(2.62, 0.0, 2.34), black, coll, 32, rot=(0, math.pi / 2, yaw))
    cyl("rb_lens_glass", 0.07, 0.01, L(2.775, 0.0, 2.34), mats["glass"], coll, 28, rot=(0, math.pi / 2, yaw))


def build_stage(coll):
    floor_m = mat_wet_floor()
    wall_m = mat_matte("stage_black_wall", (0.0, 0.0, 0.0, 1), 1.0)
    steel = mat_matte("stage_steel", (0.07, 0.075, 0.085, 1), 0.45); steel.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 0.8
    robot = mat_matte("stage_robot_blue", (0.012, 0.11, 0.42, 1), 0.28); b = robot.node_tree.nodes["Principled BSDF"]; b.inputs["Coat Weight"].default_value = 1.0; b.inputs["Coat Roughness"].default_value = 0.08
    rdark = mat_matte("stage_robot_dark", (0.012, 0.014, 0.018, 1), 0.35)
    black = mat_matte("stage_black", (0.003, 0.003, 0.004, 1), 0.4)
    glass = bpy.data.materials.new("stage_glass"); nt = _nodes(glass); o = nt.nodes.new("ShaderNodeOutputMaterial"); g = nt.nodes.new("ShaderNodeBsdfGlossy")
    g.inputs["Roughness"].default_value = 0.02; g.inputs["Color"].default_value = (0.2, 0.3, 0.4, 1); nt.links.new(g.outputs[0], o.inputs[0])
    col_m = mat_matte("stage_column", (0.04, 0.046, 0.055, 1), 0.7)
    box("ST_floor", (400, 400, 0.4), (0, 0, -0.2), floor_m, coll, 0, 0)
    for nme, size, loc in (("back", (400, 0.5, 40), (0, 110, 19.8)), ("front", (400, 0.5, 40), (0, -110, 19.8)), ("left", (0.5, 400, 40), (-110, 0, 19.8)), ("right", (0.5, 400, 40), (110, 0, 19.8))):
        box(f"ST_wall_{nme}", size, loc, wall_m, coll, 0, 0)
    box("ST_ceiling", (400, 400, 0.4), (0, 0, 39.7), wall_m, coll, 0, 0)
    # structural columns at the back (as in the reference hall)
    for i, x in enumerate((-30, -9, 12, 33)):
        box(f"ST_col{i}", (1.4, 1.4, 19.6), (x, 46, 9.8), col_m, coll, 0, 0.02)
    # ---- floating LED wall (15 x 11 m) at 8 m, face down, with a dark truss frame and four hanging cables
    led = mat_emission("stage_white_lamp", (1.0, 1.0, 1.0, 1), 2.6)      # plain white softbox panel (owner request)
    pn = box("ST_led", (12.0, 9.0, 0.12), (1.5, 3.0, 9.6), black, coll, 0, 0)
    pn.data.materials.clear(); pn.data.materials.append(black)
    plane = bpy.data.meshes.new("ST_led_face")
    plane.from_pydata([(-6.0, -4.5, 0), (6.0, -4.5, 0), (6.0, 4.5, 0), (-6.0, 4.5, 0)], [], [(3, 2, 1, 0)]); plane.update(); plane.materials.append(led)
    lf = bpy.data.objects.new("ST_led_face", plane); lf.location = (1.5, 3.0, 9.53); link(lf, coll)
    for k in ('visible_diffuse', 'visible_volume_scatter'):
        setattr(lf, k, False)           # the LED_wash area light does the lighting; the textured panel is only seen / reflected
    for nme, size, loc in (("n", (12.4, 0.3, 0.3), (1.5, 7.65, 9.75)), ("s", (12.4, 0.3, 0.3), (1.5, -1.65, 9.75)), ("e", (0.3, 9.4, 0.3), (7.65, 3.0, 9.75)), ("w", (0.3, 9.4, 0.3), (-4.65, 3.0, 9.75))):
        box(f"ST_truss_{nme}", size, loc, steel, coll, 0, 0.01)
    for i, (x, y) in enumerate(((7.65, 7.65), (-4.65, 7.65), (7.65, -1.65), (-4.65, -1.65))):
        cyl(f"ST_cable{i}", 0.012, 30.0, (x, y, 24.9), black, coll, 8)
    # ---- robot camera arm (left of the pergola), looking in
    # robot arm removed on owner request:     # robot_arm(coll, (-4.8, -1.2), math.radians(18), dict(steel=steel, robot=robot, rdark=rdark, black=black, glass=glass))
    # ---- lights: cold wash from the LED wall, warm key on the timber, cold rim, practical floor strips
    def area(name, loc, size, energy, color, target):
        L_ = bpy.data.lights.new(name, "AREA"); L_.shape = "RECTANGLE"; L_.size, L_.size_y = size; L_.energy = energy; L_.color = color
        ob = bpy.data.objects.new(name, L_); ob.location = loc
        ob.rotation_euler = mathutils.Vector(np.array(target) - np.array(loc)).to_track_quat("-Z", "Y").to_euler(); link(ob, coll); return ob
    area("LED_wash", (1.5, 3.0, 9.4), (12, 9), 1700, (0.92, 0.96, 1.0), (0, 0, 0))
    def spot(name, loc, energy, color, target, blend=0.25, angle=26):
        L_ = bpy.data.lights.new(name, "SPOT"); L_.energy = energy; L_.color = color; L_.spot_size = math.radians(angle); L_.spot_blend = blend; L_.shadow_soft_size = 0.15
        ob = bpy.data.objects.new(name, L_); ob.location = loc
        ob.rotation_euler = mathutils.Vector(np.array(target) - np.array(loc)).to_track_quat("-Z", "Y").to_euler(); link(ob, coll); return ob
    spot("KEY_warm", (8.5, -9.5, 7.5), 11000, (1.0, 0.78, 0.55), (0, 0, 1.6), 0.3, 24)
    spot("RIM_cold_L", (-9.0, 10.0, 6.5), 7500, (0.45, 0.7, 1.0), (0, 0, 1.8), 0.3, 22)
    spot("RIM_cold_R", (10.0, 9.0, 6.0), 6500, (0.5, 0.75, 1.0), (0, 0, 1.8), 0.3, 22)
    # ---- light beams: noise-free "fake haze" cones (additive, camera-only) instead of a render-expensive volume
    def beam(name, loc, target, angle, length, color, strength):
        import bmesh
        d = mathutils.Vector(np.array(target) - np.array(loc)).normalized(); L = float(length)
        rad = math.tan(math.radians(angle) / 2) * L
        bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=False, segments=48, radius1=0.02, radius2=rad, depth=L)
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        for p in me.polygons: p.use_smooth = True
        m = bpy.data.materials.new(name); nt = _nodes(m)
        o = nt.nodes.new("ShaderNodeOutputMaterial"); mx = nt.nodes.new("ShaderNodeAddShader"); tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (*color, 1); em.inputs["Strength"].default_value = 1.0
        lw = nt.nodes.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.5
        inv = nt.nodes.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
        pw = nt.nodes.new("ShaderNodeMath"); pw.operation = "POWER"; pw.inputs[1].default_value = 2.2
        tc = nt.nodes.new("ShaderNodeTexCoord"); sp = nt.nodes.new("ShaderNodeSeparateXYZ")
        gr = nt.nodes.new("ShaderNodeMapRange"); gr.inputs[1].default_value = -L / 2; gr.inputs[2].default_value = L / 2; gr.inputs[3].default_value = 1.0; gr.inputs[4].default_value = 0.05
        mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"
        nt.links.new(lw.outputs["Facing"], inv.inputs[1]); nt.links.new(inv.outputs[0], pw.inputs[0])
        nt.links.new(tc.outputs["Object"], sp.inputs[0]); nt.links.new(sp.outputs["Z"], gr.inputs[0])
        nt.links.new(pw.outputs[0], mul.inputs[0]); nt.links.new(gr.outputs[0], mul.inputs[1])
        sc2 = nt.nodes.new("ShaderNodeMath"); sc2.operation = "MULTIPLY"; sc2.inputs[1].default_value = strength
        nt.links.new(mul.outputs[0], sc2.inputs[0]); nt.links.new(sc2.outputs[0], em.inputs["Strength"])
        nt.links.new(tr.outputs[0], mx.inputs[0]); nt.links.new(em.outputs[0], mx.inputs[1]); nt.links.new(mx.outputs[0], o.inputs[0])
        me.materials.append(m)
        ob = bpy.data.objects.new(name, me); ob.location = tuple(np.array(loc) + np.array(d) * L / 2)
        ob.rotation_euler = d.to_track_quat("Z", "Y").to_euler(); link(ob, coll)
        for k in ("visible_diffuse", "visible_glossy", "visible_shadow", "visible_volume_scatter"): setattr(ob, k, False)
        return ob
    beam("BEAM_key", (8.5, -9.5, 7.5), (0, 0, 1.6), 17, 17.0, (1.0, 0.72, 0.45), 0.16)
    beam("BEAM_rimL", (-9.0, 10.0, 6.5), (0, 0, 1.8), 16, 15.0, (0.35, 0.62, 1.0), 0.14)
    beam("BEAM_rimR", (10.0, 9.0, 6.0), (0, 0, 1.8), 16, 15.0, (0.40, 0.68, 1.0), 0.12)
    return coll
