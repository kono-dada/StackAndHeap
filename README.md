# StackAndHeap

## 项目简介
StackAndHeap 是一个围绕 `openai-agents` 运行时构建的示例型智能体项目，通过「栈（Stack）」与「堆（Heap）」的比喻来管理对话状态与长期记忆。最新版本将核心逻辑收敛到 `agent_core` 模块，并引入可选 `conversation` 阶段，以模拟视觉小说编剧型角色与用户之间的高参与度互动，同时强调子任务拆分、过程反思与记忆沉淀。

## 核心设计理念
- **Stack：子任务调用栈** —— `StackAndHeapContext` 维护一个由 `Subtask` 组成的栈，每个子任务持有自己的消息列表，并记录所属阶段。栈顶子任务代表当前聚焦的子目标，结束后通过 `finish_subtask → pop_subtask` 收束上下文，并回溯到父任务的阶段。
- **Heap：可编辑长期记忆** —— `context.note` 以分层 Markdown 结构保存角色设定、工作记录、用户画像等信息。借助 `apply_patch_to_note` 工具，记忆以差异补丁方式迭代更新，同时同步保存在 `logs/note.md` 便于审阅。
- **阶段化指令** —— `dynamic_instruction` 根据 `current_stage` （`main_loop` / `conversation` / `summarizing`）切换合适的提示词，引导智能体在不同阶段执行对应职责。
- **任务阶段驱动** —— 通过 `start_subtask(..., task_type)` 在创建子任务时指定阶段，例如 `conversation` 用于高频对话、`None`（或 `regular`）用于常规思考，从而让流程和工具选择更具针对性。

## 运行流程概览
1. `main.py` 从 `agent_core` 引入 Agent 与上下文模型，执行 `set_trace_processors([])` 关闭内置 trace 处理器，然后初始化 `StackAndHeapContext` 并在循环中调用 `Runner.run`，最终将最新对话写入 `logs/conversation.json` 与 `logs/note.md`。
2. `agent_core/main_agent.py` 聚合模型、动态指令与工具集，`dynamic_instruction` 会基于上下文阶段生成合适的提示词模板。
3. 在 `main_loop` 阶段，智能体必须通过 `start_subtask → brainstorm` 锁定目标；若 `start_subtask` 设置 `task_type="conversation"`，则立即切换到高互动的 `conversation` 阶段。
4. `conversation` 阶段通过 `send_message_and_wait`/`send_message_and_finish_conversation` 与真实用户交互，同时收集 `user_response_options` 以引导短句反馈；当对话无法继续时结束该阶段并转入总结。
5. `summarizing` 阶段负责调用 `apply_patch_to_note` 整理记忆并 `pop_subtask`，随后恢复到父任务的阶段，以延续后续流程。

### 流程示意
```
main_loop ──start_subtask(task_type=main_loop/None)──▶ brainstorm ──▶ (工具调用 / 继续拆分)
      │                                                     │
      └──子任务完成──▶ finish_subtask ──▶ summarizing ──apply_patch_to_note──▶ pop_subtask
                                                                  │
                                                                  └──> 回到父任务阶段

main_loop ──start_subtask(task_type="conversation")──▶ conversation ──send_message_and_wait──▶ 用户回复
      │
      └──需要收束对话──▶ send_message_and_finish_conversation ──▶ summarizing
```

## 目录结构
```
stackAndHeap/
├── main.py                # 事件循环入口
├── agent_core/
│   ├── context.py         # 上下文模型与栈/堆维护逻辑
│   ├── dynamic_instruction.py # 阶段化提示词
│   ├── main_agent.py      # Agent 定义与工具注册
│   ├── model.py           # 基于 LiteLLM 的模型适配
│   ├── tools.py           # 工具函数及阶段约束
│   └── utils.py           # 通用工具（消息检索、补丁应用）
├── logs/                  # 对话与 note 持久化输出目录（conversation.json / note.md）
├── test.py                # `apply_patch` 行为示例
├── pyproject.toml         # 项目配置与依赖
└── uv.lock                # 依赖锁定文件
```

