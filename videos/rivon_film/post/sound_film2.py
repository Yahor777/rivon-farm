"""RIVON film sound v2 - more natural: modal wood/steel impacts with micro-bounces, impact-driver bursts, convolution reverb (lab hall vs
outdoors), per-location ambience beds (wind/traffic/birds, fire + sizzle, pan + knife + ball, pool water + chimes, cafe babble + cups),
push-through whooshes on the transitions, quiet shimmer on the logo and a soft CTA hit.  No melody.
usage: python3 sound_film2.py events.json out.wav [seconds=30]"""
import sys, json, wave, numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
SR = 44100; FPS = 30
ev = json.load(open(sys.argv[1])); out = sys.argv[2]; DUR = float(sys.argv[3]) if len(sys.argv) > 3 else 30.0
N = int(SR * DUR); rng = np.random.default_rng(11)
T = np.arange(N) / SR
BUS = {k: [np.zeros(N), np.zeros(N)] for k in ("dry", "amb", "lab", "out")}
AMB = {"on": False}
def bp(x, lo, hi, o=2): return sosfilt(butter(o, [lo, hi], 'band', fs=SR, output='sos'), x)
def lp(x, f, o=2): return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x)
def noise(n): return rng.normal(0, 1, n)
def pink(n):
    X = np.fft.rfft(rng.normal(size=n)); f = np.arange(len(X), dtype=float); f[0] = 1; X /= np.sqrt(f); y = np.fft.irfft(X, n); return y / (np.std(y) + 1e-9)
def brown(n):
    y = np.cumsum(rng.normal(size=n)); y = hp(y, 20, 1); return y / (np.std(y) + 1e-9)
def tt(d): return np.arange(int(d * SR)) / SR
def smooth_env(n, rate, lo=0.0):                       # slow random modulation 0..1
    k = max(2, int(n / (SR / rate))); pts = rng.uniform(lo, 1.0, k + 2); x = np.linspace(0, k, n); return np.interp(x, np.arange(k + 2), pts)
def in_lab(t): return t < 6.95 or t > 23.0
def put(sig, t, gain=1.0, pan=0.0, wet=0.25, lab=None):
    """mono signal -> dry bus + reverb send (lab hall or outdoor space depending on the time)."""
    i = int(t * SR)
    if i >= N or i < 0: return
    n = min(len(sig), N - i); l = gain * np.sqrt(0.5 * (1 - pan)) * 1.0; r = gain * np.sqrt(0.5 * (1 + pan)) * 1.0
    tgt = BUS["amb"] if AMB["on"] else BUS["dry"]
    tgt[0][i:i + n] += sig[:n] * l; tgt[1][i:i + n] += sig[:n] * r
    key = "lab" if (in_lab(t) if lab is None else lab) else "out"
    BUS[key][0][i:i + n] += sig[:n] * l * wet; BUS[key][1][i:i + n] += sig[:n] * r * wet
def bed(sig_l, sig_r, a, b, fade=0.35, gain=1.0):
    """ambience bed active on [a,b] seconds with soft edges (goes straight to the dry bus)."""
    w = np.clip((T - a) / fade, 0, 1) * np.clip((b - T) / fade, 0, 1); w = w * w * (3 - 2 * w)
    BUS["dry"][0] += sig_l * w * gain; BUS["dry"][1] += sig_r * w * gain

# ----------------------------------------------------------------------------------------------------------- one-shot sounds
def wood(f=300.0, size=1.0, hard=1.0, d=0.6):
    """timber knock: inharmonic modal body + low thump + short hard click (modal synthesis)."""
    t = tt(d); f *= rng.uniform(0.94, 1.06)
    modes = ((1.0, 1.0, 0.060), (2.31, 0.55, 0.040), (3.87, 0.38, 0.028), (5.92, 0.22, 0.018), (8.4, 0.12, 0.012))
    y = sum(a * np.sin(2 * np.pi * f * r * t + rng.uniform(0, 6.28)) * np.exp(-t / (dec * size)) for r, a, dec in modes)
    y += 0.8 * lp(noise(len(t)), 260 + 40 * size) * np.exp(-t / (0.045 * size))
    y += hard * 0.55 * bp(noise(len(t)), 1500, 6000) * np.exp(-t / 0.0045)
    return y / 2.0
