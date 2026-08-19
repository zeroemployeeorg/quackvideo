"""Typer CLI with human and JSON output."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from quackvideo.__version__ import __version__
from quackvideo.capabilities.pipeline import (
    MetricsImportRequest,
    MetricsImportTool,
    ReviewActionRequest,
)
from quackvideo.capabilities.support import ToolRunner
from quackvideo.domain.enums import ContentProfile, PipelineStage
from quackvideo.domain.models import ProjectConfig, ReviewManifest
from quackvideo.media.engine import FFmpegEngine
from quackvideo.media.ops import (
    extract_audio,
    generate_synthetic_audio,
    generate_synthetic_video,
    slice_media,
)
from quackvideo.settings import load_project_config
from quackvideo.store import ArtifactStore
from quackvideo.workflows.runner import WorkflowRunner

app = typer.Typer(no_args_is_help=True, help="QuackVideo creator flywheel")
project_app = typer.Typer(no_args_is_help=True)
review_app = typer.Typer(no_args_is_help=True)
media_app = typer.Typer(no_args_is_help=True)
metrics_app = typer.Typer(no_args_is_help=True)
app.add_typer(project_app, name="project")
app.add_typer(review_app, name="review")
app.add_typer(media_app, name="media")
app.add_typer(metrics_app, name="metrics")

console = Console()
err_console = Console(stderr=True)


def _emit(as_json: bool, payload: Any, message: str) -> None:
    if as_json:
        if hasattr(payload, "model_dump"):
            data = payload.model_dump(mode="json")
        else:
            data = payload
        console.print_json(json.dumps({"ok": True, "message": message, "data": data}, default=str))
    else:
        console.print(message)
        if payload is not None and not isinstance(payload, str):
            console.print(payload)


def _workspace(explicit: Path | None) -> Path:
    if explicit:
        return explicit.resolve()
    return load_project_config().workspace.resolve()


@app.callback()
def root(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON"),
) -> None:
    ctx.obj = {"json": json_output}


@app.command()
def version() -> None:
    """Print version."""
    console.print(__version__)


@app.command()
def doctor(
    ctx: typer.Context,
    workspace: Path | None = typer.Option(None, "--workspace"),
) -> None:
    """Check ffmpeg, workspace, and config."""
    engine = FFmpegEngine()
    cfg = load_project_config()
    payload = {
        "version": __version__,
        "ffmpeg": engine.ffmpeg_bin,
        "ffprobe": engine.ffprobe_bin,
        "available": engine.available(),
        "workspace": str(_workspace(workspace)),
        "transcription_provider": cfg.transcription_provider,
        "analysis_provider": cfg.analysis_provider,
    }
    _emit(ctx.obj["json"], payload, "doctor")
    raise typer.Exit(0 if engine.available() else 2)


@project_app.command("init")
def project_init(
    ctx: typer.Context,
    name: str = typer.Option("studio", "--name"),
    workspace: Path = typer.Option(Path("workspace"), "--workspace"),
) -> None:
    """Write quackvideo.toml and create the workspace."""
    workspace.mkdir(parents=True, exist_ok=True)
    toml_path = Path("quackvideo.toml")
    toml_path.write_text(
        f'[project]\nname = "{name}"\nworkspace = "{workspace}"\n'
        'default_profile = "talking-head"\ntranscription_provider = "fake"\n',
        encoding="utf-8",
    )
    ArtifactStore(load_project_config(toml_path))
    _emit(ctx.obj["json"], {"config": str(toml_path), "workspace": str(workspace)}, "Initialized project")


@app.command()
def ingest(
    ctx: typer.Context,
    source: Path = typer.Argument(..., exists=True, readable=True),
    profile: ContentProfile = typer.Option(ContentProfile.TALKING_HEAD, "--profile"),
    title: str | None = typer.Option(None, "--title"),
    workspace: Path | None = typer.Option(None, "--workspace"),
) -> None:
    """Ingest a recording into an episode workspace."""
    runner = WorkflowRunner(_workspace(workspace))
    result = runner.ingest(source, profile, title)
    if result.status != "success":
        err_console.print(result.human_message)
        raise typer.Exit(1)
    _emit(ctx.obj["json"], result.data, result.human_message)


@app.command()
def run(
    ctx: typer.Context,
    episode_id: str,
    until: PipelineStage = typer.Option(PipelineStage.ANALYZE, "--until"),
    workspace: Path | None = typer.Option(None, "--workspace"),
    force: bool = typer.Option(False, "--force"),
) -> None:
    """Run the pipeline up to a stage. Stops at review until moments are approved."""
    runner = WorkflowRunner(_workspace(workspace))
    results = runner.run_until(episode_id, until, force=force)
    payload = [{"status": r.status, "message": r.human_message} for r in results]
    failed = any(r.status == "error" for r in results)
    _emit(ctx.obj["json"], payload, "pipeline")
    raise typer.Exit(1 if failed else 0)


@app.command()
def transcribe(
    ctx: typer.Context,
    episode_id: str,
    workspace: Path | None = typer.Option(None, "--workspace"),
    force: bool = typer.Option(False, "--force"),
) -> None:
    runner = WorkflowRunner(_workspace(workspace))
    result = runner.run_stage(episode_id, PipelineStage.TRANSCRIBE, force=force)
    _emit(ctx.obj["json"], result.data, result.human_message)
    raise typer.Exit(0 if result.status != "error" else 1)


@app.command()
def analyze(
    ctx: typer.Context,
    episode_id: str,
    workspace: Path | None = typer.Option(None, "--workspace"),
    force: bool = typer.Option(False, "--force"),
) -> None:
    runner = WorkflowRunner(_workspace(workspace))
    result = runner.run_stage(episode_id, PipelineStage.ANALYZE, force=force)
    _emit(ctx.obj["json"], result.data, result.human_message)
    raise typer.Exit(0 if result.status != "error" else 1)


@review_app.command("list")
def review_list(
    ctx: typer.Context,
    episode_id: str,
    workspace: Path | None = typer.Option(None, "--workspace"),
) -> None:
    store = ArtifactStore(ProjectConfig(workspace=_workspace(workspace)))
    review = ReviewManifest.model_validate(store.read_json(episode_id, PipelineStage.REVIEW, "review.json"))
    if ctx.obj["json"]:
        _emit(True, review, "review")
        return
    table = Table(title=f"Moments for {episode_id}")
    table.add_column("id")
    table.add_column("status")
    table.add_column("start")
    table.add_column("end")
    table.add_column("score")
    table.add_column("hook")
    for moment in review.moments:
        table.add_row(
            moment.moment_id,
            moment.status.value,
            f"{moment.start:.1f}",
            f"{moment.end:.1f}",
            f"{moment.scores.total:.2f}",
            moment.hook[:60],
        )
    console.print(table)


@review_app.command("approve")
def review_approve(
    ctx: typer.Context,
    episode_id: str,
    moment_id: str,
    workspace: Path | None = typer.Option(None, "--workspace"),
    notes: str = typer.Option("", "--notes"),
    start: float | None = typer.Option(None, "--start"),
    end: float | None = typer.Option(None, "--end"),
) -> None:
    from quackvideo.capabilities.pipeline import ReviewApproveTool

    result = ToolRunner().run(
        ReviewApproveTool(),
        ReviewActionRequest(
            episode_id=episode_id,
            workspace=_workspace(workspace),
            moment_id=moment_id,
            notes=notes,
            start=start,
            end=end,
        ),
        _workspace(workspace),
    )
    _emit(ctx.obj["json"], result.data, result.human_message)
    raise typer.Exit(0 if result.status != "error" else 1)


@review_app.command("reject")
def review_reject(
    ctx: typer.Context,
    episode_id: str,
    moment_id: str,
    workspace: Path | None = typer.Option(None, "--workspace"),
    notes: str = typer.Option("", "--notes"),
) -> None:
    from quackvideo.capabilities.pipeline import ReviewRejectTool

    result = ToolRunner().run(
        ReviewRejectTool(),
        ReviewActionRequest(
            episode_id=episode_id,
            workspace=_workspace(workspace),
            moment_id=moment_id,
            notes=notes,
        ),
        _workspace(workspace),
    )
    _emit(ctx.obj["json"], result.data, result.human_message)
    raise typer.Exit(0 if result.status != "error" else 1)


@app.command()
def compose(
    ctx: typer.Context,
    episode_id: str,
    workspace: Path | None = typer.Option(None, "--workspace"),
    force: bool = typer.Option(False, "--force"),
) -> None:
    runner = WorkflowRunner(_workspace(workspace))
    result = runner.run_stage(episode_id, PipelineStage.COMPOSE, force=force)
    _emit(ctx.obj["json"], result.data, result.human_message)
    raise typer.Exit(0 if result.status != "error" else 1)


@app.command()
def package(
    ctx: typer.Context,
    episode_id: str,
    workspace: Path | None = typer.Option(None, "--workspace"),
    force: bool = typer.Option(False, "--force"),
) -> None:
    runner = WorkflowRunner(_workspace(workspace))
    result = runner.run_stage(episode_id, PipelineStage.PACKAGE, force=force)
    _emit(ctx.obj["json"], result.data, result.human_message)
    raise typer.Exit(0 if result.status != "error" else 1)


@media_app.command("probe")
def media_probe(
    ctx: typer.Context,
    source: Path = typer.Argument(..., exists=True),
) -> None:
    engine = FFmpegEngine()
    result = engine.probe(source)
    _emit(ctx.obj["json"], result, f"{source} duration={result.duration:.2f}s")


@media_app.command("extract-audio")
def media_extract_audio(
    ctx: typer.Context,
    source: Path,
    dest: Path,
) -> None:
    path = extract_audio(FFmpegEngine(), source, dest)
    _emit(ctx.obj["json"], {"output": str(path)}, str(path))


@media_app.command("slice")
def media_slice(
    ctx: typer.Context,
    source: Path,
    dest: Path,
    start: float = typer.Option(..., "--start"),
    end: float = typer.Option(..., "--end"),
) -> None:
    path = slice_media(FFmpegEngine(), source, dest, start, end, reencode=True)
    _emit(ctx.obj["json"], {"output": str(path)}, str(path))


@media_app.command("synth")
def media_synth(
    ctx: typer.Context,
    dest: Path,
    kind: str = typer.Option("video", "--kind"),
    duration: float = typer.Option(4.0, "--duration"),
) -> None:
    engine = FFmpegEngine()
    if kind == "audio":
        path = generate_synthetic_audio(engine, dest, duration=duration)
    else:
        path = generate_synthetic_video(engine, dest, duration=duration)
    _emit(ctx.obj["json"], {"output": str(path)}, str(path))


@metrics_app.command("import")
def metrics_import(
    ctx: typer.Context,
    episode_id: str,
    path: Path,
    workspace: Path | None = typer.Option(None, "--workspace"),
) -> None:
    result = ToolRunner().run(
        MetricsImportTool(),
        MetricsImportRequest(episode_id=episode_id, workspace=_workspace(workspace), path=path),
        _workspace(workspace),
    )
    _emit(ctx.obj["json"], result.data, result.human_message)
    raise typer.Exit(0 if result.status != "error" else 1)


def main() -> None:
    app()
