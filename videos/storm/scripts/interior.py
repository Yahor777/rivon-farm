"""The house is lived in. Ground-floor room behind the 9.6 m glazing (6.2 m deep, 12 m wide) is zoned like a real
open-plan living space: lounge (two sofas, lounge chair, rug, coffee table with books, side table + lamp), dining
(table, six chairs, pendant, vase), back wall (shelving with books and ceramics, low cabinet, framed pictures, clock),
kitchen island with bar stools. When the lights are on every lamp is a real fixture (table lamp, floor lamp, pendant,
shelf LED) at 2700 K."""
import math
import bpy
import numpy as np
from mathutils import Vector
import storm_lib as S, build_world as BW
import design as D

LOG = []
R = np.random.default_rng(606)


def _put(c, aid, name, loc, rot=0.0, s=1.0):
    if not (S.ASSETS / "polyhaven" / aid).exists():
        return []
    return [S.place(me, f"int2_{name}_{i}", loc, c, rot, s) for i, me in enumerate(S.ph_variants(aid, lod=0))]


def _emit(name, k, strength):
    m = bpy.data.materials.new(name); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links; N.clear()
    out = N.new("ShaderNodeOutputMaterial"); em = N.new("ShaderNodeEmission"); bb = N.new("ShaderNodeBlackbody")
    bb.inputs["Temperature"].default_value = k; L.new(bb.outputs[0], em.inputs["Color"]); em.inputs["Strength"].default_value = strength
    L.new(em.outputs[0], out.inputs["Surface"]); return m


def _point(c, name, loc, w, k=2700, r=0.05):
    Lp = bpy.data.lights.new(name, "POINT"); Lp.energy = w; Lp.shadow_soft_size = r; Lp.use_nodes = True
    bb = Lp.node_tree.nodes.new("ShaderNodeBlackbody"); bb.inputs["Temperature"].default_value = k
    Lp.node_tree.links.new(bb.outputs[0], Lp.node_tree.nodes["Emission"].inputs["Color"])
    o = bpy.data.objects.new(name, Lp); c.objects.link(o); o.location = loc


def _lamp(c, name, x, y, z0, h, lit, shade_r=0.16):
    """table / floor lamp: slim brass stem, linen drum shade (translucent), bulb light when lit"""
    brass = S.mat_simple("lamp_brass", (0.45, 0.33, 0.16), rough=0.3, metal=1.0)
    bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=0.012, depth=h, location=(x, y, z0 + h / 2)); o = bpy.context.object
    o.name = name + "_stem"; S.link(o, c); o.data.materials.append(brass)
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.09, depth=0.02, location=(x, y, z0 + 0.01)); o = bpy.context.object
    o.name = name + "_base"; S.link(o, c); o.data.materials.append(brass)
    sh = bpy.data.materials.new(name + "_shade"); sh.use_nodes = True; b = S.principled(sh)
    b.inputs["Base Color"].default_value = (0.86, 0.80, 0.68, 1); b.inputs["Roughness"].default_value = 0.9
    b.inputs["Transmission Weight"].default_value = 0.0
    if lit:                                                  # the shade glows: thin linen lit from inside
        b.inputs["Emission Color"].default_value = (1.0, 0.62, 0.30, 1); b.inputs["Emission Strength"].default_value = 3.0
    bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=shade_r, depth=shade_r * 1.25, end_fill_type="NOTHING", location=(x, y, z0 + h)); o = bpy.context.object
    o.name = name + "_shade"; S.link(o, c); o.data.materials.append(sh); o.data.shade_smooth()
    if lit:
        _point(c, name + "_bulb", (x, y, z0 + h - 0.02), 28, 2600, 0.04)


