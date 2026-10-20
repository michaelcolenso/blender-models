# Daylight revision 02 / 20 October 2026

Starting point: exterior handoff commit `fab3bd0b4d09bd4231b2a39620501562a432011a`, originally PR #9.

| Area | Change | Source and status |
| --- | --- | --- |
| Camera | Fit a seven-parameter pinhole camera to nine manual photo/model correspondences; save picks, bounds and all residuals. | Photo-02 and simplified registered polygon; interpreted, not surveyed. |
| Opening conflicts | Recompute all 16 projected centers against outward-facing plan segments and their available jamb margins. Retain every unresolved candidate; no addition or relocation. | Existing south/north elevation crops, R1/R5 plan crops and inherited A2.04 registration. Original sheets needed. |
| Brick | Warmer paired colors, lighter mortar, restrained surface variation; continuous 203 × 67 mm procedural modules. | Photo appearance; dimensions/colors remain assumed. |
| Glazing/curtains | Clearer blue reflections; more open curtain panels; daytime lamp emission disabled. | Illustrative presentation choice. No verified interior reconstruction. |
| Daylight | Clear procedural diffuse illumination, warm sun and an interpreted blue gradient for camera/reflection rays. | Weather and exposure assumed; no photographic color calibration. |
| Landscape | Eight layered broadleaf/flowering shrubs along the terrace, with deterministic individual leaf meshes. | Photo character only; no surveyed planting plan or species schedule. |
| Delivery | Separate single-scene Blender revision, GLB, still, source comparison and evidence. | Earlier handoff model, movie, specs and other projects preserved. |
| Repeatable review | Register the saved daylight scene in the existing GitHub Actions shot catalog. | CI renders the exact committed native model. |

Architectural mesh SHA-256 remains `dd1b73461d3d2ba6a0b7e9e7d0ec2e446bae0e940a435455bd70539dc15ee97e` across all 955 protected meshes. Registered polygons, floor/grid spans and roof controls are unchanged. Complete architectural components remain assumed where their geometry is assumed; the camera fit does not promote provenance.

Known differences: the rooftop/terrace profile remains more exposed than in photo-02; some window proportions, bay returns and facade sections remain simplified. Context buildings, vehicles, street surfaces and planting remain illustrative. The sixteen return-opening candidates need the original drawing sheets or clearer photographs before geometry changes can be justified.
