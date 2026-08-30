import os
from langchain_anthropic import ChatAnthropic

def get_llm(temperature:float=0.0):
    return ChatAnthropic(
        model="claude-sonnet-5",
        temperature=temperature,
        max_tokens=1024
    )