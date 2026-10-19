"""Verify the exact planned frame set, then create a storyboard or native film."""
import argparse
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from video_common import digest, load_plan, materialize, repo_path


def verify_frames(plan, folder):
    expected = {f"f{frame['index']:06}.png" for frame in plan["frames"]}
    actual = {p.name for p in folder.glob("f*.png")}
    if actual != expected:
        raise ValueError(f"Frame set mismatch: missing={sorted(expected-actual)[:8]}, extra={sorted(actual-expected)[:8]}")
    for frame in plan["frames"]:
        path = folder / f"f{frame['index']:06}.png"
        metadata = json.loads(path.with_suffix(".json").read_text())
        if metadata.get("plan_id") != plan["plan_id"] or metadata.get("index") != frame["index"] or metadata.get("sha256") != digest(path):
            raise ValueError(f"Frame provenance mismatch: {path.name}")
        if not metadata.get("raw_checks", {}).get("nonblank"):
            raise ValueError(f"Frame lacks raw-image validation: {path.name}")
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            if image.size != (plan["settings"]["width"], plan["settings"]["height"]):
                raise ValueError(f"Frame dimensions changed: {path.name}")


def storyboard(plan, folder, output):
    tw, th, band = 640, 360, 36
    columns = 2
    rows = (len(plan["frames"]) + columns - 1) // columns
    board = Image.new("RGB", (tw * columns, (th + band) * rows), "#F7F6F2")
    draw = ImageDraw.Draw(board)
    font = ImageFont.truetype(str(repo_path(plan["recipe"]["style"]["sans_font"])), 17)
    for n, frame in enumerate(plan["frames"]):
        x, y = n % columns * tw, n // columns * (th + band)
        with Image.open(folder / f"f{frame['index']:06}.png") as image:
            board.paste(image.convert("RGB").resize((tw, th), Image.Resampling.LANCZOS), (x, y))
        draw.text((x + 12, y + th + 7), f"{frame['shot']} | source {frame['source_time']:.1f}s", font=font, fill="#29343A")
    path = output / "storyboard.png"
    board.save(path)
    return path


def probe(path):
    result = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_format", "-of", "json", str(path)], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def encode(plan, folder, output, no_audio=False):
    destination = output / "video.mp4"
    command = ["ffmpeg", "-y", "-v", "error", "-framerate", str(plan["settings"]["native_fps"]),
               "-start_number", "0", "-i", str(folder / "f%06d.png")]
    audio = plan["recipe"].get("audio") if not no_audio else None
    if audio:
        path = materialize(audio["path"], audio["sha256"])
        command += ["-i", str(path)]
        graph = []
        for n, shot in enumerate(plan["shots"]):
            speed = (shot["source_out"] - shot["source_in"]) / shot["duration"]
            graph.append(f"[1:a:0]atrim=start={shot['source_in']}:end={shot['source_out']},asetpts=PTS-STARTPTS,atempo={speed}[a{n}]")
        graph.append("".join(f"[a{n}]" for n in range(len(plan["shots"]))) + f"concat=n={len(plan['shots'])}:v=0:a=1[audio]")
        command += ["-filter_complex", ";".join(graph), "-map", "0:v:0", "-map", "[audio]", "-c:a", "aac", "-b:a", "192k"]
    else:
        command += ["-map", "0:v:0", "-an"]
    command += ["-vf", f"fps={plan['delivery_fps']},format=yuv420p", "-c:v", "libx264", "-crf", "18", "-preset", "medium",
                "-threads", "2", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                "-t", str(plan["duration"]), "-movflags", "+faststart", str(destination)]
    subprocess.run(command, check=True)
    media = probe(destination)
    video = next(s for s in media["streams"] if s["codec_type"] == "video")
    expected = round(plan["duration"] * plan["delivery_fps"])
    settings = plan["settings"]
    if int(video["nb_read_frames"]) != expected or (video["width"], video["height"]) != (settings["width"], settings["height"]):
        raise ValueError("Encoded video frame count or dimensions do not match the plan")
    if video["avg_frame_rate"] != f"{plan['delivery_fps']}/1" or abs(float(video["duration"]) - plan["duration"]) > 1 / plan["delivery_fps"]:
        raise ValueError("Encoded video timing does not match the plan")
    if audio and not any(s["codec_type"] == "audio" for s in media["streams"]):
        raise ValueError("Expected narrated audio track is missing")
    return destination, media


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--frames", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--no-audio", action="store_true")
    args = parser.parse_args()
    plan = load_plan(args.plan)
    args.output.mkdir(parents=True, exist_ok=True)
    report = {"status": "failed", "plan_id": plan["plan_id"], "profile": plan["profile"],
              "native_render_fps": plan["settings"]["native_fps"], "delivery_fps": plan["delivery_fps"],
              "optical_interpolation": False, "visual_review": "pending", "model_notice": plan["model"]["notice"]}
    try:
        verify_frames(plan, args.frames)
        if plan["profile"] == "storyboard":
            artifact = storyboard(plan, args.frames, args.output)
        else:
            artifact, media = encode(plan, args.frames, args.output, args.no_audio)
            report["media"] = media
        report.update(status="assembled", file=artifact.name, sha256=digest(artifact), frames_checked=len(plan["frames"]))
    except Exception as error:
        report["error"] = str(error)
        raise
    finally:
        (args.output / "video-report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps({k: v for k, v in report.items() if k != "media"}, indent=2))


if __name__ == "__main__":
    main()
