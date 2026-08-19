"""Pydantic domain contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from quackvideo.domain.enums import (
    AspectRatio,
    ContentProfile,
    MomentStatus,
    PipelineStage,
    PlatformName,
)


def utcnow() -> datetime:
    return datetime.now(UTC)


class SourceAsset(BaseModel):
    path: Path
    sha256: str
    content_type: str
    size_bytes: int
    original_name: str


class ProbeStream(BaseModel):
    index: int
    codec_type: str
    codec_name: str | None = None
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    sample_rate: int | None = None
    channels: int | None = None
    bit_rate: int | None = None


class ProbeResult(BaseModel):
    path: Path
    duration: float = 0.0
    format_name: str | None = None
    size_bytes: int | None = None
    bit_rate: int | None = None
    streams: list[ProbeStream] = Field(default_factory=list)

    @property
    def video(self) -> ProbeStream | None:
        return next((s for s in self.streams if s.codec_type == "video"), None)

    @property
    def audio(self) -> ProbeStream | None:
        return next((s for s in self.streams if s.codec_type == "audio"), None)

    @property
    def has_video(self) -> bool:
        return self.video is not None

    @property
    def has_audio(self) -> bool:
        return self.audio is not None


class QcIssue(BaseModel):
    code: str
    severity: str
    message: str
    timestamp: float | None = None


class QcReport(BaseModel):
    duration: float
    has_video: bool
    has_audio: bool
    black_frames: list[tuple[float, float]] = Field(default_factory=list)
    silence_ranges: list[tuple[float, float]] = Field(default_factory=list)
    issues: list[QcIssue] = Field(default_factory=list)
    blocking: bool = False


class TranscriptWord(BaseModel):
    start: float
    end: float
    text: str


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str
    speaker: str | None = None
    words: list[TranscriptWord] = Field(default_factory=list)


class Transcript(BaseModel):
    language: str = "en"
    provider: str
    source_sha256: str
    segments: list[TranscriptSegment] = Field(default_factory=list)
    full_text: str = ""
    corrected: bool = False


class Chapter(BaseModel):
    index: int
    start: float
    end: float
    title: str
    summary: str = ""


class MomentScores(BaseModel):
    hook: float = 0.0
    standalone: float = 0.0
    novelty: float = 0.0
    density: float = 0.0
    platform_fit: float = 0.0
    prior_performance: float = 0.0

    @property
    def total(self) -> float:
        return round(
            0.25 * self.hook
            + 0.2 * self.standalone
            + 0.15 * self.novelty
            + 0.15 * self.density
            + 0.15 * self.platform_fit
            + 0.1 * self.prior_performance,
            4,
        )


class Moment(BaseModel):
    moment_id: str
    start: float
    end: float
    title: str
    hook: str
    rationale: str
    tags: list[str] = Field(default_factory=list)
    scores: MomentScores = Field(default_factory=MomentScores)
    status: MomentStatus = MomentStatus.PENDING
    notes: str = ""

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


class ReviewManifest(BaseModel):
    episode_id: str
    moments: list[Moment] = Field(default_factory=list)
    transcript_approved: bool = False
    updated_at: datetime = Field(default_factory=utcnow)

    def by_id(self, moment_id: str) -> Moment:
        for moment in self.moments:
            if moment.moment_id == moment_id:
                return moment
        raise KeyError(moment_id)


class PlatformPreset(BaseModel):
    name: PlatformName
    aspect: AspectRatio
    max_duration: float
    width: int
    height: int
    burn_captions: bool = True
    include_audio_only: bool = False


class PlatformPackage(BaseModel):
    platform: PlatformName
    directory: Path
    media_files: list[Path] = Field(default_factory=list)
    caption_files: list[Path] = Field(default_factory=list)
    title: str = ""
    hook: str = ""
    description: str = ""
    hashtags: list[str] = Field(default_factory=list)


class PerformanceSignal(BaseModel):
    moment_id: str
    platform: PlatformName | None = None
    views: int = 0
    retention_3s: float | None = None
    retention_30s: float | None = None
    ctr: float | None = None
    comments: int = 0


class StageRecord(BaseModel):
    stage: PipelineStage
    status: str
    finished_at: datetime | None = None
    input_hash: str | None = None
    artifact_paths: list[str] = Field(default_factory=list)
    message: str = ""


class EpisodeState(BaseModel):
    episode_id: str
    profile: ContentProfile
    title: str
    created_at: datetime = Field(default_factory=utcnow)
    source: SourceAsset | None = None
    probe: ProbeResult | None = None
    stages: dict[str, StageRecord] = Field(default_factory=dict)
    extra: dict[str, Any] = Field(default_factory=dict)


class ProjectConfig(BaseModel):
    name: str = "quackvideo"
    workspace: Path = Field(default_factory=lambda: Path("workspace"))
    default_profile: ContentProfile = ContentProfile.TALKING_HEAD
    platforms: list[PlatformName] = Field(
        default_factory=lambda: [
            PlatformName.YOUTUBE,
            PlatformName.YOUTUBE_SHORTS,
            PlatformName.TIKTOK,
            PlatformName.LINKEDIN,
        ]
    )
    language: str = "en"
    transcription_provider: str = "fake"
    analysis_provider: str = "heuristic"
    ffmpeg_timeout_sec: float = 600.0

    @field_validator("workspace", mode="before")
    @classmethod
    def coerce_workspace(cls, value: Path | str) -> Path:
        return Path(value)
