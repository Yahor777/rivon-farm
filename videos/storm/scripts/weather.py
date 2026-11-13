"""Weather states for THE STORM control frames.
  storm  photographed approaching-storm sky (sun gone), darker cooler light, choppy sea, wind-bent nothing yet
  freeze same light as storm + rain drops hanging in the air as spheres (time stopped)
  rain   photographed overcast sky, rain streaks (shutter 1/50 s -> ~15-20 cm long at 9 m/s), wet surfaces outside the
         pergola footprint (darker porous materials, glossy films, puddles on the deck), water running off the low roof edge
Only physical light sources: the sky image. No extra lamps."""
import math, os
import bpy, bmesh
import numpy as np
from mathutils import Vector
import storm_lib as S, build_world as BW, refine2 as RF2

LOG = []
log = LOG.append
R = np.random.default_rng(777)
SKY = {"storm": ("kloofendal_overcast_puresky", 1.0), "freeze": ("kloofendal_overcast_puresky", 1.0), "rain": ("kloofendal_overcast_puresky", 1.0)}


def _sky(state):
    aid, k = SKY[state]
    p = RF2._hdri_path(aid)
    if p is None:
        log(f"weather: HDRI {aid} missing"); return
    sc = bpy.context.scene; w = sc.world; N, L = w.node_tree.nodes, w.node_tree.links
    N.clear()
    img = bpy.data.images.load(str(p)); img.colorspace_settings.name = "Linear Rec.709"
    tc = N.new("ShaderNodeTexCoord"); mp = N.new("ShaderNodeMapping")
    # storm front over the sea: the darkest part of the image (its storm cell) is turned towards +x (the sea)
    px = RF2._pix(img)[..., :3].mean(-1); h, wd = px.shape
    band = px[int(h * 0.5):int(h * 0.62)]                    # just above the horizon
    col = band.mean(0); u_dark = (np.argmin(np.convolve(col, np.ones(wd // 12) / (wd // 12), "same")) + 0.5) / wd
    phi_img = -2 * math.pi * (u_dark - 0.5); phi_want = 0.0   # +x
    mp.inputs["Rotation"].default_value[2] = phi_img - phi_want
    env = N.new("ShaderNodeTexEnvironment"); env.image = img; env.interpolation = "Cubic"
    bg = N.new("ShaderNodeBackground"); out = N.new("ShaderNodeOutputWorld")
    L.new(tc.outputs["Generated"], mp.inputs["Vector"]); L.new(mp.outputs[0], env.inputs["Vector"])
    L.new(env.outputs[0], bg.inputs["Color"]); L.new(bg.outputs[0], out.inputs["Surface"])
    # exposure: keep the scene readable (owner: never murky). Target sky luminance near the horizon ~ that of the sunny
    # sky image at the same strength calibration -> then the camera exposure lifts it 1.3 EV less than the sun scene.
    ref = float(os.environ.get("WEATHER_STRENGTH", 0))
    if not ref:
        lum_h = float(band.mean())
        ref = 2.2 / max(lum_h, 1e-4)                         # horizon radiance -> ~2.2 scene units (sunny sky ~3.5)
    bg.inputs["Strength"].default_value = ref
    sc.world.cycles.sampling_method = "MANUAL"; sc.world.cycles.sample_map_resolution = 2048
    log(f"weather {state}: sky {aid}, storm side turned to the sea, strength {ref:.3g}")


def storm_cloud():
    """No free photographed storm sky exists (Poly Haven 'approaching_storm' is a bright cumulus day), so the storm front
    is built: one volumetric shelf cloud / cumulonimbus base over the sea, lit only by the overcast sky dome.
    Real numbers: base 500-700 m, tops ~3 km, front edge ~2 km offshore, extinction ~0.01-0.05 /m."""
    c = BW.fresh("STORM_CLOUD")
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(5200, 0, 1650))
    o = bpy.context.object; o.name = "cb_front"
    for cc in o.users_collection:
        cc.objects.unlink(o)
    c.objects.link(o); o.scale = (7000, 16000, 2300)
    m = bpy.data.materials.new("cb_volume"); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links
    N.clear(); out = N.new("ShaderNodeOutputMaterial"); pv = N.new("ShaderNodeVolumePrincipled")
    tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Generated"], sep.inputs[0])
    mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (7.0, 16.0, 2.3); L.new(tc.outputs["Generated"], mp.inputs["Vector"])
    nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.6; nz.inputs["Detail"].default_value = 10
    nz.inputs["Roughness"].default_value = 0.62; nz.inputs["Distortion"].default_value = 0.35; L.new(mp.outputs[0], nz.inputs["Vector"])
    def mr(src, a, b, t0=0.0, t1=1.0):
        r = N.new("ShaderNodeMapRange"); r.inputs["From Min"].default_value = a; r.inputs["From Max"].default_value = b
        r.inputs["To Min"].default_value = t0; r.inputs["To Max"].default_value = t1; L.new(src, r.inputs["Value"]); return r.outputs[0]
    def op(o_, a, b):
        x = N.new("ShaderNodeMath"); x.operation = o_
        for i, v in enumerate((a, b)):
            if isinstance(v, float):
                x.inputs[i].default_value = v
            else:
                L.new(v, x.inputs[i])
        return x.outputs[0]
    z = sep.outputs[2]; xg = sep.outputs[0]
    base = mr(z, 0.0, 0.06)                                   # flat, sharp cloud base (condensation level)
    # the shelf leans towards the shore: the front edge (low x) is lower and denser, height grows offshore
    top = mr(op("SUBTRACT", z, op("MULTIPLY", xg, 0.55)), 0.55, 0.1)
    front = mr(xg, 0.0, 0.08)
    shape = op("MULTIPLY", op("MULTIPLY", base, top), front)
    dens = op("MULTIPLY", mr(op("ADD", nz.outputs["Fac"], op("MULTIPLY", shape, 0.55)), 0.78, 0.95), shape)
    L.new(op("MULTIPLY", dens, float(os.environ.get("CB_DENS", 0.02))), pv.inputs["Density"])
    pv.inputs["Color"].default_value = (0.92, 0.93, 0.95, 1); pv.inputs["Anisotropy"].default_value = 0.35
    L.new(pv.outputs[0], out.inputs["Volume"]); o.data.materials.append(m)
    sc = bpy.context.scene; sc.cycles.volume_step_rate = 8.0; sc.cycles.volume_max_steps = 512; sc.cycles.volume_bounces = 2
    log("storm cloud: volumetric shelf cloud / cumulonimbus base over the sea (base ~550 m, tops ~2.5 km, front 1.7 km offshore)")


def _sea(state):
    for o in bpy.data.objects:
        for md in o.modifiers:
            if md.type == "OCEAN":
                md.wind_velocity = 15.0 if state != "freeze" else 15.0
                md.wave_scale = 0.9; md.choppiness = 1.25
    log("sea: wind 15 m/s, choppy (0.9 wave scale, 1.25 choppiness)")


def _pergola_box():
    c = bpy.data.collections.get("PERGOLA")
    if not c:
        return None
    pts = [o.matrix_world @ Vector(v) for o in c.all_objects if o.type == "MESH" for v in o.bound_box]
    xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)


def _roof_edge():
    """low roof edge: sheet vertices with the lowest z, as a line (x, y0..y1, z)"""
    sh = [o for o in bpy.data.objects if o.name.startswith("SHEET_")]
    if not sh:
        return None
    pts = np.array([list(o.matrix_world @ v.co) for o in sh for v in o.data.vertices])
    xlo, xhi = pts[:, 0].min(), pts[:, 0].max()
    zlo_side = pts[pts[:, 0] < xlo + 0.05, 2].mean(); zhi_side = pts[pts[:, 0] > xhi - 0.05, 2].mean()
    if zlo_side < zhi_side:
        return (xlo, pts[:, 1].min(), pts[:, 1].max(), pts[pts[:, 0] < xlo + 0.05, 2].min())
    return (xhi, pts[:, 1].min(), pts[:, 1].max(), pts[pts[:, 0] > xhi - 0.05, 2].min())


def _rain_mat():
    m = bpy.data.materials.new("rain_streak"); m.use_nodes = True
    b = S.principled(m); b.inputs["Transmission Weight"].default_value = 0.85; b.inputs["IOR"].default_value = 1.333
    b.inputs["Roughness"].default_value = 0.15; b.inputs["Base Color"].default_value = (0.85, 0.88, 0.9, 1)
    # a drop smeared over the exposure: its integrated look is a faint, slightly milky line, not a glass rod
    b.inputs["Alpha"].default_value = 0.28
    return m


def rain(cam_loc, frozen=False, n=int(os.environ.get("RAIN_N", 140000))):
    c = BW.fresh("RAIN")
    pb = _pergola_box()
    mat = _rain_mat() if not frozen else S.mat_glass("rain_drop_frozen", (1, 1, 1, 1))
    if frozen:
        S.principled(mat).inputs["IOR"].default_value = 1.333
    wind = Vector((0.18, 0.05, -1.0)).normalized()          # sea wind pushes the rain landwards a little
    variants = []
    for k, ln in enumerate((0.12, 0.17, 0.22)):
        if frozen:
            bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=6, radius=0.0014 + 0.0004 * k)
        else:
            bpy.ops.mesh.primitive_cylinder_add(vertices=5, radius=0.0005 + 0.00015 * k, depth=ln)
        o = bpy.context.object; o.name = f"rain_src_{k}"
        for cc in o.users_collection:
            cc.objects.unlink(o)
        c.objects.link(o); o.data.materials.append(mat)
        if not frozen:
            o.rotation_euler = wind.to_track_quat("Z", "Y").to_euler()
            bpy.ops.object.select_all(action="DESELECT")
        o.hide_render = False
        variants.append(o)
    cl = Vector(cam_loc)
    tot = 0
    for k, src in enumerate(variants):
        cnt = n // 3
        # sample in a camera-centred cylinder 0.4..35 m, denser near the camera (we only see near drops individually)
        r = 1.6 + 35 * R.random(cnt) ** 1.6; a = R.uniform(0, 2 * math.pi, cnt)   # nothing closer than 1.6 m (lens-blurred away)
        x = cl.x + r * np.cos(a); y = cl.y + r * np.sin(a); z = R.uniform(-0.3, 9.0, cnt)
        keep = np.ones(cnt, bool)
        if pb:                                                  # no rain under the roof
            x0, x1, y0, y1, z0, z1 = pb
            keep &= ~((x > x0) & (x < x1) & (y > y0) & (y < y1) & (z < z1))
        x, y, z = x[keep], y[keep], z[keep]
        me = bpy.data.meshes.new(f"rain_pts_{k}"); me.vertices.add(len(x))
        me.vertices.foreach_set("co", np.stack([x, y, z], 1).astype(np.float32).ravel())
        cloud = bpy.data.objects.new(f"rain_cloud_{k}", me); c.objects.link(cloud)
        cloud.instance_type = "VERTS"; src.parent = cloud
        src.location = (0, 0, 0); tot += len(x)
    log(f"rain: {tot} {'frozen drops (spheres 1.4-2.2 mm)' if frozen else 'streaks 12-22 cm (1/50 s at ~9 m/s), wind-tilted 10 deg'}, "
        f"none under the pergola roof")
    edge = _roof_edge()
    if edge and not frozen:
        xe, y0, y1, ze = edge
        cur = S.mat_glass("roof_runoff", (1, 1, 1, 1)); S.principled(cur).inputs["IOR"].default_value = 1.333
        S.principled(cur).inputs["Roughness"].default_value = 0.05
        k = 0
        for corr in np.arange(y0 + 0.02, y1, 0.076):            # one rope of water per sheet valley (76 mm pitch)
            if R.random() < 0.2:
                continue
            ln = float(R.uniform(0.25, 0.9))                   # the rope breaks into drops after 0.3-0.9 m
            bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=float(R.uniform(0.0012, 0.0028)), depth=ln,
                                                location=(xe - 0.01, float(corr + R.normal(0, 0.004)), ze - ln / 2))
            o = bpy.context.object; o.name = f"runoff_{k}"
            for cc in o.users_collection:
                cc.objects.unlink(o)
            c.objects.link(o); o.data.materials.append(cur)
            d = o.modifiers.new("wob", "DISPLACE"); tx = bpy.data.textures.new(f"wob{k}", "CLOUDS"); tx.noise_scale = 0.05
            d.texture = tx; d.strength = 0.002
            k += 1
        log(f"roof run-off: {k} water ropes from the sheet valleys along the low edge (x={xe:.2f}, z={ze:.2f})")


