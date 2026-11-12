"""RIVON THE STORM - world: modern Polish house, porcelain terrace, lawn, garden, dining table + tableware, RIVON pergola.
Coordinates: terrace top z=0, pergola centred at origin (x +-1.75 m, y +-3.0 m, 6 m along Y), house facade at x=-3.0 facing +X,
garden towards +X. Every builder is idempotent (re-running replaces its collection)."""
import sys, math
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix
import storm_lib as S

FILM = S.ROOT.parent / "rivon_film"          # validated pergola layout + builder from the earlier film (exact STEP meshes)


def fresh(name):
    c = bpy.data.collections.get(name)
    if c:
        for o in list(c.all_objects):
            bpy.data.objects.remove(o, do_unlink=True)
    return S.coll(name)


def mat_scaled(aid, size_m, name=None, variant=None):
    m = S.ph_material(aid, name)
    return m


# ------------------------------------------------------------------ house
FAC_X = -3.0              # facade plane (garden side)
H_DEPTH, H_W = 10.0, 13.0  # house footprint (x into the house, y width)
FL1, FL2 = 3.05, 3.0       # storey heights (finished floor to floor)
PLINTH = 0.32


def wall_with_openings(name, c, x0, y0, y1, z0, z1, thick, openings, mat):
    """Facade slab in the YZ plane at x=x0 (outer face), extruding -X by `thick`, with rectangular openings
    [(ya, yb, za, zb)]. Built as a bmesh grid of quads so there are no booleans and reveals are real geometry."""
    ys = sorted({y0, y1, *[o[0] for o in openings], *[o[1] for o in openings]})
    zs = sorted({z0, z1, *[o[2] for o in openings], *[o[3] for o in openings]})
    bm = bmesh.new()
    def is_open(yc, zc):
        return any(a < yc < b and za < zc < zb for a, b, za, zb in openings)
    vmap = {}
    def V(x, y, z):
        k = (round(x, 5), round(y, 5), round(z, 5))
        if k not in vmap:
            vmap[k] = bm.verts.new(k)
        return vmap[k]
    xi = x0 - thick
    for i in range(len(ys) - 1):
        for j in range(len(zs) - 1):
            ya, yb, za, zb = ys[i], ys[i + 1], zs[j], zs[j + 1]
            if is_open((ya + yb) / 2, (za + zb) / 2):
                continue
            bm.faces.new([V(x0, ya, za), V(x0, yb, za), V(x0, yb, zb), V(x0, ya, zb)])          # outer
            bm.faces.new([V(xi, ya, zb), V(xi, yb, zb), V(xi, yb, za), V(xi, ya, za)])          # inner
    for a, b, za, zb in openings:                                                              # reveals
        bm.faces.new([V(x0, a, za), V(xi, a, za), V(xi, b, za), V(x0, b, za)])
        bm.faces.new([V(x0, b, zb), V(xi, b, zb), V(xi, a, zb), V(x0, a, zb)])
        bm.faces.new([V(x0, a, zb), V(xi, a, zb), V(xi, a, za), V(x0, a, za)])
        bm.faces.new([V(x0, b, za), V(xi, b, za), V(xi, b, zb), V(x0, b, zb)])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); c.objects.link(ob); me.materials.append(mat)
    S.uv_box(ob, 1.0)
    return ob


def window_unit(name, c, x_out, ya, yb, za, zb, frame_mat, glass_mat, mullions=(), sliding=False):
    """Aluminium window/door: 70 mm frame profile set 120 mm behind the facade, double glazing (2 x 6 mm panes, 16 mm gap),
    optional vertical mullions. Frame is built from bevelled boxes (real depth, not a texture)."""
    x = x_out - 0.12; fw, fd = 0.07, 0.075
    parts = []
    W, H = yb - ya, zb - za
    parts.append(S.box(f"{name}_top", (fd, W, fw), (x, (ya + yb) / 2, zb - fw / 2), c, frame_mat, bevel=0.003))
    parts.append(S.box(f"{name}_bot", (fd, W, fw), (x, (ya + yb) / 2, za + fw / 2), c, frame_mat, bevel=0.003))
    parts.append(S.box(f"{name}_l", (fd, fw, H), (x, ya + fw / 2, (za + zb) / 2), c, frame_mat, bevel=0.003))
    parts.append(S.box(f"{name}_r", (fd, fw, H), (x, yb - fw / 2, (za + zb) / 2), c, frame_mat, bevel=0.003))
    cuts = [ya + fw] + [m for m in mullions] + [yb - fw]
    for m in mullions:
        parts.append(S.box(f"{name}_m{m:.2f}", (fd, fw * 1.4 if sliding else fw, H - 2 * fw), (x - (0.012 if sliding else 0), m, (za + zb) / 2), c, frame_mat, bevel=0.003))
    for i in range(len(cuts) - 1):
        a = cuts[i] + (fw * 0.7 if i > 0 else 0); b = cuts[i + 1] - (fw * 0.7 if i < len(cuts) - 2 else 0)
        for k, dx in enumerate((-0.012, 0.022)):
            g = S.box(f"{name}_g{i}{k}", (0.006, b - a, H - 2 * fw), (x + dx, (a + b) / 2, (za + zb) / 2), c, glass_mat)
            parts.append(g)
    # aluminium sill (parapet) outside, 2% fall
    if not sliding:
        s = S.box(f"{name}_sill", (0.16, W + 0.06, 0.025), (x_out + 0.03, (ya + yb) / 2, za - 0.012), c, frame_mat, bevel=0.002)
        s.rotation_euler.y = math.radians(-2.5); parts.append(s)
    return parts


