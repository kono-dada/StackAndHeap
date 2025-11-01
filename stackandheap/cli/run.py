"""运行相关命令。"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Optional
import time
import dotenv
import os

import typer
from agents import Runner, RunResult, set_trace_processors
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from stackandheap.agent_core import StackAndHeapContext, agent

from .utils import (
    DEFAULT_STATE_PATH,
    build_stack_table,
    display_character_message,
    load_context,
    prompt_continue,
    prompt_user_reply,
    render_messages,
    save_context,
)

dotenv.load_dotenv()
sleep_time_between_turns = float(os.getenv("SLEEP_TIME_BETWEEN_TURNS", "0.0"))


def _parse_interaction_event(output: Any) -> Optional[dict[str, Any]]:
    if not isinstance(output, str):
        return None
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    event_type = data.get("type")
    if event_type not in {"await_user", "display_message"}:
        return None
    content = str(data.get("content", ""))
    event: dict[str, Any] = {"type": event_type, "content": content}
    if event_type == "await_user":
        raw_options = data.get("options") or []
        if not isinstance(raw_options, (list, tuple)):
            raw_options = []
        event["options"] = [str(item) for item in raw_options]
    if event_type == "display_message":
        event["final"] = bool(data.get("final"))
    return event


async def _run_loop(
    ctx: StackAndHeapContext,
    console: Console,
    save_path: Path,
    max_turns: Optional[int],
    step: bool,
    dry_run: bool,
    quiet: bool,
) -> None:
    turn = 0
    spinner_frames = ["⠋", "⠙", "⠚", "⠞", "⠖", "⠦", "⠴", "⠸", "⠼", "⠷", "⠛", "⠓"]

    async def _spinner_task(stop_event: asyncio.Event) -> None:
        frame = 0
        with Live(
            Text(""),
            console=console,
            refresh_per_second=12,
            transient=True,
        ) as live:
            while not stop_event.is_set():
                symbol = spinner_frames[frame % len(spinner_frames)]
                frame += 1
                total_messages = sum(len(sub.messages) for sub in ctx.stack)
                stage = getattr(ctx, "current_stage", "unknown")
                content = Text()
                content.append(f"{symbol} 工作中…（按 Ctrl+C 可中断）", style="bold cyan")
                content.append("\n")
                content.append("阶段: ", style="dim")
                content.append(str(stage), style="magenta")
                content.append(" | 栈消息数: ", style="dim")
                content.append(str(total_messages), style="green")
                live.update(
                    Panel(
                        content,
                        border_style="cyan",
                        padding=(0, 1),
                    )
                )
                await asyncio.sleep(0.1)

    while True:
        if max_turns is not None and turn >= max_turns:
            if not quiet:
                console.print(f"[green]已达到最大轮数 {max_turns}，退出。[/green]")
            break

        if not quiet:
            console.rule(f"回合 {turn + 1}")

        if dry_run:
            conversation = ctx.build_conversation()
            body = json.dumps(conversation, ensure_ascii=False, indent=2)
            if not quiet:
                console.print(Panel(Syntax(body, "json", word_wrap=True), title="即将发送的对话"))
            break

        spinner_stop: Optional[asyncio.Event] = None
        spinner_task: Optional[asyncio.Task[None]] = None
        try:
            conversation = ctx.build_conversation()
            if quiet:
                spinner_stop = asyncio.Event()
                spinner_task = asyncio.create_task(_spinner_task(spinner_stop))
            result: RunResult = await Runner.run(
                starting_agent=agent,
                input=conversation,
                context=ctx,
            )
        except Exception as exc:  # pragma: no cover - 运行时防御
            console.print(f"[red]运行异常：{exc}[/red]")
            break
        finally:
            if spinner_stop is not None:
                spinner_stop.set()
            if spinner_task is not None:
                await spinner_task

        new_messages = []
        for item in result.new_items:
            message = item.to_input_item()
            if message.get("type") == "function_call_output":
                event = _parse_interaction_event(message.get("output"))
                if event is not None:
                    if event["type"] == "await_user":
                        user_reply = await prompt_user_reply(
                            console,
                            content=event["content"],
                            options=event.get("options", []),
                        )
                        if user_reply is None:
                            message["output"] = "<system>No response</system>"  # type: ignore
                        else:
                            message["output"] = f'<system>The user replied: {user_reply}</system>'  # type: ignore
                    elif event["type"] == "display_message":
                        display_character_message(console, event["content"])
                        if event.get("final"):
                            message["output"] = f'<system>Conversation stage finished. Final message delivered.</system>'  # type: ignore
                            if not quiet:
                                console.print("[green]对话阶段已结束，已切换到总结流程。[/green]")
                        else:
                            message["output"] = 'None' # type: ignore
            new_messages.append(message)

        if not quiet:
            render_messages(console, new_messages, title="新增消息") # type: ignore

        ctx.add_messages(new_messages)
        save_context(ctx, save_path)
        turn += 1

        if not quiet:
            console.print(build_stack_table(ctx))

        if step and not prompt_continue(console):
            if not quiet:
                console.print("[yellow]用户选择结束运行。[/yellow]")
            break
        time.sleep(sleep_time_between_turns)


def run_agent(
    state_path: Optional[Path] = None,
    max_turns: Optional[int] = None,
    step: bool = False,
    dry_run: bool = False,
    quiet: bool = False,
) -> None:
    """运行智能体对话循环的核心实现。"""
    console = Console()
    set_trace_processors([])
    save_path = state_path or DEFAULT_STATE_PATH

    if state_path is not None:
        if state_path.exists():
            if not quiet:
                console.print(f"[cyan]从 {state_path} 加载上下文。[/cyan]")
            ctx = load_context(state_path)
        else:
            if not quiet:
                console.print(f"[yellow]指定的状态文件 {state_path} 不存在，将创建新上下文。[/yellow]")
            ctx = StackAndHeapContext()
    else:
        if not quiet:
            console.print("[cyan]使用全新上下文开始对话。[/cyan]")
        ctx = StackAndHeapContext()

    if not quiet:
        console.print(build_stack_table(ctx))

    try:
        asyncio.run(_run_loop(ctx, console, save_path, max_turns, step, dry_run, quiet))
    except KeyboardInterrupt:
        if not quiet:
            console.print("\n[red]用户中断，正在保存上下文…[/red]")
    finally:
        save_context(ctx, save_path)
        if not quiet:
            console.print(f"[green]上下文已保存到 {save_path}[/green]")


def run_command(
    state_path: Optional[Path] = typer.Option(
        None,
        "--state-path",
        "-s",
        help="上下文保存/加载路径（未指定时从头开始并保存到 logs/conversation.json）",
    ),
    max_turns: Optional[int] = typer.Option(
        None,
        "--max-turns",
        "-n",
        min=1,
        help="限制运行回合数",
    ),
    step: bool = typer.Option(
        False,
        "--step",
        help="逐回合确认是否继续",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="仅展示将要发送的对话，不调用模型",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        help="安静模式，仅展示角色输出和必要输入提示",
    ),
) -> None:
    """Typer 命令封装。"""
    run_agent(
        state_path=state_path,
        max_turns=max_turns,
        step=step,
        dry_run=dry_run,
        quiet=quiet,
    )
