"""Caption helpers."""

from __future__ import annotations

from pathlib import Path

from quackvideo.domain.models import Transcript, TranscriptSegment


def format_ts(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours, rem = divmod(millis, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, milli = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milli:03d}"


def format_vtt(seconds: float) -> str:
    return format_ts(seconds).replace(",", ".")


def slice_transcript(transcript: Transcript, start: float, end: float) -> Transcript:
    segments: list[TranscriptSegment] = []
    for segment in transcript.segments:
        if segment.end <= start or segment.start >= end:
            continue
        clipped = TranscriptSegment(
            start=max(segment.start, start) - start,
            end=min(segment.end, end) - start,
            text=segment.text,
            speaker=segment.speaker,
        )
        if clipped.end > clipped.start:
            segments.append(clipped)
    text = " ".join(seg.text.strip() for seg in segments).strip()
    return Transcript(
        language=transcript.language,
        provider=transcript.provider,
        source_sha256=transcript.source_sha256,
        segments=segments,
        full_text=text,
        corrected=transcript.corrected,
    )


def write_srt(transcript: Transcript, path: Path) -> Path:
    lines: list[str] = []
    for index, segment in enumerate(transcript.segments, start=1):
        lines.append(str(index))
        lines.append(f"{format_ts(segment.start)} --> {format_ts(segment.end)}")
        lines.append(segment.text.strip())
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_vtt(transcript: Transcript, path: Path) -> Path:
    lines = ["WEBVTT", ""]
    for segment in transcript.segments:
        lines.append(f"{format_vtt(segment.start)} --> {format_vtt(segment.end)}")
        lines.append(segment.text.strip())
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_markdown(transcript: Transcript, path: Path) -> Path:
    body = transcript.full_text.strip() or "\n".join(s.text for s in transcript.segments)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# Transcript\n\n{body}\n", encoding="utf-8")
    return path
