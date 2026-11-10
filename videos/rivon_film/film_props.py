"""Furniture / outdoor-living props for the RIVON film sets, built as merged meshes (one object per material per prop group).
All coordinates are metres.  A group is built in a LOCAL frame (+y = 'front' of the piece) and then placed with loc/rot."""
import math
import numpy as np
import bpy, bmesh
from film_lib import mesh_from_arrays, link, simple, pbr
import film_envs as E

_MC = {}
def MAT(name):
    if name in _MC and name in bpy.data.materials: return _MC[name]
    S = simple
    tbl = {
        "teak": lambda: E.M("teak"), "oak": lambda: E.M("oak"), "steel": lambda: E.M("steel"), "blacksteel": lambda: E.M("blacksteel"),
        "graphite": lambda: E.M("graphite"), "ceramic": lambda: E.M("ceramic"), "stone_dark": lambda: E.M("stone_dark"), "leaf": lambda: E.M("leaf"),
        "wire": lambda: E.M("wire"), "bulb": lambda: E.M("bulb"),
        "white": lambda: S("p_white", (0.78, 0.78, 0.76, 1), 0.35),
        "cream": lambda: S("p_cream", (0.66, 0.6, 0.5, 1), 0.95, 0.0, 0.15),
        "grey": lambda: S("p_grey", (0.2, 0.21, 0.22, 1), 0.95, 0.0, 0.15),
        "lgrey": lambda: S("p_lgrey", (0.42, 0.43, 0.43, 1), 0.9, 0.0, 0.2),
        "terra": lambda: S("p_terra", (0.5, 0.17, 0.08, 1), 0.9, 0.0, 0.2),
        "teal": lambda: S("p_teal", (0.06, 0.28, 0.3, 1), 0.9, 0.0, 0.2),
        "mustard": lambda: S("p_mustard", (0.72, 0.46, 0.06, 1), 0.9, 0.0, 0.2),
        "olive": lambda: S("p_olive", (0.2, 0.26, 0.08, 1), 0.9, 0.0, 0.2),
        "red": lambda: S("p_red", (0.55, 0.05, 0.04, 1), 0.5, 0.0, 0.4),
        "wicker": lambda: S("p_wicker", (0.32, 0.2, 0.1, 1), 0.7, 0.0, 0.3),
        "charcoal": lambda: S("p_charcoal", (0.012, 0.012, 0.012, 1), 0.8),
        "brick": lambda: S("p_brick", (0.4, 0.13, 0.07, 1), 0.85, 0.0, 0.2),
        "cream_brick": lambda: S("p_cbrick", (0.72, 0.6, 0.45, 1), 0.85, 0.0, 0.2),
        "bglass": lambda: S("p_bglass", (0.02, 0.1, 0.03, 1), 0.08, 0.0, 0.8),
        "coal": lambda: S("p_coal", (0.02, 0.01, 0.008, 1), 0.7, 0.0, 0.3, emission=((1.0, 0.25, 0.04, 1), 3.0)),
        "flame": lambda: S("p_flame", (1, 0.4, 0.05, 1), 0.5, 0.0, 0.0, emission=((1.0, 0.42, 0.07, 1), 9.0)),
        "meat": lambda: S("p_meat", (0.22, 0.07, 0.03, 1), 0.7),
        "bread": lambda: S("p_bread", (0.55, 0.32, 0.12, 1), 0.7),
        "lemon": lambda: S("p_lemon", (0.8, 0.65, 0.03, 1), 0.5),
        "coffee": lambda: S("p_coffee", (0.05, 0.025, 0.012, 1), 0.2),
        "wood_light": lambda: S("p_wlight", (0.5, 0.36, 0.22, 1), 0.65, 0.0, 0.3),
        "wood_white": lambda: S("p_wwhite", (0.62, 0.6, 0.55, 1), 0.7, 0.0, 0.3),
        "ball": lambda: S("p_ball", (0.75, 0.7, 0.2, 1), 0.5),
        "net": lambda: S("p_net", (0.03, 0.03, 0.03, 1), 0.8),
        "gravel": lambda: S("p_gravel", (0.45, 0.4, 0.33, 1), 0.95),
        "rubber": lambda: S("p_rubber", (0.02, 0.02, 0.02, 1), 0.9),
        "blue": lambda: S("p_blue", (0.06, 0.15, 0.42, 1), 0.6, 0.0, 0.3),
        "pink": lambda: S("p_pink", (0.62, 0.1, 0.25, 1), 0.6, 0.0, 0.2),
        "yellow": lambda: S("p_yellow", (0.8, 0.55, 0.02, 1), 0.6, 0.0, 0.2),
        "bloom": lambda: S("p_bloom", (0.75, 0.74, 0.7, 1), 0.6, 0.0, 0.2),
        "violet": lambda: S("p_violet", (0.25, 0.1, 0.5, 1), 0.6, 0.0, 0.2),
        "skin1": lambda: S("p_skin1", (0.5, 0.33, 0.25, 1), 0.55, 0.0, 0.3),
        "skin2": lambda: S("p_skin2", (0.32, 0.2, 0.14, 1), 0.55, 0.0, 0.3),
        "hair_dk": lambda: S("p_hairdk", (0.02, 0.015, 0.012, 1), 0.6),
        "hair_br": lambda: S("p_hairbr", (0.12, 0.06, 0.025, 1), 0.6),
        "hair_bl": lambda: S("p_hairbl", (0.45, 0.33, 0.12, 1), 0.6),
        "denim": lambda: S("p_denim", (0.05, 0.1, 0.22, 1), 0.85),
        "lantern": lambda: S("p_lantern", (1, 0.8, 0.5, 1), 0.3, 0.0, 0.5, emission=((1, 0.7, 0.35, 1), 5.0)),
    }
    _MC[name] = tbl[name](); return _MC[name]