def wood_bounce(f, size, g=1.0):
    y = wood(f, size, 1.0, 0.7 * size + 0.2)
    for dt, k in ((0.085 * size, 0.34), (0.15 * size, 0.16)):
        i = int(dt * SR); w2 = wood(f * 1.04, size * 0.7, 0.7, 0.4); m = min(len(w2), len(y) - i); y[i:i + m] += w2[:m] * k
    return y * g
def steel(f=1500.0, d=1.0, ring=0.25, bright=1.0):
    """steel part clink: bar-like partial ratios, long quiet ring, hard transient."""
    t = tt(d); f *= rng.uniform(0.96, 1.04)
    modes = ((1.0, 1.0, ring), (2.76, 0.7, ring * 0.75), (5.40, 0.45, ring * 0.5), (8.93, 0.28, ring * 0.32), (13.3, 0.12, ring * 0.2))
    y = sum(a * np.sin(2 * np.pi * f * r * t + rng.uniform(0, 6.28)) * np.exp(-t / dec) for r, a, dec in modes)
    y += bright * 0.7 * hp(noise(len(t)), 3000) * np.exp(-t / 0.006); y += 0.4 * bp(noise(len(t)), 400, 1400) * np.exp(-t / 0.02)
    return y / 2.0
def slide(d, lo=500, hi=3000, q=1.0):
    """part gliding in: shaped noise, rising filter, quiet."""
    t = tt(d); u = np.clip(t / d, 0, 1); env = np.sin(np.pi * u ** 0.8) ** 2
    y = bp(noise(len(t)), lo, hi) * env; return y * q
def driver(n_hits=1, d=0.55, f0=520.0):
    """cordless impact driver: motor whine ramp (harmonic stack) + gear noise + clutch ratchet at the end."""
    t = tt(d); u = np.clip(t / 0.10, 0, 1); f = f0 * (0.55 + 0.45 * u) * (1 - 0.12 * np.clip((t - (d - 0.22)) / 0.22, 0, 1))
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = sum(np.sin(k * ph + 0.3 * k) / k ** 1.2 for k in range(1, 7)) * 0.5
    y += 0.5 * bp(noise(len(t)), 1800, 6500) * (0.5 + 0.5 * u)
    rat = np.zeros(len(t)); r0 = int((d - 0.24) * SR)
    pulse = 30.0; ph2 = (t - (d - 0.24)) * pulse
    gate = (ph2 > 0) * (np.mod(ph2, 1.0) < 0.35)
    imp = bp(noise(len(t)), 900, 5000) * gate; imp = lp(imp, 6000)
    y = y * np.clip((d - t) / 0.03, 0, 1) * np.clip(t / 0.02, 0, 1); y = y * (1 - 0.35 * gate) + 1.1 * imp * (t > d - 0.24)
    y += 0.5 * lp(noise(len(t)), 300) * gate * 0.6
    return y * np.clip((d - t) / 0.02, 0, 1) * 0.5
def thump(f=55.0, d=0.5, dec=0.12, g=1.0):
    t = tt(d); return np.sin(2 * np.pi * (f + 50 * np.exp(-t / 0.04)) * t) * np.exp(-t / dec) * g
def whoosh(d, lo, hi, rising=True, q=1.0):
    """push-through whoosh: bandpassed pink noise with a sweeping centre, smooth swell."""
    n = int(d * SR); t = np.arange(n) / SR; u = t / d; y = pink(n)
    ys = np.zeros(n); nb = 8
    for k in range(nb):
        a = k / nb; b = (k + 1) / nb
        c = lo * (hi / lo) ** ((a + b) / 2 if rising else 1 - (a + b) / 2)
        seg = bp(y, max(60, c * 0.6), min(c * 1.7, SR / 2 - 100), 2)
        w = np.exp(-((u - (a + b) / 2) / 0.22) ** 2); ys += seg * w
    env = np.sin(np.pi * np.clip(u, 0, 1)) ** 1.5
    return ys * env * q
def chirp_bird(f0, d):
    tc = tt(d); mod = 1 + 0.3 * np.sin(2 * np.pi * rng.uniform(12, 28) * tc) + 0.4 * (tc / d)
    return np.sin(2 * np.pi * np.cumsum(f0 * mod) / SR) * np.sin(np.pi * tc / d) ** 2
