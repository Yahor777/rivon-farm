"""Stary Rynek w Poznaniu: kamienice (townhouses), Ratusz (town hall), Domki Budnicze, fountain, pillory, props."""
import math, random
from mathutils import Vector
from rynek_core import *


# ------------------------------------------------------------------ materials ------------------------------------
WALLS = {"ochre": (0.93, 0.66, 0.3), "salmon": (0.9, 0.52, 0.45), "mint": (0.52, 0.76, 0.62), "cream": (0.96, 0.86, 0.62),
         "terra": (0.78, 0.4, 0.28), "blue": (0.5, 0.65, 0.84), "yellow": (0.97, 0.8, 0.3), "grey": (0.72, 0.72, 0.68),
         "white": (0.94, 0.92, 0.86), "sage": (0.62, 0.74, 0.46), "rose": (0.9, 0.62, 0.62), "teal": (0.36, 0.62, 0.62),
         "apricot": (0.96, 0.7, 0.45), "lilac": (0.7, 0.62, 0.78)}


def build_materials_town():
    M['cobble'] = cobble_material()
    M['slabs'] = cobble_material("terrace_slabs", bw=0.6, bh=0.4, c1=(0.45, 0.42, 0.4), c2=(0.66, 0.6, 0.54), mortar=(0.15, 0.14, 0.13), msize=0.01, rough=0.6)
    for k, c in WALLS.items():
        M['wall_' + k] = pbr("wall_" + k, (0.8, 0.8, 0.8), tex="beige_wall_002_diff_2k.jpg", tex_bump="beige_wall_002_disp_2k.png",
                             tint=c, rough=0.92, tile=2.2, bump=0.25, grime=0.55, streaks=0.5, bevel=0.012, vary=0.05)
    M['wall_keys'] = list(WALLS)
    M['trim'] = pbr("trim", (0.8, 0.8, 0.8), tex="beige_wall_002_diff_2k.jpg", tint=(0.95, 0.93, 0.88), rough=0.85, tile=2.2,
                    grime=0.5, bevel=0.01, streaks=0.4)
    M['stone'] = pbr("stone_plinth", (0.5, 0.5, 0.5), tex="stone_tiles_02_diff_2k.jpg", tex_rough="stone_tiles_02_rough_2k.exr",
                     mult=(0.95, 0.92, 0.88), tile=1.6, grime=0.6, bevel=0.008)
    M['frame'] = pbr("frame_white", (0.93, 0.92, 0.88), rough=0.42, bevel=0.004, grime=0.3, vary=0.04)
    M['glass'] = pbr("glass", (0.012, 0.02, 0.03), rough=0.025, metal=0.45, spec=1.0, bevel=0.0)
    M['glass_lit'] = pbr("glass_lit", (1.0, 0.7, 0.4), rough=0.3, emit=(1.0, 0.6, 0.26), emit_str=2.6, bevel=0.0)
    M['interior'] = pbr("interior", (0.05, 0.04, 0.035), rough=0.9, bevel=0.0)
    M['curt'] = pbr("curtain", (0.85, 0.8, 0.7), rough=0.95, bevel=0.0, vary=0.1)
    for k, c in {"green": (0.12, 0.3, 0.2), "brown": (0.22, 0.12, 0.08), "navy": (0.1, 0.17, 0.3), "red": (0.4, 0.1, 0.1)}.items():
        M['shut_' + k] = pbr("shut_" + k, c, rough=0.55, bevel=0.004, grime=0.3)
    M['roof'] = pbr("roof_tile", (0.6, 0.3, 0.2), tex="clay_roof_tiles_03_diff_2k.jpg", tex_rough="clay_roof_tiles_03_rough_2k.exr",
                    tex_bump="clay_roof_tiles_03_disp_2k.png", tile=1.6, bump=0.9, grime=0.35, vary=0.12, bevel=0.0)
    M['roof_dark'] = pbr("roof_dark", (0.3, 0.24, 0.22), tex="clay_roof_tiles_03_diff_2k.jpg", mult=(0.55, 0.5, 0.5), rough=0.7,
                         tex_bump="clay_roof_tiles_03_disp_2k.png", tile=1.6, bump=0.9, grime=0.3, vary=0.1, bevel=0.0)
    M['copper'] = pbr("copper_patina", (0.2, 0.46, 0.4), rough=0.45, metal=0.55, bevel=0.0, grime=0.3)
    M['gold'] = pbr("gilding", (0.9, 0.62, 0.18), rough=0.25, metal=1.0, bevel=0.0)
    M['brick'] = procedural("brick", (0.4, 0.17, 0.12), (0.62, 0.3, 0.2), scale=14, rough=0.9, bump=0.4, vary=0.1)
    M['door'] = pbr("door_wood", (0.2, 0.1, 0.06), rough=0.5, bevel=0.005, vary=0.15)
    M['iron'] = pbr("iron", (0.03, 0.03, 0.032), rough=0.45, metal=0.7, bevel=0.003)
    M['leaf'] = procedural("leaf", (0.04, 0.16, 0.05), (0.16, 0.38, 0.1), scale=60, rough=0.7, bump=0.3, vary=0.2, spec=0.5)
    M['flower_r'] = pbr("flower_r", (0.8, 0.07, 0.07), rough=0.6, bevel=0.0)
    M['flower_p'] = pbr("flower_p", (0.9, 0.35, 0.55), rough=0.6, bevel=0.0)
    M['flower_w'] = pbr("flower_w", (0.95, 0.93, 0.9), rough=0.6, bevel=0.0)
    M['flower_y'] = pbr("flower_y", (0.95, 0.75, 0.1), rough=0.6, bevel=0.0)
    M['wood_dark'] = pbr("wood_dark", (0.3, 0.17, 0.1), tex="wood_model_dom_2_1.jpg", tile=0.8, rough=0.5, bevel=0.004, vary=0.1)
    M['bulbmat'] = pbr("bulb", (1, 0.8, 0.5), emit=(1.0, 0.66, 0.3), emit_str=40.0, bevel=0.0)
    M['lamp'] = pbr("lamp_glass", (1, 0.8, 0.5), emit=(1.0, 0.7, 0.35), emit_str=6.0, bevel=0.0)
    M['water'] = pbr("water", (0.05, 0.14, 0.16), rough=0.04, spec=0.8, bevel=0.0)
    M['sandstone'] = pbr("sandstone", (0.5, 0.5, 0.5), tex="beige_wall_002_diff_2k.jpg", tint=(0.88, 0.78, 0.62), rough=0.8, tile=1.8,
                         grime=0.7, bevel=0.01, streaks=0.5)
    M['awn_red'] = pbr("awning_red", (0.55, 0.08, 0.08), rough=0.9, bevel=0.0, sheen=0.4)
    M['awn_cream'] = pbr("awning_cream", (0.85, 0.8, 0.65), rough=0.9, bevel=0.0, sheen=0.4)
    M['pigeon'] = pbr("pigeon", (0.34, 0.34, 0.38), rough=0.7, bevel=0.0)
    M['pigeon_w'] = pbr("pigeon_neck", (0.2, 0.3, 0.28), rough=0.4, bevel=0.0)


