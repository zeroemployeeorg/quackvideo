# quack-media/tests_video/conftest.py

import pytest
import tempfile
from pathlib import Path

from quackmedia.video.synthetic.video import VideoGenerator, VideoConfig
from quackmedia.video.synthetic.audio import AudioGenerator, AudioConfig


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def small_synth_video(temp_output_dir):
    """Generate a small synthetic video for testing."""
    config = VideoConfig(
        duration=3.0,  # 3 seconds
        fps=10,        # 10 fps for faster processing
        width=320,     # Small resolution
        height=240,
        pattern="color_bars"
    )
    generator = VideoGenerator(config)
    output_path = temp_output_dir / "test_video.mp4"
    return generator.generate(output_path)


@pytest.fixture
def small_synth_audio(temp_output_dir):
    """Generate a small synthetic audio for testing."""
    config = AudioConfig(
        duration=2.0,  # 2 seconds
        sample_rate=8000,  # Lower sample rate for speed
        pattern="sine",
        frequency=440.0
    )
    generator = AudioGenerator(config)
    output_path = temp_output_dir / "test_audio.wav"
    return generator.generate(output_path)


@pytest.fixture
def tiny_synth_video(temp_output_dir):
    """Generate a very small synthetic video for quick tests."""
    config = VideoConfig(
        duration=1.0,  # 1 second
        fps=5,         # 5 fps
        width=64,      # Very small resolution
        height=36,
        pattern="gradient"
    )
    generator = VideoGenerator(config)
    output_path = temp_output_dir / "tiny_video.mp4"
    return generator.generate(output_path)