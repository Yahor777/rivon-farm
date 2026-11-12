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
BW.build_house(); BW.build_ground(); BW.build_table(); BW.build_garden(); BW.build_fence(); BW.build_surroundings(); BW.build_coast()
if shot not in ("s01", "wide", "glass", "glassbg"):      # before the storm the terrace is still open (pergola arrives in the time-freeze)
    BW.build_pergola()
LK.setup_sky(elev_deg=20, rot_deg=125)
LK.setup_render(w, h, spp)
if shot == "s01":
    LK.camera("CAM", (2.15, -2.55, 1.06), (-1.5, 1.0, 1.0), lens=32, fstop=3.5, focus=3.0)
elif shot == "wide":
    LK.camera("CAM", (5.9, -4.6, 1.45), (-2.6, 0.7, 2.0), lens=26, fstop=8.0, focus=8.0)
elif shot == "glass":
    import storm_lib as S
    g = bpy.data.objects["wine_glass_0"]; gx, gy, gz = g.location
    wine_top = gz + 0.1 + 0.125 * 0.34
    drop_z = wine_top + 0.0045                     # frozen 4.5 mm above the wine surface, just before contact
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=0.0023, location=(gx + 0.004, gy - 0.003, drop_z))
    d = bpy.context.object; d.name = "hero_drop"; d.scale = (1.0, 1.0, 0.86)          # falling drops are slightly oblate
    d.data.materials.append(S.mat_glass("rain_water", (1, 1, 1, 1))); S.principled(d.data.materials[0]).inputs["IOR"].default_value = 1.333
    d.data.shade_smooth()
    import math as _m
    focus_far = len(sys.argv) > 6 and sys.argv[6] == "far"
    dist = 0.30; cz = drop_z + 0.006                 # eye just above the wine: surface reads as a thin ellipse, drop above it
    if len(sys.argv) > 6 and sys.argv[6] == "tight":     # end of the push-in: the frozen drop fills the frame
        dz = drop_z + 0.0022
        LK.camera("CAM", (gx - 0.13, gy - 0.003, dz), (gx + 1.0, gy + 0.008, dz - 1.13 * _m.tan(_m.radians(2.0))),
                  lens=100, fstop=8.0, focus=0.132)
    else:
        LK.camera("CAM", (gx - dist, gy - 0.004, cz), (gx + 1.0, gy + 0.115, cz - (1.0 + dist) * _m.tan(_m.radians(1.0))),
                  lens=50, fstop=11.0 if focus_far else 7.1, focus=60.0 if focus_far else dist)
elif shot == "glassbg":
    g = bpy.data.objects["wine_glass_0"]; gx, gy, gz = g.location; wine_top = gz + 0.1 + 0.125 * 0.34
    c = LK.camera("CAM", (gx - 0.23, gy - 0.012, wine_top + 0.02), (gx + 1.0, gy + 0.02, wine_top - 0.035), lens=24, fstop=64, focus=30)
    c.data.dof.use_dof = False
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
