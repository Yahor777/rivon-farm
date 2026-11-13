"""Wear pass (q7): the real world is not clean. Each effect is a physical mechanism placed where it actually happens,
not one noise over everything:
  glass     float-glass pillow distortion in the glazing (reflections bend), dried rain spots + dust on the lower pane,
            fingerprints on the wine-glass stem/bowl, lip mark on the rim
  table     water rings under glasses/bottle, oil worn glossy where hands rest at the edges, fine cross-scratches,
            crumbs, olive stones, a cork; wine drip on the top
  deck      boards slightly cupped / proud (+-1.5 mm, tilt), grey UV-weathering towards the open lawn side, foot-traffic
            band door -> table, a dark wine stain by the table, drip marks under the planters
  metal     table legs: scuffed powder coat at the feet (shoes, chairs), dust on top of frames (RIVON material untouched)
  plaster   stronger run-off streaks under sills/coping, darker splash zone, hairline map of tonal patches
  chairs    silver-grey UV weathering on up-facing faces, darker hand-oiled armrests/back top
  bottle    paper label (invented, no brand), foil capsule
All placement uses the RNG seed so frames stay identical between renders."""
import math, os
import bpy, bmesh
from mathutils import Vector
import storm_lib as S, build_world as BW

LOG = []
log = LOG.append
R = S.RNG


def _nodes(m):
    return m.node_tree.nodes, m.node_tree.links, S.principled(m)


def _input_src(N, b, name):
    """socket currently feeding b.inputs[name] (or a constant node)"""
    inp = b.inputs[name]
    if inp.is_linked:
        return inp.links[0].from_socket
    if inp.type == "RGBA":
        n = N.new("ShaderNodeRGB"); n.outputs[0].default_value = inp.default_value
    else:
        n = N.new("ShaderNodeValue"); n.outputs[0].default_value = inp.default_value
    return n.outputs[0]


def _mix_col(N, L, a, b_, fac, mode="MIX"):
    m = N.new("ShaderNodeMix"); m.data_type = "RGBA"; m.blend_type = mode
    L.new(fac, m.inputs["Factor"]); L.new(a, m.inputs[6])
    if isinstance(b_, tuple):
        m.inputs[7].default_value = (*b_, 1)
    else:
        L.new(b_, m.inputs[7])
    return m.outputs[2]


def _mix_f(N, L, a, b_, fac):
    m = N.new("ShaderNodeMix"); m.data_type = "FLOAT"
    L.new(fac, m.inputs["Factor"]); L.new(a, m.inputs[2])
    if isinstance(b_, (int, float)):
        m.inputs[3].default_value = b_
    else:
        L.new(b_, m.inputs[3])
    return m.outputs[0]


def _maprange(N, L, src, f0, f1, t0=0.0, t1=1.0):
    r = N.new("ShaderNodeMapRange"); r.inputs["From Min"].default_value = f0; r.inputs["From Max"].default_value = f1
    r.inputs["To Min"].default_value = t0; r.inputs["To Max"].default_value = t1; L.new(src, r.inputs["Value"]); return r.outputs[0]


def _math(N, L, op, a, b_):
    n = N.new("ShaderNodeMath"); n.operation = op
    for i, x in enumerate((a, b_)):
        if isinstance(x, (int, float)):
            n.inputs[i].default_value = x
        else:
            L.new(x, n.inputs[i])
    return n.outputs[0]


def _world_pos(N):
    g = N.new("ShaderNodeNewGeometry"); return g


def _noise(N, L, vec, scale, detail=6, rough=0.6, distortion=0.0, dims="3D"):
    n = N.new("ShaderNodeTexNoise"); n.noise_dimensions = dims
    n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough; n.inputs["Distortion"].default_value = distortion
    L.new(vec, n.inputs["Vector"]); return n.outputs["Fac"]


def _add_bump(N, L, b, height, strength, dist):
    bp = N.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = strength; bp.inputs["Distance"].default_value = dist
    L.new(height, bp.inputs["Height"])
    if b.inputs["Normal"].is_linked:
        L.new(b.inputs["Normal"].links[0].from_socket, bp.inputs["Normal"])
    L.new(bp.outputs["Normal"], b.inputs["Normal"])


