# 200 W Highland — installation model

Built 17 October 2026 from the supplied 19-sheet drawing set dated 29 October 2007. The previous owner drawing atlas and original plans are unchanged.

## Open first

- **Highland-installation-storyboard.pdf** — ten-page review: shared-system schematic, Unit B / 106 plan overlay, six installation stages, source exceptions and provenance views.
- **Highland-installation-sequence.mp4** — 24-second captioned method sequence, four seconds per stage. This is a storyboard video; it does not simulate labor duration.
- **Highland-installation-unit-B.blend** — editable proposed pilot; six visibility stages at frames 1, 25, 49, 73, 97 and 121. Open the timeline at these frames. All drawing textures are packed. The file opens at completed installation, frame 121.
- **Highland-installation-shared.blend** — separate proposed distribution schematic with the five numbered review groups and auxiliary-service stubs.
- Matching **.glb** files — portable static proposed models with provenance metadata. Visibility sequence remains in Blender and video; GLBs show the final stage.
- **installation-elements.csv** — element register with stable IDs, sources, installation stages and assumptions; no purchase quantities or measured pipe lengths.

## Modeled installation

1. Verify service boundaries and protect finishes.
2. Make controlled access openings; prepare support and penetration strategy.
3. Install new cold, hot and circulation-return distribution as an isolated network.
4. Complete branches, cap boundaries, test and inspect the new network.
5. Cut over within verified isolation boundaries; inspect final connections, flush and commission.
6. Restore rated assemblies and finishes after acceptance; retain service access and hand over as-builts.

Source-linked details include the Unit B kitchen low-wall supply and service/meter/control coordination, the three-system distribution, irrigation through Unit 101, Unit 302's alternate wall location, the distinct 106/107 tie-in, and the garage/trash plus fitness/janitor services.

## Provenance and geometry limits

**Every new physical element is assumed.** P4.01 supplies route relationships and fixture-group context, not field dimensions. The source plan's printed scale has not been calibrated against dimension strings, so the 480 x 442.1 inch display mapping is arbitrary. Do not measure the model, compute quantities from it, or adopt drawn diameters as pipe sizes. Pipes and symbols are enlarged for readability.

The assumed elements are listed individually in installation-elements.csv and highland-installation-proposed.yaml: all supply/return paths, fixture-group endpoints, access rectangles A01–A05, protection footprint P01, service assembly SVC01, test symbol TEST01, support symbols, and restoration boundaries. The shared-model positions, riser heights, valve symbols, return loops and auxiliary stubs are also assumed. Review colors: orange assumed, yellow provisional, green confirmed; drawing pixels are confirmed source content but their physical mapping is assumed.

No individual fixture count, existing CPVC alignment, usable isolation boundary, affected-unit list, actual pipe support spacing, firestop product/detail, final material, hydraulic sizing, labor duration or outage duration is established. Fixture-group endpoints are diagram symbols; individual appliance/fixture connections remain to be detailed. The proposed return termination and balancing arrangement require field tracing and design confirmation. Test caps/gauge and service symbols explain the process, not a specified test rig or assembly order. The protection footprint is illustrative and does not verify actual entry/egress.

The existing drawing reference has a separate spec, highland-installation-existing-reference.yaml. It records unchanged source pixels and the user's report of failing CPVC; it does not assert an existing-condition pipe model. The proposed installation is a separate spec and separate Blender files. Original boiler equipment is not replaced by this model; system tie-ins remain to be verified.

The drawing project title reads **200 West Highland Drive**; its location block reads **202 W Highland Drive, Seattle, WA 98119**. Confirm property address and governing revision. Drawing issue and annotation dates are not interchangeable; supplied review annotations may be later.

## Design release information still needed

Confirm measured routes/elevations, current configuration, water pressure under demand, fixture demand, material suitability, hot-water and return conditions, rated assemblies, actual valve operation, inspection and testing criteria, outage arrangements and exception routes. A qualified plumbing designer/contractor must convert this method model into the installation design under the applicable Seattle requirements.

## Rebuild

The model uses a dedicated spec-driven pipe builder because the existing generic house/detail builder does not implement this multistory plumbing-method model. P4.01 contains vector linework and was rasterized at 200 dpi for the original source review; the studio revision uses a 400-dpi crop. No automatic dimensional extraction or calibrated physical mapping is claimed.

```bash
python prepare_spec.py
/workspace/.venvs/blender-models/bin/python build_installation.py
/workspace/.venvs/blender-models/bin/python verify_blends.py
python validate_installation.py
python package_installation.py
```

Keep highland-installation-proposed.yaml as the model source of truth when revising geometry. prepare_spec.py recreates the initial spec; do not run it over later field edits. build_installation.py reads the YAML. package_installation.py and validation use the matching installation-data.json generated from that same YAML when packaging.

## Validation

See validation.json for automated results and VISUAL-REVIEW.md for the visual inspection record. These checks establish source identity, proposed network continuity and delivery integrity; they do not establish field dimensions, hydraulic performance or code approval. The previous source atlas files remain unchanged.
