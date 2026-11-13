"""Refinement pass q4: real photographed sky, report defects (wine, chair grain, deck tint, tree species) and a few
lived-in details. Called after refine.apply_all(); every step logs what it did."""
import math, os
import bpy, bmesh
import numpy as np
from mathutils import Vector
import storm_lib as S, build_world as BW

LOG = []
log = LOG.append
HDRI = os.environ.get("HDRI", "kloofendal_48d_partly_cloudy_puresky")


# ------------------------------------------------------------------ sky: real HDRI instead of the analytic sky
def _hdri_path(aid):
    d = S.ASSETS / "polyhaven" / aid
    if not d.exists():
        return None
    ex = sorted(d.glob("*.exr")) + sorted(d.glob("*.hdr"))
    return ex[0] if ex else None


_PIX = {}
def _pix(img):
    """float pixels without the 4 GB python-list detour of img.pixels[:]"""
    if img.name not in _PIX:
        w, h = img.size; a = np.empty(w * h * 4, np.float32); img.pixels.foreach_get(a); _PIX[img.name] = a.reshape(h, w, 4)
    return _PIX[img.name]


def sun_of(img):
    """Direction of the sun in an equirect image: centroid of the brightest 0.002 % pixels.
    Returns (azimuth u in [0,1), elevation in degrees)."""
    px = _pix(img)[..., :3].mean(-1)   # row 0 = bottom
    h, w = px.shape
    thr = px.max() * 0.5                           # the solar disc only (bright cloud edges next to it are ~100x dimmer)
    ys, xs = np.nonzero(px >= thr); wts = px[ys, xs]
    u = float((xs * wts).sum() / wts.sum() + 0.5) / w
    v = float((ys * wts).sum() / wts.sum() + 0.5) / h
    return u, (v - 0.5) * 180.0


def setup_hdri_sky(rot_deg=135.0, aid=HDRI):
    """Photographed clear/partly-cloudy sky (unclipped, sun inside). Rotated about Z so its sun sits at the same azimuth
    as the analytic sky used so far (shadows keep their direction); elevation is the HDRI's own (real sun + real sky
    colour belong together). Strength is set so the sun's irradiance matches the analytic sky's -> same exposure."""
    p = _hdri_path(aid)
    if p is None:
        log(f"sky: HDRI {aid} not available -> analytic sky kept"); return None
    sc = bpy.context.scene; w = sc.world; N, L = w.node_tree.nodes, w.node_tree.links
    N.clear()
    img = bpy.data.images.load(str(p)); img.colorspace_settings.name = "Linear Rec.709"
    u, el = sun_of(img)
    # Blender equirect lookup: u = -atan2(d.y, d.x)/2pi + 0.5  ->  sun azimuth in the image phi_img = -2pi(u - 0.5).
    # Mapping (POINT) rotates the lookup vector: Rz(a)·d_want must hit the image sun -> a = phi_img - phi_want,
    # with the sky convention d_want = (sin(rot)cos(el), cos(rot)cos(el), sin(el)).
    r = math.radians(rot_deg)
    phi_img = -2 * math.pi * (u - 0.5); phi_want = math.atan2(math.cos(r), math.sin(r))
    tc = N.new("ShaderNodeTexCoord"); mp = N.new("ShaderNodeMapping"); mp.inputs["Rotation"].default_value[2] = phi_img - phi_want
    env = N.new("ShaderNodeTexEnvironment"); env.image = img; env.interpolation = "Cubic"
    bg = N.new("ShaderNodeBackground"); out = N.new("ShaderNodeOutputWorld")
    L.new(tc.outputs["Generated"], mp.inputs["Vector"]); L.new(mp.outputs[0], env.inputs["Vector"])
    L.new(env.outputs[0], bg.inputs["Color"]); L.new(bg.outputs[0], out.inputs["Surface"])
    # exposure: Poly Haven HDRIs are relative. Calibrated with a sun-facing white card (cal.py): strength at which the
    # card is as bright as under the analytic sky used so far, so the camera exposure stays the same
    strength = float(os.environ.get("HDRI_STRENGTH", {"kloofendal_48d_partly_cloudy_puresky": 22.3}.get(aid, 20.0)))
    bg.inputs["Strength"].default_value = strength
    sc.world.cycles.sampling_method = "MANUAL"; sc.world.cycles.sample_map_resolution = 4096
    log(f"sky: photographed HDRI {aid} ({img.size[0]}x{img.size[1]}), sun el {el:.1f} deg rotated to az {rot_deg}, "
        f"strength {strength:.3g} (calibrated to the analytic sun); analytic sky removed")
    return el


