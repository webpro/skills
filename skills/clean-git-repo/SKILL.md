---
name: clean-git-repo
description: >-
  Clean up a git repository: delete branches whose PRs merged (incl.
  squash-merges), list or delete local branches past a confirmed age threshold,
  prune stale remote-tracking refs and worktrees, and optionally prune local tags
  absent from the remote, run gc, or delete merged remote branches. Use when
  asked to clean up / prune / tidy git branches, remove merged or stale branches,
  delete old branches, prune origin/* refs, or clear out a repo's branch list.
  Reports first (dry run); never touches the current, default, protected, or
  worktree-checked-out branches.
---

# Clean Git Repo

Report and clean up local branches, stale remote-tracking refs, worktrees, and tags
in the **repository at the current working directory**. A bundled script does the
deterministic detection and deletion; you orchestrate the safety gates.

Resolve [scripts/clean-git-repo.sh](scripts/clean-git-repo.sh) to an absolute path once
and run it from inside the target repo — it operates on the repo in the current directory,
not the skill directory. In Claude Code: `SCRIPT="${CLAUDE_SKILL_DIR}/scripts/clean-git-repo.sh"`.

```bash
"$SCRIPT"           # report only (dry run)
"$SCRIPT" --apply   # delete the SAFE tier
```

The script's `--help` lists every flag; the key ones appear below.

## Safety model: confirm unless the action is safe

| Tier        | Actions                                                                                          | Confirmation        |
| ----------- | ------------------------------------------------------------------------------------------------ | ------------------- |
| **Safe**    | `git fetch --prune` (remote-tracking refs), `git worktree prune`, delete **merged** branches (tip provably in the merge) | none (apply + report) |
| **Confirm** | delete **MERGED-but-advanced** (`--force-merged`), **GONE** (`--force-gone`), **STALE** (`--stale`), matching **remote** branches whose remote tip is identical or provably merged (`--remote`), local tags absent from the remote (`--prune-tags`), `git gc` (`--gc`) | ask the user first  |
| **Never**   | the current branch, the default branch, branches checked out in a worktree, `--keep` matches      | excluded by the script |

A branch is **merged** when GitHub (`gh`) reports its PR merged, or its tip is an
ancestor of the base, so squash- and rebase-merges are caught, not just fast-forwards.
A squash-merged branch auto-deletes only when its tip is contained in the merged PR head;
if the local tip advanced past it (extra commits that never reached the PR, or a merged head
not fetched locally), it drops to the **`--force-merged`** confirm tier instead of being
force-deleted.

## Workflow

Copy this checklist and work through it:

- [ ] 1. Confirm the current directory is the repo to clean (`git rev-parse --show-toplevel`).
- [ ] 2. Run the script with **no flags** to fetch+prune refs and print the categorized plan.
- [ ] 3. Relay the plan: counts per tier, and the SAFE list verbatim.
- [ ] 4. Apply the **SAFE** tier (`--apply`). No confirmation needed; report what was deleted.
- [ ] 5. For each non-empty CONFIRM tier, ask the user which to include, then re-run
       `--apply` with the matching opt-in flags (e.g. `--apply --force-gone --stale`). To act on
       only a **subset** of a tier, delete those branches by name (`git branch -D <names>`)
       rather than passing the whole-tier flag.
- [ ] 6. Verify: re-run with no flags and confirm the targeted tiers are now empty.

### Step 2: report

```bash
"$SCRIPT"                 # default 90-day stale threshold
"$SCRIPT" --age-days 180  # adjust the threshold the user confirms
```

Read the output. It groups branches as **SAFE TO DELETE — merged**,
**CONFIRM — merged, local tip advanced**, **CONFIRM — gone upstream**,
**CONFIRM — stale > Nd**, **CONFIRM — matching remote branches**, **REMOTE SKIP**,
**CONFIRM — local tags absent from <remote>**, **PROTECTED**, and a kept **ACTIVE** count. `[gone]` upstream alone is *not* proof of a merge: it can also be a
closed-unmerged PR. GONE is therefore always a confirm tier; each gone entry shows how many
commits it holds ahead of the base, so you can see what a delete would discard. Each stale
entry carries its push-state (`never pushed — local only`,
`ahead N — unpushed work`, or `in sync with <upstream>`), so you can see at a glance
whether deleting it discards work that exists nowhere else. With `--remote`, review both
remote sections: remote branches delete only when the remote-tracking tip is identical to
the local branch being deleted or independently proven merged; otherwise they are reported
as skipped.

### Step 4 & 5: apply

```bash
"$SCRIPT" --apply                          # SAFE only (merged branches)
"$SCRIPT" --apply --force-merged           # + delete merged branches whose tip advanced past the PR
"$SCRIPT" --apply --force-gone             # + delete GONE branches
"$SCRIPT" --apply --stale --age-days 180   # + delete STALE branches
"$SCRIPT" --apply --remote                 # + delete matching remote branches after lease check
"$SCRIPT" --apply --prune-tags --gc        # + prune listed local tags absent from the remote, reclaim space
```

Other flags: `--base <branch>` to override default-branch detection, `--keep '<glob>'`
to protect extra branches (repeatable), `--no-fetch` for offline, `--no-gh` to skip
GitHub lookups.

## Graceful degradation

- **No `gh` / not authenticated** → squash-merge detection falls back to `[gone]` +
  ancestor checks; the report says so. Branches squash-merged with their remote still
  present may land in ACTIVE instead of SAFE. Note this to the user.
- **No remote** → fetch and `gh` are skipped; only local-merged and stale detection run.
- **Base-remote fetch fails** (offline, or auth error on the remote that backs the tiers) →
  the run continues on local refs and the summary prints `⚠ fetch failed — gone/stale tiers
  computed from possibly-stale local refs`. Failures of *other* remotes (e.g. a dead fork)
  are ignored and never trip that warning.
- The script is idempotent: re-running after an apply is safe and shows the new state.

## Verification

The dry run is the review gate. Always run it before `--apply`. After applying, re-run
with no flags; the tiers you acted on should be empty and the protected/active branches
unchanged. `git branch -vv` independently confirms deletions.
