# Blender Project — Instructions

Purpose: build dimensionally accurate, realistic 3D models of Michael's restoration and defect-repair projects (occupied multifamily) from construction drawings, details, specs, and site photos, using Blender driven by Python. Accuracy first, realism second. A model is finished only when every dimension traces to a source or is labeled as assumed, the automated checks pass, and the renders have been looked at.

## Pipeline (always in this order)

1. **Intake.** Inventory every source: sheet number, detail number, revision/date, scale, photo IDs. Read drawings at full resolution (rasterize PDFs with `pdftoppm -r 200+`; crop into details). Note scale bars and "NTS" details.
2. **Takeoff.** Extract every dimension, member size, spacing, elevation, and count into the model spec. Use actual lumber sizes (2x10 = 1½ × 9¼), not nominal. Never scale an NTS detail. Never infer a dimension from a partial drawing and call it documented.
3. **Model spec** (`specs/<project>-<area>.yaml`). The spec is the single source of truth; geometry is never hand-edited in Blender without the spec changing too. Every element carries:
   - `status: confirmed` — dimension shown on a document (`source` required)
   - `status: provisional` — derived: scaled from a drawing with a scale bar, or measured from a photo against a known reference (`source` required; note the reference and expected tolerance)
   - `status: assumed` — not in any document (`basis` required, e.g. "code-minimum", "typical", "massing only")
   - Document-driven `checks`: counts, overall extents, clear gaps, spacing, elevations — each with its `source`.
4. **Build.** `python tools/build.py specs/<name>.yaml [--realistic]` (bpy, headless). One collection per trade; trades stay separate. Inches in the spec; Blender stores meters, displays imperial.
5. **Verify.** The builder fails (exit 1) on: missing source/basis, count or extent mismatch, gap mismatch, or a blank render. Then look at the review renders myself — plan, front, side, iso — colored by provenance (green confirmed, yellow provisional, orange assumed). Where a drawing elevation exists, compare the ortho render against it at the same scale. "Checks passed" and "looked right" are both required; report which were done.
6. **Realism pass** (only after geometry is verified). PBR materials by real product where known; realistic lighting via Cycles. Realism never changes geometry.
7. **Deliver.** `.blend` (editable), `.glb` (phone/web viewing, carries element metadata), review renders, `report.md`. List every assumed element in the handoff.

## Accuracy rules

- Never present an assumed or provisional element as documented. Review renders always show provenance colors; realistic renders shared outside the team must carry a note if any assumed elements are visible.
- Photos: state the reference object used for scale (brick course, CMU, door, siding exposure, known member size), the camera angle limits, and the resulting tolerance. Photo-only geometry is at best `provisional`.
- Conflicts between sources (drawing vs. photo vs. spec): model per the governing document, flag the conflict in the report — don't average or silently pick.
- Existing-conditions models (defect repair) and proposed-repair models are separate scenes or separate specs. Don't merge them.
- Models are illustrative/coordination tools, not contract documents. Any render used in a scope, PCO, or resident notice gets that label.

## Occupied-building use cases

Resident notices (what's happening at their unit), access and sequencing diagrams, protection/staging/egress layouts, and PCO backup showing concealed conditions. For these, include the relevant occupied-building elements (egress paths, protection, staging area, work zone) as their own collection, marked by source like everything else.

## Environment facts (verified 2026-09-27)

- `pip install bpy==5.0.1` works on Python 3.11 in Claude's Linux workspace; build + checks for a small spec run in seconds.
- Headless has no GPU: **Workbench and EEVEE render blank frames** — use Cycles on CPU only. Cameras need explicit rotation (track-to constraints are not evaluated before headless renders).
- Exports confirmed working: .blend, .glb, .obj, .stl, .fbx, .usdz. SVG import add-on present. IFC (Bonsai) not installed — unverified.
- Cycles realistic render: ~2 min for 4 review views + 1 realistic view at 1600×1200 on 2 CPU cores. EEVEE took 45 s for a trivial scene and still returned blank.

## CI

GitHub Actions (`.github/workflows/build-models.yml`) rebuilds changed specs on every PR and push to main, fails the PR if any check fails, writes each report to the job summary, and uploads `build/` as an artifact. Claude does the takeoff and spec edits; CI makes the geometry reproducible and blocks unsourced or inconsistent changes.

## Working style

Ask once, batched, only for what can't be read from the documents (e.g. a missing detail, which revision governs). Otherwise take the next step and mark assumptions. Don't claim a model is accurate beyond what its sources support.
