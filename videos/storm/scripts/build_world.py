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

FILM = S.ROOT.parent / "rivon_film"
SEASIDE = True            # owner: the plot ends at a Baltic beach with a wooden pier (background of the glass macro)          # validated pergola layout + builder from the earlier film (exact STEP meshes)


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
    # side walls / roof slab start 6 cm behind the facade skin: coplanar faces would z-fight (black bands in Cycles)
    S.box("wall_S", (H_DEPTH - 0.06, 0.42, z_top + 0.2), (FAC_X - 0.06 - (H_DEPTH - 0.06) / 2, y0 + 0.21, z_top / 2 - 0.1), c, plaster)
    S.box("wall_N", (H_DEPTH - 0.06, 0.42, z_top + 0.2), (FAC_X - 0.06 - (H_DEPTH - 0.06) / 2, y1 - 0.21, z_top / 2 - 0.1), c, plaster)
    S.box("roof", (H_DEPTH - 0.5, H_W - 0.9, 0.3), (FAC_X - 0.5 - (H_DEPTH - 0.5) / 2, 0, z_top - 0.45), c, interior_wall)
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


def ground_z(x, y=0.0):
    """Garden ground height: flat lawn by the terrace, then a 5 % fall towards the beach from x=8 m (the plot sits above the
    Baltic shore, so the sea is visible over the dune from table height)."""
    z = -TER["h"] + 0.025 * math.sin(x * 0.9) * math.cos(y * 0.7) + 0.012 * math.sin(x * 3.1 + y * 2.3)
    if SEASIDE and x > 8.0:
        z -= (min(x, 19.5) - 8.0) * 0.05
    return z


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
    if "tinted" not in soil:                                  # thatch under a mown lawn: green-brown, not forest litter
        S.calm_albedo(soil, (0.11, 0.14, 0.05), keep=0.5); soil["tinted"] = 1
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=240, y_subdivisions=240, size=60, location=(27.0, 0, -TER["h"]))
    g = bpy.context.object; g.name = "lawn"; S.link(g, c); g.data.materials.append(soil)
    for v in g.data.vertices:
        wx, wy = v.co.x + 27.0, v.co.y
        if wx < TER["x1"] + 0.08 and abs(wy) < TER["y1"] + 0.08:
            v.co.z = -0.5                     # under the terrace: drop out of sight
        elif SEASIDE and wx > 19.6:
            v.co.z = ground_z(19.5, wy) - 1.0  # beyond the plot: the dune mesh takes over
        else:
            v.co.z = ground_z(wx, wy) + TER["h"]
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
    st = ps.settings; st.type = "HAIR"; st.count = 90000 if S.PREVIEW else 300000; st.hair_length = 0.07; st.use_advanced_hair = True
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
    if "tinted" not in oak:                          # natural oiled oak (the raw scan reads pale / unfinished)
        S.tint(oak, (0.86, 0.70, 0.54), gain=0.95); oak["tinted"] = 1
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
    build_napkin(c, Ht)
    build_chairs(c, oak, steel)
    vase = S.ph_variants("ceramic_vase_01")
    if vase:
        v = S.place(vase[0], "vase", (-0.12, 0.35, Ht), c, 0.4, 0.75)
    return c