def _ring_field(N, L, pos_sock, centres, r_in, r_out):
    """max over circles: 1 on a thin ring (a glass base that stood in a puddle), 0 elsewhere. centres in world XY."""
    acc = None
    sep = N.new("ShaderNodeSeparateXYZ"); L.new(pos_sock, sep.inputs[0])
    for (cx, cy, rr) in centres:
        dx = _math(N, L, "SUBTRACT", sep.outputs[0], cx); dy = _math(N, L, "SUBTRACT", sep.outputs[1], cy)
        d = _math(N, L, "SQRT", _math(N, L, "ADD", _math(N, L, "MULTIPLY", dx, dx), _math(N, L, "MULTIPLY", dy, dy)), 0)
        k = rr / r_out
        band = _math(N, L, "SUBTRACT", _maprange(N, L, d, r_in * k, r_in * k + 0.0015), _maprange(N, L, d, r_out * k, r_out * k + 0.0025))
        acc = band if acc is None else _math(N, L, "MAXIMUM", acc, band)
    return acc


# ------------------------------------------------------------------ glass
def glazing():
    m = bpy.data.materials.get("window_glass")
    if not m:
        return
    N, L, b = _nodes(m); g = _world_pos(N)
    # IGU "pillow" effect: panes bow by a few mm with temperature -> mirror images bend near the frames. Low-frequency
    # height field in world space (scale ~0.4/m) with a very small bump distance.
    # (pillow distortion removed on request: reflections stay flat)
    # dried rain spots + dust film, heavier on the lower third (splash) -> roughness, very slight milky base
    v = N.new("ShaderNodeTexVoronoi"); v.inputs["Scale"].default_value = 260; L.new(g.outputs["Position"], v.inputs["Vector"])
    spots = _maprange(N, L, v.outputs["Distance"], 0.0, 0.05, 1.0, 0.0)
    sep = N.new("ShaderNodeSeparateXYZ"); L.new(g.outputs["Position"], sep.inputs[0])
    low = _maprange(N, L, sep.outputs[2], 1.2, 0.3, 0.15, 1.0)
    dust = _maprange(N, L, _noise(N, L, g.outputs["Position"], 3.0, 8), 0.45, 0.8, 0.0, 1.0)
    rough = _math(N, L, "ADD", _math(N, L, "MULTIPLY", _math(N, L, "MULTIPLY", spots, low), 0.10),
                  _math(N, L, "MULTIPLY", _math(N, L, "MULTIPLY", dust, low), 0.05))
    base = _input_src(N, b, "Roughness")
    L.new(_math(N, L, "ADD", base, rough), b.inputs["Roughness"])
    log("glazing: dried rain spots + dust film on the lower panes (flat reflections kept)")


def wine_glass_marks():
    m = bpy.data.materials.get("wine_glass")
    if not m:
        return
    N, L, b = _nodes(m)
    tc = N.new("ShaderNodeTexCoord"); obj = tc.outputs["Object"]
    sep = N.new("ShaderNodeSeparateXYZ"); L.new(obj, sep.inputs[0])
    # fingerprints: elongated voronoi ridges, only on the stem and the lower bowl where it is held (object z < 0.13)
    w = N.new("ShaderNodeTexWave"); w.wave_type = "RINGS"; w.inputs["Scale"].default_value = 900
    w.inputs["Distortion"].default_value = 6; L.new(obj, w.inputs["Vector"])
    blob = _maprange(N, L, _noise(N, L, obj, 55, 3), 0.55, 0.68, 0.0, 1.0)
    zone = _maprange(N, L, sep.outputs[2], 0.13, 0.10, 0.0, 1.0)
    fp = _math(N, L, "MULTIPLY", _math(N, L, "MULTIPLY", blob, zone), _maprange(N, L, w.outputs["Fac"], 0.3, 0.7, 0.3, 1.0))
    # lip mark: one patch on the rim on the side away from the camera (object +x hemisphere)
    lip = _math(N, L, "MULTIPLY", _maprange(N, L, sep.outputs[2], 0.205, 0.225, 0.0, 1.0),
                _maprange(N, L, sep.outputs[1], 0.012, 0.0, 0.0, 1.0))
    lip = _math(N, L, "MULTIPLY", lip, _maprange(N, L, _noise(N, L, obj, 120, 4), 0.4, 0.6, 0.0, 1.0))
    base = _input_src(N, b, "Roughness")
    r = _math(N, L, "ADD", base, _math(N, L, "ADD", _math(N, L, "MULTIPLY", fp, 0.18), _math(N, L, "MULTIPLY", lip, 0.22)))
    L.new(r, b.inputs["Roughness"])
    log("wine glass: fingerprints on stem/lower bowl (roughness +0.18 in ridged patches), lip mark on the far rim")


