"""Neutral-background test of the hero wine glass (brief §4): seamless grey sweep, one large soft key from behind-left
(typical drinks pack-shot), camera at the same height/angle as the in-scene macro. python3 glass_lab.py out.png [w h spp]"""
import sys, math
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import bpy
args = sys.argv[1:]; out = args[0]
w, h, spp = (int(args[1]), int(args[2]), int(args[3])) if len(args) > 3 else (540, 960, 256)
bpy.ops.wm.read_factory_settings(use_empty=True)
import storm_lib as S, build_world as BW, look as LK
c = S.coll("LAB")
BW.build_tableware(c, 0.0)
for o in list(c.objects):
    if o.name not in ("wine_glass_0", "wine_0"):
        bpy.data.objects.remove(o)
g = bpy.data.objects["wine_glass_0"]; g.location = (0, 0, 0); bpy.data.objects["wine_0"].location = (0, 0, 0)
# sweep: floor curving up into a back wall, mid grey
import bmesh
bm = bmesh.new(); prof = [(x, 0.0) for x in (-1.0, 0.2)] + [(0.2 + 0.4 * math.sin(a), 0.4 - 0.4 * math.cos(a)) for a in [i * math.pi / 2 / 12 for i in range(1, 13)]] + [(0.6, 1.5)]
rows = [[bm.verts.new((x, y, z)) for (x, z) in prof] for y in (-1.5, 1.5)]
for i in range(len(prof) - 1):
    bm.faces.new([rows[0][i], rows[0][i + 1], rows[1][i + 1], rows[1][i]])
me = bpy.data.meshes.new("sweep"); bm.to_mesh(me); bm.free(); sw = bpy.data.objects.new("sweep", me); c.objects.link(sw)
me.materials.append(S.mat_simple("sweep_grey", (0.42, 0.42, 0.42), rough=0.6)); me.shade_smooth()
sc = bpy.context.scene
wd = bpy.data.worlds.new("lab"); sc.world = wd; wd.use_nodes = True; wd.node_tree.nodes["Background"].inputs[1].default_value = 0.15
for nm, loc, size, e in [("key", (0.75, 0.35, 0.55), 0.9, 160), ("fill", (-1.2, -0.6, 0.6), 1.2, 25)]:
    L = bpy.data.lights.new(nm, "AREA"); L.size = size; L.energy = e; L.shape = "DISK"
    o = bpy.data.objects.new(nm, L); c.objects.link(o); o.location = loc
    from mathutils import Vector
    o.rotation_euler = (Vector((0, 0, 0.14)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
LK.setup_render(w, h, spp)
sc.view_settings.exposure = 0.0
cam = LK.camera("CAM", (-0.30, -0.004, 0.155), (1.0, 0.1, 0.13), lens=50, fstop=8.0, focus=0.30)
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
print("SAVED", out)
