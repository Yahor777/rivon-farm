"""RIVON lab film v5 - ONLY the lab, 30 s @ 30 fps = 900 frames, 9:16, one calm continuous camera take with macro moments.

Owner rules built in:
  * wood screws with a sharp point (film_lib), driven along their own axes into the real holes;
  * in every Trojak 3D both top beams fill the upper socket: the long beam runs to the corner wall, the end beam goes in and butts
    against its side (one goes deeper than the other) - shown in macro at corner C1;
  * roof: profiled sheets, all grooves one way along the rafters, one long side higher (tapered firring strips) - film_roof.
Realistic order (plan_assembly.py proves each straight move collision-free on the STEP meshes):
  feet -> posts down into the feet -> long beams -> Trojaks slide onto the long-beam ends -> end beams into the right unit ->
  right unit slides in, end beams enter the left Trojaks and butt against the long beam -> the frame is lowered onto the posts ->
  Mocowanie belek 2 on the inner beam faces + wood screws -> rafters dropped in -> screws from below -> firring strips -> sheets.
Waiting parts circle slowly in a vortex around the lab (one rigid ring, so they never touch); every part flies out on a smooth curve,
turns to its final orientation BEFORE the short straight insertion.  All transforms are rigid.  Times below are FILM FRAMES."""
import math, json, os
import numpy as np
import bpy, mathutils
from mathutils import Matrix, Vector, Quaternion
from film_lib import load_json

FPS, NF = 30, 900
LAB1 = (0, 899); SCENES = []; SCENE_LEN = 0; LAB2 = (900, 900)
F_ASM_END = 772                   # everything seated
LIFT, JOIN = 1.6, 2.0             # top frame is built LIFT above its place; right unit built JOIN out in +x
GROUP_T = {"join": (352.0, 424.0), "lift": (432.0, 506.0)}
# macro moments: the vortex (and the world around the focus) slows down here
SLOWMO = [(128.0, 196.0), (292.0, 346.0), (356.0, 428.0), (470.0, 512.0), (514.0, 592.0), (592.0, 626.0)]
SLOW_K = 0.35
LOGO_C1 = (Vector((-1.65, -2.7471, 2.5499)), Vector((1.0, 0.0, 0.0)))     # engraved RIVON mark on Trojak C1 (faces into the pergola)


def clamp01(x): return max(0.0, min(1.0, x))
def e_io(u): return u * u * (3 - 2 * u)
def e_io5(u): return u * u * u * (u * (6 * u - 15) + 10)
def e_seat(u): return 1 - (1 - u) ** 2.2               # decelerate into the seat, no overshoot


# ----------------------------------------------------------------------------------------------- vortex clock (slow in macros)
def _speed(f):
    s = 1.0
    for a0, a1 in SLOWMO:
        w = 14.0; k = clamp01((f - (a0 - w)) / w) * clamp01(((a1 + w) - f) / w); s = min(s, 1.0 - (1.0 - SLOW_K) * e_io(k))
    return s
_FG = np.arange(0, NF + 1, 0.25); _SP = np.concatenate([[0.0], np.cumsum([_speed(x) * 0.25 for x in _FG[1:]])])
def spin_of(f): return float(np.interp(f, _FG, _SP))
def clock_of_frame(f): return float(f)                 # kept for the check / route tools
def frame_of_clock(a): return float(a)
def disassembly_clock(f): return float(f)


