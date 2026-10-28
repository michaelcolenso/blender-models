# Highland: from plumbing diagram to architectural film

Prioritize **spatial depth**, then camera guidance and animated callouts. Keep the existing chapter structure and clean editorial layout. Make the drawing a quiet reference; let the replacement piping, planned access and current action carry the story.

This package includes executable Blender scripts, a separate editable studio variant, source-linked presentation settings and a revised 90-second review. The opening starts **outside the existing exterior model**, then dissolves to shared distribution before entering the Unit B / 106 pilot. The exterior is the existing photo-informed drawing study; the transition does not establish a particular window as the pilot's location.

## 1. Start from a protected copy

Keep the original installation models, animation and governing geometry specifications. `studio_upgrade.py` opens the existing animation, appends the existing exterior study and saves **output/Highland-studio-upgrade.blend**. It does not overwrite the source files. All pipe centerlines, radii, mesh vertices and local transforms are checked before and after the treatment. Added corner covers, ghost walls, access volumes and valve icons carry `status: assumed` and a presentation basis.

The new presentation settings are in **studio-config.json**. They supplement the installation specification; they do not establish measured routes, structural walls, materials, firestop details, real valve locations or an approved isolation boundary. The source title/location-block address discrepancy remains unresolved.

Use the existing folder structure from the project. A Python 3.11 environment with `bpy==5.0.1` is available in the prepared workspace. The scripts also run through Blender's background CLI:

```bash
blender --background --python studio_upgrade.py
# Optional licensed latitude-longitude HDRI:
blender --background --python studio_upgrade.py -- --hdri /path/to/studio.exr
```

These commands assume the script and its supplied project-relative inputs are in their packaged locations. Do not paste the entire file into an unsaved Blender text block with no filesystem location.

## 2. Set the studio lighting and render engine

Use **Cycles** for the deliverable: physical area-light shadows, a true shadow catcher, Principled materials and a controllable contact contribution. Enable six total bounces, two diffuse, three glossy, four transmission and twelve transparent bounces. Keep motion blur and depth of field off for this technical film. They soften pipe paths and source references.

The script supplies a genuine float EXR environment generated from neutral softbox shapes. It is an authored studio HDRI, not a photographic sky. Use its World strength **0.12**. A licensed studio HDR/EXR can replace it with `--hdri`; set its input color space according to the asset metadata. Its exposure may need adjustment because HDRIs have different radiometric ranges. There is no universal strength that normalizes every HDRI.

The included authored EXR is **sRGB-encoded floating-point data**, explicitly loaded as sRGB; Blender decodes it to scene-linear lighting. Its decoded range reaches 6.09, so it retains highlights above 1. Do not relabel that file as linear without converting its pixels. An external linear HDRI should use its declared linear input space. A float file extension alone does not establish its encoding.

The exact reference rig below uses a 12 m presentation span. Coordinates are scene meters, aimed at the stated targets. They are lighting coordinates, not dimensions of the actual condo.

| Light | Position XYZ | Target XYZ | Power | Shape/size |
|---|---|---|---|---|
| Top softbox | 0, 0, 10 | 0, 0, 0 | 900 W | Disk, 7 m |
| Key | −4.5, −6, 8 | 0, 0, 1 | 650 W | Disk, 5 m |
| Fill | 6, 1, 5.5 | 0, 0, 1 | 300 W | Disk, 5 m |
| Rim strip | 1, 6, 7.5 | 0, 0, 1.5 | 600 W | Rectangle, 6 × 1.5 m |

Scale positions and light dimensions by `s = presentation_span / 12`; scale powers by `s²`. The top light provides broad downward shadow cues. The key gives pipe curvature a readable highlight. The fill opens the shaded sides; the rear strip separates the vertical risers. All lights are neutral white. Avoid a colored HDRI that contaminates the blue/red/orange system coding.

Start look development at 32–64 samples; use 128–256 for production, adaptive threshold 0.01, and inspect the narrow pipes at delivery size. The saved configuration is a practical look-development setup, not an assertion that a low-sample review is a final 4K render. The actual review's resolution, samples and temporal sampling are recorded separately in **output/sequence-profile.json**.

### EEVEE Next / Blender 5 compatibility

`blender_compat.py` supplies an interactive EEVEE preview setup: 128 render samples, screen-traced ray tracing, Ambient Occlusion fast GI, four shadow rays and jittered shadows. In Blender 4.2–4.5 the engine identifier is `BLENDER_EEVEE_NEXT`; Blender 5.0 uses **`BLENDER_EEVEE`**. The utility selects the identifier by version.