def build_house():
    c = fresh("HOUSE")
    plaster = S.ph_material("white_plaster_02", "facade_plaster")
    if "tinted" not in plaster:                                  # fresh silicone render: warm white, scan kept for micro-relief
        S.calm_albedo(plaster, (0.80, 0.785, 0.75), keep=0.18); plaster["tinted"] = 1
    clad = S.ph_material("oak_veneer_01", "facade_cladding_oak")
    plinth = S.ph_material("concrete_floor_02", "plinth_concrete")
    frame = S.mat_simple("alu_RAL7016", (0.032, 0.036, 0.040), rough=0.42, metal=0.85)
    coping = S.mat_simple("coping_RAL7016", (0.04, 0.045, 0.05), rough=0.5, metal=0.8)
    glass = S.mat_glass("window_glass", (0.94, 0.97, 0.96, 1))
    interior_floor = S.ph_material("wood_planks", "interior_floor")
    interior_wall = S.mat_simple("interior_wall", (0.78, 0.76, 0.72), rough=0.85)
    y0, y1 = -H_W / 2, H_W / 2
    z_top = PLINTH + FL1 + FL2 + 0.55         # attic parapet of a flat-roof house
    # ground-floor sliding doors to the terrace (pergola in front), upstairs windows
    door = (-2.55, 2.55, 0.02, 2.62)
    side_win = (3.45, 5.55, 0.95, 2.62)
    up = [(-5.4, -2.6, PLINTH + FL1 + 0.9, PLINTH + FL1 + 2.55), (-1.3, 1.3, PLINTH + FL1 + 0.9, PLINTH + FL1 + 2.55),
          (2.6, 5.4, PLINTH + FL1 + 0.9, PLINTH + FL1 + 2.55)]
    ops = [door, side_win, (-5.55, -3.45, 0.95, 2.62)] + up
    w = wall_with_openings("facade_W", c, FAC_X, y0, y1, -0.20, z_top, 0.42, ops, plaster)
    # wooden cladding panel on the left upper bay (recessed 30 mm) - warm accent typical of new Wielkopolska houses
    cl = S.box("cladding_panel", (0.03, 4.4, FL2 - 0.05), (FAC_X + 0.015, -4.0, PLINTH + FL1 + FL2 / 2 + 0.2), c, clad)
    S.uv_box(cl, 1.83)
    # cladding as vertical boards with 8 mm shadow gaps
    for i in range(22):
        yb = -6.2 + i * 0.2
        b = S.box(f"board_{i:02d}", (0.022, 0.192, FL2 + 0.15), (FAC_X + 0.035, yb, PLINTH + FL1 + FL2 / 2 + 0.17), c, None, bevel=0.002)
        b.data.materials.append(S.mat_variant(clad, f"oak_board_{i:02d}", hue_shift=float(S.RNG.normal(0, 0.006)),
                                              val=float(S.RNG.normal(1.0, 0.05)), uv_offset=(float(S.RNG.random()), float(S.RNG.random()))))
        S.uv_box(b, 1.83)
    cl.hide_render = True; cl.hide_viewport = True
    # plinth band (dark render) and parapet coping
    p = S.box("plinth", (0.025, H_W, PLINTH + 0.2), (FAC_X + 0.0125, 0, (PLINTH - 0.2) / 2), c, plinth); S.uv_box(p, 2.0)
    S.box("coping", (0.5, H_W + 0.1, 0.04), (FAC_X - 0.19, 0, z_top + 0.02), c, coping, bevel=0.004)
    # side and back walls + roof slab (simple, they are never close to camera)
    S.box("wall_S", (H_DEPTH, 0.42, z_top + 0.2), (FAC_X - H_DEPTH / 2, y0 + 0.21, z_top / 2 - 0.1), c, plaster)
    S.box("wall_N", (H_DEPTH, 0.42, z_top + 0.2), (FAC_X - H_DEPTH / 2, y1 - 0.21, z_top / 2 - 0.1), c, plaster)
    S.box("roof", (H_DEPTH, H_W, 0.3), (FAC_X - H_DEPTH / 2, 0, z_top - 0.45), c, interior_wall)
    for o in c.objects:
        if o.name.startswith("wall_"):
            S.uv_box(o, 1.0)
    # windows
    window_unit("door", c, FAC_X, *door[:2], door[2], door[3], frame, glass, mullions=(0.0,), sliding=True)
    window_unit("winR", c, FAC_X, *side_win[:2], side_win[2], side_win[3], frame, glass)
    window_unit("winL", c, FAC_X, -5.55, -3.45, 0.95, 2.62, frame, glass)
    for i, (a, b, za, zb) in enumerate(up):
        window_unit(f"up{i}", c, FAC_X, a, b, za, zb, frame, glass, mullions=((a + b) / 2,))
    # interior visible through the glass: floor, ceiling, back wall, warm pendant light
    f = S.box("int_floor", (6.0, H_W - 1, 0.05), (FAC_X - 3.4, 0, -0.005), c, interior_floor); S.uv_box(f, 1.5)
    S.box("int_ceiling", (6.0, H_W - 1, 0.05), (FAC_X - 3.4, 0, 2.85), c, interior_wall)
    S.box("int_back", (0.1, H_W - 1, 2.9), (FAC_X - 6.0, 0, 1.4), c, interior_wall)
    S.box("int_upper_floor", (6.0, H_W - 1, 0.25), (FAC_X - 3.4, 0, PLINTH + FL1 - 0.1), c, interior_wall)
    S.box("int_upper_back", (0.1, H_W - 1, FL2), (FAC_X - 5.0, 0, PLINTH + FL1 + FL2 / 2), c, interior_wall)
    return c