def _foliage(key="foliage_p", dark=(0.02, 0.08, 0.015), light=(0.1, 0.24, 0.04)):
    import film_sets as FS
    return FS.foliage_mat(key, dark, light, 4.0)


# ------------------------------------------------------------------------------------------------ part builders
def box_p(c, s, rz=0.0, rx=0.0):
    hx, hy, hz = np.array(s) / 2
    v = np.array([[sx * hx, sy * hy, sz * hz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)], float)
    f = [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]]
    if rx:
        cx, sx_ = math.cos(rx), math.sin(rx); y = v[:, 1] * cx - v[:, 2] * sx_; z = v[:, 1] * sx_ + v[:, 2] * cx; v[:, 1] = y; v[:, 2] = z
    if rz:
        c_, s_ = math.cos(rz), math.sin(rz); x = v[:, 0] * c_ - v[:, 1] * s_; y = v[:, 0] * s_ + v[:, 1] * c_; v[:, 0] = x; v[:, 1] = y
    return v + np.array(c, float), f


def cyl_p(c, r, h, seg=20, r2=None, axis="z"):
    r2 = r if r2 is None else r2
    ang = np.linspace(0, 2 * math.pi, seg, endpoint=False)
    bot = np.stack([r * np.cos(ang), r * np.sin(ang), -np.full(seg, h / 2)], 1); top = np.stack([r2 * np.cos(ang), r2 * np.sin(ang), np.full(seg, h / 2)], 1)
    v = np.vstack([bot, top, [[0, 0, -h / 2], [0, 0, h / 2]]]).astype(float)
    f = [[i, (i + 1) % seg, seg + (i + 1) % seg, seg + i] for i in range(seg)] + [[(i + 1) % seg, i, 2 * seg] for i in range(seg)] + [[seg + i, seg + (i + 1) % seg, 2 * seg + 1] for i in range(seg)]
    if axis == "x": v = v[:, [2, 0, 1]]
    elif axis == "y": v = v[:, [0, 2, 1]]
    return v + np.array(c, float), f


