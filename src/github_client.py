"""
Fetches a pull request's diff from the GitHub REST API.

Requires GITHUB_TOKEN in the environment (a fine-grained PAT with
"Pull requests: Read-only" on the target repo is enough).
"""

import os

import requests


class GitHubClientError(Exception):
    """Raised when the GitHub API can't return a usable diff."""


def fetch_pr_diff(owner: str, repo: str, pr_number: int) -> str:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise GitHubClientError("GITHUB_TOKEN is not set in the environment.")

    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3.diff",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    response = requests.get(url, headers=headers, timeout=30)

    if response.status_code == 404:
        raise GitHubClientError(
            f"PR not found: {owner}/{repo}#{pr_number} "
            "(check the repo name, PR number, and that your token can see this repo)."
        )
    if response.status_code == 401:
        raise GitHubClientError("GitHub rejected the token — check GITHUB_TOKEN in .env.")
    response.raise_for_status()

    return response.text
