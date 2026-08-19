from pathlib import Path

import pytest

from quackvideo.media.engine import FFmpegEngine
from quackvideo.media.errors import ToolNotFound


def test_engine_unavailable_raises() -> None:
    engine = FFmpegEngine(ffmpeg_bin="", ffprobe_bin="")
    assert engine.available() is False
    with pytest.raises(ToolNotFound):
        engine.require()


def test_probe_missing_file(tmp_path: Path) -> None:
    engine = FFmpegEngine()
    if not engine.available():
        return
    from quackvideo.media.errors import OperationFailed

    with pytest.raises(OperationFailed):
        engine.probe(tmp_path / "missing.mp4")
