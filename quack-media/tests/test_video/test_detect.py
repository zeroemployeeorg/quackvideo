# quack-media/tests_video/test_detect.py

import pytest
import numpy as np
from pathlib import Path

from quackmedia.video import keyframes, scene_changes
from quackmedia.errors import InvalidInput


def test_keyframes_basic(small_synth_video):
    """Test basic keyframe extraction functionality."""
    keyframe_results = list(keyframes(small_synth_video))

    assert len(keyframe_results) > 0, "Should extract at least some keyframes"

    # Check structure of results
    for timestamp, frame in keyframe_results:
        assert isinstance(timestamp, float)
        assert timestamp >= 0.0
        assert isinstance(frame, np.ndarray)
        assert frame.shape == (240, 320, 3)  # height, width, channels
        assert frame.dtype == np.uint8


def test_keyframes_timestamps_ordered(small_synth_video):
    """Test that keyframe timestamps are in ascending order."""
    keyframe_results = list(keyframes(small_synth_video))

    if len(keyframe_results) > 1:
        timestamps = [timestamp for timestamp, _ in keyframe_results]
        assert timestamps == sorted(timestamps), "Timestamps should be in ascending order"


def test_keyframes_nonexistent_file():
    """Test keyframe extraction from non-existent file."""
    with pytest.raises(FileNotFoundError):
        list(keyframes(Path("nonexistent.mp4")))


def test_scene_changes_basic(small_synth_video):
    """Test basic scene change detection functionality."""
    scene_results = list(scene_changes(small_synth_video, threshold=0.3))

    # Note: synthetic videos may not have many scene changes
    # We mainly test that the function runs without error
    assert isinstance(scene_results, list)

    # If there are scene changes, check their structure
    for timestamp, frame in scene_results:
        assert isinstance(timestamp, float)
        assert timestamp >= 0.0
        assert isinstance(frame, np.ndarray)
        assert frame.shape == (240, 320, 3)
        assert frame.dtype == np.uint8


def test_scene_changes_different_thresholds(small_synth_video):
    """Test scene change detection with different thresholds."""
    # Lower threshold should detect more changes
    low_threshold_results = list(scene_changes(small_synth_video, threshold=0.1))
    high_threshold_results = list(scene_changes(small_synth_video, threshold=0.8))

    # Lower threshold should detect at least as many changes as higher threshold
    assert len(low_threshold_results) >= len(high_threshold_results)


def test_scene_changes_invalid_threshold(small_synth_video):
    """Test that invalid thresholds raise InvalidInput."""
    # Threshold too low
    with pytest.raises(InvalidInput):
        list(scene_changes(small_synth_video, threshold=-0.1))

    # Threshold too high
    with pytest.raises(InvalidInput):
        list(scene_changes(small_synth_video, threshold=1.5))


def test_scene_changes_timestamps_ordered(small_synth_video):
    """Test that scene change timestamps are in ascending order."""
    scene_results = list(scene_changes(small_synth_video, threshold=0.2))

    if len(scene_results) > 1:
        timestamps = [timestamp for timestamp, _ in scene_results]
        assert timestamps == sorted(timestamps), "Timestamps should be in ascending order"


def test_scene_changes_nonexistent_file():
    """Test scene change detection from non-existent file."""
    with pytest.raises(FileNotFoundError):
        list(scene_changes(Path("nonexistent.mp4")))


def test_keyframes_vs_scene_changes(small_synth_video):
    """Compare keyframes and scene changes for basic sanity."""
    keyframe_results = list(keyframes(small_synth_video))
    scene_results = list(scene_changes(small_synth_video, threshold=0.5))

    # Both should return valid iterables (even if empty for synthetic videos)
    assert isinstance(keyframe_results, list)
    assert isinstance(scene_results, list)

    # All timestamps should be within video duration (approximately)
    for timestamp, _ in keyframe_results + scene_results:
        assert 0.0 <= timestamp <= 4.0  # Video is ~3s, allow some tolerance


def test_streaming_behavior(tiny_synth_video):
    """Test that detection functions work as iterators (streaming)."""
    # Test that we can iterate without loading everything into memory
    keyframe_count = 0
    for timestamp, frame in keyframes(tiny_synth_video):
        keyframe_count += 1
        # Verify we get frames as we iterate
        assert isinstance(frame, np.ndarray)
        if keyframe_count >= 3:  # Stop after a few to test streaming
            break

    scene_count = 0
    for timestamp, frame in scene_changes(tiny_synth_video, threshold=0.3):
        scene_count += 1
        assert isinstance(frame, np.ndarray)
        if scene_count >= 2:  # Stop after a few
            break