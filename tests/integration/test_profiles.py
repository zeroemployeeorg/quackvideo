from pathlib import Path

import pytest

from quackvideo.domain.enums import ContentProfile, PipelineStage
from quackvideo.media.engine import FFmpegEngine
from quackvideo.media.ops import generate_synthetic_audio, generate_synthetic_video
from quackvideo.workflows.runner import WorkflowRunner

ffmpeg = FFmpegEngine()
pytestmark = pytest.mark.requires_ffmpeg


@pytest.mark.skipif(not ffmpeg.available(), reason="ffmpeg not installed")
@pytest.mark.parametrize(
    "profile,kind",
    [
        (ContentProfile.PODCAST, "audio"),
        (ContentProfile.TALKING_HEAD, "video"),
        (ContentProfile.TUTORIAL, "video"),
        (ContentProfile.SOCIAL, "video"),
    ],
)
def test_profile_flywheel(tmp_workspace: Path, profile: ContentProfile, kind: str) -> None:
    engine = FFmpegEngine()
    source = tmp_workspace / ("source.flac" if kind == "audio" else "source.mp4")
    if kind == "audio":
        generate_synthetic_audio(engine, source, duration=8)
    else:
        generate_synthetic_video(engine, source, duration=8, width=320, height=180, fps=10)
    runner = WorkflowRunner(tmp_workspace)
    ingested = runner.ingest(source, profile, title=f"{profile}-pilot")
    assert ingested.status == "success"
    assert ingested.data is not None
    episode_id = ingested.data.episode_id
    results = runner.run_until(episode_id, PipelineStage.ANALYZE)
    assert results
    assert all(r.status != "error" for r in results)
    review = runner.store.read_json(episode_id, PipelineStage.REVIEW, "review.json")
    moment_id = review["moments"][0]["moment_id"]
    from quackvideo.capabilities.pipeline import ReviewActionRequest, ReviewApproveTool
    from quackvideo.capabilities.support import ToolRunner

    ToolRunner().run(
        ReviewApproveTool(),
        ReviewActionRequest(episode_id=episode_id, workspace=tmp_workspace, moment_id=moment_id),
        tmp_workspace,
    )
    composed = runner.run_stage(episode_id, PipelineStage.COMPOSE)
    assert composed.status == "success"
    packaged = runner.run_stage(episode_id, PipelineStage.PACKAGE)
    assert packaged.status == "success"
    package_dir = runner.store.layout(episode_id).stage_dir(PipelineStage.PACKAGE)
    handoffs = list(package_dir.glob("*/handoff.json"))
    assert handoffs
    # resume / cache
    again = runner.run_stage(episode_id, PipelineStage.TRANSCRIBE)
    assert again.status in {"success", "skipped"}
