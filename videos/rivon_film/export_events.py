"""Sound-event list straight from the animation (bpy): every seat of a part (assembly and the reversed disassembly), the two big
frame moves, cuts, hero.  -> post/events2.json  usage: python export_events.py"""
import sys, json
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import bpy, numpy as np
import film_lib as FL, film_anim as AN
for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
FL.build_pergola("PERGOLA"); bpy.context.view_layer.update()
A = AN.Anim()
def slow(a): return AN._speed(a) < 0.7
def dis_frame(a_evt):
    fs = np.arange(690, 760, 0.1); ds = np.array([AN.disassembly_clock(x) for x in fs]); i = np.argmin(np.abs(ds - a_evt)); return float(fs[i])
ev = []
for pid, S in A.S.items():
    kind = pid.split("_")[0]
    if pid.startswith("SCREW"): kind = "SCREW_" + A.screw_part[pid].split("_")[0]
    if pid.startswith(("BEAM_LONG", "BEAM_END")) and S["dir"] is None: continue          # long beams just arrive, the trojaks clack on
    ev.append(dict(kind=kind, id=pid, f=AN.frame_of_clock(S["seat"]), slow=slow(S["seat"]), off=False))
for nm, (t0, t1) in AN.GROUP_T.items():
    ev.append(dict(kind="JOIN" if nm == "join" else "LOWER", id=nm, f=AN.frame_of_clock(t1), slow=slow(t1), off=False))
ev.append(dict(kind="SLOWMO", id="slow", f=0, slow=False, off=False, windows=[[AN.frame_of_clock(a0), AN.frame_of_clock(a1)] for a0, a1 in AN.SLOWMO]))
json.dump(sorted(ev, key=lambda e: e["f"]), open(HERE / "post" / "events2.json", "w"), indent=0)
print(len(ev), "events")
