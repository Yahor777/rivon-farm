"""Cut the engraved RIVON mark out of the face-on hold render (pixel aligned) -> post/logo_icon.png (white = mark) + logo_place.json.
usage: python3 make_logo.py <hold_frame.png>"""
import sys, os, json, numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, median_filter, label
HERE = os.path.dirname(os.path.abspath(__file__))
im = Image.open(sys.argv[1]).convert("L"); W, H = im.size; a = np.asarray(im, np.float32)
x0, x1, y0, y1 = int(0.33 * W), int(0.72 * W), int(0.40 * H), int(0.60 * H)
reg = a[y0:y1, x0:x1]
BRIGHT = "--bright" in sys.argv                                     # cut-through mark showing light timber behind a dark plate
face = np.percentile(reg, 30 if BRIGHT else 70)                     # plate level
d = np.clip(((reg - face) if BRIGHT else (face - reg - 0.04 * face)) / (max(face, 20) * (1.0 if BRIGHT else 0.20)), 0, 1)
d = gaussian_filter(d, W / 1080.0 * 0.6)
bin_ = d > 0.5; lab, n = label(bin_)
if n > 1:                                                          # keep the large connected pieces only (drop specks)
    sizes = np.bincount(lab.ravel()); keep = [i for i in range(1, n + 1) if sizes[i] > 0.02 * sizes[1:].max()]
    d = d * np.isin(lab, keep)
ys, xs = np.where(d > 0.15); bx0, bx1, by0, by1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
pad = int(0.01 * W); bx0 -= pad; by0 -= pad; bx1 += pad; by1 += pad
crop = d[by0:by1, bx0:bx1]
Image.fromarray((np.clip(crop, 0, 1) * 255).astype(np.uint8)).save(os.path.join(HERE, "logo_icon.png"))
cx = (x0 + (bx0 + bx1) / 2) / W; cy = (y0 + (by0 + by1) / 2) / H; wd = (bx1 - bx0) / W
json.dump([cx, cy, wd], open(os.path.join(HERE, "logo_place.json"), "w")); print("place", cx, cy, wd, "crop", crop.shape, "face", face)
