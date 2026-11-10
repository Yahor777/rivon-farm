"""RIVON lab film sound v5 (lab only, one take; events from export_events.py) - built from REAL recordings instead of synthesised noise (no hiss):
  impacts  : Kenney "Impact Sounds" (CC0)  - wood heavy/medium/plank for timber, metal/plate for the steel connectors
  ambience : Moodist library (Pixabay Content License / CC0) - birds, wind in trees, road, campfire, river, crowd, street
  no musical / tonal sounds at all (no chimes, bells, bowls; cafe recordings with background music were dropped)
The sound files are NOT stored in this public repo (third-party licences forbid standalone redistribution); pass their folder:
usage: python3 sound_film3.py events.json out.wav --sfx /home/claude/sfx [--dur 30]"""
import sys, os, json, wave, subprocess, argparse, numpy as np
from scipy.signal import butter, sosfilt, fftconvolve, resample
ap = argparse.ArgumentParser(); ap.add_argument("events"); ap.add_argument("out"); ap.add_argument("--sfx", required=True); ap.add_argument("--dur", type=float, default=30.0)
A = ap.parse_args()
SR = 44100; FPS = 30; N = int(SR * A.dur); T = np.arange(N) / SR
rng = np.random.default_rng(5)
KEN = os.path.join(A.sfx, "kenney", "addons", "kenney impact sounds"); MOO = os.path.join(A.sfx, "moodist", "public", "sounds")
ev = json.load(open(A.events))