def _scale_pts(pts, dx, dz):
    xs = [p[0] for p in pts]; zs = [p[1] for p in pts]
    cx = (min(xs) + max(xs)) / 2; cz = (min(zs) + max(zs)) / 2
    w = max(xs) - min(xs); h = max(zs) - min(zs)
    sx = max(0.1, (w + dx) / w); sz = max(0.1, (h + dz) / h)
    return [(cx + (x - cx) * sx, cz + (z - cz) * sz) for x, z in pts]


def fill_window(mb, pts, r, lit=False, shut=None, box_flowers=False, ground=False, pediment=False):
    xs = [p[0] for p in pts]; zs = [p[1] for p in pts]
    x0, x1, z0, z1 = min(xs), max(xs), min(zs), max(zs)
    ww, hh = x1 - x0, z1 - z0; cx = (x0 + x1) / 2
    glass_pts = _scale_pts(pts, -0.17, -0.17)
    frame_out = _scale_pts(pts, -0.04, -0.04)
    mb.slab_y('frame', [frame_out, glass_pts], 0.16, 0.22)                     # painted frame ring
    mb.poly_y('lit' if lit else 'glass', glass_pts, 0.20, 0.22)                 # glass pane
    mb.box('frame', (cx, 0.12, (z0 + z1) / 2 - 0.02), (0.045, 0.05, hh - 0.2), grain=False)    # mullion
    mb.box('frame', (cx, 0.12, z0 + hh * 0.66), (ww - 0.15, 0.05, 0.045), grain=False)       # transom
    if r.random() < 0.4 and not lit:                                            # curtain behind the glass
        side = r.choice((-1, 1)); cw = ww * r.uniform(0.3, 0.5)
        mb.box('curt', (cx + side * (ww / 2 - 0.1 - cw / 2), 0.26, z1 - hh * 0.5), (cw, 0.02, hh * 0.78), grain=False)
    # architrave (raised plaster surround), sill
    mb.slab_y('trim', [_scale_pts(pts, 0.34, 0.34), pts], -0.045, 0.0)
    mb.box('trim', (cx, -0.08, z0 - 0.06), (ww + 0.34, 0.2, 0.09), grain=False)
    if pediment:
        mb.poly_y('trim', [(x0 - 0.2, z1 + 0.2), (x1 + 0.2, z1 + 0.2), (cx, z1 + 0.2 + ww * 0.32)], -0.1, 0.0)
        mb.box('trim', (cx, -0.08, z1 + 0.2), (ww + 0.5, 0.22, 0.09), grain=False)
    if shut:
        for sd in (-1, 1):
            sw = ww * 0.5
            mb.box(shut, (cx + sd * (ww / 2 + sw / 2 + 0.17), -0.04, (z0 + z1) / 2), (sw, 0.04, hh), grain=False)
            for k in range(1, 6):
                mb.box(shut, (cx + sd * (ww / 2 + sw / 2 + 0.17), -0.065, z0 + hh * k / 6), (sw - 0.04, 0.012, 0.012), grain=False)
    if box_flowers:
        bw = ww + 0.12
        mb.box('wood', (cx, -0.22, z0 - 0.17), (bw, 0.22, 0.18), grain=True)
        n = max(4, int(bw / 0.17))
        for i in range(n):
            x = cx - bw / 2 + 0.07 + (bw - 0.14) * i / (n - 1)
            mb.blob('leaf', (x, -0.22 + r.uniform(-0.03, 0.03), z0 - 0.02 + r.uniform(0, 0.08)), r.uniform(0.09, 0.13))
            for _ in range(2):
                mb.blob(r.choice(('flower_r', 'flower_r', 'flower_p', 'flower_w')),
                        (x + r.uniform(-0.07, 0.07), -0.22 + r.uniform(-0.06, 0.06), z0 + r.uniform(0.05, 0.16)), 0.04, 0)