## 关键模块说明
- `StackAndHeapContext`（`agent_core/context.py`）：基于 Pydantic 定义上下文，提供 `build_conversation`、`push_subtask(stage)`、`pop_subtask`、`apply_patch_to_note` 等方法，实现阶段感知的对话栈与笔记管理，并在 `save` 时同步写出 `note.md`。
- `dynamic_instruction.py`：根据 `current_stage` 自动切换到 `main_loop`、`conversation`、`summarizing` 对应的角色设定与操作规程，确保各阶段行为一致。
- `tools.py`：封装 `brainstorm`、`start_subtask`（支持 `task_type` 参数）、`send_message_and_wait`、`send_message_and_finish_conversation`、`finish_subtask`、`apply_patch_to_note`、`pop_subtask` 等工具，利用装饰器约束调用时机，保证流程规范。
- `model.py`：加载环境变量 `MODEL_NAME`、`API_KEY`、`BASE_URL`，通过 `LitellmModel` 适配到统一推理接口。
- `main.py`：负责调度 `Runner.run`、打印代理输出、清空默认 trace 处理器并保存上下文，是脚本启动入口。
- `utils.py`：提供 `find_the_first_message_of_type` 以及自定义 diff 解析器 `apply_patch`，支撑 note 更新机制。

## 工具与阶段约束
- `start_subtask(subtask_id, subtask_goal, task_type)`：进入任何子任务前必须调用；`task_type="conversation"` 会立即切换到对话阶段，`None` 或 `"regular"` 则保持在主循环状态。
- `brainstorm(thinking)`：所有新建子任务后都需要进行一次反思，以明确目标、信息需求与退出条件。
- `send_message_and_wait(content, user_response_options)`：在 `conversation` 阶段下使用，发送角色台词并等待真实用户反馈；需提供 3 条风格不同的用户应答建议以降低对方回复门槛。
- `send_message_and_finish_conversation(content)`：当对话无法继续时收束该阶段，并切换至总结流程。
- `finish_subtask` → `apply_patch_to_note` → `pop_subtask`：总结当前子任务、更新 note、恢复到父任务阶段的标准闭环。

## 配置与运行
1. **准备环境**
   - Python 3.12+
   - 安装依赖：`pip install -e .` 或使用 `uv sync`
2. **设置模型参数**
   - 必填：`MODEL_NAME`
   - 可选：`API_KEY`、`BASE_URL`（如调用私有推理服务）
3. **启动代理**
   ```bash
   python main.py
   ```
   运行后程序会持续进入对话循环，每轮输出智能体新增消息，并把上下文同步到 `logs/conversation.json`。

## CLI 使用指南

### 启动对话循环
```bash
python -m stackandheap.cli run [OPTIONS]
```
- `--state-path PATH`：显式指定上下文文件；若省略，系统会以全新上下文启动，并在结束后保存到 `logs/conversation.json`。
- `--max-turns N`：限制执行轮数，常用于快速验证。
- `--step`：逐回合停顿，按提示输入 `y` 才继续下一轮。
- `--dry-run`：只打印即将发送给模型的对话 JSON，不触发真实推理。

### 查看子任务栈
```bash
python -m stackandheap.cli tasks [--state-path PATH]
```
表格展示当前栈中各子任务的 `task_id`、目标、阶段与消息量，便于掌握分工。未指定 `--state-path` 时读取默认日志文件（若不存在则显示空栈）。

### 管理 note
- 展示 note 当前内容：
  ```bash
  python -m stackandheap.cli note show [--state-path PATH] [--note-path PATH]
  ```
  指定 `--state-path` 可先加载上下文并确保 note 同步；`--note-path` 默认为 `logs/note.md`。
- 导出 note 备份：
  ```bash
  python -m stackandheap.cli note dump OUTPUT_PATH [--note-path PATH]
  ```

### 快速查看日志
```bash
python -m stackandheap.cli logs [--path PATH] [--lines N]
```
对指定的 JSON 日志执行 `tail`，默认展示 `logs/conversation.json` 的最后 50 行，可通过 `--lines` 调整。

> 便捷入口：`python main.py` 也会调用同一 CLI 逻辑，相当于执行 `python -m stackandheap.cli run`。

## 开发与调试提示
- 若需要验证 note 补丁语法，可运行 `python test.py` 查看 `apply_patch` 的示例效果。
- 调试时可将 `StackAndHeapContext.load(...)` 取消注释，以已有日志恢复上下文继续对话，同时直接阅读 `logs/note.md` 快速回顾角色记忆。
- 项目基于 `openai-agents` 的 `Runner`、`Agent` 与工具装饰器，若需扩展行为，可在 `agent_core/tools.py` 中新增工具或调整阶段逻辑。
- 若需要自定义 CLI 行为，可在 `stackandheap/cli` 模块中增添命令或调整输出样式。
