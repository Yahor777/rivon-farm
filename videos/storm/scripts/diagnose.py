"""Technical diagnostics of the built scene (not visual guesses). Writes a Markdown report.
python3 -I diagnose.py <report.md>"""
import sys, os, math
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import bpy
import numpy as np
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
import storm_lib as S, build_world as BW, design as D, look as LK
D.build_all_v2(with_pergola=False); D.realism_pass()
LK.setup_sky(32, 135); LK.setup_render(1080, 1920, 256)
R = []
P = lambda *a: R.append(" ".join(str(x) for x in a))

P("# Scene diagnostics (q2 state)\n")
sc = bpy.context.scene
P("## Render / colour")
P(f"- engine {sc.render.engine}, view {sc.view_settings.view_transform} / look {sc.view_settings.look}, exposure {sc.view_settings.exposure}")
P(f"- bounces max/diff/gloss/trans/transp/vol: {sc.cycles.max_bounces}/{sc.cycles.diffuse_bounces}/{sc.cycles.glossy_bounces}/"
  f"{sc.cycles.transmission_bounces}/{sc.cycles.transparent_max_bounces}/{sc.cycles.volume_bounces}")
P(f"- clamp indirect {sc.cycles.sample_clamp_indirect}, blur_glossy {sc.cycles.blur_glossy}, caustics refl/refr {sc.cycles.caustics_reflective}/{sc.cycles.caustics_refractive}")
P(f"- denoiser {sc.cycles.denoiser}, passes {sc.cycles.denoising_input_passes}, adaptive thr {sc.cycles.adaptive_threshold}")
P(f"- film filter width {sc.cycles.filter_width}, motion blur {sc.render.use_motion_blur}")

P("\n## Lights (should be: sun/sky only by day)")
for o in bpy.data.objects:
    if o.type == "LIGHT":
        P(f"- {o.name}: {o.data.type} {o.data.energy} W colour {tuple(round(c, 2) for c in o.data.color)}")
w = sc.world.node_tree.nodes
sky = next(n for n in w if n.type == "TEX_SKY")
P(f"- sky {sky.sky_type}, sun disc {sky.sun_disc}, elev {math.degrees(sky.sun_elevation):.1f}, aerosol {sky.aerosol_density}, air {sky.air_density}")

P("\n## Image textures: colour space of data maps (normal/rough/disp must be Non-Color)")
bad_cs = []
for im in bpy.data.images:
    n = im.name.lower()
    data = any(k in n for k in ("nor", "rough", "disp", "arm", "ao", "spec", "metal"))
    cs = im.colorspace_settings.name
    if data and cs not in ("Non-Color", "Linear Rec.709", "Raw"):
        bad_cs.append((im.name, cs))
    if not data and cs == "Non-Color":
        bad_cs.append((im.name + " (albedo flagged Non-Color)", cs))
P(f"- images loaded: {len(bpy.data.images)}; colour-space problems: {len(bad_cs)}")
for a, b in bad_cs[:30]:
    P(f"  - {a}: {b}")

P("\n## Normal maps / bump per material")
for m in bpy.data.materials:
    if not m.use_nodes:
        continue
    nm = [n for n in m.node_tree.nodes if n.type == "NORMAL_MAP"]
    bm = [n for n in m.node_tree.nodes if n.type == "BUMP"]
    disp = [n for n in m.node_tree.nodes if n.type == "DISPLACEMENT"]
    if not (nm or bm or disp):
        continue
    s = []
    for n in nm:
        s.append(f"normalmap space={n.space} strength={n.inputs['Strength'].default_value:.2f}")
        src = n.inputs["Color"].links[0].from_node if n.inputs["Color"].is_linked else None
        if src is not None and src.type == "TEX_IMAGE" and src.image:
            s[-1] += f" img={src.image.name} cs={src.image.colorspace_settings.name}"
    for n in bm:
        s.append(f"bump strength={n.inputs['Strength'].default_value:.2f} dist={n.inputs['Distance'].default_value}")
    for n in disp:
        s.append(f"displacement scale={n.inputs['Scale'].default_value} (method {m.displacement_method})")
    if m.users and not m.name.startswith(("oak_board", "timber_", "larch_", "soffit_slat", "chair_", "table_oak_")):
        P(f"- {m.name}: " + "; ".join(s))

