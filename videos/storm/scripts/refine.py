"""RIVON THE STORM - photorealism refinement pass (owner brief 'PHOTOREALISM REFINEMENT PASS', 2026-11-12).
Applied on top of the existing scene; cameras, architecture, proportions and the RIVON CAD stay untouched.
Each fix answers a finding in reports/diagnostics_q2.md."""
import sys, math
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import bpy
import numpy as np
from mathutils import Vector
import storm_lib as S
import build_world as BW
import design as D

LOG = []


def log(msg):
    LOG.append(msg); print("REFINE", msg)


# ------------------------------------------------------------------ 1. data maps in the wrong colour space
def fix_colorspaces():
    n = 0
    for im in bpy.data.images:
        nm = im.name.lower()
        is_data = any(k in nm for k in ("_rough", "_nor", "_disp", "_arm", "_spec", "_metal", "_ao", "_mask", "_alpha", "_opacity"))
        if is_data and im.colorspace_settings.name not in ("Non-Color", "Raw"):
            im.colorspace_settings.name = "Non-Color"; n += 1
    log(f"colour space: {n} data maps switched to Non-Color (e.g. white_plaster_02_rough was read as sRGB)")


# ------------------------------------------------------------------ 2. vegetation shading
def _leafify(m, transl=0.32, hue=0.035, val=0.16):
    """Leaves/blades: thin-sheet translucency (light through the blade, typical yellow-green glow against the sun)
    + per-plant colour variation from Object Info Random (no two shrubs share a tint)."""
    if m.get("leafified") or not m.use_nodes:
        return False
    pb = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    out = next((n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output), None)
    if pb is None or out is None or not out.inputs["Surface"].is_linked:
        return False
    N, L = m.node_tree.nodes, m.node_tree.links
    m["leafified"] = 1
    oi = N.new("ShaderNodeObjectInfo")
    if pb.inputs["Base Color"].is_linked:
        src = pb.inputs["Base Color"].links[0].from_socket
    else:
        rgb = N.new("ShaderNodeRGB"); rgb.outputs[0].default_value = pb.inputs["Base Color"].default_value; src = rgb.outputs[0]
    hsv = N.new("ShaderNodeHueSaturation")
    mh = N.new("ShaderNodeMapRange"); mh.inputs["To Min"].default_value = 0.5 - hue; mh.inputs["To Max"].default_value = 0.5 + hue
    mv = N.new("ShaderNodeMapRange"); mv.inputs["To Min"].default_value = 1 - val; mv.inputs["To Max"].default_value = 1 + val * 0.6
    fr = N.new("ShaderNodeMath"); fr.operation = "FRACT"; mul = N.new("ShaderNodeMath"); mul.inputs[1].default_value = 5.77
    L.new(oi.outputs["Random"], mh.inputs["Value"]); L.new(oi.outputs["Random"], mul.inputs[0]); L.new(mul.outputs[0], fr.inputs[0])
    L.new(fr.outputs[0], mv.inputs["Value"])
    L.new(mh.outputs[0], hsv.inputs["Hue"]); L.new(mv.outputs[0], hsv.inputs["Value"]); L.new(src, hsv.inputs["Color"])
    L.new(hsv.outputs["Color"], pb.inputs["Base Color"])
    # translucency: blade transmits a warmer, more saturated green than it reflects
    tr = N.new("ShaderNodeBsdfTranslucent")
    warm = N.new("ShaderNodeHueSaturation"); warm.inputs["Saturation"].default_value = 1.35; warm.inputs["Value"].default_value = 1.25
    warm.inputs["Hue"].default_value = 0.52
    L.new(hsv.outputs["Color"], warm.inputs["Color"]); L.new(warm.outputs["Color"], tr.inputs["Color"])
    if pb.inputs["Normal"].is_linked:
        L.new(pb.inputs["Normal"].links[0].from_socket, tr.inputs["Normal"])
    surf = out.inputs["Surface"].links[0].from_socket
    mix = N.new("ShaderNodeMixShader"); mix.inputs["Fac"].default_value = transl
    L.new(surf, mix.inputs[1]); L.new(tr.outputs[0], mix.inputs[2])
    L.new(mix.outputs[0], out.inputs["Surface"])
    return True