# ------------------------------------------------------------------ table
def table_top():
    tops = [o for o in bpy.data.objects if o.name.startswith("top_")]
    if not tops:
        return
    gl = [o for o in bpy.data.objects if o.name.startswith(("wine_glass_", "bottle_wine", "plate_25"))]
    rings = []
    for o in gl:
        p = o.matrix_world.translation
        if o.name.startswith("wine_glass"):
            rings.append((p.x + R.uniform(-0.02, 0.02), p.y + R.uniform(-0.02, 0.02), 0.038))   # old ring next to it
        if o.name.startswith("bottle"):
            rings.append((p.x + 0.03, p.y - 0.05, 0.034))
    zt = max((o.matrix_world @ Vector(v)).z for o in tops for v in o.bound_box)
    xs = [(o.matrix_world @ Vector(v)).x for o in tops for v in o.bound_box]; ys = [(o.matrix_world @ Vector(v)).y for o in tops for v in o.bound_box]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    for _ in range(3):
        rings.append((R.uniform(x0 + 0.15, x1 - 0.15), R.uniform(y0 + 0.2, y1 - 0.2), R.uniform(0.032, 0.042)))
    for o in tops:
        m = o.data.materials[0]
        if m.get("worn"):
            continue
        m["worn"] = 1
        N, L, b = _nodes(m); g = _world_pos(N); pos = g.outputs["Position"]
        ring = _ring_field(N, L, pos, rings, 0.030, 0.034)
        ring = _math(N, L, "MULTIPLY", ring, _maprange(N, L, _noise(N, L, pos, 40, 3), 0.3, 0.6, 0.35, 1.0))
        # oil worn glossy along the long edges (forearms, plates slid on and off)
        sep = N.new("ShaderNodeSeparateXYZ"); L.new(pos, sep.inputs[0])
        dx = _math(N, L, "MINIMUM", _math(N, L, "SUBTRACT", sep.outputs[0], x0), _math(N, L, "SUBTRACT", x1, sep.outputs[0]))
        edge = _maprange(N, L, dx, 0.22, 0.03, 0.0, 1.0)
        edge = _math(N, L, "MULTIPLY", edge, _maprange(N, L, _noise(N, L, pos, 6, 4), 0.35, 0.65, 0.2, 1.0))
        # fine scratches: two families of thin stretched noise lines
        mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (2.0, 260.0, 2.0); mp.inputs["Rotation"].default_value[2] = 0.35
        L.new(pos, mp.inputs["Vector"])
        mp2 = N.new("ShaderNodeMapping"); mp2.inputs["Scale"].default_value = (240.0, 2.5, 2.0); mp2.inputs["Rotation"].default_value[2] = -0.6
        L.new(pos, mp2.inputs["Vector"])
        sc1 = _maprange(N, L, _noise(N, L, mp.outputs[0], 1.0, 2, 0.5), 0.70, 0.74, 0.0, 1.0)
        sc2 = _maprange(N, L, _noise(N, L, mp2.outputs[0], 1.0, 2, 0.5), 0.71, 0.745, 0.0, 1.0)
        scr = _math(N, L, "MULTIPLY", _math(N, L, "MAXIMUM", sc1, sc2), _maprange(N, L, _noise(N, L, pos, 3, 2), 0.4, 0.7, 0.0, 1.0))
        col = _input_src(N, b, "Base Color")
        col = _mix_col(N, L, col, (0.55, 0.47, 0.36), _math(N, L, "MULTIPLY", ring, 0.55), "MULTIPLY")     # tannin/water ring: darker
        col = _mix_col(N, L, col, (1.10, 1.06, 1.0), _math(N, L, "MULTIPLY", scr, 0.5), "MULTIPLY")      # scratches: lighter fibre
        col = _mix_col(N, L, col, (0.90, 0.86, 0.80), _math(N, L, "MULTIPLY", edge, 0.35), "MULTIPLY")    # handled edge: darker oil
        L.new(col, b.inputs["Base Color"])
        rough = _input_src(N, b, "Roughness")
        rough = _mix_f(N, L, rough, 0.28, _math(N, L, "MULTIPLY", edge, 0.6))
        rough = _mix_f(N, L, rough, 0.22, _math(N, L, "MULTIPLY", ring, 0.7))
        rough = _mix_f(N, L, rough, 0.75, _math(N, L, "MULTIPLY", scr, 0.6))
        L.new(rough, b.inputs["Roughness"])
        _add_bump(N, L, b, _math(N, L, "MULTIPLY", scr, -1.0), 0.25, 0.0004)
    log(f"table: {len(rings)} water/tannin rings, oil-worn glossy long edges, two families of fine scratches (colour, gloss, micro-bump)")
    # crumbs, olive stones, cork, wine drop on the top
    c = BW.fresh("TABLE_LIFE")
    crumb = S.mat_simple("bread_crumb", (0.62, 0.46, 0.26), rough=0.85)
    plate = bpy.data.objects.get("plate_25")
    px, py = (plate.matrix_world.translation.x, plate.matrix_world.translation.y) if plate else (0.18, -0.3)
    n = 0
    for k in range(26):
        a = R.uniform(0, 6.28); r = abs(float(R.normal(0.17, 0.05)))
        x, y = px + r * math.cos(a), py + r * math.sin(a)
        if not (x0 + 0.01 < x < x1 - 0.01 and y0 + 0.01 < y < y1 - 0.01):
            continue
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1)
        o = bpy.context.object; o.name = f"crumb_{k}"
        for col_ in o.users_collection:
            col_.objects.unlink(o)
        c.objects.link(o)
        s = R.uniform(0.0008, 0.0026)
        for v in o.data.vertices:
            v.co *= s * R.uniform(0.6, 1.3)
        o.location = (x, y, zt + s * 0.5); o.rotation_euler = (R.uniform(0, 3), R.uniform(0, 3), R.uniform(0, 3))
        o.data.materials.append(crumb); n += 1
    stone = S.mat_simple("olive_stone", (0.42, 0.33, 0.24), rough=0.7)
    for k in range(3):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=0.0075,
                                             location=(px + R.uniform(-0.06, 0.06), py + R.uniform(-0.06, 0.06), zt + 0.014))
        o = bpy.context.object; o.name = f"olive_stone_{k}"; o.scale = (1.0, 0.55, 0.5); o.rotation_euler.z = R.uniform(0, 3)
        for col_ in o.users_collection:
            col_.objects.unlink(o)
        c.objects.link(o); o.data.materials.append(stone); o.data.shade_smooth()
    bot = bpy.data.objects.get("bottle_wine") or bpy.data.objects.get("wine_bottle")
    if bot:
        bx, by = bot.matrix_world.translation.x, bot.matrix_world.translation.y
        cork = S.mat_simple("cork", (0.55, 0.40, 0.25), rough=0.9)
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.0115, depth=0.044, location=(bx + 0.13, by - 0.09, zt + 0.0115))
        o = bpy.context.object; o.name = "cork"; o.rotation_euler = (math.pi / 2, 0, 0.7)
        for col_ in o.users_collection:
            col_.objects.unlink(o)
        c.objects.link(o); o.data.materials.append(cork)
        bv = o.modifiers.new("bv", "BEVEL"); bv.width = 0.0015; bv.segments = 2
    log(f"table life: {n} bread crumbs around the plate, 3 olive stones, the cork next to the bottle")


