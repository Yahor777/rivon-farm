"""Photographic camera response applied to linear-display renders (owner: 'it looks like CG').
Real lenses/sensors leave fingerprints the renderer does not: slight barrel distortion, lateral chromatic aberration,
natural vignetting (cos^4), highlight halation/bloom, luminance-dependent sensor grain. All kept subtle (no 'effects').
Usage: python3 post_photo.py in.png out.png [--seed N]"""
import sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi


def photo(img, seed=0, distort=0.012, ca=0.0007, vignette=0.22, bloom=0.06, grain=0.011):
    h, w, _ = img.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = (w - 1) / 2, (h - 1) / 2; nrm = np.hypot(cx, cy)
    dx, dy = (xx - cx) / nrm, (yy - cy) / nrm; r2 = dx * dx + dy * dy
    out = np.empty_like(img)
    for ch, s in enumerate((1 + ca, 1.0, 1 - ca)):                      # lateral CA: R slightly larger, B smaller
        k = (1 + distort * r2) * s
        sx = cx + dx * nrm * k; sy = cy + dy * nrm * k
        out[..., ch] = ndi.map_coordinates(img[..., ch], [sy, sx], order=3, mode="reflect")
    # crop back the slight barrel overscan
    lin = np.clip(out, 0, 1) ** 2.2
    hi = np.clip(lin - 0.65, 0, None)
    glow = np.stack([ndi.gaussian_filter(hi[..., c], sigma=w * 0.012) for c in range(3)], -1)
    glow2 = np.stack([ndi.gaussian_filter(hi[..., c], sigma=w * 0.05) for c in range(3)], -1)
    lin = lin + bloom * (glow * np.array([1.0, 0.92, 0.82]) + 0.5 * glow2)
    lin *= (1 - vignette * r2 ** 1.15)[..., None]
    rng = np.random.default_rng(seed)
    lum = lin.mean(-1, keepdims=True)
    amp = grain * (0.35 + 1.6 * np.sqrt(np.clip(lum, 0, 1)) * (1 - np.clip(lum, 0, 1)))
    g = rng.normal(0, 1, (h, w, 1)).astype(np.float32)
    g = 0.75 * g + 0.25 * ndi.gaussian_filter(g, 1.1)
    lin = lin + amp * g * np.array([1.0, 0.97, 1.03])
    return np.clip(lin, 0, 1) ** (1 / 2.2)


if __name__ == "__main__":
    a = np.asarray(Image.open(sys.argv[1]).convert("RGB")).astype(np.float32) / 255
    seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 0
    o = photo(a, seed)
    Image.fromarray((o * 255 + 0.5).astype(np.uint8)).save(sys.argv[2])
    print("POST", sys.argv[2])
