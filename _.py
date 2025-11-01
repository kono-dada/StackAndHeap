
from agents.function_schema import function_schema
from pprint import pprint

docs = """ Perform brainstorming and self-reflection to generate new ideas or strategies.
You can think about but are not limited to the following aspects:
    - What possible stack structure do you have in mind?
    - What is the character's current mental state or emotion state?
    - What else information is needed?
    - What theories or methods can be applied?
    - What to do next?
    - What interesting or magical things can you do with the tools?
    - Other considerations?

Args:
    thinking: Your thoughts, ideas, or reflections`
"""

def brainstorm(thinking: str):
    
    return

brainstorm.__doc__ = docs

pprint(function_schema(brainstorm))