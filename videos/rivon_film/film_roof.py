"""Roof for the lab assembly (owner rules): profiled sheets with ALL grooves running one way - across the pergola, along the rafters
(turned 90 deg from the earlier video) - and one long side higher, so water and snow drain properly.  The slope comes from tapered
pine firring strips (kliny) screwed on top of every rafter and of both end beams; the sheets lie on them.
Every piece is a separate rigid object so the animation can bring it in; nothing touches the RIVON connectors."""
import math
import numpy as np
import bpy, mathutils

TOP = 2.6006                         # strips sit on the steel tops (Trojak / Mocowanie top = 2.600; timber top = 2.597)
X0, X1 = -1.747, 1.747              # outer faces of the long beams
SLOPE = math.radians(3.0)           # high side = x0 (left), low side = x1 (right)
H_LO = 0.020
OVER_X, Y_HALF = 0.16, 3.15
SHEET_W, GAP, N_SHEETS = 1.048, 0.002, 6
RIB_PITCH, RIB_H, RIB_TOP, RIB_BOT = 0.1747, 0.022, 0.040, 0.075
T_SHEET = 0.0015
WEDGE_YS = [-2.95] + [-2.4 + 0.48 * i for i in range(11)] + [2.95]


def h_of(x):  return H_LO + (X1 - x) * math.tan(SLOPE)            # firring height above TOP at x
def plane(x): return TOP + h_of(x)


def _mat_sheet():
    m = bpy.data.materials.get("roof_sheet_anthracite")
    if m: return m
    m = bpy.data.materials.new("roof_sheet_anthracite"); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.052, 0.056, 0.062, 1); b.inputs["Metallic"].default_value = 0.65; b.inputs["Roughness"].default_value = 0.40
    return m


def _wedge(name, y, width, pine, coll):
    """tapered strip, local z = world x (long axis, so the pine shader's grain runs along it)."""
    L = X1 - X0; hl, hh = h_of(X1), h_of(X0)
    # local coords: u = world y offset, v = world z offset from TOP, w = world x
    v = []
    for w_, h_ in ((X0, hh), (X1, hl)):
        for u in (-width / 2, width / 2):
            v += [(u, 0.0, w_), (u, h_, w_)]
    f = [(0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (1, 3, 7, 5), (0, 4, 6, 2)]
    me = bpy.data.meshes.new(name); me.from_pydata(v, [], f); me.update(); me.materials.append(pine)
    ob = bpy.data.objects.new(name, me)
    R = mathutils.Matrix(((0, 0, 1, 0), (1, 0, 0, y), (0, 1, 0, TOP), (0, 0, 0, 1)))
    ob.matrix_world = R; coll.objects.link(ob)
    bv = ob.modifiers.new("edge_break", "BEVEL"); bv.width = 0.0006; bv.segments = 2; bv.limit_method = "ANGLE"
    return ob


def _profile(width):
    """trapezoid profile across the sheet (y offset, z offset of the BOTTOM surface)."""
    pts = []; n = int(round(width / RIB_PITCH)); y = -width / 2
    for k in range(n):
        y0 = -width / 2 + k * RIB_PITCH; flat = (RIB_PITCH - RIB_BOT) / 2
        sl = (RIB_BOT - RIB_TOP) / 2
        pts += [(y0, 0), (y0 + flat, 0), (y0 + flat + sl, RIB_H), (y0 + flat + sl + RIB_TOP, RIB_H), (y0 + flat + 2 * sl + RIB_TOP, 0)]
    pts.append((width / 2, 0.0))
    out = [pts[0]]
    for p in pts[1:]:
        if abs(p[0] - out[-1][0]) > 1e-6: out.append(p)
    return out


def _sheet(name, yc, mat, coll):
    """profiled sheet: ribs run along x (down the slope).  Built in world coords around its own centre."""
    prof = _profile(SHEET_W); xs = (X0 - OVER_X, X1 + OVER_X)
    n = len(prof); v = []; f = []
    nrm = (-math.sin(SLOPE), 0.0, math.cos(SLOPE))                  # sheet normal (tilted)
    for xi, x in enumerate(xs):
        for (yy, zz) in prof:
            zb = plane(x) + zz / math.cos(SLOPE)
            v.append((x, yc + yy, zb)); v.append((x + nrm[0] * T_SHEET, yc + yy, zb + nrm[2] * T_SHEET))
    def idx(xi, k, top): return xi * 2 * n + 2 * k + top
    for k in range(n - 1):
        for top in (0, 1):
            q = [idx(0, k, top), idx(0, k + 1, top), idx(1, k + 1, top), idx(1, k, top)]
            f.append(q if top else q[::-1])
    for xi in (0, 1):
        for k in range(n - 1):
            q = [idx(xi, k, 0), idx(xi, k + 1, 0), idx(xi, k + 1, 1), idx(xi, k, 1)]; f.append(q if xi else q[::-1])
    for k in (0, n - 1):
        q = [idx(0, k, 0), idx(1, k, 0), idx(1, k, 1), idx(0, k, 1)]; f.append(q if k else q[::-1])
    c = np.mean(np.array(v), 0)
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(np.array(p) - c) for p in v], [], f); me.update(); me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); ob.location = tuple(c); coll.objects.link(ob)
    return ob


def build_roof(coll, pine):
    ids = []
    for i, y in enumerate(WEDGE_YS):
        nm = f"WEDGE_{i:02d}"; _wedge(nm, y, 0.045, pine, coll); ids.append(nm)
    mat = _mat_sheet(); y0 = -Y_HALF
    for k in range(N_SHEETS):
        yc = y0 + k * (SHEET_W + GAP) + SHEET_W / 2; nm = f"SHEET_{k}"; _sheet(nm, yc, mat, coll); ids.append(nm)
    import bmesh
    for nm in ids:                                                      # outward normals (shading + collision checks)
        me = bpy.data.objects[nm].data; bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    return ids
