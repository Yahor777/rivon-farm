"""RIVON film v6 - 30 s @ 30 fps = 900 frames, 9:16.  ONE camera move: a steady orbit around the pergola for the whole film.

   0 - 540  lab: the parts DANCE in ordered rings around the pergola (each part type its own ring, rings turn smoothly in
            alternating directions with a travelling wave in height) and peel off in symmetric groups into a realistic assembly
 548 - 628  transition (post): a glowing ring expands across the floor from the pergola; behind it the lab becomes a private
            house yard with the black RAM parked under the pergola.  Frames 1548..1627 = the YARD version of frames 548..627.
 628 - 899  yard, same orbit continues; end card in post.

Owner rules: pointed wood screws along their own axes into the real holes; long beam to the Trojak corner wall, end beam butts
against it (fills the upper socket); roof sheets with grooves along the rafters, one long side higher (firring strips).
Assembly order (plan_assembly.py: every straight move verified on the STEP meshes):
  feet -> posts into feet -> long beams -> Trojaks slide onto the long-beam ends -> end beams into the right unit -> right unit
  slides in -> frame lowered onto the posts -> Mocowanie belek 2 + screws -> rafters -> screws -> firring strips -> sheets.
All transforms rigid; nothing is scaled or edited."""
import math, json, os
import numpy as np
import bpy, mathutils
from mathutils import Matrix, Vector, Quaternion
from film_lib import load_json

FPS, NF = 30, 900
LAB1 = (0, 899); SCENES = []; SCENE_LEN = 0; LAB2 = (900, 900)
F_ASM_END = 540
T_SWITCH0, T_SWITCH1 = 548, 628        # transition window (both environments rendered)
YARD_OFFSET = 1000                     # frame 1000+f = yard render of frame f
LIFT, JOIN = 1.6, 2.0
GROUP_T = {"join": (262.0, 300.0), "lift": (302.0, 352.0)}
SLOWMO = []


def clamp01(x): return max(0.0, min(1.0, x))
def e_io(u): return u * u * (3 - 2 * u)
def e_io5(u): return u * u * u * (u * (6 * u - 15) + 10)
def e_seat(u): return 1 - (1 - u) ** 2.2
def _speed(f): return 1.0
def spin_of(f): return float(f)
def clock_of_frame(f): return float(f)
def frame_of_clock(a): return float(a)
def disassembly_clock(f): return float(f)
def bearing(v): return math.atan2(v.y, v.x)


# ----------------------------------------------------------------------------------------------- the dance: ordered rings
# ring: radius, height, angular speed (rad/frame), orientation mode
RINGS = {
    "STOPA":  dict(r=4.3, z=0.45, w=+0.0105, mode="face"),
    "POST":   dict(r=5.0, z=1.30, w=-0.0085, mode="face"),
    "TROJAK": dict(r=5.7, z=3.05, w=+0.0095, mode="face"),
    "BEAM":   dict(r=7.7, z=4.45, w=+0.0060, mode="tangent"),
    "MOCOW":  dict(r=6.4, z=1.95, w=-0.0100, mode="face"),
    "SCREW":  dict(r=7.2, z=0.0,  w=+0.0070, mode="flock"),
}
WAVE_A, WAVE_NU, WAVE_K = 0.18, 0.045, 2          # travelling height wave: amplitude, speed, crests per ring


def ring_of(pid):
    for k in RINGS:
        if pid.startswith(k): return k
    return None


