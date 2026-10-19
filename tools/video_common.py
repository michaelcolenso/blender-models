"""Shared, deterministic video planning and asset handling. No Blender import."""
import hashlib
import json
import math
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILES = {
    "storyboard": {"width": 960, "height": 540, "native_fps": 1, "samples": 16},
    "preview": {"width": 640, "height": 360, "native_fps": 6, "samples": 8},
    "production1080": {"width": 1920, "height": 1080, "native_fps": 24, "samples": 128},
    "production4k": {"width": 3840, "height": 2160, "native_fps": 24, "samples": 256},
}
CODE = ["tools/video_common.py", "tools/video_plan.py", "tools/render_video.py",
        "tools/assemble_video.py", "tools/video_graphics.py", "tools/render_scene.py", "tools/render_plan.py",
        "render/requirements.txt",
        "projects/highland-installation/studio-upgrade/render_studio.py",
        "projects/highland-installation/studio-upgrade/studio-config.json",
        "projects/highland-installation/animation-90s/animation-spec.json"]


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def signature(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def repo_path(value):
    if not isinstance(value, str) or not value:
        raise ValueError("Expected a nonempty repository-relative path")
    path = Path(value)
    resolved = (ROOT / path).resolve()
    if path.is_absolute() or not resolved.is_relative_to(ROOT) or not resolved.is_file():
        raise ValueError(f"Missing or unsafe repository path: {value}")
    return resolved


def asset_identity(path):
    """LFS pointer identity is the identity of its content, not pointer bytes."""
    path = Path(path)
    with path.open("rb") as stream:
        head = stream.read(256)
    if head.startswith(b"version https://git-lfs.github.com/spec/v1\n"):
        match = re.search(rb"oid sha256:([0-9a-f]{64})\nsize ([0-9]+)", head)
        if not match:
            raise ValueError(f"Invalid Git LFS pointer: {path}")
        return match[1].decode(), True
    return digest(path), False


def materialize(path, expected):
    path = repo_path(path)
    actual, pointer = asset_identity(path)
    if actual != expected:
        raise ValueError(f"Asset version changed: {path.name}; update the catalog deliberately")
    if not pointer:
        return path
    cache = ROOT / "build/video-assets"
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / f"{expected}-{path.name}"
    if target.exists() and digest(target) == expected:
        return target
    with tempfile.NamedTemporaryFile(dir=cache, suffix=path.suffix, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            subprocess.run(["git", "lfs", "smudge", str(path.relative_to(ROOT))],
                           input=path.read_bytes(), stdout=stream, cwd=ROOT, check=True)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    if digest(temporary) != expected:
        temporary.unlink()
        raise ValueError(f"Downloaded asset checksum mismatch: {path.name}")
    temporary.replace(target)
    return target


def valid_id(value):
    return isinstance(value, str) and re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", value) and value != "all"


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def compile_plan(recipe_path, profile, selection="all", sample_seconds=None, chunk_size=48, device="CPU"):
    recipe_file = repo_path(recipe_path)
    recipe = json.loads(recipe_file.read_text())
    registry_file = ROOT / "render/models.json"
    registry = json.loads(registry_file.read_text())
    if recipe.get("schema_version") != 1 or registry.get("schema_version") != 1:
        raise ValueError("Expected schema_version 1")
    if profile not in PROFILES or type(chunk_size) is not int or not 1 <= chunk_size <= 240:
        raise ValueError("Unknown profile or invalid chunk size (1..240)")
    if device not in ("CPU", "OPTIX", "CUDA"):
        raise ValueError("Unsupported render device")
    if not valid_id(recipe.get("id")) or not isinstance(recipe.get("brief"), str) or not recipe["brief"].strip():
        raise ValueError("Video needs a safe ID and a written brief")
    model = registry["models"].get(recipe.get("model"))
    if not model or model.get("adapter") != "highland-studio":
        raise ValueError("Unknown model or unsupported presentation adapter")
    identity, _ = asset_identity(repo_path(model["blend"]))
    if identity != model["sha256"]:
        raise ValueError("Model checksum does not match the catalog")
    if digest(repo_path(model["geometry_authority"])) != model["geometry_authority_sha256"]:
        raise ValueError("Geometry specification changed; rebuild and validate the model before updating its catalog entry")
    for evidence in model["validation_evidence"]:
        if json.loads(repo_path(evidence).read_text()).get("passed") is not True:
            raise ValueError(f"Source validation has not passed: {evidence}")
    style = recipe.get("style", {})
    for field in ("paper", "ink"):
        if not isinstance(style.get(field), str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", style[field]):
            raise ValueError(f"Invalid style {field}")
    dependencies = set(CODE + [str(recipe_file.relative_to(ROOT)), "render/models.json",
                              model["geometry_authority"], *model["validation_evidence"]])
    for field in ("serif_font", "sans_font"):
        dependencies.add(str(repo_path(style[field]).relative_to(ROOT)))
    shots = recipe.get("shots")
    if not isinstance(shots, list) or not shots:
        raise ValueError("Video must contain shots")
    seen = set()
    for shot in shots:
        shot_id = shot.get("id")
        if not valid_id(shot_id) or shot_id in seen:
            raise ValueError("Shot IDs must be safe and unique")
        seen.add(shot_id)
        if shot.get("scene") not in model["scenes"]:
            raise ValueError(f"{shot_id}: unknown scene alias")
        for field in ("source_in", "source_out", "duration"):
            if not number(shot.get(field)):
                raise ValueError(f"{shot_id}: {field} must be finite")
        if not 0 <= shot["source_in"] < shot["source_out"] <= model["source_duration"] or shot["duration"] <= 0:
            raise ValueError(f"{shot_id}: invalid source interval or duration")
        if not 0.5 <= (shot["source_out"] - shot["source_in"]) / shot["duration"] <= 2:
            raise ValueError(f"{shot_id}: supported playback speed is 0.5x..2x")
        if not isinstance(shot.get("title"), str) or not shot["title"].strip():
            raise ValueError(f"{shot_id}: title is required")
        if not isinstance(shot.get("detail"), str):
            raise ValueError(f"{shot_id}: detail must be text")
        position = shot.get("title_position", style.get("title_position"))
        if not isinstance(position, list) or len(position) != 2 or any(not number(n) or not 0 <= n <= 0.9 for n in position):
            raise ValueError(f"{shot_id}: title position must be two normalized coordinates")
        if not number(shot.get("title_size", style.get("title_size", 94))) or not 32 <= shot.get("title_size", style.get("title_size", 94)) <= 144:
            raise ValueError(f"{shot_id}: title size must be 32..144 at 1920px width")
        posters = shot.get("posters")
        if not isinstance(posters, list) or not posters or any(not number(t) or not shot["source_in"] <= t < shot["source_out"] for t in posters):
            raise ValueError(f"{shot_id}: poster times must fall inside the source interval")
    selected = [dict(s) for s in shots if selection == "all" or s["id"] == selection]
    if not selected:
        raise ValueError(f"Unknown shot: {selection}")
    if sample_seconds is not None:
        if profile != "preview" or len(selected) != 1 or not number(sample_seconds) or not 0 < sample_seconds <= selected[0]["duration"]:
            raise ValueError("A sample needs preview, one shot, and a positive duration within that shot")
        shot = selected[0]
        span = min(sample_seconds, shot["source_out"] - shot["source_in"])
        begin = min(max(shot["posters"][0] - span / 2, shot["source_in"]), shot["source_out"] - span)
        shot.update(source_in=begin, source_out=begin + span, duration=sample_seconds)
    audio = recipe.get("audio")
    if audio:
        if asset_identity(repo_path(audio["path"]))[0] != audio["sha256"]:
            raise ValueError("Audio asset checksum changed")
    frames = []
    elapsed = 0.0
    settings = PROFILES[profile]
    for shot in selected:
        if profile == "storyboard":
            times = shot["posters"]
        else:
            count = shot["duration"] * settings["native_fps"]
            if not math.isclose(count, round(count), abs_tol=1e-7):
                raise ValueError(f"{shot['id']}: duration must align to native frame boundaries")
            times = [shot["source_in"] + n / round(count) * (shot["source_out"] - shot["source_in"]) for n in range(round(count))]
        for n, source_time in enumerate(times):
            output_time = elapsed + ((source_time - shot["source_in"]) / (shot["source_out"] - shot["source_in"]) * shot["duration"]
                                     if profile == "storyboard" else n / settings["native_fps"])
            frames.append({"index": len(frames), "shot": shot["id"], "scene": shot["scene"],
                           "source_time": round(source_time, 9),
                           "output_time": round(output_time, 9)})
        elapsed += shot["duration"]
    chunks = [{"id": f"chunk-{n//chunk_size:04}", "first": n, "last": min(n+chunk_size, len(frames))-1}
              for n in range(0, len(frames), chunk_size)]
    if not frames or len(chunks) > 256:
        raise ValueError("Plan needs 1..256 chunks; increase chunk size or select fewer shots")
    plan = {"schema_version": 1, "recipe": recipe, "model": model, "shots": selected,
            "profile": profile, "settings": settings, "delivery_fps": 24,
            "device": device, "blender_version": "5.0.1",
            "duration": round(elapsed, 9), "sample_seconds": sample_seconds,
            "frames": frames, "chunks": chunks,
            "dependencies": {p: digest(repo_path(p)) for p in sorted(dependencies)}}
    plan["plate_id"] = signature({"model": model["sha256"], "scenes": model["scenes"], "source_fps": model["source_fps"],
                                  "settings": settings, "device": device, "blender": plan["blender_version"],
                                  "code": {p: plan["dependencies"][p] for p in
                                           ("tools/render_video.py", "tools/render_scene.py", "tools/render_plan.py", "render/requirements.txt")}})
    plan["plan_id"] = signature(plan)
    return plan


def load_plan(path):
    plan = json.loads(Path(path).read_text())
    contents = {k: v for k, v in plan.items() if k != "plan_id"}
    if signature(contents) != plan.get("plan_id"):
        raise ValueError("Plan signature is invalid; regenerate the plan")
    for name, expected in plan["dependencies"].items():
        if digest(repo_path(name)) != expected:
            raise ValueError(f"Plan input changed: {name}; regenerate the plan")
    return plan
