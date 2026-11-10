"""Environments for the RIVON film. The pergola (film_lib.build_pergola) is NEVER touched here:
only the Polish plot (assets.blend), a paving pad, furniture/props and the lab change between scenes."""
import math
import numpy as np
import bpy, mathutils
from film_lib import *   # noqa

# pergola clear interior (metres, pergola local == world): x in +-1.62, y in +-2.9, rafters at z 2.50..2.60
# ----------------------------------------------------------------------------------------------- materials
_M = {}
def M(name):
    if name in _M and name in bpy.data.materials: return _M[name]
    if name == "teak":   m = pbr("teak_furn", "teak_veneer_diff_2k.jpg", "teak_veneer_rough_2k.exr", "teak_veneer_disp_2k.png", 1.2, 0.002, tint=(0.8, 0.7, 0.62, 1))
    elif name == "oak":  m = pbr("oak_top", "olive_veneer_diff_2k.jpg", "olive_veneer_rough_2k.exr", "olive_veneer_disp_2k.png", 1.0, 0.002, tint=(0.95, 0.86, 0.72, 1))
    elif name == "paving": m = pbr("pad_paving", "stone_tiles_02_diff_2k.jpg", "stone_tiles_02_rough_2k.exr", "stone_tiles_02_disp_2k.png", 0.6, 0.004, tint=(0.62, 0.62, 0.64, 1))
    elif name == "graphite": m = simple("graphite_cab", (0.025, 0.027, 0.03, 1), 0.45, 0.0)
    elif name == "stone_dark": m = pbr("stone_dark", "stone_tiles_02_diff_2k.jpg", "stone_tiles_02_rough_2k.exr", None, 0.8, tint=(0.18, 0.18, 0.2, 1))
    elif name == "steel":  m = simple("stainless", (0.62, 0.63, 0.65, 1), 0.28, 1.0)
    elif name == "blacksteel": m = simple("black_metal", (0.012, 0.012, 0.014, 1), 0.45, 0.6)
    elif name == "fabric": m = simple("fabric_sand", (0.46, 0.41, 0.33, 1), 0.95, 0.0, 0.2)
    elif name == "fabric_dk": m = simple("fabric_graphite", (0.06, 0.065, 0.07, 1), 0.95, 0.0, 0.2)
    elif name == "rug":    m = simple("rug_wool", (0.30, 0.28, 0.25, 1), 1.0, 0.0, 0.1)
    elif name == "ceramic": m = simple("ceramic", (0.82, 0.82, 0.8, 1), 0.25, 0.0)
    elif name == "pot":    m = simple("planter_conc", (0.12, 0.12, 0.125, 1), 0.7, 0.0)
    elif name == "leaf":   m = simple("leaf_green", (0.05, 0.16, 0.04, 1), 0.6, 0.0)
    elif name == "bulb":   m = simple("bulb_warm", (1, 0.75, 0.4, 1), 0.3, 0.0, 0.5, emission=((1, 0.62, 0.25, 1), 22.0))
    elif name == "wire":   m = simple("wire_black", (0.005, 0.005, 0.005, 1), 0.6, 0.0)
    elif name == "glass":  m = simple("glass_dark", (0.02, 0.03, 0.035, 1), 0.05, 0.0, 1.0)
    else: raise KeyError(name)
    _M[name] = m; return m


# ----------------------------------------------------------------------------------------------- primitives
def chair(coll, x, y, rot=0.0, kind="dining"):
    c, s = math.cos(rot), math.sin(rot)
    def P(lx, ly, z): return (x + lx * c - ly * s, y + lx * s + ly * c, z)
    k = f"chair_{x:.2f}_{y:.2f}"
    box(k + "_seat", (0.46, 0.46, 0.045), P(0, 0, 0.46), M("teak"), coll, rot, 0.008)
    for i, (lx, ly) in enumerate([(-0.2, -0.2), (0.2, -0.2), (-0.2, 0.2), (0.2, 0.2)]):
        box(f"{k}_l{i}", (0.03, 0.03, 0.44), P(lx, ly, 0.22), M("blacksteel"), coll, rot, 0.002)
    box(k + "_back", (0.46, 0.035, 0.34), P(0, 0.215, 0.70), M("teak"), coll, rot, 0.008)
    for i, lx in enumerate((-0.21, 0.21)):
        box(f"{k}_bp{i}", (0.03, 0.03, 0.30), P(lx, 0.215, 0.62), M("blacksteel"), coll, rot, 0.002)


