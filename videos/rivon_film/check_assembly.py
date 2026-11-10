"""Per-frame interpenetration check of the animated assembly (bpy).  usage: python check_assembly.py [f0 f1 step]
For every frame: all 49 parts + 196 screws are posed by film_anim.Anim; pairs whose AABBs touch are tested with BVH overlap on
meshes shrunk 0.6 mm (faces in contact may slide).  Pairs that are both seated in their final relative pose are skipped
(the final assembly itself is validated separately).  Also reports the camera's clearance to every part."""
import sys, json
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import bpy, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import film_lib as FL, film_anim as AN
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
FL.build_pergola("PERGOLA"); bpy.context.view_layer.update()
A = AN.Anim(); SHR = 0.0006

def shrunk_soup(ob, shr):
    """world-space triangle soup of a mesh object, every vertex moved inward by shr along the sum of its distinct face normals
    (so edges and corners shrink too, not only face interiors)."""
    M = np.array(ob.matrix_world); R = M[:3, :3]
    v = np.array([list(x.co) for x in ob.data.vertices]); vw = (R @ v.T).T + M[:3, 3]
    nrm = {}
    for p in ob.data.polygons:
        n = R @ np.array(p.normal); n /= (np.linalg.norm(n) + 1e-12); key = tuple(np.round(n, 3))
        for vi in p.vertices: nrm.setdefault(vi, {})[key] = n
    off = np.zeros_like(vw)
    for vi, d in nrm.items(): off[vi] = sum(d.values())
    vs = vw - off * shr
    V, F = [], []
    for p in ob.data.polygons:
        idx = list(p.vertices)
        for k in range(1, len(idx) - 1):
            b = len(V); V += [vs[idx[0]], vs[idx[k]], vs[idx[k + 1]]]; F.append([b, b + 1, b + 2])
    return V, F

LOCAL = {}
for pid, o in A.objs.items():
    Minv = np.array(o.matrix_world.inverted()); objs = [o] + list(o.children_recursive)
    V, F = [], []
    for ob in objs:
        if ob.type != "MESH": continue
        v2, f2 = shrunk_soup(ob, SHR); b = len(V); V += v2; F += [[b + t[0], b + t[1], b + t[2]] for t in f2]
    V = np.array(V); V = (Minv[:3, :3] @ V.T).T + Minv[:3, 3]; LOCAL[pid] = (V, F)
IDS = sorted(A.objs)
args = [int(x) for x in sys.argv[sys.argv.index("--") + 1:]] if "--" in sys.argv else []
f0, f1, st = (args + [0, 269, 1])[:3] if args else (0, 269, 1)

def seated(pid, a):
    S = A.S[pid]; return a >= S["seat"]
bad = []; camclear = []
for f in range(f0, f1 + 1, st):
    A.apply(f); bpy.context.view_layer.update()
    a = AN.clock_of_frame(min(f, AN.F_ASM_END)) if f <= AN.LAB1[1] else AN.disassembly_clock(f)
    W = {}; BB = {}
    for pid in IDS:
        M = np.array(A.objs[pid].matrix_world); V = (M[:3, :3] @ LOCAL[pid][0].T).T + M[:3, 3]; W[pid] = V; BB[pid] = (V.min(0), V.max(0))
    lo = np.array([BB[p][0] for p in IDS]); hi = np.array([BB[p][1] for p in IDS])
    trees = {}
    for i, p in enumerate(IDS):
        ov = np.where(np.all(hi[i + 1:] >= lo[i], 1) & np.all(lo[i + 1:] <= hi[i], 1))[0] + i + 1
        for j in ov:
            q = IDS[j]
            if seated(p, a) and seated(q, a) and A.S[p]["groups"] == A.S[q]["groups"]: continue
            if p.startswith("SCREW") and q.startswith("SCREW"): continue
            sc, tb = (p, q) if p.startswith("SCREW") else (q, p)
            if sc.startswith("SCREW") and tb.startswith(("POST", "BEAM", "RAFTER")) and a >= A.S[sc]["app"]: continue   # a screw being driven INTO wood
            for r in (p, q):
                if r not in trees: trees[r] = BVHTree.FromPolygons([tuple(x) for x in W[r]], LOCAL[r][1])
            if trees[p].overlap(trees[q]): bad.append((f, p, q))
    loc, tgt, lens, fs = AN.camera_for_frame(f); c = np.array(loc)
    d = min(float(np.linalg.norm(np.maximum(0, np.maximum(BB[p][0] - c, c - BB[p][1])))) for p in IDS)
    camclear.append((f, round(d, 3)))
    if f % 10 == 0: print("frame", f, "a=%.1f" % a, "overlaps so far", len(bad), "cam clearance", round(d, 3), flush=True)
pairs = {}
for f, p, q in bad: pairs.setdefault((p, q), []).append(f)
print("OVERLAPS", len(bad))
for (p, q), fs in sorted(pairs.items(), key=lambda kv: kv[1][0]): print(" ", p, q, "frames", fs[0], "-", fs[-1], "n", len(fs))
print("MIN CAMERA CLEARANCE", min(camclear, key=lambda x: x[1]))
json.dump({"overlaps": [[f, p, q] for f, p, q in bad], "camclear": camclear}, open(HERE / "check_result.json", "w"))