P("\n## Texture-space scale (UV metres per tile) on key objects")
def uv_density(o):
    me = o.data
    if not me.uv_layers:
        return None
    uv = me.uv_layers.active.data; ratios = []
    for p in list(me.polygons)[:400]:
        if len(p.loop_indices) < 3:
            continue
        l = p.loop_indices; a, b = me.loops[l[0]].vertex_index, me.loops[l[1]].vertex_index
        d3 = (o.matrix_world @ me.vertices[a].co - o.matrix_world @ me.vertices[b].co).length
        d2 = (Vector(uv[l[0]].uv) - Vector(uv[l[1]].uv)).length
        if d2 > 1e-6 and d3 > 1e-4:
            ratios.append(d3 / d2)
    return np.median(ratios) if ratios else None
for n in ["deck_boards", "gf_wall", "up_wall", "table top_0", "top_0", "step_E", "lawn", "planter0_a", "larch_00"]:
    o = bpy.data.objects.get(n)
    if o and o.type == "MESH":
        P(f"- {n}: {uv_density(o)} m per UV unit; material {o.data.materials[0].name if o.data.materials else None}")

P("\n## Vegetation materials (translucency / subsurface present? NOTE: Poly Haven foliage hides it inside a node group - check groups)")
seen = set()
for o in bpy.data.objects:
    if o.type == "MESH" and any(k in o.name for k in ("tree", "shrub", "grass", "fern", "tuft", "flower")):
        for m in o.data.materials:
            if m and m.name not in seen:
                seen.add(m.name)
                nodes = [n.type for n in m.node_tree.nodes] if m.use_nodes else []
                pb = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if m.use_nodes else None
                tr = pb.inputs["Transmission Weight"].default_value if pb else None
                ss = pb.inputs["Subsurface Weight"].default_value if pb else None
                P(f"- {m.name}: translucent_node={'BSDF_TRANSLUCENT' in nodes}, transmission={tr}, subsurface={ss}, "
                  f"alpha_linked={pb.inputs['Alpha'].is_linked if pb else None}")
lawn = bpy.data.objects["lawn"]; ps = lawn.particle_systems[0].settings
P(f"- lawn hair: count {ps.count} x children {ps.rendered_child_count}, length {ps.hair_length}, random {ps.length_random}, clump {ps.clump_factor}, "
  f"systems {len(lawn.particle_systems)} (single blade type)")
counts = {}
for o in bpy.data.objects:
    if o.type == "MESH" and o.data and o.name.split("_")[0] in ("tree", "ringtree", "planter0", "planter1"):
        counts[o.data.name] = counts.get(o.data.name, 0) + 1
P(f"- tree mesh reuse: {counts}")

P("\n## Glass / wine")
for n in ("wine_glass_0", "wine_0", "hero_drop"):
    o = bpy.data.objects.get(n)
    if not o:
        P(f"- {n}: absent"); continue
    me = o.data
    nm = sum(1 for e in me.edges if len([p for p in me.polygons if e.key in p.edge_keys]) != 2)
    P(f"- {n}: verts {len(me.vertices)}, non-manifold edges {nm}, materials {[m.name for m in me.materials]}")
for n in ("wine_glass", "red_wine", "red_wine_glass_interface", "window_glass"):
    m = bpy.data.materials.get(n)
    if m:
        pb = S.principled(m)
        vol = [x for x in m.node_tree.nodes if x.type.startswith("VOLUME")]
        P(f"- {n}: IOR {pb.inputs['IOR'].default_value:.3f}, transm {pb.inputs['Transmission Weight'].default_value}, "
          f"rough {'linked' if pb.inputs['Roughness'].is_linked else pb.inputs['Roughness'].default_value}, base {tuple(round(c,2) for c in pb.inputs['Base Color'].default_value)}, "
          f"volume {[ (v.type, tuple(round(c,3) for c in v.inputs['Color'].default_value), v.inputs['Density'].default_value) for v in vol]}")
P("- meniscus: none (wine top is a flat disc)")

P("\n## Interior")
for n in ("int_floor", "int_back", "int_ceiling"):
    o = bpy.data.objects.get(n); P(f"- {n}: {'present' if o else 'MISSING'}")
P(f"- upper floor rooms behind first-floor windows: {'present' if bpy.data.objects.get('up_room_floor') else 'MISSING (black voids)'}")
P(f"- curtains: {'present' if any(o.name.startswith('curtain') for o in bpy.data.objects) else 'none'}")

P("\n## Camera (shots)")
P("- sensor: vertical fit 36 mm; lenses wide 24 mm, s01 32 mm, glass 50 mm; DOF on")
Path(sys.argv[1]).write_text("\n".join(R))
print("REPORT", sys.argv[1])
