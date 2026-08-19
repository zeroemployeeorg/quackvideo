"""Optional LLM analysis with heuristic fallback."""

from __future__ import annotations

from typing import Protocol

from quackvideo.analysis.moments import rank_moments
from quackvideo.domain.enums import ContentProfile
from quackvideo.domain.models import Moment, PerformanceSignal, Transcript


class AnalysisProvider(Protocol):
    name: str

    def propose(
        self,
        transcript: Transcript,
        profile: ContentProfile,
        scene_cuts: list[float],
        prior: list[PerformanceSignal],
    ) -> list[Moment]: ...


class HeuristicAnalysisProvider:
    name = "heuristic"

    def propose(
        self,
        transcript: Transcript,
        profile: ContentProfile,
        scene_cuts: list[float],
        prior: list[PerformanceSignal],
    ) -> list[Moment]:
        return rank_moments(transcript, profile, scene_cuts=scene_cuts, prior=prior)


def get_analysis_provider(name: str) -> AnalysisProvider:
    return HeuristicAnalysisProvider()
