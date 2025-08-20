# quack-media/tests_video/test_extract_frames_and_audio.py

import pytest
from pathlib import Path

from quackmedia.video import extract_frames, extract_audio, transcode, probe
from quackmedia.errors import InvalidInput


def test_extract_frames_basic(small_synth_video, temp_output_dir):
    """Test basic frame extraction functionality."""
    frames_dir = temp_output_dir / "frames"

    result = extract_frames(small_synth_video, frames_dir, fps=2.0, format="png")

    assert result.input == small_synth_video
    assert result.output_dir == frames_dir
    assert result.total > 0
    assert len(result.frame_paths) == result.total

    # Check that frame files actually exist
    for frame_path in result.frame_paths:
        assert frame_path.exists()
        assert frame_path.stat().st_size > 0
        assert frame_path.suffix == ".png"


def test_extract_frames_different_fps(small_synth_video, temp_output_dir):
    """Test frame extraction with different FPS settings."""
    frames_dir = temp_output_dir / "frames_fps"

    # Extract at 1 fps (should get about 3 frames for 3 second video)
    result = extract_frames(small_synth_video, frames_dir, fps=1.0)

    assert result.total >= 2  # At least 2 frames
    assert result.total <= 4  # Not more than 4 frames

    # All frame files should exist
    frame_files = list(frames_dir.glob("frame_*.png"))
    assert len(frame_files) == result.total


def test_extract_frames_fractional_fps(small_synth_video, temp_output_dir):
    """Test frame extraction with fractional FPS (string format)."""
    frames_dir = temp_output_dir / "frames_frac"

    # Extract at 1/5 fps (one frame every 5 seconds, so should get 1 frame for 3s video)
    result = extract_frames(small_synth_video, frames_dir, fps="1/5")

    assert result.total >= 1

    # Check files exist
    frame_files = list(frames_dir.glob("frame_*.png"))
    assert len(frame_files) == result.total


def test_extract_frames_jpeg_format(small_synth_video, temp_output_dir):
    """Test frame extraction with JPEG format."""
    frames_dir = temp_output_dir / "frames_jpg"

    result = extract_frames(small_synth_video, frames_dir, fps=1.0, format="jpg")

    assert result.total > 0

    # Check JPEG files exist
    jpg_files = list(frames_dir.glob("frame_*.jpg"))
    assert len(jpg_files) == result.total

    for jpg_file in jpg_files:
        assert jpg_file.stat().st_size > 0


def test_extract_frames_nonexistent_input(temp_output_dir):
    """Test frame extraction from non-existent file."""
    frames_dir = temp_output_dir / "frames"

    with pytest.raises(FileNotFoundError):
        extract_frames(Path("nonexistent.mp4"), frames_dir)


def test_extract_audio_basic(small_synth_video, temp_output_dir):
    """Test basic audio extraction functionality."""
    audio_path = temp_output_dir / "extracted.flac"

    result = extract_audio(small_synth_video, audio_path, format="flac")

    assert result.input == small_synth_video
    assert result.output == audio_path
    assert result.format == "flac"
    assert audio_path.exists()
    assert audio_path.stat().st_size > 0

    # Duration should be approximately the same as video
    if result.duration is not None:
        assert result.duration == pytest.approx(3.0, abs=0.5)


def test_extract_audio_different_formats(small_synth_video, temp_output_dir):
    """Test audio extraction with different formats."""
    formats_to_test = ["wav", "mp3", "aac"]

    for fmt in formats_to_test:
        audio_path = temp_output_dir / f"extracted.{fmt}"

        result = extract_audio(small_synth_video, audio_path, format=fmt)

        assert result.format == fmt
        assert audio_path.exists()
        assert audio_path.stat().st_size > 0


def test_extract_audio_nonexistent_input(temp_output_dir):
    """Test audio extraction from non-existent file."""
    audio_path = temp_output_dir / "extracted.flac"

    with pytest.raises(FileNotFoundError):
        extract_audio(Path("nonexistent.mp4"), audio_path)


def test_transcode_basic(small_synth_video, temp_output_dir):
    """Test basic video transcoding functionality."""
    output_path = temp_output_dir / "transcoded.mp4"

    result = transcode(
        small_synth_video,
        output_path,
        vcodec="libx264",
        acodec="aac",
        crf=30,  # Higher CRF for faster encoding
        preset="fast"
    )

    assert result.ok is True
    assert "input" in result.meta
    assert "output" in result.meta
    assert output_path.exists()
    assert output_path.stat().st_size > 0

    # Verify the transcoded video is readable
    transcoded_metadata = probe(output_path)
    assert transcoded_metadata.width == 320
    assert transcoded_metadata.height == 240


def test_transcode_overwrite_protection(small_synth_video, temp_output_dir):
    """Test transcode overwrite protection."""
    output_path = temp_output_dir / "existing.mp4"

    # Create existing file
    output_path.write_text("existing content")

    # Should fail with overwrite=False
    with pytest.raises(InvalidInput):
        transcode(small_synth_video, output_path, overwrite=False)

    # Should work with overwrite=True
    result = transcode(small_synth_video, output_path, overwrite=True)
    assert result.ok is True
    assert output_path.exists()


def test_transcode_nonexistent_input(temp_output_dir):
    """Test transcoding non-existent file."""
    output_path = temp_output_dir / "output.mp4"

    with pytest.raises(FileNotFoundError):
        transcode(Path("nonexistent.mp4"), output_path)