# Highland / revision 06 dusk animation

[Play or download the 18-second animation](Highland-dusk-drawing-reconciled-18s.mp4) · [Poster](Highland-dusk-poster.png)

The camera approaches the building and rises to reveal the revised R5 terraces and roof. Output is 1280 × 720 at 24 fps. It uses the current reconciled model with 960 architectural meshes and 192 opening records; the native model, camera keys and architectural geometry remain unchanged.

This is an illustrative visualization. Source plan positions are provisional; complete profiles, guards and site remain assumed. North stair/MU and R1 entries stay deferred. The film uses Three.js material/lighting approximations; [the native Cycles dusk still](../highland-drawings/Highland-dusk-drawing-reconciled.png) remains the material reference.

The editable [Blender model](../highland-drawings/Highland-drawing-reconciled.blend), [portable GLB](../highland-drawings/Highland-drawing-reconciled.glb) and [source review](../highland-drawings/Highland-drawing-reconciliation.pdf) are in the drawing-reconciliation delivery. This film is a new revision 06 presentation; the old revision 03 film remains separate.

Source hashes and 432 native camera positions are recorded in `source-validation.json` and `camera-path.json`. `media-validation.json` covers full movie decode, timing, color, frame completeness and nonblank imagery. `visual-review.json` records exact inspected frames and poster. Reproduction scripts and pinned dependencies are under `projects/highland-visualization/`.

The deferred north comparison retains its 42.443-overview-pixel diagnostic maximum; other source residuals remain in the linked drawing review. The animation does not resolve those differences.