def ell_p(c, r, scale=(1, 1, 1), seg=14, rings=8, zmin=-1.0):
    lat = np.linspace(-math.pi / 2 * (-zmin if zmin > -1 else 1) * 1.0 if False else -math.pi / 2, math.pi / 2, rings + 1)
    if zmin > -1: lat = np.linspace(math.asin(zmin), math.pi / 2, rings + 1)
    lon = np.linspace(0, 2 * math.pi, seg, endpoint=False); V = []; F = []
    for a in lat:
        for b in lon: V.append([math.cos(a) * math.cos(b) * scale[0], math.cos(a) * math.sin(b) * scale[1], math.sin(a) * scale[2]])
    V = np.array(V) * r
    for i in range(rings):
        for j in range(seg): F.append([i * seg + j, i * seg + (j + 1) % seg, (i + 1) * seg + (j + 1) % seg, (i + 1) * seg + j])
    return V + np.array(c, float), F


def blob_p(c, r, seed=0, sc=(1, 1, 1), n=0.35):
    rng = np.random.default_rng(abs(int(seed))); bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=3, radius=r)
    v = np.array([vv.co[:] for vv in bm.verts]); f = [[l.vert.index for l in fc.loops] for fc in bm.faces]; bm.free()
    k = rng.uniform(1 - n, 1 + n, len(v)); v = v * k[:, None] * np.array(sc)
    return v + np.array(c, float), f


class G:
    """Collects parts per material, then flushes into merged objects placed at loc / rot_z (local +y = front)."""
    def __init__(self, coll, name, loc=(0, 0, 0), rot=0.0, bevel=0.005):
        self.coll, self.name, self.loc, self.rot, self.bevel = coll, name, np.array(loc, float), rot, bevel; self.parts = {}
    def add(self, part, mat, smooth=False):
        self.parts.setdefault((mat, smooth), []).append(part); return self
    def box(self, c, s, mat, rz=0.0, rx=0.0): return self.add(box_p(c, s, rz, rx), mat)
    def cyl(self, c, r, h, mat, seg=20, r2=None, axis="z"): return self.add(cyl_p(c, r, h, seg, r2, axis), mat, True)
    def ell(self, c, r, mat, scale=(1, 1, 1), seg=14, rings=8, zmin=-1.0): return self.add(ell_p(c, r, scale, seg, rings, zmin), mat, True)
    def blob(self, c, r, mat, seed=0, sc=(1, 1, 1), n=0.35): return self.add(blob_p(c, r, seed, sc, n), mat, True)
    def flush(self):
        c, s = math.cos(self.rot), math.sin(self.rot); out = []
        for (mat, smooth), parts in self.parts.items():
            V = []; F = []; off = 0
            for v, f in parts:
                V.append(v); F += [[i + off for i in fc] for fc in f]; off += len(v)
            V = np.vstack(V); W = V.copy(); W[:, 0] = V[:, 0] * c - V[:, 1] * s; W[:, 1] = V[:, 0] * s + V[:, 1] * c; W += self.loc
            nm = f"{self.name}_{mat if isinstance(mat, str) else mat.name}"
            me = mesh_from_arrays(nm, W, F, smooth); me.materials.append(MAT(mat) if isinstance(mat, str) else mat)
            ob = bpy.data.objects.new(nm, me)
            if self.bevel and not smooth:
                bv = ob.modifiers.new("bev", "BEVEL"); bv.width = self.bevel; bv.segments = 2; bv.limit_method = "ANGLE"
            link(ob, self.coll); out.append(ob)
        return out


# ------------------------------------------------------------------------------------------------ furniture (local +y = front)
def dining_chair(g, x, y, rot, mat="wood_light", frame="blacksteel"):
    """Chair at (x,y) in g's local frame, sitter faces direction rot (radians, 0 = +y)."""
    c, s = math.cos(rot), math.sin(rot)
    def P(lx, ly, z): return (x + lx * c - ly * s, y + lx * s + ly * c, z)
    g.box(P(0, 0, 0.45), (0.46, 0.46, 0.04), mat, rz=rot)
    for lx in (-0.2, 0.2):
        for ly in (-0.2, 0.2): g.box(P(lx, ly, 0.215), (0.035, 0.035, 0.43), frame, rz=rot)
    for lx in (-0.2, 0.2): g.box(P(lx, -0.215, 0.69), (0.035, 0.03, 0.48), frame, rz=rot, rx=0.0)
    for k, z in enumerate((0.60, 0.70, 0.80)): g.box(P(0, -0.215, z), (0.44, 0.022, 0.07), mat, rz=rot)


