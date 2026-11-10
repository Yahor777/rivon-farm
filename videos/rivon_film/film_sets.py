"""Bright daylight sets for the five RIVON applications, modelled from primitives at real-world scale (no photo panoramas).
Pergola stays at the world origin (long axis = Y).  Every set has its own house, yard, trees and light."""
import math
import numpy as np
import bpy, bmesh, mathutils
from film_lib import *   # noqa
import film_envs as E
from film_stage import mat_matte, _nodes


# ------------------------------------------------------------------------------------------------ materials
_C = {}
def cached(key, fn):
    if key not in _C or _C[key].name not in bpy.data.materials: _C[key] = fn()
    return _C[key]


def tinted_pbr(key, diff, rough, disp, scale, tint, ds=0.002):
    return cached(key, lambda: pbr(key, diff, rough, disp, scale, ds, tint=(*tint, 1)))


def plaster(color, key=None):
    return tinted_pbr(key or f"plaster_{color}", "beige_wall_002_diff_2k.jpg", "beige_wall_002_rough_2k.jpg", "beige_wall_002_disp_2k.png", 0.5, tuple(c * 1.55 for c in color), 0.004)


def roof_tiles(color): return tinted_pbr(f"roof_{color}", "clay_roof_tiles_03_diff_2k.jpg", "clay_roof_tiles_03_rough_2k.exr", "clay_roof_tiles_03_disp_2k.png", 0.55, color, 0.01)
def paving(color, scale=0.6, key=None): return tinted_pbr(key or f"paving_{color}", "stone_tiles_02_diff_2k.jpg", "stone_tiles_02_rough_2k.exr", "stone_tiles_02_disp_2k.png", scale, color, 0.004)
def timber(color, scale=1.2, key=None): return tinted_pbr(key or f"timber_{color}", "teak_veneer_diff_2k.jpg", "teak_veneer_rough_2k.exr", "teak_veneer_disp_2k.png", scale, color, 0.002)
def asphalt(): return tinted_pbr("asphalt_set", "asphalt_track_diff_2k.jpg", "asphalt_track_rough_2k.exr", "asphalt_track_disp_2k.png", 0.25, (0.5, 0.5, 0.52), 0.004)


def glass_mat():
    def mk():
        m = bpy.data.materials.new("win_glass"); nt = _nodes(m); o = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled")
        nt.links.new(b.outputs[0], o.inputs[0]); b.inputs["Base Color"].default_value = (0.02, 0.03, 0.04, 1); b.inputs["Roughness"].default_value = 0.03
        b.inputs["Specular IOR Level"].default_value = 1.0; b.inputs["Metallic"].default_value = 0.3
        return m
    return cached("glass", mk)


def foliage_mat(key, dark, light, scale=1.3):
    def mk():
        m = bpy.data.materials.new(key); nt = _nodes(m); o = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(b.outputs[0], o.inputs[0])
        tc = nt.nodes.new("ShaderNodeTexCoord"); n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = 6.0
        nt.links.new(tc.outputs["Object"], n.inputs[0])
        cr = nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].color = (*dark, 1); cr.color_ramp.elements[1].color = (*light, 1)
        nt.links.new(n.outputs["Fac"], cr.inputs[0]); nt.links.new(cr.outputs[0], b.inputs["Base Color"])
        n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 28.0; n2.inputs["Detail"].default_value = 4.0; nt.links.new(tc.outputs["Object"], n2.inputs[0])
        bm = nt.nodes.new("ShaderNodeBump"); bm.inputs["Strength"].default_value = 0.8; bm.inputs["Distance"].default_value = 0.08
        nt.links.new(n2.outputs["Fac"], bm.inputs["Height"]); nt.links.new(bm.outputs[0], b.inputs["Normal"])
        b.inputs["Roughness"].default_value = 0.65; b.inputs["Specular IOR Level"].default_value = 0.3
        return m
    return cached(key, mk)


def lawn_mat(shade=1.0):
    def mk():
        m = bpy.data.materials.new(f"lawn_{shade}"); nt = _nodes(m); o = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(b.outputs[0], o.inputs[0])
        tc = nt.nodes.new("ShaderNodeTexCoord")
        n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 0.35; n1.inputs["Detail"].default_value = 6.0
        n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 90.0; n2.inputs["Detail"].default_value = 4.0
        for n in (n1, n2): nt.links.new(tc.outputs["Object"], n.inputs[0])
        mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "FLOAT"; mx.inputs[0].default_value = 0.4; nt.links.new(n1.outputs["Fac"], mx.inputs[2]); nt.links.new(n2.outputs["Fac"], mx.inputs[3])
        cr = nt.nodes.new("ShaderNodeValToRGB"); cr.color_ramp.elements[0].position = 0.3; cr.color_ramp.elements[1].position = 0.7
        cr.color_ramp.elements[0].color = (0.016 * shade, 0.04 * shade, 0.007, 1); cr.color_ramp.elements[1].color = (0.05 * shade, 0.1 * shade, 0.016, 1)
        nt.links.new(mx.outputs[0], cr.inputs[0]); nt.links.new(cr.outputs[0], b.inputs["Base Color"])
        bm = nt.nodes.new("ShaderNodeBump"); bm.inputs["Strength"].default_value = 1.0; bm.inputs["Distance"].default_value = 0.04
        nt.links.new(n2.outputs["Fac"], bm.inputs["Height"]); nt.links.new(bm.outputs[0], b.inputs["Normal"]); b.inputs["Roughness"].default_value = 0.95
        return m
    return cached(f"lawn{shade}", mk)


