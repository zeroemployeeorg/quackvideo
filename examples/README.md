# Examples

Use the packaged CLI rather than the old Fire scripts.

```bash
quackvideo media synth demo.mp4 --kind video --duration 6
quackvideo ingest demo.mp4 --profile talking-head --workspace workspace
quackvideo run $(ls workspace/episodes) --until analyze --workspace workspace
```

Podcast audio:

```bash
quackvideo media synth demo.flac --kind audio --duration 12
quackvideo ingest demo.flac --profile podcast --workspace workspace
```