def gable_profile(style, w, H, gh, r):
    """points from right to left, starting at (w, H) and ending at (0, H)"""
    if style == 'tri':
        return [(w, H), (w, H + 0.28), (w / 2, H + gh), (0, H + 0.28), (0, H)]
    if style == 'step':
        n = 4; dx = (w / 2 - 0.3) / n; dz = (gh - 0.3) / n
        right = [(w, H), (w, H + 0.3)]
        x = w; z = H + 0.3
        for k in range(n):
            x -= dx; right.append((x, z)); z += dz; right.append((x, z))
        pts = right + [(w / 2, z)]
        left = [(w - px, pz) for px, pz in reversed(right[2:])]
        return right + left[:-0] + [(0, H + 0.3), (0, H)] if False else (
            [(w, H), (w, H + 0.3)] + [p for p in right[2:]] + [(w - p[0], p[1]) for p in reversed(right[2:])] + [(0, H + 0.3), (0, H)])
    if style == 'ogee':
        pts = [(w, H), (w, H + 0.3)]
        N = 18
        for i in range(N + 1):
            t = 1 - i / N                           # t=1 at the edge, 0 at the centre
            tt = abs(t)
            z = H + 0.3 + gh * (max(0.0, 1 - tt) ** 1.15 + 0.16 * math.sin(3 * math.pi * tt) * (1 - tt) ** 0.6)
            pts.append((w / 2 + (w / 2) * tt, z))
        for i in range(1, N + 1):
            tt = i / N
            z = H + 0.3 + gh * (max(0.0, 1 - tt) ** 1.15 + 0.16 * math.sin(3 * math.pi * tt) * (1 - tt) ** 0.6)
            pts.append((w / 2 - (w / 2) * tt, z))
        pts += [(0, H + 0.3), (0, H)]
        # remove duplicates / non-monotonic leftovers
        out = []
        for p in pts:
            if not out or abs(p[0] - out[-1][0]) > 1e-4 or abs(p[1] - out[-1][1]) > 1e-4: out.append(p)
        return out
    return [(w, H), (w, H + 1.0), (0, H + 1.0), (0, H)]       # flat parapet


