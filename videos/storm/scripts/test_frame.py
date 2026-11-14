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
import design as D
bad = D.build_all_v2(with_pergola=shot in ("macro", "s09", "pergola", "rain_under", "final", "splash"))   # pergola arrives in the time-freeze
print("PERGOLA_ZONE_CONFLICTS", bad)
import yard as YD
print("\n".join("YD " + l for l in YD.build(lit=shot in ("pergola", "rain_under", "final", "splash"))))
import props as PR
print("\n".join("PR " + l for l in PR.real_cutlery()))
import cozy as CZ
if bpy.data.collections.get("PERGOLA"):
    CZ.glass_roof()
    print("\n".join("CZ " + l for l in CZ.LOG))
D.realism_pass()
import refine as RF
for line in RF.apply_all():
    pass
LK.setup_sky(elev_deg=float(__import__("os").environ.get("SUN_EL", 32)), rot_deg=float(__import__("os").environ.get("SUN_ROT", 135)))
import refine2 as RF2
for line in RF2.apply_all():
    pass
if __import__("os").environ.get("HDRI", "kloofendal_48d_partly_cloudy_puresky") != "none":
    RF2.setup_hdri_sky(rot_deg=float(__import__("os").environ.get("SUN_ROT", 135)))
print("\n".join("RF2 " + l for l in RF2.LOG))
if __import__("os").environ.get("WEAR", "1") == "1":
    import refine3 as RF3
    print("\n".join("RF3 " + l for l in RF3.apply_all()))
if bpy.data.collections.get("PERGOLA"):              # after refine (its interior pass deletes every lamp in the scene)
    CZ.warm_lights(on=shot in ("pergola", "rain_under", "final", "splash")); print("CZ " + CZ.LOG[-1])
    if shot in ("pergola", "rain_under", "final", "splash"):
        CZ.cozy_extras(); print("CZ " + CZ.LOG[-1])
LK.setup_render(w, h, spp)
RF.render_v2()
if __import__("os").environ.get("CLOUDS", "0") == "1":
    LK.build_clouds("fair")
if shot == "s01":
    LK.camera("CAM", (2.15, -2.55, 1.06), (-1.5, 1.0, 1.0), lens=32, fstop=3.5, focus=3.0)
elif shot == "wide":
    LK.camera("CAM", (7.4, -5.6, 1.25), (-2.4, 0.9, 2.05), lens=24, fstop=8.0, focus=9.5)
elif shot in ("glass", "freeze", "splash"):
    import storm_lib as S
    g = bpy.data.objects["wine_glass_0"]; gx, gy, gz = g.location
    wine_top = gz + 0.1 + 0.125 * 0.34
    drop_z = wine_top + 0.0045                     # frozen 4.5 mm above the wine surface, just before contact
    if shot == "splash":                           # c10: the one drop that got under the roof lands in the wine
        CZ.splash(gx + 0.004, gy - 0.003, wine_top)
    else:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=0.0023, location=(gx + 0.004, gy - 0.003, drop_z))
        d = bpy.context.object; d.name = "hero_drop"; d.scale = (1.0, 1.0, 0.86)          # falling drops are slightly oblate
        d.data.materials.append(S.mat_glass("rain_water", (1, 1, 1, 1))); S.principled(d.data.materials[0]).inputs["IOR"].default_value = 1.333
        d.data.shade_smooth()
    import math as _m
    focus_far = len(sys.argv) > 6 and sys.argv[6] == "far"
    dist = 0.30; cz = drop_z + 0.024                 # eye 2.4 cm above the drop: at 6 mm the underside of the wine surface
                                                     # (total internal reflection) mirrored the bowl as dark arcs
    if shot == "freeze":                                 # c05: time stopped - the drop in the lower third, rim + bowl readable
        cz2 = drop_z + 0.016
        LK.camera("CAM", (gx - 0.25, gy - 0.003, cz2), (gx + 1.0, gy + 0.03, cz2 + 1.25 * _m.tan(_m.radians(0.6))),
                  lens=85, fstop=11.0, focus=0.25)
    elif len(sys.argv) > 6 and sys.argv[6] == "tight":     # end of the push-in: the frozen drop fills the frame
        dz = drop_z + 0.0022
        LK.camera("CAM", (gx - 0.13, gy - 0.003, dz), (gx + 1.0, gy + 0.008, dz - 1.13 * _m.tan(_m.radians(2.0))),
                  lens=100, fstop=8.0, focus=0.132)
    else:
        LK.camera("CAM", (gx - dist, gy - 0.004, cz), (gx + 1.0, gy + 0.115, cz - (1.0 + dist) * _m.tan(_m.radians(2.3))),
                  lens=50, fstop=11.0 if focus_far else 7.1, focus=60.0 if focus_far else dist)