# ------------------------------------------------------------------ terrace + ground
TER = dict(x0=-3.0, x1=2.75, y0=-4.25, y1=4.25, h=0.16)


def build_ground():
    c = fresh("GROUND")
    tile_mat = S.ph_material("concrete_floor_02", "terrace_porcelain")   # "beton look" porcelain, one 60 cm patch per slab
    if "tinted" not in tile_mat:
        S.calm_albedo(tile_mat, (0.46, 0.44, 0.41), keep=0.35); tile_mat["tinted"] = 1
        S.principled(tile_mat).inputs["Specular IOR Level"].default_value = 0.5
    # 60x60 porcelain tiles as individual slabs (2 mm joints, +-0.4 mm height scatter, own UV offset) -> real joints & glints
    sz, gap, th = 0.596, 0.004, 0.02
    nx = int((TER["x1"] - TER["x0"]) / 0.6); ny = int((TER["y1"] - TER["y0"]) / 0.6)
    verts, faces, uvs = [], [], []
    for i in range(nx):
        for j in range(ny):
            cx = TER["x0"] + 0.3 + i * 0.6; cy = TER["y0"] + 0.3 + j * 0.6
            dz = float(S.RNG.normal(0, 0.0004)); tilt = S.RNG.normal(0, 0.0006, 2)
            ou, ov = float(S.RNG.random()) * 0.7, float(S.RNG.random()) * 0.7      # random 60 cm patch of the 2 m scan
            b = len(verts)
            for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                z = dz + sx * tilt[0] * sz / 2 + sy * tilt[1] * sz / 2
                verts.append((cx + sx * sz / 2, cy + sy * sz / 2, z)); uvs.append((ou + (sx + 1) * 0.15, ov + (sy + 1) * 0.15))
            for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                verts.append((cx + sx * sz / 2, cy + sy * sz / 2, -th)); uvs.append((ou, ov))
            faces += [(b, b + 1, b + 2, b + 3), (b + 4, b + 7, b + 6, b + 5), (b, b + 4, b + 5, b + 1), (b + 1, b + 5, b + 6, b + 2),
                      (b + 2, b + 6, b + 7, b + 3), (b + 3, b + 7, b + 4, b)]
    tiles = S.mesh_obj("terrace_tiles", verts, faces, c, tile_mat)
    uvl = tiles.data.uv_layers.new(name="UVMap")
    for li, l in enumerate(tiles.data.loops):
        uvl.data[li].uv = uvs[l.vertex_index]
    bv = tiles.modifiers.new("arris", "BEVEL"); bv.width = 0.0012; bv.segments = 2; bv.limit_method = "ANGLE"
    grout = S.mat_simple("grout", (0.11, 0.105, 0.10), rough=0.95)
    S.box("terrace_bed", (TER["x1"] - TER["x0"], TER["y1"] - TER["y0"], 0.14), ((TER["x0"] + TER["x1"]) / 2, 0, -0.09), c, grout)
    # concrete edging kerb (obrzeże) around the terrace
    kerb = S.ph_material("concrete_floor_02", "kerb_concrete")
    for nm, size, loc in [("kerb_E", (0.06, TER["y1"] - TER["y0"] + 0.12, 0.25), (TER["x1"] + 0.03, 0, -0.105)),
                          ("kerb_S", (TER["x1"] - TER["x0"], 0.06, 0.25), ((TER["x0"] + TER["x1"]) / 2, TER["y0"] - 0.03, -0.105)),
                          ("kerb_N", (TER["x1"] - TER["x0"], 0.06, 0.25), ((TER["x0"] + TER["x1"]) / 2, TER["y1"] + 0.03, -0.105))]:
        k = S.box(nm, size, loc, c, kerb, bevel=0.004); S.uv_box(k, 2.0)
    build_lawn(c)
    return c


