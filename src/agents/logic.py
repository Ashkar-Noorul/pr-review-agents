from src.llm import get_llm
from src.state import ReviewState, ReviewerOutput, summarize_findings

SYSTEM_PROMPT = """You are a correctness-focused code reviewer. You ONLY look for:
- Off-by-one errors, incorrect boundary conditions
- Null/None handling gaps
- Incorrect control flow or logic errors
- Race conditions or state mutation bugs
- Edge cases the code doesn't account for (empty input, large input, etc.)

Do NOT comment on style or security unless it directly causes incorrect behavior.
Be concise. If you find nothing, return an empty findings list — do not invent issues."""


def logic_reviewer(state: ReviewState) -> dict:
    llm = get_llm().with_structured_output(ReviewerOutput)
    result = llm.invoke(
        [
            ("system", SYSTEM_PROMPT),
            ("user", f"Review this diff:\n\n{state['diff']}"),
        ]
    )
    result.summary = summarize_findings(result.findings)
    return {"logic_output": result}