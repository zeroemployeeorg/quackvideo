"""Moment ranking and chaptering."""

from __future__ import annotations

import hashlib
import re

from quackvideo.domain.enums import ContentProfile
from quackvideo.domain.models import (
    Chapter,
    Moment,
    MomentScores,
    PerformanceSignal,
    Transcript,
)
from quackvideo.domain.profiles import CLIP_WINDOW, DEFAULT_CLIP_COUNT

HOOK_WORDS = {
    "secret",
    "why",
    "never",
    "stop",
    "wrong",
    "mistake",
    "build",
    "ship",
    "agent",
    "ai",
    "claude",
    "cursor",
    "how",
    "lesson",
    "tip",
}


def _windows(transcript: Transcript, min_dur: float, max_dur: float) -> list[tuple[float, float, str]]:
    if not transcript.segments:
        duration = 30.0
        return [(0.0, min(max_dur, duration), transcript.full_text)]
    windows: list[tuple[float, float, str]] = []
    current: list[str] = []
    start = transcript.segments[0].start
    for segment in transcript.segments:
        current.append(segment.text)
        span = segment.end - start
        if span >= min_dur:
            text = " ".join(current).strip()
            windows.append((start, min(segment.end, start + max_dur), text))
            start = segment.end
            current = []
    if current:
        last_end = transcript.segments[-1].end
        windows.append((start, last_end, " ".join(current).strip()))
    return windows


def _score(text: str, duration: float, min_dur: float, max_dur: float, prior: float) -> MomentScores:
    words = re.findall(r"[a-zA-Z0-9']+", text.lower())
    density = min(1.0, len(words) / 40.0)
    hook = 1.0 if words and words[0] in HOOK_WORDS else 0.4
    if any(word in HOOK_WORDS for word in words[:8]):
        hook = max(hook, 0.75)
    fit = 1.0 if min_dur <= duration <= max_dur else 0.4
    standalone = 0.8 if text.endswith((".", "!", "?")) else 0.5
    novelty = min(1.0, len(set(words)) / max(len(words), 1))
    return MomentScores(
        hook=hook,
        standalone=standalone,
        novelty=novelty,
        density=density,
        platform_fit=fit,
        prior_performance=prior,
    )


def rank_moments(
    transcript: Transcript,
    profile: ContentProfile,
    scene_cuts: list[float] | None = None,
    prior: list[PerformanceSignal] | None = None,
) -> list[Moment]:
    min_dur, max_dur = CLIP_WINDOW[profile]
    target = DEFAULT_CLIP_COUNT[profile]
    prior_by_id = {item.moment_id: item for item in prior or []}
    windows = _windows(transcript, min_dur, max_dur)
    moments: list[Moment] = []
    for index, (start, end, text) in enumerate(windows):
        moment_id = hashlib.sha256(f"{start:.2f}:{end:.2f}:{text[:40]}".encode()).hexdigest()[:10]
        prior_score = 0.0
        if moment_id in prior_by_id:
            signal = prior_by_id[moment_id]
            prior_score = min(1.0, (signal.retention_3s or 0) * 0.5 + min(signal.views, 10000) / 10000)
        near_cut = any(abs(cut - start) < 1.5 for cut in scene_cuts or [])
        scores = _score(text, end - start, min_dur, max_dur, prior_score)
        if near_cut:
            scores.hook = min(1.0, scores.hook + 0.1)
        first_sentence = re.split(r"[.!?]", text, maxsplit=1)[0].strip() or text[:80]
        moments.append(
            Moment(
                moment_id=f"m{index:03d}-{moment_id}",
                start=round(start, 3),
                end=round(end, 3),
                title=first_sentence[:72] or f"Clip {index + 1}",
                hook=first_sentence[:120],
                rationale="Ranked from transcript windows, duration policy, and optional scene cuts.",
                tags=[profile.value],
                scores=scores,
            )
        )
    moments.sort(key=lambda item: item.scores.total, reverse=True)
    return moments[: max(target, 3)]


def chapters_from_transcript(transcript: Transcript, max_chapters: int = 8) -> list[Chapter]:
    if not transcript.segments:
        return [Chapter(index=1, start=0.0, end=0.0, title="Full episode")]
    duration = transcript.segments[-1].end
    step = max(duration / max_chapters, 30.0)
    chapters: list[Chapter] = []
    cursor = 0.0
    index = 1
    while cursor < duration - 5 and len(chapters) < max_chapters:
        end = min(duration, cursor + step)
        covering = [s for s in transcript.segments if s.start < end and s.end > cursor]
        title = covering[0].text[:60] if covering else f"Chapter {index}"
        chapters.append(
            Chapter(
                index=index,
                start=round(cursor, 3),
                end=round(end, 3),
                title=title.strip(),
                summary=" ".join(s.text for s in covering)[:240],
            )
        )
        cursor = end
        index += 1
    return chapters