def kamienica(name, pos, yaw, w, floors, wall, gable='tri', seed=0, ground='shop', lit=False, depth=11.0, flowers=0.2,
              pediments=0.35, shutters=0.25, awning=False):
    """townhouse; local frame: x along the facade (right as seen from outside), y into the building, front face at y=0.
    pos/yaw place the local origin; the facade normal is the local -Y direction."""
    r = random.Random(seed)
    G = 4.3; fh = 3.4
    H = G + (floors - 1) * fh + 0.35
    root = empty(name, (pos[0], pos[1], 0), (0, 0, yaw))
    wallm = M['wall_' + wall]
    mats = {'trim': M['trim'], 'frame': M['frame'], 'glass': M['glass'], 'lit': M['glass_lit'], 'interior': M['interior'],
            'curt': M['curt'], 'wood': M['wood_dark'], 'leaf': M['leaf'], 'flower_r': M['flower_r'], 'flower_p': M['flower_p'],
            'flower_w': M['flower_w'], 'stone': M['stone'], 'door': M['door'], 'iron': M['iron'], 'roof': r.choice((M['roof'], M['roof'], M['roof_dark'])),
            'brick': M['brick'], 'wall': wallm, 'lamp': M['lamp'], 'awn': M['awn_red'] if r.random() < 0.5 else M['awn_cream']}
    shut = r.choice(('shut_green', 'shut_brown', 'shut_navy', 'shut_red'))
    for k in ('shut_green', 'shut_brown', 'shut_navy', 'shut_red'): mats[k] = M[k]
    use_shut = r.random() < shutters
    mb = MB()
    # ---------------- ground floor slab
    tg = 2.1 if ground == 'arcade' else 0.55
    holes = []; fills = []
    cols = max(2, int(round(w / 3.0)))
    pitch = w / cols
    door_c = r.randrange(cols)
    for c in range(cols):
        cx = pitch * (c + 0.5)
        if ground == 'arcade':
            aw = pitch - 0.95
            holes.append(arch_pts(cx - aw / 2, cx + aw / 2, 0.0, 3.0, 12)); continue
        if c == door_c:
            dw = 1.45
            pts = arch_pts(cx - dw / 2, cx + dw / 2, 0.0, 2.55, 10, rise=0.55)
            holes.append(pts); fills.append(('door', pts, cx))
        else:
            sw = min(2.3, pitch - 1.0)
            pts = arch_pts(cx - sw / 2, cx + sw / 2, 0.75, 3.05, 10, rise=min(0.9, sw / 2))
            holes.append(pts); fills.append(('shop', pts, cx))
    gm = MB()
    gm.slab_y('wall', [rect_pts(0, w, 0, G)] + holes, 0.0, tg, uvm=1.0 / 1.0)
    for kind, pts, cx in fills:
        if kind == 'door':
            mb.poly_y('door', _scale_pts(pts, -0.06, -0.06), 0.18, 0.24)
            mb.box('iron', (cx + 0.5, 0.12, 1.05), (0.04, 0.05, 0.25), grain=False)                      # handle
            mb.slab_y('trim', [_scale_pts(pts, 0.4, 0.3), pts], -0.05, 0.0)
            mb.box('stone', (cx, -0.35, 0.06), (1.9, 0.9, 0.12), grain=False)                              # step
            mb.box('lamp', (cx + 1.05, -0.12, 2.9), (0.14, 0.14, 0.26), grain=False)
            mb.box('iron', (cx + 1.05, -0.12, 3.06), (0.18, 0.18, 0.04), grain=False)
        else:
            fill_window(mb, pts, r, lit=lit, box_flowers=False, pediment=False)
    if ground == 'arcade':
        # open arcade (podcienia): tunnel, inner wall with doors/windows, vaulted ceiling shade
        mb.box('wall', (w / 2, tg + 0.15, G / 2), (w, 0.3, G))
        for c in range(cols):
            cx = pitch * (c + 0.5)
            if c == door_c:
                mb.box('door', (cx, tg - 0.02, 1.2), (1.3, 0.06, 2.4), grain=True)
            else:
                mb.box('frame', (cx, tg - 0.02, 1.9), (1.5, 0.06, 1.9), grain=False)
                mb.box('lit' if lit else 'glass', (cx, tg - 0.06, 1.9), (1.3, 0.04, 1.7), grain=False)
        mb.box('stone', (w / 2, tg / 2, 0.03), (w, tg, 0.06), uvm=0.5)
        if lit:
            mb.box('lamp', (w / 2, tg / 2, G - 0.45), (0.3, 0.3, 0.1), grain=False)
    # string course
    mb.box('trim', (w / 2, -0.12, G + 0.02), (w + 0.12, 0.3, 0.3), grain=False)
    mb.box('trim', (w / 2, -0.06, G - 0.2), (w + 0.1, 0.2, 0.14), grain=False)
    mb.box('stone', (w / 2, -0.05, 0.4), (w + 0.04, 0.14, 0.8), uvm=0.5)
    if awning and ground != 'arcade':
        for kind, pts, cx in fills:
            if kind == 'shop':
                sw = max(p[0] for p in pts) - min(p[0] for p in pts)
                # sloped canopy as a rotated box
                mb.box('awn', (cx, -0.65, 3.0), (sw + 0.5, 1.4, 0.04), grain=False)
    # ---------------- upper slab with windows
    ups = []
    nwin = max(2, int(round(w / 2.7))); wp = w / nwin
    for f in range(1, floors):
        zb = G + (f - 1) * fh + 0.62
        for c in range(nwin):
            cx = wp * (c + 0.5)
            ww = 1.12 if f == 1 else 1.0
            hh = 2.25 if f == 1 else 2.0
            arched = (f == floors - 1 and floors > 2 and r.random() < 0.5) or (f == 1 and r.random() < 0.35)
            if arched: pts = arch_pts(cx - ww / 2, cx + ww / 2, zb, zb + hh - ww * 0.3, 10, rise=ww * 0.3)
            else: pts = rect_pts(cx - ww / 2, cx + ww / 2, zb, zb + hh)
            ups.append((f, pts))
    prof = gable_profile(gable, w, H, w * 0.5 if gable != 'flat' else 0.0, r)
    outline = [(0, G), (w, G)] + prof
    gm.slab_y('wall', [outline] + [p for _, p in ups], 0.0, 0.5)
    for f, pts in ups:
        fill_window(mb, pts, r, lit=False, shut=shut if use_shut else None,
                    box_flowers=(f <= 2 and r.random() < flowers), pediment=(f == 1 and r.random() < pediments))
    # eave cornice
    mb.box('trim', (w / 2, -0.25, H - 0.12), (w + 0.5, 0.65, 0.22), grain=False)
    mb.box('trim', (w / 2, -0.12, H - 0.36), (w + 0.4, 0.38, 0.14), grain=False)
    # attic details
    if gable in ('tri', 'ogee', 'step'):
        gh = w * 0.5
        mb.slab_y('trim', [[(w / 2 - 0.4, H + gh - 0.4 + 0.0), (w / 2 + 0.4, H + gh - 0.4), (w / 2 + 0.4, H + gh - 1.2), (w / 2 - 0.4, H + gh - 1.2)]] if False else
                  [rect_pts(w / 2 - 0.45, w / 2 + 0.45, H + gh * 0.35, H + gh * 0.35 + 0.95)], -0.04, 0.0)
        mb.box('frame', (w / 2, 0.1, H + gh * 0.35 + 0.47), (0.7, 0.05, 0.7), grain=False)
        mb.box('interior', (w / 2, 0.2, H + gh * 0.35 + 0.47), (0.62, 0.05, 0.62), grain=False)
        mb.blob('gold', (w / 2, 0.2, H + gh + 0.12), 0.1) if False else None
    else:
        for k in range(int(w / 0.5)):
            mb.box('trim', (0.25 + k * 0.5, 0.1, H + 0.55), (0.12, 0.12, 0.6), grain=False)
        mb.box('trim', (w / 2, 0.1, H + 0.9), (w + 0.1, 0.3, 0.14), grain=False)
    # ---------------- body + roof + chimney
    mb.box('interior', (w / 2, tg + (depth - tg) / 2, H / 2 - 0.2), (w - 0.04, depth - tg, H - 0.4), grain=False)
    rh = w * 0.42 if gable != 'flat' else 3.0
    if gable != 'flat':
        rs = [(0.0, H - 0.1), (w, H - 0.1), (w / 2, H + rh)]
        mb.poly_y('roof', rs, 0.5, depth, uvm=0.6)
        mb.box('trim', (w / 2, depth / 2 + 0.2, H + rh + 0.03), (0.2, depth - 0.6, 0.16), grain=False)       # ridge
        if r.random() < 0.7:
            cx = w * r.uniform(0.25, 0.75); cy = r.uniform(4, depth - 2)
            mb.box('brick', (cx, cy, H + rh * 0.55 + 1.0), (0.8, 0.8, 2.4)); mb.box('stone', (cx, cy, H + rh * 0.55 + 2.25), (1.0, 1.0, 0.12))
    else:
        mb.prism_x('roof', 0.0, w, [(0.4, H), (depth, H), (depth * 0.55, H + rh)], uvm=0.6)
        if r.random() < 0.7:
            cx = w * r.uniform(0.25, 0.75)
            mb.box('brick', (cx, depth * 0.6, H + rh + 0.6), (0.8, 0.8, 2.0))
    mats['gold'] = M['gold']
    mb.emit(name + "_d", mats, parent=root)
    gm.emit(name + "_w", mats, parent=root)
    return root