def chair(name, c, oak, steel, loc, rot):
    """Modern outdoor dining chair: 25x25 powder-coated steel frame, 5 oak seat slats, 3 back slats, back raked 9 deg."""
    e = bpy.data.objects.new(name, None); c.objects.link(e); e.location = loc; e.rotation_euler.z = rot
    sh, sw, sd = 0.455, 0.46, 0.47
    parts = []
    def add(o):
        o.parent = e; parts.append(o); return o
    for sx in (-1, 1):
        add(S.box(f"{name}_legF{sx}", (0.025, 0.025, sh - 0.02), (sd / 2 - 0.02, sx * (sw / 2 - 0.0125), (sh - 0.02) / 2), c, steel, bevel=0.003))
        rl = add(S.box(f"{name}_legB{sx}", (0.025, 0.025, 0.86), (-sd / 2 + 0.02, sx * (sw / 2 - 0.0125), 0.43), c, steel, bevel=0.003))
        rl.rotation_euler.y = math.radians(-4)
        add(S.box(f"{name}_rail{sx}", (sd - 0.04, 0.025, 0.03), (0, sx * (sw / 2 - 0.0125), sh - 0.035), c, steel, bevel=0.003))
    add(S.box(f"{name}_railF", (0.025, sw - 0.05, 0.03), (sd / 2 - 0.02, 0, sh - 0.035), c, steel, bevel=0.003))
    for k in range(5):
        sl = add(S.box(f"{name}_seat{k}", (0.082, sw - 0.01, 0.02), (sd / 2 - 0.05 - k * 0.09, 0, sh - 0.01), c, None, bevel=0.003))
        sl.data.materials.append(S.mat_variant(oak, f"{name}_oak_s{k}", val=float(S.RNG.normal(1.0, 0.05)),
                                               uv_offset=(float(S.RNG.random()), float(S.RNG.random()))))
        S.uv_box(sl, 1.83)
    for k in range(3):
        z = sh + 0.13 + k * 0.1
        bs = add(S.box(f"{name}_back{k}", (0.018, sw - 0.02, 0.075), (-sd / 2 + 0.005 - (z - sh) * math.tan(math.radians(9)), 0, z), c, None, bevel=0.003))
        bs.rotation_euler.y = math.radians(-9)
        bs.data.materials.append(S.mat_variant(oak, f"{name}_oak_b{k}", val=float(S.RNG.normal(1.0, 0.05)),
                                               uv_offset=(float(S.RNG.random()), float(S.RNG.random()))))
        S.uv_box(bs, 1.83)
    return e


def build_chairs(c, oak, steel):
    k = 0
    for sx in (-1, 1):
        for y in ((-0.72, 0.0, 0.72) if sx < 0 else (-0.78, 0.78)):
            pull = 0.86 + float(S.RNG.uniform(0.0, 0.1)); dy = float(S.RNG.normal(0, 0.03)); rz = float(S.RNG.normal(0, 0.06))
            if sx < 0 and y == 0.0:          # the chair opposite the hero glass was just pushed back by someone getting up:
                pull, dy, rz = 1.22, -0.3, 0.45 # keeps its back slats out of the glass reflection (were dark arcs in the wine)
            chair(f"chair_{k}", c, oak, steel, (sx * pull, y + dy, 0.0), (math.pi if sx > 0 else 0.0) + rz)
            k += 1


