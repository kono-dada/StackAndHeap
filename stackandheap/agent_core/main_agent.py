from agents import Agent
from .tools.register import prepare_all_tools
from .model import model
from .dynamic_instruction import dynamic_instructions

NAME = "main-agent"

agent = Agent(
    name=NAME,
    instructions=dynamic_instructions,
    model=model,
    tools=prepare_all_tools(),
    tool_use_behavior="stop_on_first_tool"
)
