"""note 相关命令。"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from .utils import DEFAULT_NOTE_PATH, load_context, show_note

note_app = typer.Typer(help="note 管理")


@note_app.command("show")
def show_note_cmd(
    state_path: Optional[Path] = typer.Option(
        None,
        "--state-path",
        "-s",
        help="上下文路径（用于载入 note）",
    ),
    note_path: Optional[Path] = typer.Option(
        DEFAULT_NOTE_PATH,
        "--note-path",
        "-n",
        help="note 文件路径",
    ),
) -> None:
    """展示当前 note 内容。"""
    console = Console()
    if state_path:
        ctx = load_context(state_path)
        # 再次保存确保 note 同步
        ctx.save(str(state_path))
    show_note(console, note_path)


@note_app.command("dump")
def dump_note_cmd(
    out: Path = typer.Argument(..., help="导出目标路径"),
    note_path: Optional[Path] = typer.Option(
        DEFAULT_NOTE_PATH,
        "--note-path",
        "-n",
        help="note 文件路径",
    ),
) -> None:
    """导出 note 到指定位置。"""
    console = Console()
    path = note_path or DEFAULT_NOTE_PATH
    if not path.exists():
        console.print(f"[red]note 不存在：{path}[/red]")
        raise typer.Exit(code=1)
    out.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    console.print(f"[green]note 已导出到 {out}[/green]")