# ----------------------------------------------------------------------------------------------- schedule (film frames)
def schedule():
    S = {}
    def put(pid, app, seat, d, L, groups=(), fly=44.0):
        S[pid] = dict(leave=app - fly, app=app, seat=seat, dir=None if d is None else Vector(d), L=L, groups=tuple(groups))
    D = (0, 0, -1)
    put("STOPA_C2", 52, 70, D, 0.8); put("STOPA_C3", 62, 80, D, 0.8); put("STOPA_C4", 72, 90, D, 0.8); put("STOPA_C1", 98, 118, D, 0.8)
    put("POST_C2", 106, 128, D, 1.0); put("POST_C3", 118, 140, D, 1.0); put("POST_C4", 130, 152, D, 1.0)
    put("POST_C1", 140, 192, D, 1.0, fly=52)                                                         # macro 1
    F = ("lift",); R = ("lift", "join")
    put("BEAM_LONG_L", 236, 236, None, 0.0, F, fly=60); put("BEAM_LONG_R", 246, 246, None, 0.0, R, fly=60)
    put("TROJAK_C4", 244, 262, (0, -1, 0), 0.6, F); put("TROJAK_C2", 250, 268, (0, 1, 0), 0.6, R); put("TROJAK_C3", 256, 274, (0, -1, 0), 0.6, R)
    put("TROJAK_C1", 296, 342, (0, 1, 0), 0.6, F, fly=50)                                            # macro 2
    put("BEAM_END_A", 298, 318, (1, 0, 0), 0.9, R); put("BEAM_END_B", 306, 326, (1, 0, 0), 0.9, R)
    put("MOCOW_L_0", 514, 546, D, 0.5, fly=46)                                                       # macro 4
    k = 0
    for i in range(11):
        for s in ("L", "R"):
            if (s, i) == ("L", 0): continue
            a = 520 + 3.0 * k; put(f"MOCOW_{s}_{i}", a, a + 14, D, 0.5); k += 1
    put("RAFTER_0", 590, 624, D, 0.9, fly=50)                                                        # macro 5
    for i in range(1, 11): put(f"RAFTER_{i}", 646, 666, D, 0.9, fly=50)          # the other 10 rafters come down together into their hangers
    for j in range(13): put(f"WEDGE_{j:02d}", 690, 706, D, 0.5, fly=50)          # all 13 strips come down together as one rigid comb
    for j in range(6): a = 714 + 8.0 * j; put(f"SHEET_{j}", a, a + 18, D, 0.6, fly=52)
    return S


def group_offset(groups, a):
    o = Vector((0, 0, 0))
    if "join" in groups:
        t0, t1 = GROUP_T["join"]; o += Vector((JOIN, 0, 0)) * (1 - e_seat(e_io(clamp01((a - t0) / (t1 - t0))) ** 0.8))
    if "lift" in groups:
        t0, t1 = GROUP_T["lift"]; o += Vector((0, 0, LIFT)) * (1 - e_io5(clamp01((a - t0) / (t1 - t0))))
    return o


# ----------------------------------------------------------------------------------------------- vortex
def _rng(seed): return np.random.default_rng(seed)
class Vortex:
    """ONE rigid ring turning slowly: waiting parts never move relative to each other.  Slots are packed collision-free; radius grows
    with the departure time, so a part flying inward only crosses radii whose parts already left."""
    OMEGA = 0.0075                                   # rad per (slowed) frame
    spread = 1.0
    def __init__(self, parts):
        rng = _rng(7); self.slot = {}; placed = []
        for pid in sorted(parts, key=lambda q: (-parts[q]["length"], parts[q]["leave"])):
            P = parts[pid]; th_t = math.atan2(P["target"].y, P["target"].x)
            r = 5.2 + 0.0042 * P["leave"]
            for tries in range(6000):
                spread = 0.5 + tries / 1500.0
                ph = th_t - self.OMEGA * spin_of(P["leave"]) + rng.uniform(-0.75 * spread, 0.35 * spread)
                z = rng.uniform(*P["zband"]); rr = r + rng.uniform(-0.15, 0.15) * (1 + tries / 2000.0)
                if "lane" in P:                                              # firring strips: a neat vertical ladder in front, one lane each,
                    z = P["lane"]; ph = -math.pi / 2 - self.OMEGA * spin_of(P["leave"]); rr = r + 0.6   # they peel off one by one
                pts = self._pts(rr, ph, z, P["length"])
                if all(np.min(np.linalg.norm(pts[:, None, :] - q[None, :, :], axis=2)) > P["size"] + rq + 0.06 for q, rq in placed): break
            placed.append((pts, P["size"])); self.slot[pid] = (ph, z, rr, rng.uniform(0, 1e3))
    @staticmethod
    def _pts(r, ph, z, length):
        c = np.array([r * math.cos(ph), r * math.sin(ph), z])
        if length <= 0: return c[None, :]
        t = np.array([-math.sin(ph), math.cos(ph), 0.0]); n = max(2, int(length / 0.15) + 1)
        return c[None, :] + t[None, :] * np.linspace(-length / 2, length / 2, n)[:, None]
    def pos(self, pid, s):
        ph, z, r, sd = self.slot[pid]; ang = ph + self.OMEGA * s
        return Vector((r * math.cos(ang), r * math.sin(ang), z + 0.06 * math.sin(0.02 * s + sd))), ang
    def vel(self, pid, s):
        p0, _ = self.pos(pid, s - 0.5); p1, _ = self.pos(pid, s + 0.5); return p1 - p0
    def rot(self, pid, s, q_final, long_axis_local):
        _, ang = self.pos(pid, s); ph, z, r, sd = self.slot[pid]
        if long_axis_local is not None:
            tang = Vector((-math.sin(ang), math.cos(ang), 0.0)); q_align = (q_final @ long_axis_local).rotation_difference(tang)
            return Quaternion(tang, 0.008 * s + sd) @ q_align @ q_final
        rng = _rng(int(sd)); axis = Vector(rng.normal(size=3)).normalized(); rate = rng.uniform(0.010, 0.022)
        return Quaternion(axis, rate * s + sd) @ q_final


