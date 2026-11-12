"""RIVON THE STORM - design pass v2 (owner: "cheap / plastic, especially the terrace").
Premium Wielkopolska modern house on a Baltic plot:
 * upper floor cantilevers 0.7 m over the terrace, oak-slat soffit with recessed downlights
 * ground floor: architectural precast concrete + floor-to-ceiling slim sliding glazing, warm-lit interior behind it
 * terrace: thermo-ash deck, every board real geometry (6 mm gaps, staggered butt joints, stainless screws over joists),
   monolithic concrete step around it; nothing stands in the pergola footprint (x +-1.75, y +-3.0) except the dining set
 * concrete planters with multi-stem trees and ornamental grasses outside the pergola zone
The pergola footprint is reserved: PERGOLA_ZONE below is checked by validate_layout()."""
import sys, math
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import bpy, bmesh
import numpy as np
from mathutils import Vector
import storm_lib as S
import build_world as BW

PERGOLA_ZONE = (-1.80, 1.80, -3.05, 3.05)          # x0, x1, y0, y1 of the RIVON pergola footprint incl. Stopa plates
DECK = dict(x0=-3.0, x1=3.85, y0=-5.7, y1=5.7)       # deck boards area (top of boards z = 0)
STEP_W = 0.42                                        # monolithic concrete step around the deck
FAC_UP = BW.FAC_X + 0.7                              # cantilevered upper floor face
Z_SOFFIT = 3.22


def _tinted(aid, name, rgb, keep):
    m = S.ph_material(aid, name)
    if "tinted" not in m:
        S.calm_albedo(m, rgb, keep=keep); m["tinted"] = 1
    return m


def _board_rand_material(base, name, hue=0.012, val=0.13):
    """Per-board tone variation from a face attribute 'board' (0..1) -> one material, every board different."""
    m = base.copy(); m.name = name; N, L = m.node_tree.nodes, m.node_tree.links; b = S.principled(m)
    at = N.new("ShaderNodeAttribute"); at.attribute_type = "GEOMETRY"; at.attribute_name = "board"
    src = b.inputs["Base Color"].links[0].from_socket
    hsv = N.new("ShaderNodeHueSaturation")
    mh = N.new("ShaderNodeMapRange"); mh.inputs["To Min"].default_value = 0.5 - hue; mh.inputs["To Max"].default_value = 0.5 + hue
    mv = N.new("ShaderNodeMapRange"); mv.inputs["To Min"].default_value = 1 - val; mv.inputs["To Max"].default_value = 1 + val
    sep = N.new("ShaderNodeMath"); sep.operation = "FRACT"; mul = N.new("ShaderNodeMath"); mul.inputs[1].default_value = 7.31
    L.new(at.outputs["Fac"], mul.inputs[0]); L.new(mul.outputs[0], sep.inputs[0])
    L.new(at.outputs["Fac"], mh.inputs["Value"]); L.new(sep.outputs[0], mv.inputs["Value"])
    L.new(mh.outputs[0], hsv.inputs["Hue"]); L.new(mv.outputs[0], hsv.inputs["Value"])
    L.new(src, hsv.inputs["Color"]); L.new(hsv.outputs["Color"], b.inputs["Base Color"])
    return m


