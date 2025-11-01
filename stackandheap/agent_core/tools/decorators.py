from agents import RunContextWrapper
from functools import wraps
from typing import Callable, TypeVar, cast

from ..context import StackAndHeapContext

F = TypeVar('F', bound=Callable[..., str])
MAX_CONTEXT_LENGTH = 80  # Maximum number of messages in the overall context


def require_not_in_main_loop(func: F) -> F:
    """tools装饰器，确保当前属于某个子任务的范畴"""
    @wraps(func)
    def wrapper(wrapper: RunContextWrapper[StackAndHeapContext], *args, **kwargs):
        if len(wrapper.context.stack) == 1:
            raise RuntimeError(
                "You are in the main loop now. You MUST start a new subtask before calling this tool."
            )
        return func(wrapper, *args, **kwargs)
    return cast(F, wrapper)


def remaining_frame_space_reminder(func: F) -> F:
    """tools装饰器，提醒当前frame剩余空间。"""
    @wraps(func)
    def wrapper(wrapper: RunContextWrapper[StackAndHeapContext], *args, **kwargs):
        cm = wrapper.context
        context_remaining = sum(len(frame.messages) for frame in cm.stack)
        if context_remaining >= MAX_CONTEXT_LENGTH - 10:
            reminder = f"Warning: Only {MAX_CONTEXT_LENGTH - context_remaining} messages left in the overall context. You MUST finish some subtasks soon to avoid reaching the limit."
            return func(wrapper, *args, **kwargs) + f'<system>{reminder}</system>'
        return func(wrapper, *args, **kwargs)
    return cast(F, wrapper)