def _bezier(p0, p1, p2, p3, u):
    v = 1 - u; return p0 * v ** 3 + p1 * 3 * v * v * u + p2 * 3 * v * u * u + p3 * u ** 3


class Anim:
    def __init__(self):
        bpy.context.view_layer.update()
        L = load_json("layout.json")
        self.objs = {}; self.center = {}; self.vloc = {}; self.long = {}; self.screw_part = {}
        for p in L["parts"]: self.objs[p["id"]] = bpy.data.objects[f"INST_{p['id']}"]
        for t in L["timber"]: self.objs[t["id"]] = bpy.data.objects[t["id"]]
        for o in bpy.data.collections["PERGOLA"].objects:
            if o.name.startswith(("WEDGE_", "SHEET_")): self.objs[o.name] = o
        self.S = schedule()
        mseat = {pid: S["seat"] for pid, S in self.S.items()}
        for i, fd in enumerate(L["fasteners"]):
            sid = f"SCREW_{i:03d}"; self.objs[sid] = bpy.data.objects[sid]
            part = fd["part"]; ax = Vector(fd["axis_to_timber"]).normalized(); self.screw_part[sid] = part
            j = i % 9
            if part.startswith("STOPA"):
                if fd["kind"] == "anchor": seat = mseat[part] + 10 + 1.6 * j
                else: seat = mseat["POST_" + part.split("_")[1]] + 14 + 1.6 * j
                if part == "STOPA_C1": seat += 6                       # after the macro
            elif part.startswith("TROJAK"): seat = GROUP_T["lift"][1] + 10 + 1.4 * j + (4 if part == "TROJAK_C1" else 0)
            elif abs(ax.z) < 0.5:                                        # plate -> beam side
                seat = mseat[part] + 8 + 2.2 * j if part == "MOCOW_L_0" else mseat[part] + 6 + 0.9 * j
            else:                                                         # from below into the rafter
                ri = int(part.split("_")[-1]); seat = mseat[f"RAFTER_{ri}"] + 6 + 0.8 * j
            app = seat - (11 if part == "MOCOW_L_0" else 7); self.S[sid] = dict(leave=app - 34, app=app, seat=seat, dir=ax, L=0.16, groups=(), spin=6 * math.pi)
        for pid, o in self.objs.items():
            o.rotation_mode = "QUATERNION"
            self.S[pid]["loc0"] = o.matrix_world.translation.copy(); self.S[pid]["q0"] = o.matrix_world.to_quaternion()
            self.center[pid] = self._center(o); q0 = self.S[pid]["q0"]
            self.vloc[pid] = q0.inverted() @ (self.center[pid] - self.S[pid]["loc0"]); self.long[pid] = None
            if pid.startswith(("BEAM", "RAFTER", "POST")):
                tb = next(t for t in L["timber"] if t["id"] == pid); ax = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[tb["long_axis"]]
                self.long[pid] = q0.inverted() @ Vector(ax)
            if pid.startswith(("WEDGE", "SHEET")): self.long[pid] = q0.inverted() @ Vector((1, 0, 0))
        vp = {}
        for pid in self.objs:
            S = self.S[pid]; lo, hi = self._bbox(self.objs[pid]); ext = np.array(hi) - np.array(lo)
            length = float(ext.max()) if self.long[pid] is not None else 0.0
            size = float(np.sort(ext)[1] / 2 * 1.45) if length else float(np.linalg.norm(ext) / 2)
            if pid.startswith("SHEET"): size = float(np.sort(ext)[1] / 2)
            if pid.startswith("SCREW") and self.screw_part[pid].startswith("MOCOW"): zb = (0.5, 1.9)
            elif pid.startswith(("BEAM", "SHEET")): zb = (3.3, 4.4)
            else: zb = (0.45, 3.3)
            vp[pid] = dict(leave=S["leave"], target=self.center[pid], size=size, length=length, zband=zb)

        self.V = Vortex(vp)
        rp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assembly_routes.json")
        self.route = {k: tuple(v) for k, v in json.load(open(rp)).items()} if os.path.exists(rp) else {}

    @staticmethod
    def _bbox(obj):
        pts = []; st = [obj]
        while st:
            o = st.pop(); st += list(o.children)
            if o.type == "MESH": pts += [o.matrix_world @ Vector(c) for c in o.bound_box]
        a = np.array([list(p) for p in pts]); return a.min(0).tolist(), a.max(0).tolist()
    def _center(self, obj):
        lo, hi = self._bbox(obj); return Vector(((np.array(lo) + np.array(hi)) / 2).tolist())

    def pose(self, pid, a, s=None):
        if s is None: s = spin_of(a)
        S = self.S[pid]; q0 = S["q0"]; c0 = self.center[pid]
        if pid.startswith("WEDGE") or (pid.startswith("RAFTER") and pid != "RAFTER_0"):   # rigid comb from high above, then sets down straight
            if a >= S["seat"]: return c0, q0, 0.0
            if a >= S["app"]:
                u = (a - S["app"]) / (S["seat"] - S["app"]); return c0 + Vector((0, 0, S["L"] * (1 - e_seat(u)))), q0, 1.0
            u = clamp01((a - S["leave"]) / (S["app"] - S["leave"]))
            park = 12.0 if pid.startswith("WEDGE") else 8.5                # the strip comb waits above the rafter comb
            return c0 + Vector((0, 0, S["L"] + park * (1 - e_io5(u)))), q0, 1.0
        base = c0 + group_offset(S["groups"], a); d = S["dir"]; L = S["L"]
        if a >= S["seat"]: return base, q0, 0.0
        if d is not None and a >= S["app"]:
            u = (a - S["app"]) / max(1e-6, S["seat"] - S["app"]); k = 1 - e_seat(u); return base - d * L * k, q0, k
        A = (c0 + group_offset(S["groups"], S["app"])) - (d * L if d is not None else Vector((0, 0, 0)))
        if a < S["leave"]:
            P, _ = self.V.pos(pid, s); return P, self.V.rot(pid, s, q0, self.long[pid]), 1.0
        u = (a - S["leave"]) / max(1e-6, S["app"] - S["leave"]); T = S["app"] - S["leave"]
        s_l = spin_of(S["leave"]); P0, _ = self.V.pos(pid, s_l); v0 = self.V.vel(pid, s_l) * _speed(S["leave"])
        k_out, dz, s_end, lat = self.route.get(pid, (0.5, 0.0, 0.8, 0.0))
        side = Vector((-A.y, A.x, 0.0)).normalized() * lat if (A.x or A.y) else Vector((0, 0, 0))
        if pid.startswith("SCREW"):
            P1 = P0 + v0 * (T / 3.0) + Vector((0, 0, dz * 0.6)) + side * 0.6
            if self.screw_part[pid].startswith("MOCOW"): P1.z = min(P1.z, 2.0)
            P2 = A - d * k_out + Vector((0, 0, dz)) + side
        else:
            app_v = (d * L / max(1e-6, S["seat"] - S["app"]) * 2.2) if d is not None else Vector((0, 0, -0.012))
            up = Vector((0, 0, max(0.0, 3.4 - A.z) + 0.6)) if (abs(A.x) < 2.1 and abs(A.y) < 3.3 and not pid.startswith(("WEDGE", "SHEET"))) else Vector((0, 0, 0.3))
            up = up + Vector((0, 0, dz))
            P1 = P0 + v0 * (T / 3.0) + up * 0.6 + side * 0.6 + Vector((0, 0, 0.5))
            if pid.startswith(("WEDGE", "SHEET")):                     # thin long strips peel OUT of the ring first (no brushing past neighbours)
                rad = Vector((P0.x, P0.y, 0.0)).normalized(); P1 = P1 + rad * 1.2 + Vector((0, 0, 0.6))
            if pid.startswith("RAFTER"):                               # rafters slide straight out of their ring level, height comes later
                rad = Vector((P0.x, P0.y, 0.0)).normalized(); P1 = P0 + v0 * (T / 3.0) + rad * 1.6 + side * 0.6
            P2 = A - app_v * (T / 3.0) + up + side
        P = _bezier(P0, P1, P2, A, e_io(u) * 0.5 + u * 0.5)
        Qv = self.V.rot(pid, s_l, q0, self.long[pid])
        Q = Qv.slerp(q0, e_io(clamp01((u - 0.18) / max(0.05, s_end - 0.18))))      # first lift clear of the ring, then turn
        return P, Q, 1.0

    def place(self, pid, P, Q, spin_k=0.0):
        o = self.objs[pid]; S = self.S[pid]
        if S.get("spin") and spin_k > 0: Q = Q @ Quaternion((0, 0, 1), S["spin"] * spin_k)
        o.rotation_quaternion = Q; o.location = P - Q @ self.vloc[pid]; o.hide_render = False; o.hide_viewport = False

    def set_clock(self, a, s=None):
        for pid in self.objs:
            P, Q, k = self.pose(pid, a, s); self.place(pid, P, Q, k if self.S[pid].get("spin") else 0.0)

    def apply(self, f):
        self.set_clock(float(min(f, F_ASM_END)), spin_of(min(f, F_ASM_END)))


