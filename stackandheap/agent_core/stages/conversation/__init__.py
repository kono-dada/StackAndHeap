from ..stage import Stage
from ...tools.built_in import brainstorm, send_message_and_finish_conversation, send_message_and_wait
from ..utils import read_instructions_from_file
import os


conversation = Stage(
    name="conversation",
    description="Focus on conversational tasks.",
    instructions=read_instructions_from_file(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'conversation.md')
    ),
    tools=[
        send_message_and_finish_conversation,
        send_message_and_wait,
        brainstorm
    ],
)