def vegetation_shading():
    keys = ("leaves", "leaf", "grass", "shrub", "celandine", "fern", "periwinkle", "sorrel", "twig", "needle", "fir_tree", "pine",
            "island_tree", "bermuda", "potted_plant_01_leaves", "potted_plant_02_leaves", "grass_blade", "dune")
    n = 0
    for m in bpy.data.materials:
        nm = m.name.lower()
        if any(k in nm for k in keys) and not any(k in nm for k in ("trunk", "bark", "pot", "soil", "branches", "dead")):
            n += _leafify(m)
    log(f"vegetation: translucency + per-plant colour variation added to {n} materials that lacked it (lawn blades, fern, sorrel, conifer twigs); Poly Haven foliage groups (tree_small_02, shrubs, meadow grass) already carry translucency + Object-Info variation")


# ------------------------------------------------------------------ 3. lawn: mown, mixed, not 'hair'
def build_lawn_v2():
    lawn = bpy.data.objects["lawn"]
    for m in list(lawn.modifiers):
        if m.type == "PARTICLE_SYSTEM":
            lawn.modifiers.remove(m)
    while len(lawn.data.materials) > 1:
        lawn.data.materials.pop()
    rnd = S.RNG
    # thin / bald patches: multiply density by a low-frequency noise (real lawns are never even)
    vg = lawn.vertex_groups["density"]
    for v in lawn.data.vertices:
        try:
            w = vg.weight(v.index)
        except RuntimeError:
            continue
        x, y = v.co.x + lawn.location.x, v.co.y
        patch = 0.72 + 0.28 * math.sin(x * 0.83 + 1.3 * math.sin(y * 0.41)) * math.cos(y * 0.57 + 0.6 * math.sin(x * 0.31))
        vg.add([v.index], max(0.0, min(1.0, w * patch)), "REPLACE")

    def blade_mat(name, tip, mid, root):
        m = bpy.data.materials.get(name)
        if m:
            return m
        m = bpy.data.materials.new(name); m.use_nodes = True; N, Ln = m.node_tree.nodes, m.node_tree.links; pb = S.principled(m)
        hi = N.new("ShaderNodeHairInfo"); ramp = N.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].color = (*root, 1); ramp.color_ramp.elements[1].color = (*tip, 1)
        e = ramp.color_ramp.elements.new(0.45); e.color = (*mid, 1)
        Ln.new(hi.outputs["Intercept"], ramp.inputs["Fac"])
        # per-blade variation: some blades older/yellower, some darker (Hair Info Random)
        hsv = N.new("ShaderNodeHueSaturation"); mh = N.new("ShaderNodeMapRange"); mh.inputs["To Min"].default_value = 0.47; mh.inputs["To Max"].default_value = 0.535
        mv = N.new("ShaderNodeMapRange"); mv.inputs["To Min"].default_value = 0.72; mv.inputs["To Max"].default_value = 1.18
        Ln.new(hi.outputs["Random"], mh.inputs["Value"]); Ln.new(hi.outputs["Random"], mv.inputs["Value"])
        Ln.new(mh.outputs[0], hsv.inputs["Hue"]); Ln.new(mv.outputs[0], hsv.inputs["Value"]); Ln.new(ramp.outputs["Color"], hsv.inputs["Color"])
        Ln.new(hsv.outputs["Color"], pb.inputs["Base Color"])
        pb.inputs["Roughness"].default_value = 0.38; pb.inputs["Specular IOR Level"].default_value = 0.45
        m["leafified"] = 0
        _leafify(m, transl=0.38, hue=0.0, val=0.0)
        return m

    specs = [  # name, parents, length, rand, radius, mat colours (tip, mid, root), tilt
        ("lawn_fine", 200000 if not S.PREVIEW else 60000, 0.042, 0.55, 0.0011, ((0.20, 0.32, 0.07), (0.10, 0.20, 0.035), (0.03, 0.055, 0.012)), 0.020),
        ("lawn_rye", 60000 if not S.PREVIEW else 18000, 0.070, 0.6, 0.0016, ((0.24, 0.33, 0.09), (0.09, 0.18, 0.03), (0.03, 0.05, 0.012)), 0.030),
        ("lawn_seed", 4000 if not S.PREVIEW else 1500, 0.11, 0.5, 0.0012, ((0.42, 0.40, 0.20), (0.18, 0.22, 0.07), (0.05, 0.07, 0.02)), 0.045),
    ]
    for k, (nm, cnt, ln, rr, rad, cols, tilt) in enumerate(specs):
        mat = blade_mat(f"grass_{nm}", *cols); lawn.data.materials.append(mat)
        ps = lawn.modifiers.new(nm, "PARTICLE_SYSTEM").particle_system; st = bpy.data.particles.new(nm); ps.settings = st
        st.type = "HAIR"; st.count = cnt; st.hair_length = ln; st.use_advanced_hair = True; st.hair_step = 5
        st.material = len(lawn.data.materials); st.emit_from = "FACE"; st.use_emit_random = True; st.use_even_distribution = False
        st.child_type = "INTERPOLATED"; st.child_percent = 4; st.rendered_child_count = 4 if not S.PREVIEW else 2
        st.child_parting_factor = 0.0; st.clump_factor = 0.0; st.child_length = 1.0; st.child_length_threshold = 0.25
        st.length_random = rr; st.child_radius = 0.06
        # every blade leans its own way and bends (no combed 'hair'): random initial velocity + roughness + endpoint droop
        st.normal_factor = ln * 0.9; st.factor_random = ln * 0.75; st.tangent_factor = 0.0; st.object_align_factor = (0, 0, 0)
        st.use_rotations = True; st.rotation_mode = "NOR"; st.rotation_factor_random = 1.0; st.phase_factor_random = 2.0
        st.roughness_1 = ln * 0.12; st.roughness_1_size = 0.6; st.roughness_endpoint = ln * 0.18; st.roughness_end_shape = 1.4
        st.roughness_2 = ln * 0.06; st.roughness_2_size = 1.5; st.roughness_2_threshold = 0.4
        st.kink = "WAVE"; st.kink_amplitude = ln * 0.08; st.kink_frequency = 0.6; st.kink_shape = 0.3
        st.root_radius = 1.0; st.tip_radius = 0.0; st.radius_scale = rad; st.shape = -0.25
        ps.vertex_group_density = "density"; ps.seed = 17 + 31 * k
    sc = bpy.context.scene
    sc.cycles_curves.shape = "RIBBONS"           # flat blades (round tubes read as hair)
    sc.cycles_curves.subdivisions = 2
    # clover / small broadleaf weeds in patches (shrub_sorrel_01 = Oxalis, clover-like), sparse daisy-like celandine
    c = BW.fresh("LAWN_WEEDS")
    clov = S.ph_variants("shrub_sorrel_01"); cel = S.ph_variants("celandine_01")
    for j in range(260 if not S.PREVIEW else 90):
        cx, cy = rnd.uniform(4.4, 17.0), rnd.uniform(-7.5, 7.5)
        if abs(cy) < 1.3 and cx < 6.5:
            continue
        for q in range(int(rnd.integers(2, 6))):
            x, y = cx + rnd.normal(0, 0.12), cy + rnd.normal(0, 0.12)
            S.place(clov[rnd.integers(len(clov))], f"clover_{j}_{q}", (x, y, BW.ground_z(x, y) - 0.005), c, rnd.uniform(0, 6.28),
                    rnd.uniform(0.25, 0.4), tilt=0.1)
    for j in range(25):
        x, y = rnd.uniform(6, 17), rnd.uniform(-7.5, 7.5)
        S.place(cel[rnd.integers(len(cel))], f"daisy_{j}", (x, y, BW.ground_z(x, y) - 0.01), c, rnd.uniform(0, 6.28), rnd.uniform(0.18, 0.28))
    log("lawn: 3 blade populations (fine fescue 2-6 cm, ryegrass 4-10 cm, seed heads), flat ribbons, random lean/bend/kink, "
        "bald/thin patches, clover + small weeds; was one 24 cm combed hair system")


