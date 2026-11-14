"""The garden is lived in, not an empty lawn: a stepping-stone path from the deck to the pier with low path lights,
a bistro set and a fire bowl on the lawn, planted boxes along the fence, pots on the deck, a rock-and-grass group near
the dune. Everything stays out of the pergola zone and out of the camera foregrounds."""
import math
import bpy, bmesh
import numpy as np
from mathutils import Vector
import storm_lib as S, build_world as BW

LOG = []
CLEAR = []          # (x, y, r): lawn3 removes blades here (under stepping stones)
R = np.random.default_rng(909)


def _slab(name, x, y, rz, a, b, c, mat):
    bm = bmesh.new(); n = 9; vs = []
    for i in range(n):
        t = 2 * math.pi * i / n
        rr = 1.0 + 0.16 * math.sin(3 * t + R.uniform(0, 6)) + R.normal(0, 0.05)
        vs.append(bm.verts.new((a / 2 * rr * math.cos(t), b / 2 * rr * math.sin(t), 0.0)))
    f = bm.faces.new(vs)
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    for v in [e for e in r["geom"] if isinstance(e, bmesh.types.BMVert)]:
        v.co.z += 0.05
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(mat)
    o = bpy.data.objects.new(name, me); c.objects.link(o)
    g = BW.ground_z(x, y); o.location = (x, y, g - 0.02); o.rotation_euler = (R.normal(0, 0.012), R.normal(0, 0.012), rz)
    bv = o.modifiers.new("bv", "BEVEL"); bv.width = 0.008; bv.segments = 3; bv.limit_method = "ANGLE"
    S.uv_box(o, 0.9)
    return o


def _asset(aid, name, loc, rot, s, c, lod=0):
    if not (S.ASSETS / "polyhaven" / aid).exists():
        return []
    return [S.place(me, f"{name}_{i}", loc, c, rot, s) for i, me in enumerate(S.ph_variants(aid, lod=lod))]


