"""Typed settings loaded from quackvideo.toml and environment."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from quackvideo.domain.enums import ContentProfile
from quackvideo.domain.models import ProjectConfig


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="QUACKVIDEO_",
        extra="ignore",
    )

    workspace: Path = Field(default=Path("workspace"))
    default_profile: ContentProfile = ContentProfile.TALKING_HEAD
    transcription_provider: str = "fake"
    analysis_provider: str = "heuristic"
    ffmpeg_timeout_sec: float = 600.0
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    project_name: str = "quackvideo"
    language: str = "en"

    def to_project(self) -> ProjectConfig:
        return ProjectConfig(
            name=self.project_name,
            workspace=self.workspace,
            default_profile=self.default_profile,
            language=self.language,
            transcription_provider=self.transcription_provider,
            analysis_provider=self.analysis_provider,
            ffmpeg_timeout_sec=self.ffmpeg_timeout_sec,
        )


def load_project_config(path: Path | None = None) -> ProjectConfig:
    """Load project config from quackvideo.toml if present."""
    settings = Settings()
    candidate = path or Path("quackvideo.toml")
    if candidate.exists():
        import tomllib

        data = tomllib.loads(candidate.read_text(encoding="utf-8"))
        project = data.get("project", data)
        merged = settings.model_dump()
        for key, value in project.items():
            if key in merged and value is not None:
                merged[key] = value
        if "name" in project:
            merged["project_name"] = project["name"]
        settings = Settings.model_validate(merged)
    return settings.to_project()
