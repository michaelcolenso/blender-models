"""Archive the visually reviewed revision and its exact reproduction inputs."""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / "deliverables/highland-daylight"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    validation = json.loads((OUT/"delivery-validation.json").read_text())
    review = json.loads((OUT/"visual-review.json").read_text())
    assert review["final_still_reviewed"] and review["all_comparison_pages_reviewed"]
    assert review["still_sha256"] == validation["still_sha256"] == sha(OUT/"Highland-daylight-photo-study.png")
    assert review["pdf_sha256"] == sha(OUT/"Highland-daylight-source-comparison.pdf")
    assert validation["native_sha256"] == sha(OUT/"Highland-daylight-photo-study.blend")
    assert validation["glb_sha256"] == sha(OUT/"Highland-daylight-photo-study.glb")
    outputs = ["README.md", "CHANGELOG.md", "Highland-daylight-photo-study.png",
               "Highland-daylight-photo-study.blend", "Highland-daylight-photo-study.glb",
               "Highland-daylight-source-comparison.pdf", "Highland-camera-landmarks.png",
               "camera-fit.json", "opening-audit.json", "opening-audit.csv",
               "scene-validation.json", "delivery-validation.json", "visual-review.json"]
    workflow_record = OUT/"workflow-input-validation.json"
    if workflow_record.exists():
        workflow = json.loads(workflow_record.read_text())
        assert workflow["saved_model_sha256"] == validation["native_sha256"], "Refresh the saved-scene workflow record after rebuilding."
        outputs.append(workflow_record.name)
    sources = sorted(p for p in HERE.iterdir() if p.suffix in (".py", ".json", ".md", ".txt"))
    for relative in (
        "projects/highland-refined/exterior-revised.spec.json",
        "projects/highland-refined/HANDOFF.md",
        "deliverables/highland-refined/Highland-revised-daylight-and-film.blend",
        "deliverables/highland-refined/scene-readback.json",
        "deliverables/highland-refined/source-review/south.png",
        "deliverables/highland-refined/source-review/east.png",
        "projects/highland-cinematic/assets/source.json",
        "projects/highland-drone/flight.spec.json",
        "projects/highland-drone/osm-buildings-source.json",
    ):
        sources.append(ROOT/relative)
    sources += sorted((ROOT/"projects/highland-exterior/source-review").glob("*.png"))
    sources += sorted((ROOT/"projects/highland-exterior/source-review").glob("user-photo-*.jpg"))
    manifest = {"outputs": {name: {"bytes": (OUT/name).stat().st_size, "sha256": sha(OUT/name)} for name in outputs},
                "reproduction_inputs": {str(p.relative_to(ROOT)): {"bytes": p.stat().st_size, "sha256": sha(p)} for p in sources}}
    (OUT/"source-manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
    archive = OUT/"Highland-daylight-editable.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for name in outputs+["source-manifest.json"]:
            z.write(OUT/name, name)
        for p in sources:
            z.write(p, "reproduction/"+str(p.relative_to(ROOT)))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        count = len(z.infolist())
    result = {"file": archive.name, "bytes": archive.stat().st_size, "sha256": sha(archive),
              "files": count, "crc_check_passed": True, "visual_review_bound_to_exact_still_and_pdf": True}
    (OUT/"package-validation.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
