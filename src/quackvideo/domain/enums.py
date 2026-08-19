"""Shared enumerations."""

from enum import StrEnum


class ContentProfile(StrEnum):
    PODCAST = "podcast"
    TALKING_HEAD = "talking-head"
    TUTORIAL = "tutorial"
    SOCIAL = "social"


class PipelineStage(StrEnum):
    INGEST = "ingest"
    NORMALIZE = "normalize"
    TRANSCRIBE = "transcribe"
    ANALYZE = "analyze"
    REVIEW = "review"
    COMPOSE = "compose"
    PACKAGE = "package"


class MomentStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PlatformName(StrEnum):
    YOUTUBE = "youtube"
    YOUTUBE_SHORTS = "youtube-shorts"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    X = "x"
    PODCAST = "podcast"


class AspectRatio(StrEnum):
    LANDSCAPE = "16:9"
    SQUARE = "1:1"
    VERTICAL = "9:16"


class ReviewDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    RETIME = "retime"