def build_tableware(c, ht):
    glass = S.mat_glass("wine_glass", (1, 1, 1, 1))
    wine = bpy.data.materials.new("red_wine"); wine.use_nodes = True; wb = S.principled(wine)
    wb.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1); wb.inputs["Transmission Weight"].default_value = 1.0
    wb.inputs["IOR"].default_value = 1.35; wb.inputs["Roughness"].default_value = 0.0
    vol = wine.node_tree.nodes.new("ShaderNodeVolumeAbsorption"); vol.inputs["Color"].default_value = (0.885, 0.0, 0.38, 1)
    vol.inputs["Density"].default_value = 700     # young red: near-opaque at 7 cm, ruby at the thin edge
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
    TW = 0.34                                                       # pour level (fraction of the bowl height)
    MEN = 0.0018                                                    # meniscus: wine climbs 1.8 mm up the wetted glass wall
    t_m = TW + MEN / 0.125
    rin = lambda t: bowl_r(t) - 0.0011
    ts_in = [t for t in np.linspace(1.0, 0.04, 40) if t > t_m] + [t_m]
    # rounded rim (fire-polished), then inner skin only ABOVE the meniscus line; below it the wine object owns the interface
    rim = [(bowl_r(1.0) - 0.00055 + 0.00045 * math.cos(a), 0.225 + 0.00045 * math.sin(a)) for a in np.linspace(0.0, math.pi, 7)[1:-1]]
    prof_wet = out + rim + [(rin(t), 0.1 + 0.125 * t) for t in ts_in]
    prof_dry = out + rim + [(rin(t), 0.1 + 0.125 * t) for t in np.linspace(1.0, 0.04, 40)] + [(0.0001, 0.104)]
    z_top = 0.1 + 0.125 * TW
    ts_w = list(np.linspace(0.04, t_m, 18))
    side = [(0.0, 0.104)] + [(rin(t), 0.1 + 0.125 * t) for t in ts_w]
    r_w = rin(t_m)
    # meniscus profile: concave rise over ~3.5 mm (capillary length of wine ~2.7 mm)
    men = [(r_w - d, z_top + MEN * math.exp(-d / 0.0011)) for d in (0.00015, 0.0004, 0.0008, 0.0014, 0.0022, 0.0035, 0.0055)]
    wine_prof = side + men + [(0.0, z_top)]
    n_side = len(side) - 1                                          # profile segments that touch glass (interface material)
    # glass->wine boundary: relative IOR 1.333/1.52 (no air film -> no false mirror); wine->air top: 1.333
    wine_side = wine.copy(); wine_side.name = "red_wine_glass_interface"
    S.principled(wine_side).inputs["IOR"].default_value = 1.333 / 1.52
    S.principled(wine).inputs["IOR"].default_value = 1.333
    place = [(0.18, -0.30), (-0.22, 0.38)]   # glass 0 = hero glass near the sea-side edge
    goff = [(0.12, 0.32), (0.12, 0.2)]       # hero setting 12 cm further from its glass: plate rim + knife were refracting
    for k, (gx, gy) in enumerate(place):     # through the wine as dark arcs in the macro
        g = S.lathe(f"wine_glass_{k}", prof_wet, c, glass); g.location = (gx + goff[k][0], gy + goff[k][1], ht)
        w = S.lathe(f"wine_{k}", wine_prof, c, wine); w.location = g.location
        w.data.materials.append(wine_side)
        nseg = len(wine_prof) - 1
        for pl in w.data.polygons:                                  # faces are emitted segment-major per ring
            k = pl.index % nseg
            pl.material_index = 1 if k < n_side else 0
        w.data.update()
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
    b = S.lathe("wine_bottle", bp, c, bott); b.location = (-0.24, 0.05, ht)
    cork = S.mat_simple("cork", (0.45, 0.33, 0.2), rough=0.8)
    ck = S.lathe("cork", [(0.0001, 0.27), (0.0103, 0.27), (0.0103, 0.305), (0.0001, 0.305)], c, cork); ck.location = b.location
    wl = S.lathe("bottle_wine", [(0.0001, 0.027), (0.033, 0.009), (0.033, 0.2), (0.0001, 0.2)], c, wine); wl.location = b.location
    return c


