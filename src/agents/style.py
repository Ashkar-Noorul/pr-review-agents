from src.llm import get_llm
from src.state import ReviewState, ReviewerOutput, summarize_findings

SYSTEM_PROMPT = """You are a code style and readability reviewer. You ONLY look for:
- Unclear or inconsistent naming
- Overly complex functions that should be split up
- Dead code or unused imports/variables
- Missing or misleading comments/docstrings on non-trivial logic
- Violations of common language idioms (e.g. Pythonic style if this is Python)

Do NOT comment on security or correctness bugs. Be concise. If you find nothing, return
an empty findings list — do not invent issues.

For every finding, always set `file` (the exact path from the diff's header,
e.g. 'app/user_service.py') and `line_hint` (the specific line number in the new
file, worked out from the @@ hunk header — not a code snippet). Other agents'
findings get cross-checked against yours by file+line, so these must be precise."""


def style_reviewer(state:ReviewState)->dict:
    llm = get_llm().with_structured_output(ReviewerOutput)
    result = llm.invoke(
        [
            ("system", SYSTEM_PROMPT),
            ("user", f"Review this diff:\n\n{state['diff']}"),
        ]
    )
    result.summary = summarize_findings(result.findings)
    return {"style_output": result}