# quack-media/video/io.py

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterator, Iterable
import numpy as np
import ffmpeg

from ..results import VideoProbeResult, WriteResult
from ..errors import OperationFailed, ToolNotFound, InvalidInput

logger = logging.getLogger(__name__)


def probe(input_path: Path) -> VideoProbeResult:
    """Probe video file for metadata."""
    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Video file not found: {input_path}")

    try:
        probe_result = ffmpeg.probe(str(input_path))
        video_stream = next(
            (
                stream
                for stream in probe_result["streams"]
                if stream["codec_type"] == "video"
            ),
            None,
        )
        if not video_stream:
            raise InvalidInput("No video stream found")

        # Calculate FPS from frame rate fraction
        fps_num, fps_den = map(int, video_stream["r_frame_rate"].split("/"))
        fps = fps_num / fps_den

        return VideoProbeResult(
            input=input_path,
            duration=float(probe_result["format"]["duration"]),
            fps=fps,
            width=int(video_stream["width"]),
            height=int(video_stream["height"]),
            bitrate=int(probe_result["format"].get("bit_rate", 0)) if probe_result["format"].get("bit_rate") else None,
            codec=video_stream["codec_name"],
            size_bytes=int(probe_result["format"]["size"]) if probe_result["format"].get("size") else None,
        )
    except ffmpeg.Error as e:
        stderr = e.stderr.decode() if e.stderr else "No stderr available"
        if "No such file or directory" in stderr:
            raise FileNotFoundError(f"Video file not found: {input_path}")
        elif "ffprobe" in str(e) and "not found" in str(e):
            raise ToolNotFound("ffprobe not found on PATH")
        else:
            raise OperationFailed(
                f"Failed to probe video metadata: {stderr}",
                ffmpeg_error=stderr
            )
    except FileNotFoundError:
        raise ToolNotFound("ffprobe not found on PATH")


def read_frames(
        input_path: Path,
        fps: float | None = None,
        start: float | None = None,
        end: float | None = None,
        resolution: tuple[int, int] | None = None
) -> Iterator[np.ndarray]:
    """Read video frames as numpy arrays."""
    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Video file not found: {input_path}")

    # Get video metadata to determine dimensions
    metadata = probe(input_path)
    width = resolution[0] if resolution else metadata.width
    height = resolution[1] if resolution else metadata.height

    try:
        # Build ffmpeg stream
        stream = ffmpeg.input(str(input_path))

        if start is not None:
            stream = stream.filter("setpts", f"PTS-{start}/TB")

        if fps is not None:
            stream = stream.filter("fps", fps=fps)

        if resolution is not None:
            stream = stream.filter("scale", resolution[0], resolution[1])

        if end is not None and start is not None:
            duration = end - start
            stream = stream.filter("trim", duration=duration)

        stream = stream.output(
            "pipe:", format="rawvideo", pix_fmt="rgb24"
        ).overwrite_output()

        # Start ffmpeg process
        process = stream.run_async(pipe_stdout=True, pipe_stderr=True)

        try:
            while True:
                in_bytes = process.stdout.read(width * height * 3)
                if not in_bytes:
                    break
                yield np.frombuffer(in_bytes, np.uint8).reshape((height, width, 3))

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
            raise OperationFailed(f"Frame reading failed: {stderr}", ffmpeg_error=stderr)
    except FileNotFoundError:
        raise ToolNotFound("ffmpeg not found on PATH")


def extract_frame_at(input_path: Path, timestamp: float) -> np.ndarray:
    """Extract a single frame at the specified timestamp."""
    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Video file not found: {input_path}")

    if timestamp < 0:
        raise InvalidInput("Timestamp must be non-negative")

    # Get video metadata for dimensions
    metadata = probe(input_path)

    try:
        stream = (
            ffmpeg.input(str(input_path), ss=timestamp)
            .output("pipe:", format="rawvideo", pix_fmt="rgb24", vframes=1)
            .overwrite_output()
        )

        out, _ = stream.run(capture_stdout=True, capture_stderr=True)
        return np.frombuffer(out, np.uint8).reshape(
            (metadata.height, metadata.width, 3)
        )
    except ffmpeg.Error as e:
        stderr = e.stderr.decode() if e.stderr else "No stderr available"
        if "ffmpeg" in str(e) and "not found" in str(e):
            raise ToolNotFound("ffmpeg not found on PATH")
        else:
            raise OperationFailed(f"Failed to extract frame: {stderr}", ffmpeg_error=stderr)
    except FileNotFoundError:
        raise ToolNotFound("ffmpeg not found on PATH")


def write_video(
        frames: Iterable[np.ndarray],
        output_path: Path,
        fps: float = 30.0,
        codec: str = "libx264",
        crf: int = 23,
        pixel_format: str = "yuv420p",
        preset: str = "medium",
        bitrate: str | None = None
) -> WriteResult:
    """Write frames to a video file."""
    output_path = Path(output_path)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert frames to iterator if needed
    frame_iter = iter(frames)

    try:
        # Get first frame to determine dimensions
        first_frame = next(frame_iter)
    except StopIteration:
        raise InvalidInput("No frames provided")

    height, width = first_frame.shape[:2]
    frame_count = 1

    try:
        # Build ffmpeg stream
        input_kwargs = {
            "format": "rawvideo",
            "pix_fmt": "rgb24",
            "s": f"{width}x{height}",
            "r": fps
        }

        output_kwargs = {
            "pix_fmt": pixel_format,
            "vcodec": codec,
            "preset": preset,
            "crf": crf
        }

        if bitrate:
            output_kwargs["b:v"] = bitrate

        stream = (
            ffmpeg.input("pipe:", **input_kwargs)
            .output(str(output_path), **output_kwargs)
            .overwrite_output()
        )

        # Start FFmpeg process
        process = stream.run_async(pipe_stdin=True, pipe_stderr=True)

        try:
            # Write first frame
            process.stdin.write(first_frame.tobytes())

            # Write remaining frames
            for frame in frame_iter:
                if frame.shape[:2] != (height, width):
                    raise InvalidInput(
                        f"Inconsistent frame dimensions. Expected {(height, width)}, "
                        f"got {frame.shape[:2]}"
                    )
                process.stdin.write(frame.tobytes())
                frame_count += 1

            # Close input pipe and wait for FFmpeg
            process.stdin.close()
            process.wait()

            if process.returncode != 0:
                stderr = process.stderr.read().decode() if process.stderr else "No error output"
                raise OperationFailed(f"FFmpeg encoding failed: {stderr}", ffmpeg_error=stderr)

            # Return write result
            return WriteResult(
                output=output_path,
                frame_count=frame_count,
                duration=frame_count / fps,
            )

        finally:
            try:
                if process.stdin:
                    process.stdin.close()
                if process.stderr:
                    process.stderr.close()
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=1)
            except Exception:
                pass

    except ffmpeg.Error as e:
        stderr = e.stderr.decode() if e.stderr else "No stderr available"
        if "ffmpeg" in str(e) and "not found" in str(e):
            raise ToolNotFound("ffmpeg not found on PATH")
        else:
            raise OperationFailed(f"Video writing failed: {stderr}", ffmpeg_error=stderr)
    except FileNotFoundError:
        raise ToolNotFound("ffmpeg not found on PATH")
    except Exception as e:
        logger.error(f"Error writing video: {e}")
        raise OperationFailed(f"Video writing failed: {str(e)}")