# ------------------------------------------------------------------ Ratusz ---------------------------------------
def ratusz(pos, yaw):
    """Poznan Town Hall, Renaissance: stone ground floor, three-storey-high loggia (two tiers of arches), crenellated attic with
    turrets and gables, central tower with clock and copper spire. Local frame: front at y=0 facing -Y, x from 0 to Wd."""
    Wd, Dp = 33.0, 19.0
    root = empty("ratusz", (pos[0], pos[1], 0), (0, 0, yaw))
    mats = {'wall': M['wall_cream'], 'red': M['wall_terra'], 'ochre': M['wall_ochre'], 'trim': M['trim'], 'stone': M['sandstone'],
            'interior': M['interior'], 'roof': M['roof_dark'], 'copper': M['copper'], 'gold': M['gold'], 'glass': M['glass'],
            'frame': M['frame'], 'door': M['door'], 'iron': M['iron'], 'wood': M['wood_dark'], 'white': M['wall_white'], 'blue': M['wall_blue']}
    gm = MB(); mb = MB()
    zg = 4.8; z1 = 9.7; z2 = 14.3                     # ground, tier-1 top, tier-2 top
    nb = 7; bp = Wd / nb
    # ground floor: ashlar with three portals and windows
    holes = []
    for c in range(nb):
        cx = bp * (c + 0.5)
        if c in (1, 3, 5): holes.append(arch_pts(cx - 1.15, cx + 1.15, 0.0, 2.8, 12))
        else: holes.append(rect_pts(cx - 0.7, cx + 0.7, 1.5, 3.6))
    gm.slab_y('stone', [rect_pts(0, Wd, 0, zg)] + holes, 0.0, 1.1)
    for c in range(nb):
        cx = bp * (c + 0.5)
        if c in (1, 3, 5):
            mb.box('door', (cx, 0.9, 1.45), (2.0, 0.1, 2.9)); mb.box('stone', (cx, -0.7, 0.08), (3.4, 1.6, 0.16), uvm=0.5)
        else:
            mb.box('interior', (cx, 0.9, 2.55), (1.3, 0.1, 2.0)); mb.box('glass', (cx, 0.88, 2.55), (1.2, 0.04, 1.9))
            mb.box('iron', (cx, 0.82, 2.55), (0.05, 0.06, 2.0)); mb.box('iron', (cx, 0.82, 2.0), (1.3, 0.06, 0.05))
    for zz, hh in ((zg + 0.45, 0.5), (z1 + 0.55, 0.4)):          # painted terracotta friezes
        mb.box('red', (Wd / 2, -0.28, zz), (Wd + 0.5, 0.12, hh), grain=False)
    # plinth, band between ground and loggia
    mb.box('stone', (Wd / 2, -0.12, 0.3), (Wd + 0.2, 0.3, 0.6), uvm=0.5)
    mb.box('trim', (Wd / 2, -0.25, zg + 0.1), (Wd + 0.6, 0.7, 0.35), grain=False)
    # loggia: two tiers of arches in front of a recessed wall (y = 4.2)
    yb = 4.2
    for tier, (za, zb, hole_w, arch_rise, mat) in enumerate(((zg + 0.2, z1, bp - 1.1, 0.0, 'wall'), (z1 + 0.35, z2, bp - 1.3, 0.0, 'wall'))):
        tholes = []
        for c in range(nb):
            cx = bp * (c + 0.5)
            ztop = zb - 0.2 - (hole_w / 2)
            tholes.append(arch_pts(cx - hole_w / 2, cx + hole_w / 2, za + 0.05, ztop, 14))
        gm.slab_y(mat, [rect_pts(0, Wd, za, zb)] + tholes, 0.0, 1.0)
        # floor, ceiling of the loggia depth
        mb.box('wood', (Wd / 2, yb / 2 + 0.5, za + 0.02), (Wd, yb - 0.6, 0.12), uvm=0.5)
        mb.box('wood', (Wd / 2, yb / 2 + 0.5, zb - 0.25), (Wd - 0.2, yb - 0.6, 0.12), uvm=0.5)
        # balustrade between piers: small turned columns
        for c in range(nb):
            cx = bp * (c + 0.5)
            for k in range(-4, 5):
                mb.box('trim', (cx + k * (hole_w / 9.0), -0.02 + 0.5, za + 0.55), (0.07, 0.07, 0.9), grain=False)
            mb.box('trim', (cx, 0.5, za + 1.05), (hole_w, 0.18, 0.1), grain=False)
        # back wall with openings
        for c in range(nb):
            cx = bp * (c + 0.5)
            mb.box('interior', (cx, yb - 0.1, (za + zb) / 2 - 0.4), (1.5, 0.05, 2.4), grain=False)
            mb.box('frame', (cx, yb - 0.14, (za + zb) / 2 - 0.4), (1.7, 0.05, 2.6), grain=False)
            mb.box('ochre' if tier == 0 else 'red', (cx, yb - 0.17, (za + zb) / 2 - 0.4), (1.3, 0.03, 2.2), grain=False)
        mb.box('ochre' if tier == 0 else 'red', (Wd / 2, yb, (za + zb) / 2), (Wd, 0.2, zb - za))
    mb.box('trim', (Wd / 2, -0.22, z1 + 0.14), (Wd + 0.5, 0.75, 0.3), grain=False)
    mb.box('trim', (Wd / 2, -0.3, z2 + 0.2), (Wd + 0.9, 1.0, 0.4), grain=False)
    # attic: crenellated parapet with three triangular gables
    za = z2 + 0.4
    for k in range(int(Wd / 1.2)):
        mb.box('wall', (0.6 + k * 1.2, 0.25, za + 0.5), (0.8, 0.6, 1.0))
        mb.box('trim', (0.6 + k * 1.2, 0.25, za + 1.05), (0.9, 0.7, 0.1), grain=False)
    mb.box('red', (Wd / 2, 0.7, za + 0.3), (Wd, 0.5, 0.6))
    for gx, gwid in ((Wd * 0.2, 6.0), (Wd * 0.5, 7.6), (Wd * 0.8, 6.0)):
        gh = gwid * 0.62
        prof = [(gx + gwid / 2, za + 0.6), (gx + gwid / 2 - 0.5, za + 0.6 + gh * 0.5), (gx, za + 0.6 + gh), (gx - gwid / 2 + 0.5, za + 0.6 + gh * 0.5), (gx - gwid / 2, za + 0.6)]
        gm.slab_y('ochre', [prof, rect_pts(gx - 0.5, gx + 0.5, za + 1.5, za + 1.5 + gh * 0.4)], 0.5, 1.1)
        mb.blob('gold', (gx, 0.8, za + 0.7 + gh + 0.2), 0.22)
    # roof (hip) and main block
    mb.box('wall', (Wd / 2, Dp / 2 + 0.5, z2 / 2), (Wd - 0.2, Dp - 1.0, z2), grain=False)
    ry0 = 1.2
    mb.prism_x('roof', 0.2, Wd - 0.2, [(ry0 + 1.0, za + 0.6), (Dp - 0.5, za + 0.6), (Dp * 0.5 + 0.6, za + 7.8), (ry0 + 4.0, za + 7.8)], uvm=0.5)
    # corner turrets
    for tx in (1.6, Wd - 1.6):
        for ty in (1.6, Dp - 2.0):
            mb.box('wall', (tx, ty, za + 2.2), (1.8, 1.8, 4.4))
            mb.box('trim', (tx, ty, za + 4.5), (2.1, 2.1, 0.25))
            cone = [(tx, ty)]
        # cone roofs as copper pyramids
    cm = MB()
    for tx in (1.6, Wd - 1.6):
        for ty in (1.6, Dp - 2.0):
            _cone(cm, 'copper', (tx, ty, za + 4.6), 1.45, 4.6, 8)
            cm.blob('gold', (tx, ty, za + 9.4), 0.2)
    # tower: square shaft, balcony, octagonal stages, spire
    tx, ty = Wd / 2, 9.5
    mb.box('wall', (tx, ty, za + 9.0), (7.0, 7.0, 18.0))
    mb.box('trim', (tx, ty, za + 18.1), (8.2, 8.2, 0.4), grain=False)
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box('trim', (tx + sx * 3.5, ty + sy * 3.5, za + 9.0), (0.6, 0.6, 18.0), grain=False)
    for k in range(4):                      # clock faces on the 4 sides
        ang = k * math.pi / 2
        c, s = math.cos(ang), math.sin(ang)
        px, py = tx + c * 3.55, ty + s * 3.55
        mb.box('trim', (tx, ty, 0), (0.001, 0.001, 0.001)) if False else None
    # clock faces: front side (towards -Y) with gold ring and dark dial
    clock = MB()
    for k in range(4):
        ang = k * math.pi / 2 - math.pi / 2
        px, py = tx + math.cos(ang) * 3.58, ty + math.sin(ang) * 3.58
        _disc(clock, 'gold', (px, py, za + 12.3), 1.85, ang, 0.1)
        _disc(clock, 'white', (px + math.cos(ang) * 0.06, py + math.sin(ang) * 0.06, za + 12.3), 1.6, ang, 0.1)
    oct1 = [(tx, ty, za + 18.3)]
    _prism_poly(mb, 'wall', (tx, ty), 3.7, 8, za + 18.3, za + 25.5)
    _prism_poly(mb, 'trim', (tx, ty), 4.1, 8, za + 25.5, za + 26.0)
    _prism_poly(mb, 'wall', (tx, ty), 2.7, 8, za + 26.0, za + 31.0)
    for k in range(8):
        ang = k * math.pi / 4 + math.pi / 8
        px, py = tx + math.cos(ang) * 3.4, ty + math.sin(ang) * 3.4
        mb.box('interior', (px, py, za + 22.0), (1.3, 0.12, 3.0), rot_z=ang + math.pi / 2)
    _cone(cm, 'copper', (tx, ty, za + 31.0), 3.0, 9.0, 8)
    _prism_poly(mb, 'trim', (tx, ty), 1.5, 8, za + 39.5, za + 40.2)
    _cone(cm, 'copper', (tx, ty, za + 40.0), 1.5, 8.0, 8)
    cm.blob('gold', (tx, ty, za + 48.4), 0.45, 2)
    cyl("spire", 0.05, 4.0, (tx, ty, za + 50.3), M['gold'], parent=root, seg=6)
    # tower gallery railings
    mats['white'] = M['wall_white']
    mb.emit("ratusz_d", mats, parent=root)
    gm.emit("ratusz_w", mats, parent=root)
    cm.emit("ratusz_c", mats, parent=root)
    clock.emit("ratusz_k", mats, parent=root)
    return root


