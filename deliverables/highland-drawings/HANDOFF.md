# Continue from revision 04

Open `deliverables/highland-drawings/Highland-drawing-reconciled.blend`, then read the source comparison PDF and `opening-audit.json`. The three uploaded PDFs are preserved byte-for-byte under `references/`, with nineteen inventoried sheets and SHA-256 hashes. These replace the previous handoff's missing-PDF limitation.

Thirteen candidates now have provisional plan locations. One R5 north candidate was a lower-floor MZ incorrectly repeated on R5. Two candidates still require shell reconciliation: OPEN-01 at the P1 residential step and OPEN-14 at the southeast R5 return. North R2-R5 opening counts now follow the six actual elevation openings on each floor; existing north column IDs are reassigned, so inspect the full change ledger when tracking identity.

The accepted placements are not all dimensionally reconciled. The diagnostic north overlay exposes differences up to 42.443 pixels on the inherited overview raster, particularly around the stair/MU pair. Plan jambs govern this provisional patch. Simplified wall depth, raster picks and registration remain part of that disagreement. Do not report all sixteen issues closed or call the model verified as-built.

The revision retains every inherited plan polygon and all roof/terrace geometry. The full original P1 outline was unavailable when that shell was built from R1; A2.02 is now present. Trace a separate P1 polygon and recheck its openings together before adding OPEN-01. At OPEN-14, reconcile the southeast R5 local step, the east elevation, the slab and coping above together. Do not clip its jamb to fit the old return. R1 north door/entry details also need an audit against the newly supplied elevation.

The terrace/coping profiles and exterior guards are still assumed or provisional. A2.08 confirms inherited top-elevation callouts but does not supply the referenced A4/A5 profiles. A6 stair guards do not establish exterior terrace guards. Drawings are dated 04-02-07 with handwritten ASI/RFI references; complete responses and installed-condition verification remain absent.

`geometry-validation.json` records exact changed/unchanged mesh inventories. `delivery-validation.json` reads the saved native file, all corrected frame extents, no overlapping voids, packed images, GLB architecture and the full dusk camera. `visual-review.json` binds inspected stills/source comparisons/report pages to their hashes. The ZIP includes the base native scene and reproduction inputs. The older revision 03 dusk film is not included or relabeled as revision 04.