def awning_mat(c1, c2):
    def mk():
        m = bpy.data.materials.new("awning"); nt = _nodes(m); o = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(b.outputs[0], o.inputs[0])
        tc = nt.nodes.new("ShaderNodeTexCoord"); wv = nt.nodes.new("ShaderNodeTexWave"); wv.wave_type = "BANDS"; wv.bands_direction = "X"; wv.inputs["Scale"].default_value = 2.8
        wv.inputs["Distortion"].default_value = 0.0; nt.links.new(tc.outputs["Object"], wv.inputs[0])
        st = nt.nodes.new("ShaderNodeMapRange"); st.inputs[1].default_value = 0.45; st.inputs[2].default_value = 0.55; nt.links.new(wv.outputs["Fac"], st.inputs[0])
        mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.inputs[6].default_value = (*c1, 1); mx.inputs[7].default_value = (*c2, 1)
        nt.links.new(st.outputs[0], mx.inputs[0]); nt.links.new(mx.outputs[2], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.9
        return m
    return cached("awning", mk)


# ------------------------------------------------------------------------------------------------ geometry helpers
def merged(name, parts, mat, coll, smooth=False):
    """parts: list of (verts[n,3], faces[m,k]) -> one mesh object."""
    V = []; F = []; off = 0
    for v, f in parts:
        V.append(v); F += [[i + off for i in face] for face in f]; off += len(v)
    me = mesh_from_arrays(name, np.vstack(V), F, smooth); me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); link(ob, coll); return ob


def box_part(c, s):
    hx, hy, hz = np.array(s) / 2
    v = np.array([[sx * hx, sy * hy, sz * hz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]) + np.array(c)
    f = [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]]
    return v, f


def rot_z_parts(parts, ang, pivot=(0, 0)):
    c, s = math.cos(ang), math.sin(ang); out = []
    for v, f in parts:
        w = v.copy(); x = v[:, 0] - pivot[0]; y = v[:, 1] - pivot[1]
        w[:, 0] = pivot[0] + x * c - y * s; w[:, 1] = pivot[1] + x * s + y * c; out.append((w, f))
    return out


def inst(coll, base, loc, rot=0.0, sc=1.0):
    ob = bpy.data.objects.new(base.name + "_i", base.data); ob.location = loc; ob.rotation_euler = (0, 0, rot); ob.scale = (sc, sc, sc) if np.isscalar(sc) else sc; link(ob, coll); return ob


def tree_meshes(coll, seed, kind="broad", n=2):
    """Returns list of (trunk_obj, canopy_obj) bases (hidden, instanced by place_tree)."""
    rng = np.random.default_rng(seed); out = []
    bark = mat_matte("bark", (0.07, 0.05, 0.035, 1), 0.9)
    for t in range(n):
        H = rng.uniform(6.5, 9.0) if kind == "broad" else rng.uniform(8, 12)
        parts = []
        blobs = 46 if kind == "broad" else 16
        for b_ in range(blobs):
            if kind == "broad":
                while True:
                    p = rng.uniform(-1, 1, 3)
                    if np.dot(p, p) <= 1: break
                cen = (p[0] * 2.7, p[1] * 2.7, H * 0.62 + p[2] * 2.3 + 0.2); rad = rng.uniform(0.75, 1.3) * (1.1 - 0.3 * abs(p[2]))
            else:   # columnar / cypress-like
                t_ = b_ / (blobs - 1); cz = H * 0.2 + t_ * H * 0.78; rad = (0.95 - 0.7 * t_) + rng.uniform(-0.05, 0.1); cen = (rng.uniform(-0.12, 0.12), rng.uniform(-0.12, 0.12), cz)
            bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=3, radius=rad)
            for v in bm.verts:
                d = np.array(v.co); r = 1.0 + 0.14 * math.sin(d[0] * 5.1 + b_) * math.cos(d[1] * 4.3 + 2 * b_) + 0.10 * math.sin(d[2] * 11.0 + d[0] * 9.0 + b_ * 1.7) * math.cos(d[1] * 10.0 - b_) + 0.05 * math.sin((d[0] + d[1] + d[2]) * 23.0) + rng.uniform(-0.03, 0.03)
                v.co = mathutils.Vector(d * r) + mathutils.Vector(cen)
            bm.verts.ensure_lookup_table()
            V = np.array([list(v.co) for v in bm.verts]); F = [[v.index for v in f.verts] for f in bm.faces]; bm.free()
            parts.append((V, F))
        can = merged(f"tree_canopy_{seed}_{t}", parts, foliage_mat("leaf_a", (0.006, 0.024, 0.005), (0.045, 0.1, 0.016), 1.6), coll, True)
        trunk = cyl(f"tree_trunk_{seed}_{t}", 0.16, H * 0.62, (0, 0, H * 0.31), bark, coll, 10)
        for o in (can, trunk): o.hide_render = True; o.hide_viewport = True
        out.append((trunk, can))
    return out


def place_tree(coll, bases, loc, rot=0.0, sc=1.0, i=None):
    tr, ca = bases[(i if i is not None else int(abs(loc[0] * 7 + loc[1] * 3))) % len(bases)]
    for b in (tr, ca):
        ob = inst(coll, b, loc, rot, sc); ob.hide_render = False; ob.hide_viewport = False


def treeline(coll, bases, rng, r0, r1, n):
    for i in range(n):
        a = rng.uniform(0, 2 * math.pi); r = rng.uniform(r0, r1)
        place_tree(coll, bases, (r * math.cos(a), r * math.sin(a), 0), rng.uniform(0, 6.28), rng.uniform(1.4, 2.4), i)