Do not use old `use_gtao`, `use_ssr`, `use_bloom` or legacy contact-shadow examples. They do not describe the current API. EEVEE does not reproduce Cycles' true shadow-catcher pass. The utility uses a matte receiving floor for its preview; use Cycles for the supplied transparent shadow-catcher pipeline. Cycles CPU renders were tested here; an EEVEE image render was not validated in this headless environment.

## 3. Preserve an exact warm background without flattening the lighting

Use **AgX**, **AgX – Medium High Contrast**, exposure **0**, gamma **1**, display **sRGB**, with Film Transparent enabled. Keep pipe colors as sRGB swatches converted to scene-linear values before assigning node colors. Assigning `247/255` directly as a linear color is not equivalent to sRGB `#F7F6F2`.

An illuminated floor or World color cannot remain an exact display hex under arbitrary lighting and AgX. The reliable order is:

1. Render the 3D beauty to transparent RGBA PNG, with AgX already applied by Blender's image save.
2. Build the display plate in **#F7F6F2**, RGB **247, 246, 242**.
3. Add the quiet projected drawing and illustrative context fills.
4. Alpha-composite the 3D render over that plate in display-linear sRGB.
5. Draw captions, legends and screen-space labels after the grade.

`studio_composite.py` implements this order and checks a clear PNG corner against the exact RGB triplet. Empty plate areas are exact; shadows, edges and translucent overlays intentionally change the pixels they cover. H.264/YUV encoding and playback can alter individual RGB values. Use the PNG sequence or a suitable lossless master when byte-exact background pixels are required. An H.264 review is not a pixel-exact color reference.

AgX handles the lit geometry; the editorial paper never passes through AgX a second time. Filmic remains a possible look for older projects, but it also changes display colors. Changing view transforms alone cannot solve the exact-paper requirement.

## 4. Give the pipes a restrained studio finish

The default is a **coated polymer presentation finish**, not a specification of the replacement material. The requested values remain explicit:

| Principled parameter | Value |
|---|---|
| Roughness | 0.25, varied gently from 0.225 to 0.275 |
| Coat Weight | 0.5 |
| Coat Roughness | 0.18 |
| Coat IOR | 1.35 |
| Metallic | 0 |
| IOR | 1.46 |
| Specular IOR Level | 0.35 |

The node chains in `pipe_material()` are:

```text
Geometry Position → Noise Texture, Scale 180, Detail 2
                    ├→ Map Range [0.225, 0.275] → Principled Roughness
                    └→ Bump, Strength 0.06, Distance 0.00012 m → Normal

Fresnel, IOR 1.46 → Multiply 0.10 → Mix(system color, lightly lifted system color)
                                              → Principled Base Color
Principled BSDF → Material Output
```

The Principled shader already includes physical Fresnel. The explicit Fresnel branch adds only a small **colored edge tint** for art direction. The rear area light supplies the actual rim highlight. Avoid a strong white emission rim: it desaturates system colors and makes pipes look self-lit again. Do not mix roughness noise over a wide range or use coarse bump that resembles corrugated hose.

Cold is blue **#147ECC**, hot is red **#D94736**, return is orange **#E7772C**. Proposed access uses distinct amber **#ECAF39**, a dashed edge pattern and explicit labels. Small accent text uses darker ochre **#98621D** for contrast against the paper. These colors follow the latest requested palette; the earlier purple return remains in the original files.

For an anodized-metal illustration, start with Metallic 0.7–1.0 and retune the lighting; do not describe that appearance as an installed product. Metallic 0 is more appropriate for a PEX-like finish and keeps the system colors easier to read.

### Round the corners without inventing fittings

The supplied routes are beveled POLY curves. Increasing `bevel_resolution` smooths their round cross-section; it does not create a manufactured elbow. `joints()` adds smooth sphere covers, radius **1.015 × pipe radius**, only where a route changes direction. Each cover appears when the animated pipe growth reaches that corner. The source curve centerline and radius stay unchanged.

These are presentation fillets, labeled accordingly. Use actual elbow geometry only after the material/system and fitting radius are documented. On existing service-symbol meshes the script adds a small **4 mm, three-segment Bevel modifier** to catch light. A Bevel modifier on a straight cylinder does not, by itself, round a whole pipe routing corner.

## 5. Make the blueprint crisp but subordinate

