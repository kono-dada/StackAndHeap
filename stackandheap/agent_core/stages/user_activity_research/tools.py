import io
from agents import function_tool, RunContextWrapper
from ...decorators import remaining_frame_space_reminder, require_not_in_main_loop
from ...context import StackAndHeapContext
from contextlib import redirect_stdout, redirect_stderr
from code import InteractiveConsole
from ...tools import register_tools

initial_code = """

"""

MAX_OUTPUT_LENGTH = 2000

class InProcessREPL:
    """
    使用 code.InteractiveConsole 在当前进程内模拟 REPL。
    支持多行、持久变量，返回 stdout+stderr。
    """
    def __init__(self):
        self.console = InteractiveConsole(locals={})
        self.execute(initial_code)

    def execute(self, code: str) -> str:
        out = io.StringIO()
        # InteractiveConsole.push 需要逐行送入；返回 True 表示还需更多行
        with redirect_stdout(out), redirect_stderr(out):
            # runsource 一次执行整段代码，不用逐行 push
            self.console.runsource(code, symbol="exec")
        result = out.getvalue()
        if len(result) <= MAX_OUTPUT_LENGTH:
            return result
        else:
            return result[:MAX_OUTPUT_LENGTH] + f"\n...[output truncated with {len(result) - MAX_OUTPUT_LENGTH} characters]..."
    
r = InProcessREPL()

@register_tools
@remaining_frame_space_reminder
@require_not_in_main_loop
def execute_code_in_repl(wrapper: RunContextWrapper[StackAndHeapContext], code: str) -> str:
    f"""Execute the given code in an in-process REPL and return the output.
The maximum length of code is {MAX_OUTPUT_LENGTH} characters.

Args:
    code: The code to execute in the REPL
Returns:
    The output from the REPL execution
    """
    output = r.execute(code)
    return output

if __name__ == "__main__":
    print(r.execute("import aw_client; print(1)"))