"""RIVON THE STORM - shared helpers: paths, CC0 asset loading (Poly Haven .blend), procedural materials, mesh helpers.
All units metres. Assets are expected under ASSETS/polyhaven/<id>/<id>_<res>.blend (unpacked from release lib-set1)."""
import os, glob, math, json
from pathlib import Path
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ASSETS = Path(os.environ.get("STORM_ASSETS", ROOT / "lib"))
CAD = ROOT / "cad"
MM = 0.001
PREVIEW = os.environ.get("STORM_QUALITY", "final") == "preview"   # light LODs + sparse grass for low-RAM look-dev
RNG = np.random.default_rng(20261112)          # fixed seed: every build is identical


# ---------------------------------------------------------------- collections / objects
def coll(name, parent=None):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c


def link(ob, c):
    for u in list(ob.users_collection):
        u.objects.unlink(ob)
    c.objects.link(ob)
    return ob


def mesh_obj(name, verts, faces, c, mat=None, smooth=False):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.validate(); me.update()
    if smooth:
        me.shade_smooth()
    if mat:
        me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); c.objects.link(ob)
    return ob


def box(name, size, loc, c, mat=None, bevel=0.0, rot_z=0.0, seg=2):
    sx, sy, sz = [s / 2 for s in size]
    v = [(x, y, z) for x in (-sx, sx) for y in (-sy, sy) for z in (-sz, sz)]
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    ob = mesh_obj(name, v, f, c, mat)
    ob.location = loc; ob.rotation_euler.z = rot_z
    if bevel > 0:
        m = ob.modifiers.new("bevel", "BEVEL"); m.width = bevel; m.segments = seg; m.limit_method = "ANGLE"
        m.harden_normals = False
        ob.data.shade_smooth();
        ws = ob.modifiers.new("ws", "WEIGHTED_NORMAL"); ws.keep_sharp = True
    return ob


def lathe(name, profile, c, mat=None, seg=96):
    """Revolve a (r, z) profile (list, bottom->top, outer then inner) around Z. Used for glasses, plates, bottle."""
    verts, faces = [], []
    n = len(profile)
    for i in range(seg):
        a = 2 * math.pi * i / seg; ca, sa = math.cos(a), math.sin(a)
        for r, z in profile:
            verts.append((r * ca, r * sa, z))
    for i in range(seg):
        j = (i + 1) % seg
        for k in range(n - 1):
            faces.append((i * n + k, j * n + k, j * n + k + 1, i * n + k + 1))
    ob = mesh_obj(name, verts, faces, c, mat, smooth=True)
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(ob.data); bm.free(); ob.data.shade_smooth()
    return ob


# ---------------------------------------------------------------- Poly Haven assets
def ph_blend(aid):
    hits = sorted(glob.glob(str(ASSETS / "polyhaven" / aid / f"{aid}_*.blend")))
    if not hits:
        raise FileNotFoundError(f"asset {aid} missing under {ASSETS}/polyhaven (unpack release lib-set1)")
    return hits[-1]


def ph_material(aid, name=None):
    """Append the material shipped in a Poly Haven texture .blend (full PBR graph with relative texture paths)."""
    key = name or f"PH_{aid}"
    if key in bpy.data.materials:
        return bpy.data.materials[key]
    path = ph_blend(aid)
    with bpy.data.libraries.load(path, link=False, relative=False) as (src, dst):
        dst.materials = list(src.materials)
    mats = [m for m in dst.materials if m]
    m = max(mats, key=lambda m: len(m.node_tree.nodes) if m.use_nodes else 0)
    m.name = key
    # Poly Haven ships true displacement; on low-poly boxes it pushes whole faces outward by centimetres (a beam would swallow
    # the 2 mm RIVON socket wall). Height becomes bump only: geometry stays exactly where the CAD layout puts it.
    m.displacement_method = "BUMP"
    for im in bpy.data.images:                        # make texture paths absolute to the unpacked asset folder
        if im.filepath.startswith("//"):
            im.filepath = str(Path(path).parent / im.filepath[2:])
    return m


def ph_collection(aid):
    """Append all objects of a Poly Haven model .blend into a hidden library collection (for instancing)."""
    key = f"LIB_{aid}"
    if key in bpy.data.collections:
        return bpy.data.collections[key]
    path = ph_blend(aid)
    with bpy.data.libraries.load(path, link=False, relative=False) as (src, dst):
        dst.objects = list(src.objects)
    for im in bpy.data.images:
        if im.filepath.startswith("//"):
            im.filepath = str(Path(path).parent / im.filepath[2:])
    lib = bpy.data.collections.new(key)
    root = coll("_LIBRARY"); root.children.link(lib)
    for o in dst.objects:
        if o is not None:
            lib.objects.link(o)
    bpy.context.view_layer.layer_collection.children["_LIBRARY"].exclude = True
    return lib