# ------------------------------------------------------------------ deck
def deck():
    o = bpy.data.objects.get("deck_boards")
    if not o:
        return
    me = o.data; bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
    # boards are loose parts: move each a little (proud / sunk), tilt across the width (cupping) -> light catches edges
    seen = set(); k = 0
    for v in bm.verts:
        if v.index in seen:
            continue
        stack = [v]; part = []
        while stack:
            x = stack.pop()
            if x.index in seen:
                continue
            seen.add(x.index); part.append(x)
            for e in x.link_edges:
                stack.append(e.other_vert(x))
        if len(part) < 8:
            continue
        cx = sum(p.co.x for p in part) / len(part); cy = sum(p.co.y for p in part) / len(part)
        dz = float(R.normal(0, 0.0007)); tilt = float(R.normal(0, 0.006)); twist = float(R.normal(0, 0.0004))
        xs = [p.co.x for p in part]; ys = [p.co.y for p in part]
        across_x = (max(xs) - min(xs)) < (max(ys) - min(ys))
        for p in part:
            a = (p.co.x - cx) if across_x else (p.co.y - cy)
            l = (p.co.y - cy) if across_x else (p.co.x - cx)
            p.co.z += dz + tilt * a + twist * l
        k += 1
    bm.to_mesh(me); bm.free()
    m = o.data.materials[0]
    for mm in [x for x in bpy.data.materials if x.name.startswith("thermo_ash") and x.use_nodes and not x.get("worn")]:
        mm["worn"] = 1
        N, L, b = _nodes(mm); g = _world_pos(N); pos = g.outputs["Position"]
        sep = N.new("ShaderNodeSeparateXYZ"); L.new(pos, sep.inputs[0])
        # UV greying grows towards the open lawn edge (x -> 3.85), slows under the soffit (x < -1.5)
        grey = _math(N, L, "MULTIPLY", _maprange(N, L, sep.outputs[0], -1.5, 3.8, 0.0, 0.38),
                     _maprange(N, L, _noise(N, L, pos, 1.8, 5), 0.3, 0.7, 0.5, 1.0))
        # foot traffic band door (x -3, y ~0) -> table: lighter, rougher, fibres raised
        path = _maprange(N, L, _math(N, L, "ABSOLUTE", _math(N, L, "SUBTRACT", sep.outputs[1], 0.4), 0), 1.4, 0.2, 0.0, 1.0)
        path = _math(N, L, "MULTIPLY", path, _maprange(N, L, sep.outputs[0], -3.0, -1.2, 1.0, 0.0))
        path = _math(N, L, "MULTIPLY", path, _maprange(N, L, _noise(N, L, pos, 4, 5), 0.3, 0.7, 0.3, 1.0))
        # wine stain by the table + drip lines under the planters
        st = _ring_field(N, L, pos, [(0.95, -0.55, 0.06)], 0.0, 0.06)
        st = _math(N, L, "MULTIPLY", st, _maprange(N, L, _noise(N, L, pos, 25, 6, 0.7, 1.5), 0.35, 0.55, 0.0, 1.0))
        col = _input_src(N, b, "Base Color")
        col = _mix_col(N, L, col, (1.12, 1.08, 1.02), _math(N, L, "MULTIPLY", path, 0.35), "MULTIPLY")
        L.new(col, b.inputs["Base Color"])
        rough = _input_src(N, b, "Roughness")
        rough = _mix_f(N, L, rough, 0.72, _math(N, L, "MULTIPLY", path, 0.6))
        L.new(rough, b.inputs["Roughness"])
    log(f"deck: {k} boards individually proud/sunk (+-0.7 mm), cupped and twisted; faint foot-traffic band door->table "
        f"(no greying, no stains - on request)")


