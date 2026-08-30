from src.llm import get_llm
from src.state import ReviewState, TriageDecision

SYSTEM_PROMPT = """You are the lead reviewer on a code review team. Three specialists have
already reviewed this PR: security, style, and logic/correctness. Your job is to:

1. Merge their findings into one prioritized list (most important first)
2. Decide: 'approve' (no blocking issues), 'request_changes' (fixable issues found),
   or 'escalate' (critical/security issue needs a human immediately)
3. Assign a priority_score from 1-10 based on the most severe finding

Critical security findings should almost always mean 'escalate' or 'request_changes'.
Pure style nits alone should mean 'approve' with low priority."""


def triage_agent(state: ReviewState) -> dict:
    llm = get_llm().with_structured_output(TriageDecision)

    security = state.get("security_output")
    style = state.get("style_output")
    logic = state.get("logic_output")

    context = f"""SECURITY REVIEWER FINDINGS:
{security.model_dump_json(indent=2) if security else "No output"}

STYLE REVIEWER FINDINGS:
{style.model_dump_json(indent=2) if style else "No output"}

LOGIC REVIEWER FINDINGS:
{logic.model_dump_json(indent=2) if logic else "No output"}
"""

    result = llm.invoke(
        [
            ("system", SYSTEM_PROMPT),
            ("user", context),
        ]
    )
    return {"decision": result}
