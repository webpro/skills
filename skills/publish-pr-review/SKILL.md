---
name: publish-pr-review
description: Publish an already-completed pull request review as one concise verdict with actionable findings attached inline. Use when the user asks to post, submit, or publish review findings; do not use this skill to conduct the review itself.
---

# Publish PR Review

Publish a review that is already written, taking its verdict and findings from this conversation. Do not conduct the review here, and do not introduce a finding it did not make.

## Do not publish when

Stop on any of these, say which one, and ask for what would clear it.

1. The user has not explicitly authorized this publish. Authorization covers the verdict and its inline comments and nothing else: no code changes, labels, reviewer requests, or merges.
2. The head has moved past the revision that was reviewed. Checking the findings against the new commits is reviewing rather than publishing, so hand it back instead of doing it here, even when they look like they survive. Publishing against unreviewed code is worse than publishing late.
3. Every finding is already on the pull request. Read the existing reviews and threads first, including other people's and ones predating the reviewed revision. Drop the findings those threads already cover, say which you dropped, and stop only when nothing is left to add. This condition covers duplication alone; a moved head is condition 2 and outranks it.
4. The exact copy and inline locations have not been shown and confirmed. Show them as their own step, before any mutation.

## Public copy

Pass the verdict and every finding through the `review-prose` skill when it is available. It owns the wording and whatever house style is active. This skill owns only where each piece goes.

- Put the verdict and its product-level rationale in the review body.
- Anchor each actionable finding to the changed line it concerns. Lead with priority, then the observable consequence, then the ownership-level correction.
- Keep one concern per inline thread.
- When no changed line can honestly anchor a finding, put it in the body with its file and line rather than anchoring it to an adjacent line.
- Reuse wording the user already approved verbatim, adapting only local paths and links to the pull request UI.
- Omit command logs, test ledgers, tool names, local paths, and review-process narration.

## Submit

1. Send one review carrying the verdict and every inline finding. `APPROVE` when ready, `REQUEST_CHANGES` when a finding blocks, `COMMENT` otherwise.
2. Verify the published state, head commit, comment bodies, paths, and line locations.
3. Report a direct link, and nothing else.

## GitHub

`gh pr review` sends a body only and cannot attach inline comments. One request per finding fans the review out into unrelated threads. Send the whole review at once:

```sh
gh api --method POST repos/{owner}/{repo}/pulls/NUMBER/reviews --input - <<'JSON'
{
  "commit_id": "PINNED_HEAD_SHA",
  "event": "REQUEST_CHANGES",
  "body": "Verdict and rationale.",
  "comments": [
    { "path": "src/parse.js", "line": 42, "side": "RIGHT", "body": "P1 ..." },
    { "path": "src/parse.js", "start_line": 55, "start_side": "RIGHT", "line": 58, "side": "RIGHT", "body": "P2 ..." }
  ]
}
JSON
```

- Set `event`. Omitting it leaves the review `PENDING` and unpublished.
- Set `commit_id` to the reviewed head. It otherwise defaults to the newest commit, publishing the review against code nobody reviewed.
- Anchor with `line` and `side`; add `start_line` and `start_side` for a range. Use `RIGHT` unless the finding is about a line the pull request deletes.
- `position` is deprecated. Do not use it.
- Every anchor must sit inside a diff hunk, both ends of a range included. An anchor outside a hunk fails the whole request with `422 pull_request_review_thread.line must be part of the diff`, taking the verdict and every other finding with it.
- Collect the commentable lines from the per-file `patch` in `repos/{owner}/{repo}/pulls/NUMBER/files` before sending.