The supplied P4.01 page contains **13,409 vector drawing paths**. The original 3192 × 2940 crop was rasterized at 200 DPI. `prepare_blueprint.py` re-renders the identical normalized crop at **400 DPI**, producing **6384 × 5880** pixels. It preserves source annotations and records the source PDF hash. This is real source re-rasterization rather than an AI sharpening operation.

In Blender, the source texture is **sRGB**, **Cubic**, extension **Clip**. Use a luminance ColorRamp with black point **0.28** and paper white point **0.98**, then multiply its ink alpha by **0.25**. The result is crisp-edged **25% warm gray**, not a sheet of competing black linework. Colored annotations retain their source color under the same subdued opacity. The source remains available at full contrast in the original drawing package.

```text
Image Texture, Cubic → RGB to BW → reversed ColorRamp → × 0.25 → Mix Shader factor
                                                               ↑
Transparent BSDF ───────────────────────────────────────────────┤
Warm ink Emission / retained colored annotations ────────────────┘
```

Do not hard-threshold the whole drawing. Architectural walls and secondary notes can be lighter than the plumbing; an aggressive ramp can erase them. Cubic interpolation also cannot recover detail missing from a low-resolution source. At the service close-up, use a crisp new label rather than expecting the original raster note to function as the film's headline.

For the review pipeline, a corresponding ink mask is composited deterministically using the camera-projected plane corners. This avoids stochastic transparency noise and preserves linework independently of denoising. The plane and its Cubic/ColorRamp shader remain in the editable Blender file for a fully native, sufficiently sampled render. The preview renderer hides that plane only for its separate compositing path.

## 6. Add shadows and local contact without dirtying the drawing

The Cycles receiver sits at presentation Z=0, just below the source drawing's Z=0.002 plane. It is a true `is_shadow_catcher` object. The shared schematic uses its own lower receiver because its service stubs extend below the header datum.

Enable Ambient Occlusion, Shadow and Shadow Catcher passes for production EXR work. **Enabling a pass does not automatically apply AO to Combined.** The supplied receiver also has an AO shader contribution: distance **0.12 m**, strength **0.16**, two AO samples for look development. Increase AO samples for a final render if necessary. Apply this contact contribution to the receiving surface, not globally to the blueprint's text and callouts.

The main depth cue is the top area's real soft shadow. AO is short range: a pipe depicted more than two meters above the plan will not create a local contact AO patch under itself. Its light-cast shadow and its relationship to the ghost walls communicate the height. Do not increase AO distance to several meters merely to fake contact.

The `--preview` path disables unused auxiliary render passes and uses denoised CG while compositing the blueprint and low-opacity context fills separately. It retains the receiver's short-range AO shader. A small alpha-only smoothing operation on neutral, low-coverage shadow regions removes residual low-sample catcher grain; opaque/saturated geometry and its antialiased edges are protected. The blueprint and labels are added separately and do not pass through that smoothing. The full native path keeps the material surfaces and production pass flags. If writing multilayer EXRs, preserve those passes in scene-linear space and apply the appropriate OCIO display transform before the exact-color editorial stage.

## 7. Add low ghost walls, not a guessed building model

Use only the primary wall relationships needed to explain the wet-wall and kitchen routes. The configuration lists normalized trace segments from the supplied P4.01 crop. They are manual interpretations; they are not verified structural classifications or a complete room/door model.

The display height is **42 inches / 3.5 feet / 1.0668 m**. It is an illustrative cutaway height. The material mixes **90% Transparent BSDF** and **10% frosted Principled surface**, Roughness 0.42, with thin gray-blue top edges. Shadow visibility is off for these presentation walls so they do not cover source notes with invented room shadows.

Each wall is a single upright quad. This avoids stacking two 10%-opacity glass interfaces and unexpectedly making a wall nearly 19% opaque. True refractive glass is usually less legible here: it distorts source text and costs more to render. The objective is a frosted architectural hint, not glass product simulation. The context appears during steps 02–07, from 00:08 to 01:25.

An equivalent Geometry Nodes workflow is: trace curves → Resample if needed → extrude a vertical ribbon to the display height → Set Material → optional top-edge Curve to Mesh. Keep width/height as exposed presentation inputs. Trace source walls manually or import verified vector wall paths; do not extrude every dark CAD stroke, because many strokes are pipework, dimensions or symbols.

## 8. Upgrade access zones and action cues