def trestle_table(g, x, y, L, W, h=0.76, along="y", top="teak", leg="blacksteel"):
    sx, sy = (W, L) if along == "y" else (L, W)
    g.box((x, y, h - 0.025), (sx, sy, 0.05), top)
    g.box((x, y, h - 0.07), (sx - 0.12, sy - 0.12, 0.05), leg)
    for k in (-1, 1):
        if along == "y": g.box((x, y + k * (L / 2 - 0.35), (h - 0.05) / 2), (W - 0.2, 0.06, h - 0.05), leg)
        else: g.box((x + k * (L / 2 - 0.35), y, (h - 0.05) / 2), (0.06, W - 0.2, h - 0.05), leg)


def bench(g, x, y, L, along="y", h=0.46, mat="teak"):
    sx, sy = (0.36, L) if along == "y" else (L, 0.36)
    g.box((x, y, h - 0.02), (sx, sy, 0.04), mat)
    for k in (-1, 1):
        if along == "y": g.box((x, y + k * (L / 2 - 0.2), (h - 0.04) / 2), (0.30, 0.05, h - 0.04), "blacksteel")
        else: g.box((x + k * (L / 2 - 0.2), y, (h - 0.04) / 2), (0.05, 0.30, h - 0.04), "blacksteel")


def plate(g, x, y, z, r=0.125, mat="white"): g.cyl((x, y, z + 0.008), r, 0.016, mat, 20)
def glass_(g, x, y, z, h=0.11): g.cyl((x, y, z + h / 2), 0.032, h, "bglass" if False else "white", 14, r2=0.04)
def cup(g, x, y, z, r=0.04): g.cyl((x, y, z + 0.035), r, 0.07, "white", 16, r2=r * 1.15); g.cyl((x, y, z + 0.068), r * 0.88, 0.004, "coffee", 16)
def bottle(g, x, y, z, h=0.3, mat="bglass"): g.cyl((x, y, z + h / 2), 0.04, h * 0.7, mat, 12); g.cyl((x, y, z + h * 0.85), 0.014, h * 0.3, mat, 8)
def bowl(g, x, y, z, r=0.16, food="leaf", seed=0):
    g.ell((x, y, z + r * 0.62), r, "white", (1, 1, 0.62), 14, 6, zmin=-0.05 if False else -1.0)
    g.blob((x, y, z + r * 0.62), r * 0.82, food, seed, (1, 1, 0.45), 0.25)


def set_table(g, x, y, z, w=0.4, d=0.28, side=1):
    plate(g, x, y, z); glass_(g, x + side * 0.17, y + 0.15, z)


def potted(g, x, y, h=0.5, w=0.4, kind="shrub", seed=0, pot="stone_dark"):
    g.box((x, y, h / 2), (w, w, h), pot)
    if kind == "shrub":
        rng = np.random.default_rng(abs(int(seed)))
        for k in range(5): g.blob((x + rng.uniform(-w * .25, w * .25), y + rng.uniform(-w * .25, w * .25), h + rng.uniform(.12, .5)), rng.uniform(.18, .27), "leaf", seed + k, (1, 1, 1.15), 0.3)
    elif kind == "tall":
        for k in range(4): g.blob((x, y, h + 0.25 + k * 0.28), 0.2 - k * 0.025, "leaf", seed + k, (1, 1, 1.2), 0.3)
    elif kind == "olive":
        g.cyl((x, y, h + 0.5), 0.04, 1.0, "wicker", 8)
        rng = np.random.default_rng(abs(int(seed)))
        for k in range(7): g.blob((x + rng.uniform(-.3, .3), y + rng.uniform(-.3, .3), h + 1.0 + rng.uniform(0, .5)), rng.uniform(.25, .38), "olive", seed + k, (1, 1, .7), 0.35)