def build_lawn(c):
    """Lawn = soil plane with gentle undulation + Cycles hair grass (curves): 3 blade colours, length 3-9 cm, clumped,
    density falls with distance from the terrace so the far lawn costs little."""
    soil = S.ph_material("forrest_ground_01", "lawn_soil")
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=240, y_subdivisions=240, size=60, location=(27.0, 0, -TER["h"]))
    g = bpy.context.object; g.name = "lawn"; S.link(g, c); g.data.materials.append(soil)
    for v in g.data.vertices:
        wx, wy = v.co.x + 27.0, v.co.y
        if wx < TER["x1"] + 0.08 and abs(wy) < TER["y1"] + 0.08:
            v.co.z = -0.5                     # under the terrace: drop out of sight
        else:
            v.co.z = 0.025 * math.sin(wx * 0.9) * math.cos(wy * 0.7) + 0.012 * math.sin(wx * 3.1 + wy * 2.3)
    S.uv_box(g, 2.0)
    # density vertex group: dense near the terrace / camera paths
    vg = g.vertex_groups.new(name="density")
    for v in g.data.vertices:
        d = math.hypot(v.co.x + 27.0 - 4.0, v.co.y)
        vg.add([v.index], max(0.04, min(1.0, 1.4 - d / 14.0)) if v.co.z > -0.4 else 0.0, "REPLACE")
    blade = bpy.data.materials.new("grass_blade"); blade.use_nodes = True
    N, L = blade.node_tree.nodes, blade.node_tree.links
    pb = S.principled(blade)
    hi = N.new("ShaderNodeHairInfo"); ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.035, 0.06, 0.012, 1); ramp.color_ramp.elements[1].color = (0.20, 0.30, 0.06, 1)
    e = ramp.color_ramp.elements.new(0.55); e.color = (0.09, 0.17, 0.03, 1)
    rnd = N.new("ShaderNodeValToRGB"); rnd.color_ramp.elements[0].color = (0.85, 0.95, 0.75, 1); rnd.color_ramp.elements[1].color = (1.15, 1.05, 0.8, 1)
    L.new(hi.outputs["Intercept"], ramp.inputs["Fac"]); L.new(hi.outputs["Random"], rnd.inputs["Fac"])
    mul = N.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs["Factor"].default_value = 1.0
    L.new(ramp.outputs["Color"], mul.inputs[6]); L.new(rnd.outputs["Color"], mul.inputs[7])
    L.new(mul.outputs[2], pb.inputs["Base Color"])
    pb.inputs["Roughness"].default_value = 0.45; pb.inputs["Subsurface Weight"].default_value = 0.0
    pb.inputs["Transmission Weight"].default_value = 0.0
    pb.inputs["Sheen Weight"].default_value = 0.15
    g.data.materials.append(blade)
    ps = g.modifiers.new("grass", "PARTICLE_SYSTEM").particle_system
    st = ps.settings; st.type = "HAIR"; st.count = 40000 if S.PREVIEW else 260000; st.hair_length = 0.07; st.use_advanced_hair = True
    st.material = 2; st.emit_from = "FACE"; st.use_emit_random = True
    st.child_type = "INTERPOLATED"; st.child_percent = 6; st.rendered_child_count = 2 if S.PREVIEW else 6
    st.length_random = 0.6; st.roughness_1 = 0.012; st.roughness_endpoint = 0.02; st.roughness_2 = 0.006
    st.clump_factor = 0.15; st.child_length = 1.0; st.child_length_threshold = 0.3
    st.root_radius = 1.0; st.tip_radius = 0.0; st.radius_scale = 0.0022
    st.use_rotations = True; st.rotation_factor_random = 0.25
    st.normal_factor = 0.06; st.tangent_factor = 0.003; st.factor_random = 0.012
    ps.vertex_group_density = "density"
    ps.seed = 7
    return g


