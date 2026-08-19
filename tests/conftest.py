from pathlib import Path

import pytest

from quackvideo.media.engine import FFmpegEngine


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def ffmpeg_engine() -> FFmpegEngine:
    return FFmpegEngine()


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "requires_ffmpeg: needs ffmpeg/ffprobe")
