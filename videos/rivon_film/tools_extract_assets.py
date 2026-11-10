import bpy, re, sys
KEEP = re.compile(r"^(house|car|lawn|drive|drive2|patio|terrace|street|street2|walk_[ns]|curbs2?|fence_|thuja|shrub|fern|dandelion|weed_plant|bed[A-F]|boulders|gravel|lamppost|bollard|streetlight|pond|bay|door|chim|canopy|bench|shed_|raised|greenhouse|grass_emit|tree\d+|veg)")
DROP = re.compile(r"^(nb_house|vtree|flower|U_|L_|sh_|g0_|bbq_|lng_|lamp_|streetlight_lens)")
# keep only a few of the big trees (376k polys each)
trees = sorted([o for o in bpy.data.objects if re.match(r"^tree\d+$", o.name) and o.parent is None], key=lambda o: o.location.length)
keep_trees = set(o.name for o in trees[:6])
def keep(o):
    root = o
    while root.parent is not None: root = root.parent
    n = root.name
    if re.match(r"^tree\d+$", n): return n in keep_trees
    if DROP.match(n): return False
    return bool(KEEP.match(n)) or n.startswith("prototypes")
rm = [o for o in bpy.data.objects if not keep(o) and o.type not in ("CAMERA",)]
for o in rm: bpy.data.objects.remove(o, do_unlink=True)
for o in [o for o in bpy.data.objects if o.type in ("LIGHT","CAMERA")]: bpy.data.objects.remove(o, do_unlink=True)
# purge orphans
for _ in range(3): bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
print("objects kept", len(bpy.data.objects), "meshes", len(bpy.data.meshes), "images", len(bpy.data.images))
bpy.ops.wm.save_as_mainfile(filepath="/home/claude/film_work/assets.blend", compress=True)
