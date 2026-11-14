"""Second half of the film sells comfort: the pergola is the warm, dry, lit place in the grey storm.
  glass_roof()   replaces the profiled metal sheets: laminated safety glass (VSG 8.8.2, 17.5 mm) on anthracite aluminium
                 glazing bars with pressure caps, 1.5 deg fall to the lawn side built into the aluminium bars (no timber
                 firring on the beams - owner rule), drip profile on the low edge
  warm_lights()  2700 K LED line recessed along the inside of the perimeter beams + two opal-glass pendants over the table
                 (2200 K filament); real fixtures, real wattage-like intensities
  roof_drops()   rain beads and a thin water film on the glass (seen from below in the rain shots)
  splash()       the one drop that was frozen above the glass before the roof existed finally lands: wine crown + droplets
"""
import math, os
import bpy, bmesh
import numpy as np
from mathutils import Vector
import storm_lib as S, build_world as BW

LOG = []
log = LOG.append
R = np.random.default_rng(4242)

X0, X1, OVER, YH = -1.747, 1.747, 0.16, 3.15
TOP = 2.6006
FALL = math.radians(1.5)
BAR_W, BAR_H0, CAP_H, GLASS_T = 0.060, 0.070, 0.016, 0.0175
XL, XH = X0 - OVER, X1 + OVER                      # roof runs from the house side (high, XL) to the lawn side (low, XH)


def z_bar_top(x):
    return TOP + BAR_H0 + (XH - x) * math.tan(FALL)


def _box(name, verts, coll, mat):
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], f); me.update(); me.materials.append(mat)
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); coll.objects.link(o)
    bv = o.modifiers.new("bv", "BEVEL"); bv.width = 0.0015; bv.segments = 2; bv.limit_method = "ANGLE"
    return o


def _sloped(name, y0, y1, zb_lo, zb_hi, zt_lo, zt_hi, coll, mat, x0=XL, x1=XH):
    """prism between x0 (house side) and x1 (lawn side); bottom/top heights given at x0 (hi) and x1 (lo)"""
    v = []
    for x, zb, zt in ((x0, zb_hi, zt_hi), (x1, zb_lo, zt_lo)):
        for y in (y0, y1):
            v += [(x, y, zb), (x, y, zt)]
    # order expected by _box: index = xi*4 + yi*2 + top
    return _box(name, v, coll, mat)


