"""Resumable profile pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from zeo_core.contracts import CapabilityResult

from quackvideo.capabilities.pipeline import (
    AnalyzeTool,
    ComposeTool,
    EpisodeRequest,
    IngestRequest,
    IngestTool,
    NormalizeTool,
    PackageTool,
    TranscribeTool,
)
from quackvideo.capabilities.support import ToolRunner
from quackvideo.domain.enums import ContentProfile, MomentStatus, PipelineStage
from quackvideo.domain.models import ProjectConfig, ReviewManifest
from quackvideo.store import ArtifactStore

STAGE_ORDER = [
    PipelineStage.INGEST,
    PipelineStage.NORMALIZE,
    PipelineStage.TRANSCRIBE,
    PipelineStage.ANALYZE,
    PipelineStage.REVIEW,
    PipelineStage.COMPOSE,
    PipelineStage.PACKAGE,
]


class WorkflowRunner:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.tools = ToolRunner()
        self.store = ArtifactStore(ProjectConfig(workspace=workspace))

    def ingest(self, source: Path, profile: ContentProfile, title: str | None = None) -> CapabilityResult[Any]:
        return self.tools.run(
            IngestTool(),
            IngestRequest(source=source, profile=profile, title=title, workspace=self.workspace),
            self.workspace,
        )

    def run_stage(self, episode_id: str, stage: PipelineStage, force: bool = False) -> CapabilityResult[Any]:
        request = EpisodeRequest(episode_id=episode_id, workspace=self.workspace, force=force)
        mapping = {
            PipelineStage.NORMALIZE: NormalizeTool(),
            PipelineStage.TRANSCRIBE: TranscribeTool(),
            PipelineStage.ANALYZE: AnalyzeTool(),
            PipelineStage.COMPOSE: ComposeTool(),
            PipelineStage.PACKAGE: PackageTool(),
        }
        if stage == PipelineStage.REVIEW:
            payload = self.store.read_json(episode_id, PipelineStage.REVIEW, "review.json")
            review = ReviewManifest.model_validate(payload)
            approved = sum(1 for m in review.moments if m.status == MomentStatus.APPROVED)
            if approved == 0:
                return CapabilityResult.skip(
                    reason="Human approval required before compose",
                    code="QC_REVIEW_REQUIRED",
                )
            return CapabilityResult.ok(data=review, msg=f"{approved} moments approved")
        tool = mapping.get(stage)
        if tool is None:
            return CapabilityResult.fail(msg=f"Cannot run stage {stage}", code="QC_BAD_STAGE")
        return self.tools.run(tool, request, self.workspace)

    def run_until(self, episode_id: str, until: PipelineStage, force: bool = False) -> list[CapabilityResult[Any]]:
        results: list[CapabilityResult[Any]] = []
        for stage in STAGE_ORDER:
            if stage == PipelineStage.INGEST:
                continue
            result = self.run_stage(episode_id, stage, force=force)
            results.append(result)
            if result.status == "error":
                break
            if stage == until:
                break
            if stage == PipelineStage.REVIEW and result.status == "skipped":
                break
        return results
