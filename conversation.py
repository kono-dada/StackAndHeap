
from typing import List, Any, Dict
import json
from agents import TResponseInputItem
from utils import find_the_first_message_of_type, apply_patch

# pydantic v2
from pydantic import BaseModel, Field


class Frame(BaseModel):
    frame_id: str
    goal: str
    expected_outcome: str
    messages: List[TResponseInputItem] = Field(default_factory=list)


DEFAULT_HEAP = \
    """# heap

## 角色细节设定

> 这块区域用于存储角色的细节设定，包括但不限于姓名、性别、外貌、性格、兴趣爱好、背景故事等信息。这些信息可以帮助你更好地扮演角色，并与用户进行互动。

(empty for now)

## 角色当前心流

> 这块区域用于存储角色的当前心流状态，包括但不限于情绪、动机、目标等信息。这些信息可以帮助你更好地理解角色的行为和反应。

(empty for now)

## User Profile

> this section is for storing user profile information, including factual information and your conjectures.

(empty for now)

## Plan

> this section is for storing your current plan, including subgoals, next steps, and any relevant context.

(empty for now)

## Detailed recent interactions

> this section is for storing **exact quotes** or references from previous conversations or external sources that you might need to refer to later. 
> For example, if you said something that resulted in a good user reaction, you might want to save that here for future reference.
> Vice versa, if you said something that resulted in a bad user reaction, you might want to save that here as well.

(empty for now)

(## other sections as needed, feel free to delete this line and create new sections as needed)

"""


class ConversationManager(BaseModel):
    stack: List[Frame]
    heap: str

    def __init__(self, stack: List[Frame] | None = None, heap: str | None = None):
        super().__init__(
            stack=stack or [Frame(frame_id="main", goal="main",
                                  expected_outcome="main")],
            heap=heap or DEFAULT_HEAP,
        )

    # --- Persistence API -------------------------------------------------
    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, path: str) -> 'ConversationManager':
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.model_validate(data)

    def push_frame(self, frame_id: str, frame_goal: str, expected_outcome: str):
        self.stack.append(Frame(frame_id=frame_id, goal=frame_goal,
                          expected_outcome=expected_outcome, messages=[]))

    def pop_frame(self, patch: str, return_value: str):
        """弹出最后一个Frame"""
        self.heap = apply_patch(patch, self.heap)
        if len(self.stack) == 1:
            raise ValueError("No frame to pop.")
        top_frame = self.stack.pop() if self.stack else None
        if not top_frame:
            raise ValueError("No frame to pop.")
        if top_frame.messages[0]['type'] == 'reasoning':   # type: ignore
            self.stack[-1].messages.append(top_frame.messages[0])
        first_function_call_message = find_the_first_message_of_type(
            top_frame.messages, 'function_call')
        if not first_function_call_message:
            raise ValueError(
                "No function call message found in the popped frame.")
        self.stack[-1].messages.append(first_function_call_message)
        frame_start_function_call_output = find_the_first_message_of_type(
            top_frame.messages, 'function_call_output')
        if not frame_start_function_call_output:
            raise ValueError(
                "No function call output message found in the popped frame.")
        output = f'[{len(top_frame.messages)} messages removed] You have terminated the frame with summary "{return_value}". You are now working on frame: {self.stack[-1].frame_id}. If that is "main", you MUST push a new frame immediately.'
        frame_start_function_call_output['output'] = output  # type: ignore
        self.stack[-1].messages.append(frame_start_function_call_output)

    def build_conversation(self) -> List[TResponseInputItem]:
        conversation: List[TResponseInputItem] = []
        conversation.append({
            'role': 'developer',
            'content': f'<system>以下是你的可编辑文本型heap:\n```heap\n{self.heap}\n```\nLaunched. You are now working on frame: {self.stack[-1].frame_id}</system>'
        })

        for frame in self.stack:
            conversation.extend(frame.messages)
        return conversation

    def add_messages(self, messages: List[TResponseInputItem]):
        if not self.stack:
            raise ValueError(
                "No active frame to add messages to. You can push a 'main' frame first.")
        # 如果有成功地调用pop_frame，则不添加任何消息。返回值会被pop_frame直接添加到父frame中
        if first_function_call := find_the_first_message_of_type(messages, 'function_call'):
            if first_function_call['name'] == 'pop_frame':  # type: ignore
                first_output = find_the_first_message_of_type(
                    messages, 'function_call_output')
                if 'error' not in first_output['output']:  # type: ignore
                    return
        self.stack[-1].messages.extend(messages)
