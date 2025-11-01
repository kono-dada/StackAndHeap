from agents import Agent, RunContextWrapper
from .context import StackAndHeapContext
import os
import dotenv
import frontmatter
from .general import GENERAL_INSTRUCTIONS


def dynamic_instructions(context: RunContextWrapper[StackAndHeapContext], agent: Agent[StackAndHeapContext]) -> str:
    cm = context.context
    match cm.current_stage:
        case "summarizing":
            return subtask_summarizer_instructions(cm)
        case _:
            return main_agent_instructions(cm)


def main_agent_instructions(cm: StackAndHeapContext) -> str:
    return GENERAL_INSTRUCTIONS


def subtask_summarizer_instructions(cm: StackAndHeapContext) -> str:
    return f"""<role>
你是subtask-summarizer，负责在每个子任务（subtask）完成后，充分地总结子任务的达成情况，并将有用的信息填写进note中。
</role>

<goal>
你所处的当前子任务的id是：{cm.stack[-1].task_id}。你只需要关注：
1. 当前子任务范围的内容
2. note中的内容
最终按照working_principles的要求把当前subtask的信息整合进note中，确保note内容完整且有条理。
</goal>

<working_principles>
使用apply_patch_to_note工具将总结内容以patch的形式应用到note中。
<working_principle>
"""