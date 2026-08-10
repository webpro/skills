---
name: using-git-worktrees
description: >-
  Discover Git worktree layouts from the starting directory and preserve their
  shared workspace state. Use when cwd may be a worktree container, when
  selecting or creating a worktree within one, or when cwd is not a Git repo.
---

# Using Git Worktrees

## Discover the layout

Run `scripts/discover-worktree-layout.sh` once from the initial cwd to discover the layout:

- `worktree`: use the reported `worktree`; starting there means the user already selected that checkout, so do not create another for the same target. Create another only when the task requires a different revision and no suitable checkout exists.
- `single-container`: use the sole reported `repository`.
- `mixed-container`: select the reported `repository` that matches the task.
- Nonzero exit: stop; the target is not a recognized Git workspace.

`workspace` is the shared `.agents` root and is always reported. `container` is where checkouts live and is reported for bare repositories. They differ when the container is nested, as in `project/{.agents,worktree/{.bare,main,…}}`. Values are resolved from any starting depth, including inside a checkout, so use reported values rather than deriving them from cwd.

## Prefer flat structure

- Use or create `.agents` once, at the reported `workspace`; never add a per-worktree copy.
- For new single-repository containers, keep the bare Git directory at `.bare` and checked-out worktrees as sibling directories.
- When `container` is reported, create additional checkouts as its children. Otherwise inspect existing worktree paths and follow their convention.
- Follow existing path and branch conventions.
- Use the clean-git-repo skill for bulk cleanup.