def env_for_frame(f): return "lab"


# ----------------------------------------------------------------------------------------------- one calm camera take
LOGO_CAM = (tuple(LOGO_C1[0] + LOGO_C1[1] * 0.64), tuple(LOGO_C1[0]), 70.0)
KEYS = [  # (frame, loc, target, lens, f-stop)  - smoothed afterwards; speeds verified <= ~0.05 m/frame, turns <= ~0.7 deg/frame
    (0,   (3.6, -8.8, 3.3),    (-0.2, -0.6, 1.9),    26, 5.6),     # the vortex, slow descent
    (60,  (2.4, -7.4, 2.0),    (-1.0, -2.2, 0.9),    32, 5.0),
    (128, (-0.6, -4.95, 0.62), (-1.70, -2.98, 0.30), 70, 3.2),     # macro 1: post C1 slides into its Stopa
    (196, (-0.8, -4.55, 0.55), (-1.70, -2.98, 0.30), 85, 3.2),
    (250, (-0.4, -4.85, 2.6),  (-1.70, -2.95, 3.2),  55, 4.0),     # crane up along the post
    (300, (-0.75, -4.25, 4.35), (-1.70, -2.85, 4.12), 70, 3.2),    # macro 2: Trojak C1 slides onto the long beam end
    (346, (-0.60, -4.05, 4.30), (-1.62, -2.90, 4.14), 75, 3.2),
    (400, (-0.35, -4.10, 4.05), (-1.45, -2.92, 4.12), 75, 3.2),    # macro 3: end beam enters C1 and butts against the long beam
    (428, (-0.40, -4.15, 4.00), (-1.55, -2.93, 4.10), 75, 3.2),
    (506, (-0.55, -4.15, 2.30), (-1.62, -2.92, 2.50), 70, 3.2),    # ...descending with the frame onto post C1
    (546, (-0.55, -3.30, 2.10), (-1.62, -2.42, 2.52), 75, 3.2),    # macro 4: Mocowanie belek 2 + wood screws into the beam side
    (592, (-0.70, -3.20, 2.20), (-1.62, -2.42, 2.55), 80, 3.2),
    (626, (-0.75, -3.55, 2.25), (-1.62, -2.42, 2.60), 65, 3.2),    # macro 5: rafter drops into the Mocowanie (seen from below-front)
    (700, (0.9, -5.8, 3.7),    (0.0, -0.2, 2.7),     32, 5.0),     # roof: firring strips, sheets (grooves along rafters, one side high)
    (740, (0.9, -5.5, 3.3),    (-1.2, -2.4, 2.6),    34, 5.0),
    (768, (0.6, -4.4, 2.05),   (-1.65, -2.75, 2.5),  42, 4.0),     # glide in under the end beam...
    (790, (0.25, -3.12, 2.18), (-1.65, -2.75, 2.53), 52, 3.6),
    (806, (-0.30, -2.78, 2.45), (-1.65, -2.75, 2.55), 62, 3.2),
    (822, LOGO_CAM[0],         LOGO_CAM[1],          70, 3.0),     # ...face-on to the RIVON mark on Trojak C1 (inside the pergola)
    (899, LOGO_CAM[0],         LOGO_CAM[1],          70, 3.0),
]


