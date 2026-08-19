from pathlib import Path

from quackvideo.capabilities.pipeline import MetricsImportRequest, MetricsImportTool
from quackvideo.capabilities.support import ToolRunner
from quackvideo.domain.enums import ContentProfile, MomentStatus, PipelineStage
from quackvideo.domain.models import Moment, MomentScores, ProjectConfig, ReviewManifest
from quackvideo.store import ArtifactStore


def test_metrics_import_csv(tmp_workspace: Path) -> None:
    store = ArtifactStore(ProjectConfig(workspace=tmp_workspace))
    state = store.create_episode("metrics", ContentProfile.SOCIAL)
    csv_path = tmp_workspace / "metrics.csv"
    csv_path.write_text("moment_id,platform,views,retention_3s\nm1,tiktok,1000,0.8\n", encoding="utf-8")
    result = ToolRunner().run(
        MetricsImportTool(),
        MetricsImportRequest(episode_id=state.episode_id, workspace=tmp_workspace, path=csv_path),
        tmp_workspace,
    )
    assert result.status == "success"
    assert result.data
    assert result.data[0].views == 1000


def test_review_approve_reject(tmp_workspace: Path) -> None:
    from quackvideo.capabilities.pipeline import (
        ReviewActionRequest,
        ReviewApproveTool,
        ReviewRejectTool,
    )

    store = ArtifactStore(ProjectConfig(workspace=tmp_workspace))
    state = store.create_episode("review", ContentProfile.TUTORIAL)
    review = ReviewManifest(
        episode_id=state.episode_id,
        moments=[
            Moment(
                moment_id="m001",
                start=0,
                end=12,
                title="Hook",
                hook="Why this matters",
                rationale="test",
                scores=MomentScores(hook=0.9),
            )
        ],
    )
    store.write_json(state.episode_id, PipelineStage.REVIEW, "review.json", review)
    store.write_json(state.episode_id, PipelineStage.ANALYZE, "review.json", review)
    runner = ToolRunner()
    approved = runner.run(
        ReviewApproveTool(),
        ReviewActionRequest(episode_id=state.episode_id, workspace=tmp_workspace, moment_id="m001"),
        tmp_workspace,
    )
    assert approved.status == "success"
    assert approved.data and approved.data.moments[0].status == MomentStatus.APPROVED
    rejected = runner.run(
        ReviewRejectTool(),
        ReviewActionRequest(episode_id=state.episode_id, workspace=tmp_workspace, moment_id="m001", notes="weak"),
        tmp_workspace,
    )
    assert rejected.data and rejected.data.moments[0].status == MomentStatus.REJECTED
