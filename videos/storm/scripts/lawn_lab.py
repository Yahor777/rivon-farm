"""Lawn lab: a 6 x 6 m patch of lawn v3 at full density, seen like the foreground of the wide/final shots
(camera 1.5 m high, 24 mm). python3 -I lawn_lab.py out.png [sun|overcast|rain] [w h spp]"""
import sys, math
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import bpy
a = sys.argv[1:]; out = a[0]; state = a[1] if len(a) > 1 else "sun"
w, h, spp = (int(a[2]), int(a[3]), int(a[4])) if len(a) > 4 else (540, 960, 64)
bpy.ops.wm.read_factory_settings(use_empty=True)
import storm_lib as S, look as LK, refine2 as RF2, lawn3 as L3
c = S.coll("LAB")
bpy.ops.mesh.primitive_grid_add(x_subdivisions=60, y_subdivisions=60, size=6.0, location=(0, 0, 0))
g = bpy.context.object; g.name = "lawn"; S.link(g, c)
soil = S.ph_material("forrest_ground_01", "lawn_soil"); S.calm_albedo(soil, (0.11, 0.14, 0.05), keep=0.5); soil["tinted"] = 1
g.data.materials.append(soil); S.uv_box(g, 2.0)
vg = g.vertex_groups.new(name="density"); vg.add([v.index for v in g.data.vertices], 1.0, "REPLACE")
print("\n".join(L3.build(g, 36.0)))
LK.setup_sky(32, 135); LK.setup_render(w, h, spp)
if state == "sun":
    RF2.setup_hdri_sky(135.0)
else:
    import weather as WX
    WX._sky("rain" if state == "rain" else "storm"); WX.lawn_overcast(state)
    bpy.context.scene.view_settings.exposure += 1.5
LK.camera("CAM", (0.4, -3.1, 1.45), (0.0, 3.0, 0.0), lens=24, fstop=8.0, focus=3.0)
bpy.context.scene.render.use_motion_blur = False
bpy.context.scene.render.filepath = out
bpy.ops.render.render(write_still=True)
print("SAVED", out)
