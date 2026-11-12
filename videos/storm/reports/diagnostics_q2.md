# Scene diagnostics (q2 state)

## Render / colour
- engine CYCLES, view AgX / look AgX - Base Contrast, exposure -3.049999952316284
- bounces max/diff/gloss/trans/transp/vol: 12/4/6/12/16/0
- clamp indirect 8.0, blur_glossy 0.5, caustics refl/refr False/False
- denoiser OPENIMAGEDENOISE, passes RGB_ALBEDO_NORMAL, adaptive thr 0.019999999552965164
- film filter width 1.5, motion blur True

## Lights (should be: sun/sky only by day)
- downlight0: SPOT 60.0 W colour (1.0, 0.72, 0.45)
- downlight1: SPOT 60.0 W colour (1.0, 0.72, 0.45)
- downlight2: SPOT 60.0 W colour (1.0, 0.72, 0.45)
- downlight3: SPOT 60.0 W colour (1.0, 0.72, 0.45)
- downlight4: SPOT 60.0 W colour (1.0, 0.72, 0.45)
- downlight5: SPOT 60.0 W colour (1.0, 0.72, 0.45)
- pendant0: POINT 25.0 W colour (1.0, 0.72, 0.45)
- pendant1: POINT 25.0 W colour (1.0, 0.72, 0.45)
- sky MULTIPLE_SCATTERING, sun disc True, elev 32.0, aerosol 1.399999976158142, air 1.0

## Image textures: colour space of data maps (normal/rough/disp must be Non-Color)
- images loaded: 206; colour-space problems: 17
  - celandine_01_alpha.png (albedo flagged Non-Color): Non-Color
  - fern_02_alpha.png (albedo flagged Non-Color): Non-Color
  - fir_tree_01_twig_alpha.png (albedo flagged Non-Color): Non-Color
  - fir_tree_01_twig_mask.png (albedo flagged Non-Color): Non-Color
  - grass_medium_01_alpha.png (albedo flagged Non-Color): Non-Color
  - grass_medium_02_alpha.png (albedo flagged Non-Color): Non-Color
  - modern_arm_chair_01_legs_diff.png: sRGB
  - modern_arm_chair_01_pillow_diff.png: sRGB
  - rough_linen_diff.png: sRGB
  - shrub_02_alpha.png (albedo flagged Non-Color): Non-Color
  - shrub_02_mask.png (albedo flagged Non-Color): Non-Color
  - shrub_03_alpha.png (albedo flagged Non-Color): Non-Color
  - shrub_04_alpha.png (albedo flagged Non-Color): Non-Color
  - shrub_sorrel_01_alpha.png (albedo flagged Non-Color): Non-Color
  - white_plaster_02_rough_4k.png: sRGB
  - white_rough_plaster_diff_4k.png: sRGB
  - wooden_lantern_01_glass_opacity.png (albedo flagged Non-Color): Non-Color