# ------------------------------------------------------------------ metal, plaster, chairs, bottle
def metal():
    legs = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith(("legA", "legB", "foot", "rail", "frame"))
            and o.data.materials and o.data.materials[0] and o.data.materials[0].name == "RIVON_powder_RAL9005"
            and o.matrix_world.translation.z < 1.0 and abs(o.matrix_world.translation.x) < 2 and abs(o.matrix_world.translation.y) < 2]
    if legs:
        m = legs[0].data.materials[0].copy(); m.name = "table_frame_powder_worn"
        for o in legs:
            o.data.materials[0] = m
        N, L, b = _nodes(m); g = _world_pos(N); pos = g.outputs["Position"]
        sep = N.new("ShaderNodeSeparateXYZ"); L.new(pos, sep.inputs[0])
        low = _maprange(N, L, sep.outputs[2], 0.30, 0.04, 0.0, 1.0)
        chips = _maprange(N, L, _noise(N, L, pos, 90, 6, 0.7), 0.62, 0.68, 0.0, 1.0)
        scuff = _math(N, L, "MULTIPLY", low, _maprange(N, L, _noise(N, L, pos, 25, 4), 0.45, 0.7, 0.0, 1.0))
        up = N.new("ShaderNodeSeparateXYZ"); L.new(g.outputs["Normal"], up.inputs[0])
        dust = _math(N, L, "MULTIPLY", _maprange(N, L, up.outputs[2], 0.6, 0.95, 0.0, 1.0), 0.6)
        col = _input_src(N, b, "Base Color")
        col = _mix_col(N, L, col, (0.30, 0.29, 0.28), _math(N, L, "MULTIPLY", _math(N, L, "MULTIPLY", chips, low), 0.25))
        col = _mix_col(N, L, col, (0.16, 0.155, 0.15), _math(N, L, "MULTIPLY", scuff, 0.15))
        col = _mix_col(N, L, col, (0.32, 0.30, 0.27), _math(N, L, "MULTIPLY", dust, 0.10))
        L.new(col, b.inputs["Base Color"])
        rough = _mix_f(N, L, _input_src(N, b, "Roughness"), 0.3, _math(N, L, "MULTIPLY", scuff, 0.25))
        rough = _mix_f(N, L, rough, 0.8, _math(N, L, "MULTIPLY", dust, 0.3))
        L.new(rough, b.inputs["Roughness"])
        log(f"metal (light): table frame ({len(legs)} parts) got its own worn powder coat - shoe/chair scuffs and chips at the feet, "
            f"dust on top faces; RIVON connector material untouched")
    for n in ("alu_RAL7021", "fence_RAL7016"):
        mm = bpy.data.materials.get(n)
        if mm and not mm.get("worn"):
            mm["worn"] = 1
            N, L, b = _nodes(mm); g = _world_pos(N)
            up = N.new("ShaderNodeSeparateXYZ"); L.new(g.outputs["Normal"], up.inputs[0])
            dust = _math(N, L, "MULTIPLY", _maprange(N, L, up.outputs[2], 0.5, 0.95, 0.0, 1.0),
                         _maprange(N, L, _noise(N, L, g.outputs["Position"], 8, 5), 0.3, 0.7, 0.3, 1.0))
            L.new(_mix_col(N, L, _input_src(N, b, "Base Color"), (0.36, 0.34, 0.31), _math(N, L, "MULTIPLY", dust, 0.12)), b.inputs["Base Color"])
            L.new(_mix_f(N, L, _input_src(N, b, "Roughness"), 0.8, _math(N, L, "MULTIPLY", dust, 0.3)), b.inputs["Roughness"])
    log("metal: dust and pollen on up-facing window frames, coping and fence rails")