# ----------------------------------------------------------------------------------------------- schedule (film frames)
def schedule():
    S = {}
    def put(pid, leave, app, seat, d, L, groups=()):
        S[pid] = dict(leave=leave, app=app, seat=seat, dir=None if d is None else Vector(d), L=L, groups=tuple(groups))
    D = (0, 0, -1)
    for k in (1, 2, 3, 4): put(f"STOPA_C{k}", 58, 92, 108, D, 0.7)                 # the four feet together
    for k in (1, 2, 3, 4): put(f"POST_C{k}", 100, 140, 162, D, 1.0)                # the four posts together
    F = ("lift",); R = ("lift", "join")
    put("BEAM_LONG_L", 150, 200, 200, None, 0.0, F); put("BEAM_LONG_R", 150, 200, 200, None, 0.0, R)
    put("TROJAK_C1", 176, 214, 234, (0, 1, 0), 0.6, F); put("TROJAK_C4", 176, 214, 234, (0, -1, 0), 0.6, F)
    put("TROJAK_C2", 176, 214, 234, (0, 1, 0), 0.6, R); put("TROJAK_C3", 176, 214, 234, (0, -1, 0), 0.6, R)
    put("BEAM_END_A", 200, 238, 258, (1, 0, 0), 0.9, R); put("BEAM_END_B", 200, 238, 258, (1, 0, 0), 0.9, R)
    for i in range(11):                                                               # Mocowanie: symmetric L/R pairs, centre outwards
        k = sorted(range(11), key=lambda j: abs(j - 5))[i] if False else i
        for s in ("L", "R"):
            a = 352 + 4.0 * i; put(f"MOCOW_{s}_{i}", a - 34, a, a + 14, D, 0.5)
    for i in range(11): put(f"RAFTER_{i}", 398, 438, 456, D, 0.9)                   # all rafters lowered together into their hangers
    for j in range(13): put(f"WEDGE_{j:02d}", 446, 478, 492, D, 0.5)                # firring strips as one comb
    for j in range(6): a = 494 + 7.0 * j; put(f"SHEET_{j}", a - 34, a, a + 12, D, 0.5)   # sheets one after another
    return S


def group_offset(groups, a):
    o = Vector((0, 0, 0))
    if "join" in groups:
        t0, t1 = GROUP_T["join"]; o += Vector((JOIN, 0, 0)) * (1 - e_seat(e_io(clamp01((a - t0) / (t1 - t0))) ** 0.8))
    if "lift" in groups:
        t0, t1 = GROUP_T["lift"]; o += Vector((0, 0, LIFT)) * (1 - e_io5(clamp01((a - t0) / (t1 - t0))))
    return o