# ---- sofas ---------------------------------------------------------------------------------------------------
def sofa(g, x, y, n=3, rot=0.0, seat="cream", frame="graphite", cushions=("terra", "teal")):
    """Modular outdoor sofa: n seats of 0.72 m. Local: back at -y side, sitter faces +y (before rot)."""
    W = 0.72 * n + 0.28; D = 0.92; c, s = math.cos(rot), math.sin(rot)
    def P(lx, ly, z): return (x + lx * c - ly * s, y + lx * s + ly * c, z)
    g.box(P(0, 0, 0.13), (W, D, 0.12), frame, rz=rot)
    for sx in (-1, 1): g.box(P(sx * (W / 2 - 0.07), 0, 0.37), (0.14, D, 0.5), frame, rz=rot)       # arms
    g.box(P(0, -D / 2 + 0.07, 0.52), (W - 0.28, 0.14, 0.78), frame, rz=rot)
    for i in range(n):
        lx = -W / 2 + 0.14 + 0.36 + i * 0.72
        g.box(P(lx, 0.04, 0.3), (0.70, D - 0.16, 0.2), seat, rz=rot)
        g.box(P(lx, -D / 2 + 0.27, 0.55), (0.68, 0.2, 0.46), seat, rz=rot - 0.0, rx=0.0)
    for k, cm in enumerate(cushions[:n]):
        lx = -W / 2 + 0.14 + 0.36 + (k % n) * 0.72 + (0.0)
        g.box(P(lx - 0.12 + 0.24 * (k % 2), -D / 2 + 0.38, 0.62), (0.42, 0.12, 0.4), cm, rz=rot + (0.2 if k % 2 else -0.12))


def armchair(g, x, y, rot=0.0, seat="cream", frame="graphite"):
    sofa(g, x, y, 1, rot, seat, frame, ())
    c, s = math.cos(rot), math.sin(rot)


def coffee_table(g, x, y, sx=1.1, sy=0.7, h=0.38, top="teak"):
    g.box((x, y, h), (sx, sy, 0.05), top)
    for ax in (-1, 1):
        for ay in (-1, 1): g.box((x + ax * (sx / 2 - 0.06), y + ay * (sy / 2 - 0.06), h / 2 - 0.01), (0.04, 0.04, h - 0.03), "blacksteel")
    g.box((x, y, h * 0.4), (sx - 0.15, sy - 0.15, 0.025), "blacksteel")


def round_table(g, x, y, r=0.42, h=0.74, mat="teak"):
    g.cyl((x, y, h - 0.02), r, 0.035, mat, 32); g.cyl((x, y, h / 2), 0.025, h - 0.04, "blacksteel", 10); g.cyl((x, y, 0.012), 0.2, 0.024, "blacksteel", 20)


def bistro_chair(g, x, y, rot, mat="wicker", frame="blacksteel"):
    c, s = math.cos(rot), math.sin(rot)
    def P(lx, ly, z): return (x + lx * c - ly * s, y + lx * s + ly * c, z)
    g.cyl(P(0, 0, 0.45), 0.215, 0.035, mat, 18)
    for lx, ly in ((-.15, -.15), (.15, -.15), (-.15, .15), (.15, .15)): g.box(P(lx, ly, 0.215), (0.025, 0.025, 0.43), frame, rz=rot)
    g.box(P(0, -0.2, 0.68), (0.4, 0.03, 0.34), mat, rz=rot)
    for lx in (-.18, .18): g.box(P(lx, -0.2, 0.55), (0.025, 0.025, 0.2), frame, rz=rot)


def adirondack(g, x, y, rot):
    c, s = math.cos(rot), math.sin(rot)
    def P(lx, ly, z): return (x + lx * c - ly * s, y + lx * s + ly * c, z)
    g.box(P(0, 0.02, 0.36), (0.62, 0.5, 0.04), "wood_white", rz=rot, rx=-0.1)
    g.box(P(0, -0.27, 0.62), (0.58, 0.04, 0.72), "wood_white", rz=rot, rx=0.38)
    for sx in (-1, 1):
        g.box(P(sx * 0.36, 0.02, 0.5), (0.07, 0.62, 0.035), "wood_white", rz=rot)
        g.box(P(sx * 0.31, 0.22, 0.18), (0.05, 0.05, 0.36), "wood_white", rz=rot)
        g.box(P(sx * 0.31, -0.2, 0.2), (0.05, 0.05, 0.4), "wood_white", rz=rot)


