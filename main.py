from agent import agent, StackAndHeapContext
from agents import Runner, RunResult
from pprint import pprint
import asyncio


async def main():
    ctx = StackAndHeapContext()
    # ctx = StackAndHeapContext.load('logs/conversation.json')
    while True:
        conversation = ctx.build_conversation()
        response: RunResult = await Runner.run(
            starting_agent=agent,
            input=conversation,
            context=ctx
        )
        new_item = [item.to_input_item() for item in response.new_items]
        print('--- Agent Response ---')
        pprint(new_item)
        print('----------------------\n')
        ctx.add_messages(new_item)
        ctx.save('logs/conversation.json')


if __name__ == "__main__":
    asyncio.run(main())
