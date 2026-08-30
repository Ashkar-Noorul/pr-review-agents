# PR Review Agents

A multi-agent PR review system built with [LangGraph](https://github.com/langchain-ai/langgraph). A diff is passed through a graph of specialized agents (security, style, logic) that each produce structured findings, which are then combined into a final review decision.

## Status

End-to-end pipeline is working: `coordinator → [security, style, logic] → triage → END`, running against a hardcoded sample diff. Real diff ingestion (e.g. from a GitHub PR) is next.

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

## Running

```bash
python main.py
```

This runs the sample diff in `examples/sample_diff.py` through the full graph and prints the final triage decision plus each reviewer's individual findings.

## Example output

```
============================================================
DECISION: ESCALATE
PRIORITY: 10/10
SUMMARY:  This PR contains multiple critical issues requiring immediate attention before merge: a hardcoded live API key exposed in source (requires rotation), a SQL injection vulnerability from unsanitized string concatenation in get_user_by_email, and a critical off-by-one bug in calculate_discount that will cause an IndexError in production. Additional medium-severity issues include missing null/None checks on `email` and `items` inputs, and several low-priority style issues (poor naming, missing docstrings, dead code, magic numbers). Given the presence of an exposed secret and an active SQL injection vector, this should be escalated for immediate human review and remediation before any further work proceeds.
============================================================

TOP FINDINGS:
  [CRITICAL] hardcoded_secret: Hardcoded live API key ('sk-live-...') committed to source code. Must be removed, moved to environment variable/secrets manager, and the key rotated immediately since it is exposed in version control history.
  [CRITICAL] sql_injection: get_user_by_email builds SQL via raw string concatenation with unsanitized user input, enabling SQL injection. Must use parameterized queries/prepared statements.
  [CRITICAL] off_by_one: calculate_discount uses range(len(items) + 1), causing an IndexError on the last loop iteration when accessing items[i]['price']. Fix to range(len(items)).
  [MEDIUM  ] null_check: get_user_by_email does not validate that email is non-None/non-empty before building the query, risking a TypeError.
  [MEDIUM  ] edge_case: calculate_discount does not guard against items being None (causing TypeError on len()) or handle an empty list explicitly.
  [MEDIUM  ] naming: Variable names x, y, z, result in process() are meaningless and provide no indication of intent.
  [LOW     ] dead_code: The process method chains variables with no actual logic; appears to be dead/placeholder code.
  [LOW     ] missing_comment: get_user_by_email, calculate_discount, and process all lack docstrings explaining purpose, inputs, and return values.
  [LOW     ] naming: calculate_discount hardcodes a 0.9 multiplier with no named constant or comment explaining the discount rate.

--- Individual reviewer outputs ---

security_output:
  Summary: 2 finding(s): 2 critical
  - [critical] hardcoded_secret: Hardcoded API key assigned directly in source code ('sk-live-...'). Move to environment variable or secrets manager, and rotate this key since it is now exposed in version control history.
  - [critical] sql_injection: get_user_by_email builds a SQL query via raw string concatenation with unsanitized user input (email), enabling SQL injection. Use parameterized queries/prepared statements instead.

style_output:
  Summary: 4 finding(s): 1 medium, 3 low
  - [low] dead_code: The `process` method assigns `x` through a chain of variables (`y`, `z`, `result`) with no actual logic; this appears to be dead/placeholder code and provides no clarity or value.
  - [medium] naming: Variable names `x`, `y`, `z`, `result` in `process` are meaningless and give no indication of purpose or intent.
  - [low] missing_comment: `get_user_by_email`, `calculate_discount`, and `process` all lack docstrings explaining their purpose, expected inputs, and return values, despite performing non-trivial operations.
  - [low] naming: `calculate_discount` hardcodes a 0.9 multiplier with no named constant or comment explaining what discount rate this represents.

logic_output:
  Summary: 3 finding(s): 1 critical, 2 medium
  - [critical] off_by_one: In calculate_discount, `range(len(items) + 1)` iterates one index past the end of the list, causing an IndexError when accessing items[i]['price'] on the last iteration. Should be `range(len(items))`.
  - [medium] edge_case: calculate_discount does not handle the case of an empty items list separately, but more importantly does not guard against items being None, which would raise a TypeError on len(items).
  - [medium] null_check: get_user_by_email does not validate that `email` is not None/empty before building the query; passing None would cause a TypeError when concatenating strings.
```

Note: each reviewer's `Summary` line is computed in code from its findings (`summarize_findings` in `src/state.py`), not generated by the LLM — Claude's tool-calling isn't strictly schema-enforced, so an LLM-written summary field was unreliable and often came back empty.