def wet(dry_box=None):
    """Wet outdoor surfaces: porous albedo darkens (water fills the pores), roughness drops, up-facing faces get a water
    film; puddles in deck low spots. Inside the pergola footprint everything stays dry."""
    n = 0
    for m in bpy.data.materials:
        if not m.use_nodes or m.get("wet") or m.name.startswith(("rain", "roof_runoff", "wine", "red_wine", "window_glass",
                                                                   "bottle", "label", "olive", "leaf", "lawn", "grass")):
            continue
        b = next((x for x in m.node_tree.nodes if x.type == "BSDF_PRINCIPLED"), None)
        if b is None or b.inputs["Transmission Weight"].default_value > 0.5:
            continue
        m["wet"] = 1; n += 1
        N, L = m.node_tree.nodes, m.node_tree.links
        g = N.new("ShaderNodeNewGeometry"); sep = N.new("ShaderNodeSeparateXYZ"); L.new(g.outputs["Position"], sep.inputs[0])
        nrm = N.new("ShaderNodeSeparateXYZ"); L.new(g.outputs["Normal"], nrm.inputs[0])
        def mr(src, a, b_, t0=0.0, t1=1.0):
            r = N.new("ShaderNodeMapRange"); r.inputs["From Min"].default_value = a; r.inputs["From Max"].default_value = b_
            r.inputs["To Min"].default_value = t0; r.inputs["To Max"].default_value = t1; L.new(src, r.inputs["Value"]); return r.outputs[0]
        def mul(a, b_):
            x = N.new("ShaderNodeMath"); x.operation = "MULTIPLY"; L.new(a, x.inputs[0])
            if isinstance(b_, float):
                x.inputs[1].default_value = b_
            else:
                L.new(b_, x.inputs[1])
            return x.outputs[0]
        wetf = N.new("ShaderNodeValue"); wetf.outputs[0].default_value = 1.0; wf = wetf.outputs[0]
        if dry_box:
            x0, x1, y0, y1 = dry_box
            inx = mul(mr(sep.outputs[0], x0 - 0.15, x0 + 0.1, 0.0, 1.0), mr(sep.outputs[0], x1 + 0.15, x1 - 0.1, 0.0, 1.0))
            iny = mul(mr(sep.outputs[1], y0 - 0.15, y0 + 0.1, 0.0, 1.0), mr(sep.outputs[1], y1 + 0.15, y1 - 0.1, 0.0, 1.0))
            low = mr(sep.outputs[2], 3.4, 3.0, 0.0, 1.0)              # under the roof height
            inside = mul(mul(inx, iny), low)
            sub = N.new("ShaderNodeMath"); sub.operation = "SUBTRACT"; sub.inputs[0].default_value = 1.0; L.new(inside, sub.inputs[1])
            wf = sub.outputs[0]
        up = mr(nrm.outputs[2], 0.3, 0.9, 0.0, 1.0)
        nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.6; nz.inputs["Detail"].default_value = 4
        L.new(g.outputs["Position"], nz.inputs["Vector"])
        puddle = mul(mul(mr(nz.outputs["Fac"], 0.56, 0.62, 0.0, 1.0), up), wf)
        # albedo: porous darkening ~ (albedo^1.6-ish); approximate with multiply by 0.62 where wet
        if b.inputs["Base Color"].is_linked:
            src = b.inputs["Base Color"].links[0].from_socket
        else:
            rgb = N.new("ShaderNodeRGB"); rgb.outputs[0].default_value = b.inputs["Base Color"].default_value; src = rgb.outputs[0]
        mx = N.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"
        L.new(mul(wf, 0.75), mx.inputs["Factor"]); L.new(src, mx.inputs[6]); mx.inputs[7].default_value = (0.55, 0.55, 0.57, 1)
        L.new(mx.outputs[2], b.inputs["Base Color"])
        if b.inputs["Roughness"].is_linked:
            rs = b.inputs["Roughness"].links[0].from_socket
        else:
            rv = N.new("ShaderNodeValue"); rv.outputs[0].default_value = b.inputs["Roughness"].default_value; rs = rv.outputs[0]
        film = mul(wf, mul(up, 0.85))
        m1 = N.new("ShaderNodeMix"); m1.data_type = "FLOAT"; L.new(film, m1.inputs["Factor"]); L.new(rs, m1.inputs[2]); m1.inputs[3].default_value = 0.12
        m2 = N.new("ShaderNodeMix"); m2.data_type = "FLOAT"; L.new(puddle, m2.inputs["Factor"]); L.new(m1.outputs[0], m2.inputs[2]); m2.inputs[3].default_value = 0.02
        L.new(m2.outputs[0], b.inputs["Roughness"])
        # coat: water film is a separate specular layer on top of the material
        try:
            L.new(mul(film, 1.0), b.inputs["Coat Weight"]); b.inputs["Coat Roughness"].default_value = 0.03; b.inputs["Coat IOR"].default_value = 1.33
        except KeyError:
            pass
    log(f"wet: {n} materials wetted outside the pergola footprint (albedo x0.55-0.6, water coat on up-facing faces, puddles)")


def apply(state, cam_loc):
    _sky(state); _sea(state)
    if state in ("storm", "freeze") and os.environ.get("CB", "1") == "1":
        storm_cloud()
    pb = _pergola_box()
    if state == "rain":
        wet(dry_box=(pb[0], pb[1], pb[2], pb[3]) if pb else None)
        rain(cam_loc, frozen=False)
    elif state == "freeze":
        rain(cam_loc, frozen=True, n=int(os.environ.get("RAIN_N", 30000)))
    sc = bpy.context.scene
    sc.view_settings.exposure += float(os.environ.get("WEATHER_EV", {"storm": 1.3, "freeze": 1.5, "rain": 1.5}[state]))
    return LOG