def _hermite_path(keys, idx, frames):
    ts = np.array([k[0] for k in keys], float); P = np.array([np.atleast_1d(np.array(k[idx], float)) for k in keys])
    n = len(ts); M = np.zeros_like(P)
    for i in range(n):                                              # monotone-ish tangents (finite differences, zero at ends/holds)
        if i == 0 or i == n - 1: continue
        M[i] = (P[i + 1] - P[i - 1]) / (ts[i + 1] - ts[i - 1])
        if np.allclose(P[i + 1], P[i]) or np.allclose(P[i - 1], P[i]): M[i] = 0
    out = []
    for f in frames:
        i = int(np.clip(np.searchsorted(ts, f, side="right") - 1, 0, n - 2)); h = ts[i + 1] - ts[i]; u = (f - ts[i]) / h
        h00 = 2 * u ** 3 - 3 * u ** 2 + 1; h10 = u ** 3 - 2 * u ** 2 + u; h01 = -2 * u ** 3 + 3 * u ** 2; h11 = u ** 3 - u ** 2
        out.append(h00 * P[i] + h10 * h * M[i] + h01 * P[i + 1] + h11 * h * M[i + 1])
    return np.array(out)


def _smooth(x, sigma):
    """gaussian smoothing along frames (numpy only - Blender ships without scipy), edges held."""
    r = int(3 * sigma); k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2); k /= k.sum()
    x2 = np.atleast_2d(x.T).T if x.ndim == 1 else x
    pad = np.concatenate([np.repeat(x2[:1], r, 0), x2, np.repeat(x2[-1:], r, 0)], 0)
    out = np.stack([np.convolve(pad[:, j], k, mode="valid") for j in range(x2.shape[1])], 1)
    return out.reshape(x.shape)


