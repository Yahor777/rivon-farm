import sys, os, json
from OCP.STEPControl import STEPControl_Reader
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID
import trimesh
src, out = sys.argv[1], sys.argv[2]
r = STEPControl_Reader(); st = r.ReadFile(src); assert st == 1, st
r.TransferRoots(); shp = r.OneShape()
BRepMesh_IncrementalMesh(shp, 0.05, False, 0.2, True)   # 0.05 mm linear deflection
n = 0; e = TopExp_Explorer(shp, TopAbs_SOLID)
while e.More(): n += 1; e.Next()
w = StlAPI_Writer(); w.ASCIIMode = False; w.Write(shp, out)
m = trimesh.load(out)
print(json.dumps(dict(src=os.path.basename(src), solids=n, tris=len(m.faces), watertight=bool(m.is_watertight),
  bbox_min=[round(float(v),2) for v in m.bounds[0]], bbox_max=[round(float(v),2) for v in m.bounds[1]], size=[round(float(v),2) for v in m.extents], volume_cm3=round(float(m.volume)/1000,1))))
