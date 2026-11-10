"""Synthesised material sounds (no melody) for the RIVON film, timed from events.json (film_events.py).
usage: python3 sound_film.py events.json out.wav [seconds=30]"""
import sys, json, numpy as np
from scipy.signal import butter, sosfilt
SR = 44100; FPS = 30
ev = json.load(open(sys.argv[1])); out = sys.argv[2]; DUR = float(sys.argv[3]) if len(sys.argv) > 3 else 30.0
N = int(SR * DUR); rng = np.random.default_rng(7)
L = np.zeros(N); R = np.zeros(N)
def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, hi], 'band', fs=SR, output='sos'), x)
def lp(x, f, o=2): return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x)
def noise(n): return rng.normal(0, 1, n)
def add(sig, t, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= N or i < 0: return
    n = min(len(sig), N - i); l = gain * (1 - 0.5 * max(pan, 0)); r = gain * (1 - 0.5 * max(-pan, 0))
    L[i:i + n] += sig[:n] * l; R[i:i + n] += sig[:n] * r
def tt(d): return np.arange(int(d * SR)) / SR
def tone(freq, d, dec, harm=(1.0,)):
    t = tt(d); y = sum(a * np.sin(2 * np.pi * freq * (k + 1) * t) for k, a in enumerate(harm)); return y * np.exp(-t / dec)
def thud(f=70, d=0.35, dec=0.08, nz=0.6, nf=500):
    t = tt(d); return np.sin(2 * np.pi * (f + 40 * np.exp(-t / 0.03)) * t) * np.exp(-t / dec) + nz * lp(noise(len(t)), nf) * np.exp(-t / (dec * 0.7))
def wood_tok(f=380, d=0.28, dec=0.05):
    t = tt(d); return tone(f, d, dec, (1.0, 0.5, 0.25)) + 0.7 * bp(noise(len(t)), 800, 3500) * np.exp(-t / 0.018) + 0.5 * thud(90, d, 0.06, 0.2, 300)[:len(t)]
def steel(fs_, d=0.5, dec=0.11):
    t = tt(d); y = sum(a * np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) * np.exp(-t / (dec * (1.0 - 0.15 * i))) for i, (f, a) in enumerate(fs_))
    return y + 0.4 * hp(noise(len(t)), 3000) * np.exp(-t / 0.01)
def whoosh(d, lo=500, hi=2500):
    t = tt(d); env = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2; return bp(noise(len(t)), lo, hi) * env
def drill(d=0.38):
    t = tt(d); f = 150 + 120 * np.clip(t / 0.12, 0, 1); ph = 2 * np.cumsum(f) / SR * np.pi
    y = (np.sign(np.sin(ph)) * 0.5 + np.sin(ph)) * 0.5; y += 0.6 * bp(noise(len(t)), 1500, 5000) * (0.6 + 0.4 * np.sin(2 * np.pi * 38 * t))
    return y * np.clip(t / 0.03, 0, 1) * np.clip((d - t) / 0.04, 0, 1)
# ---- ambience: lab hall room tone (0-7 s, 23-30 s) and bright garden air (7-23 s)
t = np.arange(N) / SR
hall = lp(noise(N), 260, 2) * 0.06 + 0.012 * np.sin(2 * np.pi * 55 * t) + 0.006 * np.sin(2 * np.pi * 110.5 * t)
garden = hp(lp(noise(N), 3500, 1), 400, 1) * 0.022
inlab = ((t < 7.0) | (t > 23.0)).astype(float); inlab = lp(inlab, 8, 1)
L += hall * inlab + garden * (1 - inlab); R += hall * inlab * 0.95 + garden * (1 - inlab) * 1.05
for k in range(24):                                           # birds in the garden scenes (short chirps, no melody)
    tb = rng.uniform(7.4, 22.6); f0 = rng.uniform(2600, 4200); d = rng.uniform(0.07, 0.16); tc = tt(d)
    ch = np.sin(2 * np.pi * np.cumsum(f0 * (1 + 0.35 * np.sin(2 * np.pi * rng.uniform(14, 30) * tc))) / SR) * np.sin(np.pi * tc / d) ** 2
    add(ch, tb, 0.012, rng.uniform(-0.8, 0.8))
for e in ev:
    n, f0, f1 = e["name"], e["f0"] / FPS, e["f1"] / FPS; off = n.endswith("_off"); n = n.replace("_off", ""); g = 0.8 if off else 1.0
    if n.startswith("stopa"):
        add(whoosh(max(f1 - f0, .1), 600, 2800), f0, 0.07 * g); add(steel([(1900, 0.6), (2950, 0.35), (4400, 0.2)], 0.5, 0.07), f1, 0.22 * g); add(thud(110, 0.25, 0.04, 0.4, 600), f1, 0.25 * g)
    elif n.startswith("post"):
        add(whoosh(max(f1 - f0, .1), 300, 1500), f0, 0.06 * g); add(wood_tok(310), f1, 0.42 * g)
    elif n.startswith("trojak"):
        add(whoosh(max(f1 - f0, .1), 600, 2800), f0, 0.07 * g); add(steel([(1250, 0.6), (1980, 0.4), (3100, 0.25)], 0.55, 0.10), f1, 0.28 * g); add(thud(130, 0.25, 0.04, 0.4, 700), f1, 0.22 * g)
        if not off: add(drill(0.4), f1 + 0.08, 0.20)
    elif n.startswith("beam"):
        add(whoosh(max(f1 - f0, .1), 300, 1400), f0, 0.07 * g); add(wood_tok(200, 0.4, 0.09), f1, 0.5 * g)
        if not off: add(drill(0.32), f1 + 0.1, 0.17)
    elif n.startswith("mb2"):
        add(steel([(2200, 0.45), (3500, 0.3)], 0.25, 0.04), f1, 0.12 * g)
        if not off: add(drill(0.22), f1 + 0.03, 0.09)
    elif n.startswith("rafter"):
        add(whoosh(max(f1 - f0, .1), 400, 1800), f0, 0.05 * g); add(wood_tok(260, 0.3, 0.05), f1, 0.28 * g)
    elif n == "cut":                                          # whoosh into the cut + sub impact on the flash
        add(whoosh(0.3, 800, 6000), f1 - 0.28, 0.16); add(thud(48, 0.55, 0.16, 0.25, 220), f1, 0.55); add(bp(noise(int(0.4 * SR)), 2500, 9000) * np.exp(-tt(0.4) / 0.09), f1, 0.09)
    elif n == "hero":
        add(whoosh(1.3, 300, 3500), f0, 0.12); add(steel([(880, 0.5), (1760, 0.3), (2640, 0.2)], 1.6, 0.4), f1, 0.14)
    elif n == "cta":
        add(thud(42, 1.2, 0.35, 0.1, 150), f1, 0.6); add(steel([(1320, 0.3), (1980, 0.2), (3960, 0.1)], 2.0, 0.6), f1, 0.08)
pk = max(np.abs(L).max(), np.abs(R).max()); g = 0.85 / pk
fade = np.clip((DUR - t) / 1.0, 0, 1) * np.clip(t / 0.1, 0, 1)
import wave
st = (np.stack([L, R], 1) * g * fade[:, None]); pcm = (np.clip(st, -1, 1) * 32767).astype('<i2')
w = wave.open(out, 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes()); w.close(); print("wrote", out)