def _cone(mb, key, c, r, h, seg):
    b = mb.bm(key); uv = b.loops.layers.uv.verify()
    ap = b.verts.new((c[0], c[1], c[2] + h))
    ring = [b.verts.new((c[0] + r * math.cos(2 * math.pi * i / seg), c[1] + r * math.sin(2 * math.pi * i / seg), c[2])) for i in range(seg)]
    fs = [b.faces.new((ring[(i + 1) % seg], ring[i], ap)) for i in range(seg)]
    fs.append(b.faces.new(ring[::-1]))
    for f in fs:
        for l in f.loops: l[uv].uv = (math.atan2(l.vert.co.y - c[1], l.vert.co.x - c[0]) * r, l.vert.co.z)


def _prism_poly(mb, key, c, r, seg, z0, z1):
    b = mb.bm(key); uv = b.loops.layers.uv.verify()
    lo = [b.verts.new((c[0] + r * math.cos(2 * math.pi * i / seg + math.pi / seg), c[1] + r * math.sin(2 * math.pi * i / seg + math.pi / seg), z0)) for i in range(seg)]
    hi = [b.verts.new((v.co.x, v.co.y, z1)) for v in lo]
    fs = [b.faces.new((lo[i], lo[(i + 1) % seg], hi[(i + 1) % seg], hi[i])) for i in range(seg)]
    fs.append(b.faces.new(lo[::-1])); fs.append(b.faces.new(hi))
    for f in fs:
        for l in f.loops: l[uv].uv = (math.atan2(l.vert.co.y - c[1], l.vert.co.x - c[0]) * r, l.vert.co.z)


