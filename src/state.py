from collections import Counter, defaultdict
from typing import TypedDict, List, Optional
from pydantic import BaseModel, Field

class Finding(BaseModel):
    """A single issue reported by a reviewer agent."""

    severity: str = Field(description="One of: low, medium, high, critical")
    category: str = Field(description="e.g. 'sql_injection', 'naming', 'null_check'")
    file: Optional[str] = Field(
        default=None,
        description="The file path this finding refers to, exactly as it appears "
        "in the diff header (e.g. 'app/user_service.py')",
    )
    line_hint: Optional[str] = Field(
        default=None,
        description="The specific line number (in the new version of the file) "
        "this finding refers to, e.g. '17'. Always give a line number if you can "
        "work it out from the diff's @@ hunk header — not a code snippet.",
    )
    message: str = Field(description="Clear, actionable description of the issue")

    def location_key(self) -> Optional[tuple]:
        """Normalized (file, line) key for correlating findings across agents.

        Returns None when either half is missing — those findings simply can't
        be checked for overlap with anyone else's.
        """
        if not self.file or not self.line_hint:
            return None
        return (self.file.strip().lower(), self.line_hint.strip())

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


def find_overlaps(
    reviewer_findings: dict,
) -> List[dict]:
    """Detect findings from *different* agents that point at the same (file, line).

    `reviewer_findings` maps agent name -> list[Finding], e.g.
    {"security": [...], "style": [...], "logic": [...]}.

    Findings correlate only when both `file` and `line_hint` are present and
    match exactly — this is a simple, honest heuristic, not fuzzy matching.
    Two agents commenting on the same function but different lines, or using
    differently-formatted line hints, will NOT be caught by this. It exists so
    the triage node gets an explicit, code-computed list of overlaps instead of
    having to spot them itself by reading three separate findings lists.
    """
    by_location = defaultdict(list)
    for agent_name, findings in reviewer_findings.items():
        for finding in findings:
            key = finding.location_key()
            if key is not None:
                by_location[key].append((agent_name, finding))

    overlaps = []
    for (file, line), entries in by_location.items():
        agents_here = {agent for agent, _ in entries}
        if len(agents_here) > 1:
            overlaps.append(
                {
                    "file": file,
                    "line": line,
                    "findings": entries,
                }
            )
    return overlaps


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
    # Only set when reviewing a real GitHub PR (absent for the sample diff).
    # Not used yet — this is what Phase 3 (posting results back to the PR)
    # will read to know where to post.
    pr_owner: str
    pr_repo: str
    pr_number: int
    security_output: ReviewerOutput
    style_output: ReviewerOutput
    logic_output: ReviewerOutput
    decision: TriageDecision