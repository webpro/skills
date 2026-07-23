---
name: clean-git-repo
description: >-
  Clean up a git repository: delete branches whose PRs merged (incl.
  squash-merges), remove their safely removable linked worktrees, list or delete
  local branches past a confirmed age threshold, prune stale remote-tracking
  refs and worktree metadata, and optionally prune local tags absent from the
  remote, run gc, or delete merged remote branches. Use when asked to clean up /
  prune / tidy git branches or worktrees, remove merged or stale branches,
  delete old branches, prune origin/* refs, or clear out a repo's
  branch/worktree list, including from a directory containing worktrees from one
  or more repositories. Reports first (dry run); never touches
  current/default/kept branches or main, dirty, ignored-content, locked,
  detached, unavailable, or submodule-containing worktrees.
---

# Clean Git Repo

Report and clean up local branches, linked worktrees, stale remote-tracking
refs, worktree metadata, and tags. Run from either:

- a worktree or Git directory to handle one repository; or
- a worktree container whose immediate child directories are worktrees.

In container mode, the script groups children by their resolved Git common
directory and handles each repository once. It does not recurse beyond immediate
children. A bundled script does the deterministic detection and deletion; you
orchestrate the safety gates.

Resolve [scripts/clean-git-repo.sh][1] to an absolute path once and run it from
the target repository or worktree container, not the skill directory. In Claude
Code: `SCRIPT="${CLAUDE_SKILL_DIR}/scripts/clean-git-repo.sh"`.

```bash
"$SCRIPT"           # report only (dry run)
"$SCRIPT" --apply   # delete the SAFE tier
```

The script's `--help` lists every flag; the key ones appear below.

## Safety model: confirm unless the action is safe

| Tier        | Actions                                                                                                                                                                                                                                                                                                                               | Confirmation           |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------- |
| **Safe**    | `git fetch --prune` (remote-tracking refs), `git worktree prune`, delete **merged** branches (tip provably in the merge), first removing an attached clean linked worktree with no ignored files and without `--force`                                                                                                                | none (apply + report)  |
| **Confirm** | delete **MERGED-but-advanced** (`--force-merged`), **GONE** (`--force-gone`), or **STALE** (`--stale`) branches and any attached safely removable linked worktrees; matching **remote** branches whose remote tip is identical or provably merged (`--remote`); local tags absent from the remote (`--prune-tags`); `git gc` (`--gc`) | ask the user first     |
| **Never**   | the current branch, default branch, `--keep` matches, and main, dirty, ignored-content, locked, detached, unavailable, or submodule-containing worktrees                                                                                                                                                                              | excluded by the script |

A linked worktree follows its branch's existing tier only when it is clean and
contains no ignored files or submodules. On apply, the script rechecks those
conditions, runs `git worktree remove` without `--force`, and deletes the branch
only if removal succeeds. The script never force-removes a worktree.

A branch is **merged** when GitHub (`gh`) reports its PR merged, or its tip is
an ancestor of the base, so squash- and rebase-merges are caught, not just
fast-forwards. A squash-merged branch auto-deletes only when its tip is
contained in the merged PR head; if the local tip advanced past it (extra
commits that never reached the PR, or a merged head not fetched locally), it
drops to the **`--force-merged`** confirm tier instead of being force-deleted.

## Workflow

Copy this checklist and work through it:

- [ ] 1\. Confirm the target: `git rev-parse --show-toplevel` for one repository, or
      inspect the immediate child worktrees when the current directory is a
      container.
- [ ] 2\. Run the script with **no flags** to fetch+prune refs and print the
      categorized plan.
- [ ] 3\. Relay the plan per repository: counts per tier, the SAFE list verbatim,
      and every worktree path that would be removed.
- [ ] 4\. Apply the **SAFE** tier (`--apply`). No confirmation needed; report what
      was deleted.
- [ ] 5\. For each non-empty CONFIRM tier, ask the user which to include, then
      re-run `--apply` with the matching opt-in flags (e.g. `--apply --force-gone
--stale`). To act on only a **subset** of a tier, delete those branches by
      name rather than passing the whole-tier flag. For an attached worktree, first
      run `git worktree remove <path>` without `--force`; delete the branch only if
      removal succeeds.
- [ ] 6\. Verify: re-run with no flags and confirm the targeted tiers are now empty.

### Step 2: report

```bash
"$SCRIPT"                 # default 90-day stale threshold
"$SCRIPT" --age-days 180  # adjust the threshold the user confirms
```

Read the output. It groups branches as **SAFE TO DELETE — merged**, **CONFIRM —
merged, local tip advanced**, **CONFIRM — gone upstream**, **CONFIRM — stale >
Nd**, **CONFIRM — matching remote branches**, **REMOTE SKIP**, **CONFIRM — local
tags absent from <remote>**, **PROTECTED**, and a kept **ACTIVE** count.
`[gone]` upstream alone is _not_ proof of a merge: it can also be a
closed-unmerged PR. GONE is therefore always a confirm tier; each gone entry
shows how many commits it holds ahead of the base, so you can see what a delete
would discard. Each stale entry carries its push-state (`never pushed — local
only`, `ahead N — unpushed work`, or `in sync with <upstream>`), so you can see
at a glance whether deleting it discards work that exists nowhere else. With
`--remote`, review both remote sections: remote branches delete only when the
remote-tracking tip is identical to the local branch being deleted or
independently proven merged; otherwise they are reported as skipped. A branch
entry with `; worktree <path>` also removes that safely removable linked
worktree when its tier is applied. Container mode prints a header for each
distinct Git common directory.

### Step 4 & 5: apply

```bash
"$SCRIPT" --apply                          # SAFE only (merged branches)
"$SCRIPT" --apply --force-merged           # + delete merged branches whose tip advanced past the PR
"$SCRIPT" --apply --force-gone             # + delete GONE branches
"$SCRIPT" --apply --stale --age-days 180   # + delete STALE branches
"$SCRIPT" --apply --remote                 # + delete matching remote branches after lease check
"$SCRIPT" --apply --prune-tags --gc        # + prune listed local tags absent from the remote, reclaim space
```

Other flags: `--base <branch>` to override default-branch detection, `--keep
'<glob>'` to protect extra branches (repeatable), `--no-fetch` for offline,
`--no-gh` to skip GitHub lookups.

## Graceful degradation

- **No `gh` / not authenticated** → squash-merge detection falls back to
  `[gone]` + ancestor checks; the report says so. Branches squash-merged with
  their remote still present may land in ACTIVE instead of SAFE. Note this to
  the user.
- **No remote** → fetch and `gh` are skipped; only local-merged and stale
  detection run.
- **Dirty, ignored-content, locked, detached, unavailable, main, or
  submodule-containing worktree** → the worktree is reported as protected and
  neither it nor its branch is touched.
- **No repository at the current directory** → immediate child worktrees are
  grouped by Git common directory. If none exist, the script exits without
  acting.
- **Base-remote fetch fails** (offline, or auth error on the remote that backs
  the tiers) → the run continues on local refs and the summary prints `⚠ fetch
failed — gone/stale tiers computed from possibly-stale local refs`. Failures
  of _other_ remotes (e.g. a dead fork) are ignored and never trip that warning.
- The script is idempotent: re-running after an apply is safe and shows the new
  state.

## Verification

The dry run is the review gate. Always run it before `--apply`. After applying,
re-run with no flags; the tiers you acted on should be empty and
protected/active branches and worktrees unchanged. `git branch -vv` and `git
worktree list --porcelain` independently confirm deletions. In container mode,
verify each repository header from the original report; a repository with no
remaining child worktree no longer appears in a later container scan, so run
verification from its recorded Git common directory.

[1]: scripts/clean-git-repo.sh
