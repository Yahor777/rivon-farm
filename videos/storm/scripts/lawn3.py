"""Lawn v3 - a mown garden lawn as a camera sees it, built from how real turf looks:
  * blades stand mostly upright (mown turf is dense, blades support each other): lean +-15-20 deg, not lying flat
  * cut length 3.5-5.5 cm; mower-cut tips are blunt and slightly paler/straw (torn leaf ends dry out)
  * very dense where the camera looks (~20-30k shoots/m2 near the terrace), thinner further out
  * mixture: fine fescue (narrow, dark), perennial rye (wider, glossy underside), a few longer blades the mower missed,
    ~4 % dead straw blades; no seed heads (a mown lawn has none)
  * simple (non-interpolated) children scattered around each parent: no copied clumps -> no streaks
  * thatch layer under the blades: dark olive-brown, never bare soil
Used for every shot (sun and storm); weather.lawn_overcast() only re-grades the colour."""
import math
import bpy
import storm_lib as S

LOG = []


def blade_mat(name, tip, mid, root, straw=0.04, gloss=0.42):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links; pb = S.principled(m)
    hi = N.new("ShaderNodeHairInfo")
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (*root, 1); ramp.color_ramp.elements[1].color = (tip[0] * 1.35, tip[1] * 1.15, tip[2] * 1.1, 1)
    e1 = ramp.color_ramp.elements.new(0.45); e1.color = (*mid, 1)
    e2 = ramp.color_ramp.elements.new(0.90); e2.color = (*tip, 1)             # blunt cut end: thin paler band
    L.new(hi.outputs["Intercept"], ramp.inputs["Fac"])
    # per blade: hue/value spread + a few dead straw blades (Random < straw)
    hsv = N.new("ShaderNodeHueSaturation")
    mh = N.new("ShaderNodeMapRange"); mh.inputs["To Min"].default_value = 0.475; mh.inputs["To Max"].default_value = 0.53
    mv = N.new("ShaderNodeMapRange"); mv.inputs["To Min"].default_value = 0.72; mv.inputs["To Max"].default_value = 1.18
    L.new(hi.outputs["Random"], mh.inputs["Value"]); L.new(hi.outputs["Random"], mv.inputs["Value"])
    L.new(mh.outputs[0], hsv.inputs["Hue"]); L.new(mv.outputs[0], hsv.inputs["Value"]); L.new(ramp.outputs["Color"], hsv.inputs["Color"])
    dead = N.new("ShaderNodeMath"); dead.operation = "LESS_THAN"; dead.inputs[1].default_value = straw
    L.new(hi.outputs["Random"], dead.inputs[0])
    mix = N.new("ShaderNodeMix"); mix.data_type = "RGBA"; L.new(dead.outputs[0], mix.inputs["Factor"])
    L.new(hsv.outputs["Color"], mix.inputs[6]); mix.inputs[7].default_value = (0.30, 0.25, 0.12, 1)
    # turf is never one colour: broad patches (soil moisture, fertiliser, wear) shift value/hue over 1-3 m
    geo = N.new("ShaderNodeNewGeometry"); nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.55
    nz.inputs["Detail"].default_value = 3; L.new(geo.outputs["Position"], nz.inputs["Vector"])
    nz2 = N.new("ShaderNodeTexNoise"); nz2.inputs["Scale"].default_value = 2.8; nz2.inputs["Detail"].default_value = 2
    L.new(geo.outputs["Position"], nz2.inputs["Vector"])
    patch = N.new("ShaderNodeMix"); patch.data_type = "RGBA"; patch.blend_type = "MULTIPLY"
    pr = N.new("ShaderNodeValToRGB"); pr.color_ramp.elements[0].position = 0.35; pr.color_ramp.elements[1].position = 0.65
    pr.color_ramp.elements[0].color = (0.80, 0.84, 0.70, 1); pr.color_ramp.elements[1].color = (1.12, 1.08, 1.05, 1)
    L.new(nz.outputs["Fac"], pr.inputs["Fac"]); patch.inputs["Factor"].default_value = 1.0
    L.new(mix.outputs[2], patch.inputs[6]); L.new(pr.outputs["Color"], patch.inputs[7])
    pr2 = N.new("ShaderNodeValToRGB"); pr2.color_ramp.elements[0].position = 0.3; pr2.color_ramp.elements[1].position = 0.7
    pr2.color_ramp.elements[0].color = (0.92, 0.92, 0.9, 1); pr2.color_ramp.elements[1].color = (1.06, 1.05, 1.0, 1)
    L.new(nz2.outputs["Fac"], pr2.inputs["Fac"])
    patch2 = N.new("ShaderNodeMix"); patch2.data_type = "RGBA"; patch2.blend_type = "MULTIPLY"; patch2.inputs["Factor"].default_value = 1.0
    L.new(patch.outputs[2], patch2.inputs[6]); L.new(pr2.outputs["Color"], patch2.inputs[7])
    L.new(patch2.outputs[2], pb.inputs["Base Color"])
    pb.inputs["Roughness"].default_value = gloss; pb.inputs["Specular IOR Level"].default_value = 0.45
    # thin-blade translucency (light through the leaf), warm-shifted like the rest of the vegetation
    out = next(n for n in N if n.type == "OUTPUT_MATERIAL")
    tr = N.new("ShaderNodeBsdfTranslucent"); hs2 = N.new("ShaderNodeHueSaturation"); hs2.inputs["Saturation"].default_value = 1.15
    hs2.inputs["Value"].default_value = 0.9; L.new(mix.outputs[2], hs2.inputs["Color"]); L.new(hs2.outputs["Color"], tr.inputs["Color"])
    ms = N.new("ShaderNodeMixShader"); ms.inputs["Fac"].default_value = 0.35
    L.new(pb.outputs[0], ms.inputs[1]); L.new(tr.outputs[0], ms.inputs[2]); L.new(ms.outputs[0], out.inputs["Surface"])
    m["leafified"] = 1
    return m


