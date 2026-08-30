from collections import Counter
from typing import TypedDict, List, Optional
from pydantic import BaseModel, Field

class Finding(BaseModel):
    """A single issue reported by a reviewer agent."""

    severity: str = Field(description="One of: low, medium, high, critical")
    category: str = Field(description="e.g. 'sql_injection', 'naming', 'null_check'")
    line_hint: Optional[str] = Field(
        default=None, description="Line number or code snippet the finding refers to"
    )
    message: str = Field(description="Clear, actionable description of the issue")

_SEVERITY_ORDER = ["critical", "high", "medium", "low"]


def summarize_findings(findings: List[Finding]) -> str:
    """Build a one-line summary from a findings list.

    The LLM's own `summary` field turned out to be unreliable (tool-calling
    isn't strictly schema-enforced), so we derive it ourselves instead of
    asking the model for it.
    """
    if not findings:
        return "No issues found."

    counts = Counter(f.severity.lower() for f in findings)
    parts = [f"{counts[s]} {s}" for s in _SEVERITY_ORDER if counts.get(s)]
    parts += [f"{n} {s}" for s, n in counts.items() if s not in _SEVERITY_ORDER]
    return f"{len(findings)} finding(s): " + ", ".join(parts)


class ReviewerOutput(BaseModel):
    """Structured output every specialist agent must return."""

    summary: str = Field(
        default="(no summary provided)",
        description="One-sentence summary of this reviewer's overall take",
    )
    findings: List[Finding]

class TriageDecision(BaseModel):
    """Final aggregated decision produced by the triage node."""

    decision: str = Field(description="One of: approve, request_changes, escalate")
    priority_score: int = Field(description="1 (low) to 10 (critical)", ge=1, le=10)
    summary: str = Field(description="Short human-readable summary of the overall review")
    top_findings: List[Finding] = Field(default_factory=list, description="Most important findings across all reviewers")

class ReviewState(TypedDict, total=False):
    diff: str
    security_output: ReviewerOutput
    style_output: ReviewerOutput
    logic_output: ReviewerOutput
    decision: TriageDecision