"""Profile and platform policies."""

from quackvideo.domain.enums import AspectRatio, ContentProfile, PlatformName
from quackvideo.domain.models import PlatformPreset

PLATFORM_PRESETS: dict[PlatformName, PlatformPreset] = {
    PlatformName.YOUTUBE: PlatformPreset(
        name=PlatformName.YOUTUBE,
        aspect=AspectRatio.LANDSCAPE,
        max_duration=12 * 60 * 60,
        width=1920,
        height=1080,
        burn_captions=False,
    ),
    PlatformName.YOUTUBE_SHORTS: PlatformPreset(
        name=PlatformName.YOUTUBE_SHORTS,
        aspect=AspectRatio.VERTICAL,
        max_duration=60,
        width=1080,
        height=1920,
    ),
    PlatformName.TIKTOK: PlatformPreset(
        name=PlatformName.TIKTOK,
        aspect=AspectRatio.VERTICAL,
        max_duration=180,
        width=1080,
        height=1920,
    ),
    PlatformName.INSTAGRAM: PlatformPreset(
        name=PlatformName.INSTAGRAM,
        aspect=AspectRatio.VERTICAL,
        max_duration=90,
        width=1080,
        height=1920,
    ),
    PlatformName.LINKEDIN: PlatformPreset(
        name=PlatformName.LINKEDIN,
        aspect=AspectRatio.SQUARE,
        max_duration=180,
        width=1080,
        height=1080,
        burn_captions=True,
    ),
    PlatformName.X: PlatformPreset(
        name=PlatformName.X,
        aspect=AspectRatio.LANDSCAPE,
        max_duration=140,
        width=1280,
        height=720,
        burn_captions=True,
    ),
    PlatformName.PODCAST: PlatformPreset(
        name=PlatformName.PODCAST,
        aspect=AspectRatio.LANDSCAPE,
        max_duration=12 * 60 * 60,
        width=1920,
        height=1080,
        burn_captions=False,
        include_audio_only=True,
    ),
}

PROFILE_PLATFORMS: dict[ContentProfile, list[PlatformName]] = {
    ContentProfile.PODCAST: [
        PlatformName.PODCAST,
        PlatformName.YOUTUBE,
        PlatformName.YOUTUBE_SHORTS,
        PlatformName.LINKEDIN,
    ],
    ContentProfile.TALKING_HEAD: [
        PlatformName.YOUTUBE,
        PlatformName.YOUTUBE_SHORTS,
        PlatformName.TIKTOK,
        PlatformName.LINKEDIN,
    ],
    ContentProfile.TUTORIAL: [
        PlatformName.YOUTUBE,
        PlatformName.LINKEDIN,
        PlatformName.YOUTUBE_SHORTS,
    ],
    ContentProfile.SOCIAL: [
        PlatformName.TIKTOK,
        PlatformName.YOUTUBE_SHORTS,
        PlatformName.INSTAGRAM,
        PlatformName.X,
    ],
}

CLIP_WINDOW: dict[ContentProfile, tuple[float, float]] = {
    ContentProfile.PODCAST: (20.0, 90.0),
    ContentProfile.TALKING_HEAD: (15.0, 60.0),
    ContentProfile.TUTORIAL: (20.0, 90.0),
    ContentProfile.SOCIAL: (8.0, 45.0),
}

DEFAULT_CLIP_COUNT: dict[ContentProfile, int] = {
    ContentProfile.PODCAST: 5,
    ContentProfile.TALKING_HEAD: 6,
    ContentProfile.TUTORIAL: 5,
    ContentProfile.SOCIAL: 8,
}
