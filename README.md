# PR Review Agents

A multi-agent PR review system built with [LangGraph](https://github.com/langchain-ai/langgraph). A diff is passed through a graph of specialized agents (security, style, logic) that each produce structured findings, which are then combined into a final review decision.

## Status

Early scaffolding — state schema and environment setup are in place; agent nodes and the graph are next.

## Setup

```bash
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=your-key-here
```

Verify setup:

```bash
python test_setup.py
```
