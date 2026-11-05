# Highland exterior reconciliation — source recovery and native rebuild

This product restores the work stranded on the old roof/drawing branch to the
current Highland layout:

1. **Source and controls (CPU).** Byte-identical recovered inputs, sheet locators
   and protected controls, verified by `check.py`.
2. **Native rebuild (bpy).** The revision 06 builder in [builder/](builder/) rebuilds
   the scene from those inputs. [verify.py](builder/verify.py) shows that it
   reproduces the historical delivery records.

It does not replace the earlier [exterior study](../exterior/README.md). It
publishes no new film, render set or editable model as a deliverable; packaging is
the next slice.

The current recovered geometry input is
[snapshots/reconciled.spec.json](snapshots/reconciled.spec.json): 192 openings,
an independent P1 enclosure, the 14-vertex R5 enclosure, five walking terraces,
one planter, five guard paths and three band paths. The south MO/MJ pair retains
its contiguous shared interface. Geometry units are inches; the future native
builder must convert to meters.

[recovery.json](recovery.json) records the exact original commit, path, Git blob
ID, byte count and SHA-256 of each of 12 historical JSON files. They were imported
byte for byte from archived Git history. The revision 04 spec supports the north
deferral check; the earlier roof spec supplies protected floor/grid/tower controls.
The 97 north, 815 revision 05 and 99 R5 mesh hashes are **historical controls**.
The native rebuild below reads them back from the rebuilt scene.

## Check the recovery

From the repository root:

```bash
uv run python projects/highland/products/exterior-reconciliation/check.py   # CPU only: no Blender, no PDFs
uv run bm run highland/exterior-reconciliation check-sources
uv run bm run highland/exterior-reconciliation check   # CPU check plus the native rebuild (bpy)
```

`check.py` and `check-sources` write nothing. `check.py` needs no Blender or PDFs. It verifies exact
snapshot integrity, protected controls and deferred north opening coordinates,
per-sheet dimension calibration, source-registry equality, the MO/MJ interface,
P1/non-north-R5 jamb bounds, and planar terrace/room and guard relationships. It
also compares a computed summary with the checked-in
[source check report](../../deliverables/exterior-reconciliation/source-check.json).
Missing PDFs are reported explicitly without failing this CPU contract check;
any present PDF with the wrong size/hash fails. `check-sources` additionally
requires all three PDFs to be present with matching hashes.

## Source documents and limits

[The source manifest](../../sources/manifest.json) preserves the three PDF hashes,
original names, 19 sheet locators and April 2, 2007 printed dates. Copy matching
PDFs to `projects/highland/sources/` using their manifest filenames. The files
stay ignored. No source PDF is added by this recovery. The spec's older top-level
`source_pdf_sha256` identifies its inherited PDF; the three later reconciliation
PDFs are identified under `drawing_reconciliation.sources`. Annotation/ASI/RFI
response dates remain unestablished.

North stair/MU alignment and R1 entries remain deferred. Revision 04 north
coordinates and its historical 42.443-overview-pixel diagnostic remain; six upper
north openings per floor do not establish dimensional alignment. The R5 tie-in
residuals and plan/elevation disagreements remain unresolved. Later R5/terrace
records supersede older R5 limitations embedded in historical shell records;
the original JSON is retained rather than silently rewriting that history.

Source XY remains provisional, with each sheet's recorded 3-inch raster-pick
uncertainty; that is not a global building accuracy tolerance. Complete openings
and guards remain assumed. Window schedules, A4/A5 profiles, terrace compliance,
waterproofing and installed conditions are unverified. No north audit is reopened.

## Native rebuild

```bash
uv run bm run highland/exterior-reconciliation build      # pulls the base scene, writes build/highland/exterior-reconciliation/
uv run bm run highland/exterior-reconciliation validate   # historical mesh readback: openings, slabs, coping, terraces, GLB, 432 camera frames
uv run bm run highland/exterior-reconciliation verify     # compare with the historical delivery records
uv run python projects/highland/products/exterior-reconciliation/builder/render.py --review   # optional: 12 CPU review views
```

`check` runs the CPU source check, then all three steps, and requires no diff in
the tracked [native check report](../../deliverables/exterior-reconciliation/native-check.json).
CI runs it in `build-models`.

**How it rebuilds.** The historical builder does not generate the building from
scratch. It opens the revision 03 roof-and-terrace scene and rebuilds only the
walls, openings, slabs, coping and terraces that the change ledger and spec
name. It then asserts that every other mesh is unchanged. The port keeps that
design:

- **Base scene:** a 24 MB release asset,
  [release-assets.json](builder/release-assets.json). It is byte-identical to the
  archived `deliverables/highland-roof/Highland-roof-and-terrace-revised.blend`,
  and `bm assets pull` verifies its sha256.
- **Inputs:** [builder/inputs.json](builder/inputs.json) records the archived blob
  of every builder file. These include the change ledger, the opening audit, and
  the old `highland-exterior/build.py`. Only that file's six pure mesh functions
  are parsed and run, as before; the live [exterior](../exterior/README.md)
  builder has since diverged and is not used.
- **Code:** `shell_mesh.py`, `terrace_mesh.py` and `presentation_sync.py` are
  verbatim. `build.py`, `validate.py`, `render.py` and `check_terraces.py`
  changed only where they read or write paths, which now come from
  [paths.py](builder/paths.py). `check_terraces.py` also carries verbatim copies
  of the two pure functions it imported from the prepare-stage `terraces.py`.
- **Not ported:** the prepare stage (`prepare.py`, `shell.py`, `r5.py`,
  `terraces.py`). It generated the reconciled spec from the PDFs, and that spec
  is now the recovered snapshot. The packaging, report and film scripts are left
  for the packaging slice.

**What `verify` requires:**

- All 960 rebuilt architecture mesh hashes, and the 969 base hashes, equal the
  historical `geometry-validation.json`. That covers 97/97 north, 815/815
  revision 05 and 99/99 R5 controls.
- 31 fields of the historical `delivery-validation.json` are reproduced. The
  saved `.blend`/`.glb` file hashes are not compared, because saved files embed
  write metadata. The PDF hashes are compared only when the PDFs are present.
- Verbatim files are unchanged.

Changing one opening's width by 2 in fails both the historical validator and
`verify`, which names that opening's frame, glazing and sill meshes and its wall.

**Visual review (2026-11-05, local CPU):**

- I ran `render.py --review` on the rebuild and compared the 12 views with the
  historical `geometry-review/` images.
- None are file-identical. At most 0.09% of pixels differ by more than 8 levels,
  and the three plan views by at most 1 level.
- I inspected six pairs side by side: south, iso, r5-southwest, p1-south,
  terrace-plan and r5-return. None shows a change in geometry. The largest
  difference is the shading of one thin vertical frame member in r5-return.
- That is likely Cycles resolving coincident faces in a different order (not
  confirmed). The geometry there is identical: all mesh hashes match.

The 960 identical hashes show that the port reproduces the delivered revision 06
geometry. They do not show that the geometry is accurate; the source limits
above still apply.

Snapshots are intentionally immutable recovery inputs. Proposed future geometry
changes should use a separately named working spec with an explicit migration
record; do not update archive fingerprints to make a changed snapshot pass.

Illustrative, not a contract document.