# ------------------------------------------------------------------ terrace
def build_deck():
    c = BW.fresh("DECK")
    rnd = S.RNG
    base = S.ph_material("oak_veneer_01", "thermo_ash_base")
    if "tinted" not in base:                       # thermo-treated ash: deep honey-brown, oiled (satin), open grain
        S.tint(base, (0.56, 0.43, 0.33), gain=0.95); base["tinted"] = 1
        pb = S.principled(base)
        if not pb.inputs["Roughness"].is_linked:
            pb.inputs["Roughness"].default_value = 0.55
    deck_m = _board_rand_material(base, "thermo_ash_deck")
    W, GAP, T = 0.14, 0.006, 0.026
    pitch = W + GAP
    verts, faces, uvs, board_attr = [], [], [], []
    nrow = int((DECK["x1"] - DECK["x0"]) / pitch)
    bid = 0
    for r in range(nrow):
        xc = DECK["x0"] + pitch / 2 + r * pitch
        y = DECK["y0"] + rnd.uniform(-1.6, 0.0)                     # staggered butt joints
        while y < DECK["y1"]:
            L = rnd.uniform(2.4, 4.2); ya = max(y, DECK["y0"]); yb = min(y + L, DECK["y1"])
            if yb - ya > 0.12:
                dz = float(rnd.normal(0, 0.0005)); twist = float(rnd.normal(0, 0.0007))
                uo, vo = float(rnd.random() * 4), float(rnd.random() * 4)
                b0 = len(verts); r_ = float(rnd.random())
                for sx in (-1, 1):
                    for sy in (ya, yb):
                        for z in (0.0, -T):
                            zz = z + dz + (sx * twist if z == 0.0 else 0)
                            verts.append((xc + sx * W / 2, sy, zz))
                # vertex order: (sx,y,z) -> index = ((sx>0)*2 + (y==yb))*2 + (z<0)
                def I(sx, yi, zi): return b0 + ((1 if sx > 0 else 0) * 2 + yi) * 2 + zi
                quads = [(I(-1, 0, 0), I(1, 0, 0), I(1, 1, 0), I(-1, 1, 0)),      # top
                         (I(-1, 0, 1), I(-1, 1, 1), I(1, 1, 1), I(1, 0, 1)),      # bottom
                         (I(-1, 0, 0), I(-1, 1, 0), I(-1, 1, 1), I(-1, 0, 1)),    # side -x
                         (I(1, 0, 0), I(1, 0, 1), I(1, 1, 1), I(1, 1, 0)),        # side +x
                         (I(-1, 0, 0), I(-1, 0, 1), I(1, 0, 1), I(1, 0, 0)),      # end ya
                         (I(-1, 1, 0), I(1, 1, 0), I(1, 1, 1), I(-1, 1, 1))]      # end yb
                for q in quads:
                    faces.append(q); board_attr.append(r_)
                bid += 1
            y += L + 0.004
    me = bpy.data.meshes.new("deck_boards"); me.from_pydata(verts, [], faces); me.update()
    at = me.attributes.new("board", "FLOAT", "FACE")
    for i, v in enumerate(board_attr):
        at.data[i].value = v
    ob = bpy.data.objects.new("deck_boards", me); c.objects.link(ob); me.materials.append(deck_m)
    # UVs: V along the board (grain), U across; each board its own patch of the scan
    uvl = me.uv_layers.new(name="UVMap")
    co = np.array([v.co[:] for v in me.vertices])
    for p in me.polygons:
        b = p.index // 6; rr = board_attr[p.index]
        off = (rr * 13.7 % 1.0) * 1.8, (rr * 7.9 % 1.0) * 1.8
        n = p.normal
        for li in p.loop_indices:
            x, y, z = co[me.loops[li].vertex_index]
            if abs(n.z) > 0.5:   u, v = x, y
            elif abs(n.x) > 0.5: u, v = z * 1.0, y
            else:                u, v = x * 0.25, z * 0.25        # end grain: compressed patch
            uvl.data[li].uv = (u / 1.83 + off[0], v / 1.83 + off[1])
    bv = ob.modifiers.new("arris", "BEVEL"); bv.width = 0.0025; bv.segments = 3; bv.limit_method = "ANGLE"
    ob.data.shade_smooth(); wn = ob.modifiers.new("wn", "WEIGHTED_NORMAL"); wn.keep_sharp = True
    # stainless A4 deck screws: 2 per board over every joist (joists at 0.45 m along X? boards run along Y -> joists along X)
    steel = S.mat_simple("deck_screw_A4", (0.55, 0.55, 0.53), rough=0.32, metal=1.0)
    sv, sf = [], []
    for jy in np.arange(DECK["y0"] + 0.2, DECK["y1"], 0.5):
        for r in range(nrow):
            xc = DECK["x0"] + pitch / 2 + r * pitch
            for sx in (-0.038, 0.038):
                cx, cy = xc + sx, jy + float(rnd.normal(0, 0.003))
                b0 = len(sv); nseg = 8
                sv.append((cx, cy, 0.0006))
                for k in range(nseg):
                    a = 2 * math.pi * k / nseg; sv.append((cx + 0.0034 * math.cos(a), cy + 0.0034 * math.sin(a), 0.0001))
                for k in range(nseg):
                    sf.append((b0, b0 + 1 + k, b0 + 1 + (k + 1) % nseg))
    scr = S.mesh_obj("deck_screws", sv, sf, c, steel, smooth=True)
    # substructure shadow void + monolithic step (cast concrete, 42 cm tread) around garden side and both ends
    dark = S.mat_simple("void_dark", (0.02, 0.02, 0.02), rough=0.9)
    S.box("deck_void", (DECK["x1"] - DECK["x0"], DECK["y1"] - DECK["y0"], 0.12), ((DECK["x0"] + DECK["x1"]) / 2, 0, -0.088), c, dark)
    conc = _tinted("smooth_concrete_floor", "step_concrete", (0.38, 0.37, 0.355), 0.6)
    zt = -0.075                                                       # step tread half-way between deck and lawn
    zb = BW.ground_z(DECK["x1"]) - 0.05
    for nm, (xa, xb, ya, yb) in {
            "step_E": (DECK["x1"] + 0.004, DECK["x1"] + STEP_W, DECK["y0"] - STEP_W, DECK["y1"] + STEP_W),
            "step_S": (DECK["x0"], DECK["x1"] + 0.004, DECK["y0"] - STEP_W, DECK["y0"] - 0.004),
            "step_N": (DECK["x0"], DECK["x1"] + 0.004, DECK["y1"] + 0.004, DECK["y1"] + STEP_W)}.items():
        st = S.box(nm, (xb - xa, yb - ya, zt - zb), ((xa + xb) / 2, (ya + yb) / 2, (zt + zb) / 2), c, conc, bevel=0.006, seg=3)
        S.uv_box(st, 2.0)
    # deck fascia under the board ends (dark, recessed 12 mm) gives the floating-deck shadow line
    for nm, size, loc in [("fascia_S", (DECK["x1"] - DECK["x0"], 0.02, 0.07), ((DECK["x0"] + DECK["x1"]) / 2, DECK["y0"] + 0.012, -0.06)),
                          ("fascia_N", (DECK["x1"] - DECK["x0"], 0.02, 0.07), ((DECK["x0"] + DECK["x1"]) / 2, DECK["y1"] - 0.012, -0.06)),
                          ("fascia_E", (0.02, DECK["y1"] - DECK["y0"], 0.07), (DECK["x1"] - 0.012, 0, -0.06))]:
        S.box(nm, size, loc, c, dark)
    return c


