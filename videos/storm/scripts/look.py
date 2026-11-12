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
    sc.view_settings.exposure = -3.6      # the physical sky is ~100 klx; this is the "camera exposure" for a sunny afternoon
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
    sc.cycles.max_bounces = 12; sc.cycles.diffuse_bounces = 4; sc.cycles.glossy_bounces = 6
    sc.cycles.transmission_bounces = 12; sc.cycles.transparent_max_bounces = 16
    sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False
    sc.cycles.blur_glossy = 0.5
    sc.cycles.sample_clamp_indirect = 8.0
    sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Base Contrast"
    sc.render.film_transparent = False
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.5     # 180-degree shutter
    sc.render.image_settings.file_format = "PNG"
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
    cam.data.clip_start = 0.02; cam.data.clip_end = 400
    sc.camera = cam
    return cam