def plaster():
    for n, kw in (("facade_plaster", dict(streak=0.16, tone=0.06)), ("facade_architectural_concrete", dict(streak=0.12, tone=0.08))):
        m = bpy.data.materials.get(n)
        if not m or m.get("worn"):
            continue
        m["worn"] = 1
        N, L, b = _nodes(m); g = _world_pos(N); pos = g.outputs["Position"]
        # run-off streaks: noise stretched vertically, strongest just below sills/coping (z bands) and fading downwards
        mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (18.0, 18.0, 0.7); L.new(pos, mp.inputs["Vector"])
        st = _maprange(N, L, _noise(N, L, mp.outputs[0], 1.0, 6, 0.6), 0.55, 0.75, 0.0, 1.0)
        sep = N.new("ShaderNodeSeparateXYZ"); L.new(pos, sep.inputs[0])
        z = sep.outputs[2]
        sill = _math(N, L, "MAXIMUM", _maprange(N, L, z, 6.6, 5.2, 0.0, 1.0), _maprange(N, L, z, 3.2, 2.2, 0.0, 0.7))
        sill = _math(N, L, "MULTIPLY", sill, _maprange(N, L, z, 2.0, 2.6, 0.0, 1.0))
        streak = _math(N, L, "MULTIPLY", st, sill)
        tone = _maprange(N, L, _noise(N, L, pos, 0.9, 4), 0.3, 0.7, -1.0, 1.0)
        col = _input_src(N, b, "Base Color")
        col = _mix_col(N, L, col, (0.70, 0.69, 0.66), _math(N, L, "MULTIPLY", streak, kw["streak"] / 0.3), "MULTIPLY")
        col = _mix_col(N, L, col, (1.0 - kw["tone"], 1.0 - kw["tone"], 1.0 - kw["tone"] * 1.2),
                       _maprange(N, L, tone, 0.0, 1.0, 0.0, 1.0), "MULTIPLY")
        L.new(col, b.inputs["Base Color"])
        L.new(_mix_f(N, L, _input_src(N, b, "Roughness"), 0.95, _math(N, L, "MULTIPLY", streak, 0.5)), b.inputs["Roughness"])
    log("plaster/concrete: grey run-off streaks below the coping and window sills, broad tonal patches (repairs, drying)")