def build_napkin(c, ht):
    """Linen napkin 45x45 cm, 1.2 mm, folded once; subdivided for cloth simulation (simulated in weather pass)."""
    lin = S.ph_material("rough_linen", "napkin_linen")
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=48, y_subdivisions=48, size=0.23, location=(0.17, -0.58, ht + 0.0025))   # folded in four, left of the hero plate (was under the hero glass: refracted as dark arcs)
    n = bpy.context.object; n.name = "napkin"; S.link(n, c); n.data.materials.append(lin)
    n.rotation_euler.z = math.radians(17)
    so = n.modifiers.new("thick", "SOLIDIFY"); so.thickness = 0.0045      # 4 layers of linen
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
    _gp = lambda x, y: (x, y, ground_z(x, y))
    mulch = S.ph_material("forrest_ground_01", "bed_mulch")
    # planting beds: along the south terrace edge and a long border on the south boundary
    beds = [(5.5, 10.0, -9.6, -8.2), (5.5, 10.0, 8.2, 9.6)]                              # side borders (front band: design.py)
    for i, (xa, xb, ya, yb) in enumerate(beds):
        b = S.box(f"bed_{i}", (xb - xa, yb - ya, 0.04), ((xa + xb) / 2, (ya + yb) / 2, ground_z((xa + xb) / 2, (ya + yb) / 2) + 0.005), c, mulch); S.uv_box(b, 2.0)
    shrubs = (S.ph_variants("shrub_01") + S.ph_variants("shrub_02") + S.ph_variants("shrub_03") + S.ph_variants("shrub_04")
              + S.ph_variants("shrub_sorrel_01"))
    flowers = S.ph_variants("celandine_01")                     # no dandelions: a designed garden, not a meadow
    ferns = S.ph_variants("fern_02")
    meadow = S.ph_variants("grass_medium_02")
    n = 0
    for xa, xb, ya, yb in beds:
        area = (xb - xa) * (yb - ya)
        for _ in range(int(area * 2.2)):
            me = shrubs[rnd.integers(len(shrubs))]
            S.place(me, f"shrub_{n:04d}", _gp(rnd.uniform(xa, xb), rnd.uniform(ya, yb)), c, rnd.uniform(0, 6.28),
                    rnd.uniform(0.8, 1.35), tilt=0.05); n += 1
        for _ in range(int(area * 1.5)):
            me = flowers[rnd.integers(len(flowers))]
            S.place(me, f"flower_{n:04d}", _gp(rnd.uniform(xa, xb), rnd.uniform(ya, yb)), c, rnd.uniform(0, 6.28),
                    rnd.uniform(0.7, 1.2), tilt=0.08); n += 1
        for _ in range(int(area * 0.8)):
            me = ferns[rnd.integers(len(ferns))]
            S.place(me, f"fern_{n:04d}", _gp(rnd.uniform(xa, xb), rnd.uniform(ya, yb)), c, rnd.uniform(0, 6.28),
                    rnd.uniform(0.6, 1.0), tilt=0.06); n += 1
    # a few meadow tufts where the lawn meets the border (unmown edge)
    for _ in range(60):
        y = rnd.choice([-1, 1]) * rnd.uniform(7.9, 8.3); x = rnd.uniform(3, 15)
        S.place(meadow[rnd.integers(len(meadow))], f"tuft_{n:04d}", (x, y, ground_z(x, y)), c, rnd.uniform(0, 6.28), rnd.uniform(0.25, 0.45)); n += 1
    # conifer hedge on the back boundary (typical Polish plot) + specimen trees
    firs = S.ph_variants("fir_tree_01")
    for i in ([] if SEASIDE else range(26)):
        y = -12.5 + i * 1.0 + rnd.normal(0, 0.12)
        S.place(firs[rnd.integers(len(firs))], f"hedge_{i:02d}", (19.5 + rnd.normal(0, 0.15), y, zg), c, rnd.uniform(0, 6.28),
                rnd.uniform(0.17, 0.21), tilt=0.02)
    small = S.ph_variants("tree_small_02")
    for k, (x, y, s) in enumerate([(7.2, -6.3, 1.0), (13.5, 7.0, 1.15), (16.0, -3.0, 0.9)]):
        for me in small:
            S.place(me, f"tree_{k}_{me.name}", (x, y, ground_z(x, y) - 0.03), c, rnd.uniform(0, 6.28) if False else 0.6 * k, s)
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
            S.box(f"fpost_{sy}_{i}", (0.06, 0.06, 1.6), (x0, y, ground_z(x0, y) + 0.75), c, steel, bevel=0.003)
            for k in range(12):
                S.box(f"fslat_{sy}_{i}_{k}", (2.44, 0.02, 0.09), (x0 + 1.25, y, ground_z(x0 + 1.25, y) + 0.15 + k * 0.115), c, steel, bevel=0.002)
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
    if not SEASIDE:
        gable_house("nbE", 32.0, -6.0, 10.0, 9.0, 5.8, 1.5708)
        gable_house("nbE2", 33.0, 12.0, 11.0, 9.0, 5.5, 1.5708)
    small = S.ph_variants("tree_small_02"); firs = S.ph_variants("fir_tree_01")
    ring = [(x, y) for x in np.linspace(-14, 30, 12) for y in (-13.5, 13.5)] + [(26.0, y) for y in np.linspace(-12, 12, 7)]
    if SEASIDE:
        ring = [(x, y) for x in np.linspace(-14, 17, 9) for y in (-13.5, 13.5)]
    for k, (x, y) in enumerate(ring):
        x += rnd.normal(0, 1.2); y += rnd.normal(0, 0.8)
        if rnd.random() < 0.55:
            for me in small:
                S.place(me, f"ringtree_{k}_{me.name}", (x, y, ground_z(x, y) - 0.03), c, 0.9 * k, rnd.uniform(1.1, 1.6))
        else:
            S.place(firs[rnd.integers(len(firs))], f"ringfir_{k}", (x, y, ground_z(x, y) - 0.03), c, rnd.uniform(0, 6.28), rnd.uniform(0.35, 0.55))
    return c



