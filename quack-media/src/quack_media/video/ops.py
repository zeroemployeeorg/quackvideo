# quack-media/video/ops.py

from __future__ import annotations

import logging
from pathlib import Path
import ffmpeg

from ..results import SliceResult, ExtractFramesResult, AudioExtractResult, MediaOpResult
from ..errors import OperationFailed, ToolNotFound, InvalidInput
from .io import probe
from .core.operations.frames import FrameExtractor
from .core.operations.models import FrameExtractionConfig

logger = logging.getLogger(__name__)


def slice_video(
        input_path: Path,
        output_path: Path,
        start: float,
        end: float,
        reencode: bool = False,
        overwrite: bool = False
) -> SliceResult:
    """Extract a time slice from a video."""
    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input video not found: {input_path}")

    if end <= start:
        raise InvalidInput("End time must be greater than start time")

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if output exists and handle overwrite
    if output_path.exists() and not overwrite:
        raise InvalidInput(f"Output file exists and overwrite=False: {output_path}")

    try:
        duration = end - start

        if reencode:
            # Re-encode the slice
            stream = (
                ffmpeg.input(str(input_path), ss=start, t=duration)
                .output(str(output_path))
                .overwrite_output()
            )
        else:
            # Stream copy (faster, no re-encoding)
            stream = (
                ffmpeg.input(str(input_path), ss=start, t=duration)
                .output(str(output_path), c="copy")
                .overwrite_output()
            )

        ffmpeg.run(stream, capture_stderr=True)

        return SliceResult(
            input=input_path,
            output=output_path,
            start=start,
            end=end,
        )

    except ffmpeg.Error as e:
        stderr = e.stderr.decode() if e.stderr else "No stderr available"
        if "ffmpeg" in str(e) and "not found" in str(e):
            raise ToolNotFound("ffmpeg not found on PATH")
        else:
            raise OperationFailed(f"Video slicing failed: {stderr}", ffmpeg_error=stderr)
    except FileNotFoundError:
        raise ToolNotFound("ffmpeg not found on PATH")


def extract_frames(
        input_path: Path,
        output_dir: Path,
        fps: float | str = 1.0,
        format: str = "png"
) -> ExtractFramesResult:
    """Extract frames from video to image files."""
    input_path = Path(input_path)
    output_dir = Path(output_dir)

    if not input_path.exists():
        raise FileNotFoundError(f"Input video not found: {input_path}")

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Create configuration for frame extraction
        config = FrameExtractionConfig(
            fps=str(fps),
            format=format,
            timeout=30,  # Increase timeout for frame extraction
            retries=3,
        )

        # Use the existing frame extraction engine
        extractor = FrameExtractor(config, output_dir)
        result = extractor.extract_frames(input_path, resume=False)

        # Gather frame paths
        frame_paths = sorted(output_dir.glob(f"frame_*.{format}"))

        # Get FPS from probe
        metadata = probe(input_path)

        return ExtractFramesResult(
            input=input_path,
            output_dir=output_dir,
            frame_paths=frame_paths,
            fps=float(fps) if isinstance(fps, (int, float)) else metadata.fps,
            total=len(frame_paths),
        )

    except Exception as e:
        if "ffmpeg" in str(e) and "not found" in str(e):
            raise ToolNotFound("ffmpeg not found on PATH")
        else:
            raise OperationFailed(f"Frame extraction failed: {str(e)}")


def extract_audio(
        input_path: Path,
        output_path: Path,
        format: str = "flac"
) -> AudioExtractResult:
    """Extract audio track from video."""
    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input video not found: {input_path}")

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Simple audio extraction using ffmpeg
        codec_map = {
            "flac": "flac",
            "wav": "pcm_s16le",
            "mp3": "libmp3lame",
            "aac": "aac",
        }

        acodec = codec_map.get(format, "flac")

        stream = (
            ffmpeg.input(str(input_path))
            .output(str(output_path), vn=None, acodec=acodec)
            .overwrite_output()
        )

        ffmpeg.run(stream, capture_stderr=True)

        # Try to get duration by probing the output
        duration = None
        try:
            probe_result = ffmpeg.probe(str(output_path))
            duration = float(probe_result["format"]["duration"])
        except Exception:
            # If probe fails, get duration from input
            try:
                input_metadata = probe(input_path)
                duration = input_metadata.duration
            except Exception:
                pass  # Duration will remain None

        return AudioExtractResult(
            input=input_path,
            output=output_path,
            format=format,
            duration=duration,
        )

    except ffmpeg.Error as e:
        stderr = e.stderr.decode() if e.stderr else "No stderr available"
        if "ffmpeg" in str(e) and "not found" in str(e):
            raise ToolNotFound("ffmpeg not found on PATH")
        else:
            raise OperationFailed(f"Audio extraction failed: {stderr}", ffmpeg_error=stderr)
    except FileNotFoundError:
        raise ToolNotFound("ffmpeg not found on PATH")


def transcode(
        input_path: Path,
        output_path: Path,
        vcodec: str = "libx264",
        acodec: str = "aac",
        crf: int = 23,
        preset: str = "medium",
        overwrite: bool = False
) -> MediaOpResult:
    """Transcode video to different codec/format."""
    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input video not found: {input_path}")

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if output exists and handle overwrite
    if output_path.exists() and not overwrite:
        raise InvalidInput(f"Output file exists and overwrite=False: {output_path}")

    try:
        stream = (
            ffmpeg.input(str(input_path))
            .output(
                str(output_path),
                vcodec=vcodec,
                acodec=acodec,
                crf=crf,
                preset=preset
            )
            .overwrite_output()
        )

        ffmpeg.run(stream, capture_stderr=True)

        return MediaOpResult(
            ok=True,
            message="Transcoding completed successfully",
            meta={
                "input": str(input_path),
                "output": str(output_path),
                "vcodec": vcodec,
                "acodec": acodec,
                "crf": str(crf),
                "preset": preset,
            }
        )

    except ffmpeg.Error as e:
        stderr = e.stderr.decode() if e.stderr else "No stderr available"
        if "ffmpeg" in str(e) and "not found" in str(e):
            raise ToolNotFound("ffmpeg not found on PATH")
        else:
            raise OperationFailed(f"Transcoding failed: {stderr}", ffmpeg_error=stderr)
    except FileNotFoundError:
        raise ToolNotFound("ffmpeg not found on PATH")