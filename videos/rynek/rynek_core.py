"""RIVON video #4 - Stary Rynek w Poznaniu. Core helpers: meshes, slabs with holes, materials, animation.
Units: metres. 1 Blender unit = 1 m. Metal RIVON parts come from cad/*.stl (exact STEP tessellation, mm)."""
import bpy, bmesh, math, os, random
from mathutils import Vector, Matrix, Euler, geometry

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.normpath(os.path.join(HERE, "..", "dzialka", "textures"))
CAD = os.path.join(HERE, "cad")
FPS = 30

_mesh_cache = {}
M = {}


def img(name, nc=False):
    im = bpy.data.images.load(os.path.join(TEX, name), check_existing=True)
    if nc: im.colorspace_settings.name = 'Non-Color'
    return im


def new_obj(name, me, mat=None, loc=(0, 0, 0), rot=(0, 0, 0), parent=None):
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if mat is not None:
        if len(me.materials) == 0: me.materials.append(None)
        ob.material_slots[0].link = 'OBJECT'
        ob.material_slots[0].material = mat
    ob.location = loc; ob.rotation_euler = rot
    if parent is not None: ob.parent = parent
    return ob


def empty(name, loc=(0, 0, 0), rot=(0, 0, 0), parent=None):
    e = bpy.data.objects.new(name, None); bpy.context.scene.collection.objects.link(e)
    e.location = loc; e.rotation_euler = rot
    if parent is not None: e.parent = parent
    return e


def set_smooth(me, flags=None):
    me.polygons.foreach_set("use_smooth", flags if flags is not None else [True] * len(me.polygons)); me.update()


# ------------------------------------------------------------------ primitive meshes ----------------------------
def bm_box(bm, c, s, uvm=1.0, grain=True, rot_z=0.0, uv_layer=None):
    """append an axis-aligned (optionally z-rotated) box centred at c, size s; world-metre planar UV, grain along longest axis"""
    res = bmesh.ops.create_cube(bm, size=1.0)
    vs = res['verts']
    for v in vs:
        v.co.x *= s[0]; v.co.y *= s[1]; v.co.z *= s[2]
    fs = list({f for v in vs for f in v.link_faces})
    uv = bm.loops.layers.uv.verify()
    dims = s; long_ax = max(range(3), key=lambda i: dims[i])
    for f in fs:
        n = f.normal; na = max(range(3), key=lambda i: abs(n[i]))
        axes = [a for a in range(3) if a != na]
        if grain and long_ax in axes:
            ua = long_ax; va = [a for a in axes if a != long_ax][0]
        else:
            ua, va = axes
        for l in f.loops:
            l[uv].uv = (l.vert.co[ua] * uvm + c[ua] * 0.37, l.vert.co[va] * uvm + c[va] * 0.53)
    if rot_z:
        bmesh.ops.rotate(bm, verts=vs, cent=(0, 0, 0), matrix=Matrix.Rotation(rot_z, 3, 'Z'))
    bmesh.ops.translate(bm, verts=vs, vec=c)
    return vs


def box_mesh(sx, sy, sz, grain=True, uvm=1.0):
    key = ("box", round(sx, 4), round(sy, 4), round(sz, 4), grain, uvm)
    if key in _mesh_cache: return _mesh_cache[key]
    me = bpy.data.meshes.new("box"); bm = bmesh.new()
    bm_box(bm, (0, 0, 0), (sx, sy, sz), uvm, grain)
    bm.to_mesh(me); bm.free(); _mesh_cache[key] = me
    return me


