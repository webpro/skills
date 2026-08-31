---
name: using-git-worktrees
description: >-
  Discover and select Git worktree layouts from the starting directory. Use
  when asked to find, choose, reuse, or create a checkout or worktree; when cwd
  is above checkouts, a worktree container, or not a Git repo; or when deciding
  where shared .agents state belongs. Do not use for ordinary Git history,
  commit, or pull request work, or for bulk cleanup.
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
