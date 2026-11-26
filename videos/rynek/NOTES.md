# RIVON video #4 - "Stary Rynek w Poznaniu" (flat-roof gazebos replace parasols)

Concept: Stary Rynek in Poznan (colourful kamienice with gables, Ratusz with clock tower, fountain, pillory, granite setts).
A restaurant terrace has folding parasols; they fold and sink away, RIVON gazebos with a FLAT roof assemble in minutes,
are taken down again just as quickly (only the low Stopa feet stay on the paving), then all five assemble and guests enjoy them.
28 s, 30 fps, 840 frames (0..839), vertical 1080x1920. No text, no cartoon look, no close-up faces.

## Files
- `rynek_core.py` - helpers: bmesh builder (MB), slabs with real window reveals, procedural cobbles, PBR (bevel/AO/anti-tiling), lifecycle animation.
- `rynek_town.py` - kamienice, Ratusz, fountain, pillory, props.  `rynek_people.py` - chairs, tables, settings, seated guests.
- `rynek_gazebo.py` - RIVON Stopa/Trojak (exact STEP meshes in `cad/`), timber, flat-roof cassette, parasols.
- `build_rynek.py` - scene assembly, timeline constants (`UMB_T0`, `G0_ASM`, `G0_DIS`, `RE_ASM`...), camera keys.
- `render_rynek.py` - frame renderer (resumable). `.github/workflows/render-rynek.yml` - GitHub Actions farm (branch `rynek/<name>` + run.json).

## Timeline
0-84 parasols open; 84-194 fold & sink; 152-290 gazebo 1 assembles (close-ups); 318-415 quick take-down (Stopa stay);
420-575 all five assemble; 575-839 hero tracking shot with guests, festoon lights, Ratusz.

## Rules (from the owner)
Free assets only. Never start the full final render before the owner writes exactly «Утверждаю, запускай финальный рендер» after reviewing >=5 control frames.
Connector geometry/logo is final: only the exact STEP-derived meshes are used for metal parts.
