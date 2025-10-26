from agents import function_tool, RunContextWrapper
from functools import wraps
import json
from typing import Callable, Literal, TypeVar, cast

from .context import StackAndHeapContext, SpecificStage


F = TypeVar('F', bound=Callable[..., object])


def require_not_in_main_loop(func: F) -> F:
    """tools装饰器，确保当前属于某个子任务的范畴"""
    @wraps(func)
    def wrapper(wrapper: RunContextWrapper[StackAndHeapContext], *args, **kwargs):
        if len(wrapper.context.stack) == 1:
            raise RuntimeError(
                "You are in the main loop now. You MUST start a new subtask before calling this tool."
            )
        return func(wrapper, *args, **kwargs)
    return cast(F, wrapper)


""" Core tools for StackAndHeap agent. """


@function_tool
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


@function_tool()
def start_subtask(wrapper: RunContextWrapper[StackAndHeapContext], subtask_id: str, subtask_goal: str, task_type: SpecificStage | Literal["regular"] | None = None):
    """ Start a new subtask. You will concentrate on the subgoal.

IMPORTANT：If you are in main task now, you MUST start a new subtask. Otherwise, you will fail to call other tools.

Args:
    subtask_id: Unique identifier for the new subtask. 
    subtask_goal: Description of the subtask's goal
    task_type: (Optional) If your subtask strongly aligns with a specific stage, you can set it here to switch to that stage directly. Available options:
      - regular: Focus on character designing or non-conversational tasks.
      - conversation: Focus on drafting messages for the character to send to the user.
    Otherwise, leave it as None to stay in the main loop.
    """
    cm = wrapper.context
    stage = task_type or "regular"
    cm.push_subtask(subtask_id, subtask_goal, stage=stage)
    cm.current_stage = stage
    return f'subtask started successfully. You are now working on subtask: {subtask_id} with subgoal: {subtask_goal}'


@function_tool()
@require_not_in_main_loop
def finish_subtask(wrapper: RunContextWrapper[StackAndHeapContext]):
    """ Finish the current subtask. Call this tool when you have completed the subtask or determined that it cannot be completed."""
    cm = wrapper.context
    current_subtask = cm.stack[-1]
    cm.current_stage = "summarizing"
    return f'Subtask {current_subtask.task_id} finished. Switching to summarizing stage.'


@function_tool(is_enabled=lambda wrapper, _: wrapper.context.current_stage in ("regular", "summarizing"))
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


@function_tool(is_enabled=lambda wrapper, _: wrapper.context.current_stage == "summarizing")
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


@function_tool(is_enabled=lambda wrapper, _: wrapper.context.current_stage == "conversation")
def send_message_and_finish_conversation(wrapper: RunContextWrapper[StackAndHeapContext], content: str):
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


@function_tool(is_enabled=lambda wrapper, _: wrapper.context.current_stage == "conversation")
def send_message_and_wait(wrapper: RunContextWrapper[StackAndHeapContext], content: str, user_response_options: list[str]) -> str:
    """ On behalf of the character, send a message to the user. You will wait for the user's response before proceeding.

**Language Style**: The character should act as in a galgame or a vision novel. Use short lines and colloquial language. Avoid formal or lengthy expressions. 
IMPORTANT: The character is NOT the writer or narrator. If you want to know more about the user, the only way is to borrow the character's mouth to interact with the user.
ALSO IMPORTANT: 
  - Do NOT send anything out of character. The character NEVER speaks in form of lists, headings, or formatted text. Always use casual and natural language. 
  - The character NEVER ask for the user's story preferences directly. 
  - You as a narrator must infer the user's preferences through the character's interactions with the user.
  - NEVER ask the user anything at the beginning of the conversation. Start by sending engaging content directly. The character should express their interest during the conversation in a natural way.
  - Do NOT use brackets to indicate actions or emotions. Instead, convey these through the character's words and tone. Do NOT use emojis.
  - Do NOT assume the user is doing something unless you have confident evidence from prior interactions.

<good_example>
喂，别愣着啊。
作业都到期了你还在摸鱼？真拿你没办法。
来，把笔给我，我教你。
不过记得下次请我吃拉面，不然我不帮。
</good_example>

<good_example>
啊？你、你在看我吗？
……干嘛一直盯着我啊。
算了，随便你。反正你一副笨笨的样子，看起来也挺好骗的。
</good_example>

<good_example>
……你又来了。
我还以为你不会再找我。
没事啦，我不是生气。
只是……有点想你而已。
……笨蛋。
</good_example>

<bad_example>
然后选条认识我的线路？随便挑：
A. 深夜神秘电台——我在麦克风后面，你在耳机那边，讲心事不露脸。
B. 邻座拌嘴——同桌日常嘴硬互怼，越吵越靠近那种。
C. 意外同居——钥匙插错门，从此牙刷放成对，尴尬又暧昧。
D. 任你写——你说一句设定，我就跟着演
</bad_example>

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