def glass_clink(f=2600.0):
    t = tt(0.5); return (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.22) + 0.6 * np.sin(2 * np.pi * f * 2.32 * t) * np.exp(-t / 0.12) + 0.5 * hp(noise(len(t)), 5000) * np.exp(-t / 0.004)) * 0.5
def cup_clink():
    t = tt(0.35); f = rng.uniform(3000, 3600)
    return (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.08) + 0.7 * np.sin(2 * np.pi * f * 1.51 * t) * np.exp(-t / 0.06) + 0.4 * bp(noise(len(t)), 2500, 7000) * np.exp(-t / 0.006)) * 0.5
def knife_chop():
    t = tt(0.16); return (wood(520, 0.35, 1.0, 0.16) * 0.7 + 0.5 * bp(noise(len(t)), 2500, 7000) * np.exp(-t / 0.004))[:len(t)]
def chime(f):
    t = tt(2.6); return sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / dec) for r, a, dec in ((1, 1, 1.5), (2.76, 0.4, 0.9), (5.4, 0.15, 0.5))) * 0.3 * np.clip(t / 0.002, 0, 1)
def pan_of(name):
    if name.endswith("L") or "L" in name[-3:-1]: return -0.45
    if name.endswith("R") or "R" in name[-3:-1]: return 0.45
    k = int(''.join(c for c in name if c.isdigit()) or 0)
    return (-0.3, 0.3, -0.15, 0.15)[k % 4] if name[:4] in ("stop", "post", "troj") else rng.uniform(-0.25, 0.25)

# ----------------------------------------------------------------------------------------------------------- impulse responses
def make_ir(rt, bright_hz, pre=0.012, length=None):
    n = int(SR * (length or rt * 1.35)); t = np.arange(n) / SR
    out = []
    for ch in range(2):
        x = rng.normal(0, 1, n) * np.exp(-6.91 * t / rt)
        x = 0.55 * lp(x, bright_hz, 1) + 0.45 * lp(x, bright_hz * 0.35, 1)               # darker tail
        x[: int(pre * SR)] *= 0.0; x[0] = 0
        out.append(x / np.sqrt((x ** 2).sum() + 1e-9) * 0.9)
    return out
IR_LAB = make_ir(1.6, 5200, 0.018); IR_OUT = make_ir(0.38, 7000, 0.006)

# ----------------------------------------------------------------------------------------------------------- ambience beds
AMB["on"] = True
SC = {"lab1": (0.0, 7.0), "carport": (7.0, 10.2), "barbecue": (10.2, 13.4), "kitchen": (13.4, 16.6), "lounge": (16.6, 19.8), "cafe": (19.8, 23.0), "lab2": (23.0, 30.0)}
def stereo(f): return f(), f()
# lab: air-conditioning rumble, LED tube hum, faint hall air
def lab_bed():
    r = 0.05 * lp(brown(N), 160, 2) + 0.004 * lp(pink(N), 1800, 1)
    hum = 0.0035 * (np.sin(2 * np.pi * 100 * T) + 0.6 * np.sin(2 * np.pi * 200 * T + 1) + 0.35 * np.sin(2 * np.pi * 300 * T + 2)) * (0.8 + 0.2 * smooth_env(N, 0.5))
    return r + hum
bl, br = lab_bed(), lab_bed(); a, b = SC["lab1"]; bed(bl, br, 0, 7.0, 0.35); bed(bl, br, 23.0, 29.0 + 1.0, 0.5)
# outdoor air: wind through leaves (shared by all outdoor scenes)
wind_l = bp(pink(N), 250, 2200, 1) * (0.012 + 0.028 * smooth_env(N, 0.35)); wind_r = bp(pink(N), 250, 2200, 1) * (0.012 + 0.028 * smooth_env(N, 0.35))
bed(wind_l, wind_r, 7.0, 23.0, 0.35)
# birds across the garden scenes: two song-ish phrases of repeated chirps, not a melody
for tb0 in rng.uniform(7.4, 22.0, 9):
    f0 = rng.uniform(2800, 4300); pan = rng.uniform(-0.8, 0.8)
    for k in range(int(rng.integers(3, 7))): put(chirp_bird(f0 * rng.uniform(0.95, 1.08), rng.uniform(0.06, 0.12)), tb0 + k * rng.uniform(0.11, 0.17), 0.012, pan, 0.25, False)
