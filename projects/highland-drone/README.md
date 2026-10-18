# Highland lobby-to-corridor drone view

A 26-second, portrait flight for a phone: the camera approaches the east facade, crosses the broad glazed entrance of Lobby 110, follows its connector into Corridor 108, enters an illustrative elevator, rises to R2, and continues down Corridor 208 toward the stair. An interactive, self-contained HTML viewer has Play/Pause and scrubbing; the MP4 uses the same camera path and adds a synthesized stereo score. The walkthrough is a presentation study of public circulation, not an as-built interior survey.

## Basis

- `../highland-exterior/exterior.spec.json` and its GLB establish the exterior footprint, R1 level and the east `east-R1-08` entry opening. This opening is classified **entry** in the model; A2.03 shows lobby glazing/doors there. The flight does not assert a separate operable window.
- Architectural sheets **A2.03 and A2.04**, dated 04-02-07, locate **Lobby 110**, **Corridors 108/208**, two elevators, and Stair M1. A2.03 labels the core corridor at **6 ft**. A3.11 supplies R1/R2 floor elevations 353.00/363.25 ft, a 10 ft 3 in rise. The PDF SHA-256 is in `flight.spec.json`; high-resolution crops are in `source-review/`.
- The lobby, connector and long corridor rectangles in `flight.spec.json` are manually fitted to the plans and rounded. They use the exterior study's plan-coordinate system in inches. The six-foot R1 width is documented; R2 reuse and exact wall faces are provisional. The path and test points are recorded in feet for readability.

The existing exterior GLB contains no real interior partitions. Floors, walls, ceiling (assumed 8 ft 6 in clear), doors, elevator cab/fronts, fixtures, lighting and finishes in this tour are **illustrative**. A short dark transition at the glazing covers the switch to the plan-based interior. The vertical rise is documented, while the elevator car and door timing are not. This model does not depict residential unit interiors, concealed plumbing or an egress survey. The entry doors open with camera proximity; the elevator doors use the presentation timing. The gold ribbon traces the camera route, not a construction or accessible route. Upper-floor window illumination, tree motion, the external glass/brass elevator cutaway, and warm area lights are visual treatments.

## Build and check

Requirements: Python 3 with NumPy and Pillow, Node, npm, Chromium and FFmpeg. The build installs pinned `three`, `esbuild` and `playwright` packages from `package-lock.json` when needed, and uses the published exterior GLB. The source PDF is needed only to re-evaluate the manual geometry picks, not to run the animation.

```bash
bash projects/highland-drone/build.sh
```

Headless rendering checks the entrance ID, building/interior mesh counts, camera positions at every phase, the one-floor rise, mobile overflow, playback and browser errors. Full rendering encodes 624 frames at 24 fps to a 720 x 1280 H.264 MP4 with `faststart` for phone playback; `audio.py` generates the stereo score and muxes AAC without re-encoding the video. The browser checks verify animation behavior, not the accuracy of undimensioned interior walls. The deliverable viewer embeds the GLB and scripts; it opens as one HTML file after download. A Cycles/OptiX `.blend` render requires a modeled interior Blender scene and compatible GPU, neither of which is part of this tour.

The prior exterior study has unresolved facade/window differences. This flight relies on the R1 east lobby entry and the public-hall labels and does not resolve those exterior differences. The entry and corridor finishes should be replaced with site photos/measurements before the tour is presented as existing conditions.
