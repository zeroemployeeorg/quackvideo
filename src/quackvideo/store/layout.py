"""Filesystem layout for an episode workspace."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from quackvideo.domain.enums import PipelineStage


@dataclass(frozen=True)
class EpisodeLayout:
    root: Path

    @property
    def episode_file(self) -> Path:
        return self.root / "episode.json"

    @property
    def source_dir(self) -> Path:
        return self.root / "source"

    @property
    def artifacts(self) -> Path:
        return self.root / "artifacts"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    @property
    def cache(self) -> Path:
        return self.root / "cache"

    def stage_dir(self, stage: PipelineStage) -> Path:
        return self.artifacts / stage.value

    def ensure(self) -> None:
        for path in (
            self.root,
            self.source_dir,
            self.artifacts,
            self.logs,
            self.cache,
        ):
            path.mkdir(parents=True, exist_ok=True)
        for stage in PipelineStage:
            self.stage_dir(stage).mkdir(parents=True, exist_ok=True)
