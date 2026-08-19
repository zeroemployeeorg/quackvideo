"""FFmpeg errors."""


class MediaError(Exception):
    """Media pipeline failure."""


class ToolNotFound(MediaError):
    """ffmpeg or ffprobe missing from PATH."""


class OperationFailed(MediaError):
    def __init__(self, message: str, stderr: str = "") -> None:
        super().__init__(message)
        self.stderr = stderr
