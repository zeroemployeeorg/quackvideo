# quack-media/tests_video/test_init_imports.py

"""Test that all imports work correctly after refactoring."""

import pytest


def test_main_package_imports():
    """Test that main package imports work."""
    from quackmedia import (
        QuackMediaError,
        ToolNotFound,
        InvalidInput,
        OperationFailed,
        VideoProbeResult,
        ExtractFramesResult,
        video
    )

    # Basic sanity checks
    assert issubclass(ToolNotFound, QuackMediaError)
    assert issubclass(InvalidInput, QuackMediaError)
    assert issubclass(OperationFailed, QuackMediaError)


def test_video_module_imports():
    """Test that video module imports work."""
    from quackmedia.video import (
        probe,
        read_frames,
        extract_frame_at,
        write_video,
        slice_video,
        extract_frames,
        extract_audio,
        transcode,
        keyframes,
        scene_changes
    )

    # All should be callable
    assert callable(probe)
    assert callable(read_frames)
    assert callable(extract_frame_at)
    assert callable(write_video)
    assert callable(slice_video)
    assert callable(extract_frames)
    assert callable(extract_audio)
    assert callable(transcode)
    assert callable(keyframes)
    assert callable(scene_changes)


def test_video_io_imports():
    """Test that video.io module works."""
    from quackmedia.video.io import probe, read_frames, extract_frame_at, write_video

    assert callable(probe)
    assert callable(read_frames)
    assert callable(extract_frame_at)
    assert callable(write_video)


def test_video_ops_imports():
    """Test that video.ops module works."""
    from quackmedia.video.ops import slice_video, extract_frames, extract_audio, transcode

    assert callable(slice_video)
    assert callable(extract_frames)
    assert callable(extract_audio)
    assert callable(transcode)


def test_video_detect_imports():
    """Test that video.detect module works."""
    from quackmedia.video.detect import keyframes, scene_changes

    assert callable(keyframes)
    assert callable(scene_changes)


def test_synthetic_imports():
    """Test that synthetic generators still work."""
    from quackmedia.video.synthetic.video import VideoGenerator, VideoConfig
    from quackmedia.video.synthetic.audio import AudioGenerator, AudioConfig

    # Test that we can create instances
    video_config = VideoConfig(duration=1.0, fps=10, width=64, height=64)
    audio_config = AudioConfig(duration=1.0)

    assert isinstance(video_config, VideoConfig)
    assert isinstance(audio_config, AudioConfig)


def test_error_inheritance():
    """Test that error inheritance works correctly."""
    from quackmedia.errors import QuackMediaError, OperationFailed
    from quackmedia.video.core.operations.base import FFmpegOperationError

    # Legacy errors should still work
    assert issubclass(FFmpegOperationError, Exception)

    # New errors should inherit from QuackMediaError
    assert issubclass(OperationFailed, QuackMediaError)