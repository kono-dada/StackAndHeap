
from dataclasses import dataclass
from typing import List
from agents import TResponseInputItem
from utils import find_the_first_message_of_type, apply_patch


@dataclass
class Frame:
    frame_id: str
    goal: str
    expected_outcome: str
    messages: List[TResponseInputItem]


DEFAULT_HEAP = \
    """# heap"""


class ConversationManager:
    def __init__(self, main_goal: str):
        self.stack: List[Frame] = [Frame(
            frame_id="main", goal=main_goal, expected_outcome="Continue main conversation", messages=[])]
        self.heap: str = DEFAULT_HEAP

    def push_frame(self, frame_id: str, frame_goal: str, expected_outcome: str):
        self.stack.append(Frame(frame_id=frame_id, goal=frame_goal,
                          expected_outcome=expected_outcome, messages=[]))

    def pop_frame(self, return_value: str):
        """最终状态：弹出最后一个Frame，并把返回值替换掉第一个function_call_output的内容，最后把弹出的frame的第一个function_call和function_call_output都添加到父frame中"""
        if len(self.stack) == 1:
            raise ValueError("No frame to pop.")
        top_frame = self.stack.pop() if self.stack else None
        if not top_frame:
            raise ValueError("No frame to pop.")
        first_function_call_message = find_the_first_message_of_type(
            top_frame.messages, 'function_call')
        self.stack[-1].messages.append(first_function_call_message)
        frame_start_function_call_output = find_the_first_message_of_type(
            top_frame.messages, 'function_call_output')
        frame_start_function_call_output['output'] = \
            f'You have terminated the frame with return_value: {return_value}. You are now working on frame: {self.stack[-1].frame_id}'
        self.stack[-1].messages.append(frame_start_function_call_output)

    def build_conversation(self) -> List[TResponseInputItem]:
        conversation = []
        conversation.append({
            'role': 'user',
            'content': f'<system>以下是你的可编辑文本型heap:\n```heap\n{self.heap}\n```\nLaunched. You are now working on frame: {self.stack[-1].frame_id}</system>'
        })

        for frame in self.stack:
            conversation.extend(frame.messages)
        return conversation

    def add_messages(self, messages: List[TResponseInputItem]):
        if not self.stack:
            raise ValueError(
                "No active frame to add messages to. You can push a 'main' frame first.")
        # 如果有调用pop_frame，则不添加任何消息。返回值会被pop_frame直接添加到父frame中
        if first_function_call := find_the_first_message_of_type(messages, 'function_call'):
            if first_function_call['name'] == 'pop_frame':
                return
        self.stack[-1].messages.extend(messages)

    def apply_patch_to_heap(self, patch: str):
        self.heap = apply_patch(patch, self.heap)