# --- carport: road traffic passing (swells) + distant sprinkler hiss
for tp, d, dirn in ((7.5, 2.4, 1), (9.0, 2.0, -1)):
    n = int(d * SR); tn = np.arange(n) / SR; env = np.sin(np.pi * tn / d) ** 2
    car = bp(pink(n), 120, 1400, 1) * env * 0.05
    pan = np.linspace(-0.7, 0.7, n) * dirn
    sl = car * np.sqrt(0.5 * (1 - pan)); sr_ = car * np.sqrt(0.5 * (1 + pan)); i = int(tp * SR); BUS["amb"][0][i:i + n] += sl; BUS["amb"][1][i:i + n] += sr_
# --- barbecue: fire crackle + low fire roar + sizzle on the grill
def fire(a, b, g=1.0):
    n = int((b - a) * SR); i0 = int(a * SR); roar = bp(brown(n), 60, 420, 1) * 0.02 * g * (0.7 + 0.3 * smooth_env(n, 3.0))
    BUS["amb"][0][i0:i0 + n] += roar; BUS["amb"][1][i0:i0 + n] += roar * 0.95
    for k in range(int((b - a) * 20)):
        tc = a + rng.uniform(0, b - a); d = rng.uniform(0.004, 0.02); pop = hp(noise(int(d * SR) + 8), rng.uniform(1500, 4500)) * np.exp(-tt(d + 8 / SR) / (d * 0.5))
        put(pop, tc, rng.uniform(0.02, 0.12) * g, rng.uniform(-0.9, 0.9), 0.15, False)
    for k in range(int((b - a) * 1.2)):
        tc = a + rng.uniform(0, b - a); put(lp(noise(int(0.05 * SR)), 900) * np.exp(-tt(0.05) / 0.012), tc, 0.12 * g, rng.uniform(-0.8, 0.8), 0.15, False)
fire(10.2, 13.6, 1.0)
def sizzle(a, b, g):
    n = int((b - a) * SR); i0 = int(a * SR); s = hp(noise(n), 4500, 1) * (0.4 + 0.6 * smooth_env(n, 14.0)) * 0.012 * g
    BUS["amb"][0][i0:i0 + n] += s * 0.9; BUS["amb"][1][i0:i0 + n] += s * 1.1
sizzle(10.4, 13.4, 1.0)
for tc in (10.8, 11.7, 12.5): put(glass_clink(rng.uniform(2300, 2900)), tc, 0.05, rng.uniform(-0.5, 0.5), 0.3, False)
# --- summer kitchen: frying pan + chopping on a board + a few volleyball bumps and trampoline springs further away
sizzle(13.4, 16.6, 1.9)
for burst0 in (13.8, 15.4):
    for k in range(7): put(knife_chop(), burst0 + k * 0.145 + rng.uniform(-0.01, 0.01), rng.uniform(0.10, 0.17), -0.3, 0.2, False)
for tb in (14.3, 14.95, 15.85, 16.3):
    t = tt(0.3); ball = lp(noise(len(t)), 700) * np.exp(-t / 0.05) + np.sin(2 * np.pi * (110 + 40 * np.exp(-t / 0.04)) * t) * np.exp(-t / 0.08); put(ball, tb, 0.10, 0.6, 0.5, False)
for tb in (14.0, 15.1, 16.0):
    t = tt(0.5); sp = sum(np.sin(2 * np.pi * f * t * (1 + 0.02 * np.sin(2 * np.pi * 8 * t))) * np.exp(-t / 0.2) for f in (610, 910, 1420)) * 0.1; put(sp, tb, 0.035, 0.7, 0.4, False)
# --- lounge: pool water (lapping + bubbles) and a few soft wind chimes
def water(a, b, g):
    n = int((b - a) * SR); i0 = int(a * SR); w = bp(pink(n), 300, 3000, 1) * (0.5 + 0.5 * smooth_env(n, 1.8)) * 0.02 * g
    lap = lp(noise(n), 500) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.45 * np.arange(n) / SR)) * 0.012 * g
    BUS["amb"][0][i0:i0 + n] += w + lap; BUS["amb"][1][i0:i0 + n] += w * 0.9 + lap * 1.1
    for k in range(int((b - a) * 7)):
        tc = a + rng.uniform(0, b - a); d = rng.uniform(0.02, 0.05); tcn = tt(d); f = rng.uniform(450, 1100) * (1 + 1.4 * tcn / d); bub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tcn / d) ** 2
        put(bub, tc, rng.uniform(0.01, 0.035) * g, rng.uniform(-0.8, 0.8), 0.2, False)
