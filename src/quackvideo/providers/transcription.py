"""Transcription providers."""

from __future__ import annotations

from typing import Protocol

from quackvideo.domain.models import Transcript, TranscriptSegment


class TranscriptionProvider(Protocol):
    name: str

    def transcribe(self, audio_path: str, duration: float, language: str, source_sha256: str) -> Transcript: ...


class FakeTranscriptionProvider:
    name = "fake"

    def transcribe(self, audio_path: str, duration: float, language: str, source_sha256: str) -> Transcript:
        span = max(4.0, min(12.0, duration / 4 or 4.0))
        templates = [
            "Why AI agents fail in production and how to ship anyway.",
            "Here is the workflow we use to turn one recording into a week of content.",
            "Never skip the human review gate before you package clips.",
            "Build the transcript first. Everything else is a derivative.",
        ]
        segments: list[TranscriptSegment] = []
        start = 0.0
        index = 0
        while start < max(duration, 1.0) - 0.1:
            end = min(duration or start + span, start + span)
            text = templates[index % len(templates)]
            segments.append(TranscriptSegment(start=round(start, 3), end=round(end, 3), text=text))
            start = end
            index += 1
        return Transcript(
            language=language,
            provider=self.name,
            source_sha256=source_sha256,
            segments=segments,
            full_text=" ".join(seg.text for seg in segments),
        )


class OpenAITranscriptionProvider:
    name = "openai"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def transcribe(self, audio_path: str, duration: float, language: str, source_sha256: str) -> Transcript:
        import json
        from pathlib import Path

        import httpx

        with Path(audio_path).open("rb") as handle:
            response = httpx.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                data={"model": "whisper-1", "response_format": "verbose_json", "language": language},
                files={"file": handle},
                timeout=120.0,
            )
        response.raise_for_status()
        payload = response.json()
        segments: list[TranscriptSegment] = []
        for item in payload.get("segments", []):
            segments.append(
                TranscriptSegment(
                    start=float(item.get("start", 0)),
                    end=float(item.get("end", 0)),
                    text=str(item.get("text", "")).strip(),
                )
            )
        if not segments:
            segments = [
                TranscriptSegment(
                    start=0.0,
                    end=duration,
                    text=str(payload.get("text", "")).strip() or json.dumps(payload),
                )
            ]
        return Transcript(
            language=language,
            provider=self.name,
            source_sha256=source_sha256,
            segments=segments,
            full_text=str(payload.get("text", " ".join(s.text for s in segments))),
        )


def get_transcription_provider(name: str, openai_api_key: str | None = None) -> TranscriptionProvider:
    if name == "openai":
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY / QUACKVIDEO_OPENAI_API_KEY required for openai transcription")
        return OpenAITranscriptionProvider(openai_api_key)
    return FakeTranscriptionProvider()