def chairs():
    n = 0
    for m in bpy.data.materials:
        if not (m.name.startswith("chair_") and m.name.endswith("_v2")) or m.get("worn"):
            continue
        m["worn"] = 1; n += 1
        N, L, b = _nodes(m); g = _world_pos(N)
        up = N.new("ShaderNodeSeparateXYZ"); L.new(g.outputs["Normal"], up.inputs[0])
        uv = _math(N, L, "MULTIPLY", _maprange(N, L, up.outputs[2], 0.2, 0.95, 0.0, 1.0),
                   _maprange(N, L, _noise(N, L, g.outputs["Position"], 14, 6), 0.3, 0.7, 0.4, 1.0))
        col = _mix_col(N, L, _input_src(N, b, "Base Color"), (0.36, 0.35, 0.33), _math(N, L, "MULTIPLY", uv, 0.25))
        L.new(col, b.inputs["Base Color"])
        L.new(_mix_f(N, L, _input_src(N, b, "Roughness"), 0.82, _math(N, L, "MULTIPLY", uv, 0.6)), b.inputs["Roughness"])
    log(f"chairs: silver UV weathering on up-facing faces ({n} materials), raised fibre roughness")


def bottle_label():
    bot = bpy.data.objects.get("wine_bottle") or bpy.data.objects.get("bottle_wine")
    if not bot:
        return
    bot = bpy.data.objects.get("wine_bottle") or bot
    bb = [bot.matrix_world @ Vector(v) for v in bot.bound_box]
    x = sum(v.x for v in bb) / 8; y = sum(v.y for v in bb) / 8; z0 = min(v.z for v in bb); h = max(v.z for v in bb) - z0
    rad = (max(v.x for v in bb) - min(v.x for v in bb)) / 2 + 0.0004
    c = BW.fresh("BOTTLE_DRESS")
    paper = bpy.data.materials.new("label_paper"); paper.use_nodes = True
    N, L, b = _nodes(paper); b.inputs["Roughness"].default_value = 0.8
    tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Generated"], sep.inputs[0])
    band = _math(N, L, "MULTIPLY", _maprange(N, L, sep.outputs[2], 0.30, 0.32, 0.0, 1.0), _maprange(N, L, sep.outputs[2], 0.42, 0.40, 0.0, 1.0))
    fib = _noise(N, L, tc.outputs["Object"], 300, 4)
    col = _mix_col(N, L, _mix_col(N, L, N.new("ShaderNodeRGB").outputs[0], (0.82, 0.78, 0.68), _math(N, L, "ADD", 1, 0)),
                   (0.30, 0.08, 0.07), band)
    col = _mix_col(N, L, col, (0.92, 0.9, 0.86), _maprange(N, L, fib, 0.4, 0.7, 0.0, 0.25), "MULTIPLY")
    L.new(col, b.inputs["Base Color"])
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=rad, depth=h * 0.36, end_fill_type="NOTHING",
                                        location=(x, y, z0 + h * 0.08 + h * 0.18))
    lab = bpy.context.object; lab.name = "bottle_label"
    for col_ in lab.users_collection:
        col_.objects.unlink(lab)
    c.objects.link(lab); lab.data.materials.append(paper); lab.data.shade_smooth()
    # cut a 50 deg gap at the back (labels never wrap fully) by deleting faces
    bm = bmesh.new(); bm.from_mesh(lab.data)
    gone = [f for f in bm.faces if math.atan2(f.calc_center_median().y, f.calc_center_median().x) > 2.3]
    bmesh.ops.delete(bm, geom=gone, context="FACES"); bm.to_mesh(lab.data); bm.free()
    foil = S.mat_simple("capsule_foil", (0.18, 0.05, 0.06), rough=0.35, spec=0.7)
    mw = bot.matrix_world
    top = [mw @ v.co for v in bot.data.vertices if (mw @ v.co).z > z0 + h * 0.86]
    rneck = max(math.hypot(p.x - x, p.y - y) for p in top) + 0.0004 if top else 0.0152
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=rneck, depth=h * 0.15, location=(x, y, z0 + h * 0.925))
    cap = bpy.context.object; cap.name = "bottle_capsule"
    for col_ in cap.users_collection:
        col_.objects.unlink(cap)
    c.objects.link(cap); cap.data.materials.append(foil)
    S.principled(foil).inputs["Metallic"].default_value = 0.8
    log("bottle: paper front label with a printed band (no brand), unwrapped gap at the back, foil capsule")


def apply_all():
    for f in (glazing, wine_glass_marks, table_top, deck, metal, plaster, bottle_label):   # chairs(): UV burn off on request
        try:
            f()
        except Exception as e:
            import traceback; traceback.print_exc()
            log(f"{f.__name__}: FAILED {e!r}")
    return LOG
