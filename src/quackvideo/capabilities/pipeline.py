"""Ingest, QC, normalize, transcribe, analyze, review, compose, package, metrics."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel
from zeo_core.contracts import CapabilityResult
from zeo_core.tools import BaseZeoTool, ToolContext

from quackvideo.analysis.captions import slice_transcript, write_markdown, write_srt, write_vtt
from quackvideo.analysis.moments import chapters_from_transcript
from quackvideo.domain.enums import ContentProfile, MomentStatus, PipelineStage, PlatformName
from quackvideo.domain.models import (
    EpisodeState,
    PerformanceSignal,
    ProjectConfig,
    QcIssue,
    QcReport,
    ReviewManifest,
    SourceAsset,
    Transcript,
)
from quackvideo.domain.profiles import PLATFORM_PRESETS, PROFILE_PLATFORMS
from quackvideo.media.engine import FFmpegEngine
from quackvideo.media.errors import MediaError, ToolNotFound
from quackvideo.media.ops import (
    detect_black,
    detect_scenes,
    detect_silence,
    extract_audio,
    fit_aspect,
    loudnorm_audio,
    slice_media,
    thumbnail_sheet,
    transcode_mezzanine,
)
from quackvideo.providers.analysis import get_analysis_provider
from quackvideo.providers.transcription import get_transcription_provider
from quackvideo.settings import Settings
from quackvideo.store import ArtifactStore, sha256_file


class EpisodeRequest(BaseModel):
    episode_id: str
    workspace: Path
    force: bool = False


class IngestRequest(BaseModel):
    source: Path
    profile: ContentProfile
    title: str | None = None
    workspace: Path
    force: bool = False


class ReviewActionRequest(BaseModel):
    episode_id: str
    workspace: Path
    moment_id: str
    notes: str = ""
    start: float | None = None
    end: float | None = None


class MetricsImportRequest(BaseModel):
    episode_id: str
    workspace: Path
    path: Path


def _store(workspace: Path) -> ArtifactStore:
    config = ProjectConfig(workspace=workspace)
    return ArtifactStore(config)


def _engine(workspace: Path | None = None) -> FFmpegEngine:
    settings = Settings()
    return FFmpegEngine(timeout_sec=settings.ffmpeg_timeout_sec)


class IngestTool(BaseZeoTool):
    name = "ingest"
    version = "1.0.0"

    def run(self, request: IngestRequest, ctx: ToolContext) -> CapabilityResult[EpisodeState]:
        store = _store(request.workspace)
        title = request.title or request.source.stem
        state = store.create_episode(title, request.profile)
        try:
            copied = store.ingest_source(state.episode_id, request.source)
            digest = sha256_file(copied)
            engine = _engine()
            probe = engine.probe(copied)
            issues: list[QcIssue] = []
            if not probe.has_audio:
                issues.append(QcIssue(code="QC_NO_AUDIO", severity="error", message="No audio stream"))
            if request.profile != ContentProfile.PODCAST and not probe.has_video:
                issues.append(QcIssue(code="QC_NO_VIDEO", severity="error", message="No video stream"))
            if probe.duration < 3:
                issues.append(QcIssue(code="QC_TOO_SHORT", severity="warning", message="Duration under 3s"))
            black = detect_black(engine, copied) if probe.has_video else []
            silence = detect_silence(engine, copied) if probe.has_audio else []
            if black:
                issues.append(QcIssue(code="QC_BLACK", severity="warning", message=f"{len(black)} black ranges"))
            if silence:
                issues.append(QcIssue(code="QC_SILENCE", severity="info", message=f"{len(silence)} silence ranges"))
            report = QcReport(
                duration=probe.duration,
                has_video=probe.has_video,
                has_audio=probe.has_audio,
                black_frames=black,
                silence_ranges=silence,
                issues=issues,
                blocking=any(i.severity == "error" for i in issues),
            )
            state.source = SourceAsset(
                path=copied,
                sha256=digest,
                content_type="video/mp4" if probe.has_video else "audio/*",
                size_bytes=copied.stat().st_size,
                original_name=request.source.name,
            )
            state.probe = probe
            qc_path = store.write_json(state.episode_id, PipelineStage.INGEST, "qc.json", report)
            store.write_json(state.episode_id, PipelineStage.INGEST, "probe.json", probe)
            store.mark_stage(state, PipelineStage.INGEST, "success", digest, [qc_path], "ingested")
            return CapabilityResult.ok(data=state, msg=f"Ingested {state.episode_id}")
        except ToolNotFound as exc:
            return CapabilityResult.fail_from_exc(msg="ffmpeg/ffprobe missing", code="QC_TOOL_MISSING", exc=exc)
        except Exception as exc:  # noqa: BLE001
            return CapabilityResult.fail_from_exc(msg="Ingest failed", code="QC_INGEST_FAIL", exc=exc)


class NormalizeTool(BaseZeoTool):
    name = "normalize"
    version = "1.0.0"

    def run(self, request: EpisodeRequest, ctx: ToolContext) -> CapabilityResult[dict[str, str]]:
        store = _store(request.workspace)
        state = store.load_state(request.episode_id)
        if not state.source:
            return CapabilityResult.fail(msg="Episode has no source", code="QC_NO_SOURCE")
        digest = state.source.sha256
        if store.stage_complete(state, PipelineStage.NORMALIZE, digest) and not request.force:
            return CapabilityResult.skip(reason="Normalize already complete", code="QC_CACHE_HIT")
        try:
            engine = _engine()
            layout = store.layout(state.episode_id)
            audio = extract_audio(
                engine, Path(state.source.path), layout.stage_dir(PipelineStage.NORMALIZE) / "audio.flac"
            )
            loud = loudnorm_audio(engine, audio, layout.stage_dir(PipelineStage.NORMALIZE) / "audio.loudnorm.flac")
            artifacts = [audio, loud]
            if state.probe and state.probe.has_video:
                mezz = transcode_mezzanine(
                    engine,
                    Path(state.source.path),
                    layout.stage_dir(PipelineStage.NORMALIZE) / "mezzanine.mp4",
                )
                artifacts.append(mezz)
            store.mark_stage(state, PipelineStage.NORMALIZE, "success", digest, artifacts, "normalized")
            return CapabilityResult.ok(
                data={str(path.name): str(path) for path in artifacts},
                msg="Normalized media",
            )
        except MediaError as exc:
            return CapabilityResult.fail_from_exc(msg="Normalize failed", code="QC_NORMALIZE_FAIL", exc=exc)


class TranscribeTool(BaseZeoTool):
    name = "transcribe"
    version = "1.0.0"

    def run(self, request: EpisodeRequest, ctx: ToolContext) -> CapabilityResult[Transcript]:
        store = _store(request.workspace)
        state = store.load_state(request.episode_id)
        settings = Settings()
        if not state.source:
            return CapabilityResult.fail(msg="Episode has no source", code="QC_NO_SOURCE")
        layout = store.layout(state.episode_id)
        audio = layout.stage_dir(PipelineStage.NORMALIZE) / "audio.loudnorm.flac"
        if not audio.exists():
            audio = layout.stage_dir(PipelineStage.NORMALIZE) / "audio.flac"
        if not audio.exists():
            audio = Path(state.source.path)
        cache_key = f"{state.source.sha256}:{settings.transcription_provider}:{settings.language}"
        if store.stage_complete(state, PipelineStage.TRANSCRIBE, cache_key) and not request.force:
            payload = store.read_json(state.episode_id, PipelineStage.TRANSCRIBE, "transcript.json")
            return CapabilityResult.ok(data=Transcript.model_validate(payload), msg="Transcript cache hit")
        try:
            provider = get_transcription_provider(settings.transcription_provider, settings.openai_api_key)
            duration = state.probe.duration if state.probe else 30.0
            transcript = provider.transcribe(str(audio), duration, settings.language, state.source.sha256)
            json_path = store.write_json(state.episode_id, PipelineStage.TRANSCRIBE, "transcript.json", transcript)
            srt = write_srt(transcript, layout.stage_dir(PipelineStage.TRANSCRIBE) / "transcript.srt")
            vtt = write_vtt(transcript, layout.stage_dir(PipelineStage.TRANSCRIBE) / "transcript.vtt")
            md = write_markdown(transcript, layout.stage_dir(PipelineStage.TRANSCRIBE) / "transcript.md")
            store.mark_stage(
                state, PipelineStage.TRANSCRIBE, "success", cache_key, [json_path, srt, vtt, md], "transcribed"
            )
            return CapabilityResult.ok(data=transcript, msg="Transcription complete")
        except Exception as exc:  # noqa: BLE001
            return CapabilityResult.fail_from_exc(msg="Transcription failed", code="QC_TRANSCRIBE_FAIL", exc=exc)


class AnalyzeTool(BaseZeoTool):
    name = "analyze"
    version = "1.0.0"

    def run(self, request: EpisodeRequest, ctx: ToolContext) -> CapabilityResult[ReviewManifest]:
        store = _store(request.workspace)
        state = store.load_state(request.episode_id)
        settings = Settings()
        payload = store.read_json(state.episode_id, PipelineStage.TRANSCRIBE, "transcript.json")
        transcript = Transcript.model_validate(payload)
        engine = _engine()
        source = Path(state.source.path) if state.source else None
        cuts: list[float] = []
        if source and state.probe and state.probe.has_video:
            try:
                cuts = detect_scenes(engine, source)
            except MediaError:
                cuts = []
        metrics_path = store.layout(state.episode_id).stage_dir(PipelineStage.PACKAGE) / "metrics.json"
        prior: list[PerformanceSignal] = []
        if metrics_path.exists():
            import json

            prior = [PerformanceSignal.model_validate(item) for item in json.loads(metrics_path.read_text())]
        provider = get_analysis_provider(settings.analysis_provider)
        moments = provider.propose(transcript, state.profile, cuts, prior)
        chapters = chapters_from_transcript(transcript)
        review = ReviewManifest(episode_id=state.episode_id, moments=moments)
        review_path = store.write_json(state.episode_id, PipelineStage.ANALYZE, "review.json", review)
        store.write_json(state.episode_id, PipelineStage.ANALYZE, "chapters.json", chapters)
        store.write_json(state.episode_id, PipelineStage.REVIEW, "review.json", review)
        digest = state.source.sha256 if state.source else "none"
        store.mark_stage(state, PipelineStage.ANALYZE, "success", digest, [review_path], "analyzed")
        return CapabilityResult.ok(data=review, msg=f"Proposed {len(moments)} moments")


class ReviewApproveTool(BaseZeoTool):
    name = "review.approve"
    version = "1.0.0"

    def run(self, request: ReviewActionRequest, ctx: ToolContext) -> CapabilityResult[ReviewManifest]:
        return _mutate_review(request, MomentStatus.APPROVED)


class ReviewRejectTool(BaseZeoTool):
    name = "review.reject"
    version = "1.0.0"

    def run(self, request: ReviewActionRequest, ctx: ToolContext) -> CapabilityResult[ReviewManifest]:
        return _mutate_review(request, MomentStatus.REJECTED)


def _mutate_review(request: ReviewActionRequest, status: MomentStatus) -> CapabilityResult[ReviewManifest]:
    store = _store(request.workspace)
    payload = store.read_json(request.episode_id, PipelineStage.REVIEW, "review.json")
    review = ReviewManifest.model_validate(payload)
    try:
        moment = review.by_id(request.moment_id)
    except KeyError:
        return CapabilityResult.fail(msg="Unknown moment", code="QC_UNKNOWN_MOMENT")
    moment.status = status
    if request.notes:
        moment.notes = request.notes
    if request.start is not None:
        moment.start = request.start
    if request.end is not None:
        moment.end = request.end
    store.write_json(request.episode_id, PipelineStage.REVIEW, "review.json", review)
    store.write_json(request.episode_id, PipelineStage.ANALYZE, "review.json", review)
    return CapabilityResult.ok(data=review, msg=f"{status} {moment.moment_id}")


class ComposeTool(BaseZeoTool):
    name = "compose"
    version = "1.0.0"

    def run(self, request: EpisodeRequest, ctx: ToolContext) -> CapabilityResult[dict[str, Any]]:
        store = _store(request.workspace)
        state = store.load_state(request.episode_id)
        review = ReviewManifest.model_validate(store.read_json(state.episode_id, PipelineStage.REVIEW, "review.json"))
        approved = [m for m in review.moments if m.status == MomentStatus.APPROVED]
        if not approved:
            return CapabilityResult.skip(reason="No approved moments", code="QC_REVIEW_REQUIRED")
        if not state.source:
            return CapabilityResult.fail(msg="No source", code="QC_NO_SOURCE")
        transcript = Transcript.model_validate(
            store.read_json(state.episode_id, PipelineStage.TRANSCRIBE, "transcript.json")
        )
        engine = _engine()
        layout = store.layout(state.episode_id)
        compose_dir = layout.stage_dir(PipelineStage.COMPOSE)
        source = Path(state.source.path)
        mezz = layout.stage_dir(PipelineStage.NORMALIZE) / "mezzanine.mp4"
        media_source = mezz if mezz.exists() else source
        written: list[str] = []
        try:
            for moment in approved:
                clip = compose_dir / f"{moment.moment_id}.mp4"
                if state.probe and state.probe.has_video:
                    slice_media(engine, media_source, clip, moment.start, moment.end, reencode=True)
                else:
                    audio = layout.stage_dir(PipelineStage.NORMALIZE) / "audio.loudnorm.flac"
                    slice_media(
                        engine,
                        audio if audio.exists() else source,
                        clip.with_suffix(".flac"),
                        moment.start,
                        moment.end,
                        reencode=True,
                    )
                    clip = clip.with_suffix(".flac")
                sliced = slice_transcript(transcript, moment.start, moment.end)
                write_srt(sliced, compose_dir / f"{moment.moment_id}.srt")
                write_vtt(sliced, compose_dir / f"{moment.moment_id}.vtt")
                written.append(str(clip))
            if state.probe and state.probe.has_video:
                sheet = compose_dir / "thumbnails.jpg"
                thumbnail_sheet(engine, media_source, sheet)
                written.append(str(sheet))
            store.mark_stage(
                state, PipelineStage.COMPOSE, "success", state.source.sha256, [Path(p) for p in written], "composed"
            )
            return CapabilityResult.ok(data={"clips": written}, msg=f"Composed {len(approved)} clips")
        except MediaError as exc:
            return CapabilityResult.fail_from_exc(msg="Compose failed", code="QC_COMPOSE_FAIL", exc=exc)


class PackageTool(BaseZeoTool):
    name = "package"
    version = "1.0.0"

    def run(self, request: EpisodeRequest, ctx: ToolContext) -> CapabilityResult[dict[str, Any]]:
        store = _store(request.workspace)
        state = store.load_state(request.episode_id)
        review = ReviewManifest.model_validate(store.read_json(state.episode_id, PipelineStage.REVIEW, "review.json"))
        approved = [m for m in review.moments if m.status == MomentStatus.APPROVED]
        if not approved:
            return CapabilityResult.skip(reason="No approved moments", code="QC_REVIEW_REQUIRED")
        layout = store.layout(state.episode_id)
        engine = _engine()
        platforms = PROFILE_PLATFORMS.get(state.profile, list(PLATFORM_PRESETS))
        packages: dict[str, Any] = {}
        compose_dir = layout.stage_dir(PipelineStage.COMPOSE)
        for platform in platforms:
            preset = PLATFORM_PRESETS[platform]
            dest_dir = layout.stage_dir(PipelineStage.PACKAGE) / platform.value
            dest_dir.mkdir(parents=True, exist_ok=True)
            media_files: list[str] = []
            for moment in approved:
                src = compose_dir / f"{moment.moment_id}.mp4"
                if not src.exists():
                    src = compose_dir / f"{moment.moment_id}.flac"
                if not src.exists():
                    continue
                if src.suffix == ".mp4" and preset.max_duration >= moment.duration:
                    out = dest_dir / f"{moment.moment_id}.mp4"
                    if moment.duration <= preset.max_duration:
                        try:
                            fit_aspect(engine, src, out, preset)
                            media_files.append(str(out))
                        except MediaError:
                            media_files.append(str(src))
                elif preset.include_audio_only and src.suffix in {".flac", ".mp3", ".wav", ".m4a"}:
                    target = dest_dir / src.name
                    target.write_bytes(src.read_bytes())
                    media_files.append(str(target))
                srt = compose_dir / f"{moment.moment_id}.srt"
                if srt.exists():
                    (dest_dir / srt.name).write_text(srt.read_text(encoding="utf-8"), encoding="utf-8")
            metadata = {
                "episode_id": state.episode_id,
                "profile": state.profile.value,
                "platform": platform.value,
                "title": state.title,
                "moments": [m.model_dump(mode="json") for m in approved],
                "hashtags": ["#AI", "#buildinpublic", f"#{state.profile.value}"],
            }
            (dest_dir / "handoff.json").write_text(
                __import__("json").dumps(metadata, indent=2, default=str),
                encoding="utf-8",
            )
            (dest_dir / "description.md").write_text(
                f"# {state.title}\n\n" + "\n".join(f"- {m.hook}" for m in approved),
                encoding="utf-8",
            )
            packages[platform.value] = {"directory": str(dest_dir), "media": media_files}
        store.mark_stage(
            state,
            PipelineStage.PACKAGE,
            "success",
            state.source.sha256 if state.source else "none",
            [layout.stage_dir(PipelineStage.PACKAGE)],
            "packaged",
        )
        return CapabilityResult.ok(data=packages, msg="Platform packages ready")


class MetricsImportTool(BaseZeoTool):
    name = "metrics.import"
    version = "1.0.0"

    def run(self, request: MetricsImportRequest, ctx: ToolContext) -> CapabilityResult[list[PerformanceSignal]]:
        import csv
        import json

        store = _store(request.workspace)
        path = request.path
        signals: list[PerformanceSignal] = []
        if path.suffix.lower() == ".json":
            raw = json.loads(path.read_text(encoding="utf-8"))
            items = raw if isinstance(raw, list) else raw.get("signals", [])
            signals = [PerformanceSignal.model_validate(item) for item in items]
        else:
            with path.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    signals.append(
                        PerformanceSignal(
                            moment_id=row["moment_id"],
                            platform=PlatformName(row["platform"]) if row.get("platform") else None,
                            views=int(row.get("views") or 0),
                            retention_3s=float(row["retention_3s"]) if row.get("retention_3s") else None,
                            retention_30s=float(row["retention_30s"]) if row.get("retention_30s") else None,
                            ctr=float(row["ctr"]) if row.get("ctr") else None,
                            comments=int(row.get("comments") or 0),
                        )
                    )
        dest = store.write_json(request.episode_id, PipelineStage.PACKAGE, "metrics.json", signals)
        return CapabilityResult.ok(data=signals, msg=f"Imported {len(signals)} signals to {dest}")
