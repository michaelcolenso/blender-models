# Highland source recovery record

[Source check report](source-check.json) summarizes the CPU checks of the
[recovered inputs and controls](../../products/exterior-reconciliation/README.md).
It is reproducible with `uv run bm run highland/exterior-reconciliation check`
without drawing PDFs or Blender. The command reports local PDF availability
separately, so the tracked report does not depend on one machine's source files.

This is a source consistency report. Native mesh readback, source PDF inspection,
render review, dimensional accuracy and installed conditions are not verified by
this delivery. Historical mesh hashes are preservation targets for the later
builder port. No new `.blend`, GLB, film or render is delivered here.

Illustrative, not a contract document.