def lp(x, f, o=2): return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x, axis=0)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x, axis=0)
def load(path, start=0.0, dur=None):
    cmd = ["ffmpeg", "-v", "error", "-ss", str(start)] + (["-t", str(dur)] if dur else []) + ["-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout; return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)
def rms(x): return float(np.sqrt((x ** 2).mean()) + 1e-12)
def db(v): return 10 ** (v / 20.0)
MIX = np.zeros((N, 2)); SEND = {"lab": np.zeros((N, 2)), "out": np.zeros((N, 2))}
def in_lab(t): return True

# ------------------------------------------------------------------------------------------------ one-shots (Kenney CC0)
_cache = {}
RPG = os.path.join(A.sfx, "rpg")
# hand-picked, measured NON-tonal hits only (no ringing / no pitched "notes"): dull wood, dead metal clanks
PICK = {
    "wood_dull": ["impact_wood_heavy_000", "impact_wood_heavy_001", "impact_wood_heavy_002", "impact_wood_heavy_004"],
    "plank":     ["impact_plank_medium_000", "impact_plank_medium_003", "impact_plank_medium_004"],
    "metal":     ["impact_metal_heavy_002", "impact_metal_heavy_004", "impact_metal_medium_001", "impact_metal_medium_004"],
    "metal_sm":  ["impact_plate_light_000", "impact_plate_light_001", "impact_plate_light_003"],
    "click":     ["metal_latch", "metal_click"],
    "thud":      ["impact_soft_heavy_003", "impact_soft_heavy_001"],
    "soft":      ["impact_soft_medium_000", "impact_soft_medium_002"],
    "chop":      ["chop", "knife_slice"],
}
def _find(name):
    for root in (KEN, RPG):
        for dp, _, fs in os.walk(root):
            if name + ".ogg" in fs: return os.path.join(dp, name + ".ogg")
    raise FileNotFoundError(name)
def shot(kind):
    names = PICK[kind]; f = names[rng.integers(len(names))]
    if f not in _cache:
        x = load(_find(f)); x = x / (np.abs(x).max() + 1e-9); _cache[f] = x
    return _cache[f]
def place(x, t, gain_db, pan=0.0, pitch=1.0, wet=0.2, space=None):
    if pitch != 1.0: x = resample(x, max(8, int(len(x) / pitch)), axis=0)
    i = int(t * SR)
    if i < 0 or i >= N: return
    n = min(len(x), N - i); g = db(gain_db)
    l = np.sqrt(0.5 * (1 - pan)); r = np.sqrt(0.5 * (1 + pan))
    y = x[:n] * g; y = np.stack([y[:, 0] * l * 1.414, y[:, 1] * r * 1.414], 1)
    MIX[i:i + n] += y
    SEND[space or ("lab" if in_lab(t) else "out")][i:i + n] += y * wet
def hit(kind, t, gain_db, pan=0.0, spread=0.06, wet=0.2): place(shot(kind), t, gain_db, pan, rng.uniform(1 - spread, 1 + spread), wet)

# ------------------------------------------------------------------------------------------------ beds (Moodist, real recordings)
def bed(rel, a, b, level_db, start=6.0, fade=0.45, lowcut=None, highcut=None):
    """recording looped/cut to [a,b] seconds, normalised to an RMS level, soft edges."""
    d = b - a + 2 * fade; x = load(os.path.join(MOO, rel), start, d + 0.5)[: int(d * SR)]
    if lowcut: x = hp(x, lowcut)
    if highcut: x = lp(x, highcut)
    x = x / rms(x) * db(level_db)
    i0 = int((a - fade) * SR); n = len(x); t = np.arange(n) / SR
    w = np.clip(t / (2 * fade), 0, 1) * np.clip((d - t) / (2 * fade), 0, 1); w = (w * w * (3 - 2 * w))[:, None]
    j0 = max(0, i0); k0 = j0 - i0; m = min(n - k0, N - j0)
    MIX[j0:j0 + m] += (x * w)[k0:k0 + m]

# lab: quiet low room tone only (no hiss): very low-passed brown noise + the faint lab recording, darkened
def lab_tone(a, b, lvl):
    n = int((b - a) * SR); y = np.cumsum(rng.normal(size=(n, 2)), 0); y = hp(y, 25, 1); y = lp(y, 140, 4); y = y / rms(y) * db(lvl)
    w = np.clip(np.arange(n) / (0.5 * SR), 0, 1) * np.clip((n - np.arange(n)) / (0.5 * SR), 0, 1)
    MIX[int(a * SR):int(a * SR) + n] += y * w[:, None]
lab_tone(0.0, A.dur, -38)

# ------------------------------------------------------------------------------------------------ assembly / disassembly foley
def air(d, rise=True):
    n = int(d * SR); x = rng.normal(size=(n, 2)); x = np.cumsum(x, 0); x = hp(x, 40, 1)
    t = np.arange(n) / n; out = np.zeros_like(x)
    for k in range(6):                                                          # sweeping low-pass, never above ~1.5 kHz
        c = 150 * (10 ** (((k + 0.5) / 6) if rise else (1 - (k + 0.5) / 6))) ; seg = lp(x, min(c, 1500), 2)
        w = np.exp(-((t - (k + 0.5) / 6) / 0.2) ** 2)[:, None]; out += seg * w
    env = (np.sin(np.pi * t) ** 1.6)[:, None]; out = out * env; return out / (np.abs(out).max() + 1e-9)
SLOW = next(e for e in ev if e["kind"] == "SLOWMO")["windows"]
def pan_of(pid):
    if pid.endswith(("_L", "L")) or "_L_" in pid or pid.endswith(("C1", "C4")): return -0.4
    if pid.endswith(("_R", "R")) or "_R_" in pid or pid.endswith(("C2", "C3")): return 0.4
    return rng.uniform(-0.3, 0.3)
def foley(kind, t, g, p, slow):
    pitch = 0.72 if slow else 1.0; wet = 0.55 if slow else 0.3; gg = g + (2.0 if slow else 0.0)
    def h(k, dt, db_, w=wet): place(shot(k), t + dt, db_ + gg, p, pitch * rng.uniform(0.96, 1.04), w)
    if kind == "STOPA": h("metal", 0, -15); h("thud", 0, -18, 0.1)
    elif kind == "POST": h("wood_dull", 0, -9)
    elif kind == "TROJAK": h("metal", 0, -14); h("thud", 0.01, -20, 0.1)
    elif kind == "BEAM": h("wood_dull", 0, -10); h("metal", 0.02, -20)
    elif kind == "JOIN": h("wood_dull", 0, -8); h("metal", 0.015, -15); h("thud", 0, -14, 0.1)
    elif kind == "LOWER": h("thud", 0, -9, 0.2); h("metal", 0.01, -12); h("wood_dull", 0.02, -10)
    elif kind == "MOCOW": h("metal_sm", 0, -22)
    elif kind == "RAFTER": h("plank", 0, -13)
    elif kind.startswith("SCREW"): h("click", 0, -32)
    elif kind == "WEDGE": h("plank", 0, -18)
    elif kind == "SHEET": h("thud", 0, -12, 0.3); h("metal_sm", 0.01, -18)
for e in ev:
    if e["kind"] in ("CUT", "SLOWMO"): continue
    t = e["f"] / FPS
    if e["kind"].startswith("SCREW") and rng.random() < (0.35 if not e["off"] else 0.8): continue      # not every one of 196 screws
    foley(e["kind"], t, -3.0 if e["off"] else 0.0, pan_of(e["id"]), e["slow"] and not e["off"])
# slow motion: the room breathes in (low air swell, no hiss) as time slows, and out again
for w0, w1 in SLOW:
    d = (w1 - w0) / FPS + 0.6; place(air(d, True) * 0.7, w0 / FPS - 0.3, -24, 0.0, 1.0, 0.4, "lab")

# ------------------------------------------------------------------------------------------------ transitions: soft low air-whoosh + felt thump (no hiss)
# ------------------------------------------------------------------------------------------------ end card
place(air(1.4, False), 830 / FPS, -22, 0.0, 1.0, 0.3, "lab")                  # darkening: low air falls away (no tones)
hit("thud", 864 / FPS, -15, 0.0, 0.0, 0.3)                                   # CTA

# ------------------------------------------------------------------------------------------------ reverb (dark, natural), master
def ir(rt, cut):
    n = int(SR * rt * 1.2); t = np.arange(n) / SR; x = rng.normal(size=(n, 2)) * np.exp(-6.91 * t / rt)[:, None]; x = lp(x, cut, 2); x[: int(0.012 * SR)] = 0
    return x / np.sqrt((x ** 2).sum(0, keepdims=True))
for key, (rt, cut) in (("lab", (1.5, 3200)), ("out", (0.35, 4000))):
    h = ir(rt, cut)
    for c in range(2): MIX[:, c] += fftconvolve(SEND[key][:, c], h[:, c])[:N]
MIX = hp(MIX, 30, 2)
g = np.clip((A.dur - T) / 0.9, 0, 1) * np.clip(T / 0.05, 0, 1); MIX *= g[:, None]
# transparent peak limiter (5 ms look-around max, 80 ms release) then level the whole track to about -20 dBFS RMS
from scipy.ndimage import maximum_filter1d
target = db(-20.0) / rms(MIX); MIX *= target
env = maximum_filter1d(np.abs(MIX).max(1), int(0.005 * SR)); thr = db(-3.0)
gain = np.minimum(1.0, thr / (env + 1e-9)); gain = lp(gain, 12.0, 1); gain = np.minimum(gain, thr / (env + 1e-9) * 1.05)
MIX *= np.clip(gain, 0, 1)[:, None]; pk = np.abs(MIX).max(); MIX = np.clip(MIX, -db(-1.0), db(-1.0))
pcm = (np.clip(MIX, -1, 1) * 32767).astype('<i2')
w = wave.open(A.out, 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes()); w.close(); print("wrote", A.out, "peak", round(float(pk), 3))
