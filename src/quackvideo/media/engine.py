"""Safe ffmpeg/ffprobe runner. Commands are argv lists; never shell=True."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path

from quackvideo.domain.models import ProbeResult, ProbeStream
from quackvideo.media.errors import OperationFailed, ToolNotFound


def _parse_fps(value: str | None) -> float | None:
    if not value or value in {"0/0", "N/A"}:
        return None
    if "/" in value:
        num, den = value.split("/", 1)
        try:
            denom = float(den)
            return float(num) / denom if denom else None
        except ValueError:
            return None
    try:
        return float(value)
    except ValueError:
        return None


class FFmpegEngine:
    """Discover binaries and run argv-only ffmpeg/ffprobe commands."""

    def __init__(
        self,
        ffmpeg_bin: str | None = None,
        ffprobe_bin: str | None = None,
        timeout_sec: float = 600.0,
    ) -> None:
        self.ffmpeg_bin = shutil.which("ffmpeg") if ffmpeg_bin is None else ffmpeg_bin
        self.ffprobe_bin = shutil.which("ffprobe") if ffprobe_bin is None else ffprobe_bin
        self.timeout_sec = timeout_sec

    def available(self) -> bool:
        return bool(self.ffmpeg_bin and self.ffprobe_bin)

    def require(self) -> None:
        missing: list[str] = []
        if not self.ffmpeg_bin:
            missing.append("ffmpeg")
        if not self.ffprobe_bin:
            missing.append("ffprobe")
        if missing:
            raise ToolNotFound(f"Missing on PATH: {', '.join(missing)}")

    def run(
        self,
        args: Sequence[str],
        *,
        timeout: float | None = None,
        capture: bool = True,
    ) -> subprocess.CompletedProcess[bytes]:
        self.require()
        cmd = [self.ffmpeg_bin or "ffmpeg", "-hide_banner", "-nostdin", "-y", *args]
        return self._exec(cmd, timeout=timeout, capture=capture)

    def run_ffprobe(
        self,
        args: Sequence[str],
        *,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[bytes]:
        self.require()
        cmd = [self.ffprobe_bin or "ffprobe", *args]
        return self._exec(cmd, timeout=timeout, capture=True)

    def _exec(
        self,
        cmd: list[str],
        *,
        timeout: float | None,
        capture: bool,
    ) -> subprocess.CompletedProcess[bytes]:
        try:
            return subprocess.run(  # noqa: S603
                cmd,
                check=False,
                capture_output=capture,
                timeout=timeout or self.timeout_sec,
                env=os.environ.copy(),
            )
        except subprocess.TimeoutExpired as exc:
            raise OperationFailed("FFmpeg timed out", stderr=str(exc)) from exc
        except FileNotFoundError as exc:
            raise ToolNotFound(str(exc)) from exc

    def probe(self, path: Path) -> ProbeResult:
        result = self.run_ffprobe(
            [
                "-v",
                "error",
                "-show_format",
                "-show_streams",
                "-of",
                "json",
                str(path),
            ]
        )
        if result.returncode != 0:
            stderr = (result.stderr or b"").decode("utf-8", errors="replace")
            raise OperationFailed(f"ffprobe failed for {path}", stderr=stderr)
        payload = json.loads(result.stdout.decode("utf-8"))
        streams: list[ProbeStream] = []
        for stream in payload.get("streams", []):
            streams.append(
                ProbeStream(
                    index=int(stream.get("index", 0)),
                    codec_type=stream.get("codec_type", "unknown"),
                    codec_name=stream.get("codec_name"),
                    duration=float(stream["duration"]) if stream.get("duration") else None,
                    width=int(stream["width"]) if stream.get("width") else None,
                    height=int(stream["height"]) if stream.get("height") else None,
                    fps=_parse_fps(stream.get("avg_frame_rate") or stream.get("r_frame_rate")),
                    sample_rate=int(stream["sample_rate"]) if stream.get("sample_rate") else None,
                    channels=int(stream["channels"]) if stream.get("channels") else None,
                    bit_rate=int(stream["bit_rate"]) if stream.get("bit_rate") else None,
                )
            )
        fmt = payload.get("format", {})
        duration = float(fmt.get("duration") or 0.0)
        if not duration and streams:
            duration = max((s.duration or 0.0) for s in streams)
        return ProbeResult(
            path=path,
            duration=duration,
            format_name=fmt.get("format_name"),
            size_bytes=int(fmt["size"]) if fmt.get("size") else None,
            bit_rate=int(fmt["bit_rate"]) if fmt.get("bit_rate") else None,
            streams=streams,
        )

    def ensure_ok(self, result: subprocess.CompletedProcess[bytes], action: str) -> None:
        if result.returncode == 0:
            return
        stderr = (result.stderr or b"").decode("utf-8", errors="replace")
        raise OperationFailed(f"{action} failed", stderr=stderr)
