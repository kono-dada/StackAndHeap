"""CLI 公共工具函数。"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Iterable, Optional, Sequence

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

try:  # Typer 依赖已包含 prompt_toolkit，仍做兜底判断
    from prompt_toolkit import PromptSession
    from prompt_toolkit.key_binding import KeyBindings
except Exception:  # pragma: no cover - 运行环境缺乏 prompt_toolkit
    PromptSession = None  # type: ignore
    KeyBindings = None  # type: ignore

from stackandheap.agent_core import StackAndHeapContext

DEFAULT_STATE_PATH = Path("logs/conversation.json")
DEFAULT_NOTE_PATH = Path("logs/note.md")


def load_context(state_path: Optional[Path]) -> StackAndHeapContext:
    """从给定路径加载上下文，不存在则创建新上下文。"""
    if state_path is None:
        return StackAndHeapContext()
    path = state_path
    if path.exists():
        return StackAndHeapContext.load(str(path))
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    return StackAndHeapContext()


def save_context(ctx: StackAndHeapContext, state_path: Optional[Path]) -> None:
    """保存上下文到指定路径，默认写入日志目录。"""
    path = state_path or DEFAULT_STATE_PATH
    if not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    ctx.save(str(path))


def render_messages(console: Console, messages: Iterable[dict], title: str) -> None:
    """以 JSON 高亮展示消息。"""
    messages = list(messages)
    if not messages:
        console.print(Panel(Text("(无新增消息)"), title=title, expand=False))
        return
    for idx, msg in enumerate(messages, start=1):
        body = json.dumps(msg, ensure_ascii=False, indent=2)
        syntax = Syntax(body, "json", word_wrap=True)
        panel_title = f"{title} #{idx}"
        console.print(Panel(syntax, title=panel_title, expand=False))


def build_stack_table(ctx: StackAndHeapContext) -> Table:
    """构建展示子任务栈的表格。"""
    table = Table(title="当前子任务栈", show_lines=True)
    table.add_column("序号", justify="right")
    table.add_column("task_id")
    table.add_column("goal")
    table.add_column("stage")
    table.add_column("消息数", justify="right")
    for idx, subtask in enumerate(ctx.stack):
        table.add_row(
            str(idx),
            subtask.task_id,
            subtask.goal,
            getattr(subtask, "stage", "unknown"),
            str(len(subtask.messages))
        )
    return table


def show_note(console: Console, note_path: Optional[Path]) -> None:
    """渲染 note 内容。"""
    path = note_path or DEFAULT_NOTE_PATH
    if not path.exists():
        console.print(f"[yellow]未找到 note：{path}[/yellow]")
        return
    text = path.read_text(encoding="utf-8")
    syntax = Syntax(text, "markdown", theme="monokai", word_wrap=True)
    console.print(Panel(syntax, title=f"note @ {path}", expand=False))


def tail_text_file(path: Path, lines: int) -> str:
    """简单读取文本文件尾部。"""
    if not path.exists():
        return ""
    content = path.read_text(encoding="utf-8").splitlines()
    if lines <= 0:
        return "\n".join(content)
    return "\n".join(content[-lines:])


def prompt_continue(console: Console) -> bool:
    """询问是否继续下一轮。"""
    answer = console.input("[bold cyan]继续下一轮？(y/N): [/]")
    return answer.strip().lower() in {"y", "yes"}


def display_character_message(console: Console, content: str) -> None:
    """仅展示角色消息，不要求用户输入。"""
    console.rule("[magenta]角色来信[/magenta]")
    console.print(Panel(Text(content), title="角色台词", expand=False))


async def prompt_user_reply(console: Console, content: str, options: Sequence[str]) -> Optional[str]:
    """展示角色消息并获取用户输入。返回 None 表示不回复。"""
    display_character_message(console, content)

    if options:
        table = Table(title="推荐短句", expand=False, show_edge=False, show_header=False)
        for idx, option in enumerate(options, start=1):
            table.add_row(f"[cyan]{idx}[/cyan]", option)
        console.print(table)
    console.print(
        "[bold cyan]提示：上下方向键切换推荐短句，直接输入文字自定义，回车留空或输入 skip/0 表示不回复。[/bold cyan]"
    )

    if PromptSession is None or KeyBindings is None:
        raw = await asyncio.to_thread(lambda: console.input("[bold green]回复> [/]").strip())
    else:
        session = PromptSession()
        kb = KeyBindings()
        cursor = {"index": -1}

        def apply_choice(buffer, new_index: int) -> None:
            if not options:
                return
            option = options[new_index]
            buffer.text = option
            buffer.cursor_position = len(option)
            cursor["index"] = new_index

        @kb.add("up")
        def _(event):  # pragma: no cover - 键位行为难以单测
            if not options:
                return
            new_index = (cursor["index"] - 1) % len(options)
            apply_choice(event.app.current_buffer, new_index)

        @kb.add("down")
        def _(event):  # pragma: no cover - 键位行为难以单测
            if not options:
                return
            new_index = (cursor["index"] + 1) % len(options)
            apply_choice(event.app.current_buffer, new_index)

        raw = (await session.prompt_async("[bold green]回复> [/]", key_bindings=kb)).strip()

    if raw == "" or raw.lower() in {"skip", "0"}:
        return None
    if raw.isdigit():
        idx = int(raw)
        if 1 <= idx <= len(options):
            return options[idx - 1]
    return raw
