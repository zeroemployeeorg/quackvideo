from pathlib import Path

from quackvideo.analysis.captions import format_ts, slice_transcript, write_srt
from quackvideo.analysis.moments import chapters_from_transcript, rank_moments
from quackvideo.domain.enums import ContentProfile
from quackvideo.domain.models import Transcript, TranscriptSegment


def _transcript() -> Transcript:
    return Transcript(
        provider="fake",
        source_sha256="abc",
        segments=[
            TranscriptSegment(start=0, end=12, text="Why AI agents fail in production."),
            TranscriptSegment(start=12, end=28, text="Build the transcript first."),
            TranscriptSegment(start=28, end=50, text="Never skip the human review gate."),
        ],
        full_text="Why AI agents fail in production. Build the transcript first. Never skip the human review gate.",
    )


def test_rank_moments_returns_scored_clips() -> None:
    moments = rank_moments(_transcript(), ContentProfile.TALKING_HEAD)
    assert moments
    assert moments[0].end > moments[0].start
    assert moments[0].scores.total >= 0


def test_chapters_cover_timeline() -> None:
    chapters = chapters_from_transcript(_transcript(), max_chapters=4)
    assert chapters[0].start == 0
    assert chapters[-1].end >= 50


def test_srt_roundtrip(tmp_path: Path) -> None:
    path = write_srt(_transcript(), tmp_path / "t.srt")
    text = path.read_text(encoding="utf-8")
    assert "-->" in text
    assert format_ts(1.5) == "00:00:01,500"


def test_slice_transcript_offsets() -> None:
    sliced = slice_transcript(_transcript(), 12, 28)
    assert sliced.segments
    assert sliced.segments[0].start == 0
    assert "transcript" in sliced.full_text.lower() or sliced.full_text