def glass_roof():
    c = bpy.data.collections.get("PERGOLA")
    if c is None:
        return
    for o in [o for o in c.all_objects if o.name.startswith("SHEET_")]:
        bpy.data.objects.remove(o, do_unlink=True)
    alu = S.mat_simple("alu_glazing_RAL7016", (0.055, 0.06, 0.065), rough=0.38)
    S.principled(alu).inputs["Metallic"].default_value = 0.6
    glass = S.mat_glass("roof_vsg_glass", (0.96, 0.985, 0.975, 1))
    b = S.principled(glass); b.inputs["IOR"].default_value = 1.52; b.inputs["Roughness"].default_value = 0.0
    # laminated glass: the PVB interlayer + iron in 2x8 mm float gives the faint green edge tint (thin volume absorption)
    N, L = glass.node_tree.nodes, glass.node_tree.links
    va = N.new("ShaderNodeVolumeAbsorption"); va.inputs["Color"].default_value = (0.86, 0.95, 0.92, 1); va.inputs["Density"].default_value = 6.0
    out = next(n for n in N if n.type == "OUTPUT_MATERIAL"); L.new(va.outputs[0], out.inputs["Volume"])
    tanf = math.tan(FALL)
    bars_y = np.linspace(-YH, YH, 7)
    for k, y in enumerate(bars_y):
        w = BAR_W if 0 < k < 6 else BAR_W * 0.8
        o = _sloped(f"GLAZING_BAR_{k}", y - w / 2, y + w / 2, TOP, TOP, z_bar_top(XH), z_bar_top(XL), c, alu)
        # pressure cap over the glass edges
        _sloped(f"GLAZING_CAP_{k}", y - w / 2 - 0.004, y + w / 2 + 0.004, z_bar_top(XH) + GLASS_T - 0.002,
                z_bar_top(XL) + GLASS_T - 0.002, z_bar_top(XH) + GLASS_T + CAP_H, z_bar_top(XL) + GLASS_T + CAP_H, c, alu)
    for k in range(6):
        y0 = bars_y[k] + BAR_W / 2 - 0.012; y1 = bars_y[k + 1] - BAR_W / 2 + 0.012
        _sloped(f"SHEET_glass_{k}", y0, y1, z_bar_top(XH) + 0.003, z_bar_top(XL) + 0.003,
                z_bar_top(XH) + 0.003 + GLASS_T, z_bar_top(XL) + 0.003 + GLASS_T, c, glass, x1=XH + 0.035)
    # drip profile along the low edge + flashing on the high (house) edge
    _sloped("GLAZING_DRIP", -YH - 0.03, YH + 0.03, TOP + BAR_H0 - 0.03, TOP + BAR_H0 - 0.03,
            z_bar_top(XH) + 0.003, z_bar_top(XH) + 0.003, c, alu, x0=XH + 0.035, x1=XH + 0.05)
    _sloped("GLAZING_FLASH", -YH - 0.03, YH + 0.03, z_bar_top(XL) - 0.02, z_bar_top(XL) - 0.02,
            z_bar_top(XL) + GLASS_T + CAP_H + 0.01, z_bar_top(XL) + GLASS_T + CAP_H + 0.01, c, alu, x0=XL - 0.02, x1=XL + 0.05)
    log(f"roof: laminated safety glass VSG 8.8.2 (17.5 mm) on 7 anthracite aluminium glazing bars with pressure caps; "
        f"{math.degrees(FALL):.1f} deg fall to the lawn built into the bars ({(XH - XL) * tanf * 1000:.0f} mm), drip edge; "
        f"metal sheets removed")


def _blackbody_emit(name, kelvin, strength):
    m = bpy.data.materials.new(name); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links
    N.clear(); out = N.new("ShaderNodeOutputMaterial"); em = N.new("ShaderNodeEmission"); bb = N.new("ShaderNodeBlackbody")
    bb.inputs["Temperature"].default_value = kelvin; L.new(bb.outputs[0], em.inputs["Color"])
    em.inputs["Strength"].default_value = strength; L.new(em.outputs[0], out.inputs["Surface"])
    return m