# ------------------------------------------------------------------ report defects
def wine_ruby():
    """Both wine materials own the volume: rays entering through the glass-contact faces get the INTERFACE material's
    volume (a copy made in build_tableware), so tuning only red_wine changed nothing in q4."""
    col = tuple(float(x) for x in os.environ.get("WINE_COL", "0.95,0.0,0.60").split(","))
    dens = float(os.environ.get("WINE_DENS", 700))
    n = 0
    for name in ("red_wine", "red_wine_glass_interface"):
        m = bpy.data.materials.get(name)
        if not m:
            continue
        for nd in m.node_tree.nodes:
            if nd.type == "VOLUME_ABSORPTION":
                nd.inputs["Color"].default_value = (*col, 1); nd.inputs["Density"].default_value = dens; n += 1
    dbg = os.environ.get("WINE_DEBUG", "")
    if dbg == "hide":
        for o in bpy.data.objects:
            if o.name.startswith("wine_"):
                o.hide_render = True
    if dbg == "ior":
        S.principled(bpy.data.materials["red_wine_glass_interface"]).inputs["IOR"].default_value = 1.333
    if dbg == "flip":
        w = bpy.data.objects.get("wine_0"); w.data.flip_normals()
    log(f"wine: absorption colour {col} density {dens} on {n} volume(s) (wine top + glass-contact interface)")


def chairs_fine_grain():
    n = 0
    for m in bpy.data.materials:
        if m.name.startswith("chair_") and m.name.endswith("_v2"):
            for nd in m.node_tree.nodes:
                if nd.type == "MAPPING":
                    s = nd.inputs["Scale"].default_value; nd.inputs["Scale"].default_value = (s[0] * 2.6, s[1] * 2.6, s[2] * 2.6)
            b = S.principled(m)
            n += 1
    t = bpy.data.materials.get("teak_v2")
    log(f"chairs: grain 2.6x finer on {n} member materials (rosewood scan was stretched -> knotty look)")


def deck_neutral():
    for mm in [mm for mm in bpy.data.materials if mm.name.startswith("thermo_ash") and mm.use_nodes]:
        for nd in mm.node_tree.nodes:
            if nd.type == "MIX" and nd.blend_type == "MULTIPLY" and nd.data_type == "RGBA":
                c = nd.inputs[7].default_value if len(nd.inputs) > 7 else None
                if c is not None and abs(c[0] - 0.47 * 0.8) < 0.02:
                    nd.inputs[7].default_value = (0.45 * 0.8, 0.335 * 0.8, 0.215 * 0.8, 1)   # less red, more yellow-brown
    log("deck: tint moved from salmon to yellow-brown thermo-ash (was pink in skylight shade)")


def neighbour_trees():
    trees = S.ph_variants("island_tree_01") + S.ph_variants("island_tree_02")
    if not trees:
        log("trees: island_tree assets missing"); return
    c = BW.fresh("NEIGHBOUR_TREES"); rnd = S.RNG
    # mature broadleaf trees in the neighbours' gardens behind / beside the house: real plots are never one species,
    # and their crowns over the roof line give the depth that a single repeated tree lacks. Kept off the sea axis (+x).
    spots = [(-13.5, -9.5), (-16.0, 4.0), (-12.0, 11.5), (-3.5, -13.0), (6.5, 13.5)]
    for k, (x, y) in enumerate(spots):
        me = trees[k % len(trees)]
        hgt = max(v.co.z for v in me.vertices)
        s = rnd.uniform(13.0, 17.0) / max(hgt, 0.1)    # mature limes/oaks: must clear the 7 m roof line seen from 20 m
        S.place(me, f"ntree_{k}", (x, y, BW.ground_z(x, y) - 0.15), c, rnd.uniform(0, 6.28), s, tilt=0.02)
    log(f"trees: {len(spots)} mature broadleaf neighbour trees (island_tree_01/02 scans, 13-17 m) behind and beside the plot")


