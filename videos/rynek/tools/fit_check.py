import sys, bpy
import os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import build_restaurant as B
from mathutils.bvhtree import BVHTree
B.build(w=100,h=100,spp=1)
sc=bpy.context.scene; sc.frame_set(700); dg=bpy.context.evaluated_depsgraph_get()
def bvh(ob):
    e=ob.evaluated_get(dg); me=e.to_mesh(); me.transform(ob.matrix_world)
    t=BVHTree.FromPolygons([v.co.copy() for v in me.vertices],[tuple(p.vertices) for p in me.polygons],epsilon=0.0); e.to_mesh_clear(); return t
import mathutils
objs=[o for o in bpy.data.objects if o.type=='MESH']
metal=[o for o in objs if o.name.startswith("RIVON_")]
wood=[o for o in objs if o.name.startswith(("post","beam"))]
# gazebo 0 only: first 4 stopa/trojak, first 4 posts, first 4 beams (creation order)
def first(prefix,n): return [o for o in objs if o.name.startswith(prefix)][:n]
st=first("RIVON_Stopa",4); tj=first("RIVON_Trojak",4); po=first("post",4); be=first("beam",4)
print("counts", len(st),len(tj),len(po),len(be))
for o in po:
    o.scale=(1,1,(2.4-0.001)/2.4); o.location.z += 0.0    # shrink 1 mm about centre: 0.5 mm clearance top and bottom
bpy.context.view_layer.update(); dg=bpy.context.evaluated_depsgraph_get()
bad=0
for m in st+tj:
    tm=bvh(m)
    for w in po+be:
        n=len(tm.overlap(bvh(w)))
        if n: print("OVERLAP", m.name, "x", w.name, n); bad+=1
print("pairs checked", (len(st)+len(tj))*(len(po)+len(be)), "overlapping:", bad)
# sizes: report world bbox of one beam and post vs inner 96 mm
for w in po[:1]+be[:1]:
    print(w.name, [round(x,3) for x in w.dimensions])