def cyl_mesh(r, h, seg=20, r2=None, cap=True, uvs=1.0):
    key = ("cyl", round(r, 4), round(h, 4), seg, None if r2 is None else round(r2, 4), cap, uvs)
    if key in _mesh_cache: return _mesh_cache[key]
    me = bpy.data.meshes.new("cyl"); bm = bmesh.new()
    r2 = r if r2 is None else r2
    bot = []; top = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        bot.append(bm.verts.new((r * math.cos(a), r * math.sin(a), -h / 2)))
        top.append(bm.verts.new((r2 * math.cos(a), r2 * math.sin(a), h / 2)))
    for i in range(seg):
        j = (i + 1) % seg
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    if cap:
        tb = [bm.verts.new(v.co) for v in bot]; tt = [bm.verts.new(v.co) for v in top]
        bm.faces.new(tb[::-1]); bm.faces.new(tt)
    bm.normal_update()
    uv = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for l in f.loops:
            l[uv].uv = (math.atan2(l.vert.co.y, l.vert.co.x) * (max(r, r2) + 0.01) * uvs, l.vert.co.z * uvs)
    bm.to_mesh(me); bm.free()
    nside = seg
    set_smooth(me, [i < nside for i in range(len(me.polygons))])
    _mesh_cache[key] = me
    return me


def sphere_mesh(r=0.5, seg=24, rings=16):
    key = ("sph", round(r, 4), seg, rings)
    if key in _mesh_cache: return _mesh_cache[key]
    me = bpy.data.meshes.new("sph"); bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    uv = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for l in f.loops: l[uv].uv = (l.vert.co.x, l.vert.co.z)
    bm.to_mesh(me); bm.free(); set_smooth(me)
    _mesh_cache[key] = me
    return me


def box(name, size, loc, mat, rot=(0, 0, 0), parent=None, grain=True, uvm=1.0):
    return new_obj(name, box_mesh(*size, grain=grain, uvm=uvm), mat, loc, rot, parent)


def cyl(name, r, h, loc, mat, rot=(0, 0, 0), parent=None, seg=20, r2=None, cap=True):
    return new_obj(name, cyl_mesh(r, h, seg, r2, cap), mat, loc, rot, parent)


def ball(name, r, loc, mat, scale=(1, 1, 1), parent=None, rot=(0, 0, 0), seg=16, rings=10):
    ob = new_obj(name, sphere_mesh(r, seg, rings), mat, loc, rot, parent)
    ob.scale = scale
    return ob


def limb(name, p0, p1, r0, r1, mat, parent=None, seg=10):
    """tapered round limb from p0 to p1 (local space of parent)"""
    p0 = Vector(p0); p1 = Vector(p1); d = p1 - p0
    ob = new_obj(name, cyl_mesh(1.0, 1.0, seg, r2=r1 / r0 if r0 else 1.0), mat, (p0 + p1) / 2, (0, 0, 0), parent)
    ob.rotation_euler = d.to_track_quat('Z', 'Y').to_euler()
    ob.scale = (r0, r0, d.length)
    return ob


def between(name, p0, p1, sec, mat, parent=None):
    p0 = Vector(p0); p1 = Vector(p1); d = p1 - p0
    ob = new_obj(name, box_mesh(d.length, sec[0], sec[1]), mat, (p0 + p1) / 2, (0, 0, 0), parent)
    ob.rotation_euler = d.to_track_quat('X', 'Z').to_euler()
    return ob