# ------------------------------------------------------------------ table + tableware
def build_table():
    c = fresh("TABLE")
    oak = S.ph_material("oak_veneer_01", "table_oak")
    steel = S.mat_powder_coat()
    L, W, Ht, T = 2.2, 0.98, 0.75, 0.045
    # solid oak top from 5 glued staves (each own grain patch) with eased edges
    for i in range(5):
        s = S.box(f"top_{i}", (W / 5 - 0.0004, L, T), (-W / 2 + W / 10 + i * W / 5, 0, Ht - T / 2), c, None, bevel=0.003)
        s.data.materials.append(S.mat_variant(oak, f"table_oak_{i}", hue_shift=float(S.RNG.normal(0, 0.004)),
                                              val=float(S.RNG.normal(1.0, 0.035)), uv_offset=(float(S.RNG.random()), float(S.RNG.random()))))
        S.uv_box(s, 1.83)
        # rotate UVs so the grain runs along the stave (top face projects xy -> swap)
    for sy in (-1, 1):                                    # black steel sled legs (40x40 tube)
        y = sy * (L / 2 - 0.22)
        for nm, size, loc in [("legA", (0.04, 0.04, Ht - T), (-W / 2 + 0.08, y, (Ht - T) / 2)),
                              ("legB", (0.04, 0.04, Ht - T), (W / 2 - 0.08, y, (Ht - T) / 2)),
                              ("rail", (W - 0.12, 0.04, 0.04), (0, y, Ht - T - 0.02)),
                              ("foot", (W - 0.12, 0.04, 0.02), (0, y, 0.01))]:
            S.box(f"{nm}{sy}", size, loc, c, steel, bevel=0.003)
    build_tableware(c, Ht)
    return c


