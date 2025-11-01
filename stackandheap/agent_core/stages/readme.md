# 如何新增一个 Stage（以 `user_activity_research` 为例）

本文档说明如何在 `stackandheap/agent_core/stages` 下新增一个自定义 Stage，并让它在运行时被自动发现、加载与启用。示例以现有的 `user_activity_research` 为蓝本。

## Stage 是什么

一个 Stage 描述了代理在某一“工作模式”下的：

- `name`: 阶段名称（唯一标识）。
- `description`: 阶段简介（用于文档/可视化）。
- `instructions`: 进入该阶段后追加的“补充指令”（影响行为习惯/注意事项）。
- `tools`: 本阶段允许调用的工具（以工具名字符串为元素）。
- `visible`: 是否在候选阶段列表中展示（默认 `True`）。

对应的模型定义见 `stackandheap/agent_core/stages/stage.py`。

## 目录结构（示例）

```
stackandheap/agent_core/stages/
  ├─ user_activity_research/
  │   ├─ __init__.py              # 声明并注册 Stage
  │   ├─ tools.py                 # （可选）仅此 Stage 使用的工具
  │   └─ user_activity_research.md# 本阶段的补充说明/操作指引
  ├─ conversation/
  ├─ regular/
  ├─ summarizing/
  ├─ __init__.py                  # 自动发现各子包（见“注册与发现”）
  ├─ register.py
  ├─ stage.py
  └─ readme.md                    # 本文件
```

## 快速上手：新增一个 Stage 的步骤

1) 新建目录：`stackandheap/agent_core/stages/<your_stage_name>`

2) 写阶段说明：在该目录放置 `<your_stage_name>.md`，内容用于运行时作为“补充指令”（会在 `start_subtask` 进入该 Stage 时附加给模型）。示例参见 `stackandheap/agent_core/stages/user_activity_research/user_activity_research.md`。

3) 定义（可选）专属工具：在 `tools.py` 中定义仅在本阶段开放的工具函数，使用装饰器 `@register_tools` 进行注册；必要时可以叠加：

   - `@require_not_in_main_loop`：强制要求在某个子任务上下文内调用。
   - `@remaining_frame_space_reminder`：在上下文接近上限时追加提醒。

   注意：`@register_tools` 会把函数加入全局工具表，并把同名变量替换为“工具名字符串”。因此在 Stage 声明里引用的应该是“变量名（字符串）”，而不是可调用对象。

   例（节选自 `user_activity_research/tools.py`）：

   ```python
   # stackandheap/agent_core/stages/user_activity_research/tools.py
   from agents import function_tool, RunContextWrapper
   from ...decorators import remaining_frame_space_reminder, require_not_in_main_loop
   from ...tools import register_tools

   @register_tools
   @remaining_frame_space_reminder
   @require_not_in_main_loop
   def execute_code_in_repl(wrapper, code: str) -> str:
       """Execute code in an in-process REPL and return stdout/stderr."""
       ...
   ```

4) 声明并注册 Stage：在 `__init__.py` 中实例化 `Stage`。实例化时会自动调用内部注册逻辑（见 `Stage.__init__`）。

   例（`user_activity_research/__init__.py` 核心结构）：

   ```python
   # stackandheap/agent_core/stages/user_activity_research/__init__.py
   from ..stage import Stage
   from ...tools.built_in import brainstorm, start_subtask, finish_subtask, apply_patch_to_note
   from ..utils import read_instructions_from_file
   from .tools import execute_code_in_repl
   import os

   user_activity_research = Stage(
       name="user_activity_research",
       description="Research and analyze user activity data for insights.",
       instructions=read_instructions_from_file(
           os.path.join(os.path.dirname(os.path.abspath(__file__)), 'user_activity_research.md')
       ),
       tools=[
           brainstorm,
           start_subtask,
           finish_subtask,
           apply_patch_to_note,
           execute_code_in_repl,   # 专属工具
       ],
   )
   ```

   关键点：
   - `tools` 列表中的元素是“工具名字符串”（因为 `@register_tools` 的返回值即为字符串）。
   - `instructions` 可使用 `read_instructions_from_file` 从同目录的 `.md` 读入，便于维护长文档。
   - 如果希望该 Stage 只在内部使用、不出现在可选列表中，可设置 `visible=False`。

5) 注册与发现：无需手动把 Stage 加入任何全局列表。

   - `stackandheap/agent_core/stages/__init__.py` 会在包导入时自动遍历并 `import` 所有子目录（子包）。
   - 每个子包的顶层 `Stage(...)` 实例化会通过 `register_stage` 自动加入全局 `all_stages`。

## 在对话中启用你的 Stage

- 通过工具 `start_subtask(subtask_id, subtask_goal, task_type)` 切换 Stage：

  - 若 `task_type` 设为你的阶段名（如 `"user_activity_research"`），会直接切换并把该阶段的 `instructions` 追加给模型。
  - 若不指定 `task_type`，默认进入 `regular` 阶段。

  示例（逻辑层面）：

  ```text
  调用：start_subtask("research-001", "分析近两周活跃度", task_type="user_activity_research")
  效果：切换到 user_activity_research，随即可用 tools 仅为该阶段白名单内的工具
  ```

## 工具启用规则（重要）

- 只有当“工具名字符串”存在于当前阶段 `tools` 列表中时，该工具才会被 `is_enabled` 放行。
- 请确保：
  - 工具函数已用 `@register_tools` 装饰（否则不会被注册，Stage 中也拿不到正确的字符串名）。
  - 在 Stage 的 `tools` 列表中引用的变量名，正是被装饰器替换后的“字符串”。

## 常见问题与排错

- 症状：工具明明写了，但调用时提示不可用。
  - 排查：是否忘记给工具加 `@register_tools`？Stage 中 `tools=[...]` 是否使用了函数对象而非字符串？

- 症状：进入 Stage 后没有看到补充指令。
  - 排查：是否在 `__init__.py` 中正确加载了 `<stage>.md`，路径是否使用了 `os.path.dirname(os.path.abspath(__file__))`？

- 症状：新 Stage 未被识别。
  - 排查：目录是否为“子包”（包含 `__init__.py`）？是否存在顶层的 `Stage(...)` 实例化？

## 进一步参考

- 现有 Stage：
  - `stackandheap/agent_core/stages/user_activity_research`（含示例工具与详细 `.md` 指南）
  - `stackandheap/agent_core/stages/conversation`
  - `stackandheap/agent_core/stages/regular`
  - `stackandheap/agent_core/stages/summarizing`

如需我按照你要实现的场景（名称/目标/可用工具）直接脚手架一个新 Stage，请告诉我：

- 阶段名（英文小写、下划线分隔）
- 阶段描述（1–2 句）
- 补充指令要点（列表）
- 需要开放的工具（内置/自定义）及其参数