def _disc(mb, key, c, r, ang, th, seg=24):
    """flat disc facing direction `ang` (xy plane angle of outward normal)"""
    b = mb.bm(key); uv = b.loops.layers.uv.verify()
    n = Vector((math.cos(ang), math.sin(ang), 0)); t = Vector((-math.sin(ang), math.cos(ang), 0)); up = Vector((0, 0, 1))
    ring0 = [b.verts.new(Vector(c) + t * r * math.cos(2 * math.pi * i / seg) + up * r * math.sin(2 * math.pi * i / seg)) for i in range(seg)]
    ring1 = [b.verts.new(v.co - n * th) for v in ring0]
    fs = [b.faces.new(ring0[::-1]), b.faces.new(ring1)]
    for i in range(seg): fs.append(b.faces.new((ring0[i], ring0[(i + 1) % seg], ring1[(i + 1) % seg], ring1[i])))
    for f in fs:
        for l in f.loops: l[uv].uv = (l.vert.co.x, l.vert.co.z)


# ------------------------------------------------------------------ fountain, pillory, props ---------------------
def fountain(cx, cy):
    """Proserpina-style fountain: octagonal basin, water, baluster with two bowls and a figure"""
    mb = MB(); mats = {'stone': M['sandstone'], 'water': M['water'], 'gold': M['gold'], 'iron': M['iron']}
    _prism_poly(mb, 'stone', (cx, cy), 3.0, 8, 0.0, 0.62)
    _prism_poly(mb, 'water', (cx, cy), 2.78, 8, 0.0, 0.5)
    _prism_poly(mb, 'stone', (cx, cy), 0.9, 8, 0.0, 1.2)
    _prism_poly(mb, 'stone', (cx, cy), 0.35, 8, 0.0, 2.4)
    _cone(mb, 'stone', (cx, cy, 1.1), 1.35, 0.35, 12)
    _cone(mb, 'stone', (cx, cy, 2.0), 0.85, 0.28, 12)
    _prism_poly(mb, 'stone', (cx, cy), 0.55, 8, 2.28, 2.45)
    mb.blob('stone', (cx, cy, 2.95), 0.3, 2)
    b = mb.bm('stone')
    bmesh_ellipsoid(mb, 'stone', (cx, cy, 3.5), (0.22, 0.2, 0.55))
    mb.blob('stone', (cx, cy, 4.15), 0.17, 2)
    mb.emit("fountain", mats)


def bmesh_ellipsoid(mb, key, c, rad):
    b = mb.bm(key)
    res = bmesh.ops.create_icosphere(b, subdivisions=2, radius=1.0)
    for v in res['verts']: v.co.x *= rad[0]; v.co.y *= rad[1]; v.co.z *= rad[2]
    bmesh.ops.translate(b, verts=res['verts'], vec=c)
    uv = b.loops.layers.uv.verify()
    for v in res['verts']:
        for f in v.link_faces:
            for l in f.loops: l[uv].uv = (l.vert.co.x * 2, l.vert.co.z * 2)


def pillory(cx, cy):
    mb = MB(); mats = {'stone': M['sandstone'], 'gold': M['gold']}
    _prism_poly(mb, 'stone', (cx, cy), 1.4, 8, 0.0, 0.3)
    _prism_poly(mb, 'stone', (cx, cy), 1.0, 8, 0.3, 0.6)
    _prism_poly(mb, 'stone', (cx, cy), 0.42, 8, 0.6, 3.6)
    _prism_poly(mb, 'stone', (cx, cy), 0.55, 8, 3.6, 3.9)
    mb.blob('stone', (cx, cy, 4.15), 0.28, 2)
    _cone(mb, 'stone', (cx, cy, 4.3), 0.2, 0.6, 8)
    mb.emit("pillory", mats)


def lamp_post(x, y):
    cyl("lp", 0.045, 3.8, (x, y, 1.9), M['iron'], seg=10)
    cyl("lpb", 0.13, 0.7, (x, y, 0.35), M['iron'], seg=10, r2=0.07)
    cyl("lpc", 0.1, 0.08, (x, y, 3.8), M['iron'], seg=10)
    box("lpl", (0.28, 0.28, 0.42), (x, y, 4.05), M['lamp'])
    box("lpt", (0.4, 0.4, 0.05), (x, y, 4.3), M['iron'])