# ---- outdoor kitchen -------------------------------------------------------------------------------------------
def kitchen_run(g, x0, y, length, depth=0.64, kind="full", front=1, cab="graphite", top="oak"):
    """Counter run along local x starting at x0 for `length`; front faces +y (front=1) or -y (front=-1). Includes appliances."""
    n = int(round(length / 0.6)); w = length / n; yc = y
    for i in range(n):
        cx = x0 + w * (i + 0.5)
        g.box((cx, yc, 0.43), (w - 0.012, depth, 0.8), cab)
        g.box((cx, yc + front * (depth / 2 + 0.004), 0.43), (w - 0.05, 0.012, 0.72), cab)
        g.box((cx, yc + front * (depth / 2 + 0.018), 0.74), (0.24, 0.014, 0.014), "steel")
    g.box((x0 + length / 2, yc, 0.84), (length + 0.04, depth + 0.06, 0.04), top)
    return n


def grill_unit(g, x, y, front=1):
    """Built-in gas grill: stainless box with raised lid and knobs, on the worktop (top z=0.86)."""
    g.box((x, y, 0.995), (0.72, 0.55, 0.26), "steel")
    g.box((x, y - front * 0.02, 1.2), (0.72, 0.5, 0.05), "steel", rx=0.0)
    g.box((x, y + front * 0.27, 1.0), (0.6, 0.03, 0.06), "blacksteel")
    for k in range(4): g.cyl((x - 0.24 + k * 0.16, y + front * 0.285, 1.0), 0.02, 0.025, "blacksteel", 10, axis="y")
    g.box((x, y - front * 0.1, 1.145), (0.7, 0.3, 0.012), "blacksteel", rx=0.0)


def sink_unit(g, x, y, front=1):
    g.box((x, y, 0.862), (0.5, 0.4, 0.008), "steel"); g.box((x, y, 0.864), (0.42, 0.32, 0.006), "blacksteel")
    g.cyl((x, y - front * 0.24, 1.0), 0.013, 0.28, "steel", 10); g.cyl((x + 0.06 * front, y - front * 0.24, 1.14), 0.011, 0.14, "steel", 10, axis="x")


def hob_unit(g, x, y):
    g.box((x, y, 0.862), (0.55, 0.45, 0.008), "blacksteel")
    for hx in (-0.12, 0.12):
        for hy in (-0.1, 0.1): g.cyl((x + hx, y + hy, 0.868), 0.065, 0.006, "steel", 20)


def fridge(g, x, y, front=1):
    g.box((x, y, 0.9), (0.62, 0.64, 1.8), "steel"); g.box((x, y + front * 0.325, 1.3), (0.012, 0.012, 0.5), "blacksteel"); g.box((x, y + front * 0.32, 0.9), (0.62, 0.003, 0.006), "blacksteel")


def pizza_oven(g, x, y, front=1):
    g.box((x, y, 0.45), (1.1, 1.0, 0.9), "cream_brick"); g.box((x, y, 0.92), (1.2, 1.1, 0.06), "stone_dark")
    g.ell((x, y, 0.95), 0.58, "brick", (1, 0.95, 0.9), 22, 10, zmin=0.0)
    g.box((x, y + front * 0.5, 1.12), (0.5, 0.12, 0.38), "charcoal")        # arched opening (dark)
    g.cyl((x - 0.2, y - front * 0.18, 1.8), 0.1, 1.1, "brick", 14)                 # chimney


def kettle_grill(g, x, y):
    for k in range(3):
        a = k * 2.09; g.cyl((x + 0.22 * math.cos(a), y + 0.22 * math.sin(a), 0.34), 0.012, 0.68, "blacksteel", 8)
    g.ell((x, y, 0.85), 0.29, "charcoal", (1, 1, 0.7), 20, 8, zmin=-0.05)
    g.ell((x, y, 0.89), 0.3, "charcoal", (1, 1, 0.6), 20, 8, zmin=0.0)
    g.cyl((x, y, 1.1), 0.02, 0.05, "steel", 8); g.box((x + 0.26, y, 0.99), (0.1, 0.02, 0.02), "steel")


