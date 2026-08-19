---
name: quackvideo
description: Run the QuackVideo creator flywheel from Claude Code. Use when ingesting recordings, transcribing, ranking clips, reviewing moments, composing captions, or packaging platform-ready social/podcast/tutorial assets.
---

# QuackVideo

Drive the `quackvideo` CLI. Do not reimplement FFmpeg, transcription, or packaging in ad-hoc scripts.

## Preconditions

1. `uv sync --extra dev` in the repo.
2. `ffmpeg` and `ffprobe` on PATH (`quackvideo doctor --json`).
3. A workspace directory (`quackvideo project init` or `--workspace`).

## Canonical loop

```bash
quackvideo ingest SOURCE --profile PROFILE --workspace WS --json
quackvideo run EPISODE_ID --until analyze --workspace WS --json
quackvideo review list EPISODE_ID --workspace WS --json
# stop for human approval
quackvideo review approve EPISODE_ID MOMENT_ID --workspace WS --json
quackvideo compose EPISODE_ID --workspace WS --json
quackvideo package EPISODE_ID --workspace WS --json
```

Profiles: `podcast`, `talking-head`, `tutorial`, `social`.

## Rules

- Prefer `--json` so results are machine-readable.
- Never compose or package until at least one moment is `approved`.
- Do not upload or publish. Packages are the handoff.
- Resume is hash-based; use `--force` only when asked.
- Inspect artifacts under `workspace/episodes/<id>/artifacts/` on failure.
- Default transcription provider is `fake`. Use `openai` only when an API key is configured.
- Do not commit `.env`, API keys, or generated media workspaces.
