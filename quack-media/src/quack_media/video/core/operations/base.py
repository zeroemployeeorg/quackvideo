# quack-media/video/core/operations/base.py
from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Generic, TypeVar
from urllib.parse import quote

import ffmpeg
from pydantic import BaseModel

from ..operations.models import (
    FFmpegBaseConfig,
    MediaType,
    OutputMetadata,
    ProcessingMetadata,
)

T = TypeVar("T", bound=FFmpegBaseConfig)
R = TypeVar("R", bound=BaseModel)  # For operation results


class FFmpegOperationError(Exception):
    """Base exception for FFmpeg operation errors."""

    def __init__(self, message: str, ffmpeg_error: str | None = None):
        super().__init__(message)
        self.ffmpeg_error = ffmpeg_error


class FFmpegTimeoutError(FFmpegOperationError):
    """Raised when an FFmpeg operation times out."""

    pass


class FFmpegOperation(ABC, Generic[T, R]):
    """Base class for FFmpeg operations."""

    def __init__(
        self,
        config: T,
        episode_dir: Path,
        logger: logging.Logger | None = None,
    ) -> None:
        """
        Initialize FFmpeg operation.

        Args:
            config: Operation configuration
            episode_dir: Directory for episode files
            logger: Optional logger instance
        """
        self.config = config
        self.episode_dir = Path(episode_dir)
        self.logger = logger or self._setup_logger()
        self._total_frames = 0  # Initialize properly

        # Ensure episode directory exists
        self.episode_dir.mkdir(parents=True, exist_ok=True)

    def _setup_logger(self) -> logging.Logger:
        """Set up logging for the operation."""
        logger = logging.getLogger(f"ffmpeg_operation.{self.__class__.__name__}")
        logger.setLevel(logging.INFO)

        # Create logs directory
        log_dir = self.episode_dir / ".logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        # Create file handler
        handler = logging.FileHandler(log_dir / f"{self.__class__.__name__}.log")
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def _create_metadata_file(self, metadata: ProcessingMetadata) -> None:
        """Create or update metadata file for the operation."""
        metadata_file = self.episode_dir / ".metadata.json"
        metadata_file.write_text(metadata.model_dump_json(indent=2))

    @abstractmethod
    def _build_ffmpeg_stream(self, input_path: Path) -> ffmpeg.Stream:
        """
        Build FFmpeg stream for the operation.

        Must be implemented by subclasses to define specific FFmpeg operations.
        """
        pass

    @abstractmethod
    def _process_output(self, result: Any, metadata: ProcessingMetadata) -> R:
        """
        Process operation output.

        Must be implemented by subclasses to handle operation-specific results.
        """
        pass

    def _validate_input_file(self, input_path: Path, media_type: MediaType) -> None:
        """Validate input file exists and has correct format."""
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        if (
            input_path.suffix.lower()
            not in self.config.compatible_formats[media_type.value]
        ):
            raise ValueError(
                f"Unsupported file format for {media_type.value}: {input_path.suffix}"
            )

    def _get_output_path(self, input_path: Path, operation_type: str) -> Path:
        """Generate output path with timestamp."""
        timestamp = time.strftime("%Y-%m-%d-%H%M%S")
        safe_name = quote(input_path.stem)
        return (
            self.episode_dir
            / f"{timestamp}-{safe_name}-{operation_type}{input_path.suffix}"
        )

    def execute_with_retry(
        self,
        input_path: Path,
        media_type: MediaType,
        operation_type: str,
        progress_desc: str = "Processing",
    ) -> R:
        """
        Execute FFmpeg operation with retry logic.

        Args:
            input_path: Path to input file
            media_type: Type of media being processed
            operation_type: Type of operation being performed
            progress_desc: Description for progress (logged only)

        Returns:
            Operation result of type R

        Raises:
            FFmpegOperationError: If operation fails after all retries
        """
        self.logger.info(f"Starting {operation_type} operation on {input_path}")
        self.logger.debug(f"Media type: {media_type}, Progress desc: {progress_desc}")

        self._validate_input_file(input_path, media_type)
        self.logger.debug("Input file validation passed")

        metadata = ProcessingMetadata()
        self._create_metadata_file(metadata)

        output_metadata = OutputMetadata(
            original_filename=input_path.name,
            operation_type=operation_type,
            output_path=self._get_output_path(input_path, operation_type),
        )
        self.logger.debug(f"Created output metadata: {output_metadata.model_dump_json()}")

        last_error = None
        for attempt in range(self.config.retries):
            try:
                self.logger.debug(f"Attempt {attempt + 1}/{self.config.retries}")

                # Build FFmpeg stream
                stream = self._build_ffmpeg_stream(input_path)
                cmd = ffmpeg.compile(stream)
                self.logger.debug(f"FFmpeg command for attempt {attempt + 1}: {' '.join(cmd)}")

                # Run FFmpeg operation (no progress bar)
                try:
                    result = ffmpeg.run(
                        stream,
                        capture_stdout=True,
                        capture_stderr=True,
                        overwrite_output=True,
                    )
                    self.logger.info("FFmpeg operation completed successfully")

                except ffmpeg.Error as e:
                    stderr = e.stderr.decode() if e.stderr else "No stderr"
                    stdout = e.stdout.decode() if e.stdout else "No stdout"
                    self.logger.error(f"FFmpeg error occurred:")
                    self.logger.error(f"STDOUT: {stdout}")
                    self.logger.error(f"STDERR: {stderr}")
                    raise

                # Process and return results
                metadata.status = "completed"
                self._create_metadata_file(metadata)
                return self._process_output(result, metadata)

            except ffmpeg.Error as e:
                stderr = e.stderr.decode() if e.stderr else "No stderr"
                last_error = FFmpegOperationError(
                    f"FFmpeg operation failed on attempt {attempt + 1}/{self.config.retries}",
                    ffmpeg_error=stderr,
                )
                self.logger.error(f"Attempt {attempt + 1} failed with FFmpeg error:")
                self.logger.error(f"Error message: {last_error}")
                self.logger.error(f"FFmpeg stderr: {stderr}")

                if attempt < self.config.retries - 1:
                    self.logger.info(f"Waiting {self.config.retry_delay}s before next attempt")
                    time.sleep(self.config.retry_delay)
                continue

            except Exception as e:
                self.logger.error(f"Unexpected error type: {type(e)}")
                self.logger.error(f"Error message: {str(e)}")
                self.logger.error(f"Error details: {e.__dict__}")
                last_error = FFmpegOperationError(str(e))
                break

        metadata.status = "failed"
        self._create_metadata_file(metadata)
        raise last_error or FFmpegOperationError(
            "Operation failed with no specific error"
        )

    def cleanup(self) -> None:
        """Clean up any temporary files or resources."""
        pass

    def __enter__(self) -> FFmpegOperation[T, R]:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cleanup()