# ------------------------------------------------------------------ mesh builder: many boxes -> one object per material
class MB:
    """accumulates geometry per material key, then emits one object per material (keeps the object count low)"""
    def __init__(self): self.bms = {}
    def bm(self, key):
        if key not in self.bms:
            b = bmesh.new(); b.loops.layers.uv.new("UVMap"); self.bms[key] = b
        return self.bms[key]
    def box(self, key, c, s, uvm=1.0, grain=True, rot_z=0.0):
        return bm_box(self.bm(key), c, s, uvm, grain, rot_z)
    def prism_x(self, key, x0, x1, pts, uvm=1.0):
        """extrude polygon pts=[(y,z),...] (CCW seen from +X) between x0 and x1"""
        b = self.bm(key); uv = b.loops.layers.uv.verify()
        va = [b.verts.new((x0, y, z)) for y, z in pts]; vb = [b.verts.new((x1, y, z)) for y, z in pts]
        n = len(pts)
        fa = b.faces.new(va[::-1]); fb = b.faces.new(vb)
        fs = [fa, fb]
        for i in range(n):
            j = (i + 1) % n
            fs.append(b.faces.new((va[i], va[j], vb[j], vb[i])))
        b.normal_update()
        for f in fs:
            for l in f.loops:
                p = l.vert.co; l[uv].uv = ((p.y + p.x * 0.7) * uvm, p.z * uvm)
        return fs
    def poly_y(self, key, pts, y0, y1, uvm=1.0, flip=False):
        """extrude polygon pts=[(x,z)...] (CCW seen from -Y) between y0 and y1; box-projected UV"""
        b = self.bm(key); uv = b.loops.layers.uv.verify()
        tess = geometry.tessellate_polygon([[Vector((x, z, 0)) for x, z in pts]])
        va = [b.verts.new((x, y0, z)) for x, z in pts]; vb = [b.verts.new((x, y1, z)) for x, z in pts]
        fs = []
        for a, b_, c in tess:
            fs.append(b.faces.new((va[a], va[c], va[b_]))); fs.append(b.faces.new((vb[a], vb[b_], vb[c])))
        n = len(pts)
        for i in range(n):
            j = (i + 1) % n
            fs.append(b.faces.new((va[i], va[j], vb[j], vb[i])))
        b.normal_update()
        for f in fs:
            nn = f.normal; na = max(range(3), key=lambda i: abs(nn[i]))
            axes = [a for a in range(3) if a != na]
            for l in f.loops:
                l[uv].uv = (l.vert.co[axes[0]] * uvm, l.vert.co[axes[1]] * uvm)
        return fs
    def slab_y(self, key, polys, y0, y1, uvm=1.0):
        """polygon with holes (polys[0] outer, rest holes, (x,z) CCW from -Y), thickness y0..y1, real reveals"""
        b = self.bm(key); uv = b.loops.layers.uv.verify()
        tess = geometry.tessellate_polygon([[Vector((x, z, 0)) for x, z in p] for p in polys])
        flat = [p for poly in polys for p in poly]
        vf = [b.verts.new((x, y0, z)) for x, z in flat]; vb = [b.verts.new((x, y1, z)) for x, z in flat]
        fs = []
        for a, b_, c in tess:
            fs.append(b.faces.new((vf[a], vf[c], vf[b_]))); fs.append(b.faces.new((vb[a], vb[b_], vb[c])))
        start = 0
        for pi, poly in enumerate(polys):
            n = len(poly)
            for i in range(n):
                j = (i + 1) % n
                if pi == 0: fs.append(b.faces.new((vf[start + i], vf[start + j], vb[start + j], vb[start + i])))
                else: fs.append(b.faces.new((vf[start + j], vf[start + i], vb[start + i], vb[start + j])))
            start += n
        b.normal_update()
        for f in fs:
            nn = f.normal; na = max(range(3), key=lambda i: abs(nn[i]))
            axes = [a for a in range(3) if a != na]
            for l in f.loops: l[uv].uv = (l.vert.co[axes[0]] * uvm, l.vert.co[axes[1]] * uvm)
        return fs
    def blob(self, key, c, r, sub=1):
        b = self.bm(key); uv = b.loops.layers.uv.verify()
        res = bmesh.ops.create_icosphere(b, subdivisions=sub, radius=r)
        bmesh.ops.translate(b, verts=res['verts'], vec=c)
        for v in res['verts']:
            for f in v.link_faces:
                for l in f.loops: l[uv].uv = (l.vert.co.x * 3, l.vert.co.z * 3)
    def ellipsoid(self, key, c, rad, sub=2, pivot=None, rot_z=0.0, tilt=0.0):
        b = self.bm(key); uv = b.loops.layers.uv.verify()
        res = bmesh.ops.create_icosphere(b, subdivisions=sub, radius=1.0)
        vs = res['verts']
        for v in vs: v.co.x *= rad[0]; v.co.y *= rad[1]; v.co.z *= rad[2]
        if tilt: bmesh.ops.rotate(b, verts=vs, cent=(0, 0, 0), matrix=Matrix.Rotation(tilt, 3, 'Y'))
        bmesh.ops.translate(b, verts=vs, vec=c)
        if rot_z:
            pv = pivot if pivot is not None else c
            bmesh.ops.rotate(b, verts=vs, cent=pv, matrix=Matrix.Rotation(rot_z, 3, 'Z'))
        for v in vs:
            for f in v.link_faces:
                for l in f.loops: l[uv].uv = (l.vert.co.x * 2 + l.vert.co.y, l.vert.co.z * 2)
        return vs
    def tube(self, key, p0, p1, r0, r1, seg=8, caps=True):
        """tapered round tube from p0 to p1 with spherical end caps (joints)"""
        b = self.bm(key); uv = b.loops.layers.uv.verify()
        p0 = Vector(p0); p1 = Vector(p1); d = p1 - p0; L = d.length
        q = d.to_track_quat('Z', 'Y')
        ring0 = []; ring1 = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            ring0.append(b.verts.new(p0 + q @ Vector((r0 * math.cos(a), r0 * math.sin(a), 0))))
            ring1.append(b.verts.new(p0 + q @ Vector((r1 * math.cos(a), r1 * math.sin(a), L))))
        fs = [b.faces.new((ring0[i], ring0[(i + 1) % seg], ring1[(i + 1) % seg], ring1[i])) for i in range(seg)]
        for f in fs:
            for l in f.loops: l[uv].uv = (math.atan2(l.vert.co.y, l.vert.co.x) * r0, l.vert.co.z)
        if caps:
            self.ellipsoid(key, tuple(p0), (r0, r0, r0), 1); self.ellipsoid(key, tuple(p1), (r1, r1, r1), 1)
    def emit(self, prefix, mats, parent=None, loc=(0, 0, 0), rot=(0, 0, 0), smooth=False):
        out = []
        for key, b in self.bms.items():
            if len(b.verts) == 0: b.free(); continue
            bmesh.ops.recalc_face_normals(b, faces=b.faces[:])
            me = bpy.data.meshes.new(prefix + "_" + str(key)); b.to_mesh(me); b.free()
            if smooth: set_smooth(me)
            out.append(new_obj(prefix + "_" + str(key), me, mats[key], loc, rot, parent))
        self.bms = {}
        return out