# ------------------------------------------------------------------ 4. trees: denser crowns, Baltic pines behind the dune
def trees_v2():
    c = BW.fresh("PINES")
    rnd = S.RNG
    pines = S.ph_variants("pine_sapling_medium")          # (pine_tree_01 .blend is not in the release: textures only)
    if not pines:
        return
    # coastal Scots-pine belt on the dune (classic Polish Baltic coast), leaving the view axis to the pier open
    for k in range(22):
        y = rnd.choice([-1, 1]) * rnd.uniform(9.5, 38.0); x = rnd.uniform(19.0, 24.0)
        S.place(pines[rnd.integers(len(pines))], f"pine_{k}", (x, y, BW.ground_z(19.5, y) - 0.1 - (x - 19.5) * 0.15), c,
                rnd.uniform(0, 6.28), rnd.uniform(0.75, 1.05), tilt=0.03)
    log("trees: Scots-pine belt on the dune (Baltic coast character); garden trees keep tree_small_02 scans with translucent leaves")


# ------------------------------------------------------------------ 5. materials
def materials_v2():
    g = bpy.data.materials.get
    # deck: thermo-ash = chocolate brown with open grain; use the white-oak veneer scan (ring-porous like ash) instead of the
    # rotary-cut 'oak_veneer_01' whose flat repeating figure produced the stripe pattern on the boards
    deck = g("thermo_ash_deck")
    if deck and (S.ASSETS / "polyhaven" / "white_oak_veneer").exists():
        src = S.ph_material("white_oak_veneer", "white_oak_src")
        newb = src.copy(); newb.name = "thermo_ash_base_v2"
        S.tint(newb, (0.47, 0.33, 0.235), gain=0.8)
        nd = D._board_rand_material(newb, "thermo_ash_deck_v2", hue=0.01, val=0.16)
        S.add_grime(nd, ao=0.35, dust=0.08)
        _rough_variation(nd, 0.42, 0.62, scale=1.7)
        ob = bpy.data.objects.get("deck_boards")
        if ob:
            ob.data.materials[0] = nd
        log("deck: white-oak scan tinted to thermo-ash, per-board tone +-16 %, roughness field 0.42-0.62 (oiled, foot-worn)")
    # chairs: teak-like rosewood scan instead of the tinted oak (was orange and uniform)
    if (S.ASSETS / "polyhaven" / "rosewood_veneer1").exists():
        teak = S.ph_material("rosewood_veneer1", "teak_v2")
        if "tinted" not in teak:
            S.calm_albedo(teak, (0.36, 0.24, 0.15), keep=0.9); teak["tinted"] = 1     # weathered-oiled teak: brown, not red
            _rough_variation(teak, 0.45, 0.65, scale=3.1)
        for m in list(bpy.data.materials):
            if m.name.startswith("chair_") and ("_teak" in m.name or "_slat" in m.name):
                v = S.mat_variant(teak, m.name + "_v2", val=float(S.RNG.normal(1.0, 0.07)),
                                  uv_offset=(float(S.RNG.random()), float(S.RNG.random())))
                for o in bpy.data.objects:
                    if o.type == "MESH" and o.data.materials and o.data.materials[0] == m:
                        o.data.materials[0] = v
        log("chairs: oiled teak from the rosewood veneer scan, each member its own grain patch")
    # facade render: large-scale tonal drift + specular variation (hand-floated render is never one flat value)
    pl = g("facade_plaster")
    if pl and not pl.get("drift"):
        _tone_drift(pl, scale=0.35, amount=0.035); _rough_variation(pl, 0.78, 0.93, scale=0.9); pl["drift"] = 1
    for nm in ("facade_architectural_concrete", "step_concrete", "planter_concrete"):
        m = g(nm)
        if m and not m.get("drift"):
            _tone_drift(m, scale=0.6, amount=0.05); _rough_variation(m, 0.6, 0.85, scale=1.3); m["drift"] = 1
    log("facade/concrete: low-frequency tone drift and roughness variation (each material its own noise scale)")