def mangal(g, x, y, rot=0.0, skewers=8):
    """Brazier for skewers (szaszłyki): long steel box on legs with glowing coals and skewers across."""
    c, s = math.cos(rot), math.sin(rot)
    def P(lx, ly, z): return (x + lx * c - ly * s, y + lx * s + ly * c, z)
    for lx in (-0.33, 0.33):
        for ly in (-0.13, 0.13): g.box(P(lx, ly, 0.35), (0.03, 0.03, 0.7), "blacksteel", rz=rot)
    g.box(P(0, 0, 0.74), (0.82, 0.34, 0.2), "blacksteel", rz=rot)
    g.box(P(0, 0, 0.838), (0.76, 0.28, 0.01), "coal", rz=rot)
    for k in range(skewers):
        lx = -0.32 + k * 0.0914
        g.box(P(lx, 0, 0.855), (0.012, 0.52, 0.012), "steel", rz=rot)
        for m_ in range(3): g.box(P(lx, -0.1 + m_ * 0.1, 0.862), (0.04, 0.07, 0.04), "meat", rz=rot)


def fire_pit(g, x, y, r=0.55):
    for k in range(14):
        a = k * 2 * math.pi / 14; g.box((x + r * math.cos(a), y + r * math.sin(a), 0.16), (0.3, 0.24, 0.3), "stone_dark", rz=a + math.pi / 2)
    g.cyl((x, y, 0.13), r - 0.08, 0.18, "coal", 20)
    for k in range(4):
        a = k * 0.8; g.cyl((x, y, 0.28), 0.045, 0.7, "wicker", 8, axis="x") if False else g.box((x, y, 0.24 + 0.07 * k), (0.8, 0.09, 0.09), "wicker", rz=a)
    for k, (dx, dy, hh) in enumerate(((0, 0, 0.55), (0.12, 0.05, 0.38), (-0.1, -0.08, 0.42), (0.05, -0.14, 0.33))):
        g.cyl((x + dx, y + dy, 0.42 + hh / 2), 0.09 - k * 0.012, hh, "flame", 10, r2=0.012)


def stump(g, x, y, h=0.42, r=0.2): g.cyl((x, y, h / 2), r, h, "wicker", 14)


# ---- misc garden ---------------------------------------------------------------------------------------------
def volleyball_net(g, x, y, length=6.0, rot=0.0):
    c, s = math.cos(rot), math.sin(rot)
    def P(lx, z): return (x + lx * c, y + lx * s, z)
    for sx in (-1, 1): g.cyl(P(sx * length / 2, 1.2), 0.04, 2.4, "blacksteel", 10)
    zs = np.linspace(1.5, 2.43, 9); xs = np.linspace(-length / 2, length / 2, int(length / 0.12))
    for z in zs: g.box(P(0, z), (length, 0.008, 0.008), "net", rz=rot)
    for lx in xs: g.box(P(lx, 1.97), (0.006, 0.006, 0.93), "net", rz=rot)
    g.box(P(0, 2.45), (length, 0.012, 0.07), "white", rz=rot)


def trampoline(g, x, y, r=1.6):
    g.cyl((x, y, 0.5), r, 0.04, "rubber", 36)
    g.cyl((x, y, 0.505), r - 0.18, 0.012, "blue", 36)
    for k in range(10):
        a = k * 2 * math.pi / 10; g.cyl((x + r * math.cos(a), y + r * math.sin(a), 0.25), 0.02, 0.5, "steel", 6)
        g.cyl((x + r * math.cos(a), y + r * math.sin(a), 1.4), 0.015, 1.8, "blacksteel", 6)


def sunbed(g, x, y, rot, seat="white"):
    c, s = math.cos(rot), math.sin(rot)
    def P(lx, ly, z): return (x + lx * c - ly * s, y + lx * s + ly * c, z)
    g.box(P(0, 0.2, 0.32), (0.66, 1.2, 0.07), seat, rz=rot)
    g.box(P(0, -0.58, 0.46), (0.66, 0.85, 0.07), seat, rz=rot, rx=0.5)
    for lx in (-0.3, 0.3):
        for ly in (-0.2, 0.7): g.box(P(lx, ly, 0.14), (0.04, 0.04, 0.28), "blacksteel", rz=rot)