def build_tableware(c, ht):
    glass = S.mat_glass("wine_glass", (1, 1, 1, 1))
    wine = bpy.data.materials.new("red_wine"); wine.use_nodes = True; wb = S.principled(wine)
    wb.inputs["Base Color"].default_value = (0.35, 0.01, 0.03, 1); wb.inputs["Transmission Weight"].default_value = 1.0
    wb.inputs["IOR"].default_value = 1.35; wb.inputs["Roughness"].default_value = 0.0
    vol = wine.node_tree.nodes.new("ShaderNodeVolumeAbsorption"); vol.inputs["Color"].default_value = (0.55, 0.02, 0.05, 1)
    vol.inputs["Density"].default_value = 60
    wine.node_tree.links.new(vol.outputs[0], wine.node_tree.nodes["Material Output"].inputs["Volume"])
    porcelain = S.mat_simple("porcelain", (0.86, 0.85, 0.82), rough=0.12, spec=0.5)
    pbz = S.principled(porcelain); pbz.inputs["Subsurface Weight"].default_value = 0.15
    pbz.inputs["Subsurface Radius"].default_value = (0.003, 0.003, 0.003); pbz.inputs["Coat Weight"].default_value = 0.6
    cutlery = S.mat_simple("cutlery_steel", (0.62, 0.62, 0.62), rough=0.18, metal=1.0)
    # Bordeaux glass: 1.1 mm wall, 0.9 mm rim, 6 mm stem, 75 mm foot, 225 mm tall (real proportions)
    def bowl_r(t):  # t 0..1 bottom->rim
        return 0.0395 * math.sin(math.pi * (0.12 + 0.72 * t)) ** 0.85 + 0.004
    out = [(0.0001, 0), (0.0375, 0.0), (0.038, 0.002), (0.012, 0.004), (0.004, 0.012), (0.0032, 0.03), (0.0032, 0.09), (0.006, 0.1)]
    out += [(bowl_r(t), 0.1 + 0.125 * t) for t in np.linspace(0.02, 1.0, 34)]
    inner = [(bowl_r(t) - 0.0011, 0.1 + 0.125 * t) for t in np.linspace(1.0, 0.04, 34)] + [(0.0001, 0.104)]
    prof = out + inner
    wine_prof = [(0.0001, 0.104)] + [(bowl_r(t) - 0.0012, 0.1 + 0.125 * t) for t in np.linspace(0.04, 0.34, 14)]
    wine_prof += [(0.0001, 0.1 + 0.125 * 0.34)]
    place = [(-0.22, -0.42), (0.22, 0.38)]
    for k, (gx, gy) in enumerate(place):
        g = S.lathe(f"wine_glass_{k}", prof, c, glass); g.location = (gx + 0.12, gy + 0.2, ht)
        w = S.lathe(f"wine_{k}", wine_prof, c, wine); w.location = g.location
        # dinner plate 27 cm with rim + side plate
        pl = S.lathe(f"plate_{k}", [(0.0001, 0.0), (0.06, 0.0), (0.062, 0.006), (0.105, 0.008), (0.135, 0.02), (0.1355, 0.022),
                                    (0.1325, 0.022), (0.104, 0.0115), (0.06, 0.0095), (0.0001, 0.0095)], c, porcelain)
        pl.location = (gx, gy, ht + 0.0002)
        for sx, ln in ((-1, 0.2), (1, 0.21)):
            cu = S.box(f"cutlery_{k}{sx}", (0.012, ln, 0.0025), (gx, gy + sx * 0.165, ht + 0.0015), c, cutlery, bevel=0.001)
            cu.rotation_euler.z = math.radians(90 + S.RNG.normal(0, 1.5))
    # 750 ml Bordeaux bottle: 300 mm, 75 mm body, dark green glass + cork
    bott = S.mat_glass("bottle_glass", (0.08, 0.16, 0.08, 1))
    S.principled(bott).inputs["Base Color"].default_value = (0.12, 0.25, 0.13, 1)
    bp = [(0.0001, 0.0), (0.035, 0.0), (0.0375, 0.006), (0.0375, 0.205), (0.033, 0.23), (0.016, 0.255), (0.0145, 0.29),
          (0.0155, 0.292), (0.0155, 0.30), (0.0105, 0.30), (0.0105, 0.29), (0.0123, 0.255), (0.029, 0.23), (0.0335, 0.205),
          (0.0335, 0.008), (0.012, 0.025), (0.0001, 0.026)]
    b = S.lathe("wine_bottle", bp, c, bott); b.location = (0.05, 0.02, ht)
    cork = S.mat_simple("cork", (0.45, 0.33, 0.2), rough=0.8)
    ck = S.lathe("cork", [(0.0001, 0.27), (0.0103, 0.27), (0.0103, 0.305), (0.0001, 0.305)], c, cork); ck.location = b.location
    wl = S.lathe("bottle_wine", [(0.0001, 0.027), (0.033, 0.009), (0.033, 0.2), (0.0001, 0.2)], c, wine); wl.location = b.location
    return c


def build_napkin(c, ht):
    """Linen napkin 45x45 cm, 1.2 mm, folded once; subdivided for cloth simulation (simulated in weather pass)."""
    lin = S.ph_material("rough_linen", "napkin_linen")
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=64, y_subdivisions=64, size=0.45, location=(0.25, -0.15, ht + 0.0025))
    n = bpy.context.object; n.name = "napkin"; S.link(n, c); n.data.materials.append(lin)
    n.rotation_euler.z = math.radians(17)
    so = n.modifiers.new("thick", "SOLIDIFY"); so.thickness = 0.0012
    return n


# ------------------------------------------------------------------ pergola (exact STEP meshes, validated layout)
def build_pergola():
    sys.path.insert(0, str(FILM))
    import film_lib as FL
    c_old = bpy.data.collections.get("PERGOLA")
    if c_old:
        for o in list(c_old.all_objects):
            bpy.data.objects.remove(o, do_unlink=True)
    root = FL.build_pergola("PERGOLA")
    powder = S.mat_powder_coat()
    import glob
    wood_id = next((w for w in ("coated_pine", "stained_pine", "fine_grained_wood", "oak_veneer_01")
                    if glob.glob(str(S.ASSETS / "polyhaven" / w / "*.blend"))), "oak_veneer_01")
    beams = S.ph_material(wood_id, "pergola_timber_base")
    bpy.context.view_layer.update()
    for o in bpy.data.collections["PERGOLA"].all_objects:
        if o.type != "MESH" or not o.data.materials:
            continue
        mname = o.data.materials[0].name
        if mname.startswith("RIVON"):
            o.data.materials[0] = powder
        elif "pine" in mname.lower() or o.name.startswith(("POST", "BEAM", "RAFTER", "LONG", "END")):
            # every timber member gets its own grain patch and a slight tone shift (no two identical boards)
            o.data = o.data.copy()
            o.data.materials[0] = S.mat_variant(beams, f"timber_{o.name}", hue_shift=float(S.RNG.normal(0, 0.005)),
                                                val=float(S.RNG.normal(1.0, 0.045)),
                                                uv_offset=(float(S.RNG.random() * 3), float(S.RNG.random() * 3)))
            uv_along_grain(o)
    return root