def warm_lights(on=True):
    c = BW.fresh("PERGOLA_LIGHT")
    if not on:
        return
    k_led = float(os.environ.get("LED_K", 2700)); s_led = float(os.environ.get("LED_S", 25))
    led = _blackbody_emit("led_2700k", k_led, s_led)
    diffuser = S.mat_simple("led_profile_alu", (0.05, 0.05, 0.055), rough=0.4)
    # LED line on the inside face of the 4 perimeter beams, 40 mm below the beam top, facing inwards/down
    zt = 2.597 - 0.045
    runs = [((-1.68, -2.93), (-1.68, 2.93), (1, 0)), ((1.68, -2.93), (1.68, 2.93), (-1, 0)),
            ((-1.68, -2.93), (1.68, -2.93), (0, 1)), ((-1.68, 2.93), (1.68, 2.93), (0, -1))]
    for k, ((ax, ay), (bx, by), (nx, ny)) in enumerate(runs):
        ln = math.hypot(bx - ax, by - ay); cx, cy = (ax + bx) / 2, (ay + by) / 2
        along_y = abs(by - ay) > 0.1
        sx, sy = (0.012, ln) if along_y else (ln, 0.012)
        S.box(f"led_profile_{k}", (sx, sy, 0.016), (cx - nx * 0.006, cy - ny * 0.006, zt), c, diffuser)
        S.box(f"led_strip_{k}", (sx * 0.5 if along_y else sx, sy if along_y else sy * 0.5, 0.004),
              (cx + nx * 0.0005, cy + ny * 0.0005, zt - 0.009), c, led)
        # the light it throws: a long narrow area light at the strip, aimed down and slightly inwards
        A = bpy.data.lights.new(f"led_area_{k}", "AREA"); A.shape = "RECTANGLE"
        A.size, A.size_y = (0.02, ln) if along_y else (ln, 0.02)
        A.energy = float(os.environ.get("LED_W_PER_M", 40)) * ln; A.spread = math.radians(120); A.use_nodes = True
        bb = A.node_tree.nodes.new("ShaderNodeBlackbody"); bb.inputs["Temperature"].default_value = k_led
        A.node_tree.links.new(bb.outputs[0], A.node_tree.nodes["Emission"].inputs["Color"])
        ao = bpy.data.objects.new(f"led_area_{k}", A); c.objects.link(ao); ao.location = (cx + nx * 0.01, cy + ny * 0.01, zt - 0.012)
        ao.rotation_euler = (-ny * 0.35, nx * 0.35, 0.0)
    # two pendants over the table: cord, opal-glass globe, filament bulb (point light inside for clean sampling)
    opal = bpy.data.materials.new("opal_globe"); opal.use_nodes = True
    b = S.principled(opal); b.inputs["Base Color"].default_value = (0.98, 0.95, 0.9, 1); b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["Roughness"].default_value = 0.45; b.inputs["IOR"].default_value = 1.5
    b.inputs["Subsurface Weight"].default_value = 0.0
    # shadow rays pass the thin opal shell (caustics are off in this scene, so light from the bulb would otherwise be
    # trapped inside the refractive globe - a real 2 mm opal shell transmits ~60 %)
    N, L = opal.node_tree.nodes, opal.node_tree.links; out = next(n for n in N if n.type == "OUTPUT_MATERIAL")
    lp = N.new("ShaderNodeLightPath"); tr = N.new("ShaderNodeBsdfTransparent"); tr.inputs["Color"].default_value = (0.62, 0.6, 0.57, 1)
    mx = N.new("ShaderNodeMixShader"); L.new(lp.outputs["Is Shadow Ray"], mx.inputs[0]); L.new(b.outputs[0], mx.inputs[1])
    L.new(tr.outputs[0], mx.inputs[2]); L.new(mx.outputs[0], out.inputs["Surface"])
    cord = S.mat_simple("pendant_cord", (0.03, 0.03, 0.03), rough=0.6)
    fil = _blackbody_emit("filament_2200k", 2200, 25)
    z_roof_under = TOP + 0.0
    for k, y in enumerate((-0.48, 0.48)):
        x = 0.0; zg = 1.72
        bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.0028, depth=z_roof_under - zg - 0.11, location=(x, y, (z_roof_under + zg + 0.11) / 2))
        o = bpy.context.object; o.name = f"pendant_cord_{k}"; S.link(o, c); o.data.materials.append(cord)
        bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.022, depth=0.04, location=(x, y, zg + 0.105))
        o = bpy.context.object; o.name = f"pendant_cap_{k}"; S.link(o, c); o.data.materials.append(S.mat_simple("brass", (0.55, 0.42, 0.22), rough=0.3))
        S.principled(o.data.materials[0]).inputs["Metallic"].default_value = 1.0
        bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=0.095, location=(x, y, zg))
        o = bpy.context.object; o.name = f"pendant_globe_{k}"; S.link(o, c); o.data.materials.append(opal); o.data.shade_smooth()
        sol = o.modifiers.new("t", "SOLIDIFY"); sol.thickness = 0.003
        bpy.ops.mesh.primitive_torus_add(major_radius=0.012, minor_radius=0.0008, location=(x, y, zg))
        o = bpy.context.object; o.name = f"pendant_filament_{k}"; S.link(o, c); o.data.materials.append(fil)
        L_ = bpy.data.lights.new(f"pendant_bulb_{k}", "POINT"); L_.energy = float(os.environ.get("PENDANT_W", 100))
        L_.shadow_soft_size = 0.02; L_.use_nodes = True
        bb = L_.node_tree.nodes.new("ShaderNodeBlackbody"); bb.inputs["Temperature"].default_value = 2300
        L_.node_tree.links.new(bb.outputs[0], L_.node_tree.nodes["Emission"].inputs["Color"])
        lo = bpy.data.objects.new(f"pendant_bulb_{k}", L_); c.objects.link(lo); lo.location = (x, y, zg)
    log(f"warm light: {k_led:.0f} K LED line along the inside of the 4 beams (~{s_led:.0f} emission), "
        f"2 opal-glass pendants over the table (2300 K, {os.environ.get('PENDANT_W', 100)} W)")


