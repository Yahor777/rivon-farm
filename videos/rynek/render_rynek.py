"""Render RIVON video #4 frames (Blender 5.x, Cycles CPU).
  blender -b -P render_rynek.py -- --w 1080 --h 1920 --spp 64 --start 0 --end 839 --out frames
  blender -b -P render_rynek.py -- --w 540 --h 960 --spp 64 --frames 20,140,260 --out control
Resumable: frames that already exist are skipped. Files f0000.png ..."""
import sys, os, time, argparse
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bpy
import build_rynek as B
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
ap = argparse.ArgumentParser()
ap.add_argument("--w", type=int, default=1080); ap.add_argument("--h", type=int, default=1920); ap.add_argument("--spp", type=int, default=64)
ap.add_argument("--start", type=int, default=0); ap.add_argument("--end", type=int, default=B.NFR - 1)
ap.add_argument("--frames", default=""); ap.add_argument("--out", default="frames"); ap.add_argument("--persist", type=int, default=0)
ap.add_argument("--cam", default="")        # debug: "x,y,z,tx,ty,tz" static camera
a = ap.parse_args(argv)
import numpy as np
def grade_png(path, sat=1.45, con=0.12, warm=0.03):
    # final look: richer colour + a little contrast, applied to the sRGB frame
    im = bpy.data.images.load(path); w, h = im.size
    buf = np.empty(w * h * 4, dtype=np.float32); im.pixels.foreach_get(buf); buf = buf.reshape(-1, 4)
    c = buf[:, :3]; l = (c * np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)).sum(1, keepdims=True)
    mx = c.max(1, keepdims=True); mn = c.min(1, keepdims=True)
    sl = (mx - mn) / np.maximum(mx, 1e-4)                                   # current saturation 0..1
    k = 1.0 + (sat - 1.0) * (1.0 - np.clip(sl, 0, 1) * 0.85)                # vibrance: dull colours gain most, saturated ones barely
    c = l + (c - l) * k
    c = c + np.array([warm, 0.0, -warm], dtype=np.float32) * c.mean(1, keepdims=True)
    c = np.clip(c, 0, 1); c = c * (1 - con) + c * c * (3 - 2 * c) * con
    buf[:, :3] = np.clip(c * 1.06, 0, 1)
    im.pixels.foreach_set(buf.ravel()); im.filepath_raw = path; im.file_format = 'PNG'; im.save(); bpy.data.images.remove(im)
t0 = time.time()
co, tgt = B.build(w=a.w, h=a.h, spp=a.spp)
print("BUILD %.1fs" % (time.time() - t0), flush=True)
if a.cam:
    co.animation_data_clear(); tgt.animation_data_clear()
    v = [float(x) for x in a.cam.split(",")]; co.location = v[:3]; tgt.location = v[3:6]
sc = bpy.context.scene; sc.cycles.device = 'CPU'
sc.render.use_persistent_data = bool(a.persist)
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.compression = 12
out = os.path.abspath(a.out); os.makedirs(out, exist_ok=True)
frames = [int(x) for x in a.frames.split(",")] if a.frames else list(range(a.start, a.end + 1))
for f in frames:
    path = os.path.join(out, "f%04d.png" % f)
    if os.path.exists(path): continue
    sc.frame_set(f); sc.render.filepath = path; ts = time.time()
    bpy.ops.render.render(write_still=True)
    if not os.environ.get('NOGRADE'): grade_png(path)
    print("FRAME %d  %.0fs" % (f, time.time() - ts), flush=True)
print("DONE", out)
