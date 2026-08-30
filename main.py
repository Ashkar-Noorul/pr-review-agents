"""
Run: python main.py

Loads the sample diff, runs it through the multi-agent graph, and prints
the final triage decision plus every finding from every reviewer.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

if not os.getenv("ANTHROPIC_API_KEY"):
    print("ERROR: Set ANTHROPIC_API_KEY in a .env file (see .env.example).")
    sys.exit(1)

from src.graph import build_graph
from examples.sample_diff import SAMPLE_DIFF


def main():
    graph = build_graph()

    print("Running multi-agent review pipeline...\n")
    final_state = graph.invoke({"diff": SAMPLE_DIFF})

    decision = final_state["decision"]

    print("=" * 60)
    print(f"DECISION: {decision.decision.upper()}")
    print(f"PRIORITY: {decision.priority_score}/10")
    print(f"SUMMARY:  {decision.summary}")
    print("=" * 60)

    print("\nTOP FINDINGS:")
    for f in decision.top_findings:
        print(f"  [{f.severity.upper():8}] {f.category}: {f.message}")

    print("\n--- Individual reviewer outputs ---")
    for name in ["security_output", "style_output", "logic_output"]:
        output = final_state.get(name)
        print(f"\n{name}:")
        print(f"  Summary: {output.summary}")
        for f in output.findings:
            print(f"  - [{f.severity}] {f.category}: {f.message}")


if __name__ == "__main__":
    main()