def build(lit=False):
    c = BW.fresh("YARD"); CLEAR.clear()
    stone = S.ph_material("granite_tile", "path_granite")
    # stepping-stone path: deck step -> pier steps, a gentle S-curve
    p0, p1 = Vector((4.75, 0.5)), Vector((17.9, 4.6)); n = 23
    pts = []
    for i in range(n):
        t = i / (n - 1); p = p0.lerp(p1, t); p.y += 0.25 * math.sin(t * math.pi) - 0.55 * math.sin(2 * t * math.pi)
        pts.append(p)
        ang = math.atan2(p1.y - p0.y, p1.x - p0.x) + R.normal(0, 0.25)
        _slab(f"step_stone_{i}", p.x + R.normal(0, 0.03), p.y + R.normal(0, 0.05), ang, R.uniform(0.50, 0.62), R.uniform(0.36, 0.46), c, stone)
        CLEAR.append((p.x, p.y, 0.31))
    # low path lights beside every 5th stone
    alu = S.mat_simple("bollard_alu", (0.03, 0.032, 0.035), rough=0.4, metal=0.8)
    lens = bpy.data.materials.new("bollard_lens"); lens.use_nodes = True
    N, L = lens.node_tree.nodes, lens.node_tree.links; N.clear(); out = N.new("ShaderNodeOutputMaterial")
    if lit:
        em = N.new("ShaderNodeEmission"); bb = N.new("ShaderNodeBlackbody"); bb.inputs["Temperature"].default_value = 2700
        L.new(bb.outputs[0], em.inputs["Color"]); em.inputs["Strength"].default_value = 40; L.new(em.outputs[0], out.inputs["Surface"])
    else:
        d = N.new("ShaderNodeBsdfPrincipled"); d.inputs["Base Color"].default_value = (0.85, 0.85, 0.82, 1); d.inputs["Roughness"].default_value = 0.3
        L.new(d.outputs[0], out.inputs["Surface"])
    nb = 0
    for i in range(2, n - 1, 5):
        p = pts[i]; x, y = p.x + 0.15, p.y - 0.55; g = BW.ground_z(x, y)
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.035, depth=0.42, location=(x, y, g + 0.21))
        o = bpy.context.object; o.name = f"bollard_{nb}"; S.link(o, c); o.data.materials.append(alu)
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.033, depth=0.05, location=(x, y, g + 0.445))
        o = bpy.context.object; o.name = f"bollard_lens_{nb}"; S.link(o, c); o.data.materials.append(lens)
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.045, depth=0.012, location=(x, y, g + 0.476))
        o = bpy.context.object; o.name = f"bollard_cap_{nb}"; S.link(o, c); o.data.materials.append(alu)
        if lit:
            Lp = bpy.data.lights.new(f"bollard_light_{nb}", "POINT"); Lp.energy = 9; Lp.shadow_soft_size = 0.03; Lp.use_nodes = True
            bb = Lp.node_tree.nodes.new("ShaderNodeBlackbody"); bb.inputs["Temperature"].default_value = 2700
            Lp.node_tree.links.new(bb.outputs[0], Lp.node_tree.nodes["Emission"].inputs["Color"])
            lo = bpy.data.objects.new(f"bollard_light_{nb}", Lp); c.objects.link(lo); lo.location = (x + 0.06, y, g + 0.44)
        nb += 1
    # bistro set + fire bowl on the lawn, north side (clear of the pergola zone and of the camera foregrounds)
    bx, by = 12.8, -3.5; g = BW.ground_z(bx, by)          # the bistro set sits by the fire bowl: one fire-pit corner
    _asset("outdoor_table_chair_set_01", "bistro", (bx, by, g), 0.7, 1.0, c)
    fx, fy = 11.4, -2.5; g = BW.ground_z(fx, fy)
    corten = S.mat_simple("corten_steel", (0.21, 0.095, 0.045), rough=0.85)
    S.lathe("fire_bowl", [(0.0001, 0.12), (0.12, 0.125), (0.30, 0.19), (0.40, 0.30), (0.405, 0.305), (0.395, 0.31), (0.29, 0.205),
                          (0.12, 0.14), (0.0001, 0.135)], c, corten, seg=64).location = (fx, fy, g)
    for k in range(3):
        a = k * 2.094 + 0.4
        S.box(f"fire_bowl_leg_{k}", (0.03, 0.03, 0.19), (fx + 0.2 * math.cos(a), fy + 0.2 * math.sin(a), g + 0.085), c, corten)
    for i, me in enumerate(S.ph_variants("dry_branches_medium_01") if (S.ASSETS / "polyhaven" / "dry_branches_medium_01").exists() else []):
        S.place(me, f"fire_wood_{i}", (fx, fy, g + 0.2), c, i * 1.3, 0.5, tilt=0.05)
    # planted boxes along the south fence
    shrubs = S.ph_variants("shrub_02") + S.ph_variants("shrub_03"); tufts = S.ph_variants("grass_medium_01")
    for k, x in enumerate((6.2, 9.4, 12.6)):
        y = -9.55; g = BW.ground_z(x, y)
        _asset("planter_box_02", f"fence_planter_{k}", (x, y, g), 0.0, 1.25, c)
        for j, dx in enumerate((-0.5, -0.1, 0.35)):
            me = shrubs[(k * 3 + j) % len(shrubs)] if shrubs else None
            if me:
                S.place(me, f"fence_shrub_{k}_{j}", (x + dx, y, g + 0.5), c, R.uniform(0, 6.28), R.uniform(0.5, 0.75))
        if tufts:
            S.place(tufts[k % len(tufts)], f"fence_tuft_{k}", (x + 0.6, y + 0.05, g + 0.5), c, R.uniform(0, 6.28), 0.7)
    # rock + ornamental grass group near the dune, south-east
    if (S.ASSETS / "polyhaven" / "boulder_01").exists():
        b = S.ph_variants("boulder_01")
        for k, (x, y, s, rz) in enumerate(((14.8, -6.6, 0.55, 0.3), (15.7, -6.0, 0.32, 2.1), (14.2, -5.8, 0.22, 4.0))):
            S.place(b[0], f"yard_boulder_{k}", (x, y, BW.ground_z(x, y) - 0.12 * s), c, rz, s)
        for k in range(9):
            a = R.uniform(0, 6.28); r = R.uniform(0.5, 1.3); x, y = 14.9 + r * math.cos(a), -6.2 + r * math.sin(a)
            if tufts:
                S.place(tufts[k % len(tufts)], f"yard_tuft_{k}", (x, y, BW.ground_z(x, y) - 0.02), c, R.uniform(0, 6.28), R.uniform(0.7, 1.1))
    # pots on the deck corners + lanterns by the step
    deck = bpy.data.objects.get("deck_boards")
    zd = max((deck.matrix_world @ Vector(v)).z for v in deck.bound_box) if deck else 0.0
    for k, (x, y, aid, s) in enumerate(((3.45, -5.25, "potted_plant_01", 1.0), (3.45, 5.3, "potted_plant_02", 1.0))):
        _asset(aid, f"deck_pot_{k}", (x, y, zd), R.uniform(0, 6.28), s, c)
    for k, (x, y) in enumerate(((3.55, 2.75), (3.4, 3.05))):
        _asset("Lantern_01", f"deck_lantern_{k}", (x, y, zd), R.uniform(0, 6.28), 1.6 - 0.4 * k, c)
    LOG.append(f"yard: {n}-stone granite path deck->pier with {nb} low path lights ({'lit' if lit else 'off'}), bistro set + corten "
               f"fire bowl with logs, 3 planted boxes on the fence, rock + grass group by the dune, pots and lanterns on the deck")
    return LOG
