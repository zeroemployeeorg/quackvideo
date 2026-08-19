"""Capability helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel
from zeo_core.contracts import CapabilityResult
from zeo_core.tools import BaseZeoTool

from quackvideo.runtime import build_context


class ToolRunner:
    def run(self, tool: BaseZeoTool, request: BaseModel, work_dir: Path) -> CapabilityResult[Any]:
        ctx = build_context(tool.name or tool.__class__.__name__, tool.version, work_dir, work_dir)
        init = tool.initialize(ctx)
        if init.status != "success":
            return init
        return tool.run(request, ctx)


def fail(message: str, code: str, exc: Exception | None = None) -> CapabilityResult[Any]:
    if exc is None:
        return CapabilityResult.fail(msg=message, code=code)
    return CapabilityResult.fail_from_exc(msg=message, code=code, exc=exc)