Each proposed access area becomes a **3D amber envelope** with 2.5%-opacity faces and dashed edge curves. The display height is **0.38 m** and is explicitly not an opening dimension or wall depth. Dash pitch is 0.11 m with a 58% visible segment. Wire radius is 0.007 m. The same source rectangle controls the footprint and its existing stage timing.

The edge material uses a modest 0.8 emission contribution within a Principled surface. `blender_compat.restrained_glow(scene)` optionally adds a small compositor halo. Blender 5's Glare node uses socket values **'Fog Glow'**, **'High'**, Threshold 1.5, Strength 0.04; the utility handles Blender 4's older property API. A wire that stays below the threshold will not produce a halo: lower the threshold or raise emission on an isolated wire pass if that effect is desired. Keep it restrained so the amber envelope never swallows the pipe colors.

During 00:58–01:04, three illustrative valve-ring/handle symbols rotate toward a closed position at the assumed service assembly. The accompanying label says **“Proposed isolation · verify on site.”** These icons explain a required operation; they do not prove a real valve exists at that point or that a unit can be independently isolated. Do not glow an entire building riser green or claim an established affected-service boundary without field evidence.

The test stage remains a required hold: capped boundaries, a gauge symbol and **Required test + inspection / Before service transfer**. There are no invented readings, pressure values or passed-test graphics. Restoration replaces access boundaries after transfer while retaining service access and documentation cues.

## 9. Make the camera guide the eye

The revised opening uses the existing exterior source model, with a gentle southeast approach. The exterior render lasts 4.5 s; the shared-system render begins at global 3.5 s. A **one-second dissolve from 3.5–4.5 s** produces an eight-second opening, with the unit sequence still beginning at 00:08. The film remains 90 seconds.

The unit camera keeps a continuous **0.38°/s azimuth drift**, about four degrees per ten-second chapter. Target and orthographic scale change with smoothstep interpolation. The script keys the complete 24 fps camera, not only the review's sampled frames.

| Time | Camera purpose |
|---|---|
| 00:08–00:18 | Establish the pilot and service location |
| 00:18–00:26 | Move toward the kitchen low-wall connection |
| 00:26–00:47 | Reopen the wider installation view as distribution and branches appear |
| 00:47–01:01 | Glide into the service/test area and hold readable context |
| 01:01–01:08 | Pull back gradually for the restored loop |
| 01:08–01:25 | Continue the gentle drift through commissioning and restoration |

Keep an orthographic camera, or a long perspective lens if changing the film's visual language. Avoid short focal lengths, camera roll, simulated handheld movement, abrupt large scale changes and shallow focus. Review the complete route against all four viewport edges at every camera key; a detail view may intentionally crop distant fixtures, while the wide view must retain the important distribution connections.

## 10. Replace tilted labels with projected screen-space pins

`render_studio.py` projects anchors through `world_to_camera_view()` at every native sample. It writes a small JSON sidecar beside each PNG. `studio_composite.py` places horizontal badges and thin leaders after the display transform. They stay sharp without rotating with the floorplan.

The shared diagram uses its original source-labeled riser groups, not invented G1/G2 identifiers. Unit pins identify the planned service assembly, kitchen low-wall connection, return loop and restoration/service-access area at the relevant stage. Existing tilted source-model text is hidden in the studio variant.

Keep badges inside the model panel and away from the right-hand narrative. A handful of relevant labels beats labeling every pipe. The 1080p badge type is approximately 19 px; test the complete frame at laptop and phone size. Reuse the existing readable inspection/transfer panel rather than shrinking CAD text to do that job.

## 11. Animate assembly, flow and commissioning as different actions

An installation highlight is allowed during 00:29–00:45, but it follows only the **leading edge of pipe growth**, with an explicit **Assembly highlight · not water flow** caption. It does not show water moving in an isolated, untested replacement network.

Directional flow starts at **01:07**, after the depicted transfer and final connection checks. It remains a schematic cue, not a hydraulic simulation or measured performance claim. Hot and cold follow their source route order; the orange unit return runs from the far hot-water end toward the service connection. The shared return header reverses its presentation travel direction.

`pulse_overlay()` builds a slim overlay mesh with a float point attribute **studio_s**, equal to cumulative route distance. Its shader computes:

```text
q = fract(direction × studio_s / 1.8 − time × 0.35 / 1.8)
q → soft ColorRamp band, width 0.12 of a cycle
band × post-transfer gate × installed-length mask → Transparent / Emission mix
```

