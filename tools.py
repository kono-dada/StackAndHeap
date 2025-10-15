from agents import function_tool
from conversation import ConversationManager
import asyncio

cm = ConversationManager(main_goal="Your ultimate goal is to befriend the user.")

@function_tool
def brainstorm(thinking: str):
    """ Perform brainstorming and self-reflection to generate new ideas or strategies.
You can think about but are not limited to the following aspects:
    - What possible stack structure do you have in mind?
    - What is your current mental state or emotion state?
    - What are you going to do to manage your heap? What's the structure of it?
    - What information is needed?
    - What theories or methods can be applied to achieve the final goal?
    - What to do next?
    - What interesting things can you do with the tools?
    - Other considerations?

Returns:
    None
    """
    return 

@function_tool
def push_frame(frame_id: str, frame_goal: str, expected_outcome: str):
    """ Push a new frame onto the conversation stack. You will concentrate on the subgoal of this new frame until it is popped.

Args:
    frame_id: Unique identifier for the new frame, usually related to the task
    frame_goal: Description of the frame's goal
    expected_outcome: Description of the expected return value when popping this frame
    """
    cm.push_frame(frame_id, frame_goal, expected_outcome)
    return f'Frame pushed successfully. You are now working on frame: {frame_id} with subgoal: {frame_goal}'

@function_tool
def pop_frame(return_value: str):
    """ Pop the most recent frame from the conversation stack. Once the frame is popped, all conversation in this frame will be removed from the context.

Args:
    return_value: The result or output produced by the frame being popped
    """
    cm.pop_frame(return_value)
    return return_value

@function_tool
async def send_message(content: str):
    """ Send a message to the user. When you want to communicate with the user, you must call this tool. Then wait for the user's response before proceeding.

Args:
    content: The content of the message to send
    """
    user_response = await asyncio.to_thread(input, f"User received message: {content}\nYour reply: ")
    return f'User replied: {user_response}'

@function_tool
def apply_patch_to_heap(patch: str):
    """Apply a text patch to the heap text.

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
@@ ## 用户画像
-current user profile is empty.
+preferred_language: zh
+last_message_summary: 这里是新内容
*** End Patch

Args:
    patch: The patch string to apply, following the specified format
"""
    cm.apply_patch_to_heap(patch)
    return 'Patch applied successfully.'

"""
*** Begin Patch
@@\\n<heap>\\n-\\n+用户名字: '
               'dada\\n</heap>\\n*** End Patch
"""