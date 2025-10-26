# CLI 设计草案

## 背景
当前 `main.py` 使用 `print` 输出代理响应，缺乏结构化控制，无法方便地管理会话、日志与 note。拟开发一个命令行工具提升交互体验与可扩展性。

## 目标
- 以命令行形式启动/控制智能体主循环。
- 支持载入历史上下文、限定运行轮数、单步调试。
- 提供便捷命令查看 note、子任务栈、最近日志。
- 结构化输出（颜色、表格）提升可读性。
- 保持与 `agent_core` 隔离，便于扩展其他前端。

## 命令结构草案
使用 `python -m stackandheap.cli <command>` 或安装后 `stackandheap <command>`。

- `run`
  - 参数：`--load LOG_PATH`、`--max-turns N`、`--dry-run`（仅显示将会发送的消息，不调用真实模型）、`--step`（逐回合确认继续）。
  - 功能：初始化上下文，循环执行智能体，结构化显示每轮新增消息，并在用户确认后续回合。
- `note`
  - 子命令：`show`（展示 note 当前内容）、`dump --out PATH`（导出）。
- `tasks`
  - 功能：打印当前子任务栈，展示 task_id、goal、stage、消息数量。
- `logs`
  - 参数：`--tail N`、`--path PATH`。
  - 功能：快速查看最近对话日志。

## 技术选型
- 使用 `typer` 构建 CLI（基于 `click`，支持类型提示）。若不新增依赖，则使用 `argparse` + `rich`；倾向于引入 `typer` 与 `rich`，兼顾易用性与输出效果。
- 输出渲染：`rich.Console` 提供颜色、高亮、表格与实时刷新。
- 长时间运行需捕获 `KeyboardInterrupt`，优雅保存上下文。

## 模块划分
```
stackAndHeap/
├── cli/
│   ├── __init__.py
│   ├── app.py           # Typer 应用定义
│   ├── run.py           # run 命令实现
│   ├── note.py          # note 命令实现
│   └── utils.py         # 公共输出、上下文加载
```

## 与现有代码的集成
- 抽取 `main.py` 中的循环逻辑至 `agent_core.runner`（或 `cli/run.py` 内的函数），以便 CLI 与脚本复用。
- 保持 `main.py` 可作为最小示例：内部调用 CLI 的 `run` 函数。
- `StackAndHeapContext.save` 继续负责 `conversation.json` 与 `note.md` 持久化。

## 开发步骤
1. 调整依赖：在 `pyproject.toml` 中加入 `typer[all]` 与 `rich`。
2. 新建 `cli` 模块，实现 `Typer` 应用与各命令。
3. 抽取并复用运行循环逻辑，支持 `max_turns`、`step`、`dry_run` 等参数。
4. 为 note、tasks、logs 命令编写工具函数，输出结构化内容。
5. 更新 `main.py` 使用新接口，保留向后兼容。
6. 增补 README 与开发文档，示例演示 CLI 用法。

## 待确认问题
- 是否允许新增第三方依赖（`typer`、`rich`）。
- `dry_run` 模式需要使用模拟响应？可基于 `Runner.run` 的 mock 或跳过模型调用，仅打印计划。
- 是否需要命令行内直接编辑 note（例如调用系统编辑器）。

