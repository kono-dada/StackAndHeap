from agents import Agent
from .tools import brainstorm, pop_subtask, start_subtask, send_message, apply_patch_to_note, finish_subtask, enter_sending_stage
from .model import model
from .dynamic_instruction import dynamic_instructions

NAME = "main-agent"

agent = Agent(
    name=NAME,
    instructions=dynamic_instructions,
    model=model,
    tools=[brainstorm, pop_subtask, start_subtask,
           send_message, apply_patch_to_note, finish_subtask, enter_sending_stage],
    tool_use_behavior="stop_on_first_tool"
)