def roof_drops(n=int(os.environ.get("ROOF_DROPS", 6000))):
    panes = [o for o in bpy.data.objects if o.name.startswith("SHEET_glass_")]
    if not panes:
        return
    c = BW.fresh("ROOF_WATER")
    water = S.mat_glass("roof_bead_water", (1, 1, 1, 1)); S.principled(water).inputs["IOR"].default_value = 1.333
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=1.0)
    src = bpy.context.object; src.name = "bead_src"; S.link(src, c)
    bm = bmesh.new(); bm.from_mesh(src.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.z < -0.05], context="VERTS"); bm.to_mesh(src.data); bm.free()
    src.scale = (0.003, 0.003, 0.0012); src.data.materials.append(water); src.data.shade_smooth()
    pts = []
    for o in panes:
        bb = [o.matrix_world @ Vector(v) for v in o.bound_box]
        x0, x1 = min(p.x for p in bb), max(p.x for p in bb); y0, y1 = min(p.y for p in bb), max(p.y for p in bb)
        m = n // len(panes)
        xs = R.uniform(x0 + 0.01, x1 - 0.01, m); ys = R.uniform(y0 + 0.01, y1 - 0.01, m)
        zs = z_bar_top(xs) + 0.003 + GLASS_T
        pts.append(np.stack([xs, ys, zs], 1))
    P = np.concatenate(pts)
    me = bpy.data.meshes.new("bead_pts"); me.vertices.add(len(P)); me.vertices.foreach_set("co", P.astype(np.float32).ravel())
    cl = bpy.data.objects.new("bead_cloud", me); c.objects.link(cl); cl.instance_type = "VERTS"; src.parent = cl
    src.location = (0, 0, 0)
    log(f"roof water: {len(P)} rain beads on the glass (3 mm, flattened)")