def build_planters():
    """Precast concrete planters (1.2 x 1.2 x 0.6 m, 6 cm walls) with multi-stem trees + grasses, outside the pergola zone."""
    c = BW.fresh("PLANTERS")
    rnd = S.RNG
    conc = _tinted("precast_concrete_wall", "planter_concrete", (0.56, 0.545, 0.52), 0.55)
    soil = _tinted("forrest_ground_01", "planter_soil", (0.08, 0.065, 0.05), 0.6)
    tree = S.ph_variants("tree_small_02")
    grass = S.ph_variants("grass_medium_02")
    spots = [(2.95, -4.75, 1.25), (2.95, 4.75, 1.25), (-2.25, 4.85, 0.9)]
    for k, (x, y, s) in enumerate(spots):
        h = 0.62 if s > 1 else 0.48; w = s
        for nm, size, loc in [("a", (w, 0.06, h), (x, y - w / 2 + 0.03, h / 2)), ("b", (w, 0.06, h), (x, y + w / 2 - 0.03, h / 2)),
                              ("c", (0.06, w - 0.12, h), (x - w / 2 + 0.03, y, h / 2)), ("d", (0.06, w - 0.12, h), (x + w / 2 - 0.03, y, h / 2))]:
            o = S.box(f"planter{k}_{nm}", size, loc, c, conc, bevel=0.004); S.uv_box(o, 2.0)
        sl = S.box(f"planter{k}_soil", (w - 0.12, w - 0.12, 0.02), (x, y, h - 0.06), c, soil); S.uv_box(sl, 2.0)
        if s > 1:
            for me in tree:
                S.place(me, f"planter{k}_tree_{me.name}", (x, y, h - 0.06), c, 1.3 * k + 0.4, 0.46)
        for j in range(5 if s > 1 else 7):
            S.place(grass[rnd.integers(len(grass))], f"planter{k}_grass{j}",
                    (x + rnd.uniform(-w / 2.8, w / 2.8), y + rnd.uniform(-w / 2.8, w / 2.8), h - 0.06), c, rnd.uniform(0, 6.28),
                    rnd.uniform(0.32, 0.42) if s > 1 else rnd.uniform(0.4, 0.5), tilt=0.05)
    # ornamental grass band in front of the step (Miscanthus/Pennisetum feel: one species repeated, varied scale) + boulders
    rocks = S.ph_variants("boulder_01")
    for j in range(140):
        y = rnd.uniform(-7.5, 7.5); x = DECK["x1"] + STEP_W + rnd.uniform(0.25, 1.35)
        if abs(y) < 1.3 and x < DECK["x1"] + STEP_W + 0.9:
            continue                                                # opening on the axis: path from the terrace to the beach
        S.place(grass[rnd.integers(len(grass))], f"band_grass{j}", (x, y, BW.ground_z(x, y) - 0.01), c, rnd.uniform(0, 6.28),
                rnd.uniform(0.3, 0.46), tilt=0.06)
    mulch = _tinted("forrest_ground_01", "band_mulch", (0.07, 0.06, 0.045), 0.7)
    for side in (-1, 1):
        b = S.box(f"band_bed{side}", (1.3, 6.4, 0.03), (DECK["x1"] + STEP_W + 0.8, side * 4.4, BW.ground_z(DECK["x1"] + 1.2) + 0.01), c, mulch)
        S.uv_box(b, 2.0)
    for j, (x, y, s) in enumerate([(DECK["x1"] + 1.4, -2.2, 0.12), (DECK["x1"] + 1.0, 3.1, 0.09), (DECK["x1"] + 1.7, 5.6, 0.14)]):
        if rocks:
            S.place(rocks[0], f"band_rock{j}", (x, y, BW.ground_z(x, y) - 0.05), c, rnd.uniform(0, 6.28), s)
    # potted olive-like plants by the glazing (outside the pergola footprint)
    for j, (aid, x, y, s) in enumerate([("potted_plant_01", -2.55, -4.3, 1.3), ("potted_plant_04", -2.6, 4.0, 1.1)]):
        v = S.ph_variants(aid) if (S.ASSETS / "polyhaven" / aid).exists() else []
        for me in v[:1]:
            S.place(me, f"pot_{j}", (x, y, 0.0), c, 0.7 * j, s)
    return c


