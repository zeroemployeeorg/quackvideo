# quack-media/tests_video/test_probe_and_read.py

import pytest
import numpy as np
from pathlib import Path

from quackmedia.video import probe, read_frames, extract_frame_at
from quackmedia.errors import QuackMediaError, ToolNotFound, InvalidInput


def test_probe_basic(small_synth_video):
    """Test basic video probing functionality."""
    result = probe(small_synth_video)

    assert result.input == small_synth_video
    assert result.duration == pytest.approx(3.0, abs=0.5)  # ~3 seconds with tolerance
    assert result.width == 320
    assert result.height == 240
    assert result.fps > 0
    assert result.codec is not None


def test_probe_nonexistent_file():
    """Test probing a non-existent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        probe(Path("nonexistent_file.mp4"))


def test_read_frames_basic(small_synth_video):
    """Test basic frame reading functionality."""
    frames = list(read_frames(small_synth_video))

    assert len(frames) > 0, "Should yield at least some frames"

    # Check frame properties
    first_frame = frames[0]
    assert isinstance(first_frame, np.ndarray)
    assert first_frame.shape == (240, 320, 3)  # height, width, channels
    assert first_frame.dtype == np.uint8


def test_read_frames_with_fps(small_synth_video):
    """Test frame reading with specific FPS."""
    # Read at 5 fps (should get about 15 frames for 3 second video)
    frames = list(read_frames(small_synth_video, fps=5.0))

    assert len(frames) > 10, "Should get reasonable number of frames at 5 fps"
    assert len(frames) < 20, "Shouldn't get too many frames"


def test_read_frames_with_time_range(small_synth_video):
    """Test frame reading with start/end times."""
    # Read middle 1 second
    frames = list(read_frames(small_synth_video, start=1.0, end=2.0, fps=10.0))

    assert len(frames) >= 8, "Should get about 10 frames for 1 second at 10fps"
    assert len(frames) <= 12, "Allow some tolerance in frame count"


def test_read_frames_with_resolution(small_synth_video):
    """Test frame reading with resolution scaling."""
    # Scale down to 160x120
    frames = list(read_frames(small_synth_video, resolution=(160, 120)))

    assert len(frames) > 0
    first_frame = frames[0]
    assert first_frame.shape == (120, 160, 3)  # height, width, channels


def test_read_frames_nonexistent_file():
    """Test reading frames from non-existent file."""
    with pytest.raises(FileNotFoundError):
        list(read_frames(Path("nonexistent.mp4")))


def test_extract_frame_at_basic(small_synth_video):
    """Test extracting a single frame at timestamp."""
    frame = extract_frame_at(small_synth_video, 1.0)  # 1 second mark

    assert isinstance(frame, np.ndarray)
    assert frame.shape == (240, 320, 3)
    assert frame.dtype == np.uint8


def test_extract_frame_at_zero(small_synth_video):
    """Test extracting frame at timestamp 0."""
    frame = extract_frame_at(small_synth_video, 0.0)

    assert isinstance(frame, np.ndarray)
    assert frame.shape == (240, 320, 3)


def test_extract_frame_at_negative_timestamp(small_synth_video):
    """Test that negative timestamps raise InvalidInput."""
    with pytest.raises(InvalidInput):
        extract_frame_at(small_synth_video, -1.0)


def test_extract_frame_at_nonexistent_file():
    """Test extracting frame from non-existent file."""
    with pytest.raises(FileNotFoundError):
        extract_frame_at(Path("nonexistent.mp4"), 1.0)