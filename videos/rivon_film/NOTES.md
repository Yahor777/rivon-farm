# RIVON film "ONE SYSTEM. ENDLESS POSSIBILITIES" (30 s, 9:16)
Pergola = exact STEP meshes (Stopa x4, Trojak 3D x4, Mocowanie belek 2 x18) + timber boxes + screws in real O10 holes, from `layout.json`
(validated: 0 collisions, 0 misplaced screws). Mocowanie belek 2: base plate screwed flat to the INNER SIDE face of the long beam, rafter 45x95 dropped
into its channel (end butted to the plate, top flush with the beam - nothing sticks out above).
Environments (Polish plot from `assets.blend` = trimmed copy of the earlier video-2 scene: house, Mercedes, lawn with grass particles, fences, trees; textures reused from `../dzialka/textures`):
carport, barbecue, summer kitchen, lounge, commercial cafe terrace + the dark lab. The pergola stays at the world origin; the plot is moved/rotated per environment.
- `film_lib.py` materials, STL reader, pergola builder · `film_envs.py` props/lab · `build_film.py` env placement + camera shots · `render_film.py` renderer (resumable).
- Control frames: push branch `film/<name>` with run.json (see `.github/workflows/render-film.yml`).
Rules (owner): free assets only; no full final render until the owner writes exactly «Утверждаю, запускай финальный рендер» after >=5 control frames; connector geometry is final.

## v2 (daylight sets + timeline)
- `film_scenes.py` five bright sets (carport / barbecue / summer kitchen / lounge / cafe), `film_props.py` furniture + guests, `film_sets.py` houses/trees/materials.
- Light = truck-video recipe: saturated procedural sky ramp + warm SUN lamp (7.2 W/m2, ~35-50 deg), Khronos PBR Neutral, exposure +0.15; lab keeps AgX Medium High Contrast.
- `film_anim.py` timeline: 0-209 lab assembly, 210-689 five scenes x 96 frames, 690-899 lab disassembly + hero Trojak 3D + CTA.  `build_film.apply_frame(f)` sets env/pergola/hero/camera.
- Post: `post/finish_film.py` (grade, flash on cuts, CTA "Jedno rozwiazanie. Wiele mozliwosci." + RIVON logo, MP4), `post/sound_film.py` + `film_events.py` (synth material sounds).
