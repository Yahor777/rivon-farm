"""Assemble THE STORM: frames f0001..f0600 (any subset; gaps are held) -> 30 fps MP4 with the end card (RIVON logo +
'Mały detal. Wielkie możliwości.') and a synthesized soundtrack of real-world sounds (sea, wind, thunder, impacts of
wood on steel, rain on glass, the drop) - no melody. python3 finish_storm.py <frames_dir> <film.json> <out.mp4>"""
import sys, json, subprocess, wave, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy.signal import butter, sosfilt

HERE = Path(__file__).resolve().parent; POST = HERE.parent.parent / "rivon_film" / "post"
fr_dir, cfg, out = Path(sys.argv[1]), json.load(open(sys.argv[2])), sys.argv[3]
FPS, NF = 30, 600
have = sorted(int(p.stem[1:]) for p in fr_dir.glob("f[0-9][0-9][0-9][0-9].png"))
assert have, "no frames"
W, H = Image.open(fr_dir / f"f{have[0]:04d}.png").size
tmp = Path(out).with_suffix("").as_posix() + "_frames"; Path(tmp).mkdir(parents=True, exist_ok=True)

# ---- end card -------------------------------------------------------------------------------------------------------
logo = Image.open(POST / "rivon_logo.png").convert("L")
bb = logo.point(lambda v: 255 if v > 40 else 0).getbbox(); logo = logo.crop(bb)
lw = int(W * 0.56); logo = logo.resize((lw, int(logo.height * lw / logo.width)), Image.LANCZOS)
try:
    font = ImageFont.truetype(str(POST / "fonts" / "Inter-Light.otf"), max(12, int(W * 0.040)))
except OSError:
    font = ImageFont.load_default()
SLOGAN = "Mały detal. Wielkie możliwości."