def slab_mesh(outline, holes, thick, name="slab", uvm=1.0, reveal_uv_scale=1.0):
    """wall slab in the XZ plane (front face at y=0 normal -Y, back face at y=thick).
    outline: [(x,z)...] CCW as seen from the front (-Y looking +Y: x to the right, z up); holes: list of such polygons.
    Front/back are triangulated with holes; all reveals are real geometry (recessed windows without booleans)."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")

    def loop_verts(poly, y): return [bm.verts.new((x, y, z)) for x, z in poly]
    polys = [outline] + holes
    tess = geometry.tessellate_polygon([[Vector((x, z, 0)) for x, z in p] for p in polys])
    flat = [p for poly in polys for p in poly]
    vf = [bm.verts.new((x, 0.0, z)) for x, z in flat]
    vb = [bm.verts.new((x, thick, z)) for x, z in flat]
    for t in tess:
        a, b_, c = t
        # front face normal must point to -Y: (x,z) CCW seen from -Y looking +Y gives normal -Y when the winding is (a,c,b)
        f1 = bm.faces.new((vf[a], vf[c], vf[b_])); f2 = bm.faces.new((vb[a], vb[b_], vb[c]))
    # side + reveals
    start = 0
    for pi, poly in enumerate(polys):
        n = len(poly)
        for i in range(n):
            j = (i + 1) % n
            ia, ib = start + i, start + j
            if pi == 0:
                bm.faces.new((vf[ia], vf[ib], vb[ib], vb[ia]))
            else:
                bm.faces.new((vf[ib], vf[ia], vb[ia], vb[ib]))
        start += n
    bm.normal_update()
    for f in bm.faces:
        n = f.normal
        for l in f.loops:
            p = l.vert.co
            if abs(n.y) > 0.5: l[uv].uv = (p.x * uvm, p.z * uvm)
            elif abs(n.x) > abs(n.z): l[uv].uv = (p.y * uvm, p.z * uvm)
            else: l[uv].uv = (p.x * uvm, p.y * uvm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me); bm.free()
    return me


def arch_pts(x0, x1, z0, zs, n=10, rise=None):
    """polygon (CCW from front) of an opening: rectangle x0..x1, z0..zs springing line, semicircular/segmental head"""
    w = x1 - x0
    rise = w / 2 if rise is None else rise
    pts = [(x0, z0), (x1, z0), (x1, zs)]
    if rise > 0.01:
        R = (rise * rise + (w / 2) ** 2) / (2 * rise)
        cx = (x0 + x1) / 2; cz = zs + rise - R
        a0 = math.atan2(zs - cz, x1 - cx); a1 = math.atan2(zs - cz, x0 - cx)
        if a1 < a0: a1 += 2 * math.pi
        for k in range(1, n):
            a = a0 + (a1 - a0) * k / n
            pts.append((cx + R * math.cos(a), cz + R * math.sin(a)))
    pts.append((x0, zs))
    return pts


def rect_pts(x0, x1, z0, z1): return [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]


# ------------------------------------------------------------------ materials ------------------------------------
def principled(nt):
    for n in nt.nodes:
        if n.type == 'BSDF_PRINCIPLED': return n


def mat_new(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    return m, m.node_tree, principled(m.node_tree)


def _mix(nt, a, b, fac, blend='MIX'):
    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = blend
    if isinstance(fac, (int, float)): mx.inputs[0].default_value = fac
    else: nt.links.new(fac, mx.inputs[0])
    for idx, v in ((6, a), (7, b)):
        if isinstance(v, tuple): mx.inputs[idx].default_value = (*v, 1) if len(v) == 3 else v
        else: nt.links.new(v, mx.inputs[idx])
    return mx.outputs[2]


def _tex(nt, image, vec, nc=False):
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = img(image, nc); t.interpolation = 'Cubic'
    nt.links.new(vec, t.inputs['Vector'])
    return t.outputs['Color']


def _uv_map(nt, scale, rot=0.0, off=(0, 0)):
    uvn = nt.nodes.new('ShaderNodeUVMap'); uvn.uv_map = "UVMap"
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (1 / scale[0], 1 / scale[1], 1)
    mp.inputs['Rotation'].default_value = (0, 0, rot); mp.inputs['Location'].default_value = (off[0], off[1], 0)
    nt.links.new(uvn.outputs['UV'], mp.inputs['Vector'])
    return mp.outputs['Vector']


def _noise(nt, vec, scale, detail=6, rough=0.55, stretch=None):
    n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = scale
    n.inputs['Detail'].default_value = detail; n.inputs['Roughness'].default_value = rough
    nt.links.new(vec, n.inputs['Vector'])
    return n.outputs['Fac']


def _ramp(nt, fac, stops):
    r = nt.nodes.new('ShaderNodeValToRGB')
    el = r.color_ramp.elements
    el[0].position, el[0].color = stops[0][0], (*stops[0][1], 1)
    el[1].position, el[1].color = stops[-1][0], (*stops[-1][1], 1)
    for p, c in stops[1:-1]:
        e = el.new(p); e.color = (*c, 1)
    nt.links.new(fac, r.inputs['Fac'])
    return r.outputs['Color']


def _math(nt, op, a, b=None, clamp=False):
    m = nt.nodes.new('ShaderNodeMath'); m.operation = op; m.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None: continue
        if isinstance(v, (int, float)): m.inputs[i].default_value = v
        else: nt.links.new(v, m.inputs[i])
    return m.outputs[0]


def pbr(name, color=(0.5, 0.5, 0.5), rough=0.5, metal=0.0, tex=None, tex_rough=None, tex_bump=None, bump=0.3, tile=1.0,
        tint=None, mult=None, spec=0.5, emit=None, emit_str=0.0, coat=0.0, bevel=0.006, grime=0.0, vary=0.0,
        streaks=0.0, antitile=True, sheen=0.0, ao_dist=0.6, sss=0.0, sss_col=None, bump_dist=0.02):
    """principled material with: bevel node (soft edges catch light), anti-tiling, ambient-occlusion grime, rain streaks,
    per-object random brightness (vary)"""
    m, nt, bsdf = mat_new(name)
    L = nt.links
    bsdf.inputs['Base Color'].default_value = (*color, 1); bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal; bsdf.inputs['Specular IOR Level'].default_value = spec
    if coat: bsdf.inputs['Coat Weight'].default_value = coat; bsdf.inputs['Coat Roughness'].default_value = 0.2
    if sheen: bsdf.inputs['Sheen Weight'].default_value = sheen
    if sss:
        bsdf.inputs['Subsurface Weight'].default_value = sss
        bsdf.inputs['Subsurface Radius'].default_value = (1.0, 0.35, 0.2)
        bsdf.inputs['Subsurface Scale'].default_value = 0.02
    if emit is not None:
        bsdf.inputs['Emission Color'].default_value = (*emit, 1); bsdf.inputs['Emission Strength'].default_value = emit_str
    col = None
    mask = None
    if tex:
        v1 = _uv_map(nt, (tile, tile))
        c1 = _tex(nt, tex, v1)
        if antitile:
            v2 = _uv_map(nt, (tile * 0.61, tile * 0.61), rot=0.9, off=(0.37, 0.19))
            c2 = _tex(nt, tex, v2)
            nv = _uv_map(nt, (1.0, 1.0))
            mask = _ramp(nt, _noise(nt, nv, 0.35, 3), [(0.40, (0, 0, 0)), (0.60, (1, 1, 1))])
            col = _mix(nt, c1, c2, mask)
        else:
            col = c1
        if tint is not None:
            bw = nt.nodes.new('ShaderNodeRGBToBW'); L.new(col, bw.inputs['Color'])
            mr = nt.nodes.new('ShaderNodeMapRange')
            mr.inputs['From Min'].default_value = 0.25; mr.inputs['From Max'].default_value = 0.7
            mr.inputs['To Min'].default_value = 0.8; mr.inputs['To Max'].default_value = 1.12
            L.new(bw.outputs['Val'], mr.inputs['Value'])
            col = _mix(nt, tint, mr.outputs['Result'], 1.0, 'MULTIPLY')
        elif mult is not None:
            col = _mix(nt, col, mult, 1.0, 'MULTIPLY')
    else:
        col = (*color, 1)
    toc = nt.nodes.new('ShaderNodeTexCoord')
    # large-scale tonal variation + rain streaks (object-space so every object differs)
    if grime or streaks or vary:
        base = col if not isinstance(col, tuple) else None
        if isinstance(col, tuple):
            rgb = nt.nodes.new('ShaderNodeRGB'); rgb.outputs[0].default_value = col; base = rgb.outputs[0]
        if vary:
            oi = nt.nodes.new('ShaderNodeObjectInfo')
            f = _math(nt, 'MULTIPLY', oi.outputs['Random'], vary * 2)
            f = _math(nt, 'ADD', f, 1.0 - vary)
            gray = nt.nodes.new('ShaderNodeCombineColor'); [L.new(f, gray.inputs[i]) for i in range(3)]
            base = _mix(nt, base, gray.outputs[0], 1.0, 'MULTIPLY')
        if grime:
            ao = nt.nodes.new('ShaderNodeAmbientOcclusion'); ao.inputs['Distance'].default_value = ao_dist
            ao.samples = 4; ao.inputs['Color'].default_value = (1, 1, 1, 1)
            dark = _mix(nt, (0.55, 0.5, 0.45), (1, 1, 1), ao.outputs['AO'])
            base = _mix(nt, base, dark, grime, 'MULTIPLY')
            nz = _ramp(nt, _noise(nt, toc.outputs['Object'], 1.3, 5), [(0.35, (1, 1, 1)), (0.7, (0.78, 0.74, 0.68))])
            base = _mix(nt, base, nz, grime * 0.8, 'MULTIPLY')
        if streaks:
            mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (7.0, 1.2, 0.35)
            L.new(toc.outputs['Object'], mp.inputs['Vector'])
            sn = _ramp(nt, _noise(nt, mp.outputs['Vector'], 3.0, 4, 0.6), [(0.42, (1, 1, 1)), (0.7, (0.72, 0.68, 0.62))])
            base = _mix(nt, base, sn, streaks, 'MULTIPLY')
        col = base
    if not isinstance(col, tuple): L.new(col, bsdf.inputs['Base Color'])
    if tex_rough:
        v = _uv_map(nt, (tile, tile))
        L.new(_tex(nt, tex_rough, v, True), bsdf.inputs['Roughness'])
    nrm = None
    if bevel:
        bv = nt.nodes.new('ShaderNodeBevel'); bv.inputs['Radius'].default_value = bevel; bv.samples = 3
        nrm = bv.outputs['Normal']
    if tex_bump:
        v = _uv_map(nt, (tile, tile))
        hb = _tex(nt, tex_bump, v, True)
        bn = nt.nodes.new('ShaderNodeBump'); bn.inputs['Strength'].default_value = bump; bn.inputs['Distance'].default_value = bump_dist
        L.new(hb, bn.inputs['Height'])
        if nrm is not None: L.new(nrm, bn.inputs['Normal'])
        nrm = bn.outputs['Normal']
    if nrm is not None: L.new(nrm, bsdf.inputs['Normal'])
    return m


def procedural(name, c1, c2, scale=40.0, rough=0.8, bump=0.25, bevel=0.0, c3=None, sat_var=0.0, vary=0.0, spec=0.4):
    m, nt, bsdf = mat_new(name)
    L = nt.links
    tc = nt.nodes.new('ShaderNodeTexCoord')
    ns = _noise(nt, tc.outputs['Object'], scale, 8, 0.6)
    stops = [(0.3, c1), (0.65, c2)] if c3 is None else [(0.25, c1), (0.5, c2), (0.75, c3)]
    col = _ramp(nt, ns, stops)
    if vary:
        oi = nt.nodes.new('ShaderNodeObjectInfo')
        f = _math(nt, 'ADD', _math(nt, 'MULTIPLY', oi.outputs['Random'], vary * 2), 1.0 - vary)
        gray = nt.nodes.new('ShaderNodeCombineColor'); [L.new(f, gray.inputs[i]) for i in range(3)]
        col = _mix(nt, col, gray.outputs[0], 1.0, 'MULTIPLY')
    L.new(col, bsdf.inputs['Base Color'])
    bn = nt.nodes.new('ShaderNodeBump'); bn.inputs['Strength'].default_value = bump; bn.inputs['Distance'].default_value = 0.02
    L.new(ns, bn.inputs['Height']); L.new(bn.outputs['Normal'], bsdf.inputs['Normal'])
    bsdf.inputs['Roughness'].default_value = rough; bsdf.inputs['Specular IOR Level'].default_value = spec
    return m


def cobble_material(name="cobble", bw=0.2, bh=0.1, c1=(0.36, 0.29, 0.25), c2=(0.72, 0.53, 0.42), mortar=(0.07, 0.065, 0.06), msize=0.012,
                    offset=0.5, rough=0.72):
    """granite setts laid in running bond (like the real Rynek): per-sett tone, dark joints, dirt patches, bump per sett"""
    m, nt, bsdf = mat_new(name)
    L = nt.links
    tc = nt.nodes.new('ShaderNodeTexCoord')
    br = nt.nodes.new('ShaderNodeTexBrick')
    br.offset = offset; br.offset_frequency = 2
    br.inputs['Scale'].default_value = 1.0
    br.inputs['Brick Width'].default_value = bw; br.inputs['Row Height'].default_value = bh
    br.inputs['Mortar Size'].default_value = msize; br.inputs['Mortar Smooth'].default_value = 0.3
    br.inputs['Color1'].default_value = (*c1, 1); br.inputs['Color2'].default_value = (*c2, 1); br.inputs['Mortar'].default_value = (*mortar, 1)
    br.inputs['Bias'].default_value = 0.0
    L.new(tc.outputs['Object'], br.inputs['Vector'])
    grit = _noise(nt, tc.outputs['Object'], 120.0, 3, 0.7)
    gcol = _ramp(nt, grit, [(0.3, (0.7, 0.7, 0.7)), (0.7, (1.0, 1.0, 1.0))])
    col = _mix(nt, br.outputs['Color'], gcol, 1.0, 'MULTIPLY')
    dirt = _ramp(nt, _noise(nt, tc.outputs['Object'], 0.5, 6), [(0.35, (1.0, 1.0, 1.0)), (0.7, (0.66, 0.62, 0.56))])
    col = _mix(nt, col, dirt, 1.0, 'MULTIPLY')
    L.new(col, bsdf.inputs['Base Color'])
    inv = _math(nt, 'SUBTRACT', 1.0, br.outputs['Fac'])
    hn = _math(nt, 'MULTIPLY', br.outputs['Fac'], _ramp_to_val(nt, grit))
    bn = nt.nodes.new('ShaderNodeBump'); bn.inputs['Strength'].default_value = 0.8; bn.inputs['Distance'].default_value = 0.03
    L.new(hn, bn.inputs['Height']); L.new(bn.outputs['Normal'], bsdf.inputs['Normal'])
    L.new(_math(nt, 'ADD', _math(nt, 'MULTIPLY', grit, 0.2), rough - 0.1), bsdf.inputs['Roughness'])
    bsdf.inputs['Specular IOR Level'].default_value = 0.4
    return m


def _ramp_to_val(nt, fac):
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['To Min'].default_value = 0.85; mr.inputs['To Max'].default_value = 1.0
    nt.links.new(fac, mr.inputs['Value'])
    return mr.outputs['Result']


# ------------------------------------------------------------------ animation helpers ----------------------------
def key_loc(ob, f, loc): ob.location = loc; ob.keyframe_insert('location', frame=f)
def key_rot(ob, f, rot): ob.rotation_euler = rot; ob.keyframe_insert('rotation_euler', frame=f)
def key_scale(ob, f, sc): ob.scale = sc; ob.keyframe_insert('scale', frame=f)


def key_vis(ob, f, visible):
    ob.hide_render = not visible; ob.keyframe_insert('hide_render', frame=f)


def fix_constant(ob):
    ad = ob.animation_data
    if not ad or not ad.action: return
    try: fcs = list(ad.action.fcurves)
    except Exception:
        fcs = []
        for layer in ad.action.layers:
            for strip in layer.strips:
                for cb in strip.channelbags: fcs.extend(cb.fcurves)
    for fc in fcs:
        if fc.data_path in ('hide_render', 'hide_viewport'):
            for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'


def lifecycle(obs, rest, spans, root=None):
    """spans: list of (t_in, t_land, t_out0, t_out1, off_in, off_out). The part (or parent group `root`, with `obs` its
    renderable members) is hidden, glides in from off_in during [t_in, t_land], rests, lifts away by off_out during
    [t_out0, t_out1] and is hidden again. t_out0=None -> stays."""
    rest = Vector(rest)
    mover = root if root is not None else obs[0]
    for o in obs: key_vis(o, 0, False)
    first = True
    for (t_in, t_land, t_out0, t_out1, off_in, off_out) in spans:
        for o in obs: key_vis(o, max(0, t_in - 1) if not first else max(1, t_in - 1), False); key_vis(o, t_in, True)
        first = False
        key_loc(mover, t_in, rest + Vector(off_in)); key_loc(mover, t_land, rest)
        if t_out0 is not None:
            key_loc(mover, t_out0, rest); key_loc(mover, t_out1, rest + Vector(off_out))
            for o in obs: key_vis(o, t_out1, True); key_vis(o, t_out1 + 1, False)
    return mover


def finalize_anim():
    for ob in bpy.data.objects: fix_constant(ob)
