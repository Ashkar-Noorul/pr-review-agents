"""
Fetches a pull request's diff from the GitHub REST API, and cleans it up
before it's handed to the review graph: strips out noisy files (lockfiles,
generated code, binaries) and caps the total size so a huge PR doesn't blow
past a reasonable prompt budget.

Requires GITHUB_TOKEN in the environment (a fine-grained PAT with
"Pull requests: Read-only" on the target repo is enough).
"""

import fnmatch
import os

import requests

# Default cap on diff size handed to the graph. ~4 chars/token is a rough
# rule of thumb, so this is roughly an 8000-token budget — see
# GITHUB_INTEGRATION.md Phase 2, step 5. This is a blunt truncation, not
# per-file chunking (that's called out as a separate, bigger change).
DEFAULT_MAX_DIFF_CHARS = 32_000

# Filenames/paths noisy enough that reviewing them wastes tokens and produces
# junk findings. Matched with fnmatch, so these are glob patterns, not regex.
NOISY_FILE_PATTERNS = [
    # lockfiles
    "*/package-lock.json", "package-lock.json",
    "*/yarn.lock", "yarn.lock",
    "*/pnpm-lock.yaml", "pnpm-lock.yaml",
    "*/poetry.lock", "poetry.lock",
    "*/Cargo.lock", "Cargo.lock",
    "*/Gemfile.lock", "Gemfile.lock",
    # minified / generated / build output
    "*.min.js", "*.min.css", "*.map",
    "*/dist/*", "*/build/*", "*/vendor/*", "*/node_modules/*",
    "*.generated.*",
    # binaries / images
    "*.png", "*.jpg", "*.jpeg", "*.gif", "*.ico", "*.svg",
    "*.woff", "*.woff2", "*.ttf", "*.eot",
    "*.pdf", "*.zip",
]


class GitHubClientError(Exception):
    """Raised when the GitHub API can't return a usable diff."""


def _auth_headers(accept: str) -> dict:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise GitHubClientError("GITHUB_TOKEN is not set in the environment.")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": accept,
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _handle_common_errors(response, owner: str, repo: str, pr_number: int) -> None:
    if response.status_code == 404:
        raise GitHubClientError(
            f"PR not found: {owner}/{repo}#{pr_number} "
            "(check the repo name, PR number, and that your token can see this repo)."
        )
    if response.status_code == 401:
        raise GitHubClientError("GitHub rejected the token — check GITHUB_TOKEN in .env.")
    response.raise_for_status()


def fetch_pr_diff(owner: str, repo: str, pr_number: int) -> str:
    """Raw unified diff for a PR, exactly as GitHub returns it — unfiltered."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = _auth_headers("application/vnd.github.v3.diff")

    response = requests.get(url, headers=headers, timeout=30)
    _handle_common_errors(response, owner, repo, pr_number)

    return response.text


def fetch_pr_filenames(owner: str, repo: str, pr_number: int) -> list:
    """All filenames changed in a PR, following pagination."""
    headers = _auth_headers("application/vnd.github+json")
    filenames = []
    page = 1

    while True:
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
        response = requests.get(
            url, headers=headers, params={"per_page": 100, "page": page}, timeout=30
        )
        _handle_common_errors(response, owner, repo, pr_number)

        page_items = response.json()
        if not page_items:
            break
        filenames.extend(item["filename"] for item in page_items)
        page += 1

    return filenames


def is_noisy_file(filename: str) -> bool:
    return any(fnmatch.fnmatch(filename, pattern) for pattern in NOISY_FILE_PATTERNS)


def filter_diff(diff_text: str, excluded_files: set) -> tuple:
    """Strip the `diff --git` blocks for any file in `excluded_files`.

    Returns (filtered_diff, removed_filenames). Splits on the `diff --git`
    line that starts every file's block in a unified diff — this is a plain
    text operation, no diff-parsing library needed.
    """
    if not excluded_files:
        return diff_text, []

    blocks = diff_text.split("diff --git ")
    preamble, file_blocks = blocks[0], blocks[1:]

    kept_blocks = []
    removed = []
    for block in file_blocks:
        # First line looks like: a/path/to/file.ext b/path/to/file.ext
        first_line = block.split("\n", 1)[0]
        # The "b/..." side reflects the file's post-change path.
        b_path = first_line.split(" b/", 1)[-1].strip() if " b/" in first_line else None

        if b_path in excluded_files:
            removed.append(b_path)
        else:
            kept_blocks.append(block)

    filtered = preamble + "".join(f"diff --git {block}" for block in kept_blocks)
    return filtered, removed


def truncate_diff(diff_text: str, max_chars: int = DEFAULT_MAX_DIFF_CHARS) -> tuple:
    """Cap diff size. Returns (possibly-truncated diff, was_truncated)."""
    if len(diff_text) <= max_chars:
        return diff_text, False
    truncated = diff_text[:max_chars]
    truncated += f"\n\n[... diff truncated at {max_chars} characters ...]"
    return truncated, True


def fetch_pr_diff_filtered(
    owner: str, repo: str, pr_number: int, max_chars: int = DEFAULT_MAX_DIFF_CHARS
) -> tuple:
    """Fetch a PR's diff, strip noisy files, and cap the size.

    Returns (diff_text, info) where info is a dict with `removed_files`,
    `truncated`, and `total_files` — the caller decides what to print.
    """
    raw_diff = fetch_pr_diff(owner, repo, pr_number)
    filenames = fetch_pr_filenames(owner, repo, pr_number)

    noisy = {f for f in filenames if is_noisy_file(f)}
    diff_text, removed_files = filter_diff(raw_diff, noisy)

    diff_text, truncated = truncate_diff(diff_text, max_chars)

    info = {
        "total_files": len(filenames),
        "removed_files": removed_files,
        "truncated": truncated,
    }
    return diff_text, info
