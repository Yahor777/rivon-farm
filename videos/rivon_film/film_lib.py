"""Shared helpers for the RIVON film (pure bpy + numpy; runs inside plain Blender 5.2 on GitHub Actions)."""
import json, math, struct
from pathlib import Path
import numpy as np
import bpy, mathutils

HERE = Path(__file__).resolve().parent
MM = 0.001
TEX = HERE / "textures"          # symlink -> ../dzialka/textures (created by the workflow)


def load_json(name):
    return json.loads((HERE / name).read_text())


def read_stl(path):
    """Binary STL -> (verts[n,3], faces[m,3]) with shared vertices (exact, no scaling)."""
    raw = Path(path).read_bytes()
    n = struct.unpack("<I", raw[80:84])[0]
    dt = np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    arr = np.frombuffer(raw, dtype=dt, count=n, offset=84)
    tri = arr["v"].reshape(-1, 3).astype(np.float64)
    uniq, inv = np.unique(np.round(tri, 4), axis=0, return_inverse=True)
    return uniq, inv.reshape(-1, 3)


def collection(name, parent=None):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(c)
    return c


def link(obj, coll):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)


# ------------------------------------------------------------------ materials
def _principled(mat):
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return nt, bsdf


def mat_steel():
    """Black powder-coated steel: dielectric paint layer, satin, fine micro-texture. No chrome."""
    m = bpy.data.materials.new("RIVON_black_powder_coat")
    nt, b = _principled(m)
    b.inputs["Base Color"].default_value = (0.006, 0.006, 0.007, 1)
    b.inputs["Metallic"].default_value = 0.15
    b.inputs["Roughness"].default_value = 0.42
    b.inputs["Specular IOR Level"].default_value = 0.3
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 900.0
    noise.inputs["Detail"].default_value = 6.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.08
    bump.inputs["Distance"].default_value = 0.0002
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    rough = nt.nodes.new("ShaderNodeMapRange")
    rough.inputs["To Min"].default_value = 0.42
    rough.inputs["To Max"].default_value = 0.58
    nt.links.new(noise.outputs["Fac"], rough.inputs["Value"])
    nt.links.new(rough.outputs["Result"], b.inputs["Roughness"])
    return m


def mat_screw():
    m = bpy.data.materials.new("fastener_bright_zinc")                 # light galvanised wood screw
    nt, b = _principled(m)
    b.inputs["Base Color"].default_value = (0.66, 0.67, 0.66, 1)
    b.inputs["Metallic"].default_value = 1.0
    b.inputs["Roughness"].default_value = 0.30
    return m