def hedge(coll, p0, p1, h=1.8, w=0.9, mat=None, key="hedge"):
    p0 = np.array(p0, float); p1 = np.array(p1, float); L = np.linalg.norm(p1 - p0); ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    ob = box(f"{key}_{p0[0]:.1f}_{p0[1]:.1f}", (L, w, h), ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, h / 2), mat or foliage_mat("hedge_m", (0.02, 0.06, 0.015), (0.06, 0.15, 0.03), 2.0), coll, ang, 0.18)
    ob.modifiers["bev"].segments = 4; return ob


def slat_fence(coll, p0, p1, h=1.7, color=(0.55, 0.38, 0.25), key="fence", gap=0.02, board=0.11):
    p0 = np.array(p0, float); p1 = np.array(p1, float); L = np.linalg.norm(p1 - p0); ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    parts = []; n = int(L / (board + gap))
    for i in range(n): parts.append(box_part(((i + 0.5) * (board + gap), 0, h / 2 + 0.05), (board, 0.025, h)))
    for z in (0.25, h - 0.15): parts.append(box_part((L / 2, 0.03, z), (L, 0.04, 0.07)))
    for k in range(int(L / 2.4) + 2): parts.append(box_part((min(k * 2.4, L), 0.0, (h + 0.1) / 2), (0.1, 0.1, h + 0.1)))
    parts = rot_z_parts(parts, ang)
    ob = merged(f"{key}_{p0[0]:.1f}_{p0[1]:.1f}", parts, timber(color, 1.0, f"fence_{color}"), coll); ob.location = (p0[0], p0[1], 0); return ob


def window(coll, wall_ctr, normal_ang, w, h, z0, frame=(0.95, 0.95, 0.93), depth=0.12, muntins=(1, 1), frame_w=0.07, key="win"):
    """Window on a wall whose outward normal points at normal_ang (about z). wall_ctr = (x, y) on the wall plane."""
    fm = mat_matte(f"frame_{frame}", (*frame, 1), 0.5); gm = glass_mat()
    c, s = math.cos(normal_ang), math.sin(normal_ang)
    def P(u, z, d=0.0): return (wall_ctr[0] - s * u + c * d, wall_ctr[1] + c * u + s * d, z)   # u along wall, d out of wall
    k = f"{key}_{wall_ctr[0]:.1f}_{wall_ctr[1]:.1f}_{z0:.1f}"
    box(k + "_g", (0.015, w, h), P(0, z0 + h / 2, 0.02), gm, coll, normal_ang, 0)
    for i, (u, z, sw, sh) in enumerate([(0, z0 + frame_w / 2, w, frame_w), (0, z0 + h - frame_w / 2, w, frame_w), (-w / 2 + frame_w / 2, z0 + h / 2, frame_w, h), (w / 2 - frame_w / 2, z0 + h / 2, frame_w, h)]):
        box(f"{k}_f{i}", (depth, sw, sh), P(u, z, 0.03), fm, coll, normal_ang, 0.004)
    for i in range(1, muntins[0]): box(f"{k}_mv{i}", (depth * 0.6, 0.035, h), P(-w / 2 + w * i / muntins[0], z0 + h / 2, 0.04), fm, coll, normal_ang, 0.002)
    for j in range(1, muntins[1]): box(f"{k}_mh{j}", (depth * 0.6, w, 0.035), P(0, z0 + h * j / muntins[1], 0.04), fm, coll, normal_ang, 0.002)
    box(k + "_sill", (depth * 2.2, w + 0.16, 0.05), P(0, z0 - 0.025, 0.07), fm, coll, normal_ang, 0.004)


def _closed(name, V, F, mat, coll, loc, rot=0.0):
    bm = bmesh.new()
    vs = [bm.verts.new(v) for v in V]
    for f in F: bm.faces.new([vs[i] for i in f])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); ob.location = loc; ob.rotation_euler = (0, 0, rot); link(ob, coll); return ob


def gable_roof(coll, cx, cy, W, D, z0, pitch_deg, over, mat, along="x", key="roof", th=0.22):
    """Closed gable roof over a W(x) by D(y) footprint; eave line z0; ridge along x ('x') or y."""
    if along == "y": W, D = D, W
    rise = (D / 2 + over) * math.tan(math.radians(pitch_deg)); hw = W / 2 + over; hd = D / 2 + over
    V = [[-hw, -hd, z0 - 0.05], [hw, -hd, z0 - 0.05], [hw, 0, z0 - 0.05 + rise], [-hw, 0, z0 - 0.05 + rise], [-hw, hd, z0 - 0.05], [hw, hd, z0 - 0.05]]
    V = V + [[x, y, z - th] for x, y, z in V]
    F = [[0, 1, 2, 3], [3, 2, 5, 4], [0, 3, 4], [1, 5, 2], [6, 9, 8, 7], [9, 10, 11, 8], [6, 10, 9], [7, 8, 11],
         [0, 1, 7, 6], [4, 5, 11, 10], [0, 3, 9, 6], [3, 4, 10, 9], [1, 2, 8, 7], [2, 5, 11, 8]]
    return _closed(key, V, F, mat, coll, (cx, cy, 0), math.pi / 2 if along == "y" else 0.0)


def hip_roof(coll, cx, cy, W, D, z0, pitch_deg, over, mat, key="hip"):
    hw, hd = W / 2 + over, D / 2 + over; rise = min(hw, hd) * math.tan(math.radians(pitch_deg)); rl = max(hw - hd, 0.0) if hw > hd else 0.0
    if hw >= hd:
        V = [[-hw, -hd, z0], [hw, -hd, z0], [hw, hd, z0], [-hw, hd, z0], [-hw + hd, 0, z0 + rise], [hw - hd, 0, z0 + rise]]
        F = [[0, 1, 5, 4], [1, 2, 5], [2, 3, 4, 5], [3, 0, 4]]
    else:
        V = [[-hw, -hd, z0], [hw, -hd, z0], [hw, hd, z0], [-hw, hd, z0], [0, -hd + hw, z0 + rise], [0, hd - hw, z0 + rise]]
        F = [[0, 1, 4], [1, 2, 5, 4], [2, 3, 5], [3, 0, 4, 5]]
    me = mesh_from_arrays(key, np.array(V, float), F, False); me.materials.append(mat)
    ob = bpy.data.objects.new(key, me); ob.location = (cx, cy, 0); link(ob, coll); return ob