## Normal maps / bump per material
- baltic_water: bump strength=0.08 dist=0.0010000000474974513
- band_mulch: normalmap space=TANGENT strength=1.00 img=forrest_ground_01_nor_4k.png.002 cs=Non-Color; displacement scale=0.03500000014901161 (method BUMP)
- beach_sand: normalmap space=TANGENT strength=1.00 img=gravelly_sand_nor_gl.png cs=Non-Color; displacement scale=0.07999999821186066 (method BUMP)
- bed_mulch: normalmap space=TANGENT strength=1.00 img=forrest_ground_01_nor_4k.png.003 cs=Non-Color; displacement scale=0.03500000014901161 (method BUMP)
- boulder_01: normalmap space=TANGENT strength=1.00 img=boulder_01_nor_gl.png cs=Non-Color
- ceramic_vase_01: normalmap space=TANGENT strength=1.00 img=ceramic_vase_01_nor_gl.png cs=Non-Color
- ceramic_vase_01.001: normalmap space=TANGENT strength=1.00 img=ceramic_vase_01_nor_gl.png.001 cs=Non-Color
- facade_architectural_concrete: normalmap space=TANGENT strength=1.00 img=smooth_concrete_floor_nor_gl.png cs=Non-Color; displacement scale=0.02500000037252903 (method BUMP)
- facade_plaster: normalmap space=TANGENT strength=1.00 img=white_plaster_02_nor_4k.png cs=Non-Color; displacement scale=0.009999999776482582 (method BUMP)
- fern_02: normalmap space=TANGENT strength=1.00 img=fern_02_nor_gl.png cs=Non-Color
- fir_tree_01_bark: normalmap space=TANGENT strength=1.00 img=fir_tree_01_bark_nor_gl.png cs=Non-Color; displacement scale=0.20000000298023224 (method BUMP)
- fir_tree_01_dead_branches: normalmap space=TANGENT strength=1.00 img=fir_tree_01_bark_nor_gl.png cs=Non-Color; displacement scale=0.10000000149011612 (method BUMP)
- fir_tree_01_trunk_a: normalmap space=TANGENT strength=1.00 img=fir_tree_01_trunk_a_nor_gl.png cs=Non-Color; normalmap space=TANGENT strength=1.00 img=fir_tree_01_bark_nor_gl.png cs=Non-Color; displacement scale=1.0 (method BUMP)
- fir_tree_01_trunk_b: normalmap space=TANGENT strength=1.00 img=fir_tree_01_trunk_b_nor_gl.png cs=Non-Color; normalmap space=TANGENT strength=1.00 img=fir_tree_01_bark_nor_gl.png cs=Non-Color; displacement scale=1.0 (method BUMP)
- fir_tree_01_trunk_c: normalmap space=TANGENT strength=1.00 img=fir_tree_01_trunk_c_nor_gl.png cs=Non-Color; normalmap space=TANGENT strength=1.00 img=fir_tree_01_bark_nor_gl.png cs=Non-Color; displacement scale=1.0 (method BUMP)
- fir_tree_01_twig: normalmap space=TANGENT strength=1.00 img=fir_tree_01_twig_nor_gl.png cs=Non-Color
- int_shelf_oak: normalmap space=TANGENT strength=1.00 img=white_oak_veneer_nor_gl.png cs=Non-Color; displacement scale=0.009999999776482582 (method BUMP)
- interior_oak_floor: normalmap space=TANGENT strength=1.00 img=white_oak_veneer_nor_gl.png cs=Non-Color; displacement scale=0.009999999776482582 (method BUMP)
- lawn_soil: normalmap space=TANGENT strength=1.00 img=forrest_ground_01_nor_4k.png cs=Non-Color; displacement scale=0.03500000014901161 (method BUMP)
- mid_century_lounge_chair: normalmap space=TANGENT strength=1.00 img=mid_century_lounge_chair_nor_gl.png cs=Non-Color
- modern_arm_chair_01_legs: normalmap space=TANGENT strength=1.00 img=modern_arm_chair_01_legs_nor_gl.png cs=Non-Color
- modern_arm_chair_01_pillow: normalmap space=TANGENT strength=1.00 img=modern_arm_chair_01_pillow_nor_gl.png cs=Non-Color
- modern_ceiling_globe: normalmap space=TANGENT strength=1.00 img=modern_ceiling_lamp_01_gl_normal.png cs=Non-Color
- modern_ceiling_lamp_01: normalmap space=TANGENT strength=1.00 img=modern_ceiling_lamp_01_gl_normal.png cs=Non-Color
- modern_ceiling_lamp_01_glass: normalmap space=TANGENT strength=1.00 img=modern_ceiling_lamp_01_gl_normal.png cs=Non-Color
- modern_coffee_table_01: normalmap space=TANGENT strength=1.00 img=modern_coffee_table_01_nor_gl.png cs=Non-Color
- napkin_linen: normalmap space=TANGENT strength=1.00 img=rough_linen_nor_gl.png cs=Non-Color; displacement scale=0.0005000000237487257 (method BUMP)
- neighbour_render: normalmap space=TANGENT strength=1.00 img=white_rough_plaster_nor_4k.png cs=Non-Color; displacement scale=0.014999999664723873 (method BUMP)
- pier_boards: normalmap space=TANGENT strength=1.00 img=wood_planks_nor_gl.png cs=Non-Color; displacement scale=0.004999999888241291 (method BUMP)
- pier_piles: normalmap space=TANGENT strength=1.00 img=wood_planks_nor_gl.png cs=Non-Color; displacement scale=0.004999999888241291 (method BUMP)
- pier_rail: normalmap space=TANGENT strength=1.00 img=wood_planks_nor_gl.png cs=Non-Color; displacement scale=0.004999999888241291 (method BUMP)
- planter_concrete: normalmap space=TANGENT strength=1.00 img=smooth_concrete_floor_nor_gl.png.002 cs=Non-Color; displacement scale=0.02500000037252903 (method BUMP)
- planter_soil: normalmap space=TANGENT strength=1.00 img=forrest_ground_01_nor_4k.png.001 cs=Non-Color; displacement scale=0.03500000014901161 (method BUMP)
- potted_plant_01_leaves: normalmap space=TANGENT strength=1.00 img=potted_plant_01_leaves_nor_gl.png.001 cs=Non-Color
- potted_plant_01_pot: normalmap space=TANGENT strength=1.00 img=potted_plant_01_pot_nor_gl.png cs=Non-Color
- potted_plant_02_leaves: normalmap space=TANGENT strength=1.00 img=potted_plant_02_leaves_nor_gl.png cs=Non-Color
- potted_plant_02_pot: normalmap space=TANGENT strength=1.00 img=potted_plant_02_pot_nor_gl.png cs=Non-Color
- potted_plant_04: normalmap space=TANGENT strength=1.00 img=potted_plant_04_nor_gl.png cs=Non-Color
- RIVON_powder_RAL9005: bump strength=0.22 dist=0.0002500000118743628
- shrub_sorrel_01: normalmap space=TANGENT strength=1.00 img=shrub_sorrel_01_nor_gl.png cs=Non-Color
- side_table_01: normalmap space=TANGENT strength=1.00 img=side_table_01_gl_normal.png cs=Non-Color
- sofa_02: normalmap space=TANGENT strength=1.00 img=sofa_02_nor_gl.png cs=Non-Color
- step_concrete: normalmap space=TANGENT strength=1.00 img=smooth_concrete_floor_nor_gl.png.001 cs=Non-Color; displacement scale=0.02500000037252903 (method BUMP)
- thermo_ash_deck: normalmap space=TANGENT strength=1.00 img=oak_veneer_01_nor_gl.png.001 cs=Non-Color; displacement scale=0.009999999776482582 (method BUMP)
- tree_small_02_branches: normalmap space=TANGENT strength=1.00 img=tree_small_02_branch_nor_gl.png cs=Non-Color
- tree_small_02_trunk: normalmap space=TANGENT strength=1.00 img=tree_small_02_nor_gl.png cs=Non-Color
- wooden_lantern_01: normalmap space=TANGENT strength=1.00 img=wooden_lantern_01_nor_gl.png cs=Non-Color
- wooden_lantern_01_glass: normalmap space=TANGENT strength=1.00 img=wooden_lantern_01_glass_nor_gl.png cs=Non-Color

