# Checklist review results

Read with acceptance_notes.md, the JSON reports, and renders/detail. PASS refers to modeled coordination behavior, not field verification. Build/reopen process results are in their respective JSON reports.

| Checklist | Result | Evidence / limitation |
|---|---|---|
| A — Preflight | PASS | preflight_report.json |
| A — Strict build and all three passes | See build_validation_report.json | Original launcher uses --fail-on-warning |
| A — Saved blend and fresh reopen | See saved_blend_verification.json | Original launcher reopens in a new process |
| A — Controller properties and drivers | PASS | extended_runtime_qa.json: evaluated at 13 checkpoints, no invalid drivers or error flags |
| B — Trench Boolean present and evaluated | PASS | Exact collection difference, evaluated grid agrees with cutter union |
| B — Continuous bends / corner slivers | PASS at inspected scale | Isolated slab image, manifold mesh, 3-inch sampling; no proof for every sub-grid feature |
| B — No prior-ABS-envelope intrusion | FAIL | Approximately 2.375 sf sampled overlap, cutters 001 and 008; conflict screenshot |
| B — Structural crossing | PASS as tagged assumption | DO_NOT_CUT_STRUCTURE/FIELD_VERIFY marker retained; no footing Boolean applied |
| B — Slab thickness | PASS | Evaluated 5.5 inches |
| C — Calibrated main routing | PASS within package basis | QA board visually compared to isolated route; supplied route validator and saved route checks |
| C — Prior ABS distinct/protected | PARTIAL | Retained pipe persists and is distinct; slab envelope conflict prevents acceptance |
| C — Prior ABS tie without continuing trench | FAIL at boundary | Pipe tie preserved; cutter endpoint extensions cross protection envelope |
| C — 4-inch/6-inch continuity | PASS within model | Supplied route validation and saved network control comparison |
| C — +18-inch lateral limit | PASS | New lateral and exterior cut at Y=-1.5 ft |
| C — Branch/fixture clusters | PASS as coordination proxies | QA fitting overlay compared to isolated fitting/route views; not exact manufactured connections |
| D — Frame 001 existing | PASS in cutaway | Existing fixture state visible |
| D — Frame 038 access item removal | PARTIAL at exact checkpoint | Motion starts at 38 and reaches storage at 48; 038 is not the completed storage state |
| D — Frame 050 finish strips | PASS in cutaway | Access-strip markers visible; final measured extent remains field verified |
| D — Frame 061 wall/stack exposure | PASS as proxy | Vertical exposure/cut markers; no excessive structural cutting inferred |
| D — Frame 068 sawcuts | PASS in cutaway | Sawcut edges appear |
| D — Frame 076 slab lift/vapor | PASS in cutaway | Lifted chunks and vapor layer visible |
| D — Frame 083 existing CI | PASS in cutaway | CI, carrier and support geometry visible; soil/vapor overlays remain |
| D — Frame 089 CI removed | PASS for phasing | DEMO_CI role goes to zero; not a literal excavated-soil Boolean model |
| E — >=10 junction bodies | PASS | 10 |
| E — Oriented bends | PASS at coordination scale | Seven bend objects follow branch/pipe directions |
| E — Seven traps / conditional kitchen | PASS as proxies | Seven objects; concealed/as-found details remain FIELD_VERIFY |
| E — Both WC carriers | PASS as generic proxies | North and south carrier bodies present; inspected isolated |
| E — WC/stack cut rings | PASS | 40-inch WC and 36-inch wet-core/laundry targets |
| E — Supports above/below | PASS | Ten supports for five vertical cuts |
| E — Prior ABS cut field verified | PASS | FIELD_VERIFY remains true |
| E — Exterior cut +18 inches | PASS | X=23.24833 ft, Y=-1.5 ft |
| F — Default camera shows B-101 clearly | FAIL | Upper slabs obscure work, B-101 poorly framed |
| F — Materials distinguish categories | PARTIAL | Categories are distinct in diagnostic views; default Eevee camera prevents detailed review |
| F — X-ray/cutaway clarity | FAIL in authored camera | No adequate cutaway in saved model; supplemental views only |
| F — Render completeness / no black frames | See render_inventory.json | All returned PNGs decoded and inspected; occlusion remains an acceptance failure |
| G — Overall | REVISION REQUIRED | Geometry protection conflict and authored-camera visibility |
