# quack-media/video/detect.py

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterator, Tuple
import numpy as np
import ffmpeg

from ..errors import OperationFailed, ToolNotFound, InvalidInput
from .io import probe, read_frames
from .core.utils import FrameComparisonConfig, detect_scene_change

logger = logging.getLogger(__name__)


def keyframes(input_path: Path) -> Iterator[Tuple[float, np.ndarray]]:
    """Extract keyframes from video."""
    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Video file not found: {input_path}")

    # Get video metadata for FPS
    metadata = probe(input_path)

    try:
        # Use ffmpeg to select only keyframes
        stream = (
            ffmpeg.input(str(input_path))
            .filter("select", "key")
            .output("pipe:", format="rawvideo", pix_fmt="rgb24")
            .overwrite_output()
        )

        process = stream.run_async(pipe_stdout=True, pipe_stderr=True)
        width = metadata.width
        height = metadata.height
        frame_size = width * height * 3
        timestamp = 0.0

        try:
            while True:
                in_bytes = process.stdout.read(frame_size)
                if not in_bytes:
                    break
                frame = np.frombuffer(in_bytes, np.uint8).reshape((height, width, 3))
                yield timestamp, frame
                # Approximate timestamp increment (keyframes are not uniformly spaced)
                timestamp += 1.0 / metadata.fps

            process.wait()
            if process.returncode != 0:
                stderr = process.stderr.read().decode() if process.stderr else "No error output"
                raise OperationFailed(f"FFmpeg process failed: {stderr}", ffmpeg_error=stderr)

        finally:
            try:
                if process.stdout:
                    process.stdout.close()
                if process.stderr:
                    process.stderr.close()
                if process.poll() is None:
                    process.terminate()
            except Exception:
                pass

    except ffmpeg.Error as e:
        stderr = e.stderr.decode() if e.stderr else "No stderr available"
        if "ffmpeg" in str(e) and "not found" in str(e):
            raise ToolNotFound("ffmpeg not found on PATH")
        else:
            raise OperationFailed(f"Keyframe extraction failed: {stderr}", ffmpeg_error=stderr)
    except FileNotFoundError:
        raise ToolNotFound("ffmpeg not found on PATH")


def scene_changes(input_path: Path, threshold: float = 0.3) -> Iterator[Tuple[float, np.ndarray]]:
    """Detect scene changes in video using streaming comparison."""
    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Video file not found: {input_path}")

    if not 0 <= threshold <= 1:
        raise InvalidInput("Threshold must be between 0 and 1")

    # Get video metadata for FPS
    metadata = probe(input_path)

    # Create frame comparison config
    config = FrameComparisonConfig(threshold=threshold)

    try:
        # Stream frames and compare with previous
        frame_iterator = read_frames(input_path)
        prev_frame = None
        frame_index = 0

        for frame in frame_iterator:
            timestamp = frame_index / metadata.fps

            if prev_frame is not None:
                # Detect scene change between previous and current frame
                if detect_scene_change(prev_frame, frame, config=config):
                    yield timestamp, frame

            prev_frame = frame
            frame_index += 1

    except Exception as e:
        if isinstance(e, (OperationFailed, ToolNotFound, FileNotFoundError)):
            raise
        else:
            raise OperationFailed(f"Scene change detection failed: {str(e)}")