def uv_along_grain(ob, size=1.2):
    """UVs with V along the member's long axis so wood grain runs lengthwise; end-grain faces get a small-scale patch."""
    me = ob.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    uv = me.uv_layers.active.data
    co = np.array([list(v.co) for v in me.vertices]); ext = co.max(0) - co.min(0); ax = int(np.argmax(ext))
    others = [i for i in range(3) if i != ax]
    for p in me.polygons:
        n = np.abs(np.array(p.normal)); facing_end = int(np.argmax(n)) == ax
        for li in p.loop_indices:
            v = co[me.loops[li].vertex_index]
            if facing_end:
                uv[li].uv = (v[others[0]] / size * 0.25 + 0.5, v[others[1]] / size * 0.25 + 0.5)
            else:
                side = others[0] if int(np.argmax(n)) == others[1] else others[1]
                uv[li].uv = (v[side] / size, v[ax] / size)


def build_all(with_pergola=True):
    build_house(); build_ground(); build_table()
    if with_pergola:
        build_pergola()


# ------------------------------------------------------------------ garden (Poly Haven scanned vegetation, varied instances)
def build_garden():
    c = fresh("GARDEN")
    zg = -TER["h"]
    rnd = S.RNG
    mulch = S.ph_material("forrest_ground_01", "bed_mulch")
    # planting beds: along the south terrace edge and a long border on the south boundary
    beds = [(TER["x1"] + 0.15, TER["x1"] + 1.15, TER["y0"] - 0.2, TER["y1"] * 0.2),       # in front of the terrace (garden side)
            (3.0, 15.0, -9.6, -8.2), (3.0, 15.0, 8.2, 9.6)]                                 # side borders
    for i, (xa, xb, ya, yb) in enumerate(beds):
        b = S.box(f"bed_{i}", (xb - xa, yb - ya, 0.04), ((xa + xb) / 2, (ya + yb) / 2, zg + 0.005), c, mulch); S.uv_box(b, 2.0)
    shrubs = (S.ph_variants("shrub_01") + S.ph_variants("shrub_02") + S.ph_variants("shrub_03") + S.ph_variants("shrub_04")
              + S.ph_variants("shrub_sorrel_01"))
    flowers = S.ph_variants("celandine_01") + S.ph_variants("dandelion_01")
    ferns = S.ph_variants("fern_02")
    meadow = S.ph_variants("grass_medium_02")
    n = 0
    for xa, xb, ya, yb in beds:
        area = (xb - xa) * (yb - ya)
        for _ in range(int(area * 2.2)):
            me = shrubs[rnd.integers(len(shrubs))]
            S.place(me, f"shrub_{n:04d}", (rnd.uniform(xa, xb), rnd.uniform(ya, yb), zg), c, rnd.uniform(0, 6.28),
                    rnd.uniform(0.8, 1.35), tilt=0.05); n += 1
        for _ in range(int(area * 6)):
            me = flowers[rnd.integers(len(flowers))]
            S.place(me, f"flower_{n:04d}", (rnd.uniform(xa, xb), rnd.uniform(ya, yb), zg), c, rnd.uniform(0, 6.28),
                    rnd.uniform(0.7, 1.2), tilt=0.08); n += 1
        for _ in range(int(area * 0.8)):
            me = ferns[rnd.integers(len(ferns))]
            S.place(me, f"fern_{n:04d}", (rnd.uniform(xa, xb), rnd.uniform(ya, yb), zg), c, rnd.uniform(0, 6.28),
                    rnd.uniform(0.6, 1.0), tilt=0.06); n += 1
    # a few meadow tufts where the lawn meets the border (unmown edge)
    for _ in range(60):
        y = rnd.choice([-1, 1]) * rnd.uniform(7.9, 8.3); x = rnd.uniform(3, 15)
        S.place(meadow[rnd.integers(len(meadow))], f"tuft_{n:04d}", (x, y, zg), c, rnd.uniform(0, 6.28), rnd.uniform(0.25, 0.45)); n += 1
    # conifer hedge on the back boundary (typical Polish plot) + specimen trees
    firs = S.ph_variants("fir_tree_01")
    for i in range(26):
        y = -12.5 + i * 1.0 + rnd.normal(0, 0.12)
        S.place(firs[rnd.integers(len(firs))], f"hedge_{i:02d}", (19.5 + rnd.normal(0, 0.15), y, zg), c, rnd.uniform(0, 6.28),
                rnd.uniform(0.17, 0.21), tilt=0.02)
    small = S.ph_variants("tree_small_02")
    for k, (x, y, s) in enumerate([(7.2, -6.3, 1.0), (13.5, 7.0, 1.15), (16.0, -3.0, 0.9)]):
        for me in small:
            S.place(me, f"tree_{k}_{me.name}", (x, y, zg), c, rnd.uniform(0, 6.28) if False else 0.6 * k, s)
    pines = S.ph_variants("pine_tree_01") if False else []       # 570 MB; enabled for wide shots only (see build_far)
    rocks = S.ph_variants("rock_moss_set_01") if False else []
    return c


