# quack-media/tests_video/test_write_and_slice.py

import pytest
import numpy as np
from pathlib import Path

from quackmedia.video import write_video, slice_video, probe, read_frames
from quackmedia.errors import InvalidInput


def test_write_video_basic(temp_output_dir):
    """Test basic video writing functionality."""
    # Create some simple test frames
    frames = []
    for i in range(30):  # 30 frames = 1 second at 30fps
        frame = np.full((100, 100, 3), i * 8, dtype=np.uint8)  # Gradient effect
        frames.append(frame)

    output_path = temp_output_dir / "test_output.mp4"
    result = write_video(frames, output_path, fps=30.0)

    assert result.output == output_path
    assert result.frame_count == 30
    assert result.duration == pytest.approx(1.0, abs=0.1)
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_write_video_empty_frames(temp_output_dir):
    """Test that writing empty frames raises InvalidInput."""
    output_path = temp_output_dir / "empty.mp4"

    with pytest.raises(InvalidInput):
        write_video([], output_path)


def test_write_video_inconsistent_dimensions(temp_output_dir):
    """Test that inconsistent frame dimensions raise InvalidInput."""
    frames = [
        np.zeros((100, 100, 3), dtype=np.uint8),
        np.zeros((200, 100, 3), dtype=np.uint8),  # Different height
    ]
    output_path = temp_output_dir / "inconsistent.mp4"

    with pytest.raises(InvalidInput):
        write_video(frames, output_path)


def test_write_video_different_codecs(temp_output_dir):
    """Test writing video with different codec settings."""
    frames = [np.full((50, 50, 3), 128, dtype=np.uint8) for _ in range(10)]

    # Test different codec
    output_path = temp_output_dir / "h264.mp4"
    result = write_video(frames, output_path, codec="libx264", crf=30)

    assert result.output.exists()
    assert result.frame_count == 10


def test_slice_video_basic(small_synth_video, temp_output_dir):
    """Test basic video slicing functionality."""
    output_path = temp_output_dir / "sliced.mp4"

    result = slice_video(small_synth_video, output_path, start=0.5, end=2.0)

    assert result.input == small_synth_video
    assert result.output == output_path
    assert result.start == 0.5
    assert result.end == 2.0
    assert output_path.exists()
    assert output_path.stat().st_size > 0

    # Verify the sliced video has approximately correct duration
    sliced_metadata = probe(output_path)
    assert sliced_metadata.duration == pytest.approx(1.5, abs=0.2)  # 2.0 - 0.5 = 1.5s


def test_slice_video_with_reencode(small_synth_video, temp_output_dir):
    """Test video slicing with re-encoding."""
    output_path = temp_output_dir / "sliced_reencoded.mp4"

    result = slice_video(small_synth_video, output_path, start=0.0, end=1.0, reencode=True)

    assert result.output.exists()

    # Verify duration
    sliced_metadata = probe(output_path)
    assert sliced_metadata.duration == pytest.approx(1.0, abs=0.2)


def test_slice_video_invalid_times(small_synth_video, temp_output_dir):
    """Test that invalid time ranges raise InvalidInput."""
    output_path = temp_output_dir / "invalid.mp4"

    # End time before start time
    with pytest.raises(InvalidInput):
        slice_video(small_synth_video, output_path, start=2.0, end=1.0)

    # Equal start and end times
    with pytest.raises(InvalidInput):
        slice_video(small_synth_video, output_path, start=1.0, end=1.0)


def test_slice_video_nonexistent_input(temp_output_dir):
    """Test slicing non-existent video file."""
    output_path = temp_output_dir / "output.mp4"

    with pytest.raises(FileNotFoundError):
        slice_video(Path("nonexistent.mp4"), output_path, start=0.0, end=1.0)


def test_slice_video_overwrite_protection(small_synth_video, temp_output_dir):
    """Test that existing output files are protected when overwrite=False."""
    output_path = temp_output_dir / "existing.mp4"

    # Create an existing file
    output_path.write_text("existing content")

    # Should raise error when overwrite=False (default)
    with pytest.raises(InvalidInput):
        slice_video(small_synth_video, output_path, start=0.0, end=1.0, overwrite=False)

    # Should work when overwrite=True
    result = slice_video(small_synth_video, output_path, start=0.0, end=1.0, overwrite=True)
    assert result.output.exists()


def test_roundtrip_read_write(small_synth_video, temp_output_dir):
    """Test reading frames and writing them back."""
    # Read frames from original video
    frames = list(read_frames(small_synth_video, fps=5.0))  # Lower fps for speed

    # Write frames to new video
    output_path = temp_output_dir / "roundtrip.mp4"
    result = write_video(frames, output_path, fps=5.0)

    assert result.output.exists()
    assert result.frame_count == len(frames)

    # Verify the new video is readable
    new_metadata = probe(output_path)
    assert new_metadata.width == 320
    assert new_metadata.height == 240