"""Tessellate STEP files to high-density binary STL (mm units), one STL per solid.
Usage: python3 -I step_to_stl.py <step_dir> <out_dir>"""
import sys, glob, os, re, json
from OCP.STEPControl import STEPControl_Reader
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
report = {}
for f in sorted(glob.glob(os.path.join(src, "*.step"))):
    name = os.path.basename(f)[:-5]
    name = name.replace("#U00f3", "o").replace("#U017c", "z").replace("#U0105", "a")
    name = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")
    r = STEPControl_Reader(); r.ReadFile(f); r.TransferRoots(); shape = r.OneShape()
    # 0.02 mm linear / 0.1 rad angular: smooth bends and holes on macro shots
    BRepMesh_IncrementalMesh(shape, 0.02, False, 0.1, True)
    e = TopExp_Explorer(shape, TopAbs_SOLID); i = 0; parts = []
    while e.More():
        s = e.Current(); p = os.path.join(out, f"{name}_s{i}.stl")
        w = StlAPI_Writer(); w.ASCIIMode = False; w.Write(s, p)
        b = Bnd_Box(); BRepBndLib.Add_s(s, b, False); lo, hi = b.CornerMin(), b.CornerMax()
        parts.append({"file": os.path.basename(p), "bytes": os.path.getsize(p),
                      "min": [lo.X(), lo.Y(), lo.Z()], "max": [hi.X(), hi.Y(), hi.Z()]})
        i += 1; e.Next()
    report[name] = parts
    print(name, [(p["file"], round(p["bytes"]/1e6, 1)) for p in parts])
json.dump(report, open(os.path.join(out, "cad_manifest.json"), "w"), indent=1)
