# StackAndHeap

## 项目简介
StackAndHeap 是一个围绕 `openai-agents` 运行时构建的示例型智能体项目，通过「栈（Stack）」与「堆（Heap）」的比喻来管理对话状态与长期记忆。项目模拟一位视觉小说编剧型角色与用户互动，强调子任务拆分、过程反思与记忆沉淀。

## 核心设计理念
- **Stack：子任务调用栈** —— `StackAndHeapContext` 维护一个由 `Subtask` 组成的栈，每个子任务持有自己的消息列表。栈顶子任务代表当前聚焦的子目标，结束后通过 `finish_subtask → pop_subtask` 收束上下文。
- **Heap：可编辑长期记忆** —— `context.note` 以 Markdown 结构保存角色设定、用户画像、计划等信息。借助 `apply_patch_to_note` 工具，记忆以差异补丁方式迭代更新。
- **阶段化指令** —— `dynamic_instruction` 根据 `current_stage` 切换为主流程（main_loop）、总结（summarizing）、预发送（pre-sending）三类指令，驱动智能体在不同阶段执行对应职责。

## 运行流程概览
1. `main.py` 初始化 `StackAndHeapContext`，循环调用 `Runner.run` 执行代理逻辑，并写回最新对话到 `logs/conversation.json`。
2. `Agent` 入口由 `agent/main_agent.py` 定义，结合 `dynamic_instruction` 动态生成提示词，并绑定一组工具函数。
3. 智能体在主循环阶段必须先 `start_subtask → brainstorm`，随后视情况调用其他工具；当子任务完成，转入 `summarizing` 阶段整理记忆；若需对外发言，则进入 `pre-sending` 阶段，通过 `send_message` 与真实用户交互。
4. 所有新消息通过 `StackAndHeapContext.add_messages` 统一写入当前子任务栈，必要时持久化，以便后续轮次延续上下文。

### 流程示意
```
main_loop ──start_subtask──▶ brainstorm ──▶ (工具调用 / 继续拆分)
      │                                      │
      └──子任务完成──▶ finish_subtask ──▶ summarizing ──apply_patch_to_note──▶ pop_subtask
                                                              │
                                                              └──> 返回 main_loop

main_loop ──enter_sending_stage──▶ pre-sending ──send_message──▶ main_loop
```

## 目录结构
```
stackAndHeap/
├── main.py                # 事件循环入口
├── agent/
│   ├── context.py         # 上下文模型与栈/堆维护逻辑
│   ├── dynamic_instruction.py # 阶段化提示词
│   ├── main_agent.py      # Agent 定义与工具注册
│   ├── model.py           # 基于 LiteLLM 的模型适配
│   ├── tools.py           # 工具函数及阶段约束
│   └── utils.py           # 通用工具（消息检索、补丁应用）
├── logs/                  # 对话持久化输出目录
├── test.py                # `apply_patch` 行为示例
├── pyproject.toml         # 项目配置与依赖
└── uv.lock                # 依赖锁定文件
```

## 关键模块说明
- `StackAndHeapContext`（`agent/context.py`）：基于 Pydantic 定义上下文，提供 `build_conversation`、`push_subtask`、`pop_subtask`、`apply_patch_to_note` 等方法，实现对话栈与笔记的管理。
- `dynamic_instruction.py`：根据 `current_stage` 选择不同角色设定与操作规程，确保智能体在主流程、总结和发送前各司其职。
- `tools.py`：封装 `brainstorm`、`start_subtask`、`enter_sending_stage`、`send_message`、`finish_subtask`、`apply_patch_to_note`、`pop_subtask` 等工具，利用装饰器约束调用时机，保证流程规范。
- `model.py`：加载环境变量 `MODEL_NAME`、`API_KEY`、`BASE_URL`，通过 `LitellmModel` 适配到统一推理接口。
- `main.py`：负责调度 `Runner.run`、打印代理输出并保存上下文，是脚本启动入口。
- `utils.py`：提供 `find_the_first_message_of_type` 以及自定义 diff 解析器 `apply_patch`，支撑 note 更新机制。

## 工具与阶段约束
- `start_subtask` / `brainstorm`：主循环下的基本操作，所有子任务从头脑风暴开始。
- `finish_subtask` → `pop_subtask`：关闭当前子任务并将精炼信息传回父任务。
- `enter_sending_stage` → `send_message`：当需要以角色身份与真实用户互动时切换到发送阶段，结束后回到主循环。
- `apply_patch_to_note`：在总结阶段使用，按补丁语法安全更新 note。

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

## 开发与调试提示
- 若需要验证 note 补丁语法，可运行 `python test.py` 查看 `apply_patch` 的示例效果。
- 调试时可将 `StackAndHeapContext.load(...)` 取消注释，以已有日志恢复上下文继续对话。
- 依赖基于 `openai-agents` 提供的 `Runner`、`Agent` 与工具装饰器，若需扩展行为，可查阅官方文档或在 `tools.py` 中新增自定义工具。