def build_fence(c=None):
    """Modern anthracite panel fence on the side boundaries (1.5 m), steel posts every 2.5 m."""
    c = c or fresh("FENCE")
    steel = S.mat_simple("fence_RAL7016", (0.035, 0.038, 0.042), rough=0.55, metal=0.6)
    zg = -TER["h"]
    for sy in (-1, 1):
        y = sy * 10.2
        for i in range(14):
            x0 = -14.5 + i * 2.5
            S.box(f"fpost_{sy}_{i}", (0.06, 0.06, 1.6), (x0, y, zg + 0.8), c, steel, bevel=0.003)
            for k in range(12):
                S.box(f"fslat_{sy}_{i}_{k}", (2.44, 0.02, 0.09), (x0 + 1.25, y, zg + 0.15 + k * 0.115), c, steel, bevel=0.002)
    return c


def build_surroundings():
    """What lies beyond the plot in every direction: neighbour houses (gable roofs, typical Poznan suburb), a ring of trees,
    so any camera heading has a believable, deep background."""
    c = fresh("SURROUND")
    rnd = S.RNG; zg = -TER["h"]
    render = S.ph_material("white_rough_plaster", "neighbour_render")
    roof = S.mat_simple("roof_tiles_graphite", (0.045, 0.045, 0.05), rough=0.55)
    win = S.mat_simple("neighbour_window", (0.02, 0.025, 0.03), rough=0.08, spec=0.8)
    def gable_house(name, x, y, w, d, h, rot):
        b = S.box(f"{name}_body", (d, w, h), (x, y, zg + h / 2), c, render, rot_z=rot); S.uv_box(b, 1.0)
        rh = 0.42 * d
        v = [(-d / 2 - 0.4, -w / 2 - 0.4, 0), (d / 2 + 0.4, -w / 2 - 0.4, 0), (0, -w / 2 - 0.4, rh),
             (-d / 2 - 0.4, w / 2 + 0.4, 0), (d / 2 + 0.4, w / 2 + 0.4, 0), (0, w / 2 + 0.4, rh)]
        f = [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (0, 2, 5, 3)]
        r = S.mesh_obj(f"{name}_roof", v, f, c, roof); r.location = (x, y, zg + h); r.rotation_euler.z = rot
        so = r.modifiers.new("t", "SOLIDIFY"); so.thickness = 0.25
        for k in range(3):                                    # dark window openings (seen only far away, through DOF)
            wv = S.box(f"{name}_win{k}", (d + 0.02, 1.2, 1.3), (x, y - w / 3 + k * w / 3, zg + 1.6), c, win, rot_z=rot)
    gable_house("nbS", 2.0, -19.0, 11.0, 9.0, 5.6, 0.0)
    gable_house("nbN", 4.0, 19.5, 12.0, 8.5, 5.4, 0.0)
    gable_house("nbE", 32.0, -6.0, 10.0, 9.0, 5.8, 1.5708)
    gable_house("nbE2", 33.0, 12.0, 11.0, 9.0, 5.5, 1.5708)
    small = S.ph_variants("tree_small_02"); firs = S.ph_variants("fir_tree_01")
    ring = [(x, y) for x in np.linspace(-14, 30, 12) for y in (-13.5, 13.5)] + [(26.0, y) for y in np.linspace(-12, 12, 7)]
    for k, (x, y) in enumerate(ring):
        x += rnd.normal(0, 1.2); y += rnd.normal(0, 0.8)
        if rnd.random() < 0.55:
            for me in small:
                S.place(me, f"ringtree_{k}_{me.name}", (x, y, zg), c, 0.9 * k, rnd.uniform(1.1, 1.6))
        else:
            S.place(firs[rnd.integers(len(firs))], f"ringfir_{k}", (x, y, zg), c, rnd.uniform(0, 6.28), rnd.uniform(0.35, 0.55))
    return c