def table(coll, x, y, sx, sy, h=0.76, mat="teak"):
    k = f"table_{x:.2f}_{y:.2f}"
    box(k + "_top", (sx, sy, 0.05), (x, y, h), M(mat), coll, 0, 0.01)
    for i, (ax, ay) in enumerate([(-1, -1), (1, -1), (-1, 1), (1, 1)]):
        box(f"{k}_leg{i}", (0.07, 0.07, h - 0.025), (x + ax * (sx / 2 - 0.1), y + ay * (sy / 2 - 0.1), (h - 0.025) / 2), M("blacksteel"), coll, 0, 0.003)


def stool(coll, x, y):
    k = f"stool_{x:.2f}_{y:.2f}"
    cyl(k + "_seat", 0.17, 0.045, (x, y, 0.70), M("teak"), coll, 28, bevel=0.008)
    for i, a in enumerate((0, 2.09, 4.19)):
        box(f"{k}_l{i}", (0.025, 0.025, 0.68), (x + 0.12 * math.cos(a), y + 0.12 * math.sin(a), 0.34), M("blacksteel"), coll, 0, 0.002)


def planter(coll, x, y, h=0.55, w=0.5, plant=True):
    k = f"planter_{x:.2f}_{y:.2f}"
    box(k, (w, w, h), (x, y, h / 2), M("pot"), coll, 0, 0.01)
    if plant:
        rng = np.random.default_rng(int(abs(x * 100) + abs(y * 10)))
        for i in range(14):
            a = rng.uniform(0, 6.28); r = rng.uniform(0, w * 0.35); hh = rng.uniform(0.55, 0.95)
            ob = sphere(f"{k}_g{i}", 0.05, (x + r * math.cos(a), y + r * math.sin(a), h + hh * 0.35), M("leaf"), coll, 10, (1, 1, hh * 7))


def string_lights(coll, n_lines=4):
    """Festoon between the two long beams, under the rafters (z 2.46), warm bulbs on black wire."""
    for li in range(n_lines):
        y = -2.1 + li * (4.2 / (n_lines - 1))
        x0, x1, zt = -1.65, 1.65, 2.47
        pts = []
        for i in range(25):
            t = i / 24; pts.append((x0 + (x1 - x0) * t, y + 0.25 * math.sin(t * 3.1), zt - 0.33 * 4 * t * (1 - t)))
        for i, p in enumerate(pts):
            if i % 3 == 0: sphere(f"bulb_{li}_{i}", 0.032, p, M("bulb"), coll, 10)
        cv = bpy.data.curves.new(f"wire_{li}", "CURVE"); cv.dimensions = "3D"; cv.bevel_depth = 0.0015
        sp = cv.splines.new("POLY"); sp.points.add(len(pts) - 1)
        for i, p in enumerate(pts): sp.points[i].co = (*p, 1)
        ob = bpy.data.objects.new(f"wire_{li}", cv); cv.materials.append(M("wire")); link(ob, coll)


# ----------------------------------------------------------------------------------------------- the five applications
def props_barbecue(coll):
    box("bbq_base", (2.2, 0.7, 0.85), (0, 2.25, 0.425), M("stone_dark"), coll, 0, 0.012)
    box("bbq_top", (2.3, 0.8, 0.05), (0, 2.25, 0.875), M("oak"), coll, 0, 0.01)
    sphere("kettle_bowl", 0.31, (-0.45, 2.25, 1.0), M("blacksteel"), coll, 32, (1, 1, 0.8))
    cyl("kettle_lid", 0.31, 0.02, (-0.45, 2.25, 1.20), M("blacksteel"), coll, 32)
    box("grill_steel", (0.7, 0.5, 0.05), (0.55, 2.25, 0.925), M("steel"), coll, 0, 0.004)
    for i in range(7): box(f"grill_bar{i}", (0.7, 0.012, 0.015), (0.55, 2.07 + i * 0.06, 0.96), M("blacksteel"), coll, 0, 0.001)
    table(coll, 0, -0.55, 0.95, 2.6)
    for i, yy in enumerate((-1.3, -0.55, 0.2)):
        chair(coll, -0.95, yy, math.pi / 2 * 1.0 + math.pi)    # backs outward
        chair(coll, 0.95, yy, math.pi / 2)
    planter(coll, -1.45, -2.55); planter(coll, 1.45, -2.55)
    string_lights(coll, 3)


