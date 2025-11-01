# StackAndHeap

一个基于 openai-agents 运行时的“栈 × 堆”型智能体示例：

- Stack（子任务栈）：用分层子任务管理复杂流程与上下文聚焦。
- Heap（可编辑记忆）：用 Markdown note 持久化知识与决策，支持差异补丁更新。
- Stage（阶段）：按“工作模式”切换工具白名单与补充指令，形成可插拔的工作流。

本仓库已重构为“插件式阶段架构”，内置 `regular`、`conversation`、`summarizing` 与示例阶段 `user_activity_research`（ActivityWatch 数据分析只读）。

---

## 快速开始

1) 安装依赖

```bash
pip install -e .
# 或使用 uv
# uv sync
```

2) 配置环境变量（复制 .env.example 为 .env 并按需修改）

- 必填：`MODEL_NAME`（如 `openai/gemini-2.5-pro` 或你的兼容模型标识）
- 可选：`API_KEY`、`BASE_URL`、`BASIC_CHARACTER_SETTINGS_PATH`、`NOTE_TEMPLATE_PATH`、`SLEEP_TIME_BETWEEN_TURNS`

3) 运行对话循环

```bash
python -m stackandheap.cli run \
  --max-turns 3 \
  --step
```

常用参数：

- `--state-path PATH` 指定上下文保存/加载位置（默认 `logs/conversation.json`）。
- `--max-turns N` 限制轮数，便于试跑。
- `--step` 逐轮确认；`--dry-run` 仅打印将要发送的对话 JSON。

配套命令：

- 查看子任务栈：`python -m stackandheap.cli tasks`（支持 `--state-path`）。
- 展示/导出 note：`python -m stackandheap.cli note show|dump`。
- 查看日志尾部：`python -m stackandheap.cli logs`。

---

## 核心概念

- Stack：`StackAndHeapContext.stack` 保存一组 `Subtask`，每个子任务记录 `messages` 与 `stage`。
- Heap：`context.note` 是持久化 Markdown 记忆；通过工具 `apply_patch_to_note` 以“最小补丁”方式更新，并写入 `logs/note.md`。
- Stage：不同阶段拥有不同工具白名单与附加指令。默认阶段为 `regular`；`conversation` 负责与用户互动；`summarizing` 负责收束与写记忆。

标准闭环：

```
start_subtask →（强制）brainstorm → 使用工具推进 →
判定完成 → finish_subtask → summarizing → apply_patch_to_note → pop_subtask
```

---

## 新阶段（Stage）架构

阶段为可插拔子包，自动发现与注册：

```
stackandheap/agent_core/stages/
  ├─ conversation/
  ├─ regular/
  ├─ summarizing/
  ├─ user_activity_research/   # 示例：ActivityWatch 数据分析（只读）
  ├─ __init__.py               # 自动 import 子包
  ├─ register.py               # 全局注册表（all_stages）
  ├─ stage.py                  # Stage 模型（自动注册）
  └─ readme.md                 # 新增 Stage 指南（强烈推荐先读）
```

每个阶段在其 `__init__.py` 中实例化 `Stage(...)`：

```python
from ..stage import Stage
from ..utils import read_instructions_from_file
from ...tools.built_in import brainstorm, start_subtask, finish_subtask, apply_patch_to_note
from .tools import execute_code_in_repl  # 可选：阶段专属工具

user_activity_research = Stage(
    name="user_activity_research",
    description="Research and analyze user activity data for insights.",
    instructions=read_instructions_from_file(".../user_activity_research.md"),
    tools=[brainstorm, start_subtask, finish_subtask, apply_patch_to_note, execute_code_in_repl],
)
```

注意：工具经 `@register_tools` 装饰后，变量被替换为“工具名字符串”，Stage 的 `tools=[...]` 接受的正是这些字符串。

如何编写新阶段，请参考：`stackandheap/agent_core/stages/readme.md`。

---

## 工具体系（按阶段启用）

内置工具位于 `stackandheap/agent_core/tools/`：

- `built_in.py`
  - `brainstorm(thinking)`：反思/计划。
  - `start_subtask(id, goal, task_type)`：创建子任务并（可选）切换阶段；会把阶段说明注入到输出中。
  - `finish_subtask()`：标记完成，切到 `summarizing`。
  - `apply_patch_to_note(patch)`：把总结写入 note（具备严谨的最小补丁语法）。
  - `pop_subtask(return_value)`：将子任务关键消息回收至父任务并返回父阶段。
  - `send_message_and_wait(content, options)` / `send_message_and_finish_conversation(content)`：在 `conversation` 阶段用以与用户交互。
- `register.py`：集中注册并根据当前阶段过滤可用工具。

示例阶段工具（可选）：

- `user_activity_research/tools.py` 提供 `execute_code_in_repl(code)`，用于在当前进程内执行多行 Python（仅作数据分析演示）。

---

## 动态指令与模型

- `dynamic_instruction.py`：按 `current_stage` 提供不同的系统提示（普通/总结），并包含工作准则与流程图。
- `agent_core/model.py`：通过 `LitellmModel` 使用环境变量：
  - `MODEL_NAME`（必填）
  - `API_KEY`、`BASE_URL`（可选，视提供商而定）

---

## 目录速览

```
stackAndHeap/
├─ main.py                              # 便捷入口（可用 CLI 代替）
├─ stackandheap/agent_core/
│  ├─ context.py                        # Stack/Heap 上下文与持久化
│  ├─ dynamic_instruction.py            # 动态系统提示
│  ├─ main_agent.py                     # Agent 组装（工具来自 tools/register.prepare_all_tools）
│  ├─ model.py                          # 模型适配
│  ├─ stages/                           # 插件式阶段（含新增指南）
│  └─ tools/                            # 内置工具与注册
├─ stackandheap/cli/                    # Typer CLI：run / tasks / note / logs
├─ examples/                            # 角色设定与 note 模板
└─ logs/                                # conversation.json 与 note.md 输出
```

---

## 配置说明（.env）

- `MODEL_NAME`：必填，模型标识（与 LiteLLM 兼容）。
- `API_KEY`：选填，鉴权密钥。
- `BASE_URL`：选填，自定义推理服务地址。
- `BASIC_CHARACTER_SETTINGS_PATH`：角色基本设定 Markdown（默认 `examples/basic_character_settings_1.md`）。
- `NOTE_TEMPLATE_PATH`：note 模板（默认 `examples/note_template.md`）。
- `SLEEP_TIME_BETWEEN_TURNS`：回合间休眠秒数（默认 `0`）。

---

## 开发提示

- 运行 `python -m stackandheap.cli run --dry-run` 查看即将发送的对话载荷。
- 若上下文文件不存在，CLI 会自动创建，并把 note 同步到 `logs/note.md`。
- 新增阶段时建议先阅读 `stages/readme.md`，并复用 `user_activity_research` 的目录与代码结构。
- 如需最小验证，可将 `--max-turns` 设为 `1`，或在 `run.py` 中开启 `quiet` 以减少输出。
