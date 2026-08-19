"""ZeoCore ToolContext factory used by the CLI runner."""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import uuid4

from zeo_core.core.fs import get_service as get_fs_service
from zeo_core.tools import ToolContext


def build_context(
    tool_name: str,
    tool_version: str = "1.0.0",
    work_dir: Path | None = None,
    output_dir: Path | None = None,
) -> ToolContext:
    root = work_dir or Path.cwd()
    out = output_dir or root
    return ToolContext(
        run_id=str(uuid4()),
        tool_name=tool_name,
        tool_version=tool_version,
        logger=logging.getLogger(f"quackvideo.{tool_name}"),
        fs=get_fs_service(),
        work_dir=str(root),
        output_dir=str(out),
    )
