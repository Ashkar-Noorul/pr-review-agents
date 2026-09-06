from src.llm import get_llm
from src.state import ReviewState, TriageDecision, find_overlaps

SYSTEM_PROMPT = """You are the lead reviewer on a code review team. Three specialists have
already reviewed this PR: security, style, and logic/correctness. Your job is to:

1. Merge their findings into one prioritized list (most important first)
2. Decide: 'approve' (no blocking issues), 'request_changes' (fixable issues found),
   or 'escalate' (critical/security issue needs a human immediately)
3. Assign a priority_score from 1-10 based on the most severe finding

Critical security findings should almost always mean 'escalate' or 'request_changes'.
Pure style nits alone should mean 'approve' with low priority.

You will sometimes be given an OVERLAPPING LOCATIONS section, listing lines where
more than one specialist commented on the exact same file+line. When that happens:
- security's opinion on a location always outweighs style's or logic's for that
  location — a style/logic comment never excuses a real security issue.
- between logic and style on the same location, logic (correctness) wins — a
  performance or style justification does not override an actual correctness bug,
  but it CAN downgrade a pure style nit if logic explicitly explains the code is
  intentional (e.g. written that way for performance).
- when you fold an overlapping location into top_findings, mention in that
  finding's message that multiple reviewers commented on it and how you resolved
  the disagreement, so the reasoning isn't silently dropped.
If no overlaps are listed, just merge normally — there's nothing to reconcile."""


def _format_reviewer(name: str, output) -> str:
    if not output:
        return f"{name.upper()} REVIEWER FINDINGS:\nNo output"
    return f"{name.upper()} REVIEWER FINDINGS:\n{output.model_dump_json(indent=2)}"


def _format_overlaps(overlaps: list) -> str:
    if not overlaps:
        return "OVERLAPPING LOCATIONS:\nNone — no two reviewers commented on the same file+line."

    lines = ["OVERLAPPING LOCATIONS:"]
    for overlap in overlaps:
        lines.append(f"\n{overlap['file']}:{overlap['line']}")
        for agent_name, finding in overlap["findings"]:
            lines.append(f"  - [{agent_name}] ({finding.severity}) {finding.message}")
    return "\n".join(lines)


def triage_agent(state: ReviewState) -> dict:
    llm = get_llm().with_structured_output(TriageDecision)

    security = state.get("security_output")
    style = state.get("style_output")
    logic = state.get("logic_output")

    overlaps = find_overlaps(
        {
            "security": security.findings if security else [],
            "style": style.findings if style else [],
            "logic": logic.findings if logic else [],
        }
    )

    context = "\n\n".join(
        [
            _format_reviewer("security", security),
            _format_reviewer("style", style),
            _format_reviewer("logic", logic),
            _format_overlaps(overlaps),
        ]
    )

    result = llm.invoke(
        [
            ("system", SYSTEM_PROMPT),
            ("user", context),
        ]
    )
    return {"decision": result}