def props_kitchen(coll):
    for i in range(4):   # base cabinets along +x side
        box(f"cab_{i}", (0.62, 0.8, 0.86), (1.28, -1.7 + i * 0.82, 0.43), M("graphite"), coll, 0, 0.006)
        box(f"cab_handle_{i}", (0.015, 0.4, 0.015), (0.965, -1.7 + i * 0.82, 0.74), M("steel"), coll, 0, 0.002)
    box("worktop", (0.7, 3.3, 0.05), (1.26, -0.6, 0.885), M("oak"), coll, 0, 0.01)
    box("sink", (0.5, 0.55, 0.01), (1.26, -1.2, 0.912), M("steel"), coll, 0, 0.002)
    cyl("tap_stem", 0.012, 0.3, (1.45, -1.2, 1.06), M("steel"), coll, 12)
    for i, (hx, hy) in enumerate([(-0.12, -0.12), (0.12, -0.12), (-0.12, 0.12), (0.12, 0.12)]):
        cyl(f"hob{i}", 0.07, 0.008, (1.26 + hx, 0.45 + hy, 0.914), M("blacksteel"), coll, 24)
    box("fridge", (0.68, 0.7, 1.85), (1.27, 2.35, 0.925), M("steel"), coll, 0, 0.01)
    box("shelf", (0.3, 2.4, 0.04), (1.45, 0.4, 1.55), M("oak"), coll, 0, 0.006)
    box("island", (0.8, 1.9, 0.9), (-0.55, 0.0, 0.45), M("graphite"), coll, 0, 0.008)
    box("island_top", (0.95, 2.05, 0.05), (-0.55, 0.0, 0.925), M("oak"), coll, 0, 0.01)
    for i, yy in enumerate((-0.6, 0.0, 0.6)): stool(coll, -1.2, yy)
    table(coll, -0.75, -2.1, 0.8, 0.8)
    planter(coll, -1.45, 2.5)
    string_lights(coll, 3)


def props_lounge(coll):
    box("rug", (2.9, 3.6, 0.012), (0, -0.2, 0.006), M("rug"), coll, 0, 0.004)
    def sofa(x, y, sx, sy, back_side):
        box(f"sofa_base_{x}_{y}", (sx, sy, 0.22), (x, y, 0.20), M("blacksteel"), coll, 0, 0.01)
        box(f"sofa_seat_{x}_{y}", (sx - 0.1, sy - 0.1, 0.2), (x, y, 0.42), M("fabric"), coll, 0, 0.07)
        bx, by = back_side
        box(f"sofa_back_{x}_{y}", (0.2 if bx else sx - 0.1, 0.2 if by else sy - 0.1, 0.42), (x + bx * (sx / 2 - 0.12), y + by * (sy / 2 - 0.12), 0.74), M("fabric"), coll, 0, 0.08)
    sofa(-0.85, 0.2, 0.95, 2.6, (-1, 0))
    sofa(0.2, 1.75, 1.4, 0.95, (0, 1))
    sofa(1.1, -0.6, 0.9, 0.9, (1, 0))
    box("cushA", (0.4, 0.14, 0.4), (-0.78, -0.55, 0.68), M("fabric_dk"), coll, 0.3, 0.05)
    box("cushB", (0.4, 0.14, 0.4), (-0.78, 0.9, 0.68), M("fabric_dk"), coll, -0.2, 0.05)
    box("coffee_top", (0.9, 0.9, 0.05), (0.15, 0.05, 0.38), M("teak"), coll, 0, 0.01)
    for i, (ax, ay) in enumerate([(-1, -1), (1, -1), (-1, 1), (1, 1)]):
        box(f"coffee_leg{i}", (0.05, 0.05, 0.36), (0.15 + ax * 0.38, 0.05 + ay * 0.38, 0.18), M("blacksteel"), coll, 0, 0.002)
    cyl("lamp_stem", 0.012, 1.6, (-1.5, 1.45, 0.8), M("blacksteel"), coll, 10)
    sphere("lamp_head", 0.14, (-1.5, 1.45, 1.62), M("bulb"), coll, 16)
    planter(coll, 1.45, 2.4, 0.7, 0.6); planter(coll, -1.45, -2.5)
    string_lights(coll, 4)


