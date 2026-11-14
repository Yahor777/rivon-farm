"""Assemble THE STORM: frames f0001..f0600 (any subset; gaps are held) -> 30 fps MP4 with the end card (RIVON logo +
'Mały detal. Wielkie możliwości.') and a synthesized soundtrack of real-world sounds (sea, wind, thunder, impacts of
wood on steel, rain on glass, the drop) - no melody. python3 finish_storm.py <frames_dir> <film.json> <out.mp4>"""
import sys, json, subprocess, wave, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = Path(__file__).resolve().parent; POST = HERE.parent.parent / "rivon_film" / "post"
fr_dir, cfg, out = Path(sys.argv[1]), json.load(open(sys.argv[2])), sys.argv[3]
FPS, NF = 30, 990
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
    a = (f - 946) / 26.0
    im = end_card(im, min(1.0, a)) if a > 0 else im
    if f > 980:                                             # last 0.3 s: gentle fade to black
        im = Image.blend(im, Image.new("RGB", im.size, (0, 0, 0)), min(1.0, (f - 980) / 10.0) * 0.85)
    im.save(f"{tmp}/o{f:04d}.png")

# ---- sound: real recordings mixed to picture (sound_storm.py); silent film if the recordings are not there
wav = Path(out).with_suffix(".wav").as_posix()
sfx_dir = Path(sys.argv[4]) if len(sys.argv) > 4 else None
if sfx_dir and sfx_dir.exists():
    subprocess.check_call([sys.executable, str(HERE / "sound_storm.py"), str(sfx_dir), str(HERE.parent / "sound" / "sources.json"), wav])
else:
    import wave as _w
    with _w.open(wav, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000); w.writeframes(b"\0" * (48000 * NF // FPS * 4))
subprocess.check_call(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", f"{tmp}/o%04d.png", "-i", wav,
                       "-c:v", "libx264", "-crf", "14" if W >= 1000 else "18", "-preset", "veryfast", "-pix_fmt", "yuv420p",
                       "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", out])
print("VIDEO", out, f"{len(have)} rendered frames of {NF}")