def sky_world(sun_elev, sun_rot, strength=0.33, dust=0.7, air=1.5):
    w = bpy.data.worlds.new("sky"); w.use_nodes = True; nt = w.node_tree; nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputWorld"); bg = nt.nodes.new("ShaderNodeBackground"); sk = nt.nodes.new("ShaderNodeTexSky")
    sk.sky_type = "MULTIPLE_SCATTERING"; sk.sun_elevation = math.radians(sun_elev); sk.sun_rotation = math.radians(sun_rot); sk.aerosol_density = dust; sk.air_density = air; sk.sun_size = math.radians(0.55); sk.sun_intensity = 1.0
    bg.inputs["Strength"].default_value = strength
    nt.links.new(sk.outputs[0], bg.inputs[0]); nt.links.new(bg.outputs[0], o.inputs[0]); return w


def ground(coll, mat, size=(400, 400), z=-0.002, name="GROUND"):
    return box(name, (size[0], size[1], 0.2), (0, 0, z - 0.1), mat, coll, 0, 0)


# ================================================================================================ houses (local frame: centre at ground, front facade toward -y)
class Root:
    """Group everything created inside the block under one empty so a whole building can be placed/rotated in the world."""
    def __init__(self, coll, loc, rot_deg=0.0, name="house"):
        self.coll = coll; self.loc = loc; self.rot = math.radians(rot_deg); self.name = name
    def __enter__(self):
        self.before = set(bpy.data.objects); return self
    def __exit__(self, *a):
        new = [o for o in bpy.data.objects if o not in self.before and o.parent is None]
        root = bpy.data.objects.new(self.name + "_root", None); root.location = (self.loc[0], self.loc[1], self.loc[2] if len(self.loc) > 2 else 0.0); root.rotation_euler = (0, 0, self.rot); self.coll.objects.link(root)
        for o in new: o.parent = root


def house_traditional(coll, loc, rot_deg, plaster_col=(0.88, 0.84, 0.74), roof_col=(0.30, 0.13, 0.09), W=10.5, D=8.4, floors=2, pitch=38, frame=(0.96, 0.96, 0.95), shutters=None, key="house"):
    with Root(coll, loc, rot_deg, key):
        Hw = 2.75 * floors + 0.35
        pm = plaster(plaster_col, f"pl_{key}")
        box(f"{key}_wall", (W, D, Hw), (0, 0, Hw / 2 + 0.4), pm, coll, 0, 0.01)
        box(f"{key}_plinth", (W + 0.06, D + 0.06, 0.55), (0, 0, 0.275), paving((0.35, 0.34, 0.33), 0.8, "plinth"), coll, 0, 0.01)
        gable_roof(coll, 0, 0, W, D, Hw + 0.4, pitch, 0.55, roof_tiles(tuple(min(1.0, c * 1.8) for c in roof_col)), "x", key + "_roof")
        for sx in (-1, 1):                                                  # chimney + gutters
            pass
        box(f"{key}_chimney", (0.7, 0.7, 2.0), (W * 0.27, 0.6, Hw + 0.4 + (D / 2 + 0.55) * math.tan(math.radians(pitch)) * 0.7 + 0.6), plaster((0.55, 0.45, 0.4), "chim"), coll, 0, 0.01)
        gut = mat_matte("gutter", (0.05, 0.05, 0.055, 1), 0.4)
        for sy in (-1, 1): box(f"{key}_gut{sy}", (W + 1.2, 0.1, 0.12), (0, sy * (D / 2 + 0.58), Hw + 0.38), gut, coll, 0, 0.01)
        xs = np.linspace(-W / 2 + 1.7, W / 2 - 1.7, 3)
        for f in range(floors):
            z0 = 0.4 + 0.95 + f * 2.75 if f else 0.4 + 0.9
            for i, x in enumerate(xs):
                if f == 0 and i == 1: continue                                         # front door position
                window(coll, (x, -D / 2), -math.pi / 2, 1.25, 1.45, z0, frame, muntins=(2, 2), key=f"{key}_wf{f}{i}")
                if shutters:
                    for sx in (-1, 1): box(f"{key}_sh{f}{i}{sx}", (0.04, 0.45, 1.45), (x + sx * 0.85, -D / 2 - 0.05, z0 + 0.72), mat_matte("shutter", (*shutters, 1), 0.7), coll, 0, 0.004)
            for sd in (-1, 1):
                for y in (-D / 4, D / 4): window(coll, (sd * W / 2, y), 0.0 if sd > 0 else math.pi, 1.2, 1.4, z0, frame, muntins=(2, 2), key=f"{key}_ws{f}{sd}{y:.0f}")
        if floors > 1: window(coll, (xs[1], -D / 2), -math.pi / 2, 1.6, 1.8, 0.4 + 0.95 + 2.75 - 0.35, frame, muntins=(3, 2), key=key + "_balc")
        # entrance: door, canopy, steps
        box(f"{key}_door", (0.08, 1.05, 2.15), (xs[1], -D / 2 - 0.02, 0.4 + 1.08), timber((0.45, 0.28, 0.17), 1.0, "door"), coll, -math.pi / 2, 0.01)
        box(f"{key}_door_f", (0.14, 1.25, 2.3), (xs[1], -D / 2 - 0.0, 0.4 + 1.15), mat_matte("doorframe", (0.95, 0.95, 0.94, 1), 0.5), coll, -math.pi / 2, 0.01)
        box(f"{key}_canopy", (2.3, 1.2, 0.12), (xs[1], -D / 2 - 0.6, 0.4 + 2.55), mat_matte("canopy", (0.07, 0.07, 0.08, 1), 0.5), coll, 0, 0.01)
        for k in range(3): box(f"{key}_step{k}", (1.8, 0.35, 0.16), (xs[1], -D / 2 - 0.2 - k * 0.32, 0.4 - 0.08 * (k + 1) + 0.0), paving((0.5, 0.5, 0.5), 0.8, "steps"), coll, 0, 0.005)
    return Hw