def splash(gx, gy, wine_top):
    """crown splash of the single drop entering the wine (~3 ms after contact): thin wine wall rising 3-4 mm with cusps
    that pinch off into droplets; a few secondary droplets in flight."""
    c = BW.fresh("SPLASH")
    wine = bpy.data.materials.get("red_wine")
    bm = bmesh.new(); nseg, nz = 96, 10; r0 = 0.0062; cusps = 13      # 4.6 mm drop from ~0.5 m -> crown ~13 mm across
    rings = []
    for j in range(nz + 1):
        t = j / nz; ring = []
        for i in range(nseg):
            th = 2 * math.pi * i / nseg
            hcusp = 0.0052 + 0.0020 * abs(math.cos(cusps * th / 2)) ** 6
            r = r0 + 0.0019 * t ** 1.5 + 0.00015 * math.sin(7 * th)       # flares outwards as it rises
            ring.append(bm.verts.new((gx + r * math.cos(th), gy + r * math.sin(th), wine_top - 0.0004 + hcusp * t)))
        rings.append(ring)
    for j in range(nz):
        for i in range(nseg):
            bm.faces.new([rings[j][i], rings[j][(i + 1) % nseg], rings[j + 1][(i + 1) % nseg], rings[j + 1][i]])
    me = bpy.data.meshes.new("splash_crown"); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new("splash_crown", me); c.objects.link(o); me.materials.append(wine); me.shade_smooth()
    sol = o.modifiers.new("t", "SOLIDIFY"); sol.thickness = 0.00025; sol.offset = 0
    n = 0
    for i in range(cusps):
        th = 2 * math.pi * (i + 0.5) / cusps * 1.0
        for k in range(2 if R.random() < 0.6 else 1):
            rr = r0 + 0.0021 + 0.0008 * k; zz = wine_top + 0.0078 + 0.0020 * k + float(R.uniform(0, 0.0008))
            bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=float(R.uniform(0.0004, 0.0007)),
                                                 location=(gx + rr * math.cos(th), gy + rr * math.sin(th), zz))
            d = bpy.context.object; d.name = f"splash_drop_{n}"; S.link(d, c); d.data.materials.append(wine); d.data.shade_smooth(); n += 1
    # central cavity rim: a shallow ring bump on the surface around the crown base
    log(f"splash: wine crown (r 6.2 mm, 13 cusps, 5-7 mm high) + {n} pinch-off droplets at the moment the single drop lands")


def _area(name, c, loc, size, power, kelvin, rot=(0, 0, 0)):
    A = bpy.data.lights.new(name, "AREA"); A.shape = "RECTANGLE"; A.size, A.size_y = size; A.energy = power; A.use_nodes = True
    bb = A.node_tree.nodes.new("ShaderNodeBlackbody"); bb.inputs["Temperature"].default_value = kelvin
    A.node_tree.links.new(bb.outputs[0], A.node_tree.nodes["Emission"].inputs["Color"])
    o = bpy.data.objects.new(name, A); c.objects.link(o); o.location = loc; o.rotation_euler = rot
    return o


