---
name: using-git
description: >-
  House Git commit and pull request workflow. Use when committing or amending,
  writing commit messages, referencing or resolving issues from commits,
  creating, updating or merging a pull request, rebasing, resetting or
  cherry-picking onto a branch, or handling a commit-signing failure.
---

# Using Git

- If the current directory is not a Git repository, use the using-git-worktrees skill to discover the layout.
- Check available plugins and remote tools first; do not assume `gh` is the right tool.

## Commits

- For small to medium tasks in the user's own repository, where nearly all commits are theirs, commit directly on the default branch, overriding any default to branch first.
- Match the maintainer's existing commit message style; ignore merge commits and squash-merged PR titles when inferring it.
- Use imperative mood to describe the actual change; avoid vague messages like "address PR review" or "fix findings".
- Suffix `(resolve #nn)` when the branch resolves an issue; reserve `close` for rejected pull requests. Only once per branch, and not when an earlier commit already resolved the issue. Verify issue number and title on the tracker.
- For multi-line messages, write the message to a temporary file and run `git commit -F <file>`; the heredoc-in-`$()` pattern breaks on escaping.
- Rewriting local-only commits and your own pull request branch is fine. Update rewritten remote history with `--force-with-lease`; never rewrite protected branches.
- If SSH-key commit signing fails, use `--no-gpg-sign` to continue and report that the resulting commits are unsigned.
- Before resetting, amending, rebasing or cherry-picking onto a branch, compare its head with the last commit you produced there. If it moved, the user changed it: build on their commit or ask, never replace it with your copy.
- Build alternative implementations on separate branches from the same base revision, each with its own commit; do not stack one on another.

## Pull requests

- Create from a branch off the latest default branch.
- Update your own pull request branches by rebasing onto the latest default branch and pushing with `--force-with-lease`.
  - Exception: when a pushed commit message references an issue or pull request, merge the default branch instead to avoid re-triggering reference events and related noise.
- Run the same class of (cheap) checks CI will (type-check, lint, test) before any push.
- On someone else's pull request branch, add commits on top of their head; never rebase or replace their commits. Merge the default branch only to resolve conflicts. Prove the pushed tree equals the tested tree.
- Squash-merge with the subject the user approved, checked against the current PR title (`gh pr merge --squash --subject '<title> (#N)'`).