water(16.6, 19.9, 1.0)
for tc, f in ((17.2, 1480.0), (18.1, 1976.0), (19.0, 1319.0)): put(chime(f), tc, 0.05, rng.uniform(-0.6, 0.6), 0.45, False)
# --- cafe: speech-like babble from several voices + cups + espresso machine steam
def babble(a, b, nv=8, g=1.0):
    n = int((b - a) * SR); i0 = int(a * SR); accl = np.zeros(n); accr = np.zeros(n)
    for v in range(nv):
        f1 = rng.uniform(450, 800); f2 = rng.uniform(1100, 1900); base = pink(n)
        voice = bp(base, f1 * 0.8, f1 * 1.3, 1) + 0.6 * bp(base, f2 * 0.8, f2 * 1.25, 1) + 0.15 * bp(base, 2600, 3800, 1)
        syl = smooth_env(n, rng.uniform(3.0, 5.5)) ** 2.0 * (smooth_env(n, 0.7, 0.0) > 0.35)
        pan = rng.uniform(-0.9, 0.9); accl += voice * syl * np.sqrt(0.5 * (1 - pan)); accr += voice * syl * np.sqrt(0.5 * (1 + pan))
    BUS["amb"][0][i0:i0 + n] += accl * 0.012 * g / np.sqrt(nv) * 2.0; BUS["amb"][1][i0:i0 + n] += accr * 0.012 * g / np.sqrt(nv) * 2.0
babble(19.8, 23.1, 9, 1.0)
for tc in (20.2, 20.9, 21.6, 22.3): put(cup_clink(), tc + rng.uniform(-0.05, 0.05), rng.uniform(0.04, 0.08), rng.uniform(-0.7, 0.7), 0.3, False)
n = int(1.6 * SR); st = hp(noise(n), 3500, 1) * np.sin(np.pi * np.arange(n) / n) ** 1.5 * 0.025; put(st, 21.0, 1.0, 0.7, 0.2, False)

AMB["on"] = False
# ----------------------------------------------------------------------------------------------------------- assembly / disassembly foley
for e in ev:
    n, f0, f1 = e["name"], e["f0"] / FPS, e["f1"] / FPS; off = n.endswith("_off"); n = n.replace("_off", ""); g = 0.75 if off else 1.0
    if n in ("cut", "hero", "cta"): continue
    pan = pan_of(n); dur = max(f1 - f0, 0.12)
    if n.startswith("stopa"):
        put(slide(dur, 700, 3200), f0, 0.05 * g, pan, 0.2); put(steel(1700, 0.9, 0.22), f1, 0.17 * g, pan, 0.45); put(thump(95, 0.3, 0.06, 0.25), f1, 1.0 * g, pan, 0.2)
        if not off: put(driver(1, 0.5, 480), f1 + 0.1, 0.14, pan, 0.3)
    elif n.startswith("post"):
        put(slide(dur, 250, 1400), f0, 0.045 * g, pan, 0.2); put(wood_bounce(185, 1.3, 0.42 * g), f1, 1.0, pan, 0.45)
    elif n.startswith("trojak"):
        put(slide(dur, 500, 2800), f0, 0.05 * g, pan, 0.2); put(steel(1200, 1.0, 0.28), f1, 0.2 * g, pan, 0.45); put(thump(120, 0.25, 0.05, 0.22), f1, 1.0 * g, pan, 0.2)
        if not off: put(driver(1, 0.6, 520), f1 + 0.08, 0.15, pan, 0.3)
    elif n.startswith("beam"):
        put(slide(dur, 220, 1300), f0, 0.05 * g, pan, 0.2); put(wood_bounce(135, 1.7, 0.5 * g), f1, 1.0, pan, 0.5)
        if not off: put(driver(1, 0.5, 460), f1 + 0.12, 0.13, pan, 0.3)
    elif n.startswith("mb2"):
        put(steel(2300, 0.35, 0.07, 0.8), f1, 0.07 * g, pan, 0.35)
        if not off: put(driver(1, 0.28, 560), f1 + 0.04, 0.07, pan, 0.25)
    elif n.startswith("rafter"):
        put(slide(dur, 300, 1700), f0, 0.04 * g, pan, 0.2); put(wood_bounce(240, 0.9, 0.3 * g), f1, 1.0, pan, 0.4)