def house_modern(coll, loc, rot_deg, key="villa", cladding=(0.55, 0.40, 0.28), plaster_col=(0.9, 0.9, 0.88), glass_wide=True, garage=True):
    with Root(coll, loc, rot_deg, key):
        pm = plaster(plaster_col, f"pl_{key}"); tm = timber(cladding, 1.0, f"clad_{key}"); dk = mat_matte("anthracite", (0.035, 0.037, 0.04, 1), 0.45)
        W, D, H1, H2 = 12.0, 9.0, 3.1, 2.95
        box(f"{key}_gf", (W, D, H1), (0, 0, H1 / 2), pm, coll, 0, 0.01)
        box(f"{key}_gf_roof", (W + 0.8, D + 0.8, 0.35), (0, 0, H1 + 0.175), dk, coll, 0, 0.01)
        box(f"{key}_uf", (7.6, 7.2, H2), (2.0, 0.3, H1 + 0.35 + H2 / 2), tm, coll, 0, 0.01)
        box(f"{key}_uf_roof", (8.4, 8.0, 0.35), (2.0, 0.3, H1 + 0.35 + H2 + 0.175), dk, coll, 0, 0.01)
        # upper-floor ribbon window + ground-floor wide glazing
        window(coll, (2.0, 0.3 - 3.6), -math.pi / 2, 5.4, 1.5, H1 + 0.35 + 0.9, (0.04, 0.04, 0.045), muntins=(3, 1), frame_w=0.06, key=key + "_uw")
        window(coll, (3.2, -D / 2), -math.pi / 2, 4.4, 2.4, 0.35, (0.04, 0.04, 0.045), muntins=(3, 1), frame_w=0.06, key=key + "_lw")
        # entrance door + stone accent wall
        box(f"{key}_stone", (3.2, 0.25, H1), (-4.1, -D / 2 - 0.1, H1 / 2), paving((0.45, 0.43, 0.4), 0.7, "villa_stone"), coll, 0, 0.01)
        box(f"{key}_door", (1.15, 0.1, 2.35), (-2.0, -D / 2 - 0.03, 1.2), tm, coll, 0, 0.008)
        box(f"{key}_door_h", (0.03, 0.04, 1.0), (-1.55, -D / 2 - 0.1, 1.15), mat_matte("steelh", (0.7, 0.7, 0.72, 1), 0.25), coll, 0, 0.002)
        if garage:   # sectional garage door (4.6 x 2.3) with panel lines, in an anthracite surround
            gx = -4.3
            box(f"{key}_gar_f", (5.0, 0.12, 2.6), (gx, -D / 2 - 0.02, 1.3), dk, coll, 0, 0.01) if False else None
            box(f"{key}_gar", (4.6, 0.1, 2.3), (-4.3 + 0.0, -D / 2 - 0.05, 1.15), mat_matte("garage_door", (0.78, 0.78, 0.76, 1), 0.45), coll, 0, 0.01) if False else None
    return None


def garage_front(coll, loc, rot_deg, key="garage"):
    """Standalone anthracite sectional garage door with panel grooves, centred at loc on a wall facing -y (rot about z)."""
    with Root(coll, loc, rot_deg, key):
        dk = mat_matte("anthracite", (0.035, 0.037, 0.04, 1), 0.45); pn = mat_matte("garage_panel", (0.2, 0.21, 0.22, 1), 0.4)
        box(f"{key}_fr", (5.1, 0.14, 2.6), (0, 0, 1.3), dk, coll, 0, 0.01)
        box(f"{key}_leaf", (4.7, 0.08, 2.3), (0, -0.05, 1.15), pn, coll, 0, 0.01)
        for k in range(1, 5): box(f"{key}_g{k}", (4.7, 0.09, 0.025), (0, -0.07, k * 0.46), dk, coll, 0, 0)