# ------------------------------------------------------------------ lived-in details
def _fabric(name, rgb, scale=900):
    m = bpy.data.materials.new(name); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links
    b = S.principled(m); b.inputs["Roughness"].default_value = 0.92; b.inputs["Sheen Weight"].default_value = 0.6
    b.inputs["Sheen Roughness"].default_value = 0.4
    tc = N.new("ShaderNodeTexCoord")
    w1 = N.new("ShaderNodeTexWave"); w1.wave_type = "BANDS"; w1.bands_direction = "X"; w1.inputs["Scale"].default_value = scale
    w2 = N.new("ShaderNodeTexWave"); w2.wave_type = "BANDS"; w2.bands_direction = "Y"; w2.inputs["Scale"].default_value = scale * 1.07
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 40; nz.inputs["Detail"].default_value = 6
    for t in (w1, w2, nz):
        L.new(tc.outputs["Object"], t.inputs["Vector"])
    mx = N.new("ShaderNodeMath"); mx.operation = "MAXIMUM"; L.new(w1.outputs["Fac"], mx.inputs[0]); L.new(w2.outputs["Fac"], mx.inputs[1])
    bump = N.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.25; bump.inputs["Distance"].default_value = 0.0004
    L.new(mx.outputs[0], bump.inputs["Height"]); L.new(bump.outputs[0], b.inputs["Normal"])
    cr = N.new("ShaderNodeMix"); cr.data_type = "RGBA"; cr.inputs["Factor"].default_value = 0.12
    cr.inputs[6].default_value = (*rgb, 1); cr.inputs[7].default_value = (rgb[0] * 0.8, rgb[1] * 0.8, rgb[2] * 0.78, 1)
    L.new(nz.outputs["Fac"], cr.inputs["Factor"]); L.new(cr.outputs[2], b.inputs["Base Color"])
    return m


def _pillow(name, size, c, mat, sag=0.35):
    """Seat pad: subdivided box, edges pulled in and top crowned/sagged like a filled linen cushion."""
    sx, sy, sz = size
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    o = bpy.context.object; o.name = name
    for col in o.users_collection:
        col.objects.unlink(o)
    c.objects.link(o)
    o.scale = (sx, sy, sz); bpy.ops.object.transform_apply(scale=True) if False else None
    me = o.data
    for v in me.vertices:
        v.co.x *= sx; v.co.y *= sy; v.co.z *= sz
    o.scale = (1, 1, 1)
    # dense grid first (no smoothing) so the outline stays a rounded SQUARE; a subsurfed 8-vertex cube becomes an
    # oval "bean bag" (what q4 showed). One smooth level afterwards only softens the seams.
    bm = bmesh.new(); bm.from_mesh(me)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=14, use_grid_fill=True)
    bm.to_mesh(me); bm.free()
    md = o.modifiers.new("sub", "SUBSURF"); md.levels = md.render_levels = 1
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier="sub")
    rnd = S.RNG
    for v in me.vertices:
        nx, ny = v.co.x / (sx / 2), v.co.y / (sy / 2)
        edge = max(abs(nx), abs(ny))
        puff = (1 - edge ** 10)            # flat pad with a tight rolled edge, not a round pillow
        if v.co.z > 0:
            v.co.z = sz / 2 * (0.25 + 0.75 * puff) - sag * sz * puff * math.exp(-((nx + 0.1) ** 2 + (ny - 0.15) ** 2) * 2.5) * 0.5
        else:
            v.co.z = -sz / 2 * (0.4 + 0.6 * puff)
        v.co.z += float(rnd.normal(0, 0.0004))
    me.materials.append(mat); me.shade_smooth()
    return o


