from ..stage import Stage
from ...tools.built_in import brainstorm, apply_patch_to_note, pop_subtask


summarizing = Stage(
    name="summarizing",
    description="Summarize the completed subtasks and prepare for the next steps.",
    instructions="",
    tools=[pop_subtask, apply_patch_to_note, brainstorm],
    visible=False
)
