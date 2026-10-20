# Highland exterior continuation / revision 03

Start with `deliverables/highland-roof/Highland-roof-terrace-source-comparison.pdf`, then open `Highland-roof-and-terrace-revised.blend`. Both native scenes and the 432-frame dusk camera are saved. Revision 02 and the original handoff remain available for comparison.

The new delivery contains the corrected daylight still, 18-second dusk film, tagged GLB, fresh provenance views, source-pick images and exact validation records. The ZIP also includes the revision 02 native base, available drawing/photo references and reproduction scripts. No original architectural PDF is present.

## Completed

Selected terrace cornices/parapets now follow local elevation picks; the central brick band is 28 in above R5, southwest cornice 26 in and southeast cornice 30 in. These are provisional (+/-3 in), with assumed profiles and returns. Main roof coping tops match 406.25/407.75 ft; tower/clerestory caps match their inherited top controls. Main and tower coping corners are mitered. Tower bodies terminate below caps to avoid coincident faces. Two R5 headers now follow both sides of the retained roof-level split.

Eight south MN internal frame bars on R1-R4 are mirrored to the elevation's wide fixed/narrow operable pattern, approximately 65%/35% (+/-0.03). Opening extents, glass, sills, perimeter frames and horizontal rails are preserved. Camera fitting uses the revised terrace tops and the same nine manual photo picks; its residual is not an independent accuracy metric.

914 architectural meshes are unchanged. The bounded correction changes 39 existing meshes, removes two long roof-parapet objects and adds sixteen objects, yielding 969 architectural meshes. The registered plan polygons, all floor/grid controls and all 175 opening records are retained. The sixteen opening conflicts are still unresolved.

The film uses the full native camera move with Three.js materials and approximate lighting/context. Architecture is not decimated. Foliage simplification, 4x MSAA on rails/window frames over a depth-matched base and full-frame FXAA are documented in the capture evidence. Cycles is the native still/material reference. Thin rails can still shimmer; film glass and area-light appearance differ from Cycles.

## Next work

The next architectural change depends on better sources: original A2.03/A2.04/A2.07 and A3.01/A3.02 sheets, a window schedule and clearer north/return photographs. Resolve each of the eight south/eight north candidates with those records; do not add openings to meet a count. Confirm terrace sections, coping profiles and installed guards before replacing their assumptions. Site and neighboring facade details remain illustrative.

For a native Cycles movie, choose GPU/render-farm hardware and benchmark representative frames from the saved dusk camera before selecting production settings. The delivered CPU benchmark views are diagnostic low-resolution frames, not final movie frames.

## Reproduction and review

See `README.md` for exact commands. `geometry.json`, `presentation.json` and `photo-landmarks.json` drive the changes; `prepare.py` regenerates `geometry-revision.spec.json`. The builder starts from the delivered revision 02 native scene. Editing only a generated spec or the saved Blender file will not survive regeneration.

`geometry-validation.json` lists every allowed geometry change. `delivery-validation.json` covers the native readback, all 432 camera frames, packed assets, source controls and GLB. `media-validation.json` covers every decoded frame and encoding metadata. `visual-review.json` binds the actual images/PDF/movie to the review; `package-validation.json` covers the exact ZIP and CRC.

Movie PNGs are cached under ignored `build/highland-geometry/film-frames/`. A signature binds them to exact rendering inputs and runtime. Interrupted captures resume; changed inputs fail until the cache is moved/removed. Rebuilds overwrite the revision 03 outputs, so version delivered files before making another revision.
