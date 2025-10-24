
from typing import List, Literal
import json
from agents import TResponseInputItem
from .utils import find_the_first_message_of_type, apply_patch
from pydantic import BaseModel, Field
import os


class Subtask(BaseModel):
    task_id: str = "main"
    goal: str = "main"
    messages: List[TResponseInputItem] = Field(default_factory=list)


DEFAULT_note = \
    """# note
## 角色细节设定
> 这块区域用于存储角色的细节设定，包括但不限于姓名、性别、外貌、性格、兴趣爱好、背景故事等信息。这些信息可以帮助你更好地扮演角色，并与用户进行互动。
empty for now

## 角色当前心流
> 这块区域用于存储角色的当前心流状态，包括但不限于情绪、动机、目标等信息。这些信息可以帮助你更好地理解角色的行为和反应。
empty for now

## 用户画像
> 这块区域用于存储用户的画像信息，包括但不限于用户的兴趣、偏好、背景故事等。这些信息可以帮助你更好地理解用户，并与其进行互动。
empty for now

## 计划
> 这块区域用于存储你当前的计划，包括子目标、下一步和任何相关的上下文信息。
empty for now

## 近期详细互动
> 这块区域用于存储**确切的引用**或来自先前对话或外部来源的参考，以便你在稍后需要时可以引用。
empty for now

## 角色故事
> 为角色编写故事。使用童话般的语言风格，注重细节和角色心理描写。创作故事是为了丰富角色的背景，使其更具深度和吸引力，并在与用户交谈中提供谈资。
empty for now

"""


class StackAndHeapContext(BaseModel):
    stack: List[Subtask] = [Subtask()]
    note: str = DEFAULT_note
    current_stage: Literal["main_loop", "summarizing", "pre-sending"] = "main_loop"
    chat_history: List[TResponseInputItem] = Field(default_factory=list)

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, path: str) -> 'StackAndHeapContext':
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.model_validate(data)

    def push_subtask(self, subtask_id: str, subtask_goal: str):
        self.stack.append(Subtask(task_id=subtask_id,
                          goal=subtask_goal, messages=[]))

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
