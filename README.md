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
SUMMARY:  This PR has multiple critical security vulnerabilities requiring immediate human attention: a hardcoded live API key committed to source control and a SQL injection vulnerability in get_user_by_email via string concatenation. Additionally, there's a critical off-by-one bug (range(len(items)+1)) that will cause an IndexError, plus missing null/empty checks on inputs. Style issues (poor naming, dead/no-op code in 'process', missing docstrings) are secondary but compound the risk profile of shipping this code as-is.
============================================================

TOP FINDINGS:
  [CRITICAL] hardcoded_secret: Hardcoded live API key found in source code. Must be removed and loaded via environment variables or a secrets manager; rotate the key immediately.
  [CRITICAL] sql_injection: get_user_by_email builds a SQL query via string concatenation with unsanitized user input, allowing SQL injection. Use parameterized queries instead.
  [CRITICAL] off_by_one: range(len(items) + 1) iterates one index beyond the list bounds, causing an IndexError on the last iteration.
  [MEDIUM  ] null_check: calculate_discount does not handle an empty or None items list.
  [MEDIUM  ] null_check: get_user_by_email does not check for None or empty email input before building the query.
  [MEDIUM  ] dead_code: 'process' is just a chain of redundant reassignments with no actual logic.
  [LOW     ] naming: Function 'process' and variables 'x', 'y', 'z', 'result' are non-descriptive.
  [LOW     ] naming: 'calculate_discount' doesn't clearly convey via naming that a discount is applied.
  [LOW     ] missing_docstring: New public methods lack docstrings explaining purpose, parameters, and return values.
```
