from typing import Callable, List
from agents import Tool


all_tools: list[Callable] = []


def register_tools(tool: Callable) -> str:
    all_tools.append(tool)
    return tool.__name__


def prepare_all_tools() -> List[Tool]:
    from agents import RunContextWrapper, function_tool, Tool
    from typing import Callable, Any
    from ..context import StackAndHeapContext
    from ..stages import get_stage_by_name
    from ..tools import all_tools
    from ..stages import all_stages

    start_subtask_doc = f"""Start a new subtask. You will concentrate on the subgoal.

    IMPORTANT：If you are in main task now, you MUST start a new subtask. Otherwise, you will fail to call other tools.

    For the third argument `task_type`, if your subtask strongly aligns with a specific stage, you can set it here to switch to that stage directly. Available options are:
    {'\n'.join([f'- "{stage.name}": {stage.description}' for stage in all_stages if stage.visible])}

    Args:
        subtask_id: Unique identifier for the new subtask. 
        subtask_goal: Description of the subtask's goal
        task_type: {" | ".join([f'"{stage.name}"' for stage in all_stages if stage.visible])} | None = None
    """

    def wrapper(tool_name: str) -> Callable[[RunContextWrapper, Any], bool]:
        def is_enable(wrapper: RunContextWrapper[StackAndHeapContext], _: Any) -> bool:
            return tool_name in get_stage_by_name(wrapper.context.current_stage).tools
        return is_enable

    all_function_tools: list[Tool] = []

    for tool in all_tools:
        if tool.__name__ == "start_subtask":
            tool.__doc__ = start_subtask_doc
        all_function_tools.append(
            function_tool(
                func=tool,
                is_enabled=wrapper(tool.__name__),
            )
        )
    return all_function_tools
