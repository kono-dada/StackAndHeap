
from typing import List, Literal
import json
from agents import TResponseInputItem
from .utils import find_the_first_message_of_type, apply_patch
from pydantic import BaseModel, Field
import os

SpecificStage = Literal["conversation"]
Stage = SpecificStage | Literal["summarizing", "main_loop"]

note_template_path = os.getenv(
    "SAH_NOTE_TEMPLATE_PATH", "examples/note_template.md")
with open(note_template_path, "r", encoding="utf-8") as f:
    NOTE_TEMPLATE = f.read()


class Subtask(BaseModel):
    task_id: str = "main"
    goal: str = "main"
    messages: List[TResponseInputItem] = Field(default_factory=list)
    stage: Stage = "main_loop"


class StackAndHeapContext(BaseModel):
    stack: List[Subtask] = [Subtask()]
    note: str = NOTE_TEMPLATE
    current_stage: Stage = "main_loop"
    chat_history: List[TResponseInputItem] = Field(default_factory=list)

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))
        with open(os.path.dirname(path) + '/note.md', "w", encoding="utf-8") as f:
            f.write(self.note)

    @classmethod
    def load(cls, path: str) -> 'StackAndHeapContext':
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.model_validate(data)

    def push_subtask(self, subtask_id: str, subtask_goal: str, stage: Stage):
        self.stack.append(Subtask(task_id=subtask_id,
                          goal=subtask_goal, messages=[], stage=stage))

    def pop_subtask(self, return_value: str):
        """弹出最后一个subtask"""
        assert len(self.stack) > 1, "No subtask to pop."
        top_subtask = self.stack.pop() if self.stack else None
        assert top_subtask, "No subtask to pop."
        if top_subtask.messages[0]['type'] == 'reasoning':   # type: ignore
            self.stack[-1].messages.append(top_subtask.messages[0])
        first_function_call_message = find_the_first_message_of_type(
            top_subtask.messages, 'function_call')
        assert first_function_call_message, "No function call message found in the popped subtask."
        self.stack[-1].messages.append(first_function_call_message)
        subtask_start_function_call_output = find_the_first_message_of_type(
            top_subtask.messages, 'function_call_output')
        assert subtask_start_function_call_output, "No function call output message found in the popped subtask."
        output = f'[{len(top_subtask.messages)} messages removed] You have terminated the subtask with summary "{return_value}". You are now working on subtask: {self.stack[-1].task_id}.'
        subtask_start_function_call_output['output'] = output  # type: ignore
        self.stack[-1].messages.append(subtask_start_function_call_output)

    def build_conversation(self) -> List[TResponseInputItem]:
        conversation: List[TResponseInputItem] = []
        conversation.append({
            'role': 'user',
            'content': f'<system>以下是你的可编辑文本型note:\n```note\n{self.note}\n```\nLaunched. You are now working on task: {self.stack[-1].task_id}</system>'
        })

        for subtask in self.stack:
            conversation.extend(subtask.messages)
        return conversation

    def add_messages(self, messages: List[TResponseInputItem]):
        self.chat_history.extend(messages)
        # 如果有成功地调用pop_subtask，则不添加任何消息。返回值会被pop_subtask直接添加到父subtask中
        if first_function_call := find_the_first_message_of_type(messages, 'function_call'):
            if first_function_call['name'] == 'pop_subtask':  # type: ignore
                first_output = find_the_first_message_of_type(
                    messages, 'function_call_output')
                if 'error' not in first_output['output']:  # type: ignore
                    return
        self.stack[-1].messages.extend(messages)

    def apply_patch_to_note(self, patch: str):
        self.note = apply_patch(patch, self.note)
