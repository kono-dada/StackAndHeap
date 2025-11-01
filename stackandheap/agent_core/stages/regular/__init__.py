from ..stage import Stage
from ...tools.built_in import brainstorm, start_subtask, finish_subtask, apply_patch_to_note


regular = Stage(
    name="regular",
    description="Focus on character designing or non-conversational tasks.",
    instructions="",
    tools=[brainstorm, start_subtask, finish_subtask, apply_patch_to_note],
)