def townhouse(coll, loc, rot_deg, W, D, floors, plaster_col, roof_col, key, ground_h=4.1, shop=True, shutter_col=None, awning=None, roof_pitch=34):
    with Root(coll, loc, rot_deg, key):
        up = 3.15; H = ground_h + up * (floors - 1) + 0.3
        pm = plaster(plaster_col, f"pl_{key}")
        box(f"{key}_wall", (W, D, H), (0, 0, H / 2), pm, coll, 0, 0.01)
        gable_roof(coll, 0, 0, W, D, H, roof_pitch, 0.35, roof_tiles(tuple(min(1.0, c * 1.8) for c in roof_col)), "x", key + "_roof")
        cor = mat_matte("cornice", (0.9, 0.88, 0.82, 1), 0.7)
        box(f"{key}_cornice", (W + 0.3, 0.45, 0.28), (0, -D / 2 - 0.1, H - 0.14), cor, coll, 0, 0.01)
        box(f"{key}_band", (W + 0.12, 0.2, 0.18), (0, -D / 2 - 0.05, ground_h), cor, coll, 0, 0.01)
        for f in range(1, floors):
            z0 = ground_h + (f - 1) * up + 0.55
            for i, x in enumerate((-W * 0.27, W * 0.27)):
                window(coll, (x, -D / 2), -math.pi / 2, 1.15, 1.7, z0, (0.97, 0.97, 0.96), muntins=(2, 3), key=f"{key}_w{f}{i}")
                if shutter_col:
                    for sx in (-1, 1): box(f"{key}_sh{f}{i}{sx}", (0.05, 0.5, 1.7), (x + sx * 0.82, -D / 2 - 0.05, z0 + 0.85), mat_matte(f"sh_{shutter_col}", (*shutter_col, 1), 0.7), coll, 0, 0.004)
        if shop:
            dkf = (0.05, 0.05, 0.055)
            window(coll, (-W * 0.12, -D / 2), -math.pi / 2, W * 0.58, 2.7, 0.35, dkf, muntins=(4, 1), frame_w=0.08, key=key + "_shop")
            box(f"{key}_door", (0.07, 1.1, 2.3), (W * 0.33, -D / 2 - 0.03, 1.2), mat_matte("shopdoor", (0.05, 0.05, 0.055, 1), 0.4), coll, -math.pi / 2, 0.01)
            if awning:
                am = awning_mat(*awning)
                ob = box(f"{key}_awning", (W * 0.8, 1.7, 0.06), (0, -D / 2 - 0.85, 3.25), am, coll, 0, 0.01); ob.rotation_euler = (math.radians(14), 0, 0)
                box(f"{key}_awn_valance", (W * 0.8, 0.05, 0.3), (0, -D / 2 - 1.66, 3.0), am, coll, 0, 0.01)
        else:
            window(coll, (-W * 0.27, -D / 2), -math.pi / 2, 1.15, 1.7, 0.95, (0.97, 0.97, 0.96), muntins=(2, 3), key=key + "_gw")
            box(f"{key}_door", (0.08, 1.1, 2.3), (W * 0.2, -D / 2 - 0.03, 1.2), timber((0.4, 0.25, 0.16), 1.0, "tdoor"), coll, -math.pi / 2, 0.01)
    return H


# ================================================================================================ the five set-ups
def _horizon(coll, seed, n=70, r0=55, r1=95, kind="broad"):
    rng = np.random.default_rng(seed); bases = tree_meshes(coll, seed, kind, 3)
    treeline(coll, bases, rng, r0, r1, n); return bases


def _pad(coll, name, size, loc, mat, top=0.0):
    return box(name, (size[0], size[1], 0.2), (loc[0], loc[1], top - 0.1), mat, coll, 0, 0.0)


def set_carport(coll):
    ground(coll, lawn_mat(1.0))
    _horizon(coll, 11)
    _pad(coll, "driveway", (9.0, 30.0), (0, -4.5), paving((0.42, 0.42, 0.44), 0.55, "drive"), 0.0)
    _pad(coll, "road", (240, 9.0), (0, -27), asphalt(), -0.05); _pad(coll, "pavement", (240, 2.4), (0, -21.2), paving((0.62, 0.6, 0.57), 0.6, "pave"), 0.0)
    box("curb", (240, 0.18, 0.15), (0, -22.5, -0.03), paving((0.7, 0.7, 0.7), 0.8, "curb"), coll, 0, 0.01)
    house_modern(coll, (4.3, 14.0), 0, "villa")
    garage_front(coll, (0.0, 9.43), 0, "garage")
    hedge(coll, (-5.8, -14), (-5.8, 9.4), 1.9, 1.0); hedge(coll, (-5.8, 9.4), (-9, 9.4), 1.9, 1.0)
    slat_fence(coll, (8.0, -14), (8.0, 9.3), 1.8, (0.62, 0.45, 0.3), "fenceR")
    bases = tree_meshes(coll, 21, "broad", 2)
    for p, s in (((-8.5, 4.5), 0.95), ((-9.5, -7.5), 0.8), ((11.5, 2.0), 0.9), ((-3, 22), 1.0), ((18, 12), 1.1), ((-14, 16), 1.2)): place_tree(coll, bases, (p[0], p[1], 0), p[0], s)
    for p in ((-4, -26.5), (12, -17.7)): place_tree(coll, bases, (p[0], p[1], 0), 1.0, 0.7)
    # street lamp
    cyl("lamp_pole", 0.07, 6.0, (-12, -20.6, 3.0), mat_matte("pole", (0.1, 0.1, 0.11, 1), 0.4), coll, 12)
    box("lamp_arm", (1.2, 0.06, 0.06), (-11.4, -20.6, 6.0), mat_matte("pole", (0.1, 0.1, 0.11, 1), 0.4), coll, 0, 0.0)
    return dict(world=sky_world(24, 150, dust=0.8), exp=-0.1, car=True)


