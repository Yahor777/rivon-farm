"""Scene assembly for the RIVON film: Polish plot (assets.blend) + exact-STEP pergola + per-application props.
Open assets.blend, call prepare() once, then apply_env(name) / set_shot(shot) before every frame."""
import math, sys
from pathlib import Path
import numpy as np
import bpy, mathutils
sys.path.insert(0, str(Path(__file__).resolve().parent))
from film_lib import *      # noqa
import film_envs as E
import film_stage as ST
import film_sets as SETM
import film_scenes as SCN
import film_anim as AN
import film_labs as LB

# ---- environment placement: PLOT (the whole Polish plot) is rotated/moved, the pergola stays at the world origin
def _plot(F, W, rot_deg=0.0):
    r = math.radians(rot_deg); R = np.array([[math.cos(r), -math.sin(r)], [math.sin(r), math.cos(r)]])
    loc = np.array(W) - R @ np.array(F)
    return (loc[0], loc[1], 0.0), r

ENVS = {
    "lab":        dict(kind="lab"),
    # every application is its own modelled daylight set: own house, yard, trees and sky (no photo panoramas)
    "yard":       dict(kind="set"), "carport":    dict(kind="set"), "barbecue": dict(kind="set"), "kitchen": dict(kind="set"), "lounge": dict(kind="set"), "commercial": dict(kind="set"),
}

# ---- camera shots (low, wide, close: the pergola must read as big, heavy and strong)
SHOTS = {
    "S0_lab":        dict(env="lab",        loc=(5.0, -8.6, 0.75), tgt=(0.0, 0.0, 2.2), lens=22),
    "S1_carport":    dict(env="carport",    loc=(6.8, -8.0, 0.9), tgt=(-0.6, 0.4, 1.2), lens=24),
    "S2_barbecue":   dict(env="barbecue",   loc=(-5.6, -7.2, 0.9), tgt=(0.5, 0.4, 1.2), lens=24),
    "S3_kitchen":    dict(env="kitchen",    loc=(-3.2, -7.2, 0.9), tgt=(0.8, 1.0, 1.25), lens=22),
    "S4_lounge":     dict(env="lounge",     loc=(5.4, -6.4, 0.85), tgt=(-0.4, 0.9, 1.15), lens=22),
    "S5_commercial": dict(env="commercial", loc=(-5.2, -5.2, 1.1), tgt=(0.4, 1.0, 1.3), lens=21),
}
SHOT_ORDER = list(SHOTS)

_state = {"env": None, "worlds": {}}


BODY_WHITE = ("Material_6", "Material_16")        # white paint of the Dodge RAM 1500 -> repainted black
GLASS = ("Material_2",)
RIMS = ("Material_9", "Material_17", "Material_27", "Material_29", "Material_30", "Material_12")