def build_lounge():
    """Lounge corner on the north end of the deck (outside the pergola): lounge chair, side table, lanterns."""
    c = BW.fresh("LOUNGE")
    items = [("mid_century_lounge_chair", (1.6, 4.55, 0.0), 2.6, 1.0), ("side_table_01", (2.25, 4.15, 0.0), 0.0, 1.0),
             ("wooden_lantern_01", (-1.95, 3.55, 0.0), 0.3, 1.0), ("wooden_lantern_01", (-2.2, 3.75, 0.0), 1.1, 0.75)]
    for k, (aid, loc, rot, s) in enumerate(items):
        if not (S.ASSETS / "polyhaven" / aid).exists():
            continue
        for me in S.ph_variants(aid, lod=0):
            S.place(me, f"lounge_{k}_{me.name}", loc, c, rot, s)
    return c


# ------------------------------------------------------------------ house v2
def build_house():
    c = BW.fresh("HOUSE")
    render = S.ph_material("white_plaster_02", "facade_plaster")
    if "tinted" not in render:
        S.calm_albedo(render, (0.79, 0.775, 0.74), keep=0.22); render["tinted"] = 1
    conc = _tinted("precast_concrete_wall", "facade_architectural_concrete", (0.50, 0.49, 0.47), 0.75)
    larch = S.ph_material("oak_veneer_01", "facade_larch")
    frame = S.mat_simple("alu_RAL7021", (0.018, 0.019, 0.021), rough=0.38, metal=0.9)
    glass = S.mat_glass("window_glass", (0.93, 0.96, 0.95, 1))
    S.principled(glass).inputs["Roughness"].default_value = 0.0
    oak_floor = S.ph_material("white_oak_veneer", "interior_oak_floor") if (S.ASSETS / "polyhaven" / "white_oak_veneer").exists() \
        else S.ph_material("oak_veneer_01", "interior_oak_floor")
    int_wall = S.mat_simple("interior_wall_warm", (0.80, 0.77, 0.72), rough=0.9)
    y0, y1 = -BW.H_W / 2, BW.H_W / 2
    z_top = Z_SOFFIT + 3.15 + 0.45
    # ---- ground floor: concrete wall with a 9.6 m floor-to-ceiling glazing band
    glaz = (-4.8, 4.8, 0.0, Z_SOFFIT - 0.02)
    BW.wall_with_openings("gf_wall", c, BW.FAC_X, y0, y1, -0.2, Z_SOFFIT, 0.35, [glaz], conc)
    for o in c.objects:
        if o.name == "gf_wall":
            S.uv_box(o, 2.4)
    # 4-panel lift-and-slide, 50 mm sight lines (slim premium system)
    xg = BW.FAC_X - 0.10
    fw = 0.05
    for nm, size, loc in [("gl_head", (0.09, glaz[1] - glaz[0], fw), (xg, 0, glaz[3] - fw / 2)),
                          ("gl_sill", (0.12, glaz[1] - glaz[0], 0.02), (xg, 0, 0.01))]:
        S.box(nm, size, loc, c, frame, bevel=0.003)
    for k, yy in enumerate(np.linspace(glaz[0], glaz[1], 5)):
        S.box(f"gl_mull{k}", (0.09, fw, glaz[3] - glaz[2]), (xg - (0.02 if k % 2 else 0), yy, (glaz[2] + glaz[3]) / 2), c, frame, bevel=0.003)
    for k in range(4):
        a = glaz[0] + k * 2.4 + 0.03; b = a + 2.34
        for dx in (-0.016, 0.016):
            S.box(f"gl_pane{k}{dx}", (0.006, b - a, glaz[3] - 0.08), (xg + dx - (0.02 if k % 2 else 0), (a + b) / 2, glaz[3] / 2), c, glass)
    # ---- upper floor: cantilevered render volume with larch section
    up_d = BW.H_DEPTH + 0.7
    ups = [(-5.6, -3.0), (-0.9, 2.3), (3.6, 5.6)]
    ops = [(a, b, Z_SOFFIT + 0.85, Z_SOFFIT + 2.65) for a, b in ups]
    BW.wall_with_openings("up_wall", c, FAC_UP, y0, y1, Z_SOFFIT, z_top, 0.4, ops, render)
    for o in c.objects:
        if o.name == "up_wall":
            S.uv_box(o, 1.0)
    for i, (a, b) in enumerate(ups):
        BW.window_unit(f"upw{i}", c, FAC_UP, a, b, Z_SOFFIT + 0.85, Z_SOFFIT + 2.65, frame, glass, mullions=((a + b) / 2,))
    # larch rainscreen between the left windows (vertical boards, 10 mm open joints)
    for i in range(12):
        yb = -2.85 + i * 0.16
        b = S.box(f"larch_{i:02d}", (0.024, 0.15, 3.2), (FAC_UP + 0.04, yb + 0.075, Z_SOFFIT + 1.65), c, None, bevel=0.002)
        b.data.materials.append(S.mat_variant(larch, f"larch_{i:02d}", hue_shift=float(S.RNG.normal(0, 0.008)),
                                              val=float(S.RNG.normal(0.92, 0.07)), uv_offset=(float(S.RNG.random()), float(S.RNG.random()))))
        S.uv_box(b, 1.83)
    S.box("larch_backing", (0.02, 1.95, 3.2), (FAC_UP + 0.012, -1.92, Z_SOFFIT + 1.65), c, S.mat_simple("membrane_black", (0.01, 0.01, 0.01), 0.8))
    # soffit under the cantilever: oak slats + recessed 2700 K downlights (on at dusk, off by day)
    soffit_base = S.mat_simple("soffit_dark", (0.02, 0.02, 0.02), 0.9)
    S.box("soffit_back", (0.72, BW.H_W, 0.02), (BW.FAC_X + 0.35, 0, Z_SOFFIT - 0.01), c, soffit_base)
    for i in range(int(BW.H_W / 0.09)):
        yy = y0 + 0.045 + i * 0.09
        sl = S.box(f"soffit_slat{i:03d}", (0.70, 0.06, 0.03), (BW.FAC_X + 0.35, yy, Z_SOFFIT - 0.035), c, None, bevel=0.0015)
        sl.data.materials.append(S.mat_variant(larch, f"soffit_slat{i:03d}", val=float(S.RNG.normal(0.95, 0.05)),
                                               uv_offset=(float(S.RNG.random()), float(S.RNG.random()))))
        S.uv_box(sl, 1.83)
    S.box("coping", (up_d + 0.06, BW.H_W + 0.06, 0.04), (FAC_UP - up_d / 2 + 0.03, 0, z_top + 0.02), c, frame, bevel=0.003)
    S.box("wall_S", (up_d - 0.06, 0.4, z_top + 0.2), (FAC_UP - 0.06 - (up_d - 0.06) / 2, y0 + 0.2, z_top / 2 - 0.1), c, render)
    S.box("wall_N", (up_d - 0.06, 0.4, z_top + 0.2), (FAC_UP - 0.06 - (up_d - 0.06) / 2, y1 - 0.2, z_top / 2 - 0.1), c, render)
    for o in c.objects:
        if o.name.startswith("wall_"):
            S.uv_box(o, 1.0)
    S.box("roof", (up_d - 0.6, BW.H_W - 0.9, 0.3), (FAC_UP - 0.5 - (up_d - 0.6) / 2, 0, z_top - 0.45), c, int_wall)
    S.box("slab_edge", (up_d - 0.5, BW.H_W - 0.9, 0.25), (FAC_UP - 0.45 - (up_d - 0.5) / 2, 0, Z_SOFFIT + 0.1), c, int_wall)
    build_interior(c, oak_floor, int_wall)
    return c


