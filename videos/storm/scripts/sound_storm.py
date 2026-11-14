"""THE STORM soundtrack from real recordings (CC0 / public domain, see sound/sources.json), mixed to the picture.
No synthesis, no melody. Every impact is trimmed to its onset and placed on the frame where the part lands
(film.assemble timings). python3 sound_storm.py <sfx_dir> <sources.json> <out.wav>"""
import sys, json, subprocess, math
from pathlib import Path
import numpy as np

SR = 48000; FPS = 30; NF = 990; N = int(SR * NF / FPS)
sfx, src, out = Path(sys.argv[1]), json.load(open(sys.argv[2])), sys.argv[3]
rng = np.random.default_rng(11)
mixL = np.zeros(N, np.float64); mixR = np.zeros(N, np.float64)
T = np.arange(N) / SR
fr = lambda f: (f - 1) / FPS


def load(key, idx=0):
    """decode with ffmpeg -> float stereo; returns None if the recording is missing"""
    files = src.get(key) or []
    if not files:
        return None
    f = sfx / files[idx % len(files)]["file"]
    if not f.exists():
        return None
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(f), "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"], capture_output=True).stdout
    a = np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)
    off = files[idx % len(files)].get("start", 0.0); a = a[int(off * SR):]
    return a if len(a) > SR // 20 else None


def onset(a, thr=0.12):
    """trim leading silence so the attack sits exactly on the cue"""
    env = np.abs(a).max(1); pk = env.max() + 1e-9; i = int(np.argmax(env > thr * pk))
    return a[max(0, i - int(0.004 * SR)):]


def norm(a, peak=None, rms=None):
    if peak is not None:
        return a / (np.abs(a).max() + 1e-9) * peak
    r = math.sqrt(float((a ** 2).mean()) + 1e-12); return a / r * rms


def place(a, t, gain=1.0, pan=0.0, fade_in=0.0, fade_out=0.05, dur=None):
    if a is None:
        return
    if dur is not None:
        a = a[:int(dur * SR)]
    a = a.copy(); n = len(a)
    if fade_in > 0:
        k = min(n, int(fade_in * SR)); a[:k] *= np.linspace(0, 1, k)[:, None]
    k = min(n, int(fade_out * SR)); a[n - k:] *= np.linspace(1, 0, k)[:, None]
    i0 = int(t * SR); k = min(n, N - i0)
    if k <= 0 or i0 < 0:
        return
    mixL[i0:i0 + k] += a[:k, 0] * gain * math.sqrt(0.5 * (1 - pan)) * 1.414
    mixR[i0:i0 + k] += a[:k, 1] * gain * math.sqrt(0.5 * (1 + pan)) * 1.414


def bed(key, t0, t1, gain, env=None, idx=0, rms=0.06):
    """looped ambience with crossfaded loop points and an envelope (list of (time, level))"""
    a = load(key, idx)
    if a is None:
        return
    a = norm(a[int(0.3 * SR):], rms=rms); need = int((t1 - t0) * SR); xf = int(0.5 * SR)
    if len(a) < need + xf:
        reps = []
        while sum(len(r) for r in reps) < need + xf:
            reps.append(a)
        outb = reps[0]
        for r in reps[1:]:
            k = min(xf, len(outb), len(r)); w = np.linspace(0, 1, k)[:, None]
            outb = np.concatenate([outb[:-k], outb[-k:] * (1 - w) + r[:k] * w, r[k:]])
        a = outb
    a = a[:need].copy()
    tt = t0 + np.arange(len(a)) / SR
    if env:
        a *= np.interp(tt, [e[0] for e in env], [e[1] for e in env])[:, None]
    place(a, t0, gain, 0.0, 0.0, 0.0)


def hit(key, f, gain=1.0, pan=0.0, idx=0, dur=None, peak=0.8, pitch=1.0):
    a = load(key, idx)
    if a is None:
        return
    a = onset(a)
    if pitch != 1.0:                                           # small resample = a different beam, not the same sample
        n2 = int(len(a) / pitch); a = np.stack([np.interp(np.linspace(0, len(a) - 1, n2), np.arange(len(a)), a[:, c]) for c in (0, 1)], 1)
    place(norm(a, peak=peak), fr(f), gain, pan, 0.0, 0.08 if dur is None else min(0.08, dur / 3), dur)


FREEZE = 418; RESUME = 745                                      # frames: time stops / the drop lands
# ---- world before the freeze: sea, light wind, the gust, thunder
duck = [(0, 1.0), (fr(FREEZE) - 0.05, 1.0), (fr(FREEZE) + 0.22, 0.0), (fr(RESUME) + 0.3, 0.0), (fr(RESUME) + 1.6, 1.0), (33.0, 1.0)]
def env_mul(e):
    return [(t, v * float(np.interp(t, [d[0] for d in duck], [d[1] for d in duck]))) for t, v in e]
