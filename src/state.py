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

class ReviewerOutput(BaseModel):
    """Structured output every specialist agent must return."""

    findings: List[Finding]
    summary: str = Field(description="One-sentence summary of this reviewer's overall take")

class TriageDecision(BaseModel):
    """Final aggregated decision produced by the triage node."""

    decision: str = Field(description="One of: approve, request_changes, escalate")
    priority_score: int = Field(description="1 (low) to 10 (critical)", ge=1, le=10)
    summary: str = Field(description="Short human-readable summary of the overall review")
    top_findings: List[Finding] = Field(description="Most important findings across all reviewers")

class ReviewState(TypedDict, total=False):
    diff: str
    security_output: ReviewerOutput
    style_output: ReviewerOutput
    logic_output: ReviewerOutput
    decision: TriageDecision