# ------------------------------------------------------------------ Baltic coast: dune, beach, sea, wooden pier
SEA_Z = -1.55          # mean sea level relative to the terrace (house on a low dune ridge)
PIER_Y = 4.6           # pier centre line (runs out to sea along +X, just right of the table axis)


def build_coast():
    c = fresh("COAST")
    rnd = S.RNG; zg = ground_z(19.5)
    sand = S.ph_material("gravelly_sand", "beach_sand")
    if "tinted" not in sand:
        S.calm_albedo(sand, (0.62, 0.55, 0.43), keep=0.45); sand["tinted"] = 1
    # dune + beach profile along X, gently varying along Y; continues under water so the shoreline is a real intersection
    xs = np.concatenate([np.linspace(19.0, 40.0, 180), np.linspace(40.5, 70.0, 30)])
    ys = np.linspace(-90, 90, 220)
    def zprof(x, y):
        if x < 20.2:  t = (x - 19.0) / 1.2; z = zg + 0.18 * math.sin(math.pi * t)            # dune crest
        elif x < 26.5: z = zg - (x - 20.2) / 6.3 * (SEA_Z - zg + 0.35) * -1 * -1             # dune face
        elif x < 31.0: z = SEA_Z + 0.35 - (x - 26.5) / 4.5 * 0.45                             # dry -> wet beach
        else:          z = SEA_Z - 0.1 - (x - 31.0) * 0.06                                    # shelf under water
        if 20.2 <= x < 26.5:
            z = zg + (SEA_Z + 0.35 - zg) * ((x - 20.2) / 6.3) ** 0.8
        return z + 0.05 * math.sin(y * 0.21 + x * 0.4) + 0.02 * math.sin(y * 0.9)
    verts = [(x, y, zprof(x, y)) for x in xs for y in ys]
    ny = len(ys); faces = [(i * ny + j, i * ny + j + 1, (i + 1) * ny + j + 1, (i + 1) * ny + j) for i in range(len(xs) - 1) for j in range(ny - 1)]
    beach = S.mesh_obj("beach", verts, faces, c, sand, smooth=True); S.uv_box(beach, 2.48)
    # marram grass on the dune
    tufts = S.ph_variants("grass_medium_01") + S.ph_variants("grass_medium_02")
    for k in range(260):
        x = rnd.uniform(19.2, 23.5); y = rnd.uniform(-40, 40)
        if abs(y - PIER_Y) < 2.2:
            continue
        S.place(tufts[rnd.integers(len(tufts))], f"dune_grass_{k}", (x, y, zprof(x, y) - 0.02), c, rnd.uniform(0, 6.28),
                rnd.uniform(0.35, 0.7), tilt=0.12)
    # sea: displaced wave mesh near shore (Ocean modifier, fixed seed), flat far sea with fine bump to the horizon
    water = bpy.data.materials.new("baltic_water"); water.use_nodes = True; wb = S.principled(water)
    wb.inputs["Base Color"].default_value = (0.012, 0.035, 0.04, 1); wb.inputs["Roughness"].default_value = 0.035
    wb.inputs["IOR"].default_value = 1.333; wb.inputs["Transmission Weight"].default_value = 0.0
    N, L = water.node_tree.nodes, water.node_tree.links
    tc = N.new("ShaderNodeTexCoord"); nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 3.0; nz.inputs["Detail"].default_value = 8
    L.new(tc.outputs["Object"], nz.inputs["Vector"])
    bm = N.new("ShaderNodeBump"); bm.inputs["Strength"].default_value = 0.08; L.new(nz.outputs["Fac"], bm.inputs["Height"]); L.new(bm.outputs["Normal"], wb.inputs["Normal"])
    bpy.ops.mesh.primitive_plane_add(size=1, location=(110.0, 0, SEA_Z)); near = bpy.context.object; near.name = "sea_near"; S.link(near, c)
    oc = near.modifiers.new("ocean", "OCEAN"); oc.geometry_mode = "GENERATE"; oc.size = 1.0; oc.spatial_size = 160
    oc.resolution = 9 if S.PREVIEW else 14; oc.wave_scale = 0.35; oc.wind_velocity = 7.5; oc.choppiness = 0.9; oc.random_seed = 11
    oc.wave_alignment = 0.4; oc.wave_direction = math.radians(180); oc.time = 1.0; oc.repeat_x = 1; oc.repeat_y = 2
    near.data.materials.append(water); near.data.shade_smooth()
    near.location = (29.0 + 80.0, 0, SEA_Z)
    far = S.box("sea_far", (4000, 4000, 0.01), (2000 + 189.0, 0, SEA_Z - 0.06), c, water)
    build_pier(c)
    return c


