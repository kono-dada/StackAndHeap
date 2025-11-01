from agents import RunContextWrapper
from functools import wraps
import json
from typing import Callable, Literal, TypeVar, cast
from ..context import StackAndHeapContext
from .decorators import require_not_in_main_loop
from .register import register_tools

""" Core tools for StackAndHeap agent. """


@register_tools
def brainstorm(wrapper: RunContextWrapper[StackAndHeapContext], thinking: str):
    """ Perform brainstorming and self-reflection to generate new ideas or strategies.
    You can think about but are not limited to the following aspects:
        - What possible stack structure do you have in mind?
        - What is the character's current mental state or emotion state?
        - What else information is needed?
        - What theories or methods can be applied?
        - What to do next?
        - What interesting or magical things can you do with the tools?
        - Other considerations?

    Args:
        thinking: Your thoughts, ideas, or reflections
    """
    return


@register_tools
def start_subtask(wrapper: RunContextWrapper[StackAndHeapContext], subtask_id: str, subtask_goal: str, task_type: str | None = None) -> str:
    from ..stages import get_stage_by_name
    stage = task_type or "regular"
    additional_instructions = get_stage_by_name(stage).instructions
    cm = wrapper.context
    cm.push_subtask(subtask_id, subtask_goal, stage=stage)
    cm.current_stage = stage
    output = f'subtask started successfully. You are now working on subtask: {subtask_id} with subgoal: {subtask_goal}'
    if additional_instructions:
        output += f' \n Additional instructions for this stage:\n{additional_instructions}'
    return output


@register_tools
@require_not_in_main_loop
def finish_subtask(wrapper: RunContextWrapper[StackAndHeapContext]):
    """ Finish the current subtask. Call this tool when you have completed the subtask or determined that it cannot be completed."""
    cm = wrapper.context
    current_subtask = cm.stack[-1]
    cm.current_stage = "summarizing"
    return f'Subtask {current_subtask.task_id} finished. Switching to summarizing stage.'


@register_tools
@require_not_in_main_loop
def apply_patch_to_note(wrapper: RunContextWrapper[StackAndHeapContext], patch: str):
    """Apply a text patch to the note to retain important information.

    Your patch language is a minimal, file-oriented diff:

    *** Begin Patch
    [ one or more hunks ]
    *** End Patch

    Grammar:
    Patch := Begin { FileOp } End
    Begin := "*** Begin Patch" NEWLINE
    End   := "*** End Patch" NEWLINE
    FileOp := "@@" [ header ] NEWLINE { HunkLine } [ "*** End of File" NEWLINE ]
    HunkLine := (" " | "-" | "+") text NEWLINE

    VERY IMPORTANT RULES (must follow exactly):
    1) ALWAYS provide a non-empty header after "@@", and the header MUST be exactly the section title line in the document
    (e.g. "## 计划", "### 用户画像", "#### 其它信息"). Trim and punctuation must match exactly. Dot not forget the leading hashes.
    2) NEVER include the header line itself as a context line inside the hunk.
    The hunk content MUST be lines *under that header only*.
    3) By default, DO NOT output any context (' ' prefix) lines, unless there are duplicate targets that require disambiguation.
    4) Prefer exact replace of a single line: use '-' for the exact old line, and '+' for new lines. Copy the old line EXACTLY.
    5) If you only need to add new lines (not replace), you may use only '+' lines under the target header.
    6) Do not invent or reorder unrelated lines. Preserve spacing and punctuation exactly.
    7) Use one hunk per section you modify.
    8) Feel free to delete any unnecessary context lines in order to improve clarity.

    Example pattern:
    *** Begin Patch
    @@ ## section1
    reference_line
    -old_content1_line_1
    -old_content1_line_2
    +new_content1_line_1
    +new_content1_line_2
    @@ ### section2
    -old_content2_line_1
    -old_content2_line_2
    +new_content2_line_1
    +new_content2_line_2
    @@ #### section3
    +added_line_1
    +added_line_2
    *** End Patch

    Args:
        patch: The patch string to apply, following the specified format. 
    """
    cm = wrapper.context
    cm.apply_patch_to_note(patch)

    return f'Patch applied successfully.\nThe note is now updated.'


@register_tools
@require_not_in_main_loop
def pop_subtask(wrapper: RunContextWrapper[StackAndHeapContext], return_value: str):
    """ Pop the most recent subtask from the conversation stack. Once the subtask is popped, all conversation in this subtask will be removed from the context.

    Args:
        return_value: one-sentence summary of the subtask completion status. List all events that happened in this subtask, no matter how relevant to the subtask goal.
    """
    cm = wrapper.context
    cm.pop_subtask(return_value)
    cm.current_stage = cm.stack[-1].stage
    return return_value


""" Tools for conversations. """


@register_tools
def send_message_and_finish_conversation(wrapper: RunContextWrapper[StackAndHeapContext], content: str) -> str:
    """ Finish a conversation. Call this tool when the conversation cannot continue. For example:
    - You want to end the conversation.
    - The user is unresponsive or has left.
    - The user asks you to do something complex that cannot be handled in a single conversation.

    Before finishing, let the character send a final message to the user.

    Args:
        content: The content of the message to send
    """
    cm = wrapper.context
    cm.current_stage = "summarizing"
    event = {
        "type": "display_message",
        "content": content,
        "final": True,
    }
    return json.dumps(event, ensure_ascii=False)


@register_tools
def send_message_and_wait(wrapper: RunContextWrapper[StackAndHeapContext], content: str, user_response_options: list[str]) -> str:
    """ On behalf of the character, send a message to the user. You will wait for the user's response before proceeding.

    Args:
        content: The content of the message to send
        user_response_options: You can suggest 3 options for the user to respond shortly, including teasing, flirtatious, and neutral replies. 
    """
    event = {
        "type": "await_user",
        "content": content,
        "options": user_response_options,
    }
    return json.dumps(event, ensure_ascii=False)
