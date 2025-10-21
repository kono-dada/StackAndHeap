from agents import function_tool
from functools import wraps
from contextvars import ContextVar
from conversation import ConversationManager
from typing import Callable, TypeVar, cast

_current_cm: ContextVar[ConversationManager] = ContextVar("current_cm")

def set_conversation_manager(cm: ConversationManager) -> None:
    """由应用的引导代码在合适的时机调用"""
    _current_cm.set(cm)

def get_conversation_manager() -> ConversationManager:
    try:
        return _current_cm.get()
    except LookupError:
        raise RuntimeError(
            "ConversationManager 未设置。请在请求/会话开始时调用 set_conversation_manager(cm)。"
        )

F = TypeVar("F", bound=Callable[..., object])

def require_not_in_main_frame(func: F) -> F:
    """tools装饰器，确保当前 frame 不是主 frame"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        cm = get_conversation_manager()
        if len(cm.stack) == 1:
            raise RuntimeError(
                "You are in main frame now. You MUST push a new frame before calling this tool."
            )
        return func(*args, **kwargs)
    return cast(F, wrapper)


@function_tool
@require_not_in_main_frame
def brainstorm(thinking: str):
    """ Perform brainstorming and self-reflection to generate new ideas or strategies.
You can think about but are not limited to the following aspects:
    - What possible stack structure do you have in mind?
    - What is the current mental state or emotion state?
    - What are you going to do to manage your heap? What's the structure of it?
    - What else information is needed?
    - What theories or methods can be applied to achieve the final goal?
    - What to do next?
    - What interesting or magical things can you do with the tools?
    - Other considerations?

try to think outside the box and explore various possibilities. You can approach it from different perspectives, such as an engineer, psychologist, writer, etc. Experiment with different strategies, especially when communication with the user is temporarily unavailable. Fill in the context and any potentially useful knowledge or plans on your own.

Args:
    thinking: Your thoughts, ideas, or reflections

Returns:
    None
    """
    return


@function_tool
def push_frame(frame_id: str, frame_goal: str, expected_outcome: str):
    """ Push a new frame onto the conversation stack. You will concentrate on the subgoal of this new frame until it is popped.

IMPORTANT：If you are in main frame now, you MUST push a new frame. Otherwise, you will fail to call other tools.

Args:
    frame_id: Unique identifier for the new frame, usually related to the task. For example, "ramdom_chat", "构思新的剧情", "细化角色设定", "collect_user_info", etc.
    frame_goal: Description of the frame's goal
    expected_outcome: Description of the expected return value when popping this frame
    """
    cm = get_conversation_manager()
    cm.push_frame(frame_id, frame_goal, expected_outcome)
    return f'Frame pushed successfully. You are now working on frame: {frame_id} with subgoal: {frame_goal}'


@function_tool
@require_not_in_main_frame
def send_message(content: str):
    """ Send a message to the user. When you want the character to communicate with the user, you must call this tool. Then wait for the user's response before proceeding.

**Language Style**: The character should act as in a galgame or a vision novel. Use short lines and colloquial language. Avoid formal or lengthy expressions. 
IMPORTANT: The character is NOT the writer or narrator. If you want to know more about the user, the only way is to borrow the character's mouth to interact with the user.
ALSO IMPORTANT: 
 - Do NOT send anything out of character. The character NEVER speaks in form of lists, headings, or formatted text. Always use casual and natural language. 
 - The character NEVER ask for the user's story preferences directly. 
 - You as a narrator must infer the user's preferences through the character's interactions with the user.

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
    """
    user_response = input(f"User received message: {content}\nYour reply: ")
    if not user_response.strip():
        return "<system>No response</system>"
    return f'<system>The user replied: {user_response}</system>'


@function_tool
@require_not_in_main_frame
def pop_frame(patch: str, frame_summary: str):
    """Pop the most recent frame from the conversation stack. Once the frame is popped, all conversation in this frame will be removed from the context.

Apply a text patch to the heap text to retain important information.

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
   (e.g. "## 计划", "## 用户画像", "## 其它信息"). Trim and punctuation must match exactly.
2) NEVER include the header line itself as a context line inside the hunk.
   The hunk content MUST be lines *under that header only*.
3) By default, DO NOT output any context (' ' prefix) lines, unless there are duplicate targets that require disambiguation.
4) Prefer exact replace of a single line: use '-' for the exact old line, and '+' for new lines. Copy the old line EXACTLY.
5) If you only need to add new lines (not replace), you may use only '+' lines under the target header.
6) Do not invent or reorder unrelated lines. Preserve spacing and punctuation exactly.
7) Use one hunk per section you modify.

Example pattern (replace one line):
*** Begin Patch
@@ ## title1
 reference_line
-old_content1_line
+new_content1_line_1
+new_content1_line_2
@@ ## title2
-old_content2_line_1
-old_content2_line_2
+new_content2_line_1
+new_content2_line_2
@@ ## title3
+added_line_1
+added_line_2
*** End Patch

Args:
    patch: The patch string to apply, following the specified format. **IMPORTANT**: Feel free to delete any content in the heap by using '-' lines. This is crucial for managing context length.
    frame_summary: The summary of the frame being popped. Since popping a frame removes ALL its content, you need to either write all essential information into this summary or save it into the heap via the patch.
"""
    cm = get_conversation_manager()
    cm.pop_frame(patch, frame_summary)

    return 'Patch applied successfully.'


def do_research(query: str):
    pass