def mat_pine():
    """Planed light pine: concentric rings (pith offset per object), fibre streaks, subtle knots.
    Object-space coordinates with the long axis = local Z, so end grain shows rings automatically."""
    m = bpy.data.materials.new("pine_planed")
    nt, b = _principled(m)
    N = nt.nodes
    tc = N.new("ShaderNodeTexCoord")
    oi = N.new("ShaderNodeObjectInfo")
    # per-object pith offset from Object Info random
    off = N.new("ShaderNodeCombineXYZ")
    mul = N.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = 0.09
    sub = N.new("ShaderNodeMath"); sub.operation = "SUBTRACT"; sub.inputs[1].default_value = 0.5
    nt.links.new(oi.outputs["Random"], sub.inputs[0]); nt.links.new(sub.outputs[0], mul.inputs[0])
    nt.links.new(mul.outputs[0], off.inputs["X"])
    nt.links.new(mul.outputs[0], off.inputs["Y"])
    add = N.new("ShaderNodeVectorMath"); add.operation = "ADD"
    nt.links.new(tc.outputs["Object"], add.inputs[0]); nt.links.new(off.outputs[0], add.inputs[1])
    # rings
    wave = N.new("ShaderNodeTexWave")
    wave.wave_type = "RINGS"; wave.rings_direction = "Z"; wave.wave_profile = "SAW"
    wave.inputs["Scale"].default_value = 55.0
    wave.inputs["Distortion"].default_value = 2.6
    wave.inputs["Detail"].default_value = 2.5
    wave.inputs["Detail Scale"].default_value = 1.4
    nt.links.new(add.outputs[0], wave.inputs["Vector"])
    # long fibre streaks: stretch noise along Z
    map_f = N.new("ShaderNodeMapping")
    map_f.inputs["Scale"].default_value = (350.0, 350.0, 12.0)
    nt.links.new(add.outputs[0], map_f.inputs["Vector"])
    fib = N.new("ShaderNodeTexNoise"); fib.inputs["Detail"].default_value = 4.0
    nt.links.new(map_f.outputs[0], fib.inputs["Vector"])
    # knots: sparse dark blobs
    map_k = N.new("ShaderNodeMapping"); map_k.inputs["Scale"].default_value = (9.0, 9.0, 2.2)
    nt.links.new(add.outputs[0], map_k.inputs["Vector"])
    kn = N.new("ShaderNodeTexNoise"); kn.inputs["Scale"].default_value = 1.0
    kramp = N.new("ShaderNodeValToRGB")
    kramp.color_ramp.elements[0].position = 0.62; kramp.color_ramp.elements[1].position = 0.68
    nt.links.new(map_k.outputs[0], kn.inputs["Vector"]); nt.links.new(kn.outputs["Fac"], kramp.inputs["Fac"])
    # colour
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.60, 0.40, 0.21, 1)
    ramp.color_ramp.elements[1].color = (0.42, 0.25, 0.11, 1)
    ramp.color_ramp.elements[0].position = 0.25; ramp.color_ramp.elements[1].position = 0.85
    nt.links.new(wave.outputs["Fac"], ramp.inputs["Fac"])
    mixf = N.new("ShaderNodeMix"); mixf.data_type = "RGBA"; mixf.inputs[0].default_value = 0.35
    nt.links.new(ramp.outputs["Color"], mixf.inputs[6])
    tint = N.new("ShaderNodeMix"); tint.data_type = "RGBA"
    tint.inputs[7].default_value = (0.58, 0.34, 0.15, 1)
    nt.links.new(fib.outputs["Fac"], mixf.inputs[0])
    nt.links.new(oi.outputs["Random"], tint.inputs[0]); tint.inputs[0].default_value = 0.0
    nt.links.new(ramp.outputs["Color"], mixf.inputs[6])
    mixf.inputs[7].default_value = (0.40, 0.21, 0.08, 1)
    kn_mix = N.new("ShaderNodeMix"); kn_mix.data_type = "RGBA"
    kn_mix.inputs[7].default_value = (0.16, 0.07, 0.02, 1)
    nt.links.new(kramp.outputs["Color"], kn_mix.inputs[0])
    nt.links.new(mixf.outputs[2], kn_mix.inputs[6])
    # per-object slight tone shift
    gam = N.new("ShaderNodeMix"); gam.data_type = "RGBA"
    gam.inputs[7].default_value = (0.62, 0.38, 0.17, 1)
    mr = N.new("ShaderNodeMapRange"); mr.inputs["To Max"].default_value = 0.22
    nt.links.new(oi.outputs["Random"], mr.inputs["Value"]); nt.links.new(mr.outputs["Result"], gam.inputs[0])
    nt.links.new(kn_mix.outputs[2], gam.inputs[6])
    nt.links.new(gam.outputs[2], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.62
    b.inputs["Specular IOR Level"].default_value = 0.3
    bump = N.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.25; bump.inputs["Distance"].default_value = 0.0004
    nt.links.new(wave.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def mat_floor():
    m = bpy.data.materials.new("lab_polished_concrete")
    nt, b = _principled(m)
    b.inputs["Base Color"].default_value = (0.012, 0.013, 0.016, 1)
    b.inputs["Roughness"].default_value = 0.2
    b.inputs["Specular IOR Level"].default_value = 0.6
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 1.6; n1.inputs["Detail"].default_value = 8.0
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = 0.13; mr.inputs["To Max"].default_value = 0.34
    nt.links.new(tc.outputs["Object"], n1.inputs["Vector"]); nt.links.new(n1.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    return m


def mat_wall():
    m = bpy.data.materials.new("lab_graphite_wall")
    nt, b = _principled(m)
    b.inputs["Base Color"].default_value = (0.018, 0.02, 0.024, 1)
    b.inputs["Roughness"].default_value = 0.55
    return m


def mat_emission(name, color, strength):
    m = bpy.data.materials.new(name)
    nt = m.node_tree if m.use_nodes else None
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = color; em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return m



def mesh_from_arrays(name, verts, faces, smooth=False):
    me = bpy.data.meshes.new(name)
    me.from_pydata(np.asarray(verts).tolist(), [], faces.tolist() if hasattr(faces, "tolist") else faces)
    me.update()
    for p in me.polygons:
        p.use_smooth = smooth
    return me


def matrix4(R, t_mm):
    M = np.eye(4); M[:3, :3] = np.array(R); M[:3, 3] = np.array(t_mm) * MM
    return M


def rot_long_axis(axis):
    if axis == "z":
        return np.eye(3)
    if axis == "y":
        a = math.radians(-90); c, s = math.cos(a), math.sin(a)
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    a = math.radians(90); c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def basis_from_z(z):
    z = np.array(z, float); z /= np.linalg.norm(z)
    t = np.array([1.0, 0, 0]) if abs(z[0]) < 0.9 else np.array([0, 1.0, 0])
    x = np.cross(t, z); x /= np.linalg.norm(x); y = np.cross(z, x)
    return np.column_stack([x, y, z])


def pbr(name, diff, rough=None, disp=None, scale=1.0, disp_strength=0.01, tint=None):
    """Poly Haven (CC0) texture set from videos/dzialka/textures; box-projected in object space."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs[0], out.inputs[0])
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale, scale, scale)
    nt.links.new(tc.outputs["Object"], mp.inputs[0])
    def img(fn, cs):
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(str(TEX / fn), check_existing=True)
        t.image.colorspace_settings.name = cs; t.projection = "BOX"; t.projection_blend = 0.2
        nt.links.new(mp.outputs[0], t.inputs[0]); return t
    d = img(diff, "sRGB")
    if tint:
        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
        mix.inputs[0].default_value = 1.0; mix.inputs[7].default_value = tint
        nt.links.new(d.outputs[0], mix.inputs[6]); nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    else:
        nt.links.new(d.outputs[0], b.inputs["Base Color"])
    if rough:
        r = img(rough, "Non-Color"); nt.links.new(r.outputs[0], b.inputs["Roughness"])
    if disp:
        h = img(disp, "Non-Color"); bm = nt.nodes.new("ShaderNodeBump")
        bm.inputs["Strength"].default_value = 0.6; bm.inputs["Distance"].default_value = disp_strength
        nt.links.new(h.outputs[0], bm.inputs["Height"]); nt.links.new(bm.outputs[0], b.inputs["Normal"])
    return m


def simple(name, color, rough=0.5, metal=0.0, spec=0.5, emission=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = color; b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal; b.inputs["Specular IOR Level"].default_value = spec
    if emission:
        b.inputs["Emission Color"].default_value = emission[0]; b.inputs["Emission Strength"].default_value = emission[1]
    return m


def box(name, size, loc, mat, coll, rot_z=0.0, bevel=0.004, rot=None):
    """Axis-aligned box (metres) with a small bevel; origin at its centre."""
    hx, hy, hz = np.array(size) / 2
    v = np.array([[sx * hx, sy * hy, sz * hz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)])
    f = np.array([[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]])
    me = mesh_from_arrays(name, v, f); me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); ob.location = loc; ob.rotation_euler = rot if rot else (0, 0, rot_z)
    if bevel:
        bv = ob.modifiers.new("bev", "BEVEL"); bv.width = bevel; bv.segments = 2; bv.limit_method = "ANGLE"
    link(ob, coll); return ob


def cyl(name, r, h, loc, mat, coll, seg=32, rot=None, bevel=0.0):
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=h)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); ob.location = loc
    if rot: ob.rotation_euler = rot
    if bevel:
        bv = ob.modifiers.new("bev", "BEVEL"); bv.width = bevel; bv.segments = 2
    link(ob, coll); return ob


def sphere(name, r, loc, mat, coll, seg=24, scale=(1, 1, 1)):
    import bmesh
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=r)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); ob.location = loc; ob.scale = scale
    link(ob, coll); return ob


# ------------------------------------------------------------------ the pergola (exact STEP meshes, fixed layout)
def build_pergola(coll_name="PERGOLA"):
    """Instances of the RIVON STEP meshes (mm->m only) + timber + screws, all rigid transforms from layout.json.
    PERGOLA_ROOT keeps an identity transform for the whole film: the pergola never changes."""
    C = load_json("rivon_config.json"); L = load_json("layout.json"); FD = C["fasteners"]
    coll = collection(coll_name)
    steel, screw, pine = mat_steel(), mat_screw(), mat_pine()
    key = {"Stopa": "Stopa", "Trojak 3D": "Trojak_3D", "Mocowanie belek 2": "Mocowanie_belek_2"}
    nsol = {"Stopa": 1, "Trojak_3D": 3, "Mocowanie_belek_2": 1}
    lib = {}
    for k, n in nsol.items():
        lib[k] = []
        for s in range(n):
            v, f = read_stl(HERE / "cad" / f"{k}_s{s}.stl")
            me = mesh_from_arrays(f"CAD_{k}_s{s}", v * MM, f); me.materials.append(steel); lib[k].append(me)
    root = bpy.data.objects.new("PERGOLA_ROOT", None); coll.objects.link(root)
    parts = {}
    for p in L["parts"]:
        k = key[p["cad"]]
        emp = bpy.data.objects.new(f"INST_{p['id']}", None); emp.parent = root
        emp.matrix_world = mathutils.Matrix(matrix4(p["R"], p["t_mm"]).tolist()); coll.objects.link(emp)
        for s, me in enumerate(lib[k]):
            ob = bpy.data.objects.new(f"{p['id']}_s{s}", me); ob.parent = emp; coll.objects.link(ob)
        parts[p["id"]] = emp
    for b in L["timber"]:
        c = np.array(b["centre_mm"]) * MM; R = rot_long_axis(b["long_axis"])
        dl = np.abs(R.T @ (np.array(b["size_mm"]) * MM)); hx, hy, hz = dl / 2
        v = np.array([[sx * hx, sy * hy, sz * hz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)])
        f = np.array([[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]])
        me = mesh_from_arrays(b["id"], v, f); me.materials.append(pine)
        ob = bpy.data.objects.new(b["id"], me); ob.parent = root
        ob.matrix_world = mathutils.Matrix(np.block([[R, c[:, None]], [np.zeros((1, 3)), np.ones((1, 1))]]).tolist())
        bv = ob.modifiers.new("edge_break", "BEVEL"); bv.width = 0.0006; bv.segments = 2; bv.limit_method = "ANGLE"
        coll.objects.link(ob)
    # WOOD SCREW (owner rule: wood screws with a sharp pointed tip, not blunt machine screws). Axis +Z points into the timber.
    # hex head + washer flange, smooth shank under the head, coarse helical thread, thread runs out into a sharp point.
    r, hr, hh, ln = FD["shank_diameter"] / 2 * MM, FD["head_diameter"] / 2 * MM, FD["head_height"] * MM, FD["length"] * MM
    verts, faces = [], []
    nth = 24; pitch = 0.42 * 2 * r; core = 0.64 * r; z_thr = 0.38 * ln; z_tip = ln - 2.6 * r
    def rad(z, th):
        if z < z_thr - 0.6 * pitch: return r                                         # smooth shank
        ph = (z / pitch - th / (2 * np.pi)) % 1.0; tooth = 1 - abs(2 * ph - 1)          # helical V-thread
        rr = core + (r - core) * tooth ** 1.6
        if z < z_thr: rr = r + (rr - r) * (z - (z_thr - 0.6 * pitch)) / (0.6 * pitch)
        if z > z_tip: k = max(0.0, (ln - z) / (ln - z_tip)); rr = rr * k                # sharp tip
        return rr
    zs = list(np.linspace(0, z_thr - 0.6 * pitch, 4)) + list(np.arange(z_thr - 0.6 * pitch, ln, pitch / 8.0))[1:] + [ln]
    for z in zs:
        for i in range(nth):
            th = 2 * np.pi * i / nth; rr = rad(z, th); verts.append([rr * np.cos(th), rr * np.sin(th), z])
    nz = len(zs)
    for a_ in range(nz - 1):
        for i in range(nth):
            j = (i + 1) % nth; faces.append([a_ * nth + i, a_ * nth + j, (a_ + 1) * nth + j, (a_ + 1) * nth + i])
    tip = len(verts); verts.append([0, 0, ln + 0.0002])
    for i in range(nth): faces.append([(nz - 1) * nth + i, (nz - 1) * nth + (i + 1) % nth, tip])
    # washer flange (round) + hex head on top (z negative = outside the part)
    fr, ft = hr * 0.98, 1.3 * MM                                     # flange fits the flat land around the holes (checked on STEP)
    base = len(verts); nf = 28
    for z in (0.0, -ft):
        for i in range(nf): verts.append([fr * np.cos(2 * np.pi * i / nf), fr * np.sin(2 * np.pi * i / nf), z])
    for i in range(nf): j = (i + 1) % nf; faces.append([base + i, base + j, base + nf + j, base + nf + i])
    faces.append([base + i for i in range(nf)][::-1])
    hb = len(verts)
    for z in (-ft, -hh):
        for i in range(6): verts.append([0.9 * hr * np.cos(np.pi / 3 * i + np.pi / 6), 0.9 * hr * np.sin(np.pi / 3 * i + np.pi / 6), z])
    for i in range(6): j = (i + 1) % 6; faces.append([hb + i, hb + j, hb + 6 + j, hb + 6 + i])
    faces.append([hb + 6 + i for i in range(6)][::-1]); faces.append([base + nf + i for i in range(nf)])
    sme = mesh_from_arrays("SCREW_wood", np.array(verts), faces, smooth=True); sme.materials.append(screw)
    import bmesh                                                           # consistent outward normals (shading + collision shrink)
    bm = bmesh.new(); bm.from_mesh(sme); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(sme); bm.free()
    for pl in sme.polygons: pl.use_smooth = max(pl.vertices) <= tip and not (base <= min(pl.vertices))     # thread smooth, head/flange crisp
    for i, f in enumerate(L["fasteners"]):
        ax = np.array(f["axis_to_timber"]); pos = np.array(f["pos_mm"]) * MM - ax / np.linalg.norm(ax) * 0.001
        ob = bpy.data.objects.new(f"SCREW_{i:03d}", sme); ob.parent = root
        ob.matrix_world = mathutils.Matrix(np.block([[basis_from_z(ax), pos[:, None]], [np.zeros((1, 3)), np.ones((1, 1))]]).tolist())
        coll.objects.link(ob)
    import film_roof                                                   # roof: firring wedges + profiled sheets (lab film)
    ids = film_roof.build_roof(coll, pine); bpy.context.view_layer.update()
    for nm in ids:
        o = bpy.data.objects[nm]; mw = o.matrix_world.copy(); o.parent = root; o.matrix_world = mw
    return root
