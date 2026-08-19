"""Media package."""

from quackvideo.media.engine import FFmpegEngine
from quackvideo.media.errors import MediaError, OperationFailed, ToolNotFound

__all__ = ["FFmpegEngine", "MediaError", "OperationFailed", "ToolNotFound"]