def planter_tree(x, y, size=1.0):
    mb = MB(); mats = {'wood': M['wood_dark'], 'soil': M['iron']}
    mb.box('wood', (0, 0, 0.35), (0.8, 0.8, 0.7))
    mb.box('soil', (0, 0, 0.7), (0.7, 0.7, 0.04))
    rr = random.Random(int(x * 10 + y * 7))
    mb.tube('wood', (0, 0, 0.7), (0.03, 0.02, 1.9), 0.045, 0.03, 8, caps=False)
    mb.emit("ptree", mats, loc=(x, y, 0))
    lm = MB(); lmats = {'leaf': M['leaf']}
    for _ in range(260):
        a = rr.uniform(0, 6.283); rad = rr.uniform(0, 1.0) ** 0.7 * 0.62; zz = rr.uniform(-1, 1)
        sq = math.sqrt(max(0.0, 1 - zz * zz * 0.7))
        lm.blob('leaf', (math.cos(a) * rad * sq, math.sin(a) * rad * sq, 2.5 + zz * 0.75), rr.uniform(0.09, 0.15), 2)
    lm.emit("ptree_leaves", lmats, loc=(x, y, 0), smooth=True)


def pigeon(x, y, yaw, r):
    root = empty("pigeon", (x, y, 0), (0, 0, yaw))
    ball("pb", 0.06, (0, 0, 0.1), M['pigeon'], scale=(1.7, 0.9, 0.9), parent=root, seg=10, rings=6)
    ball("pn", 0.04, (0.07, 0, 0.14), M['pigeon_w'], parent=root, seg=8, rings=5)
    ball("ph", 0.032, (0.11, 0, 0.17), M['pigeon'], parent=root, seg=8, rings=5)
    box("pt", (0.1, 0.05, 0.015), (-0.13, 0, 0.1), M['pigeon'], rot=(0, 0.2, 0), parent=root)
    return root


STALLS = []


def market_stalls():
    """white-canopy market stalls on the square (as on the real Rynek), with goods"""
    r = random.Random(31)
    spots = [(14, -21), (22, -20), (29, -23), (44, -21), (46, -33), (30, -30), (20, -27), (10, -22), (72, -12), (80, -10), (40, -37), (8, -36)]
    for k, (x, y) in enumerate(spots):
        STALLS.append((x, y))
        mb = MB(); mats = {'canvas': M['awn_cream'], 'pole': M['iron'], 'wood': M['wood_dark'], 'g1': M['flower_r'], 'g2': M['flower_y'], 'g3': M['leaf'], 'g4': M['flower_p']}
        for (px, py) in ((1.7, 0), (-1.7, 0), (0, 1.7), (0, -1.7)):
            mb.tube('pole', (px, py, 0), (px, py, 2.3), 0.03, 0.03, 6, caps=False)
        _cone(mb, 'canvas', (0, 0, 2.3), 1.7, 0.7, 4)
        mb.box('wood', (0, 0.9, 0.45), (2.6, 0.8, 0.9))
        for _ in range(26):
            mb.blob(r.choice(('g1', 'g2', 'g3', 'g4', 'g3')), (r.uniform(-1.1, 1.1), 0.9 + r.uniform(-0.3, 0.3), 1.0 + r.uniform(0, 0.15)), r.uniform(0.07, 0.13), 1)
        mb.emit("stall%d" % k, mats, loc=(x, y, 0), rot=(0, 0, r.choice((0, math.pi / 2, math.pi, -math.pi / 2)) + r.uniform(-0.2, 0.2)))


def big_tree(x, y, s=1.0):
    mb = MB(); mats = {'wood': M['wood_dark']}
    mb.tube('wood', (0, 0, 0), (0.05, 0.03, 4.2 * s), 0.22 * s, 0.14 * s, 8, caps=False)
    mb.emit("btree", mats, loc=(x, y, 0))
    rr = random.Random(int(x * 3 + y * 11))
    lm = MB(); lmats = {'leaf': M['leaf']}
    for _ in range(170):
        a = rr.uniform(0, 6.283); rad = rr.uniform(0, 1.0) ** 0.6 * 3.0 * s; zz = rr.uniform(-1, 1)
        sq = math.sqrt(max(0.0, 1 - zz * zz * 0.8))
        lm.blob('leaf', (math.cos(a) * rad * sq, math.sin(a) * rad * sq, 6.3 * s + zz * 2.4 * s), rr.uniform(0.45, 0.75) * s, 2)
    lm.emit("btree_l", lmats, loc=(x, y, 0), smooth=True)


def church_tower(x, y, h=42.0):
    mb = MB(); cm = MB()
    mats = {'brick': M['brick'], 'trim': M['trim'], 'copper': M['copper'], 'gold': M['gold'], 'wall': M['wall_cream']}
    mb.box('brick', (0, 0, h * 0.35), (7.0, 7.0, h * 0.7))
    mb.box('trim', (0, 0, h * 0.7 + 0.2), (7.8, 7.8, 0.4), grain=False)
    _prism_poly(mb, 'wall', (0, 0), 3.3, 8, h * 0.7 + 0.4, h * 0.88)
    _cone(cm, 'copper', (0, 0, h * 0.88), 3.6, h * 0.34, 8)
    cm.blob('gold', (0, 0, h * 0.88 + h * 0.34 + 0.2), 0.4, 2)
    mb.emit("church", mats, loc=(x, y, 0)); cm.emit("church_c", mats, loc=(x, y, 0))
