"""Finds a collision-free flight route (vortex -> approach start) for every part that touches anything on its way, and keeps the
camera clear (>= 0.35 m).  Writes assembly_routes.json, read by film_anim.Anim.   usage: python solve_routes.py"""
import sys, json, itertools
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import bpy, numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
import film_lib as FL, film_anim as AN
RP = HERE / "assembly_routes.json"
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
FL.build_pergola("PERGOLA"); bpy.context.view_layer.update()
A = AN.Anim(); SHR = 0.0006; CAM_CLEAR = 0.35
exec(open(HERE / "check_assembly.py").read().split("def shrunk_soup")[1].join(["def shrunk_soup", ""]).split("LOCAL = {}")[0]) if False else None
src = open(HERE / "check_assembly.py").read()
exec("def shrunk_soup" + src.split("def shrunk_soup")[1].split("\nLOCAL = {}")[0])
LOCAL = {}
for pid, o in A.objs.items():
    Minv = np.array(o.matrix_world.inverted()); V, F = [], []
    for ob in [o] + list(o.children_recursive):
        if ob.type != "MESH": continue
        v2, f2 = shrunk_soup(ob, SHR); b = len(V); V += v2; F += [[b + t[0], b + t[1], b + t[2]] for t in f2]
    V = np.array(V); LOCAL[pid] = ((Minv[:3, :3] @ V.T).T + Minv[:3, 3], F)
IDS = sorted(A.objs); FR = list(range(0, int(AN.F_ASM_END) + 2))

def clock(f): return AN.clock_of_frame(min(f, AN.F_ASM_END))
CACHE = {}
def build_cache():
    for f in FR:
        A.apply(f); bpy.context.view_layer.update()
        CACHE[f] = {p: np.array(A.objs[p].matrix_world) for p in IDS}
def mat_of(pid, f):
    a = clock(f); P, Q, k = A.pose(pid, a)
    if A.S[pid].get("spin") and k > 0:
        from mathutils import Quaternion
        Q = Q @ Quaternion((0, 0, 1), A.S[pid]["spin"] * k)
    M = Matrix.Translation(P - Q @ A.vloc[pid]) @ Q.to_matrix().to_4x4(); return np.array(M)
def world(pid, M): return (M[:3, :3] @ LOCAL[pid][0].T).T + M[:3, 3]
def skip(p, q, a):
    Sp, Sq = A.S[p], A.S[q]
    if a >= Sp["seat"] and a >= Sq["seat"] and Sp["groups"] == Sq["groups"]: return True
    if p.startswith("SCREW") and q.startswith("SCREW"): return True
    sc, tb = (p, q) if p.startswith("SCREW") else (q, p)
    if sc.startswith("SCREW") and tb.startswith(("POST", "BEAM", "RAFTER")) and a >= A.S[sc]["app"]: return True
    return False
def window(pid):
    S = A.S[pid]; f0 = int(AN.frame_of_clock(S["leave"])) - 1; f1 = int(AN.frame_of_clock(S["seat"])) + 1
    return [f for f in FR if f0 <= f <= f1]
def violations(pid, frames=None):
    out = []
    for f in (frames or window(pid)):
        a = clock(f); M = mat_of(pid, f); V = world(pid, M); lo, hi = V.min(0), V.max(0); tp = None
        cam = np.array(AN.camera_for_frame(f)[0])
        if np.linalg.norm(np.maximum(0, np.maximum(lo - cam, cam - hi))) < CAM_CLEAR: out.append((f, "CAMERA"))
        for q in IDS:
            if q == pid or skip(pid, q, a): continue
            Mq = CACHE[f][q]; Vq = world(q, Mq)
            if np.any(Vq.max(0) < lo) or np.any(Vq.min(0) > hi): continue
            tp = tp or BVHTree.FromPolygons([tuple(x) for x in V], LOCAL[pid][1])
            if tp.overlap(BVHTree.FromPolygons([tuple(x) for x in Vq], LOCAL[q][1])): out.append((f, q))
    return out

build_cache()
VAR_S = [(k, dz, se, lat) for dz in (0.0, -0.5, 0.5, 1.0, -1.0) for k in (0.5, 0.9, 1.4) for lat in (0.0, 0.8, -0.8) for se in (0.85,)]
VAR_O = [(0.5, dz, se, lat) for dz in (0.0, 0.6, 1.2, -0.4, 1.8) for se in (0.85, 0.6) for lat in (0.0, 1.0, -1.0, 2.0, -2.0)]
routes = {k: list(v) for k, v in A.route.items()}               # start from the previous solution
for rnd in range(3):
    bad = [p for p in sorted(IDS, key=lambda q: A.S[q]["leave"]) if violations(p)]
    print("round", rnd, "parts with violations:", len(bad), bad[:20], flush=True)
    if not bad: break
    for p in bad:
        best = None
        for v in (VAR_S if p.startswith("SCREW") else VAR_O):
            A.route[p] = v; n = len(violations(p))
            if best is None or n < best[0]: best = (n, v)
            if n == 0: break
        A.route[p] = best[1]; routes[p] = list(best[1])
        for f in window(p): CACHE[f][p] = mat_of(p, f)
        print("  ", p, "->", best[1], "remaining", best[0], flush=True)
json.dump(routes, open(RP, "w"), indent=0)
print("wrote", RP, len(routes))