def furnish(lit=False):
    c = BW.fresh("INTERIOR2"); x_in = BW.FAC_X - 0.36; zc = D.Z_SOFFIT - 0.12
    # ---- lounge (y -5 .. 0.6)
    rug = bpy.data.materials.new("rug_wool"); rug.use_nodes = True; N, L = rug.node_tree.nodes, rug.node_tree.links; b = S.principled(rug)
    b.inputs["Roughness"].default_value = 1.0; b.inputs["Sheen Weight"].default_value = 0.5
    tc = N.new("ShaderNodeTexCoord"); nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 420; L.new(tc.outputs["Object"], nz.inputs["Vector"])
    cr = N.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (0.42, 0.39, 0.34, 1); cr.color_ramp.elements[1].color = (0.60, 0.57, 0.50, 1)
    L.new(nz.outputs["Fac"], cr.inputs["Fac"]); L.new(cr.outputs["Color"], b.inputs["Base Color"])
    bp = N.new("ShaderNodeBump"); bp.inputs["Distance"].default_value = 0.004; L.new(nz.outputs["Fac"], bp.inputs["Height"]); L.new(bp.outputs[0], b.inputs["Normal"])
    S.box("int2_rug", (3.0, 4.2, 0.012), (x_in - 2.7, -2.0, 0.006), c, rug, bevel=0.004)
    _put(c, "sofa_03", "sofa_long", (x_in - 2.6, -4.05, 0.0), 0.0)                       # back to the side wall, faces +y
    _put(c, "throw_pillows_01", "pillows_a", (x_in - 3.3, -3.95, 0.48), 0.2, 0.9)
    _put(c, "throw_pillows_01", "pillows_b", (x_in - 3.75, -0.9, 0.42), 1.7, 0.85)
    _put(c, "mid_century_lounge_chair", "lounge", (x_in - 1.15, -0.2, 0.0), -2.3)
    _put(c, "side_table_01", "side_a", (x_in - 4.25, -3.95, 0.0), 0.0)
    _lamp(c, "int2_tablelamp", x_in - 4.25, -3.95, 0.55, 0.42, lit, 0.14)
    _put(c, "decorative_book_set_01", "ctbooks", (x_in - 2.25, -1.45, 0.47), 1.2, 1.0)
    _put(c, "wooden_bowl_01", "bowl", (x_in - 2.1, -0.95, 0.47), 0.4, 1.0)
    _lamp(c, "int2_floorlamp", x_in - 0.75, -4.6, 0.0, 1.55, lit, 0.20)
    _put(c, "potted_plant_01", "plant_a", (x_in - 0.7, 0.9, 0.0), 1.0, 1.5)
    # ---- dining (y 1.8 .. 5.4)
    dx, dy = x_in - 2.5, 3.6
    _put(c, "dining_table", "dining", (dx, dy, 0.0), math.pi / 2)                       # long axis along y
    for k, (ox, oy, rz) in enumerate(((-0.95, -0.65, -math.pi / 2), (-0.95, 0.0, -math.pi / 2), (-0.95, 0.65, -math.pi / 2),
                                       (0.95, -0.65, math.pi / 2), (0.95, 0.0, math.pi / 2), (0.95, 0.65, math.pi / 2))):
        _put(c, "dining_chair_02", f"dchair{k}", (dx + ox + R.normal(0, 0.02), dy + oy + R.normal(0, 0.02), 0.0), rz + R.normal(0, 0.06))
    _put(c, "ceramic_vase_03", "dvase", (dx, dy + 0.1, 0.87), 0.0, 1.0)
    cord = S.mat_simple("int_cord", (0.03, 0.03, 0.03), rough=0.6)
    shade = S.mat_simple("int_pendant_shade", (0.07, 0.07, 0.075), rough=0.45)
    glow = _emit("int_pendant_glow", 2700, 30 if lit else 0.0)
    for k, oy in enumerate((-0.45, 0.45)):
        z = 1.62
        bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=0.003, depth=zc - z - 0.12, location=(dx, dy + oy, (zc + z + 0.12) / 2)); o = bpy.context.object
        o.name = f"int2_dpend_cord{k}"; S.link(o, c); o.data.materials.append(cord)
        bpy.ops.mesh.primitive_cone_add(vertices=40, radius1=0.17, radius2=0.04, depth=0.2, end_fill_type="NOTHING", location=(dx, dy + oy, z + 0.02)); o = bpy.context.object
        o.name = f"int2_dpend_shade{k}"; S.link(o, c); o.data.materials.append(shade); o.data.shade_smooth()
        sol = o.modifiers.new("t", "SOLIDIFY"); sol.thickness = 0.004
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=0.035, location=(dx, dy + oy, z - 0.02)); o = bpy.context.object
        o.name = f"int2_dpend_bulb{k}"; S.link(o, c); o.data.materials.append(glow)
        if lit:
            _point(c, f"int2_dpend_light{k}", (dx, dy + oy, z - 0.08), 45, 2700, 0.035)
    # ---- back wall: shelving, cabinet, pictures, clock
    xw = x_in - 6.15                                                                    # front face of the back wall
    for k, y in enumerate((-4.9, -3.75)):
        _put(c, "wooden_display_shelves_01", f"shelf{k}", (xw + 0.22, y, 0.0), math.pi / 2)
        for j, z in enumerate((0.42, 0.80, 1.18)):
            if (k + j) % 3 != 2:
                for i, me in enumerate(S.ph_variants("book_encyclopedia_set_01", lod=0)[:9] if (S.ASSETS / "polyhaven" / "book_encyclopedia_set_01").exists() else []):
                    S.place(me, f"int2_book_{k}_{j}_{i}", (xw + 0.2, y - 0.4 + 0.045 * i, z), c, math.pi / 2 + R.normal(0, 0.03), 1.0)
            else:
                _put(c, "ceramic_vase_03", f"shv{k}{j}", (xw + 0.22, y + 0.15, z), R.uniform(0, 6), 0.7)
        if lit:
            _point(c, f"int2_shelf_led{k}", (xw + 0.3, y, 1.5), 6, 2700, 0.1)
    _put(c, "modern_wooden_cabinet", "cabinet", (xw + 0.36, -0.9, 0.0), math.pi / 2)
    _put(c, "standing_picture_frame_01", "sframe", (xw + 0.38, -0.3, 0.68), math.pi / 2 + 0.2)
    _put(c, "ceramic_vase_01", "cabvase", (xw + 0.36, -1.6, 0.68), 0.5, 1.0)
    _lamp(c, "int2_cablamp", xw + 0.36, -1.15, 0.68, 0.38, lit, 0.12)
    for k, (aid, y, z, s) in enumerate((("hanging_picture_frame_01", -1.25, 1.62, 1.5), ("hanging_picture_frame_02", -0.35, 1.72, 1.3),
                                        ("hanging_picture_frame_03", -0.35, 1.25, 1.3), ("hanging_picture_frame_01", 0.5, 1.55, 1.2))):
        _put(c, aid, f"wallframe{k}", (xw + 0.012, y, z), math.pi / 2, s)
    _put(c, "wall_clock", "clock", (xw + 0.012, 1.55, 1.95), math.pi / 2, 1.3)
    # ---- kitchen island (y 2.2 .. 5.2 at the back) with bar stools
    stone = S.mat_simple("island_stone", (0.72, 0.71, 0.69), rough=0.25)
    front = S.mat_simple("island_front", (0.045, 0.05, 0.055), rough=0.5)
    S.box("int2_island_body", (0.80, 2.8, 0.88), (x_in - 5.0, 3.7, 0.44), c, front, bevel=0.003)
    S.box("int2_island_top", (0.92, 2.95, 0.03), (x_in - 5.0, 3.7, 0.895), c, stone, bevel=0.003)
    for k, y in enumerate((2.9, 3.7, 4.5)):
        _put(c, "bar_chair_round_01", f"stool{k}", (x_in - 4.35, y, 0.0), R.uniform(0, 6.28))
    _put(c, "wooden_bowl_01", "island_bowl", (x_in - 5.0, 3.3, 0.91), 1.0, 1.2)
    if lit:
        _point(c, "int2_island_light", (x_in - 5.0, 3.7, 2.4), 60, 2800, 0.15)
    LOG.append(f"interior: lounge (2 sofas, lounge chair, wool rug, books, side table + lamp, floor lamp), dining for six with "
               f"two pendants, back wall with shelving, books, ceramics, cabinet, 4 pictures, clock, kitchen island with 3 stools; "
               f"lamps {'on (2700 K fixtures)' if lit else 'off'}")
    return LOG
