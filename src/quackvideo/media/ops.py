"""FFmpeg-backed media operations."""

from __future__ import annotations

import re
from pathlib import Path

from quackvideo.domain.enums import AspectRatio
from quackvideo.domain.models import PlatformPreset
from quackvideo.media.engine import FFmpegEngine
from quackvideo.media.errors import OperationFailed


def extract_audio(engine: FFmpegEngine, source: Path, dest: Path, codec: str = "flac") -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    codec_map = {"flac": "flac", "wav": "pcm_s16le", "mp3": "libmp3lame", "aac": "aac"}
    result = engine.run(
        [
            "-i",
            str(source),
            "-vn",
            "-acodec",
            codec_map.get(codec, codec),
            str(dest),
        ]
    )
    engine.ensure_ok(result, "audio extraction")
    return dest


def loudnorm_audio(engine: FFmpegEngine, source: Path, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    result = engine.run(
        [
            "-i",
            str(source),
            "-af",
            "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-ar",
            "48000",
            str(dest),
        ]
    )
    engine.ensure_ok(result, "loudnorm")
    return dest


def slice_media(
    engine: FFmpegEngine,
    source: Path,
    dest: Path,
    start: float,
    end: float,
    *,
    reencode: bool = False,
) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    duration = max(0.01, end - start)
    args = ["-ss", f"{start:.3f}", "-i", str(source), "-t", f"{duration:.3f}"]
    if reencode:
        if dest.suffix.lower() in {".mp4", ".mov", ".mkv"}:
            args += ["-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p"]
        else:
            args += ["-vn", "-c:a", "flac"]
    else:
        args += ["-c", "copy"]
    args.append(str(dest))
    result = engine.run(args)
    engine.ensure_ok(result, "slice")
    return dest


def mix_audio(
    engine: FFmpegEngine,
    first: Path,
    second: Path,
    dest: Path,
    volumes: tuple[float, float] = (0.2, 0.8),
) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    filt = f"[0:a]volume={volumes[0]}[a0];[1:a]volume={volumes[1]}[a1];[a0][a1]amix=inputs=2:duration=longest[a]"
    result = engine.run(
        [
            "-i",
            str(first),
            "-i",
            str(second),
            "-filter_complex",
            filt,
            "-map",
            "[a]",
            str(dest),
        ]
    )
    engine.ensure_ok(result, "audio mix")
    return dest


def replace_audio(engine: FFmpegEngine, video: Path, audio: Path, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    result = engine.run(
        [
            "-i",
            str(video),
            "-i",
            str(audio),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "320k",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-shortest",
            str(dest),
        ]
    )
    engine.ensure_ok(result, "audio swap")
    return dest


def transcode_mezzanine(engine: FFmpegEngine, source: Path, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    result = engine.run(
        [
            "-i",
            str(source),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(dest),
        ]
    )
    engine.ensure_ok(result, "transcode")
    return dest


def fit_aspect(engine: FFmpegEngine, source: Path, dest: Path, preset: PlatformPreset) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    vf = _scale_pad_filter(preset)
    result = engine.run(
        [
            "-i",
            str(source),
            "-vf",
            vf,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-pix_fmt",
            "yuv420p",
            str(dest),
        ]
    )
    engine.ensure_ok(result, "aspect fit")
    return dest


def burn_subtitles(engine: FFmpegEngine, source: Path, srt: Path, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    escaped = str(srt).replace("\\", "\\\\").replace(":", "\\:").replace("'", r"\'")
    result = engine.run(
        [
            "-i",
            str(source),
            "-vf",
            f"subtitles='{escaped}'",
            "-c:a",
            "copy",
            str(dest),
        ]
    )
    engine.ensure_ok(result, "caption burn-in")
    return dest


def thumbnail_sheet(engine: FFmpegEngine, source: Path, dest: Path, fps: str = "1/5") -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    result = engine.run(
        [
            "-i",
            str(source),
            "-vf",
            f"fps={fps},scale=320:-1,tile=4x4",
            "-frames:v",
            "1",
            str(dest),
        ]
    )
    engine.ensure_ok(result, "thumbnail sheet")
    return dest


def detect_silence(engine: FFmpegEngine, source: Path) -> list[tuple[float, float]]:
    result = engine.run(
        [
            "-i",
            str(source),
            "-af",
            "silencedetect=noise=-30dB:d=0.5",
            "-f",
            "null",
            "-",
        ]
    )
    stderr = (result.stderr or b"").decode("utf-8", errors="replace")
    starts = [float(m) for m in re.findall(r"silence_start:\s*([0-9.]+)", stderr)]
    ends = [float(m) for m in re.findall(r"silence_end:\s*([0-9.]+)", stderr)]
    ranges: list[tuple[float, float]] = []
    for index, start in enumerate(starts):
        end = ends[index] if index < len(ends) else start
        ranges.append((start, end))
    return ranges


def detect_black(engine: FFmpegEngine, source: Path) -> list[tuple[float, float]]:
    result = engine.run(
        [
            "-i",
            str(source),
            "-vf",
            "blackdetect=d=0.5:pic_th=0.98",
            "-an",
            "-f",
            "null",
            "-",
        ]
    )
    stderr = (result.stderr or b"").decode("utf-8", errors="replace")
    found: list[tuple[float, float]] = []
    for match in re.finditer(r"black_start:([0-9.]+)\s+black_end:([0-9.]+)", stderr):
        found.append((float(match.group(1)), float(match.group(2))))
    return found


def detect_scenes(engine: FFmpegEngine, source: Path, threshold: float = 0.3) -> list[float]:
    result = engine.run(
        [
            "-i",
            str(source),
            "-vf",
            f"select='gt(scene,{threshold})',showinfo",
            "-f",
            "null",
            "-",
        ]
    )
    stderr = (result.stderr or b"").decode("utf-8", errors="replace")
    times = [float(m) for m in re.findall(r"pts_time:([0-9.]+)", stderr)]
    return times


def generate_synthetic_video(
    engine: FFmpegEngine,
    dest: Path,
    *,
    duration: float = 4.0,
    width: int = 640,
    height: int = 360,
    fps: int = 15,
    with_audio: bool = True,
) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    args = [
        "-f",
        "lavfi",
        "-i",
        f"testsrc=duration={duration}:size={width}x{height}:rate={fps}",
    ]
    if with_audio:
        args += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}"]
        args += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest"]
    else:
        args += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
    args.append(str(dest))
    result = engine.run(args)
    engine.ensure_ok(result, "synthetic video")
    if not dest.exists():
        raise OperationFailed("synthetic video was not written")
    return dest


def generate_synthetic_audio(
    engine: FFmpegEngine,
    dest: Path,
    *,
    duration: float = 4.0,
    frequency: float = 440.0,
) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    result = engine.run(
        [
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={frequency}:duration={duration}",
            str(dest),
        ]
    )
    engine.ensure_ok(result, "synthetic audio")
    return dest


def _scale_pad_filter(preset: PlatformPreset) -> str:
    w, h = preset.width, preset.height
    if preset.aspect == AspectRatio.VERTICAL:
        return f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}"
    if preset.aspect == AspectRatio.SQUARE:
        return f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2"
    return f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2"