grid = sorted(set([d[0] for d in duck] + list(np.arange(0, 33.01, 0.25))))
bed("sea_waves", 0.0, 33.0, 1.0, env_mul([(t, float(np.interp(t, [0, 7, 10.5, 27, 29.5, 33], [0.8, 0.8, 0.45, 0.0, 0.35, 0.55]))) for t in grid]))
bed("wind_gust", 0.0, 33.0, 1.0, env_mul([(t, float(np.interp(t, [0, 4.2, 4.9, 5.6, 6.2, 6.9, 10.5, 13.9, 27.0, 28.5, 33], [0.10, 0.12, 0.9, 0.55, 1.0, 0.7, 0.45, 0.5, 0.25, 0.3, 0.08]))) for t in grid]), rms=0.09)
bed("leaves_rustle", 0.0, 14.0, 1.0, env_mul([(t, float(np.interp(t, [0, 4.4, 5.0, 6.3, 7.0, 14], [0.25, 0.3, 1.0, 1.0, 0.5, 0.2]))) for t in grid if t <= 14.0]), rms=0.05)
hit("cloth_flap", 158, 0.5, -0.2, dur=1.6, peak=0.5); hit("glass_set", 170, 0.22, 0.3, dur=0.6, peak=0.4)
hit("thunder", 236, 0.75, 0.2, dur=7.0, peak=0.85)             # far thunder as the cloud takes the sky
# ---- the freeze: everything is pulled out, one low hit, near silence
hit("whoosh_low", FREEZE - 2, 0.7, 0.0, dur=2.2, peak=0.8)
# ---- assembly in the silence: concrete, close, dry
hit("metal_clank", 474, 0.55, 0.25, idx=0, dur=0.9); hit("wood_on_metal", 475, 0.5, 0.25, idx=0, dur=0.8, pitch=1.15)   # Trojak seats on the post
for k, f in enumerate((478, 487, 495)):
    hit("screwdriver", f, 0.42, 0.2, idx=0, dur=0.55, pitch=1.0 + 0.04 * k)
for k, (f, pan) in enumerate(((549, 0.3), (554, -0.3))):                                                          # long beams land on the plates
    hit("wood_on_metal", f, 0.95, pan, idx=k, dur=1.2, pitch=0.82 + 0.05 * k); hit("metal_clank", f, 0.3, pan, idx=1, dur=0.6, pitch=0.9)
for k, (f, pan) in enumerate(((570, 0.2), (574, -0.2))):
    hit("wood_on_metal", f, 0.8, pan, idx=k + 1, dur=1.0, pitch=0.95 + 0.05 * k)
for k, f in enumerate((558, 565, 573, 580)):
    hit("screwdriver", f, 0.36, (-1) ** k * 0.3, idx=k, dur=0.5, pitch=0.97 + 0.03 * k)
for k in range(11):                                                                                               # rafters into the Mocowanie
    f = 592 + 26 * k / 10.0 + 28
    hit("wood_on_metal", f, 0.6 if k != 4 else 0.9, -0.6 + 0.12 * k, idx=k, dur=0.7, pitch=1.05 + 0.03 * (k % 4))
for k, f in enumerate((624, 631, 638, 644)):
    hit("screwdriver", f, 0.3, (-1) ** k * 0.25, idx=k + 1, dur=0.45, pitch=1.02)
for k in range(7):
    hit("metal_clank", 676 + 16 * k / 6.0, 0.22, -0.5 + k / 6.0, idx=k, dur=0.4, pitch=1.3)                        # glazing bars
for k in range(6):
    hit("glass_set", 704 + 16 * k / 5.0, 0.3, -0.5 + k / 5.0, idx=k, dur=0.7, pitch=0.8)                            # glass panes settle
hit("switch", 716, 0.5, 0.0, dur=0.3)                                                                             # the lights
# ---- time resumes: the drop, then the sky opens
hit("water_drop", RESUME, 0.8, 0.0, dur=1.2, peak=0.85)
hit("thunder", 792, 1.0, -0.1, idx=1, dur=8.0, peak=0.95)
bed("rain_heavy", fr(806), 33.0, 1.0, [(fr(806), 0.0), (fr(830), 0.55), (fr(860), 0.9), (fr(900), 0.8), (fr(950), 0.3), (33.0, 0.12)], rms=0.085)
bed("rain_roof", fr(811), fr(960), 1.0, [(fr(811), 0.0), (fr(835), 0.8), (fr(886), 0.8), (fr(905), 0.25), (fr(960), 0.0)], rms=0.07)
bed("birds", fr(925), 33.0, 1.0, [(fr(925), 0.0), (fr(950), 0.5), (33.0, 0.6)], rms=0.035)
# ---- master
st = np.stack([mixL, mixR], 1)
st *= (np.clip(T / 0.4, 0, 1) * np.clip((NF / FPS - T) / 1.2, 0, 1))[:, None]
st = np.tanh(st * 1.25); st = st / (np.abs(st).max() + 1e-9) * 0.92
import wave
with wave.open(out, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype(np.int16).tobytes())
print("SOUND", out, "recordings used:", {k: len(v) for k, v in src.items()})