def cozy_extras():
    """More warm light, all of it from real fixtures: candles in glass hurricane lanterns on the table, deck uplights at
    the pergola posts, and the house lived-in behind the glazing (warm ceiling light in the rooms)."""
    c = BW.fresh("COZY_EXTRAS")
    glass = S.mat_glass("hurricane_glass", (0.98, 0.98, 0.97, 1))
    N, L = glass.node_tree.nodes, glass.node_tree.links; out = next(n for n in N if n.type == "OUTPUT_MATERIAL")
    src = out.inputs["Surface"].links[0].from_socket
    lp = N.new("ShaderNodeLightPath"); tr = N.new("ShaderNodeBsdfTransparent"); mx = N.new("ShaderNodeMixShader")
    L.new(lp.outputs["Is Shadow Ray"], mx.inputs[0]); L.new(src, mx.inputs[1]); L.new(tr.outputs[0], mx.inputs[2]); L.new(mx.outputs[0], out.inputs["Surface"])
    wax = bpy.data.materials.new("candle_wax"); wax.use_nodes = True; b = S.principled(wax)
    b.inputs["Base Color"].default_value = (0.92, 0.86, 0.74, 1); b.inputs["Subsurface Weight"].default_value = 0.6
    b.inputs["Subsurface Radius"].default_value = (0.012, 0.008, 0.004); b.inputs["Roughness"].default_value = 0.45
    flame = _blackbody_emit("candle_flame", 1850, 60)
    tops = [o for o in bpy.data.objects if o.name.startswith("top_")]
    zt = max((o.matrix_world @ Vector(v)).z for o in tops for v in o.bound_box) if tops else 0.75
    spots = [(-0.02, 0.22), (-0.05, -0.62)]
    for k, (x, y) in enumerate(spots):
        S.lathe(f"lantern_glass_{k}", [(0.0001, 0.0), (0.045, 0.0), (0.05, 0.01), (0.056, 0.09), (0.05, 0.19), (0.052, 0.2),
                                        (0.049, 0.2), (0.047, 0.19), (0.053, 0.09), (0.047, 0.012), (0.0001, 0.004)],
                c, glass).location = (x, y, zt)
        cnd = S.lathe(f"candle_{k}", [(0.0001, 0.0), (0.03, 0.0), (0.03, 0.075), (0.026, 0.08), (0.004, 0.077), (0.0001, 0.077)], c, wax)
        cnd.location = (x, y, zt + 0.004)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=0.006, location=(x, y, zt + 0.004 + 0.077 + 0.012))
        f = bpy.context.object; f.name = f"flame_{k}"; S.link(f, c); f.scale = (0.75, 0.75, 2.0); f.data.materials.append(flame)
        Lp = bpy.data.lights.new(f"candle_light_{k}", "POINT"); Lp.energy = 4.0; Lp.shadow_soft_size = 0.006; Lp.use_nodes = True
        bb = Lp.node_tree.nodes.new("ShaderNodeBlackbody"); bb.inputs["Temperature"].default_value = 1850
        Lp.node_tree.links.new(bb.outputs[0], Lp.node_tree.nodes["Emission"].inputs["Color"])
        lo = bpy.data.objects.new(f"candle_light_{k}", Lp); c.objects.link(lo); lo.location = (x, y, zt + 0.004 + 0.077 + 0.016)
    # deck uplights at the posts: small warm spots in the deck washing up each post (outside face)
    posts = []
    pc = bpy.data.collections.get("PERGOLA")
    if pc:
        for o in pc.all_objects:
            if o.type == "MESH" and o.dimensions.z > 1.8 and max(o.dimensions.x, o.dimensions.y) < 0.25:
                bb = [o.matrix_world @ Vector(v) for v in o.bound_box]
                p = Vector((sum(v.x for v in bb) / 8, sum(v.y for v in bb) / 8, 0))
                if min(v.z for v in bb) < 0.4 and all((p - q).length > 0.3 for q in posts):   # one per standing post
                    posts.append(p)
    for k, p in enumerate(posts):
        out = Vector((p.x, p.y, 0)).normalized() if p.length > 0.1 else Vector((1, 0, 0))
        Ls = bpy.data.lights.new(f"post_uplight_{k}", "SPOT"); Ls.energy = 25; Ls.spot_size = math.radians(28); Ls.spot_blend = 0.6
        Ls.shadow_soft_size = 0.02; Ls.use_nodes = True
        bb = Ls.node_tree.nodes.new("ShaderNodeBlackbody"); bb.inputs["Temperature"].default_value = 2700
        Ls.node_tree.links.new(bb.outputs[0], Ls.node_tree.nodes["Emission"].inputs["Color"])
        lo = bpy.data.objects.new(f"post_uplight_{k}", Ls); c.objects.link(lo)
        lo.location = (p.x + out.x * 0.16, p.y + out.y * 0.16, 0.02)
        tgt = Vector((p.x, p.y, 2.4)); lo.rotation_euler = (tgt - Vector(lo.location)).to_track_quat("-Z", "Y").to_euler()
        S.box(f"uplight_ring_{k}", (0.07, 0.07, 0.006), (lo.location[0], lo.location[1], 0.003), c,
              S.mat_simple("uplight_ring", (0.05, 0.05, 0.05), rough=0.35))
    # the house is lived in: warm ceiling light in the ground-floor living room and two upstairs rooms
    for k, y in enumerate((-3.4, 0.0, 3.4)):
        _area(f"room_gf_{k}", c, (-5.2, y, 2.95), (1.6, 0.9), 220, 2700)
    for k, y in enumerate((-2.5, 2.5)):
        _area(f"room_up_{k}", c, (-4.2, y, 6.1), (1.2, 0.8), 140, 2700)
    log(f"warm extras: 2 candles in glass hurricane lanterns on the table, {len(posts)} deck uplights at the posts, "
        f"warm ceiling light in 3 ground-floor + 2 upstairs rooms")
