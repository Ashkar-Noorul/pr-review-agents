"""
Run: python main.py
Or:  python main.py --repo owner/name --pr 42
Or:  python main.py --repo owner/name --pr 42 --post

With no --repo/--pr, runs the sample diff (examples/sample_diff.py). With
both given, fetches that PR's real diff from GitHub instead. Add --post to
also post the decision back to the PR as a summary comment (requires
GITHUB_TOKEN to have "Issues: Read and write" on that repo).

Prints the final triage decision plus every finding from every reviewer.
"""

import argparse
import os
import sys
from dotenv import load_dotenv

load_dotenv()

if not os.getenv("ANTHROPIC_API_KEY"):
    print("ERROR: Set ANTHROPIC_API_KEY in a .env file (see .env.example).")
    sys.exit(1)

from src.graph import build_graph
from src.github_client import fetch_pr_diff_filtered, GitHubClientError
from src.github_writer import format_decision_as_markdown, post_pr_comment, GitHubWriterError
from examples.sample_diff import SAMPLE_DIFF


def parse_args():
    parser = argparse.ArgumentParser(description="Run the PR review agent pipeline.")
    parser.add_argument("--repo", help="GitHub repo as owner/name, e.g. octocat/Hello-World")
    parser.add_argument("--pr", type=int, help="Pull request number")
    parser.add_argument(
        "--post",
        action="store_true",
        help="Post the decision back to the PR as a summary comment (requires --repo/--pr).",
    )
    return parser.parse_args()


def get_initial_state(args) -> dict:
    """Returns the dict to pass to graph.invoke() — just {"diff": ...} for the
    sample diff, or diff + pr_owner/pr_repo/pr_number for a real PR."""
    if not args.repo and not args.pr:
        print("No --repo/--pr given, using the sample diff.\n")
        return {"diff": SAMPLE_DIFF}

    if bool(args.repo) != bool(args.pr):
        print("ERROR: --repo and --pr must be given together.")
        sys.exit(1)

    if "/" not in args.repo:
        print(f"ERROR: --repo must be in owner/name form, got '{args.repo}'.")
        sys.exit(1)
    owner, repo = args.repo.split("/", 1)

    print(f"Fetching diff for {args.repo}#{args.pr} from GitHub...\n")
    try:
        diff, info = fetch_pr_diff_filtered(owner, repo, args.pr)
    except GitHubClientError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    if info["removed_files"]:
        print(
            f"Filtered out {len(info['removed_files'])} noisy file(s) "
            f"of {info['total_files']} total: {', '.join(info['removed_files'])}"
        )
    if info["truncated"]:
        print("Diff was truncated to stay within the size budget.")
    print()

    return {"diff": diff, "pr_owner": owner, "pr_repo": repo, "pr_number": args.pr}


def main():
    args = parse_args()

    if args.post and not (args.repo and args.pr):
        print("ERROR: --post requires --repo and --pr.")
        sys.exit(1)

    initial_state = get_initial_state(args)

    graph = build_graph()

    print("Running multi-agent review pipeline...\n")
    final_state = graph.invoke(initial_state)

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

    if args.post:
        body = format_decision_as_markdown(
            decision,
            security=final_state.get("security_output"),
            style=final_state.get("style_output"),
            logic=final_state.get("logic_output"),
        )
        owner, repo = args.repo.split("/", 1)
        print(f"\nPosting comment to {args.repo}#{args.pr}...")
        try:
            result = post_pr_comment(owner, repo, args.pr, body)
        except GitHubWriterError as e:
            print(f"ERROR: {e}")
            sys.exit(1)
        print(f"Posted: {result['html_url']}")


if __name__ == "__main__":
    main()