def parasol(g, x, y, h=2.5, r=1.5, mat="cream", rim=None):
    g.cyl((x, y, h / 2), 0.025, h, "blacksteel", 8)
    g.add(ell_p((x, y, h), r, (1, 1, 0.18), 24, 5, zmin=0.0), mat, True)
    g.cyl((x, y, 0.03), 0.28, 0.06, "stone_dark", 16)


def string_lights_line(g, p0, p1, sag=0.35, n=18, bulbs=True):
    for i in range(n + 1):
        t = i / n; p = np.array(p0) * (1 - t) + np.array(p1) * t; p[2] -= sag * 4 * t * (1 - t)
        g.cyl(p, 0.02, 0.05, "bulb", 6) if i % 2 == 0 else None


# ---- stylised seated / standing guests (clay-like smooth forms, readable at 3-8 m) ------------------------------------
def person(g, x, y, rot=0.0, shirt="teal", pants="denim", skin="skin1", hair="hair_br", seated=True, long_hair=False, arm_to=0.28):
    """Guest facing local +y (rot as for chairs).  Seated: seat height 0.46."""
    c, s = math.cos(rot), math.sin(rot)
    def P(lx, ly, z): return (x + lx * c - ly * s, y + lx * s + ly * c, z)
    def PE(lx, ly, z, r, sc, **k): return ell_p(P(lx, ly, z), r, sc, **k)
    def rotvec(v): return v
    z0 = 0.50 if seated else 0.0
    if seated:
        for sx in (-1, 1):
            g.add(_rot_box(P(sx * 0.1, 0.2, z0 + 0.07), (0.15, 0.46, 0.14), rot), pants)            # thigh
            g.add(_rot_box(P(sx * 0.1, 0.42, z0 - 0.17), (0.12, 0.12, 0.44), rot), pants)           # shin
            g.add(_rot_box(P(sx * 0.1, 0.5, 0.04), (0.11, 0.26, 0.07), rot), "blacksteel")          # shoe
        torso_z = z0 + 0.44
    else:
        for sx in (-1, 1):
            g.add(_rot_box(P(sx * 0.09, 0, 0.45), (0.15, 0.17, 0.9), rot), pants); g.add(_rot_box(P(sx * 0.09, 0.05, 0.04), (0.12, 0.27, 0.08), rot), "blacksteel")
        torso_z = 1.15
    g.add(PE(0, 0, torso_z, 0.2, (0.95, 0.62, 1.45), seg=14, rings=8), shirt, True)            # torso
    g.add(PE(0, 0, torso_z + 0.34, 0.075, (1, 1, 1.4), seg=10, rings=4), skin, True)         # neck
    g.add(PE(0, 0.01, torso_z + 0.5, 0.115, (0.9, 1.0, 1.15), seg=14, rings=8), skin, True)  # head
    g.add(PE(0, -0.02, torso_z + 0.55, 0.12, (0.95, 1.05, 0.95), seg=12, rings=6, zmin=0.1 if False else -0.2), hair, True)
    if long_hair: g.add(PE(0, -0.07, torso_z + 0.36, 0.12, (1.0, 0.7, 1.7), seg=10, rings=6), hair, True)
    for sx in (-1, 1):                                                                           # arms reaching forward to the table / lap
        g.add(_rot_box(P(sx * 0.24, 0.0, torso_z + 0.1), (0.075, 0.09, 0.3), rot), shirt)
        g.add(_rot_box(P(sx * 0.23, arm_to, torso_z - 0.02), (0.065, 0.3, 0.075), rot), shirt)
        g.add(PE(sx * 0.22, arm_to + 0.17, torso_z - 0.02, 0.04, (1, 1.1, 0.9), seg=8, rings=4), skin, True)


def _rot_box(c, s, rz):
    return box_p(c, s, rz)