def set_barbecue(coll):
    ground(coll, lawn_mat(1.05))
    _horizon(coll, 12)
    _pad(coll, "patio", (5.2, 8.0), (0, 0), paving((0.5, 0.48, 0.45), 0.6, "patio"), 0.0)
    _pad(coll, "walk", (1.4, 8.0), (0.0, 7.0 + 0.0), paving((0.5, 0.48, 0.45), 0.6, "patio"), 0.0)
    house_traditional(coll, (0.0, 14.5), 0, (0.93, 0.9, 0.84), (0.22, 0.2, 0.21), 10.5, 8.4, 2, 40, key="farm")
    slat_fence(coll, (-9.5, -14), (-9.5, 10.0), 1.75, (0.5, 0.36, 0.24), "fL"); slat_fence(coll, (9.5, -14), (9.5, 10.0), 1.75, (0.5, 0.36, 0.24), "fR")
    hedge(coll, (-9.5, 10.0), (-5.2, 10.0), 1.8, 0.9)
    bases = tree_meshes(coll, 22, "broad", 3)
    for p, s in (((-6.5, 5.5), 0.6), ((6.8, 3.0), 0.62), ((-7.0, -4.5), 0.55), ((12.5, 8), 1.1), ((-13, 6), 1.15), ((0, 25), 1.2)): place_tree(coll, bases, (p[0], p[1], 0), p[0] * 2.0, s)
    # raised vegetable beds + shed
    for k in range(3):
        box(f"bed{k}", (2.2, 0.9, 0.38), (-6.2 + k * 0.0, -9.5 + k * 1.3 - 0.0, 0.19), timber((0.5, 0.35, 0.22), 1.0, "bedw"), coll, 0, 0.01)
        box(f"soil{k}", (2.1, 0.8, 0.02), (-6.2, -9.5 + k * 1.3, 0.37), mat_matte("soil", (0.025, 0.018, 0.012, 1), 1.0), coll, 0, 0)
    box("shed", (3.0, 2.4, 2.2), (-7.2, 7.5, 1.1), timber((0.4, 0.32, 0.25), 0.8, "shedw"), coll, 0, 0.01)
    gable_roof(coll, -7.2, 7.5, 3.0, 2.4, 2.2, 20, 0.25, mat_matte("shedroof", (0.06, 0.06, 0.065, 1), 0.6), "x", "shed_roof")
    return dict(world=sky_world(38, 215), exp=-0.05, car=False)


def set_kitchen(coll):
    ground(coll, lawn_mat(0.95))
    _horizon(coll, 13, 60)
    _pad(coll, "terrace", (13.0, 9.0), (3.2, 0.0), paving((0.6, 0.53, 0.42), 0.7, "limestone"), 0.0)
    house_traditional(coll, (13.8, 0.0), -90, (0.95, 0.88, 0.72), (0.52, 0.22, 0.13), 10.5, 8.4, 2, 30, shutters=(0.1, 0.3, 0.22), key="stucco")
    # low stone wall + lavender planters + cypresses (Mediterranean mood)
    box("wall_low", (0.4, 9.0, 0.7), (-3.9, 4.0, 0.35), paving((0.6, 0.55, 0.48), 0.8, "stonewall"), coll, 0, 0.02)
    lav = foliage_mat("lavender", (0.05, 0.07, 0.07), (0.15, 0.13, 0.25), 3.0)
    for i in range(7): box(f"lav{i}", (0.7, 0.7, 0.5), (-2.8 + 0.0, -3.2 - 0.0 + i * 0.0, 0.25), lav, coll, 0, 0.2) if False else None
    for k in range(6): box(f"lavbed{k}", (0.9, 0.9, 0.55), (4.5 + k * 1.0, -4.6, 0.28), lav, coll, 0, 0.25)
    cyp = tree_meshes(coll, 31, "columnar", 3)
    for p, s in (((9.0, 5.4), 0.75), ((9.0, -5.4), 0.7), ((-8.5, 3.0), 0.6)): place_tree(coll, cyp, (p[0], p[1], 0), p[0], s)
    bases = tree_meshes(coll, 32, "broad", 2)
    for p, s in (((-9, -6), 0.75), ((-6.5, 9.0), 0.8), ((12, 14), 1.1), ((10, -15), 1.1), ((-15, 0), 1.3)): place_tree(coll, bases, (p[0], p[1], 0), p[0], s)
    slat_fence(coll, (-12, -10), (-12, 12), 1.8, (0.55, 0.42, 0.3), "fK")
    return dict(world=sky_world(52, 20), exp=-0.1, car=False)


