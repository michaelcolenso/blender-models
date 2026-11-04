# Highland exterior reconciliation — source recovery

This product restores the source records stranded on the old roof/drawing branch
to the current Highland layout. It is the source/control recovery slice, before
the native builder port. It does not replace the earlier
[exterior study](../exterior/README.md), regenerate Blender geometry, or publish
the old branch's films and editable models as new deliverables.

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
They have not been read back from a rebuilt Blender scene in this recovery.

## Check the recovery

From the repository root:

```bash
uv run bm run highland/exterior-reconciliation check
uv run bm run highland/exterior-reconciliation check-sources
```

Both commands are read-only. The first needs no Blender or PDFs. It verifies exact
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

## Next native-build slice

The historical builder patched
`deliverables/highland-roof/Highland-roof-and-terrace-revised.blend`, read the old
`projects/highland-exterior/build.py` mesh functions and used historical ledgers.
Those paths in the snapshots are archival references, not executable inputs to
this check. Before a native build can be offered, port these dependencies into
the current product layout, restore and verify required assets, preserve the
mesh controls, build, read back the meshes and inspect the source/render pairs.
Source consistency checks alone do not establish that the Blender port works.

Snapshots are intentionally immutable recovery inputs. Proposed future geometry
changes should use a separately named working spec with an explicit migration
record; do not update archive fingerprints to make a changed snapshot pass.

Illustrative, not a contract document.
