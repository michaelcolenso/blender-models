# Highland studio upgrade

[Read the complete upgrade guide](UPGRADE-GUIDE.md).

This treatment keeps the source pipe geometry and chapter order, starts outside the existing exterior model, subdues the drawing to 25% warm gray, adds studio lighting/coated pipes/ghost walls, replaces flat access outlines with dashed volumes, and uses projected labels plus gated assembly/flow cues.

Scripts, in order:

1. `prepare_blueprint.py` — re-rasterize the same P4.01 source crop at 400 DPI.
2. `studio_upgrade.py` — build a separate editable Blender variant with the three source-derived scenes.
3. `validate_studio.py` — verify source geometry, staging, return direction and camera continuity/framing.
4. `render_studio.py` — render representative stills or a resumable sequence; record settings and projected label anchors.
5. `studio_composite.py` — apply the exact-color paper, drawing/context overlays, sharp labels, exterior dissolve and narrated 90-second assembly.

`studio-config.json` contains the presentation choices and provenance. `blender_compat.py` provides optional EEVEE preview and restrained glow helpers for Blender 4/5. The original source models remain separate.

The saved Blender file uses real shaded materials. Its preview renderer can composite the faint drawing/context fills separately to avoid low-sample transparency grain. This is described in the guide. A low-sample/interpolated review is not a native 4K production render; actual settings are recorded with the rendered output.