def set_lounge(coll):
    ground(coll, lawn_mat(1.1))
    _horizon(coll, 14, 60)
    teak = timber((0.62, 0.46, 0.32), 1.1, "deck")
    # deck around a rectangular pool (x -3.5..3.5, y 7..16)
    for nme, size, loc in (("d_a", (24, 18.0, 0.2), (0, -3.0 - 0.0, -0.1)), ("d_b", (8.5, 3.0, 0.2), (-7.75, 8.5, -0.1)), ("d_c", (8.5, 3.0, 0.2), (7.75, 8.5, -0.1)), ("d_d", (24, 5.0, 0.2), (0, 18.5, -0.1))):
        pass
    _pad(coll, "deck_front", (22, 16.0), (0, -1.0), teak, 0.0)             # y -9 .. 7
    _pad(coll, "deck_left", (7.5, 9.0), (-7.25, 11.5), teak, 0.0); _pad(coll, "deck_right", (7.5, 9.0), (7.25, 11.5), teak, 0.0); _pad(coll, "deck_back", (22, 5.0), (0, 18.5), teak, 0.0)
    tile = mat_matte("pool_tile", (0.28, 0.5, 0.58, 1), 0.3)
    box("pool_floor", (7.0, 9.0, 0.1), (0, 11.5, -1.4), tile, coll, 0, 0)
    for nme, size, loc in (("pw1", (0.1, 9.0, 1.4), (-3.5, 11.5, -0.7)), ("pw2", (0.1, 9.0, 1.4), (3.5, 11.5, -0.7)), ("pw3", (7.0, 0.1, 1.4), (0, 7.0, -0.7)), ("pw4", (7.0, 0.1, 1.4), (0, 16.0, -0.7))): box(nme, size, loc, tile, coll, 0, 0)
    def water():
        m = bpy.data.materials.new("pool_water"); nt = _nodes(m); o = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(b.outputs[0], o.inputs[0])
        b.inputs["Base Color"].default_value = (0.35, 0.8, 0.9, 1); b.inputs["Roughness"].default_value = 0.02; b.inputs["Transmission Weight"].default_value = 0.92; b.inputs["IOR"].default_value = 1.33
        tc = nt.nodes.new("ShaderNodeTexCoord"); n = nt.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = 3.0; n.inputs["Detail"].default_value = 3.0; nt.links.new(tc.outputs["Object"], n.inputs[0])
        bm = nt.nodes.new("ShaderNodeBump"); bm.inputs["Strength"].default_value = 0.06; bm.inputs["Distance"].default_value = 0.02; nt.links.new(n.outputs["Fac"], bm.inputs["Height"]); nt.links.new(bm.outputs[0], b.inputs["Normal"])
        return m
    box("pool_water", (6.9, 8.9, 0.02), (0, 11.5, -0.12), cached("water", water), coll, 0, 0)
    for nme, size, loc in (("cp1", (0.45, 9.9, 0.06), (-3.72, 11.5, 0.03)), ("cp2", (0.45, 9.9, 0.06), (3.72, 11.5, 0.03)), ("cp3", (7.9, 0.45, 0.06), (0, 6.78, 0.03)), ("cp4", (7.9, 0.45, 0.06), (0, 16.22, 0.03))): box(nme, size, loc, mat_matte("coping", (0.85, 0.85, 0.83, 1), 0.5), coll, 0, 0.01)
    house_modern(coll, (0.0, 21.5), 0, "villa2", cladding=(0.22, 0.17, 0.13), plaster_col=(0.28, 0.28, 0.29), garage=False)
    bases = tree_meshes(coll, 41, "broad", 3)
    for p, s in (((-10.5, 4.0), 0.8), ((10.5, 8.0), 0.85), ((-12, 14), 0.9), ((13, 17), 1.0), ((-4, 30), 1.4), ((10, 28), 1.4)): place_tree(coll, bases, (p[0], p[1], 0), p[0], s)
    gr = foliage_mat("grass_orn", (0.12, 0.1, 0.04), (0.45, 0.4, 0.2), 4.0)
    for k, x in enumerate(np.linspace(-9.5, 9.5, 9)):
        sphere(f"orn{k}", 0.55, (x, 4.3 + 0.0, 0.35), gr, coll, 14, (1, 1, 0.7))
    return dict(world=sky_world(11, 330, dust=1.4, air=1.3), exp=0.0, car=False)


def set_cafe(coll):
    ground(coll, paving((0.34, 0.33, 0.31), 0.6, "cityfloor"))
    _horizon(coll, 15, 40, 60, 100)
    cob = paving((0.42, 0.4, 0.38), 0.7, "terrace_pav")
    _pad(coll, "terrace", (30, 15.5), (0, 0.0), cob, 0.0)
    _pad(coll, "road", (240, 9.0), (0, -17.0), asphalt(), -0.05); box("curb2", (240, 0.18, 0.15), (0, -12.4, -0.03), paving((0.7, 0.7, 0.7), 0.8, "curb"), coll, 0, 0.01)
    blds = [(-6.8, 6.0, 3, (0.78, 0.56, 0.42), (0.28, 0.14, 0.1), None, (0.15, 0.3, 0.2), False),
            (0.0, 7.0, 3, (0.92, 0.88, 0.76), (0.45, 0.2, 0.14), (( 0.1, 0.35, 0.28), (0.95, 0.95, 0.92)), None, True),
            (6.9, 6.2, 4, (0.62, 0.72, 0.78), (0.3, 0.15, 0.11), None, None, False),
            (-13.4, 6.4, 3, (0.9, 0.78, 0.55), (0.28, 0.14, 0.1), None, (0.4, 0.15, 0.12), False),
            (13.4, 6.3, 3, (0.78, 0.5, 0.45), (0.5, 0.25, 0.18), None, None, False)]
    for i, (x, w, fl, pc, rc, aw, sh, shop) in enumerate(blds):
        townhouse(coll, (x, 13.0), 0, w, 11.0, fl, pc, rc, f"th{i}", 4.1, shop or i in (2, 4), sh, aw)
    # terrace edge: boxwood hedges in planters + two parasols + street trees
    for k, x in enumerate(np.linspace(-11, 11, 8)):
        box(f"pl{k}", (1.4, 0.6, 0.45), (x, -6.8, 0.225), mat_matte("planter_c", (0.17, 0.17, 0.18, 1), 0.7), coll, 0, 0.02)
        box(f"bx{k}", (1.3, 0.5, 0.7), (x, -6.8, 0.75), foliage_mat("boxwood", (0.02, 0.07, 0.02), (0.07, 0.17, 0.04), 2.5), coll, 0, 0.15)
    for x in (-8.0, 8.0):
        cyl(f"parasol_pole{x}", 0.03, 2.4, (x, -2.0, 1.2), mat_matte("pole", (0.1, 0.1, 0.11, 1), 0.4), coll, 8)
        c = cyl(f"parasol{x}", 1.4, 0.34, (x, -2.0, 2.45), awning_mat((0.9, 0.85, 0.7), (0.78, 0.3, 0.2)), coll, 24)
        for k in range(2): box(f"pt{x}{k}", (0.9, 0.9, 0.04), (x - 0.0, -2.0 + (k * 1.1 - 0.55) * 1.0, 0.76), E.M("teak"), coll, 0, 0.01)
    bases = tree_meshes(coll, 51, "broad", 2)
    for p, s in (((-10.5, -10.8), 0.55), ((10.5, -10.8), 0.55), ((20, -4), 0.9), ((-22, 2), 0.95)): place_tree(coll, bases, (p[0], p[1], 0), p[0], s)
    return dict(world=sky_world(46, 200), exp=-0.05, car=False)


SETS = {"carport": set_carport, "barbecue": set_barbecue, "kitchen": set_kitchen, "lounge": set_lounge, "commercial": set_cafe}
