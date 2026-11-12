"""Quick look-dev render. python3 test_frame.py <out.png> [w h spp] [shot]"""
import sys, math
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import bpy
args = [a for a in sys.argv[1:]]
out = args[0]; w, h, spp = (int(args[1]), int(args[2]), int(args[3])) if len(args) > 3 else (270, 480, 16)
shot = args[4] if len(args) > 4 else "s01"
bpy.ops.wm.read_factory_settings(use_empty=True)
import build_world as BW, look as LK
BW.build_house(); BW.build_ground(); BW.build_table(); BW.build_garden(); BW.build_fence(); BW.build_surroundings()
if shot != "s01":
    BW.build_pergola()
LK.setup_sky(elev_deg=20, rot_deg=125)
LK.setup_render(w, h, spp)
if shot == "s01":
    LK.camera("CAM", (2.15, -2.55, 1.06), (-1.5, 1.0, 1.0), lens=32, fstop=3.5, focus=3.0)
elif shot == "s09":
    LK.camera("CAM", (9.5, -6.5, 1.7), (-1.0, 0.3, 1.6), lens=32, fstop=8)
elif shot == "macro":
    LK.camera("CAM", (-1.05, -2.25, 2.25), (-1.72, -2.95, 2.47), lens=85, fstop=4.0)
bpy.context.scene.render.filepath = out
bpy.ops.render.render(write_still=True)
import numpy as np
im = bpy.data.images.load(out); a = np.array(im.pixels[:]).reshape(-1, 4)[:, :3]
print("MEAN", a.mean(0).round(3), "P99", np.percentile(a.mean(1), 99).round(3))
print("SAVED", out)