def build_interior(c, oak_floor, wall):
    """Living room behind the glazing: oak floor, sofa, coffee table, plants, pendants and warm downlights (lived-in, not empty)."""
    x_in = BW.FAC_X - 0.36
    f = S.box("int_floor", (7.0, BW.H_W - 1, 0.04), (x_in - 3.5, 0, -0.02), c, oak_floor); S.uv_box(f, 1.83)
    S.box("int_ceiling", (7.0, BW.H_W - 1, 0.04), (x_in - 3.5, 0, Z_SOFFIT - 0.12), c, wall)
    S.box("int_back", (0.1, BW.H_W - 1, Z_SOFFIT), (x_in - 6.2, 0, Z_SOFFIT / 2), c, wall)
    # feature wall: dark oak shelving block
    S.box("int_shelf", (0.4, 3.6, 2.2), (x_in - 6.0, 2.6, 1.1), c, S.mat_variant(oak_floor, "int_shelf_oak", val=0.45))
    def put(aid, loc, rot, s=1.0):
        if (S.ASSETS / "polyhaven" / aid).exists():
            for me in S.ph_variants(aid, lod=0):
                S.place(me, f"int_{aid}_{me.name}", loc, c, rot, s)
    put("sofa_02", (x_in - 3.4, -1.2, 0.0), math.pi / 2)
    put("modern_coffee_table_01", (x_in - 2.2, -1.2, 0.0), 0.0)
    put("modern_arm_chair_01", (x_in - 1.6, 1.4, 0.0), -2.4)
    put("potted_plant_02", (x_in - 0.6, -4.2, 0.0), 0.3, 1.4)
    put("ceramic_vase_01", (x_in - 2.2, -1.1, 0.42), 0.0, 1.0)
    # 2700 K light: pendants over the dining spot + recessed downlights (point lights with a small radius)
    warm = (1.0, 0.72, 0.45)
    for k, (x, y) in enumerate([(x_in - 2.5, -3.6), (x_in - 2.5, -1.2), (x_in - 2.5, 1.2), (x_in - 2.5, 3.6),
                                (x_in - 4.8, -2.4), (x_in - 4.8, 2.4)]):
        L = bpy.data.lights.new(f"downlight{k}", "SPOT"); L.energy = 60; L.color = warm; L.spot_size = math.radians(70)
        L.spot_blend = 0.6; L.shadow_soft_size = 0.03
        o = bpy.data.objects.new(f"downlight{k}", L); c.objects.link(o); o.location = (x, y, Z_SOFFIT - 0.16)
    for k, y in enumerate((-0.6, 0.6)):
        L = bpy.data.lights.new(f"pendant{k}", "POINT"); L.energy = 25; L.color = warm; L.shadow_soft_size = 0.12
        o = bpy.data.objects.new(f"pendant{k}", L); c.objects.link(o); o.location = (x_in - 3.6, y + 2.6, 1.75)
    if (S.ASSETS / "polyhaven" / "modern_ceiling_lamp_01").exists():
        for k, y in enumerate((-0.6, 0.6)):
            for me in S.ph_variants("modern_ceiling_lamp_01", lod=0):
                S.place(me, f"int_pendant{k}_{me.name}", (x_in - 3.6, y + 2.6, Z_SOFFIT - 0.12 - 0.95), c, 0.0, 1.0)