SPECS = [  # name, parents per unit-weight m2 (x area), length, rand, width radius, cols (tip, mid, root), lean, children
    ("lawn_fescue", 5200, 0.038, 0.35, 0.00085, ((0.105, 0.18, 0.040), (0.050, 0.110, 0.020), (0.018, 0.035, 0.008)), 0.30, 3),
    ("lawn_rye",    2600, 0.046, 0.35, 0.00130, ((0.125, 0.20, 0.050), (0.060, 0.125, 0.024), (0.020, 0.038, 0.009)), 0.34, 3),
    ("lawn_missed",  120, 0.072, 0.40, 0.00110, ((0.13, 0.20, 0.055), (0.065, 0.12, 0.025), (0.02, 0.04, 0.01)), 0.55, 2),
]


def trim_density(lawn, x_max=19.8, y_abs=10.3, clear=()):
    """no blades where no camera can see them: under the dune (x > 19.8) and far beyond the side fences"""
    vg = lawn.vertex_groups.get("density")
    if not vg:
        return
    ox = lawn.matrix_world.translation.x
    for v in lawn.data.vertices:
        x, y = v.co.x + ox, v.co.y
        if v.co.z < -0.4:                                   # under the terrace
            vg.add([v.index], 0.0, "REPLACE"); continue
        # full density where cameras look (terrace edge -> 8 m), thinning beyond: memory goes where it shows
        d = math.hypot(x - 5.0, y + 1.0)
        vg.add([v.index], max(0.07, min(1.0, 1.55 - d / 8.0)), "REPLACE")
        if x > x_max or abs(y) > y_abs + 6:
            vg.add([v.index], 0.0, "REPLACE")
        elif abs(y) > y_abs:
            vg.add([v.index], 0.03, "REPLACE")
        for (cx, cy, cr) in clear:                              # stepping stones: no blades under them
            if (x - cx) ** 2 + (y - cy) ** 2 < cr * cr:
                vg.add([v.index], 0.0, "REPLACE"); break