def build_pier(c):
    """Baltic wooden pier: 3.0 m deck on paired oak piles every 3 m, board deck, posts + handrail, 140 m long."""
    wood = S.ph_material("wood_planks", "pier_boards")
    piles_m = S.mat_variant(wood, "pier_piles", val=0.55)
    rail_m = S.mat_variant(wood, "pier_rail", val=0.8, uv_offset=(0.3, 0.7))
    x0, x1, wdt = 21.5, 165.0, 3.0
    deck_z = SEA_Z + 1.55
    d = S.box("pier_deck", (x1 - x0, wdt, 0.06), ((x0 + x1) / 2, PIER_Y, deck_z), c, wood, bevel=0.01); S.uv_box(d, 1.5)
    for side in (-1, 1):
        S.box(f"pier_stringer{side}", (x1 - x0, 0.2, 0.3), ((x0 + x1) / 2, PIER_Y + side * (wdt / 2 - 0.1), deck_z - 0.18), c, piles_m)
        S.box(f"pier_handrail{side}", (x1 - x0, 0.09, 0.09), ((x0 + x1) / 2, PIER_Y + side * (wdt / 2 - 0.05), deck_z + 1.05), c, rail_m, bevel=0.01)
        S.box(f"pier_midrail{side}", (x1 - x0, 0.05, 0.12), ((x0 + x1) / 2, PIER_Y + side * (wdt / 2 - 0.05), deck_z + 0.55), c, rail_m)
    k = 0
    for x in np.arange(x0 + 0.5, x1, 3.0):
        for side in (-1, 1):
            y = PIER_Y + side * (wdt / 2 - 0.12)
            S.box(f"pier_post_{k}", (0.1, 0.1, 1.1), (x, y, deck_z + 0.55), c, rail_m, bevel=0.008)
            bottom = SEA_Z - 2.5; top = deck_z - 0.2
            bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.14, depth=top - bottom, location=(x, y, (top + bottom) / 2))
            pl = bpy.context.object; pl.name = f"pier_pile_{k}"; S.link(pl, c); pl.data.materials.append(piles_m); S.uv_box(pl, 1.5)
            k += 1
    for o in c.objects:
        if o.name.startswith("pier_") and o.type == "MESH" and not o.data.uv_layers:
            S.uv_box(o, 1.5)