## Texture-space scale (UV metres per tile) on key objects
- deck_boards: 1.8300030534817036 m per UV unit; material thermo_ash_deck
- gf_wall: 2.4000000475187315 m per UV unit; material facade_architectural_concrete
- up_wall: 1.0 m per UV unit; material facade_plaster
- top_0: 1.829999755163549 m per UV unit; material table_oak_0
- step_E: 2.0000001655066377 m per UV unit; material step_concrete
- lawn: 2.0 m per UV unit; material lawn_soil
- planter0_a: 2.0 m per UV unit; material planter_concrete
- larch_00: 1.8300009970610058 m per UV unit; material larch_00

## Vegetation materials (translucency / subsurface present?)
- grass_medium_02: translucent_node=False, transmission=None, subsurface=None, alpha_linked=None
- grass_medium_02_sphere: translucent_node=False, transmission=0.0, subsurface=0.0, alpha_linked=False
- grass_medium_01: translucent_node=False, transmission=None, subsurface=None, alpha_linked=None
- fern_02: translucent_node=True, transmission=0.0, subsurface=0.0, alpha_linked=True
- celandine_01: translucent_node=False, transmission=None, subsurface=None, alpha_linked=None
- tree_small_02_branches: translucent_node=False, transmission=0.0, subsurface=0.0, alpha_linked=False
- tree_small_02_leaves: translucent_node=False, transmission=None, subsurface=None, alpha_linked=None
- tree_small_02_trunk: translucent_node=False, transmission=0.0, subsurface=0.0, alpha_linked=False
- shrub_sorrel_01: translucent_node=True, transmission=0.0, subsurface=0.0, alpha_linked=False
- shrub_04: translucent_node=False, transmission=None, subsurface=None, alpha_linked=None
- shrub_02: translucent_node=False, transmission=None, subsurface=None, alpha_linked=None
- shrub_01: translucent_node=False, transmission=None, subsurface=None, alpha_linked=None
- shrub_03: translucent_node=False, transmission=None, subsurface=None, alpha_linked=None
- lawn hair: count 90000 x children 2, length 0.23999999463558197, random 0.6000000238418579, clump 0.15000000596046448, systems 1 (single blade type)
- tree mesh reuse: {'planter0_a': 1, 'planter0_b': 1, 'planter0_c': 1, 'planter0_d': 1, 'Plane.006': 2, 'Plane.044': 2, 'Plane.004': 2, 'Plane.031': 1, 'Sphere.001': 1, 'planter0_soil': 1, 'BezierCurve.003': 14, 'planter1_a': 1, 'planter1_b': 1, 'planter1_c': 1, 'planter1_d': 1, 'Plane.005': 1, 'Plane.040': 1, 'planter1_soil': 1}

## Glass / wine
- wine_glass_0: verts 6241, non-manifold edges 96, materials ['wine_glass']
- wine_0: verts 1346, non-manifold edges 0, materials ['red_wine', 'red_wine_glass_interface']
- hero_drop: absent
- wine_glass: IOR 1.500, transm 1.0, rough linked, base (1.0, 1.0, 1.0, 1.0), volume []
- red_wine: IOR 1.333, transm 1.0, rough 0.0, base (1.0, 0.92, 0.92, 1.0), volume [('VOLUME_ABSORPTION', (0.74, 0.0, 0.07, 1.0), 900.0)]
- red_wine_glass_interface: IOR 0.877, transm 1.0, rough 0.0, base (1.0, 0.92, 0.92, 1.0), volume [('VOLUME_ABSORPTION', (0.74, 0.0, 0.07, 1.0), 900.0)]
- window_glass: IOR 1.500, transm 1.0, rough linked, base (0.93, 0.96, 0.95, 1.0), volume []
- meniscus: none (wine top is a flat disc)

## Interior
- int_floor: present
- int_back: present
- int_ceiling: present
- upper floor rooms behind first-floor windows: MISSING (black voids)
- curtains: none

## Camera (shots)
- sensor: vertical fit 36 mm; lenses wide 24 mm, s01 32 mm, glass 50 mm; DOF on