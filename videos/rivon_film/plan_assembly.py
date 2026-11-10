"""Collision-free assembly planner for the RIVON pergola (assembly-by-disassembly).
Run inside Blender/bpy:  python plan_assembly.py  -> writes assembly_plan.json
Every part (exact STEP meshes + timber boxes, screws excluded) is tested against the parts still in place: a part may be taken out
along an axis direction only if a straight translation of 4 m along it never overlaps any remaining part (meshes shrunk by 0.6 mm so
faces in contact may slide). The reverse of the removal sequence is a physically valid assembly order with an insertion direction
per part. Screws go in last for each part, along their own axis, into the real holes."""
import sys, json, math
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import bpy, numpy as np, mathutils
from mathutils.bvhtree import BVHTree
import film_lib as FL

for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
FL.build_pergola("PERGOLA"); bpy.context.view_layer.update()
L = FL.load_json("layout.json")
SHRINK = 0.0006

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

def part_mesh(name):
    """world-space verts/tris of a part (instance empty with CAD children, or timber object), shrunk along face normals."""
    o = bpy.data.objects[name]; objs = [o] + [c for c in o.children_recursive] if o.type == "EMPTY" else [o]
    V, F = [], []
    for ob in objs:
        if ob.type != "MESH": continue
        v2, f2 = shrunk_soup(ob, SHRINK); b = len(V); V += v2; F += [[b + t[0], b + t[1], b + t[2]] for t in f2]
    return np.array(V), F

PARTS = [p["id"] for p in L["parts"]] + [t["id"] for t in L["timber"]] + [o.name for o in bpy.data.objects if o.name.startswith(("WEDGE_", "SHEET_"))]
OBJ = {pid: (f"INST_{pid}" if f"INST_{pid}" in bpy.data.objects else pid) for pid in PARTS}
MESH = {pid: part_mesh(OBJ[pid]) for pid in PARTS}
TREE = {pid: BVHTree.FromPolygons([tuple(x) for x in MESH[pid][0]], MESH[pid][1]) for pid in PARTS}
BB = {pid: (MESH[pid][0].min(0), MESH[pid][0].max(0)) for pid in PARTS}
print("parts", len(PARTS), "tris", sum(len(MESH[p][1]) for p in PARTS), flush=True)

DIRS = {"+z": (0, 0, 1), "+x": (1, 0, 0), "-x": (-1, 0, 0), "+y": (0, 1, 0), "-y": (0, -1, 0), "-z": (0, 0, -1)}
STEPS = np.concatenate([np.arange(0.002, 0.40, 0.004), np.arange(0.40, 4.0, 0.02)])

def blocked(pid, d, others):
    v0, F = MESH[pid]; lo, hi = BB[pid]; d = np.array(d, float)
    # broad phase: which others can the swept AABB touch at all
    sw_lo = np.minimum(lo, lo + d * STEPS[-1]); sw_hi = np.maximum(hi, hi + d * STEPS[-1])
    cand = [q for q in others if np.all(BB[q][1] >= sw_lo) and np.all(BB[q][0] <= sw_hi)]
    if not cand: return None
    for s in STEPS:
        mlo, mhi = lo + d * s, hi + d * s
        near = [q for q in cand if np.all(BB[q][1] >= mlo) and np.all(BB[q][0] <= mhi)]
        if not near: continue
        t = BVHTree.FromPolygons([tuple(x) for x in (v0 + d * s)], F)
        for q in near:
            if t.overlap(TREE[q]): return q
    return None

# The top frame (4 Trojak 3D + 4 beams) is a closed loop of tube sockets: no single part can go in last by a straight move
# (the greedy check proves it).  It is built from rigid sub-assemblies instead - each move below is one straight translation
# of a GROUP of parts, verified against everything already in place:
#   trojaks slide onto beam ends -> the two end beams slide into the right-side unit -> the right unit slides into the left unit
#   -> the finished frame is lowered onto the four posts standing in their Stopa feet.
FRAME = ["BEAM_LONG_L", "TROJAK_C1", "TROJAK_C4", "BEAM_LONG_R", "TROJAK_C2", "TROJAK_C3", "BEAM_END_A", "BEAM_END_B"]
# assembly steps in order: (stage, moving group, insertion direction).  Frame steps happen in the air (the frame is built
# FRAME_LIFT above its final height, clear of the posts) and only frame parts count as obstacles there.
STEPS_A = (
    [("feet", [f"STOPA_C{k}"], "-z") for k in (1, 2, 3, 4)] +
    [("posts", [f"POST_C{k}"], "-z") for k in (1, 2, 3, 4)] +
    [("frame", ["BEAM_LONG_L"], "none"), ("frame", ["TROJAK_C1"], "+y"), ("frame", ["TROJAK_C4"], "-y"),
     ("frameR", ["BEAM_LONG_R"], "none"), ("frameR", ["TROJAK_C2"], "+y"), ("frameR", ["TROJAK_C3"], "-y"),
     ("frameR", ["BEAM_END_A"], "+x"), ("frameR", ["BEAM_END_B"], "+x"),
     ("frame", ["BEAM_LONG_R", "TROJAK_C2", "TROJAK_C3", "BEAM_END_A", "BEAM_END_B"], "-x"),
     ("lower", FRAME, "-z")] +
    [("mocow", [f"MOCOW_{s}_{i}"], "-z") for i in range(11) for s in ("L", "R")] +
    [("rafter", [f"RAFTER_{i}"], "-z") for i in range(11)] +
    [("roof", [f"SHEET_{j}"], "-z") for j in range(6)])
