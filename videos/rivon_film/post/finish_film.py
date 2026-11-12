"""RIVON film post: cinematic grade + the lab->yard RING transition (v6) + end card, then H.264 MP4.
v6: frames f1548..f1627 in the frames dir are the YARD renders of frames 548..627; a glowing ring expands across the floor from
the pergola (radius in metres on the ground plane, from the known orbit camera) and behind it the lab becomes the yard.
End card: the camera holds on the engraved RIVON mark of the hero connector, everything darkens except the mark, the engraved mark
becomes a clean white graphic (cut from the same render, pixel-aligned), glides to the centre, the wordmark and the CTA appear below.
usage: python3 finish_film.py <frames_dir> <out.mp4> [--crf 16] [--audio film.wav] [--fps 30]
       python3 finish_film.py --still <frame.png> <frame_index> <out.png>"""
import sys, os, argparse, subprocess, glob, json
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); FD = os.path.join(HERE, "fonts") + os.sep
CUTS = ()                     # lab-only film: one continuous take, no cuts
TN = 8                                                              # frames on each side of a cut used by the push-through transition
CTA_LINES = ("Jedno rozwiązanie.", "Wiele możliwości.")           # exact copy: "Jedno rozwiązanie. Wiele możliwości."
D0, D1 = 652, 668            # darkening (fade to black)
G0, G1 = 662, 676            # icon fades in
M0, M1 = 0, 1                # (no glide in v6: the icon appears in place)
W0, W1 = 672, 684            # wordmark
C0 = 678                     # CTA lines (second one 6 frames later, 12-frame fades)
ICON_FINAL = (0.5, 0.42, 0.25)          # centre x, centre y (fraction of frame), width (fraction of frame width)
WORD_Y, WORD_W = 0.525, 0.44
CTA_Y = 0.65
ap = argparse.ArgumentParser(); ap.add_argument("frames", nargs="?"); ap.add_argument("out", nargs="?"); ap.add_argument("--crf", type=int, default=16)
ap.add_argument("--audio", default=None); ap.add_argument("--still", nargs=3, default=None); ap.add_argument("--fps", type=int, default=30)
a = ap.parse_args()

_m = Image.open(os.path.join(HERE, "rivon_logo.png")).convert("L"); _bb = _m.point(lambda v: 255 if v > 40 else 0).getbbox(); WORD = _m.crop(_bb)
_ICON = None
if os.path.exists(os.path.join(HERE, "logo_icon.png")):
    _ICON = Image.open(os.path.join(HERE, "logo_icon.png")).convert("L"); PLACE = list(ICON_FINAL)      # v6: icon appears in its final place
def ease(x): x = float(np.clip(x, 0, 1)); return x * x * (3 - 2 * x)
def spaced(d, xy, text, fnt, fill, sp=0.0):
    x, y = xy
    for ch in text: d.text((x, y), ch, font=fnt, fill=fill); x += d.textlength(ch, font=fnt) + sp
def spaced_len(d, text, fnt, sp=0.0): return sum(d.textlength(ch, font=fnt) + sp for ch in text) - sp

_rng = np.random.default_rng(3); _VIG = {}
def grade(a):
    from scipy.ndimage import gaussian_filter
    h, w = a.shape[:2]; s = max(1, w / 1080.0)
    bl = np.stack([gaussian_filter(a[..., c], 9 * s) for c in range(3)], 2); bl2 = np.stack([gaussian_filter(a[..., c], 26 * s) for c in range(3)], 2)
    hl = np.clip(bl - 0.6, 0, 1) * 2.0; hl2 = np.clip(bl2 - 0.5, 0, 1) * 2.0
    a = 1 - (1 - a) * (1 - 0.10 * hl * np.array([1.0, 0.85, 0.7], np.float32)) * (1 - 0.06 * hl2)            # halation + bloom
    a = a + 0.10 * (a - 0.5) * (1 - np.abs(2 * a - 1)) * 2                                                     # gentle S-curve
    lum = (a * np.array([0.2126, 0.7152, 0.0722], np.float32)).sum(2, keepdims=True)
    a = a + (np.array([1.04, 1.0, 0.94], np.float32) - 1) * lum * 0.5 + (np.array([0.97, 1.0, 1.03], np.float32) - 1) * (1 - lum) * 0.25     # warm highlights / cool shadows
    a = lum + (a - lum) * 1.06
    if (h, w) not in _VIG:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32); rx = (xx - w / 2) / (w / 2); ry = (yy - h / 2) / (h / 2)
        _VIG[(h, w)] = (1 - 0.12 * np.clip(rx ** 2 * 0.7 + ry ** 2 * 0.45, 0, 1.4) ** 1.2)[..., None]
    a = a * _VIG[(h, w)]
    a = a + _rng.normal(0, 0.0045, (h, w, 1)).astype(np.float32) * (1 - 0.5 * lum)
    return np.clip(a, 0, 1)


