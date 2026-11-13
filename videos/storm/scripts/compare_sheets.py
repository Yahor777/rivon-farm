"""BEFORE / AFTER sheets + 1:1 zoom crops (wood, foliage, glass, facade). python3 compare_sheets.py before_dir after_dir out_dir"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

B, A, O = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]); LB = sys.argv[4] if len(sys.argv) > 4 else "ДО (q2)"; LA = sys.argv[5] if len(sys.argv) > 5 else "ПОСЛЕ (q3)"; O.mkdir(parents=True, exist_ok=True)
try:
    F = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 34)
    f2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
except OSError:
    F = f2 = ImageFont.load_default()

CROPS = {  # shot: [(label, (x0, y0, x1, y1)) in 1080x1920 pixels]
    "wide": [("листва / деревья", (0, 650, 420, 1150)), ("газон, передний план", (0, 1480, 700, 1920)),
             ("фасад, остекление", (380, 560, 860, 1000))],
    "s01": [("доска террасы", (0, 1450, 700, 1920)), ("стул, тик", (560, 1150, 1080, 1700)),
            ("штукатурка, софит", (650, 120, 1080, 560))],
    "glass": [("вино, мениск, капля", (380, 880, 1000, 1400)), ("стекло, кромка", (450, 300, 1000, 760)),
              ("фон: пирс, дымка", (0, 700, 520, 1100))],
}


def label(im, text, sub=None):
    d = ImageDraw.Draw(im); d.rectangle((0, 0, im.width, 50 if not sub else 84), fill=(0, 0, 0))
    d.text((14, 8), text, font=F, fill=(255, 255, 255))
    if sub:
        d.text((14, 50), sub, font=f2, fill=(210, 210, 210))
    return im


for shot in CROPS:
    b = Image.open(B / f"{shot}_photo.png").convert("RGB"); a = Image.open(A / f"{shot}_photo.png").convert("RGB")
    half = (540, 960)
    sheet = Image.new("RGB", (1080 + 20, 960), (20, 20, 20))
    sheet.paste(label(b.resize(half, Image.LANCZOS), LB), (0, 0))
    sheet.paste(label(a.resize(half, Image.LANCZOS), LA), (560, 0))
    sheet.save(O / f"compare_{shot}.jpg", quality=92)
    for k, (name, box) in enumerate(CROPS[shot]):
        cb, ca = b.crop(box), a.crop(box)
        w, h = cb.size; s = min(1.0, 700 / w) * 1.0
        cb = cb.resize((int(w * s), int(h * s)), Image.LANCZOS); ca = ca.resize((int(w * s), int(h * s)), Image.LANCZOS)
        z = Image.new("RGB", (cb.width * 2 + 16, cb.height), (20, 20, 20))
        z.paste(label(cb, "ДО", name), (0, 0)); z.paste(label(ca, "ПОСЛЕ", name), (cb.width + 16, 0))
        z.save(O / f"zoom_{shot}_{k}.jpg", quality=92)
print("SHEETS", O)