The speed is 0.35 presentation meters/s; it is not actual water velocity. The attribute follows corners, so a pulse does not reverse or stretch arbitrarily when a route turns. Do not use global X coordinates as a substitute for distance along a branched pipe.

The same idea in Geometry Nodes is **Spline Parameter Length → Store Named Attribute before trimming → Trim Curve using the installation reveal → Curve to Mesh**. Store length before trimming so the pulse phase does not restart as the visible pipe grows. The supplied implementation uses explicit overlay mesh attributes, leaving the original animated curve untouched.

## 12. Tighten the pace without shortening the agreed runtime

Retain the narration and chapter timing. Use the pauses to let viewers see pipe growth, valve closing, the inspection hold, final-connection checks, moving return pulses and restoration boundaries. The soundtrack adds quiet original clicks at meaningful graphic changes and low-level swells under focus glides. The score and cues sit beneath the narration; they are not recordings of field work.

Do not animate pressure numbers simply to fill a pause. Do not make the testing hold feel like a completed inspection. A brief purposeful hold on the required release condition is useful for both owners and the construction team.

## 13. Run the supplied pipeline

From the repository root, replacing `PY_BPY` and `PY_COMPOSE` with the appropriate Python executables:

```bash
# Source preparation needs PyMuPDF:
uv run python projects/highland/products/installation/studio-upgrade/prepare_blueprint.py

# Build a separate editable studio scene:
PY_BPY projects/highland/products/installation/studio-upgrade/studio_upgrade.py

# Six representative frames, without changing the source animation:
PY_BPY projects/highland/products/installation/studio-upgrade/render_studio.py --width 1280 --samples 32 --preview
PY_COMPOSE projects/highland/products/installation/studio-upgrade/studio_composite.py

# Resumable 90-second look-development render and assembly:
PY_BPY projects/highland/products/installation/studio-upgrade/render_studio.py --sequence --width 1280 --samples 48 --native-fps 6 --preview
PY_COMPOSE projects/highland/products/installation/studio-upgrade/studio_composite.py --sequence --native-fps 6
```

`PY_BPY` needs bpy 5.0.1; `PY_COMPOSE` needs NumPy, Pillow and OpenCV. From the repository root, `uv sync --group vision --group pdf` installs the complete locked Python 3.11 dependencies, including PyMuPDF for source preparation and ReportLab for the guide/storyboard PDFs; both `PY_BPY` and `PY_COMPOSE` can then be `uv run --no-sync python`. FFmpeg/FFprobe and DejaVu Sans fonts are system dependencies. `--watch` lets the compositor process completed shots while the renderer continues. Native FPS must divide 24. Rendering uses a profile signature to reject an incompatible old cache; move the generated `output/raw/` directory before changing settings.

After changing post-processing settings, remove the generated **output/clips/** folder to rebuild those intermediates. Complete clips are otherwise reused after their exact frame counts are verified; new encodes use a temporary file until validation succeeds.

For a final native 4K/24 fps render on a configured GPU workstation:

```bash
PY_BPY render_studio.py --sequence --device GPU --width 3840 --samples 256 --native-fps 24
PY_COMPOSE studio_composite.py --sequence --native-fps 24 --master-width 3840
```

Use full paths or run from this script folder. Configure and enable the intended Cycles GPU devices in Blender preferences first. At native 24 fps the compositor does not create intermediate optical-flow frames. When native FPS is lower, it interpolates only the model imagery; editorial typography remains at the delivery resolution. Disclose that distinction when sharing a review. The saved native rig supports a full-resolution re-render; a low-resolution review cannot be relabeled as a native 4K master.

## 14. Review before calling it finished

- Start on the actual exterior study; transition to shared distribution and then the distinct Unit B / 106 pilot.
- Verify source-file hashes and unchanged original route geometry.
- Check that orange return and amber dashed access remain distinguishable.
- Inspect the kitchen and service close-ups, ghost-wall traces and all wide camera framing.
- Confirm that source linework is quiet and labels are horizontal, readable and collision-free.
- Verify that assembly highlighting stops at the installed extent and that commissioned flow is absent before 01:07.
- Keep the test/inspection gate as future required work and the valve indicators explicitly conceptual.
- Check the PNG plate color, exported movie duration/frame count, audio/subtitle tracks and the conceptual-status footer.
- Watch the exterior dissolve, camera focus changes and moving pulses in real time; compare decoded movie frames to the source PNGs.

The visual upgrade makes the proposed installation easier to understand. It does not resolve the source model's field, design or provenance limitations.
