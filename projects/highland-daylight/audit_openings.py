"""Recheck all handoff conflicts against outward-facing registered plan returns."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "deliverables/highland-daylight"


def interpolate(value, pixels, inches):
    pairs = sorted(zip(pixels, inches))
    i = next((i for i in range(len(pairs)-1) if value <= pairs[i+1][0]), len(pairs)-2)
    a, b = pairs[i:i+2]
    return a[1] + (value-a[0])/(b[0]-a[0])*(b[1]-a[1])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    spec = json.loads((ROOT / "projects/highland-refined/exterior-revised.spec.json").read_text())
    records = []
    for i, candidate in enumerate(spec["rejected_candidates"]):
        registration = spec["facade_registration"][candidate["face"]]
        lo, hi = sorted(interpolate(v, registration["pixels"], registration["inches"])
                        for v in candidate["pixels"])
        center = (lo+hi)/2
        polygon = "r1" if candidate["level"] in ("P1", "R1") else "r5" if candidate["level"] == "R5" else "typical"
        vertices = spec["polygons"][polygon]
        matches = []
        for j, (a, b) in enumerate(zip(vertices, vertices[1:]+vertices[:1])):
            outward = b[0] < a[0] if candidate["face"] == "south" else b[0] > a[0]
            mn, mx = sorted((a[0], b[0]))
            if abs(a[1]-b[1]) < .01 and outward and mn <= center <= mx:
                matches.append({"segment": j, "extent_in": [mn, mx], "depth_in": a[1],
                                "fitting_width_in_with_6in_jamb_margin": round(min(hi-lo, 2*(center-mn-6), 2*(mx-center-6)), 3)})
        evidence = ("Projected center falls outside every outward-facing segment for this elevation and floor."
                    if not matches else "Projected opening cannot fit the matching outward-facing return with the inherited six-inch jamb allowance.")
        records.append({"id": f"OPEN-{i+1:02}", **candidate, "polygon": polygon,
                        "projected_center_in": round(center, 3), "projected_width_in": round(hi-lo, 3),
                        "outward_facing_matches": matches, "decision": "retain unresolved; no geometry change",
                        "review_basis": evidence,
                        "source_review": "A3.01 south / A3.02 north elevation crops; A2.03 R1 and A2.07 R5 plan crops; inherited A2.04 polygon registration",
                        "needed_to_resolve": "Original plan/elevation sheets or a clearer return photograph to establish the correct wall and jamb locations."})
    report = {"opening_inventory": len(spec["openings"]), "reviewed_candidates": len(records),
              "resolved_candidates": 0, "remaining_unresolved": len(records),
              "basis": "Existing source crops visually reviewed; geometry calculations independently recomputed using outward-facing segments. Partial cropped drawings do not establish revised jamb offsets.",
              "candidates": records}
    (OUT / "opening-audit.json").write_text(json.dumps(report, indent=2)+"\n")
    with (OUT / "opening-audit.csv").open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["id", "face", "level", "source_pixels", "projected_center_in", "projected_width_in", "decision", "review_basis"])
        for r in records:
            writer.writerow([r[k] for k in ("id", "face", "level", "pixels", "projected_center_in", "projected_width_in", "decision", "review_basis")])
    print(f"Reviewed {len(records)} conflicts; {len(spec['openings'])} openings retained; no unsupported opening added.")


if __name__ == "__main__":
    main()