# ---------------------------------------------------------------------------------------------- push-through transition
def trans_u(f):
    """0 = no transition; 1 = the cut frame itself.  Symmetric around each cut (TN frames before and after)."""
    u = 0.0
    for c in CUTS:
        if c - TN <= f < c: d = c - f; u = max(u, (TN - d + 1) / TN)
        elif c <= f < c + TN: d = f - c + 1; u = max(u, (TN - d + 1) / TN)
    return u

def push_through(a, u, n=28):
    """zoom towards the pergola with growing radial motion blur and a light chromatic split; no white flash."""
    h, w = a.shape[:2]; cx, cy = w * 0.5, h * 0.50
    sc = 1.0 + 0.55 * u ** 2.0; bw = 0.03 + 0.19 * u ** 1.6
    acc = np.zeros_like(a)
    for j in range(n):
        t = j / (n - 1) - 0.5; s = sc * (1 + bw * t)
        for c, ch in enumerate((1.010, 1.0, 0.990)):                                 # R / G / B scale split
            M = cv2.getRotationMatrix2D((cx, cy), 0.0, s * ch)
            acc[..., c] += cv2.warpAffine(a[..., c], M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    acc /= n
    lift = 1.0 + 0.22 * u ** 2.0
    return np.clip(acc * lift, 0, 1)


# ---------------------------------------------------------------------------------------------- end card
def endcard(a, f):
    h, w = a.shape[:2]
    if f < D0 or _ICON is None: return a
    cxp, cyp, wp = PLACE
    td = ease((f - D0) / (D1 - D0))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32); r = np.hypot((xx - cxp * w) / (wp * w), (yy - cyp * h) / (wp * w))
    keep = np.exp(-(r / 1.2) ** 2)[..., None]                                       # the area around the mark darkens last
    k = np.clip(td * 1.3 - 0.3 * keep * td - 0.0, 0, 1)
    k = np.where(td >= 1.0, 1.0, k)
    a = a * (1 - k)
    img = Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)).convert("RGBA")
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    # graphic icon: starts exactly on the engraved mark, then glides / grows to its final place
    tg = ease((f - G0) / (G1 - G0)); tm = ease((f - M0) / (M1 - M0))
    if tg > 0:
        cx = cxp + (ICON_FINAL[0] - cxp) * tm; cy = cyp + (ICON_FINAL[1] - cyp) * tm; wd = wp + (ICON_FINAL[2] - wp) * tm
        iw = max(2, int(round(wd * w))); ih = max(2, int(round(_ICON.height * iw / _ICON.width)))
        ic = _ICON.resize((iw, ih), Image.LANCZOS)
        g = Image.new("RGBA", (iw, ih), (255, 255, 255, 0)); g.putalpha(ic.point(lambda v: int(v * tg)))
        lay.alpha_composite(g, (int(round(cx * w - iw / 2)), int(round(cy * h - ih / 2))))
    tw = ease((f - W0) / (W1 - W0))
    if tw > 0:
        ww = int(w * WORD_W); wh = int(round(WORD.height * ww / WORD.width)); wm = WORD.resize((ww, wh), Image.LANCZOS)
        g = Image.new("RGBA", (ww, wh), (255, 255, 255, 0)); g.putalpha(wm.point(lambda v: int(v * tw)))
        lay.alpha_composite(g, ((w - ww) // 2, int(h * WORD_Y + (1 - tw) * 10)))
    d = ImageDraw.Draw(lay); fnt = ImageFont.truetype(FD + "Inter-Medium.otf", int(w * 0.056))
    for i, line in enumerate(CTA_LINES):
        tl = ease((f - C0 - i * 6) / 12.0)
        if tl <= 0: continue
        wd2 = spaced_len(d, line, fnt, 1.5); x = (w - wd2) / 2; y = h * CTA_Y + i * int(w * 0.082) + (1 - tl) * 16
        spaced(d, (x, y), line, fnt, (255, 255, 255, int(255 * tl)), 1.5)
    return np.asarray(Image.alpha_composite(img, lay).convert("RGB"), np.float32) / 255.0


# ---------------------------------------------------------------------------------------------- v6b lab -> yard WHIP transition
# The orbit camera whips ~110 deg in 20 frames (speed peaks at T_WHIP); the picture gets a horizontal motion blur that follows the
# real angular speed, the two worlds cross-blend inside the blur (lab frames T-3..T-1 mixed with their yard renders f1000+), plus a
# soft light streak.  Pergola stays centred, so it reads as one continuous move.
T_WHIP, YOFF, WHIP_HALF = 336, 1000, 10.0
def _e5(u): u = min(max(u, 0.0), 1.0); return u * u * u * (u * (6 * u - 15) + 10)
def whip_speed(f):                     # extra degrees per frame from the whip at frame f
    return 110.0 * (_e5((f + 0.5 - (T_WHIP - WHIP_HALF)) / (2 * WHIP_HALF)) - _e5((f - 0.5 - (T_WHIP - WHIP_HALF)) / (2 * WHIP_HALF)))
def hblur(a, px):
    """horizontal motion blur of px pixels (box kernel, done with cv2.blur on each channel)."""
    k = int(max(1, round(px)))
    if k <= 1: return a
    return cv2.blur(a, (k, 1), borderType=cv2.BORDER_REFLECT)
def whip(a, f):
    h, w = a.shape[:2]; sp = whip_speed(f)
    if sp < 0.4: return a
    deg_per_px = (2 * np.degrees(np.arctan(18.0 / 27.0 * w / h))) / w        # horizontal FOV / width (lens ~27-30)
    px = sp / deg_per_px * 0.9
    out = hblur(a, px)
    k = min(1.0, sp / 10.0)
    streak = hblur(np.clip(a - 0.6, 0, 1), px * 1.6) * 0.9 * k                 # highlights smear into light streaks
    return np.clip(out * (1 + 0.08 * k) + streak, 0, 1)


def process(path, f):
    a = grade(np.asarray(Image.open(path).convert("RGB"), np.float32) / 255.0)
    if T_WHIP <= f < T_WHIP + 3:                                     # cross-blend inside the blur (lab renders of these frames are f2000+)
        lp = os.path.join(os.path.dirname(path), f"f{f + 2000:04d}.png")
        lab = grade(np.asarray(Image.open(lp).convert("RGB"), np.float32) / 255.0)
        m = (f - T_WHIP + 1) / 4.0; a = lab * (1 - m) + a * m
    a = whip(a, f); a = endcard(a, f)
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8))


def process_one(path, f):
    a = grade(np.asarray(Image.open(path).convert("RGB"), np.float32) / 255.0)
    u = trans_u(f)
    if u > 0: a = push_through(a, u)
    a = endcard(a, f)
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8))


if a.still:
    p, f, o = a.still; process(p, int(f)).save(o); sys.exit(0)
fs = sorted(p for p in glob.glob(os.path.join(a.frames, "f*.png")) if int(os.path.basename(p)[1:5]) < YOFF); assert fs, "no frames"
tmp = a.out + ".frames"; os.makedirs(tmp, exist_ok=True)
for i, p in enumerate(fs):
    f = int(os.path.basename(p)[1:5]); process(p, f).save(os.path.join(tmp, f"g{i:05d}.png"))
cmd = ["ffmpeg", "-y", "-framerate", str(a.fps), "-i", os.path.join(tmp, "g%05d.png")] + (["-i", a.audio] if a.audio else []) + ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", str(a.crf), "-preset", "slow"] + (["-c:a", "aac", "-b:a", "192k", "-shortest"] if a.audio else []) + [a.out]
subprocess.run(cmd, check=True)