def validate_layout():
    """Nothing but the dining set may stand inside the pergola footprint (posts + Stopa plates need the space)."""
    x0, x1, y0, y1 = PERGOLA_ZONE
    bad = []
    for col in ("PLANTERS", "LOUNGE", "HOUSE"):
        cc = bpy.data.collections.get(col)
        if not cc:
            continue
        for o in cc.objects:
            if o.type not in ("MESH",):
                continue
            P = np.array([list(o.matrix_world @ Vector(b)) for b in o.bound_box])
            lo, hi = P.min(0), P.max(0)
            if lo[0] < x1 and hi[0] > x0 and lo[1] < y1 and hi[1] > y0 and lo[2] < 2.7 and hi[2] > 0.01:
                bad.append(o.name)
    return bad


def build_all_v2(with_pergola=False):
    BW.TER.update(x0=DECK["x0"], x1=DECK["x1"] + STEP_W, y0=DECK["y0"] - STEP_W, y1=DECK["y1"] + STEP_W)
    build_house(); build_deck()
    BW.build_lawn(BW.fresh("GROUND"))
    BW.build_table(); build_planters(); build_lounge()
    BW.build_garden(); BW.build_fence(); BW.build_surroundings(); BW.build_coast()
    if with_pergola:
        BW.build_pergola()
    return validate_layout()
