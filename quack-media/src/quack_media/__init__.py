# quack-media/__init__.py

"""
QuackMedia - A unified media processing library.

This package provides a clean, consistent API for video, audio, and image processing
using FFmpeg and other media tools.
"""

__version__ = "0.1.0"

# Re-export common error types
from .errors import (
    QuackMediaError,
    ToolNotFound,
    InvalidInput,
    OperationFailed,
    Timeout,
)

# Re-export common result types
from .results import (
    MediaOpResult,
    VideoProbeResult,
    ExtractFramesResult,
    SliceResult,
    AudioExtractResult,
    WriteResult,
)

# Video processing is the main module for now
from . import video

__all__ = [
    # Core errors
    "QuackMediaError",
    "ToolNotFound",
    "InvalidInput",
    "OperationFailed",
    "Timeout",

    # Core results
    "MediaOpResult",
    "VideoProbeResult",
    "ExtractFramesResult",
    "SliceResult",
    "AudioExtractResult",
    "WriteResult",

    # Modules
    "video",
]