
from dataclasses import dataclass
from typing import List, Tuple
from agents import TResponseInputItem
import re


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
        if len(self.stack) == 1:
            raise ValueError("No frame to pop.")
        top_frame = self.stack.pop() if self.stack else None
        if not top_frame:
            raise ValueError("No frame to pop.")
        first_function_call_message = find_the_first_message_of_type(top_frame.messages, 'function_call')
        self.stack[-1].messages.append(first_function_call_message)
        frame_start_function_call_output = find_the_first_message_of_type(top_frame.messages, 'function_call_output')
        frame_start_function_call_output['output'] = \
            f'The frame has been over with return_value: {return_value}. You are now working on frame: {self.stack[-1].frame_id}'
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
        # 如果有调用pop_frame，则不添加任何消息
        if first_function_call := find_the_first_message_of_type(messages, 'function_call'):
            if first_function_call['name'] == 'pop_frame':
                return
        self.stack[-1].messages.extend(messages)

    def apply_patch_to_heap(self, patch: str):
        self.heap = apply_patch(patch, self.heap)

def find_the_first_message_of_type(messages: List[TResponseInputItem], msg_type: str) -> TResponseInputItem | None:
    for msg in messages:
        if msg['type'] == msg_type:
            return msg
    return None

def apply_patch(patch: str, text: str) -> str:
    """
    将自定义 patch（*** Begin Patch / *** End Patch，@@ 开头表示 hunk）应用到 text。
    语义尽量与给定的 TypeScript 版本保持一致：
      1) 先尝试在指定范围内用 expected 块进行精确替换；
      2) 若存在仅上下文（以空格' '标记）的匹配，则在上下文末尾插入新增（'+'）；
      3) 若需要精确匹配但失败则报错；
      4) 否则根据 header（@@ 后的字符串）定位分节尾部插入；若 header 不存在则在文末附加，
         若提供了 header 但原文未找到，则先在文末创建一个 header 行再附加。

    :param patch: 自定义补丁文本
    :param text:  原始文档文本
    :return: 应用补丁后的文本
    :raises ValueError: 补丁格式非法或 hunk 无法匹配且必须精确匹配时
    """
    BEGIN = '*** Begin Patch'
    END = '*** End Patch'
    HUNK_START = '@@'
    END_OF_FILE = '*** End of File'

    # 如果不像一个 patch，就直接报错
    trimmed = patch.strip()
    if not (trimmed.startswith(BEGIN) and trimmed.endswith(END)):
        raise ValueError('Invalid patch format')

    # 工具：分割为行（保留空行）
    def to_lines(s: str) -> List[str]:
        # 统一换行：\r\n 或 \r -> \n
        s = s.replace('\r\n', '\n').replace('\r', '\n')
        return s.split('\n')

    def from_lines(lines: List[str]) -> str:
        return '\n'.join(lines)

    @dataclass
    class Hunk:
        header: str
        lines: List[str]

    patch_lines = to_lines(trimmed)

    # 提取 @@ 分块
    hunks: List[Hunk] = []
    i = 0
    # 跳过第一行 *** Begin Patch
    if i < len(patch_lines) and patch_lines[i].strip() == BEGIN:
        i += 1

    while i < len(patch_lines):
        line = patch_lines[i]
        if line.strip() == END:
            break
        if line.startswith(HUNK_START):
            # 解析 header
            header = line[len(HUNK_START):].strip()
            i += 1
            hunk_lines: List[str] = []
            while i < len(patch_lines):
                l = patch_lines[i]
                if l.startswith(HUNK_START) or l.strip() in (END, END_OF_FILE):
                    break
                # 只接受以 ' ', '-', '+' 开头的行；其他行当作上下文（以空格补齐）
                if l.startswith((' ', '-', '+')):
                    hunk_lines.append(l)
                else:
                    hunk_lines.append(' ' + l)
                i += 1
            hunks.append(Hunk(header=header, lines=hunk_lines))
            # 如果遇到 *** End of File，跳过它
            if i < len(patch_lines) and patch_lines[i].strip() == END_OF_FILE:
                i += 1
        else:
            # 非法或空行，跳过
            i += 1

    # 当前 character 行数组
    doc_lines = to_lines(text)

    # 一些小工具函数
    def find_header_index(header: str) -> int:
        if not header:
            return -1
        h = header.strip()
        for idx, l in enumerate(doc_lines):
            if l.strip() == h:
                return idx
        return -1

    def find_next_section_after(start_idx: int) -> int:
        if start_idx < 0:
            return -1
        for k in range(start_idx + 1, len(doc_lines)):
            # 简单约定：以 "#" 开头视为下一个分节（markdown 风格）
            if doc_lines[k].strip().startswith('#'):
                return k
        return len(doc_lines)  # 到文末

    def strip_prefix(s: str) -> str:
        return s[1:] if s else s

    def build_expected_and_replacement(hunk_lines: List[str]) -> Tuple[List[str], List[str]]:
        expected: List[str] = []
        replacement: List[str] = []
        for hl in hunk_lines:
            if hl == '':
                expected.append('')
                replacement.append('')
                continue
            tag = hl[0]
            txt = strip_prefix(hl)
            if tag == ' ':
                expected.append(txt)
                replacement.append(txt)
            elif tag == '-':
                expected.append(txt)
            elif tag == '+':
                replacement.append(txt)
        return expected, replacement

    def build_context_only(hunk_lines: List[str]) -> List[str]:
        return [strip_prefix(l) for l in hunk_lines if l.startswith(' ')]

    def find_subsequence(hay: List[str], needle: List[str], start: int = 0, end: int = None) -> int:
        if end is None:
            end = len(hay)
        if len(needle) == 0:
            return -1
        last_start = max(start, 0)
        last_idx = min(end, len(hay)) - len(needle)
        for s in range(last_start, last_idx + 1):
            ok = True
            for j in range(len(needle)):
                if hay[s + j] != needle[j]:
                    ok = False
                    break
            if ok:
                return s
        return -1

    def insert_at(arr: List[str], idx: int, items: List[str]) -> None:
        arr[idx:idx] = items

    def replace_at(arr: List[str], idx: int, remove_count: int, items: List[str]) -> None:
        arr[idx:idx + remove_count] = items

    # 应用每个 hunk
    for h in hunks:
        expected, replacement = build_expected_and_replacement(h.lines)
        context_only = build_context_only(h.lines)
        has_removals = any(l.startswith('-') for l in h.lines)
        requires_exact_match = has_removals or len(context_only) > 0
        header_label = (h.header or '').strip()

        # 确定搜索范围
        search_start = 0
        search_end = len(doc_lines)
        header_idx = find_header_index(h.header) if h.header else -1
        if header_idx >= 0:
            search_start = header_idx + 1
            search_end = find_next_section_after(header_idx)

        # 1) 期望块替换
        where = find_subsequence(doc_lines, expected, search_start, search_end)
        if where >= 0:
            replace_at(doc_lines, where, len(expected), replacement)
            continue

        # 2) 仅上下文匹配后插入新增
        if len(context_only) > 0:
            ctx_where = find_subsequence(
                doc_lines, context_only, search_start, search_end)
            if ctx_where >= 0:
                insert_pos = ctx_where + len(context_only)  # 紧跟上下文末尾插入
                # 只插入 '+' 产生且不在上下文里的行
                to_insert = [l for l in replacement if l not in context_only]
                insert_at(doc_lines, insert_pos, to_insert)
                continue

        if requires_exact_match:
            location_msg = f' near "{header_label}"' if header_label else ''
            raise ValueError(
                f'Patch hunk{location_msg} did not match target content')

        # 3) 兜底：基于 header 追加；若无 header 或未找到，则在文末追加
        if header_idx >= 0:
            sec_end = find_next_section_after(header_idx)
            insert_at(doc_lines, sec_end, replacement)
        else:
            # 如果提供了 header 但未找到，先创建 header
            if h.header:
                if len(doc_lines) > 0 and doc_lines[-1] != '':
                    doc_lines.append('')
                doc_lines.append(h.header)
            insert_at(doc_lines, len(doc_lines), replacement)

    # 去掉末尾多余换行并做右侧空白裁剪
    out = from_lines(doc_lines)
    out = re.sub(r'\n+$', '', out)
    return out.rstrip()
