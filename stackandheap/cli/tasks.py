"""任务栈相关命令。"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from .utils import build_stack_table, load_context, DEFAULT_STATE_PATH


def tasks_command(
    state_path: Optional[Path] = typer.Option(
        DEFAULT_STATE_PATH,
        "--state-path",
        "-s",
        help="上下文路径",
    ),
) -> None:
    """查看当前子任务栈。"""
    console = Console()
    ctx = load_context(state_path)
    console.print(build_stack_table(ctx))