def ph_variants(aid, lod=None, prefix=None):
    """Mesh datablocks of every variant of a Poly Haven vegetation/prop asset at the given LOD (each centred at its origin).
    Shared datablocks -> instancing for free."""
    if lod is None:
        lod = 2 if PREVIEW else 0
    key = f"VAR_{aid}_{lod}_{prefix}"
    cache = bpy.app.driver_namespace.setdefault("ph_variants", {})
    if key in cache:
        return cache[key]
    path = ph_blend(aid)
    with bpy.data.libraries.load(path, link=False, relative=False) as (src, dst):
        names = []
        for l in range(lod, -1, -1):                       # requested LOD, else the nearest finer one
            names = [c for c in src.collections if c == f"{aid}_LOD{l}"]
            if names:
                break
        names = names or [c for c in src.collections if c == aid]
        dst.collections = names
    for im in bpy.data.images:
        if im.filepath.startswith("//"):
            im.filepath = str(Path(path).parent / im.filepath[2:])
    meshes = []
    for c in dst.collections:
        for o in c.all_objects:
            if o.type == "MESH" and (prefix is None or o.name.startswith(prefix)):
                meshes.append(o.data)
        for o in list(c.all_objects):
            bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.collections.remove(c)
    cache[key] = meshes
    return meshes


def place(me, name, loc, c, rot_z=0.0, scale=1.0, tilt=0.0):
    ob = bpy.data.objects.new(name, me); c.objects.link(ob)
    ob.location = loc; ob.rotation_euler = (float(RNG.normal(0, tilt)), float(RNG.normal(0, tilt)), rot_z)
    ob.scale = (scale,) * 3 if np.isscalar(scale) else scale
    return ob


def ph_objects(aid):
    return [o for o in ph_collection(aid).objects if o.type == "MESH"]


def instance(lib, name, loc, c, rot_z=0.0, scale=1.0):
    e = bpy.data.objects.new(name, None)
    e.instance_type = "COLLECTION"; e.instance_collection = lib
    e.location = loc; e.rotation_euler.z = rot_z; e.scale = (scale,) * 3
    c.objects.link(e)
    return e


def lib_bounds(lib):
    pts = []
    for o in lib.objects:
        if o.type == "MESH":
            pts += [o.matrix_world @ Vector(b) for b in o.bound_box]
    P = np.array([list(p) for p in pts])
    return P.min(0), P.max(0)


# ---------------------------------------------------------------- materials
def _nodes(m):
    m.use_nodes = True
    return m.node_tree.nodes, m.node_tree.links