elif shot == "glassbg":
    g = bpy.data.objects["wine_glass_0"]; gx, gy, gz = g.location; wine_top = gz + 0.1 + 0.125 * 0.34
    c = LK.camera("CAM", (gx - 0.23, gy - 0.012, wine_top + 0.02), (gx + 1.0, gy + 0.02, wine_top - 0.035), lens=24, fstop=64, focus=30)
    c.data.dof.use_dof = False
elif shot == "storm":                                 # c04: the storm front over the sea, seen from the deck edge
    LK.camera("CAM", (2.6, -1.3, 1.75), (40.0, 3.5, 13.5), lens=24, fstop=8.0, focus=25.0)   # sky 2/3 of the frame
elif shot == "pergola":                               # c07: the pergola standing, frozen time
    LK.camera("CAM", (5.6, -3.4, 1.45), (0.0, 0.2, 1.75), lens=24, fstop=8.0, focus=6.5)
elif shot == "rain_under":                            # c08: under the roof, looking out through the water curtain
    LK.camera("CAM", (-0.95, 0.85, 1.3), (8.0, -4.0, 1.05), lens=24, fstop=5.6, focus=2.4)
elif shot in ("final",):                              # c09: the pergola standing in the downpour, table dry under it
    LK.camera("CAM", (7.2, -4.9, 1.5), (0.0, 0.1, 1.65), lens=24, fstop=8, focus=8.5)
elif shot == "s09":
    LK.camera("CAM", (9.5, -6.5, 1.7), (-1.0, 0.3, 1.6), lens=32, fstop=8)
elif shot == "macro":
    LK.camera("CAM", (2.62, -3.98, 2.12), (1.72, -3.02, 2.56), lens=70, fstop=5.6, focus=1.38)   # outer corner Trojak C2 from the lawn
WEATHER = __import__("os").environ.get("WEATHER", {"storm": "storm", "freeze": "freeze", "macro": "freeze", "pergola": "freeze", "splash": "rain",
                                                    "rain_under": "rain", "final": "clearing"}.get(shot, ""))
if WEATHER:
    import weather as WX
    print("\n".join("WX " + l for l in WX.apply(WEATHER, bpy.context.scene.camera.location)))
    bpy.context.scene.view_settings.exposure += {"macro": 1.0, "freeze": 0.3}.get(shot, 0.0)
    if WEATHER in ("rain", "clearing") and bpy.data.collections.get("PERGOLA"):
        CZ.roof_drops(); print("CZ " + CZ.LOG[-1])   # per-shot exposure, as a photographer would
bpy.context.scene.render.filepath = out
bpy.ops.render.render(write_still=True)
if __import__("os").environ.get("AERIAL", "1") == "1":
    LK.render_haze_pass(out.replace(".png", "_haze.png"))
import numpy as np
im = bpy.data.images.load(out); a = np.array(im.pixels[:]).reshape(-1, 4)[:, :3]
print("MEAN", a.mean(0).round(3), "P99", np.percentile(a.mean(1), 99).round(3))
print("SAVED", out)
