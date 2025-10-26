"""运行相关命令。"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer
from agents import Runner, RunResult, set_trace_processors
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from stackandheap.agent_core import StackAndHeapContext, agent

from .utils import (
    DEFAULT_STATE_PATH,
    build_stack_table,
    load_context,
    prompt_continue,
    render_messages,
    save_context,
)


async def _run_loop(
    ctx: StackAndHeapContext,
    console: Console,
    save_path: Path,
    max_turns: Optional[int],
    step: bool,
    dry_run: bool,
) -> None:
    turn = 0
    while True:
        if max_turns is not None and turn >= max_turns:
            console.print(f"[green]已达到最大轮数 {max_turns}，退出。[/green]")
            break

        console.rule(f"回合 {turn + 1}")

        if dry_run:
            conversation = ctx.build_conversation()
            body = json.dumps(conversation, ensure_ascii=False, indent=2)
            console.print(Panel(Syntax(body, "json", word_wrap=True), title="即将发送的对话"))
            break

        try:
            conversation = ctx.build_conversation()
            result: RunResult = await Runner.run(
                starting_agent=agent,
                input=conversation,
                context=ctx,
            )
        except Exception as exc:  # pragma: no cover - 运行时防御
            console.print(f"[red]运行异常：{exc}[/red]")
            break

        new_messages = [item.to_input_item() for item in result.new_items]
        render_messages(console, new_messages, title="新增消息") # type: ignore

        ctx.add_messages(new_messages)
        save_context(ctx, save_path)
        turn += 1

        console.print(build_stack_table(ctx))

        if step and not prompt_continue(console):
            console.print("[yellow]用户选择结束运行。[/yellow]")
            break


def run_agent(
    state_path: Optional[Path] = None,
    max_turns: Optional[int] = None,
    step: bool = False,
    dry_run: bool = False,
) -> None:
    """运行智能体对话循环的核心实现。"""
    console = Console()
    set_trace_processors([])
    save_path = state_path or DEFAULT_STATE_PATH

    if state_path is not None:
        if state_path.exists():
            console.print(f"[cyan]从 {state_path} 加载上下文。[/cyan]")
            ctx = load_context(state_path)
        else:
            console.print(f"[yellow]指定的状态文件 {state_path} 不存在，将创建新上下文。[/yellow]")
            ctx = StackAndHeapContext()
    else:
        console.print("[cyan]使用全新上下文开始对话。[/cyan]")
        ctx = StackAndHeapContext()

    console.print(build_stack_table(ctx))

    try:
        asyncio.run(_run_loop(ctx, console, save_path, max_turns, step, dry_run))
    except KeyboardInterrupt:
        console.print("\n[red]用户中断，正在保存上下文…[/red]")
    finally:
        save_context(ctx, save_path)
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
) -> None:
    """Typer 命令封装。"""
    run_agent(
        state_path=state_path,
        max_turns=max_turns,
        step=step,
        dry_run=dry_run,
    )