def props_commercial(coll):
    for i, (tx, ty) in enumerate([(-0.85, -1.9), (0.85, -1.9), (-0.85, 0.0), (0.85, 0.0), (0.0, 1.55)]):
        cyl(f"bis_top{i}", 0.38, 0.035, (tx, ty, 0.74), M("teak"), coll, 36, bevel=0.006)
        cyl(f"bis_ped{i}", 0.03, 0.72, (tx, ty, 0.37), M("blacksteel"), coll, 12)
        cyl(f"bis_base{i}", 0.22, 0.02, (tx, ty, 0.01), M("blacksteel"), coll, 28)
        for j, a in enumerate((0.7, 3.84)):
            chair(coll, tx + 0.62 * math.cos(a), ty + 0.62 * math.sin(a), a + math.pi / 2)
    box("bar", (0.6, 2.4, 1.05), (-1.5, 2.0 - 1.0, 0.525), M("graphite"), coll, 0, 0.008)
    box("bar_top", (0.72, 2.5, 0.05), (-1.5, 1.0, 1.075), M("oak"), coll, 0, 0.01)
    box("coffee_machine", (0.45, 0.4, 0.4), (-1.5, 1.7, 1.3), M("steel"), coll, 0, 0.02)
    for i in range(3): stool(coll, -2.05 + 0.0, 0.2 + i * 0.7)
    planter(coll, 1.45, 2.55, 0.8, 0.55); planter(coll, -1.45, -2.65, 0.8, 0.55); planter(coll, 1.45, -2.65, 0.8, 0.55)
    string_lights(coll, 5)


PROPS = {"barbecue": props_barbecue, "kitchen": props_kitchen, "lounge": props_lounge, "commercial": props_commercial}


# ----------------------------------------------------------------------------------------------- lab
def build_lab(coll):
    floor_m, wall_m = mat_floor(), mat_wall()
    box("LAB_floor", (60, 60, 0.4), (0, 0, -0.2), floor_m, coll, 0, 0)
    box("LAB_wall_back", (60, 0.5, 14), (0, 18, 6.8), wall_m, coll, 0, 0)
    box("LAB_wall_left", (0.5, 60, 14), (-20, 0, 6.8), wall_m, coll, 0, 0)
    box("LAB_wall_right", (0.5, 60, 14), (20, 0, 6.8), wall_m, coll, 0, 0)
    box("LAB_wall_front", (60, 0.5, 14), (0, -22, 6.8), wall_m, coll, 0, 0)
    box("LAB_ceiling", (60, 60, 0.4), (0, 0, 13.7), wall_m, coll, 0, 0)
    em = mat_emission("lab_linear_light", (0.80, 0.90, 1.0, 1), 14.0)
    for x in (-6, -2, 2, 6): box(f"LAB_linear_{x}", (0.14, 20, 0.05), (x, 0, 7.2), em, coll, 0, 0)
    def area(name, loc, size, energy, color, target=(0, 0, 1.4)):
        L = bpy.data.lights.new(name, "AREA"); L.shape = "RECTANGLE"; L.size, L.size_y = size; L.energy = energy; L.color = color
        ob = bpy.data.objects.new(name, L); ob.location = loc
        ob.rotation_euler = mathutils.Vector(np.array(target) - np.array(loc)).to_track_quat("-Z", "Y").to_euler(); link(ob, coll)
    area("KEY_softbox", (1.5, -3.0, 9.0), (7, 9), 3600, (0.86, 0.92, 1.0))
    area("FILL_left", (-9.0, -6.0, 4.0), (5, 5), 1100, (0.80, 0.88, 1.0))
    area("RIM_right", (9.0, 7.0, 4.5), (4, 7), 1700, (0.62, 0.74, 1.0))
    area("FRONT_soft", (3.0, -11.0, 3.2), (6, 4), 850, (0.90, 0.94, 1.0))
