"""CLI 入口定义。"""

from __future__ import annotations

import typer

from .logs import logs_command
from .note import note_app
from .run import run_command
from .tasks import tasks_command

app = typer.Typer(help="StackAndHeap 命令行工具")

app.command("run")(run_command)
app.command("tasks")(tasks_command)
app.command("logs")(logs_command)
app.add_typer(note_app, name="note")


def main() -> None:
    """Typer 入口。"""
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
