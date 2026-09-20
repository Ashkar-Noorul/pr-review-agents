# Tracking real GitHub PRs

Right now the pipeline reviews one hardcoded diff (`examples/sample_diff.py`). This doc lists everything needed to point it at a real GitHub pull request instead — as a step-by-step plan, not yet implemented.

## Overview of the change

```
BEFORE:  examples/sample_diff.py (hardcoded string) → graph.invoke({"diff": ...})

AFTER:   GitHub PR (owner/repo#123) → fetch diff via GitHub API
                                    → graph.invoke({"diff": ..., "pr_meta": {...}})
                                    → (optional) post results back to the PR
```

Three phases, roughly in order of effort:

1. **Read a real diff in** — minimum needed to stop using the sample diff.
2. **Handle real-world diff shape** — real diffs are messier than the sample (big, multi-file, noisy).
3. **Write results back to the PR** — turns this from "a script you run" into "an actual PR review tool."

---

## Phase 1 — Fetch a real diff

### 1. Get a GitHub token
- Create a **fine-grained personal access token** (Settings → Developer settings → Personal access tokens) scoped to `Pull requests: Read` on the repo(s) you'll test against.
- Add it to `.env`:
  ```
  GITHUB_TOKEN=ghp_xxxxxxxxxxxx
  ```
- Add `GITHUB_TOKEN` to `.env.example` (not the real value) so the requirement is documented.

### 2. New module: `src/github_client.py`
A single function that takes `owner`, `repo`, `pr_number` and returns the diff as a string — same shape `SAMPLE_DIFF` already has, so nothing downstream needs to change yet.

Two ways to implement it — pick one:

| Approach | Pros | Cons |
|---|---|---|
| Shell out to `gh pr diff <number>` via `subprocess` | Zero new dependencies, reuses your already-authenticated `gh` CLI | Requires `gh` installed wherever this runs; less portable (e.g. won't work in a plain CI container without setup) |
| GitHub REST API directly (`requests` + `Accept: application/vnd.github.v3.diff` header on `GET /repos/{owner}/{repo}/pulls/{pr_number}`) | Pure Python, portable anywhere, uses the `GITHUB_TOKEN` from `.env` | One more dependency (`requests`), a bit more code |

Recommendation: the REST API approach — it's what you'd need anyway for Phase 3 (posting comments back), so no wasted work.

### 3. Update `requirements.txt`
Add `requests` (skip if you go the `gh` CLI route).

### 4. Update `main.py` to accept a PR instead of the sample diff
Turn it into a CLI: `python main.py --repo owner/name --pr 42`, falling back to the sample diff if no args given (so `python main.py` with no args still works for quick testing).

```python
import argparse
...
parser.add_argument("--repo", help="owner/name")
parser.add_argument("--pr", type=int)
args = parser.parse_args()

if args.repo and args.pr:
    owner, repo = args.repo.split("/")
    diff = fetch_pr_diff(owner, repo, args.pr)
else:
    diff = SAMPLE_DIFF
```

**Checkpoint:** at this point, `python main.py --repo <you>/<some-repo> --pr <number>` runs the exact same graph against a real diff. This alone gets you "realistic," even before Phases 2–3.

---

## Phase 2 — Handle real diff shape

Real PRs break assumptions the sample diff doesn't test:

### 5. Size limits
A large PR's diff can be tens of thousands of tokens — bigger than what you'd want to send in one prompt (cost, latency, and the model's attention degrades over very long diffs anyway).
- Add a size guard: if the diff exceeds some threshold (e.g. ~8000 tokens), either truncate with a warning, or split per-file and review files individually, merging findings after.
- Per-file review is the more correct fix long-term but is a bigger change (each agent runs once per changed file instead of once per PR) — worth treating as its own follow-up rather than doing it as part of this integration.

### 6. Filtering noisy files
Real diffs include files you don't want reviewed: lockfiles (`package-lock.json`, `poetry.lock`), generated code, `.min.js`, images, vendored dependencies.
- Add a filter step after fetching the diff — either ask GitHub's API for the file list (`GET /repos/{owner}/{repo}/pulls/{pr}/files`) and drop known-noisy patterns before building the diff text, or post-process the unified diff string to strip `diff --git` blocks matching an ignore list.

### 7. State schema update — `src/state.py`
Add PR metadata to `ReviewState` so later phases (posting comments) know what to write back to:
```python
class ReviewState(TypedDict, total=False):
    diff: str
    pr_owner: str
    pr_repo: str
    pr_number: int
    ...
```
`coordinator` (currently a no-op in `graph.py`) becomes the natural place to populate/validate this.

---

## Phase 3 — Post results back to the PR

This is what makes it a real review tool instead of a script that prints to your terminal.

### 8. New module: `src/github_writer.py`
Two options, increasing in usefulness:

- **Single summary comment** — `POST /repos/{owner}/{repo}/issues/{pr_number}/comments` with the `TriageDecision` (decision, priority, summary, top findings) formatted as markdown. Simplest, one API call.
- **Inline review comments** — `POST /repos/{owner}/{repo}/pulls/{pr_number}/reviews` with per-finding comments anchored to specific files/lines. More useful (matches what a human reviewer's comments look like) but requires each `Finding.line_hint` to map to a real file + line number, which means capturing that mapping when the diff is parsed in Phase 1/2 rather than just treating the diff as one opaque string. This is the biggest structural change in the whole plan — every agent's `line_hint` field would need to become a real `(file, line)` reference instead of a free-text hint.

Recommendation: build the summary-comment version first (small, valuable on its own), treat inline comments as a later upgrade.

### 9. Decide what triggers a review
- **Manual** (what you have today, just pointed at a real PR): you run `python main.py --repo ... --pr ...` by hand.
- **Automated via GitHub Actions**: a workflow that runs this script on every `pull_request` event, using the Actions-provided `GITHUB_TOKEN` — no separate token/hosting needed, but only runs for repos where you control the Actions config.
- **Automated via webhook**: a small server (e.g. FastAPI) that GitHub calls on PR events, which then runs the graph — needed if you want this to react to PRs in real time. Bigger step (hosting, webhook secret verification), worth treating as its own future phase, not part of this integration pass.

---

## Suggested order to actually build this

1. Phase 1, steps 1–4 — get *any* real PR diff flowing through the existing graph. This is the smallest useful change and validates the rest works before adding complexity.
2. Phase 2, step 6 (noise filtering) — cheap, prevents wasted tokens/bad findings on lockfiles etc.
3. Phase 3, step 8 (summary comment only) — turns this into something that produces visible value on a real PR.
4. Everything else (size/chunking, inline comments, automation trigger) — revisit once the above is working and you've seen it run against a few real PRs.

## Out of scope for this pass
- Inline line-anchored comments (needs diff→line mapping, bigger change — see step 8)
- Per-file chunked review (needs restructuring the graph to run agents per-file, not per-PR)
- Automated triggering (GitHub Actions / webhook) — do this once the manual flow is proven