_FR = np.arange(0, NF)
_CL = _smooth(_hermite_path(KEYS, 1, _FR), 11.0); _CT = _smooth(_hermite_path(KEYS, 2, _FR), 14.0)
_CN = _smooth(_hermite_path(KEYS, 3, _FR), 9.0)[:, 0]; _CF = _smooth(_hermite_path(KEYS, 4, _FR), 9.0)[:, 0]
_HOLD = 822                                                    # exact face-on hold for the logo end card (no smoothing drift)
_CL[_HOLD:] = np.array(LOGO_CAM[0]); _CT[_HOLD:] = np.array(LOGO_CAM[1]); _CN[_HOLD:] = 70.0; _CF[_HOLD:] = 3.0
_bl = np.array([e_io(clamp01((f - (_HOLD - 24)) / 24.0)) for f in _FR])[:, None]
_CL = _CL * (1 - _bl) + np.array(LOGO_CAM[0]) * _bl; _CT = _CT * (1 - _bl) + np.array(LOGO_CAM[1]) * _bl


def camera_for_frame(f):
    f = int(min(max(f, 0), NF - 1)); return tuple(_CL[f]), tuple(_CT[f]), float(_CN[f]), float(_CF[f])


def light_rig(f):
    """soft key that rides with the camera in the macros (so close-ups stay readable in the dark hall); energy follows distance^2."""
    loc, tgt, lens, fs = camera_for_frame(f); c = Vector(loc); t = Vector(tgt); d = (t - c)
    fwd = d.normalized(); right = fwd.cross(Vector((0, 0, 1))).normalized(); up = right.cross(fwd)
    macro = clamp01((lens - 40.0) / 25.0); dl = d.length
    p = c + up * min(0.55, 0.25 * dl) - right * min(0.45, 0.4 * dl)
    return [("cam_key", tuple(p), tuple(t), 260.0 * dl ** 2 * macro, min(0.9, 0.5 * dl))]
