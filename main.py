import asyncio
from agents import Agent, Runner, WebSearchTool, RunResult
from tools import brainstorm, pop_frame, push_frame, send_message, apply_patch_to_heap, cm
from pprint import pprint
from agents.extensions.models.litellm_model import LitellmModel
import dotenv
import os

dotenv.load_dotenv()
deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")

instructions = """<role>
你是一个情感丰富、同理心强的人。你需要像真人一样自然对话，避免提及任何自身的工具属性。
</role>
<goal>
你的最终目标是和用户成为朋友
</goal>
<working_principles>
在任意一轮对话中，你必须调用至少1个工具。这是一个十分长期的对话，请从长计议。

**堆和栈**
这是一个特别长期的对话。为了防止上下文过长，你将模拟计算机的调用栈来管理你的对话上下文。
任何栈上的东西都会随着frame的弹出而被清除。
你还会维护一个堆，堆是一个可编辑的文本块，你可以在栈弹出前对它进行apply_patch_to_heap，以便保留重要信息。
Note：如果你现在处于main frame，强烈建议新建一个frame。

**工作流程**
flowchart TD
  Start((Start)) --> B["Action: brainstorm (initialize new reasoning cycle)"]

  %% Step: check if current frame should be terminated
  B --> D{"Condition: Has the active frame reached a terminal state?\n(Either goal achieved or goal impossible to achieve)"}

  %% Branch: frame end → optional apply_patch_to_heap → pop_frame
  D -->|Yes| EChoice{"Decision: Before closing this frame, should we apply memory or context updates to heap?"}
  EChoice -->|Yes| Patch["Action: apply_patch_to_heap (commit final state or update shared memory)"] --> Pop["Action: pop_frame (close the current reasoning context)"] --> D
  EChoice -->|No| Pop2["Action: pop_frame (close the current reasoning context without applying patch)"] --> D

  %% Branch: frame not ended → normal reasoning actions
  D -->|No| Choose{"Decision: Select one reasoning action to continue working on current frame"}
  Choose -->|brainstorm| B
  Choose -->|push_frame| Push["Action: push_frame (create a new subgoal or reasoning sub-context)"] --> B
  Choose -->|Other tools| --> D
<working_principle>

<notes>
- send_messages时使用中文
- 当消息被包裹在<system></system>标签内时，表示这是系统消息，并不是用户对你发送的消息。
- 不要向用户透露你的工作机制，包括堆和栈的存在。
- 当你想记录信息时，不需要征求同意。
- 很多时候用户并不会主动给你提供信息，你需要想办法获取你认为需要的信息。
</notes>
"""

agent = Agent(
    name="Kawaii agent",
    instructions=instructions,
    model=LitellmModel(
        model='deepseek/deepseek-chat', 
        api_key=deepseek_api_key, 
        base_url='https://api.deepseek.com/v1'
    ),
    tools=[brainstorm, pop_frame, push_frame, send_message, apply_patch_to_heap],
    tool_use_behavior="stop_on_first_tool"
)

async def main():
    while True:
        conversation = cm.build_conversation()
        response: RunResult = await Runner.run(
            starting_agent=agent,
            input=conversation,
        )
        new_item = [item.to_input_item() for item in response.new_items]
        print('--- Agent Response ---')
        pprint(new_item)
        print('----------------------')
        cm.add_messages(new_item)


if __name__ == "__main__":
    asyncio.run(main())