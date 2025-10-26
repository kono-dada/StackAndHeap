from agents import Agent
from .tools import brainstorm, pop_subtask, start_subtask, send_message_and_wait, apply_patch_to_note, finish_subtask, send_message_and_finish_conversation
from .model import model
from .dynamic_instruction import dynamic_instructions

NAME = "main-agent"

agent = Agent(
    name=NAME,
    instructions=dynamic_instructions,
    model=model,
    tools=[
        brainstorm,
        pop_subtask,
        start_subtask,
        send_message_and_wait,
        apply_patch_to_note,
        finish_subtask,
        send_message_and_finish_conversation
    ],
    tool_use_behavior="stop_on_first_tool"
)
