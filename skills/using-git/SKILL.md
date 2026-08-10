---
name: using-git
description: >-
  House Git commit and pull request workflow. Use when committing or amending,
  writing commit messages, referencing or resolving issues from commits,
  creating or updating a pull request, rebasing, or handling a commit-signing
  failure.
---

# Using Git

- If the current directory is not a Git repository, use the using-git-worktrees skill to discover the layout.
- Check available plugins and remote tools first; do not assume `gh` is the right tool.

## Commits

- Match the maintainer's existing commit message style; ignore merge commits and squash-merged PR titles when inferring it.
- Use imperative mood to describe the actual change; avoid vague messages like "address PR review" or "fix findings".
- Suffix `(resolve #nn)` when the branch resolves an issue; reserve `close` for rejected pull requests. Only once per branch. Verify issue number and title on the tracker.
- For multi-line messages, write the message to a temporary file and run `git commit -F <file>`; the heredoc-in-`$()` pattern breaks on escaping.
- Rewriting local-only commits and the current pull request branch is fine. Update rewritten remote history with `--force-with-lease`; never rewrite protected branches.
- If SSH-key commit signing fails, use `--no-gpg-sign` to continue locally, but do not push; user may want to rebase and sign afterward.

## Pull requests

- Create from a branch off the latest default branch.
- Update pull request branches by rebasing onto the latest default branch and pushing with `--force-with-lease`.
  - Exception: when a pushed commit message references an issue or pull request, merge the default branch instead to avoid re-triggering reference events and related noise.
- Run the same class of (cheap) checks CI will (type-check, lint, test) before any push.
