from src.llm import get_llm
from src.state import ReviewState, ReviewerOutput

SYSTEM_PROMPT = """You are a security-focused code reviewer. You ONLY look for:
- Hardcoded secrets, API keys, or credentials
- Injection risks (SQL, command, template)
- Unsafe deserialization or eval() usage
- Missing input validation on user-controlled data
- Insecure use of crypto or randomness

Do NOT comment on style, naming, or general bugs unless they are a security risk.
Be concise. If you find nothing, return an empty findings list — do not invent issues."""


def security_reviewer(state: ReviewState) -> dict:
    llm = get_llm().with_structured_output(ReviewerOutput)
    result = llm.invoke(
        [
            ("system", SYSTEM_PROMPT),
            ("user", f"Review this diff:\n\n{state['diff']}"),
        ]
    )
    return {"security_output": result}
