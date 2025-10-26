"""日志查看命令。"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from .utils import DEFAULT_STATE_PATH, tail_text_file


def logs_command(
    path: Optional[Path] = typer.Option(
        DEFAULT_STATE_PATH,
        "--path",
        "-p",
        help="日志文件路径",
    ),
    lines: int = typer.Option(
        50,
        "--lines",
        "-n",
        help="显示末尾多少行，<=0 表示全部",
    ),
) -> None:
    """查看 conversation.json 等文本日志的尾部。"""
    console = Console()
    target = path or DEFAULT_STATE_PATH
    if not target.exists():
        console.print(f"[red]日志不存在：{target}[/red]")
        raise typer.Exit(code=1)
    text = tail_text_file(target, lines)
    syntax = Syntax(text, "json", theme="monokai", word_wrap=True)
    console.print(Panel(syntax, title=f"tail -n {lines} {target}"))