VEC = {"+z": (0, 0, 1), "-z": (0, 0, -1), "+x": (1, 0, 0), "-x": (-1, 0, 0), "+y": (0, 1, 0), "-y": (0, -1, 0)}
placed = []; report = []; ok_all = True
for stage, grp, dn in STEPS_A:
    if dn == "none": placed += grp; report.append(dict(stage=stage, group=grp, insert=None, ok=True)); continue
    rem = tuple(-c for c in VEC[dn])
    RUNIT = ["BEAM_LONG_R", "TROJAK_C2", "TROJAK_C3", "BEAM_END_A", "BEAM_END_B"]       # the right unit is built apart (offset in +x)
    static = [q for q in placed if q not in grp and (stage not in ("frame", "frameR") or q in FRAME) and (stage != "frameR" or q in RUNIT)]
    hits = {g: blocked(g, rem, static) for g in grp}
    ok = all(h is None for h in hits.values()); ok_all &= ok
    print(stage, grp if len(grp) < 3 else f"{len(grp)} parts", dn, "OK" if ok else f"BLOCKED {hits}", flush=True)
    report.append(dict(stage=stage, group=grp, insert=list(VEC[dn]), ok=ok))
    placed += [g for g in grp if g not in placed]
json.dump({"steps": report, "all_ok": bool(ok_all)}, open(HERE / "assembly_plan.json", "w"), indent=1)
print("ALL OK" if ok_all else "SOME MOVES BLOCKED")
raise SystemExit
MOVES = [  # (group that moves, removal direction = opposite of the insertion, static set it is checked against)
    (["STOPA_C1"], "+z"), (["STOPA_C2"], "+z"), (["STOPA_C3"], "+z"), (["STOPA_C4"], "+z"),
    (["POST_C1"], "+z"), (["POST_C2"], "+z"), (["POST_C3"], "+z"), (["POST_C4"], "+z"),
]
def side(pid): c = BB[pid]; return (c[0] + c[1]) / 2
TRO = {k: side(f"TROJAK_{k}") for k in ("C1", "C2", "C3", "C4")}
print({k: np.round(v, 2).tolist() for k, v in TRO.items()}, {b: np.round(side(b), 2).tolist() for b in ("BEAM_LONG_L", "BEAM_LONG_R", "BEAM_END_A", "BEAM_END_B")})
RANK = {"RAFTER": 0, "MOCOW": 1, "BEAM_END": 2, "BEAM_LONG": 3, "TROJAK": 4, "POST": 5, "STOPA": 6}
def rank(pid):
    for k, r in RANK.items():
        if pid.startswith(k): return r
    return 9
PREF = ["+z", "+x", "-x", "+y", "-y", "-z"]          # prefer lowering parts in from above
remaining = list(PARTS); removal = []
while remaining:
    progress = False
    for pid in sorted(remaining, key=lambda p: (rank(p), -BB[p][1][2], p)):
        others = [q for q in remaining if q != pid]
        for dn in PREF:
            hitp = blocked(pid, DIRS[dn], others)
            if hitp is None:
                removal.append((pid, dn)); remaining.remove(pid); progress = True
                print("remove", pid, dn, flush=True); break
        if progress: break
    if not progress:
        print("DEADLOCK, remaining:", remaining, flush=True)
        for pid in remaining:
            print(" ", pid, {dn: blocked(pid, DIRS[dn], [q for q in remaining if q != pid]) for dn in PREF})
        break

order = [{"id": pid, "insert_dir": [-c for c in DIRS[dn]], "remove": dn} for pid, dn in reversed(removal)]
json.dump({"order": order, "deadlock": remaining}, open(HERE / "assembly_plan.json", "w"), indent=1)
print("wrote assembly_plan.json", len(order), "parts; deadlock", remaining)
