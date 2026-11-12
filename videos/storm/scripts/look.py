"""Lighting, colour management, render settings and test cameras for RIVON THE STORM."""
import sys, math
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import bpy
from mathutils import Vector, Euler
import storm_lib as S


def setup_sky(elev_deg=21.0, rot_deg=125.0, strength=1.0, cloud=0.0):
    """Physically based sky (multiple scattering) + a matching sun lamp for sharp, correctly coloured shadows.
    rot_deg: sun azimuth in Blender's sky convention; the lamp is aimed along the same direction."""
    sc = bpy.context.scene
    w = sc.world or bpy.data.worlds.new("World"); sc.world = w; w.use_nodes = True
    N, L = w.node_tree.nodes, w.node_tree.links
    N.clear()
    sky = N.new("ShaderNodeTexSky"); sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_disc = True; sky.sun_size = math.radians(0.545); sky.sun_intensity = 1.0   # physically matched sun + sky
    sky.sun_elevation = math.radians(elev_deg); sky.sun_rotation = math.radians(rot_deg)
    sky.altitude = 90.0; sky.air_density = 1.0; sky.aerosol_density = 1.4; sky.ozone_density = 1.0
    bg = N.new("ShaderNodeBackground"); bg.inputs["Strength"].default_value = strength
    out = N.new("ShaderNodeOutputWorld")
    L.new(sky.outputs["Color"], bg.inputs["Color"]); L.new(bg.outputs[0], out.inputs["Surface"])
    old = bpy.data.objects.get("SUN")
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    sc.view_settings.exposure = float(__import__("os").environ.get("EXPOSURE", -3.05))   # owner: bright, sunny look; the physical sky is ~100 klx; this is the "camera exposure" for a sunny afternoon
    return sky, None


def setup_render(w=540, h=960, spp=64, final=False, device="CPU"):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "GPU" if device != "CPU" else "CPU"
    sc.render.resolution_x, sc.render.resolution_y = w, h; sc.render.resolution_percentage = 100
    sc.render.fps = 30
    sc.cycles.samples = spp; sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.004 if final else 0.02
    sc.cycles.use_denoising = True; sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.denoising_input_passes = "RGB_ALBEDO_NORMAL"
    sc.cycles.max_bounces = 24; sc.cycles.diffuse_bounces = 6; sc.cycles.glossy_bounces = 8
    sc.cycles.transmission_bounces = 24; sc.cycles.transparent_max_bounces = 24   # glass+wine: up to 8 interfaces per path
    sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False
    sc.cycles.blur_glossy = 0.2
    sc.cycles.sample_clamp_indirect = 25.0      # 8 was dulling real sun glints on glass/water
    sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Base Contrast"
    sc.render.film_transparent = False
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5     # 180-degree shutter
    sc.render.image_settings.file_format = "PNG"
    import storm_lib as S
    import os
    lim = os.environ.get("TEX_LIMIT") or ("1024" if S.PREVIEW else "")
    if lim:                           # cap texture size on RAM-limited machines (4k float EXR maps are ~270 MB each in RAM)
        sc.render.use_simplify = True; sc.cycles.texture_limit_render = lim
    return sc


def camera(name, loc, target, lens=40.0, fstop=5.6, focus=None, sensor=36.0):
    sc = bpy.context.scene
    cam = bpy.data.objects.get(name)
    if cam is None:
        cam = bpy.data.objects.new(name, bpy.data.cameras.new(name)); sc.collection.objects.link(cam)
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    # vertical 9:16 frame: full-frame sensor turned 90 degrees, 36 mm along the long (vertical) side
    cam.data.lens = lens; cam.data.sensor_fit = "VERTICAL"; cam.data.sensor_height = sensor
    cam.data.dof.use_dof = True; cam.data.dof.aperture_fstop = fstop
    cam.data.dof.focus_distance = focus if focus else (Vector(target) - Vector(loc)).length
    cam.data.clip_start = 0.02; cam.data.clip_end = 20000      # clouds are 2-7 km away
    sc.camera = cam
    return cam