def build(lawn, area_m2, preview=False):
    for md in list(lawn.modifiers):
        if md.type == "PARTICLE_SYSTEM":
            lawn.modifiers.remove(md)
    while len(lawn.data.materials) > 1:
        lawn.data.materials.pop()
    tot = 0
    for k, (nm, per_m2, ln, rr, rad, cols, lean, kids) in enumerate(SPECS):
        mat = blade_mat(f"grass_{nm}", *cols, straw=0.04 if nm != "lawn_missed" else 0.12)
        lawn.data.materials.append(mat)
        ps = lawn.modifiers.new(nm, "PARTICLE_SYSTEM").particle_system; st = bpy.data.particles.new(nm); ps.settings = st
        cnt = int(per_m2 * area_m2 * (0.12 if preview else 1.0))
        st.type = "HAIR"; st.count = cnt; st.hair_length = ln; st.use_advanced_hair = True; st.hair_step = 3
        st.material = len(lawn.data.materials); st.emit_from = "FACE"; st.use_emit_random = True; st.use_even_distribution = True
        st.distribution = "RAND"          # NOT jittered: the jitter table caps particles per face, and on the 25 cm lawn
                                          # faces that left ~150 parents/m2 in a visible grid of tufts (d1 stills)
        st.child_type = "SIMPLE"; st.child_percent = 2; st.rendered_child_count = kids if not preview else max(2, kids // 3)
        st.child_radius = 0.012; st.child_roundness = 0.0; st.child_length = 1.0; st.child_length_threshold = 0.0
        st.clump_factor = 0.0; st.child_parting_factor = 0.0
        st.length_random = rr
        # upright with individual lean: velocity mostly along the normal, random part gives +-lean
        # NB measured: in this Blender the strand length follows the emission velocity (~4.1 x normal_factor), not
        # hair_length - the v2 lawn asked for 4.2 cm and got ~17 cm blades (the 'field of long grass' look)
        V = ln / 4.1
        st.normal_factor = V; st.factor_random = V * lean; st.tangent_factor = 0.0; st.object_align_factor = (0, 0, 0)
        st.use_rotations = True; st.rotation_mode = "NOR"; st.rotation_factor_random = 1.0; st.phase_factor_random = 2.0
        # gentle individual curvature, no shared wave
        st.roughness_1 = ln * 0.10; st.roughness_1_size = 0.9; st.roughness_endpoint = ln * 0.12; st.roughness_end_shape = 1.6
        st.roughness_2 = ln * 0.05; st.roughness_2_size = 2.0; st.roughness_2_threshold = 0.2
        st.kink = "NO"
        st.root_radius = 1.0; st.tip_radius = 0.45 if nm != "lawn_missed" else 0.1   # mown = blunt cut tips
        st.radius_scale = rad; st.shape = 0.15
        ps.vertex_group_density = "density"; ps.seed = 101 + 37 * k
        tot += cnt * (1 + st.rendered_child_count)
    sc = bpy.context.scene
    sc.cycles_curves.shape = "RIBBONS"; sc.cycles_curves.subdivisions = 2
    soil = lawn.data.materials[0]
    if soil and "thatch" not in soil:                         # thatch: dark olive-brown dead-grass mat, never bare soil
        S.calm_albedo(soil, (0.075, 0.085, 0.035), keep=0.35); soil["thatch"] = 1
    LOG.append(f"lawn v3: mown turf - fescue + rye + a few missed blades, 3.5-5.5 cm, blunt paler cut tips, upright with "
               f"+-17 deg individual lean, simple scattered children (no clump streaks), 4 % straw blades, dark thatch; "
               f"~{tot / 1e6:.1f} M rendered blades")
    return LOG


def weighted_area(lawn):
    """sum(face area x mean density weight): particle counts are spread by the density group, so per-m2 targets must be
    multiplied by this, not by the raw area"""
    me = lawn.data; vg = lawn.vertex_groups["density"]; gi = vg.index
    w = [0.0] * len(me.vertices)
    for v in me.vertices:
        for g in v.groups:
            if g.group == gi:
                w[v.index] = g.weight
    sx, sy, sz = lawn.scale
    return sum(p.area * sx * sy * sum(w[i] for i in p.vertices) / len(p.vertices) for p in me.polygons)
