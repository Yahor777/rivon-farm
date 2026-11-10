"""Frame renderer for the RIVON film.  blender -b assets.blend -P render_film.py -- [--stills] --frames 0,1,2 --w 810 --h 1440 --spp 48 --out DIR
--stills : frame index i renders SHOT_ORDER[i] (control frames / Checkpoint C).  Output f####.png, skips frames that already exist (resumable)."""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bpy
a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(k, d=None):
    return a[a.index(k) + 1] if k in a else d
import build_film as B
W, H, SPP = int(arg("--w", 540)), int(arg("--h", 960)), int(arg("--spp", 32))
out = Path(arg("--out", "out")); out.mkdir(parents=True, exist_ok=True)
frames = [int(x) for x in arg("--frames", "0").split(",")] if "--frames" in a else list(range(int(arg("--start", 0)), int(arg("--end", 0)) + 1))
sc = B.prepare(W, H, SPP)
for f in frames:
    p = out / f"f{f:04d}.png"
    if p.exists(): print("FRAME", f, "exists"); continue
    t = time.time()
    if "--stills" in a: B.set_shot(B.SHOT_ORDER[f])
    else: B.apply_frame(f)
    sc.render.filepath = str(p); bpy.ops.render.render(write_still=True)
    print("FRAME", f, "ok", round(time.time() - t, 1), "s", flush=True)