def build_clouds(kind="fair", seed=3):
    """Volumetric cumulus (real 3D volumes lit by the same sun/sky, so shading and shadows are physically consistent).
    kind='fair': scattered fair-weather cumulus 1.2-1.8 km up; 'storm': heavy cumulonimbus wall (weather pass)."""
    import numpy as np
    rnd = np.random.default_rng(seed)
    c = S.coll("CLOUDS")
    for o in list(c.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    m = bpy.data.materials.get(f"cloud_{kind}")
    if m is None:
        m = bpy.data.materials.new(f"cloud_{kind}"); m.use_nodes = True
        N, L = m.node_tree.nodes, m.node_tree.links; N.clear()
        out = N.new("ShaderNodeOutputMaterial"); vol = N.new("ShaderNodeVolumePrincipled")
        vol.inputs["Color"].default_value = (1, 1, 1, 1) if kind == "fair" else (0.55, 0.57, 0.6, 1)
        vol.inputs["Anisotropy"].default_value = 0.55
        tc = N.new("ShaderNodeTexCoord")
        ln = N.new("ShaderNodeVectorMath"); ln.operation = "LENGTH"; L.new(tc.outputs["Object"], ln.inputs[0])
        fall = N.new("ShaderNodeMapRange"); fall.inputs["From Min"].default_value = 0.35; fall.inputs["From Max"].default_value = 1.0
        fall.inputs["To Min"].default_value = 1.0; fall.inputs["To Max"].default_value = 0.0; L.new(ln.outputs["Value"], fall.inputs["Value"])
        # flat-ish cloud base: density cut below local z=-0.35
        sep = N.new("ShaderNodeSeparateXYZ"); L.new(tc.outputs["Object"], sep.inputs[0])
        base = N.new("ShaderNodeMapRange"); base.inputs["From Min"].default_value = -0.45; base.inputs["From Max"].default_value = -0.25
        L.new(sep.outputs["Z"], base.inputs["Value"])
        nz = N.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 2.2; nz.inputs["Detail"].default_value = 10
        nz.inputs["Roughness"].default_value = 0.62; L.new(tc.outputs["Object"], nz.inputs["Vector"])
        a = N.new("ShaderNodeMath"); a.operation = "MULTIPLY_ADD"; a.inputs[1].default_value = 1.3
        L.new(fall.outputs[0], a.inputs[0]); L.new(nz.outputs["Fac"], a.inputs[2])
        th = N.new("ShaderNodeMapRange"); th.inputs["From Min"].default_value = 1.15; th.inputs["From Max"].default_value = 1.45
        th.inputs["To Max"].default_value = 0.035 if kind == "fair" else 0.06; L.new(a.outputs[0], th.inputs["Value"])
        dm = N.new("ShaderNodeMath"); dm.operation = "MULTIPLY"; L.new(th.outputs[0], dm.inputs[0]); L.new(base.outputs[0], dm.inputs[1])
        L.new(dm.outputs[0], vol.inputs["Density"]); L.new(vol.outputs[0], out.inputs["Volume"])
    n = 14 if kind == "fair" else 30
    for i in range(n):
        az = rnd.uniform(0, 2 * np.pi); dist = rnd.uniform(1800, 6500)
        if kind == "fair" and abs(np.degrees(az) - 0) < 25:
            dist += 1500                               # keep the sun side (camera backlight) a bit clearer
        sx, sy, sz = rnd.uniform(350, 900), rnd.uniform(350, 900), rnd.uniform(180, 380)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1.0, location=(dist * np.cos(az), dist * np.sin(az), rnd.uniform(1300, 1900) + sz * 0.3))
        o = bpy.context.object; o.name = f"cloud_{i:02d}"; S.link(o, c); o.scale = (sx, sy, sz)
        o.data.materials.append(m)
        o.visible_shadow = True
    sc = bpy.context.scene; sc.cycles.volume_step_rate = 4.0 if S.PREVIEW else 1.0; sc.cycles.volume_max_steps = 256
    return c


def render_haze_pass(path, visibility_km=20.0):
    """Aerial-perspective factor per pixel, rendered as a cheap 2-spp pass with a material override:
    f = 1 - exp(-d / L), L = visibility / 3 (Koschmieder). Sky pixels get 0 (the physical sky already contains the atmosphere).
    The post step blends each pixel towards the horizon haze colour by f -> distant trees, houses and the pier lose
    contrast and saturation exactly as much as their distance implies."""
    sc = bpy.context.scene; vl = bpy.context.view_layer
    m = bpy.data.materials.get("_haze_override")
    if m is None:
        m = bpy.data.materials.new("_haze_override"); m.use_nodes = True; N, L = m.node_tree.nodes, m.node_tree.links; N.clear()
        out = N.new("ShaderNodeOutputMaterial"); em = N.new("ShaderNodeEmission"); cd = N.new("ShaderNodeCameraData")
        div = N.new("ShaderNodeMath"); div.operation = "DIVIDE"; div.inputs[1].default_value = -visibility_km * 1000 / 3.0
        ex = N.new("ShaderNodeMath"); ex.operation = "EXPONENT"
        one = N.new("ShaderNodeMath"); one.operation = "SUBTRACT"; one.inputs[0].default_value = 1.0
        L.new(cd.outputs["View Distance"], div.inputs[0]); L.new(div.outputs[0], ex.inputs[0]); L.new(ex.outputs[0], one.inputs[1])
        L.new(one.outputs[0], em.inputs["Strength"]); L.new(em.outputs[0], out.inputs["Surface"])
    saved = dict(vt=sc.view_settings.view_transform, look=sc.view_settings.look, ex=sc.view_settings.exposure,
                 spp=sc.cycles.samples, dn=sc.cycles.use_denoising, world=sc.world, mb=sc.render.use_motion_blur,
                 fp=sc.render.filepath, cd=sc.render.image_settings.color_depth, dof=sc.camera.data.dof.use_dof)
    wd = bpy.data.worlds.get("_haze_world") or bpy.data.worlds.new("_haze_world"); wd.use_nodes = True
    wd.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    vl.material_override = m; sc.world = wd
    sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"; sc.view_settings.exposure = 0.0
    sc.cycles.samples = 2; sc.cycles.use_denoising = False; sc.render.use_motion_blur = False; sc.camera.data.dof.use_dof = False
    sc.render.image_settings.color_depth = "16"; sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    vl.material_override = None; sc.world = saved["world"]
    sc.view_settings.view_transform = saved["vt"]; sc.view_settings.look = saved["look"]; sc.view_settings.exposure = saved["ex"]
    sc.cycles.samples = saved["spp"]; sc.cycles.use_denoising = saved["dn"]; sc.render.use_motion_blur = saved["mb"]
    sc.render.filepath = saved["fp"]; sc.render.image_settings.color_depth = saved["cd"]; sc.camera.data.dof.use_dof = saved["dof"]