# ----------------------------------------------------------------------------------------------------------- transitions (push-through)
for e in ev:
    if e["name"] != "cut": continue
    c = e["f1"] / FPS; tw = 8 / FPS
    put(whoosh(tw + 0.06, 350, 6500, True, 0.20), c - tw - 0.03, 1.0, -0.1, 0.35, False)
    put(thump(52, 0.7, 0.2, 0.55)[:int(0.6 * SR)] + 0.5 * lp(noise(int(0.6 * SR)), 180) * np.exp(-tt(0.6) / 0.18)[:int(0.6 * SR)], c, 1.0, 0.0, 0.1, False)
    put(whoosh(tw + 0.12, 6000, 500, False, 0.17), c, 1.0, 0.1, 0.35, False)
    put(bp(noise(int(0.5 * SR)), 3000, 9000) * np.exp(-tt(0.5) / 0.12), c, 0.025, 0.0, 0.3, False)
# ----------------------------------------------------------------------------------------------------------- hero + end card
put(whoosh(1.2, 300, 3200, True, 0.2), 758 / FPS, 1.0, 0.0, 0.5, True)
put(steel(880, 2.4, 0.7), 798 / FPS, 0.10, 0.0, 0.7, True)
# darkening: air falls away into a low swell, glassy shimmer when the engraved mark becomes the graphic, soft hit with the CTA
ds = 826 / FPS; n = int(2.4 * SR); sw = lp(brown(n), 90, 2) * np.sin(np.pi * np.clip(np.arange(n) / n, 0, 1) ** 0.8) ** 2 * 0.2; put(sw, ds, 1.0, 0.0, 0.15, True)
put(np.sin(2 * np.pi * 55 * tt(2.0)) * np.exp(-tt(2.0) / 0.9) * 0.1, ds + 0.1, 1.0, 0.0, 0.1, True)
tg = tt(3.0); sh = sum(a * np.sin(2 * np.pi * f * tg + k) * np.exp(-tg / dec) for k, (f, a, dec) in enumerate(((1760, 1, 1.6), (2217, 0.7, 1.4), (2960, 0.55, 1.1), (4435, 0.3, 0.8)))) * np.clip(tg / 0.01, 0, 1)
put(sh * 0.4, 838 / FPS, 0.06, 0.0, 0.7, True)
put(thump(46, 1.4, 0.4, 0.8), 866 / FPS, 0.35, 0.0, 0.3, True)
put(hp(noise(int(0.15 * SR)), 5000) * np.exp(-tt(0.15) / 0.03), 866 / FPS, 0.02, 0.0, 0.4, True)
put(hp(noise(int(0.15 * SR)), 5000) * np.exp(-tt(0.15) / 0.03), 872 / FPS, 0.02, 0.0, 0.4, True)

# ----------------------------------------------------------------------------------------------------------- mix: reverb returns, master
AMB_GAIN = 3.2
def conv(x, ir): return fftconvolve(x, ir)[:N]
for key, ir, g in (("lab", IR_LAB, 1.0), ("out", IR_OUT, 0.9)):
    BUS["dry"][0] += conv(BUS[key][0], ir[0]) * g; BUS["dry"][1] += conv(BUS[key][1], ir[1]) * g
BUS["dry"][0] += BUS["amb"][0] * AMB_GAIN; BUS["dry"][1] += BUS["amb"][1] * AMB_GAIN
L, R = BUS["dry"]
fade = np.clip((DUR - T) / 0.8, 0, 1) * np.clip(T / 0.08, 0, 1)
end_duck = 1 - 0.55 * np.clip((T - 27.5) / 1.0, 0, 1)                 # ambience eases during the CTA hold
st = np.stack([L, R], 1)
st = np.tanh(st * 1.6) / 1.6 if np.abs(st).max() > 0.9 else st        # gentle safety saturation
pk = np.abs(st).max(); st = st * (0.8 / pk) * fade[:, None]
pcm = (np.clip(st, -1, 1) * 32767).astype('<i2')
w = wave.open(out, 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes()); w.close(); print("wrote", out, "peak", round(float(pk), 3))