def end_card(im, a):
    """a in 0..1: darken the lower-middle slightly, fade in logo then slogan"""
    if a <= 0:
        return im
    im = im.convert("RGB"); ov = Image.new("RGB", im.size, (0, 0, 0))
    grad = Image.new("L", (1, H))
    for y in range(H):
        t = abs(y / H - 0.31) / 0.3
        grad.putpixel((0, y), int(255 * 0.42 * a * max(0.0, 1 - t ** 1.5)))
    im = Image.composite(ov, im, grad.resize(im.size))
    la = min(1.0, a / 0.6)
    x0 = (W - logo.width) // 2; y0 = int(H * 0.27)          # over the facade, the pergola stays visible below
    sh = Image.new("L", im.size, 0); sh.paste(logo, (x0, y0 + max(1, H // 480)))
    sh = sh.filter(ImageFilter.GaussianBlur(max(1, W // 180)))
    im = Image.composite(Image.new("RGB", im.size, (0, 0, 0)), im, sh.point(lambda v: int(v * 0.55 * la)))
    m = Image.new("L", im.size, 0); m.paste(logo, (x0, y0))
    im = Image.composite(Image.new("RGB", im.size, (255, 255, 255)), im, m.point(lambda v: int(v * la)))
    sa = max(0.0, min(1.0, (a - 0.45) / 0.55))
    if sa > 0:
        t = Image.new("L", im.size, 0); d = ImageDraw.Draw(t)
        tw = d.textlength(SLOGAN, font=font); d.text(((W - tw) / 2, y0 + logo.height + H * 0.022), SLOGAN, font=font, fill=255)
        im = Image.composite(Image.new("RGB", im.size, (255, 255, 255)), im, t.point(lambda v: int(v * sa)))
    return im


for f in range(1, NF + 1):
    src = max([h for h in have if h <= f], default=have[0])
    im = Image.open(fr_dir / f"f{src:04d}.png").convert("RGB")
    a = (f - 546) / 26.0
    im = end_card(im, min(1.0, a)) if a > 0 else im
    if f > 588:                                             # last 0.4 s: gentle fade to black
        im = Image.blend(im, Image.new("RGB", im.size, (0, 0, 0)), min(1.0, (f - 588) / 12.0) * 0.85)
    im.save(f"{tmp}/o{f:04d}.png")

# ---- sound: synthesized physical sources, no melody ------------------------------------------------------------------
SR = 44100; N = int(SR * NF / FPS); rng = np.random.default_rng(5); T = np.arange(N) / SR
L = np.zeros(N); R = np.zeros(N)
def filt(x, kind, f, o=2): return sosfilt(butter(o, f, kind, fs=SR, output="sos"), x)
def env(t0, t1, a=0.3, r=0.5):
    e = np.clip((T - t0) / a, 0, 1) * np.clip((t1 - T) / r, 0, 1); return np.clip(e, 0, 1)
def add(sig, g=1.0, pan=0.0):
    global L, R
    L += sig * g * math.sqrt(0.5 * (1 - pan)); R += sig * g * math.sqrt(0.5 * (1 + pan))
def hit(t, f0, dur, g, pan=0.0, noise=0.3):
    n = int(dur * SR); tt = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f0 * m * tt) * np.exp(-tt * (9 + 5 * i)) / (i + 1) for i, m in enumerate((1.0, 2.31, 3.87, 5.2)))
    s += noise * filt(rng.normal(size=n), "high", 1500) * np.exp(-tt * 60)
    z = np.zeros(N); i0 = int(t * SR); k = min(n, N - i0)
    if k > 0:
        z[i0:i0 + k] = s[:k]; add(z, g, pan)
fr = lambda f: f / FPS
white = rng.normal(size=N)
slow = np.interp(T, np.linspace(0, NF / FPS, 60), rng.uniform(0.5, 1.0, 60))
sea = filt(white, "band", [120, 900]) * (0.55 + 0.45 * np.sin(2 * np.pi * T / 7.0 + 1.0) ** 2)
add(sea * env(0, fr(240), 0.8, 1.0), 0.20, -0.2)                                   # surf, calm part
wind = filt(rng.normal(size=N), "band", [180, 1400]) * slow
add(wind * env(0, fr(150), 1.0, 1.0), 0.05); add(wind * env(fr(150), fr(244), 0.5, 0.15), 0.42, 0.2)   # the gust
gust = filt(rng.normal(size=N), "band", [300, 2600]) * env(fr(155), fr(205), 0.25, 0.9); add(gust, 0.30, -0.3)
def thunder(t, g):
    n = int(4.0 * SR); tt = np.arange(n) / SR
    s = filt(np.cumsum(rng.normal(size=n)), "band", [28, 140]); s = s / (np.abs(s).max() + 1e-9) * np.exp(-tt * 0.9) * (1 - np.exp(-tt * 14))
    z = np.zeros(N); i0 = int(t * SR); k = min(n, N - i0); z[i0:i0 + k] = s[:k]; add(z, g, 0.1)
thunder(fr(214), 0.9); thunder(fr(424), 1.0); thunder(fr(520), 0.35)
# time freeze: everything stops (sub drop + silence with a faint room tone), f 252-420
n = int(1.2 * SR); tt = np.arange(n) / SR; sub = np.sin(2 * np.pi * (70 - 35 * tt / 1.2) * tt) * np.exp(-tt * 3.2)
z = np.zeros(N); i0 = int(fr(252) * SR); z[i0:i0 + n] = sub; add(z, 0.8)
add(filt(rng.normal(size=N), "low", 160) * env(fr(256), fr(420), 0.6, 0.4), 0.05)
# assembly: wood into steel, steel on deck, glass panes; timed to film.assemble windows
for f, f0, g, pan in [(272, 190, .5, -.3), (276, 205, .5, .3), (282, 120, .6, -.2), (286, 128, .6, .2), (296, 310, .45, .3),
                      (300, 330, .45, -.3), (312, 150, .6, .2), (316, 142, .6, -.2), (322, 160, .55, 0)] + \
                     [(340 + 3 * i, 170 + 9 * (i % 4), .32, (-1) ** i * .4) for i in range(11)] + \
                     [(376 + 3 * i, 520 + 30 * i, .25, (-1) ** i * .3) for i in range(6)]:
    hit(fr(f), f0, 0.5, g, pan)
hit(fr(398), 1900, 0.12, 0.25, 0, 0.8)                                               # lights: relay click
add(filt(rng.normal(size=N), "band", [90, 130]) * env(fr(399), fr(600), 0.4, 1.0), 0.012)   # faint warm hum
# rain: on glass roof (bright) + on deck/lawn (broad), f 421-...; thins after f 520
rain_e = env(fr(421), fr(600), 0.25, 0.1) * np.interp(T, [0, fr(511), fr(575), fr(600)], [1, 1, 0.25, 0.12])
add(filt(rng.normal(size=N), "high", 2500) * rain_e, 0.20, 0.0); add(filt(rng.normal(size=N), "band", [400, 3000]) * rain_e, 0.28, 0.25)
for k in range(700):                                                                # individual drops on the glass
    t = rng.uniform(fr(421), fr(590));
    if rng.random() < float(np.interp(t, [fr(421), fr(511), fr(600)], [1, 1, 0.15])):
        hit(t, rng.uniform(1800, 4200), 0.03, rng.uniform(0.02, 0.07), rng.uniform(-0.8, 0.8), 0.6)
# the drop lands in the wine (contact at ~f 478): plink + tiny splash
n = int(0.25 * SR); tt = np.arange(n) / SR; pl = np.sin(2 * np.pi * (900 + 1700 * np.exp(-tt * 22)) * tt) * np.exp(-tt * 16)
z = np.zeros(N); i0 = int(fr(478) * SR); z[i0:i0 + n] = pl; add(z, 0.5)
# sun break: birds return (short chirps), surf back
add(sea * env(fr(520), fr(600), 2.0, 0.6), 0.14, -0.2)
for k in range(9):
    t = rng.uniform(fr(535), fr(592)); n = int(0.12 * SR); tt = np.arange(n) / SR
    ch = np.sin(2 * np.pi * (rng.uniform(2600, 3800) + 900 * np.sin(2 * np.pi * 18 * tt)) * tt) * np.hanning(n)
    z = np.zeros(N); i0 = int(t * SR); k2 = min(n, N - i0); z[i0:i0 + k2] = ch[:k2]; add(z, 0.05, rng.uniform(-0.7, 0.7))
fade = np.clip((NF / FPS - T) / 0.5, 0, 1) * np.clip(T / 0.3, 0, 1)
st = np.stack([L, R], 1) * fade[:, None]; st = np.tanh(st * 1.4) / max(1e-9, np.abs(np.tanh(st * 1.4)).max()) * 0.89
wav = Path(out).with_suffix(".wav").as_posix()
with wave.open(wav, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype(np.int16).tobytes())
subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", f"{tmp}/o%04d.png", "-i", wav,
                       "-c:v", "libx264", "-crf", "14" if W >= 1000 else "18", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                       "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", out])
print("VIDEO", out, f"{len(have)} rendered frames of {NF}")
