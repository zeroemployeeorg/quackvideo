"""Episode artifact store."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, cast

from quackvideo.domain.enums import ContentProfile, PipelineStage
from quackvideo.domain.models import EpisodeState, ProjectConfig
from quackvideo.store.layout import EpisodeLayout


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned or "episode"


class ArtifactStore:
    """Deterministic episode workspace with JSON state."""

    def __init__(self, config: ProjectConfig) -> None:
        self.config = config
        self.workspace = Path(config.workspace).resolve()
        self.episodes_dir = self.workspace / "episodes"
        self.episodes_dir.mkdir(parents=True, exist_ok=True)

    def layout(self, episode_id: str) -> EpisodeLayout:
        layout = EpisodeLayout(self.episodes_dir / episode_id)
        layout.ensure()
        return layout

    def create_episode(self, title: str, profile: ContentProfile) -> EpisodeState:
        stem = slugify(title)
        suffix = hashlib.sha256(title.encode()).hexdigest()[:8]
        episode_id = f"{stem}-{suffix}"
        layout = self.layout(episode_id)
        state = EpisodeState(episode_id=episode_id, profile=profile, title=title)
        self.write_state(state)
        (layout.root / "README.md").write_text(
            f"# {title}\n\nProfile: {profile}\nEpisode: {episode_id}\n",
            encoding="utf-8",
        )
        return state

    def write_state(self, state: EpisodeState) -> None:
        layout = self.layout(state.episode_id)
        layout.episode_file.write_text(
            state.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def load_state(self, episode_id: str) -> EpisodeState:
        path = self.layout(episode_id).episode_file
        if not path.exists():
            raise FileNotFoundError(f"Unknown episode: {episode_id}")
        return EpisodeState.model_validate_json(path.read_text(encoding="utf-8"))

    def ingest_source(self, episode_id: str, source: Path) -> Path:
        layout = self.layout(episode_id)
        destination = layout.source_dir / source.name
        if source.resolve() != destination.resolve():
            shutil.copy2(source, destination)
        return destination

    def write_json(self, episode_id: str, stage: PipelineStage, name: str, payload: object) -> Path:
        path = self.layout(episode_id).stage_dir(stage) / name
        if hasattr(payload, "model_dump"):
            data: Any = payload.model_dump(mode="json")
        else:
            data = payload
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        return path

    def read_json(self, episode_id: str, stage: PipelineStage, name: str) -> dict[str, Any]:
        path = self.layout(episode_id).stage_dir(stage) / name
        loaded = json.loads(path.read_text(encoding="utf-8"))
        return cast(dict[str, Any], loaded)

    def mark_stage(
        self,
        state: EpisodeState,
        stage: PipelineStage,
        status: str,
        input_hash: str | None,
        artifacts: list[Path],
        message: str,
    ) -> EpisodeState:
        from quackvideo.domain.models import StageRecord, utcnow

        state.stages[stage.value] = StageRecord(
            stage=stage,
            status=status,
            finished_at=utcnow(),
            input_hash=input_hash,
            artifact_paths=[str(path) for path in artifacts],
            message=message,
        )
        self.write_state(state)
        return state

    def stage_complete(self, state: EpisodeState, stage: PipelineStage, input_hash: str) -> bool:
        record = state.stages.get(stage.value)
        return bool(record and record.status == "success" and record.input_hash == input_hash)
