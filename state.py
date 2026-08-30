from typing import TypedDict

class ReviewState(TypedDict, total=False):
    diff: str
    security_output: dict
    style_output: dict
    logic_output: dict
    decision: dict