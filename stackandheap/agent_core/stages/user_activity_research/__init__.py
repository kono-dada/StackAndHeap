from ..stage import Stage
from ...tools.built_in import brainstorm, start_subtask, finish_subtask, apply_patch_to_note, pop_subtask, send_message_and_finish_conversation, send_message_and_wait
from ..utils import read_instructions_from_file
from .tools import execute_code_in_repl
import os

user_activity_research = Stage(
    name="user_activity_research",
    description="Research and analyze user activity data for insights.",
    instructions=read_instructions_from_file(
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     'user_activity_research.md')
    ),
    tools=[brainstorm, start_subtask, finish_subtask,
           apply_patch_to_note, execute_code_in_repl],
)