def principled(m):
    return next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def mat_powder_coat():
    """RAL 9005 fine-texture powder coat: near-black dielectric, rough 0.38-0.5 varying, micro orange-peel bump (~0.3 mm)."""
    if "RIVON_powder_RAL9005" in bpy.data.materials:
        return bpy.data.materials["RIVON_powder_RAL9005"]
    m = bpy.data.materials.new("RIVON_powder_RAL9005"); N, L = _nodes(m); b = principled(m)
    b.inputs["Base Color"].default_value = (0.0105, 0.0105, 0.0112, 1)
    b.inputs["Metallic"].default_value = 0.0
    b.inputs["IOR"].default_value = 1.52
    tc = N.new("ShaderNodeTexCoord")
    peel = N.new("ShaderNodeTexVoronoi"); peel.feature = "SMOOTH_F1"; peel.inputs["Scale"].default_value = 2600
    L.new(tc.outputs["Object"], peel.inputs["Vector"])
    fine = N.new("ShaderNodeTexNoise"); fine.inputs["Scale"].default_value = 9000; fine.inputs["Detail"].default_value = 2
    L.new(tc.outputs["Object"], fine.inputs["Vector"])
    big = N.new("ShaderNodeTexNoise"); big.inputs["Scale"].default_value = 18; big.inputs["Detail"].default_value = 3
    L.new(tc.outputs["Object"], big.inputs["Vector"])
    rr = N.new("ShaderNodeMapRange"); rr.inputs["To Min"].default_value = 0.36; rr.inputs["To Max"].default_value = 0.5
    L.new(big.outputs["Fac"], rr.inputs["Value"]); L.new(rr.outputs["Result"], b.inputs["Roughness"])
    mix = N.new("ShaderNodeMath"); mix.operation = "MULTIPLY_ADD"; mix.inputs[1].default_value = 0.35
    L.new(fine.outputs["Fac"], mix.inputs[0]); L.new(peel.outputs["Distance"], mix.inputs[2])
    bump = N.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.22; bump.inputs["Distance"].default_value = 0.00025
    L.new(mix.outputs["Value"], bump.inputs["Height"]); L.new(bump.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Coat Weight"].default_value = 0.0
    return m


def mat_glass(name="glass_clear", tint=(0.98, 0.99, 0.985, 1), rough=0.0):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = bpy.data.materials.new(name); _nodes(m); b = principled(m)
    b.inputs["Base Color"].default_value = tint
    b.inputs["Roughness"].default_value = rough
    b.inputs["IOR"].default_value = 1.5
    b.inputs["Transmission Weight"].default_value = 1.0
    return m


def mat_simple(name, color, rough=0.5, metal=0.0, spec=0.5):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = bpy.data.materials.new(name); _nodes(m); b = principled(m)
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Specular IOR Level"].default_value = spec
    return m


def mat_variant(base, name, hue_shift=0.0, val=1.0, uv_offset=(0, 0), rough_add=0.0):
    """Copy of a PBR material with its own UV offset and a slight colour shift, so neighbouring boards are not identical."""
    m = base.copy(); m.name = name
    N, L = m.node_tree.nodes, m.node_tree.links
    maps = [n for n in N if n.type == "MAPPING"]
    for mp in maps:
        mp.inputs["Location"].default_value[0] += uv_offset[0]
        mp.inputs["Location"].default_value[1] += uv_offset[1]
    b = principled(m)
    src = b.inputs["Base Color"].links[0].from_socket if b.inputs["Base Color"].is_linked else None
    if src is not None:
        hsv = N.new("ShaderNodeHueSaturation")
        hsv.inputs["Hue"].default_value = 0.5 + hue_shift; hsv.inputs["Value"].default_value = val
        L.new(src, hsv.inputs["Color"]); L.new(hsv.outputs["Color"], b.inputs["Base Color"])
    if rough_add and b.inputs["Roughness"].is_linked:
        rs = b.inputs["Roughness"].links[0].from_socket
        ad = N.new("ShaderNodeMath"); ad.operation = "ADD"; ad.inputs[1].default_value = rough_add; ad.use_clamp = True
        L.new(rs, ad.inputs[0]); L.new(ad.outputs[0], b.inputs["Roughness"])
    return m


def set_tex_scale(m, scale):
    for n in m.node_tree.nodes:
        if n.type == "MAPPING":
            n.inputs["Scale"].default_value = (scale, scale, scale)


def uv_box(ob, size=1.0):
    """World-scale box-projection UVs (1 UV unit = `size` metres) so PBR textures keep real-world scale."""
    me = ob.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    uv = me.uv_layers.active.data
    M = ob.matrix_world
    for p in me.polygons:
        n = (M.to_3x3() @ p.normal).normalized(); ax = max(range(3), key=lambda i: abs(n[i]))
        for li in p.loop_indices:
            co = M @ me.vertices[me.loops[li].vertex_index].co
            u, v = [(co.y, co.z), (co.x, co.z), (co.x, co.y)][ax]
            uv[li].uv = (u / size, v / size)


def tint(m, rgb, gain=1.0):
    """Multiply a PBR material's base colour (keeps the scan's variation)."""
    N, L = m.node_tree.nodes, m.node_tree.links; b = principled(m)
    if not b.inputs["Base Color"].is_linked:
        c = b.inputs["Base Color"].default_value; b.inputs["Base Color"].default_value = (c[0]*rgb[0]*gain, c[1]*rgb[1]*gain, c[2]*rgb[2]*gain, 1); return
    src = b.inputs["Base Color"].links[0].from_socket
    mx = N.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"; mx.inputs["Factor"].default_value = 1.0
    mx.inputs[7].default_value = (rgb[0] * gain, rgb[1] * gain, rgb[2] * gain, 1)
    L.new(src, mx.inputs[6]); L.new(mx.outputs[2], b.inputs["Base Color"])


def calm_albedo(m, rgb, keep=0.25):
    """Replace a scan's albedo by a uniform colour, keeping `keep` of the scan's variation (scan normal/roughness untouched).
    Used where the scan is dirtier than a new surface (fresh render, new porcelain)."""
    N, L = m.node_tree.nodes, m.node_tree.links; b = principled(m)
    if not b.inputs["Base Color"].is_linked:
        return
    src = b.inputs["Base Color"].links[0].from_socket
    bw = N.new("ShaderNodeRGBToBW"); L.new(src, bw.inputs[0])
    # normalise around the scan's mid grey (~0.35) -> multiplier near 1
    mul = N.new("ShaderNodeMath"); mul.operation = "DIVIDE"; mul.inputs[1].default_value = 0.35; L.new(bw.outputs[0], mul.inputs[0])
    lerp = N.new("ShaderNodeMapRange"); lerp.clamp = False
    lerp.inputs["From Min"].default_value = 0.0; lerp.inputs["From Max"].default_value = 1.0
    lerp.inputs["To Min"].default_value = 1.0 - keep; lerp.inputs["To Max"].default_value = 1.0
    L.new(mul.outputs[0], lerp.inputs["Value"])
    cm = N.new("ShaderNodeMix"); cm.data_type = "RGBA"; cm.blend_type = "MULTIPLY"; cm.inputs["Factor"].default_value = 1.0
    cm.inputs[6].default_value = (*rgb, 1)
    comb = N.new("ShaderNodeCombineColor")
    for k in range(3):
        L.new(lerp.outputs[0], comb.inputs[k])
    L.new(comb.outputs[0], cm.inputs[7]); L.new(cm.outputs[2], b.inputs["Base Color"])