def _tone_drift(m, scale, amount):
    N, L = m.node_tree.nodes, m.node_tree.links; b = S.principled(m)
    src = b.inputs["Base Color"].links[0].from_socket if b.inputs["Base Color"].is_linked else None
    if src is None:
        return
    geo = N.new("ShaderNodeNewGeometry"); nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = 3; L.new(geo.outputs["Position"], nz.inputs["Vector"])
    mr = N.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = 1 - amount; mr.inputs["To Max"].default_value = 1 + amount
    L.new(nz.outputs["Fac"], mr.inputs["Value"])
    hsv = N.new("ShaderNodeHueSaturation"); L.new(mr.outputs[0], hsv.inputs["Value"]); L.new(src, hsv.inputs["Color"])
    L.new(hsv.outputs["Color"], b.inputs["Base Color"])


def _rough_variation(m, lo, hi, scale):
    N, L = m.node_tree.nodes, m.node_tree.links; b = S.principled(m)
    geo = N.new("ShaderNodeNewGeometry"); nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = 5; L.new(geo.outputs["Position"], nz.inputs["Vector"])
    mr = N.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = lo; mr.inputs["To Max"].default_value = hi
    L.new(nz.outputs["Fac"], mr.inputs["Value"])
    if b.inputs["Roughness"].is_linked:   # keep the scan's micro roughness, re-centre it on the macro field
        src = b.inputs["Roughness"].links[0].from_socket
        mix = N.new("ShaderNodeMix"); mix.data_type = "FLOAT"; mix.inputs["Factor"].default_value = 0.55
        L.new(src, mix.inputs[2]); L.new(mr.outputs[0], mix.inputs[3]); L.new(mix.outputs[0], b.inputs["Roughness"])
    else:
        L.new(mr.outputs[0], b.inputs["Roughness"])