class Dance:
    """explicit, ordered slots.  phase is chosen so every part passes its own target bearing exactly when it leaves the ring,
    which makes the groups peel off symmetrically and fly straight in (no criss-crossing)."""
    def __init__(self, anim):
        self.slot = {}; A = anim
        lanes = {"STOPA": 0.0, "TROJAK": 0.0, "MOCOW": 0.0, "RAFTER": 0.0}
        cnt = {}
        for pid, S in A.S.items():
            rk = ring_of(pid)
            if rk is None: continue
            R = RINGS[rk]; tgt = A.center[pid] + group_offset(S["groups"], S["app"])
            ph = bearing(tgt) - R["w"] * S["leave"]
            r, z = R["r"], R["z"]
            if rk == "SCREW":                                    # screws: short tidy columns per connector, each group its own lane
                part = A.screw_part[pid]; key = part
                n = cnt.get(key, 0); cnt[key] = n + 1
                g = part.split("_")[0]
                if part.startswith("MOCOW") and abs(S["dir"].z) > 0.5: g = "RAFTER"
                base = {"STOPA": (0.55, 6.9), "TROJAK": (2.35, 7.2), "MOCOW": (1.05, 7.5), "RAFTER": (3.15, 7.8)}[g]
                z = base[0] + 0.105 * n; r = base[1]
                ph += 0.012 * (n % 2)                            # tiny stagger, reads as a braided column
            self.slot[pid] = (ph, r, z, rk)
    def pos(self, pid, f):
        ph, r, z, rk = self.slot[pid]; w = RINGS[rk]["w"]; ang = ph + w * f
        dz = WAVE_A * math.sin(WAVE_NU * f - WAVE_K * ang)
        return Vector((r * math.cos(ang), r * math.sin(ang), z + dz)), ang
    def vel(self, pid, f):
        p0, _ = self.pos(pid, f - 0.5); p1, _ = self.pos(pid, f + 0.5); return p1 - p0
    def rot(self, pid, f, q0, long_local):
        ph, r, z, rk = self.slot[pid]; _, ang = self.pos(pid, f); mode = RINGS[rk]["mode"]
        if mode == "face":                                       # keeps its final upright pose, turned to always face the centre
            return Quaternion((0, 0, 1), ang - ph) @ q0
        if mode == "tangent":                                    # timbers ride along the ring, long axis tangential, level
            tang = Vector((-math.sin(ang), math.cos(ang), 0.0)); return (q0 @ long_local).rotation_difference(tang) @ q0
        # flock: screw axis (local +Z) along the direction of travel, like a school of fish
        w = RINGS[rk]["w"]; tang = Vector((-math.sin(ang), math.cos(ang), 0.0)) * (1 if w > 0 else -1)
        return (q0 @ Vector((0, 0, 1))).rotation_difference(tang) @ q0


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
        self.S = schedule(); mseat = {pid: S["seat"] for pid, S in self.S.items()}
        cnt = {}
        for i, fd in enumerate(L["fasteners"]):
            sid = f"SCREW_{i:03d}"; self.objs[sid] = bpy.data.objects[sid]
            part = fd["part"]; ax = Vector(fd["axis_to_timber"]).normalized(); self.screw_part[sid] = part
            j = cnt.get(part, 0); cnt[part] = j + 1
            if part.startswith("STOPA"):
                seat = (mseat[part] + 8 if fd["kind"] == "anchor" else mseat["POST_" + part.split("_")[1]] + 10) + 2.0 * (j % 4)
            elif part.startswith("TROJAK"): seat = GROUP_T["lift"][1] + 8 + 2.0 * j
            elif abs(ax.z) < 0.5: seat = mseat[part] + 6 + 1.5 * j
            else:
                ri = int(part.split("_")[-1]); seat = mseat[f"RAFTER_{ri}"] + 6 + 1.5 * j
            app = seat - 8; self.S[sid] = dict(leave=app - 30, app=app, seat=seat, dir=ax, L=0.16, groups=(), spin=6 * math.pi)
        for pid, o in self.objs.items():
            o.rotation_mode = "QUATERNION"
            self.S[pid]["loc0"] = o.matrix_world.translation.copy(); self.S[pid]["q0"] = o.matrix_world.to_quaternion()
            self.center[pid] = self._center(o); q0 = self.S[pid]["q0"]
            self.vloc[pid] = q0.inverted() @ (self.center[pid] - self.S[pid]["loc0"]); self.long[pid] = None
            if pid.startswith(("BEAM", "RAFTER", "POST")):
                tb = next(t for t in L["timber"] if t["id"] == pid); ax = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[tb["long_axis"]]
                self.long[pid] = q0.inverted() @ Vector(ax)
            if pid.startswith(("WEDGE", "SHEET")): self.long[pid] = q0.inverted() @ Vector((1, 0, 0))
        self.V = Dance(self)
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
        S = self.S[pid]; q0 = S["q0"]; c0 = self.center[pid]
        if pid.startswith(("WEDGE", "RAFTER", "SHEET")):         # from high above, straight down, level (combs / one sheet at a time)
            if a >= S["seat"]: return c0, q0, 0.0
            if a >= S["app"]:
                u = (a - S["app"]) / (S["seat"] - S["app"]); return c0 + Vector((0, 0, S["L"] * (1 - e_seat(u)))), q0, 1.0
            u = clamp01((a - S["leave"]) / (S["app"] - S["leave"]))
            park = {"WEDGE": 12.0, "RAFTER": 9.0, "SHEET": 16.0}[pid.split("_")[0]]          # sheets wait above the strip comb
            return c0 + Vector((0, 0, S["L"] + park * (1 - e_io5(u)))), q0, 1.0
        base = c0 + group_offset(S["groups"], a); d = S["dir"]; L = S["L"]
        if a >= S["seat"]: return base, q0, 0.0
        if d is not None and a >= S["app"]:
            u = (a - S["app"]) / max(1e-6, S["seat"] - S["app"]); k = 1 - e_seat(u); return base - d * L * k, q0, k
        A = (c0 + group_offset(S["groups"], S["app"])) - (d * L if d is not None else Vector((0, 0, 0)))
        if a < S["leave"]:
            P, _ = self.V.pos(pid, a); return P, self.V.rot(pid, a, q0, self.long[pid]), 1.0
        u = (a - S["leave"]) / max(1e-6, S["app"] - S["leave"]); T = S["app"] - S["leave"]
        P0, _ = self.V.pos(pid, S["leave"]); v0 = self.V.vel(pid, S["leave"])
        k_out, dz, s_end, lat = self.route.get(pid, (0.5, 0.0, 0.8, 0.0))
        side = Vector((-A.y, A.x, 0.0)).normalized() * lat if (A.x or A.y) else Vector((0, 0, 0))
        if pid.startswith("SCREW"):
            P1 = P0 + v0 * (T / 3.0) + Vector((0, 0, dz * 0.6)) + side * 0.6
            P2 = A - d * k_out + Vector((0, 0, dz)) + side
        else:
            app_v = (d * L / max(1e-6, S["seat"] - S["app"]) * 2.2) if d is not None else Vector((0, 0, -0.01))
            up = Vector((0, 0, dz))
            P1 = P0 + v0 * (T / 3.0) + up * 0.6 + side * 0.6
            P2 = A - app_v * (T / 3.0) + up + side
        P = _bezier(P0, P1, P2, A, e_io(u) * 0.5 + u * 0.5)
        Qv = self.V.rot(pid, S["leave"], q0, self.long[pid])
        Q = Qv.slerp(q0, e_io(clamp01((u - 0.1) / max(0.05, s_end - 0.1))))
        return P, Q, 1.0

    def place(self, pid, P, Q, spin_k=0.0):
        o = self.objs[pid]; S = self.S[pid]
        if S.get("spin") and spin_k > 0: Q = Q @ Quaternion((0, 0, 1), S["spin"] * spin_k)
        o.rotation_quaternion = Q; o.location = P - Q @ self.vloc[pid]; o.hide_render = False; o.hide_viewport = False

    def set_clock(self, a, s=None):
        for pid in self.objs:
            P, Q, k = self.pose(pid, a, s); self.place(pid, P, Q, k if self.S[pid].get("spin") else 0.0)

    def apply(self, f):
        f = f - YARD_OFFSET if f >= YARD_OFFSET else f
        self.set_clock(float(min(f, F_ASM_END)))


def env_for_frame(f):
    if f >= YARD_OFFSET: return "yard"
    return "lab" if f < T_SWITCH1 else "yard"


# ----------------------------------------------------------------------------------------------- the orbit
ORBIT_R, ORBIT_TURNS, ORBIT_A0 = 10.8, 1.0, math.radians(-62.0)
def camera_for_frame(f):
    f = f - YARD_OFFSET if f >= YARD_OFFSET else f
    t = f / (NF - 1)
    a = ORBIT_A0 + 2 * math.pi * ORBIT_TURNS * t                       # constant angular speed: one turn in 30 s
    r = ORBIT_R - 0.5 * math.sin(math.pi * t)                         # breathes in a little mid-film
    h = 5.6 + 0.5 * math.sin(2 * math.pi * t - 0.6)                   # high 3/4 view: the rings read as circles around the pergola
    tz = 1.3 + 0.3 * math.sin(math.pi * t)
    return (r * math.cos(a), r * math.sin(a), h), (0.0, 0.0, tz), 27.0, 5.6


def light_rig(f): return []