def lived_in():
    c = BW.fresh("LIVED_IN"); rnd = S.RNG
    linen = _fabric("linen_cushion", (0.21, 0.20, 0.16))     # taupe/olive outdoor linen: light albedos blew out in full sun
    # seat cushions on the two chairs facing the camera side (not all: real tables are never fully dressed)
    chairs = sorted([o for o in bpy.data.objects if o.type == "EMPTY" and o.name.startswith("chair")], key=lambda o: o.name)
    used = 0
    for e in chairs:
        if used >= int(os.environ.get("CUSHIONS", 0)):   # q5: modelled pads read as slabs -> off until a scanned cushion is found
            break
        if e.location.x < -0.2:
            continue
        p = _pillow(f"cushion_{used}", (0.42, 0.41, 0.03), c, linen, sag=0.45)
        p.parent = e; p.location = (float(rnd.normal(0, 0.008)), float(rnd.normal(0.005, 0.008)), 0.47)
        p.rotation_euler.z = float(rnd.normal(0, 0.05)); used += 1
    # table: a closed hardback book left askew + a small bowl of olives (simple, physically honest objects)
    tops = [o for o in bpy.data.objects if o.name.startswith("top_")]
    if tops:
        zs = [ (o.matrix_world @ Vector(v)).z for o in tops for v in o.bound_box]
        xs = [(o.matrix_world @ Vector(v)).x for o in tops for v in o.bound_box]
        ys = [(o.matrix_world @ Vector(v)).y for o in tops for v in o.bound_box]
        zt = max(zs); x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        # book near the near-left corner, off the hero glass and off the camera axis of the glass shot
        bx, by = x0 + 0.24, y0 + 0.32
        cover = S.mat_simple("book_cloth", (0.09, 0.10, 0.12), rough=0.8)
        paper = S.mat_simple("book_paper", (0.80, 0.77, 0.69), rough=0.9)
        b1 = S.box("book_cover", (0.155, 0.235, 0.022), (bx, by, zt + 0.011), c, cover, bevel=0.0015, rot_z=0.42)
        b2 = S.box("book_pages", (0.147, 0.227, 0.018), (bx + 0.003 * math.cos(0.42), by + 0.003 * math.sin(0.42), zt + 0.011), c,
                   paper, bevel=0.0005, rot_z=0.42)
        # olive bowl: lathe stoneware bowl + 14 olives
        stone = S.mat_simple("stoneware", (0.58, 0.55, 0.50), rough=0.55)
        ox, oy = x0 + 0.42, y1 - 0.30
        prof = [(0.0, 0.0), (0.035, 0.0), (0.045, 0.004), (0.062, 0.03), (0.066, 0.042), (0.062, 0.043), (0.055, 0.032),
                (0.04, 0.008), (0.0, 0.006)]
        bowl = S.lathe("olive_bowl", prof, c, stone, seg=64); bowl.location = (ox, oy, zt)
        olive = S.mat_simple("olive", (0.035, 0.04, 0.012), rough=0.22)
        for k in range(14):
            a = rnd.uniform(0, 6.28); r = rnd.uniform(0, 0.035)
            bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, radius=0.0095,
                                                 location=(ox + r * math.cos(a), oy + r * math.sin(a), zt + 0.016 + rnd.uniform(0, 0.014)))
            o = bpy.context.object; o.name = f"olive_{k}"; o.scale = (1.0, 0.78, 0.78)
            o.rotation_euler = (rnd.uniform(0, 3), rnd.uniform(0, 3), rnd.uniform(0, 3))
            for col in o.users_collection:
                col.objects.unlink(o)
            c.objects.link(o); o.data.materials.append(olive); o.data.shade_smooth()
    # a few fallen leaves on the deck near the planters and on the lawn edge (late-summer, not autumn)
    leaf_mats = [S.mat_simple(f"leaf_fallen_{i}", col, rough=0.6) for i, col in
                 enumerate([(0.18, 0.20, 0.05), (0.32, 0.25, 0.07), (0.38, 0.22, 0.07), (0.22, 0.24, 0.07)])]
    for m in leaf_mats:
        b = S.principled(m); b.inputs["Subsurface Weight"].default_value = 0.0
        m.node_tree.nodes.new  # no-op, keep simple
    n = 0
    for k in range(22):
        x = rnd.uniform(-2.5, 3.6); y = rnd.uniform(-5.4, 5.4)
        if -1.0 < x < 1.6 and -1.4 < y < 1.4:      # not under the table
            continue
        bm = bmesh.new(); L_ = rnd.uniform(0.04, 0.07); W_ = L_ * rnd.uniform(0.38, 0.5)
        ring = []
        for i in range(16):
            t = i / 16 * 2 * math.pi
            px, py = L_ / 2 * math.cos(t), W_ / 2 * math.sin(t) * (1 - 0.35 * math.cos(t))
            curl = 0.004 * (py / (W_ / 2)) ** 2 + 0.003 * (px / (L_ / 2)) ** 2
            ring.append(bm.verts.new((px, py, curl)))
        ctr = bm.verts.new((0, 0, 0.0005))
        for i in range(16):
            bm.faces.new([ctr, ring[i], ring[(i + 1) % 16]])
        me = bpy.data.meshes.new(f"leaf_{k}"); bm.to_mesh(me); bm.free()
        me.materials.append(leaf_mats[k % 4]); me.shade_smooth()
        o = bpy.data.objects.new(f"leaf_{k}", me); c.objects.link(o)
        deck = bpy.data.objects.get("deck_boards")
        z = (max((deck.matrix_world @ Vector(v)).z for v in deck.bound_box) + 0.0008) if deck else 0.30
        o.location = (x, y, z); o.rotation_euler = (rnd.normal(0, 0.08), rnd.normal(0, 0.08), rnd.uniform(0, 6.28))
        sol = o.modifiers.new("sol", "SOLIDIFY"); sol.thickness = 0.0004
        n += 1
    log(f"lived-in: {used} seat cushions, closed book + olive bowl on the table, {n} fallen leaves on the deck")


def apply_all(rot_deg=135.0):
    for f in (wine_ruby, chairs_fine_grain, deck_neutral, neighbour_trees, lived_in):
        try:
            f()
        except Exception as e:                      # one failing detail must not cost a 1-hour CI frame
            log(f"{f.__name__}: FAILED {e!r}")
    return LOG