# ------------------------------------------------------------------ 6. interior: daylight only, real rooms upstairs, curtains
def interior_v2():
    n = 0
    for o in list(bpy.data.objects):
        if o.type == "LIGHT" and o.name.startswith(("downlight", "pendant")):
            bpy.data.objects.remove(o, do_unlink=True); n += 1
    c = bpy.data.collections["HOUSE"]
    wall = bpy.data.materials.get("interior_wall_warm") or S.mat_simple("interior_wall_warm", (0.80, 0.77, 0.72), rough=0.9)
    S.principled(wall).inputs["Base Color"].default_value = (0.83, 0.81, 0.77, 1)     # light walls: daylight bounces deep into the room
    oak = bpy.data.materials.get("interior_oak_floor")
    up_z0 = D.Z_SOFFIT + 0.25; up_h = 2.75
    x_in = D.FAC_UP - 0.4
    f = S.box("up_room_floor", (6.0, BW.H_W - 1, 0.04), (x_in - 3.0, 0, up_z0), c, oak); S.uv_box(f, 1.83)
    S.box("up_room_ceiling", (6.0, BW.H_W - 1, 0.04), (x_in - 3.0, 0, up_z0 + up_h), c, wall)
    S.box("up_room_back", (0.1, BW.H_W - 1, up_h), (x_in - 5.5, 0, up_z0 + up_h / 2), c, wall)
    for yy in (-2.95, 2.45):                                       # partition walls between rooms
        S.box(f"up_room_part{yy}", (5.5, 0.12, up_h), (x_in - 2.75, yy, up_z0 + up_h / 2), c, wall)
    # bedroom furniture silhouettes from the scans (armchair, plant) + a bed block with linen
    linen = S.ph_material("rough_linen", "bed_linen")
    S.box("up_bed", (2.0, 1.7, 0.45), (x_in - 3.4, 0.6, up_z0 + 0.25), c, linen, bevel=0.04, seg=4)
    S.box("up_headboard", (0.08, 1.8, 1.0), (x_in - 4.45, 0.6, up_z0 + 0.5), c, S.mat_variant(oak, "headboard_oak", val=0.6))
    for aid, loc, rot in (("modern_arm_chair_01", (x_in - 1.2, -4.4, up_z0), 2.2), ("potted_plant_02", (x_in - 0.5, 3.6, up_z0), 0.5)):
        if (S.ASSETS / "polyhaven" / aid).exists():
            for me in S.ph_variants(aid, lod=0):
                S.place(me, f"up_{aid}_{me.name}", loc, c, rot, 1.0)
    # sheer linen curtains (gathered folds = real geometry), half drawn in two upper windows and at the glazing ends
    sheer = bpy.data.materials.get("sheer_linen")
    if sheer is None:
        sheer = S.ph_material("rough_linen", "sheer_linen").copy(); sheer.name = "sheer_linen"
        b = S.principled(sheer); b.inputs["Transmission Weight"].default_value = 0.0
        tr = sheer.node_tree.nodes.new("ShaderNodeBsdfTranslucent"); tr.inputs["Color"].default_value = (0.9, 0.88, 0.84, 1)
        out = next(n for n in sheer.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
        mix = sheer.node_tree.nodes.new("ShaderNodeMixShader"); mix.inputs["Fac"].default_value = 0.55
        sheer.node_tree.links.new(out.inputs["Surface"].links[0].from_socket, mix.inputs[1]); sheer.node_tree.links.new(tr.outputs[0], mix.inputs[2])
        sheer.node_tree.links.new(mix.outputs[0], out.inputs["Surface"])
    def curtain(name, x, ya, yb, z0, z1, folds):
        nu, nv = 120, 24; verts, faces = [], []
        for j in range(nv + 1):
            z = z0 + (z1 - z0) * j / nv
            for i in range(nu + 1):
                t = i / nu; y = ya + (yb - ya) * t
                amp = 0.035 * (0.6 + 0.4 * (1 - j / nv))
                verts.append((x + amp * math.sin(t * folds * 2 * math.pi + 0.3 * math.sin(z * 3)), y, z))
        for j in range(nv):
            for i in range(nu):
                a = j * (nu + 1) + i; faces.append((a, a + 1, a + nu + 2, a + nu + 1))
        o = S.mesh_obj(name, verts, faces, c, sheer, smooth=True); S.uv_box(o, 0.8)
        so = o.modifiers.new("t", "SOLIDIFY"); so.thickness = 0.0015
    up = [(-5.6, -3.0), (-0.9, 2.3), (3.6, 5.6)]
    curtain("curtain_up0", D.FAC_UP - 0.48, up[0][0] + 0.05, up[0][0] + 0.9, D.Z_SOFFIT + 0.85, D.Z_SOFFIT + 2.62, 9)
    curtain("curtain_up2", D.FAC_UP - 0.48, up[2][1] - 0.85, up[2][1] - 0.05, D.Z_SOFFIT + 0.85, D.Z_SOFFIT + 2.62, 9)
    curtain("curtain_gf_s", BW.FAC_X - 0.45, -4.75, -3.95, 0.02, D.Z_SOFFIT - 0.15, 10)
    curtain("curtain_gf_n", BW.FAC_X - 0.45, 3.85, 4.75, 0.02, D.Z_SOFFIT - 0.15, 10)
    log(f"interior: removed {n} artificial daytime lights (only sun+sky now); upper-floor rooms with floor, ceiling, partitions, bed, "
        f"chair, plant; sheer linen curtains with real folds; lighter walls for daylight bounce")


# ------------------------------------------------------------------ 7. render/camera settings
def render_v2():
    sc = bpy.context.scene
    sc.cycles.denoising_prefilter = "ACCURATE"; sc.cycles.denoising_quality = "HIGH"
    if not S.PREVIEW:
        sc.cycles.adaptive_threshold = 0.008
    sc.cycles.filter_width = 1.5
    log("render: OIDN prefilter ACCURATE/HIGH, adaptive threshold 0.008, glossy clamp 25 (was 8), transmission depth 24")


def apply_all():
    fix_colorspaces(); vegetation_shading(); build_lawn_v2(); trees_v2(); materials_v2(); interior_v2()
    fix_colorspaces(); vegetation_shading()                      # assets loaded by the steps above
    return LOG
