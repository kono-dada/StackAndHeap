from typing import List
from pydantic import BaseModel


class Stage(BaseModel):
    name: str
    description: str
    instructions: str
    tools: List[str]
    visible: bool = True

    def __init__(self, **data):
        super().__init__(**data)
        from .register import register_stage
        register_stage(self)