def import_ram():
    """Owner-supplied Dodge RAM 1500 (SketchUp .dae converted to metric glTF, geometry untouched), body repainted gloss black."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(HERE / "ram.glb"))
    new = [o for o in bpy.data.objects if o not in before]
    coll = collection("CAR_RAM")
    root = bpy.data.objects.new("CAR_RAM_ROOT", None); coll.objects.link(root)
    for o in new:
        if o.parent is None or o.parent not in new: o.parent = root
        link(o, coll)
    for m in {ms.material for o in new if o.type == "MESH" for ms in o.material_slots if ms.material}:
        b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if b is None: continue
        if m.name in BODY_WHITE:       # gloss black car paint with clear coat
            b.inputs["Base Color"].default_value = (0.004, 0.004, 0.005, 1); b.inputs["Metallic"].default_value = 0.2
            b.inputs["Roughness"].default_value = 0.28; b.inputs["Coat Weight"].default_value = 1.0; b.inputs["Coat Roughness"].default_value = 0.03
        elif m.name in GLASS:
            b.inputs["Base Color"].default_value = (0.01, 0.014, 0.018, 1); b.inputs["Roughness"].default_value = 0.04
            b.inputs["Specular IOR Level"].default_value = 1.0; b.inputs["Alpha"].default_value = 1.0
            m.blend_method = "OPAQUE" if hasattr(m, "blend_method") else None
        elif m.name in RIMS:
            b.inputs["Metallic"].default_value = 0.9; b.inputs["Roughness"].default_value = 0.32
        else:
            b.inputs["Roughness"].default_value = 0.55
    return root


def prepare(w, h, spp):
    sc = bpy.context.scene
    sc.animation_data_clear()          # assets.blend carried a stale keyframed exposure (0.15) that overrode the per-scene exposure from the 2nd frame on
    # relink textures / HDRI to the repo copy
    for img in bpy.data.images:
        if img.filepath:
            fn = Path(bpy.path.abspath(img.filepath.replace("\\", "/"))).name
            if (TEX / fn).exists(): img.filepath = str(TEX / fn)
    # whole plot -> PLOT_COLL, parented to one empty (so it can be moved/rotated as a unit)
    plot_coll = collection("PLOT_COLL")
    plot = bpy.data.objects.new("PLOT", None); plot_coll.objects.link(plot)
    for o in list(bpy.data.objects):
        if o is plot or o.parent is not None: continue
        if o.type in ("CAMERA", "LIGHT"): bpy.data.objects.remove(o, do_unlink=True); continue
        o.parent = plot; link(o, plot_coll)
    for o in bpy.data.objects:
        if o.parent is not None and o is not plot and o.name not in plot_coll.objects: link(o, plot_coll)
    # natural lawn: the stock colour was neon green; desaturate/darken the base shader of the plot lawn
    lm = bpy.data.materials.get("lawn")
    if lm and lm.use_nodes:
        for n in lm.node_tree.nodes:
            if n.type == "BSDF_PRINCIPLED":
                bc = n.inputs["Base Color"]
                if not bc.is_linked: bc.default_value = (0.085, 0.13, 0.04, 1)
                else:
                    hs = lm.node_tree.nodes.new("ShaderNodeHueSaturation"); hs.inputs["Saturation"].default_value = 0.88; hs.inputs["Value"].default_value = 0.8
                    src = bc.links[0].from_socket; lm.node_tree.links.new(src, hs.inputs["Color"]); lm.node_tree.links.new(hs.outputs[0], bc)
    import_ram()
    build_pergola("PERGOLA")
    lab = collection("LAB"); LB.v5b_tubes_dark_floor(lab)      # owner-approved lab: LED-tube hall with the dark wet floor
    collection("ENV_PROPS"); collection("ENV_PAD"); collection("ENV_DOME")
    # sun (outdoor key light)
    sun = bpy.data.lights.new("sun", "SUN"); sun.energy = 4.2; sun.angle = math.radians(0.8); sun.color = (1.0, 0.86, 0.70)
    so = bpy.data.objects.new("sun", sun); collection("LIGHTS").objects.link(so)
    el, az = math.radians(22), math.radians(215)
    d = -mathutils.Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
    so.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    # camera
    cam = bpy.data.cameras.new("film_cam"); co = bpy.data.objects.new("film_cam", cam); collection("CAMERA_RIG").objects.link(co)
    sc.camera = co; cam.clip_start = 0.05; cam.clip_end = 400
    # lab world
    lw = bpy.data.worlds.new("lab_world"); lw.use_nodes = True
    lw.node_tree.nodes["Background"].inputs["Color"].default_value = (0.0005, 0.0007, 0.001, 1)
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = spp
    sc.cycles.use_denoising = True; sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.use_volume_guiding = True; sc.cycles.volume_bounces = 2
    sc.cycles.max_bounces = 6; sc.cycles.diffuse_bounces = 3; sc.cycles.glossy_bounces = 4
    sc.cycles.transparent_max_bounces = 8; sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.02
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w, h, 100
    sc.render.image_settings.file_format = "PNG"; sc.render.film_transparent = False
    sc.view_settings.view_transform = "Khronos PBR Neutral"; sc.view_settings.look = "None"; sc.view_settings.exposure = 0.0
    _state["world_outdoor"] = sc.world; _state["lab_world"] = lw
    return sc


def _excl(name, on):
    lc = bpy.context.view_layer.layer_collection.children.get(name)
    if lc is not None: lc.exclude = on


def _hide_car(on):
    """Old Mercedes is never used; the Dodge RAM (collection CAR_RAM) shows only in the carport."""
    car = bpy.data.objects.get("car")
    stack = [car] if car else []
    while stack:
        o = stack.pop(); o.hide_render = True; o.hide_viewport = True
        stack += list(o.children)
    _excl("CAR_RAM", on)


def apply_env(name):
    if _state["env"] == name: return
    sc = bpy.context.scene; cfg = ENVS[name]
    for cn in ("ENV_PROPS", "ENV_PAD", "ENV_DOME"):
        c = bpy.data.collections[cn]
        for o in list(c.objects): bpy.data.objects.remove(o, do_unlink=True)
    lab = cfg["kind"] == "lab"
    _excl("LAB", not lab); _excl("PLOT_COLL", True)           # the old plot (same house everywhere) is no longer used
    bpy.data.objects["sun"].hide_render = True
    if lab:
        _excl("CAR_RAM", True); sc.world = _state["lab_world"]; sc.view_settings.exposure = 0.0; sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"
    else:
        res = SCN.SETS[name](bpy.data.collections["ENV_DOME"])
        sc.world = res["world"]; sc.view_settings.exposure = res.get("exp", 0.0); sc.view_settings.view_transform = "Khronos PBR Neutral"; sc.view_settings.look = "None"
        el, az, en, col = res["sun"]; so = bpy.data.objects["sun"]; so.hide_render = False; so.data.energy = en; so.data.color = col; so.data.angle = math.radians(0.6)
        d = -mathutils.Vector((math.cos(math.radians(el)) * math.cos(math.radians(az)), math.cos(math.radians(el)) * math.sin(math.radians(az)), math.sin(math.radians(el))))
        so.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        _hide_car(not res.get("car"))
        ram = bpy.data.objects["CAR_RAM_ROOT"]; ram.location = (0.0, 0.0, 0.0); ram.rotation_euler = (0, 0, 0)
    _state["env"] = name


def set_shot(shot, w=None):
    s = SHOTS[shot]; apply_env(s["env"])
    cam = bpy.data.objects["film_cam"]; cam.location = s["loc"]; cam.data.lens = s["lens"]
    cam.rotation_euler = mathutils.Vector(np.array(s["tgt"]) - np.array(s["loc"])).to_track_quat("-Z", "Y").to_euler()
    d = cam.data.dof; d.use_dof = True; d.focus_distance = float(np.linalg.norm(np.array(s["tgt"]) - np.array(s["loc"]))) * 1.02; d.aperture_fstop = 4.0
    bpy.context.view_layer.update()


# ---------------------------------------------------------------------------------------------- timeline mode
_anim = {"obj": None}


def apply_frame(f):
    """Everything that depends on the film frame f (0..899): environment, pergola assembly state, hero connector, camera."""
    if _anim["obj"] is None: _anim["obj"] = AN.Anim()
    apply_env(AN.env_for_frame(f))
    _anim["obj"].apply(f)
    loc, tgt, lens, fst = AN.camera_for_frame(f)
    cam = bpy.data.objects["film_cam"]; cam.location = loc; cam.data.lens = lens
    cam.rotation_euler = mathutils.Vector(np.array(tgt) - np.array(loc)).to_track_quat("-Z", "Y").to_euler()
    for nm, loc_, tgt_, en, sz in AN.light_rig(f):
        lo = bpy.data.objects.get(nm)
        if lo is None:
            ld = bpy.data.lights.new(nm, "AREA"); ld.color = (1.0, 0.98, 0.95); lo = bpy.data.objects.new(nm, ld); bpy.data.collections["LIGHTS"].objects.link(lo)
        lo.data.size = sz; lo.data.energy = en; lo.location = loc_
        lo.rotation_euler = (mathutils.Vector(tgt_) - mathutils.Vector(loc_)).to_track_quat("-Z", "Y").to_euler(); lo.hide_render = en <= 0.01
    d = cam.data.dof; d.use_dof = True; d.focus_distance = float(np.linalg.norm(np.array(tgt) - np.array(loc))); d.aperture_fstop = fst
    bpy.context.view_layer.update()




