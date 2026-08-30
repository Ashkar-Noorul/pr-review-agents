import os
from langchain_anthropic import ChatAnthropic

def get_llm():
    return ChatAnthropic(
        model="claude-sonnet-5",
        max_tokens=4096
    )