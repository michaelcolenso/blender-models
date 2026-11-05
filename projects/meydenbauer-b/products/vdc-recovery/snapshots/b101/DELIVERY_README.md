# B-101 v4 executed Blender handoff

Built with Blender 4.3.2 on Linux using `bash run_blender.sh --render-keyframes`.
All three build passes, strict validation, save and fresh-process reopen completed successfully. Original supplied Python sources are unchanged. No runtime model fixes were required.

**Coordination acceptance: REVISION REQUIRED.** Authored trench cutters overlap the marked prior-ABS no-demolition envelope by approximately 2.4 square feet, and upper-floor context obscures the authored camera. These are documented modeling/review issues; geometry was not redesigned. FIELD_VERIFY assumptions remain intact.

- [Editable Blender model](output/Meydenbauer_B101_Demolition_v4.blend)
- [Acceptance and visual review](output/acceptance_notes.md)
- [Checklist results](output/checklist_review.md)
- [Execution summary](output/execution_summary.json)
- [Build validation](output/build_validation_report.json)
- [Fresh-process reopen verification](output/saved_blend_verification.json)
- [Extended evaluated-scene checks](output/extended_runtime_qa.json)
- [Execution logs](logs/)
- [Eight requested checkpoint renders](renders/)
- [Twelve additional diagnostic renders](renders/detail/)

This directory preserves the executed package, including source scripts, calibration data, QA overlays, reports, logs and images. Earlier handoff documents describe the pre-execution state; the reports above describe the completed run. Absolute paths in reports/logs refer to the original execution workspace. Scripts locate their package root relative to their own files and can be rerun here.

`DELIVERY_MANIFEST.sha256` covers the delivered package before this repository index was added. `MANIFEST.sha256` is the original input manifest, not a checksum list for generated outputs. The intermediate `.blend1`, Python bytecode and duplicate ZIP are omitted.
