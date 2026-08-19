# QuackVideo

Transcript-first content engine for podcasts, talking-head videos, tutorials, and short-form social packages.

QuackVideo turns one recording into a reviewable set of platform-ready files. It does not upload or schedule posts.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- FFmpeg and ffprobe on `PATH`

```bash
uv sync --extra dev
make verify
```

## Workflow

```bash
quackvideo project init --name studio --workspace workspace
quackvideo ingest recording.mp4 --profile talking-head --workspace workspace
quackvideo run EPISODE_ID --until analyze --workspace workspace
quackvideo review list EPISODE_ID --workspace workspace
quackvideo review approve EPISODE_ID MOMENT_ID --workspace workspace
quackvideo compose EPISODE_ID --workspace workspace
quackvideo package EPISODE_ID --workspace workspace
```

Profiles: `podcast`, `talking-head`, `tutorial`, `social`.

Every command accepts `--json` for agents.

## Output layout

```
workspace/episodes/<id>/
  source/                 immutable copy of the recording
  artifacts/ingest/       probe + QC
  artifacts/normalize/    loudnorm audio + mezzanine
  artifacts/transcript/   json, srt, vtt, markdown
  artifacts/analyze/      chapters + ranked moments
  artifacts/review/       approval manifest
  artifacts/compose/      approved clips + captions
  artifacts/packages/     per-platform handoff directories
```

Compose and package run only after at least one moment is approved.

## Providers

Default transcription is `fake` (deterministic, for tests and dry runs).

```bash
export QUACKVIDEO_TRANSCRIPTION_PROVIDER=openai
export QUACKVIDEO_OPENAI_API_KEY=...
```

Analysis defaults to a heuristic ranker that uses transcript windows, duration policy, scene cuts, and imported performance signals.

```bash
quackvideo metrics import EPISODE_ID stats.csv --workspace workspace
```

CSV columns: `moment_id,platform,views,retention_3s,retention_30s,ctr,comments`.

## License

MIT
