"""Real cutlery instead of the placeholder bars (they read as chopsticks): a table fork and a table knife modelled from
real dimensions (fork 200 mm, 4 tines; knife 215 mm, rounded blade), stainless, handle resting on the table, head raised
by the bend like real cutlery."""
import math
import bpy, bmesh
from mathutils import Vector
import storm_lib as S

LOG = []


def _outline(name, pts, thick, c, mat, bend):
    """pts: closed outline in the XY plane (x = length axis, metres). Extruded, beveled, subdivided, then bent: z = bend(x)."""
    bm = bmesh.new()
    vs = [bm.verts.new((x, y, 0.0)) for x, y in pts]
    f = bm.faces.new(vs)
    bmesh.ops.triangulate(bm, faces=[f])
    r = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
    for v in [e for e in r["geom"] if isinstance(e, bmesh.types.BMVert)]:
        v.co.z += thick
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); c.objects.link(o); me.materials.append(mat)
    rm = o.modifiers.new("rm", "REMESH"); rm.mode = "SHARP"; rm.octree_depth = 8; rm.use_remove_disconnected = False
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.modifier_apply(modifier="rm")
    for v in me.vertices:
        v.co.z += bend(v.co.x)
    sm = o.modifiers.new("sm", "SMOOTH"); sm.factor = 0.5; sm.iterations = 3
    me.shade_smooth()
    return o


def fork(name, c, mat):
    L = 0.200
    pts = [(0.0, 0.0)]
    # handle 0..0.115 (width 10 -> 14 mm), neck 0.115..0.145 (5 mm), head 0.145..0.200 (24 mm wide, 4 tines from 0.165)
    right = [(0.0, -0.0050), (0.03, -0.0065), (0.09, -0.0072), (0.115, -0.0040), (0.140, -0.0028), (0.150, -0.0095),
             (0.165, -0.0120)]
    tines = []
    tw, gap = 0.0042, 0.0022
    y = -0.0120
    for t in range(4):
        y0 = y; y1 = y + tw
        tines += [(0.200 if t in (0, 3) else 0.201, y0 + 0.0004), (0.2015, (y0 + y1) / 2), (0.200 if t in (0, 3) else 0.201, y1 - 0.0004)]
        if t < 3:
            tines += [(0.168, y1), (0.168, y1 + gap)]
        y = y1 + gap
    left = [(0.165, 0.0120), (0.150, 0.0095), (0.140, 0.0028), (0.115, 0.0040), (0.09, 0.0072), (0.03, 0.0065), (0.0, 0.0050)]
    outline = right + tines + left
    return _outline(name, outline, 0.0022, c, mat, lambda x: 0.0 if x < 0.11 else 0.0105 * math.sin(min(1.0, (x - 0.11) / 0.06) * math.pi / 2) ** 2)


def knife(name, c, mat):
    pts = [(0.0, -0.0055), (0.04, -0.0072), (0.095, -0.0075), (0.105, -0.0050), (0.115, -0.0080), (0.19, -0.0090),
           (0.207, -0.0070), (0.214, -0.0020), (0.214, 0.0015), (0.20, 0.0070), (0.115, 0.0080), (0.105, 0.0050),
           (0.095, 0.0075), (0.04, 0.0072), (0.0, 0.0055)]
    return _outline(name, pts, 0.0024, c, mat, lambda x: 0.0 if x < 0.10 else 0.0035 * min(1.0, (x - 0.10) / 0.03))


def real_cutlery():
    bars = [o for o in bpy.data.objects if o.name.startswith("cutlery_")]
    if not bars:
        return LOG
    mat = bars[0].data.materials[0]
    S.principled(mat).inputs["Roughness"].default_value = 0.16
    c = bars[0].users_collection[0]
    n = 0
    for o in bars:
        loc = o.location.copy()                                   # (matrix_world can be stale right after creation)
        minus = o.name.endswith("-1")
        # the diner sits on the long table edge nearest the plate: plate x > 0 -> diner at +x facing -x (left = -y)
        facing_neg_x = loc.x > 0
        is_fork = minus if facing_neg_x else not minus
        name = o.name.replace("cutlery_", "fork_" if is_fork else "knife_")
        bpy.data.objects.remove(o, do_unlink=True)
        m = fork(name, c, mat) if is_fork else knife(name, c, mat)
        L = 0.200 if is_fork else 0.214
        jitter = S.RNG.normal(0, 0.025)
        ang = (math.pi if facing_neg_x else 0.0) + jitter       # outline x axis points from handle to head
        m.rotation_euler.z = ang
        d = Vector((math.cos(ang), math.sin(ang), 0))
        m.location = loc - d * (L / 2); m.location.z = loc.z - 0.0012
        n += 1
    LOG.append(f"cutlery: {n} placeholder bars replaced by modelled forks (4 tines, 200 mm) and knives (215 mm), bent like real ones")
    return LOG
