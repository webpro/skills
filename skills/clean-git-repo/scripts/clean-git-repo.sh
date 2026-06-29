#!/usr/bin/env bash
#
# clean-git-repo.sh — report and clean up local git branches, stale
# remote-tracking refs, worktrees, and tags for the repo in the current directory.
#
# Dry-run by default: it fetches+prunes remote-tracking refs (safe, reversible) and
# prints a categorized plan, but deletes NO branches/tags/remotes without --apply.
#
# Usage:
#   clean-git-repo.sh [options]
#
#   --apply           Execute the plan (without it, report only). Auto-deletes only
#                     the safe tier: tip in base, or tip == the merged PR head.
#   --age-days N      Stale threshold for branches (default: 90).
#   --base BRANCH     Override default-branch detection (e.g. master).
#   --keep PATTERN    Glob of branch names to always protect (repeatable or comma-list).
#   --no-fetch        Skip 'git fetch --prune' (offline; [gone] detection may be stale).
#   --no-gh           Skip GitHub PR-state lookup even if gh is available.
#
#   Confirm-tier opt-ins (only act when passed; pair with --apply):
#   --force-gone      Also delete GONE branches (upstream gone, not confirmed merged).
#   --force-merged    Also delete MERGED branches whose local tip advanced past the
#                     merged PR head (extra commits gh can't vouch for).
#   --stale           Also delete STALE branches (older than --age-days, unmerged).
#   --remote          Also delete matching REMOTE branches whose tips are identical
#                     or provably merged; remote deletion is lease-checked.
#   --prune-tags      Also delete local tags absent from the selected remote.
#   --gc              Run 'git gc --prune=now' at the end to reclaim space.
#
# Exit codes: 0 ok, 1 usage/environment error.

set -uo pipefail

PROG=${0##*/}
APPLY=0
AGE_DAYS=90
BASE_OVERRIDE=""
KEEP_PATTERNS=""
DO_FETCH=1
USE_GH=1
FORCE_GONE=0
FORCE_MERGED=0
DO_STALE=0
DO_REMOTE=0
PRUNE_TAGS=0
DO_GC=0

die() { printf '%s: %s\n' "$PROG" "$*" >&2; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --apply) APPLY=1 ;;
    --age-days) shift; AGE_DAYS=${1:-90} ;;
    --base) shift; BASE_OVERRIDE=${1:-} ;;
    --keep) shift; KEEP_PATTERNS="$KEEP_PATTERNS ${1:-}"; KEEP_PATTERNS=${KEEP_PATTERNS//,/ } ;;
    --no-fetch) DO_FETCH=0 ;;
    --no-gh) USE_GH=0 ;;
    --force-gone) FORCE_GONE=1 ;;
    --force-merged) FORCE_MERGED=1 ;;
    --stale) DO_STALE=1 ;;
    --remote) DO_REMOTE=1 ;;
    --prune-tags) PRUNE_TAGS=1 ;;
    --gc) DO_GC=1 ;;
    -h|--help) grep '^#' "$0" | cut -c3-; exit 0 ;;
    *) die "unknown option: $1 (try --help)" ;;
  esac
  shift
done

case "$AGE_DAYS" in *[!0-9]*|'') die "--age-days must be an integer" ;; esac

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "not inside a git work tree"

# Field separator for for-each-ref: ASCII Unit Separator (0x1F). It is non-whitespace
# (so 'read' preserves empty fields) and forbidden in git ref names (so it never collides).
SEP=$(printf '\037')

# --- temp state (bash 3.2: no associative arrays) ---------------------------
TMP=$(mktemp -d "${TMPDIR:-/tmp}/clean-git-repo.XXXXXX") || die "mktemp failed"
trap 'rm -rf "$TMP"' EXIT
MERGED_HEADS="$TMP/merged_heads"   # gh: 'headRefName<TAB>headRefOid' per MERGED PR
DEL_SAFE="$TMP/del_safe"           # branch  (merged/in-base; containment proven -> -D)
DEL_GONE="$TMP/del_gone"           # branch             (GONE -> --force-gone)
DEL_STALE="$TMP/del_stale"         # branch             (STALE -> --stale)
DEL_AHEAD="$TMP/del_ahead"         # branch             (merged, tip advanced -> --force-merged)
DEL_SELECTED="$TMP/del_selected"
DEL_TAGS="$TMP/del_tags"
: >"$MERGED_HEADS"
: >"$DEL_SAFE"; : >"$DEL_GONE"; : >"$DEL_STALE"; : >"$DEL_AHEAD"; : >"$DEL_SELECTED"; : >"$DEL_TAGS"

# --- determine remote, base, current ----------------------------------------
REMOTE=$(git remote | grep -Fx origin || git remote | head -1)
HAS_REMOTE=0; [ -n "$REMOTE" ] && HAS_REMOTE=1

FETCH_FAILED=0
if [ "$DO_FETCH" = 1 ] && [ "$HAS_REMOTE" = 1 ]; then
  echo "→ updating remote-tracking refs from $REMOTE (+ other remotes, best-effort)"
  # Only the base remote's refs back the gone/stale/ancestor tiers, so only its fetch is
  # authoritative for the staleness warning. Extra remotes (e.g. a dead fork) stay best-effort
  # and never trip the warning — otherwise it would cry wolf on every run.
  git fetch --prune --quiet "$REMOTE" || { FETCH_FAILED=1; echo "  (fetch of $REMOTE failed; gone/stale computed from local state)"; }
  for r in $(git remote | grep -Fxv "$REMOTE"); do
    git fetch --prune --quiet "$r" 2>/dev/null || echo "  (fetch of $r failed; ignored — not used for the tiers)"
  done
fi

CURRENT=$(git symbolic-ref --quiet --short HEAD 2>/dev/null || true)  # empty if detached
BASE="$BASE_OVERRIDE"
if [ -z "$BASE" ] && [ "$HAS_REMOTE" = 1 ]; then
  BASE=$(git symbolic-ref --quiet --short "refs/remotes/$REMOTE/HEAD" 2>/dev/null | sed "s@^$REMOTE/@@")
fi
if [ -z "$BASE" ] && [ "$HAS_REMOTE" = 1 ]; then
  for c in main master; do
    git rev-parse --verify --quiet "refs/remotes/$REMOTE/$c" >/dev/null 2>&1 && BASE="$c" && break
  done
fi
if [ -z "$BASE" ]; then
  for c in main master; do
    git rev-parse --verify --quiet "refs/heads/$c" >/dev/null 2>&1 && BASE="$c" && break
  done
fi
[ -z "$BASE" ] && [ -n "$CURRENT" ] && BASE="$CURRENT"
[ -z "$BASE" ] && die "could not determine default branch (use --base)"

if [ "$HAS_REMOTE" = 1 ] && git rev-parse --verify --quiet "refs/remotes/$REMOTE/$BASE" >/dev/null 2>&1; then
  BASEREF="$REMOTE/$BASE"
else
  BASEREF="$BASE"
fi

# --- GitHub PR state (optional, one call each) ------------------------------
GH_OK=0
if [ "$USE_GH" = 1 ] && command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  if gh pr list --state merged --limit 1000 --json headRefName,headRefOid --jq '.[] | [.headRefName, .headRefOid] | @tsv' >"$MERGED_HEADS" 2>/dev/null; then
    GH_OK=1
  fi
fi

gh_state() { # echoes MERGED|"" for a branch name
  [ "$GH_OK" = 1 ] || return 0
  cut -f1 "$MERGED_HEADS" | grep -Fxq "$1" && echo MERGED
  return 0
}

# For a branch gh marked MERGED, relate its local tip to the recorded merged head OID(s).
# Echoes "safe" when the tip is contained in a merged head (== it or an ancestor, so
# force-delete discards nothing), else the fewest commits the tip sits PAST any merged
# head (work a force-delete would lose), or "?" when no merged head is available locally.
merged_oid_rel() { # branch oid
  local b="$1" tip="$2" name oid min="" c
  while IFS=$'\t' read -r name oid; do
    [ "$name" = "$b" ] && [ -n "$oid" ] || continue
    git merge-base --is-ancestor "$tip" "$oid" 2>/dev/null && { echo "safe"; return; }
    c=$(git rev-list --count "$oid..$tip" 2>/dev/null) || c=""
    if [ -n "$c" ] && { [ -z "$min" ] || [ "$c" -lt "$min" ]; }; then min="$c"; fi
  done <"$MERGED_HEADS"
  echo "${min:-?}"
}

merged_tip_rel() { # branch
  local b="$1" tip
  tip=$(git rev-parse --verify --quiet "refs/heads/$b") || { echo "?"; return; }
  merged_oid_rel "$b" "$tip"
}

matches_keep() {
  local b="$1" pat
  for pat in $KEEP_PATTERNS; do
    # shellcheck disable=SC2254  # $pat is a user-supplied glob, matched intentionally
    case "$b" in $pat) return 0 ;; esac
  done
  return 1
}

# Human push-state for a branch, so confirm tiers reveal whether deleting loses work.
push_state() { # track-string upstream-short
  local track="$1" up="$2" n
  [ -z "$up" ] && { echo "never pushed — local only"; return; }
  case "$track" in
    *ahead*) n=${track#*ahead }; n=${n%%[!0-9]*}; echo "ahead $n — unpushed work" ;;
    *behind*) echo "pushed, local behind" ;;
    *) echo "in sync with $up" ;;
  esac
}

NOW=$(date +%s)
STALE_CUTOFF=$((NOW - AGE_DAYS * 86400))

# --- classify every local branch --------------------------------------------
n_prot=0; n_merged=0; n_gone=0; n_stale=0; n_active=0; n_ahead=0
report_active="$TMP/active"; : >"$report_active"
report_prot="$TMP/prot"; : >"$report_prot"
report_merged="$TMP/r_merged"; : >"$report_merged"
report_ahead="$TMP/r_ahead"; : >"$report_ahead"
report_gone="$TMP/r_gone"; : >"$report_gone"
report_stale="$TMP/r_stale"; : >"$report_stale"
report_remote="$TMP/r_remote"; : >"$report_remote"
report_remote_skip="$TMP/r_remote_skip"; : >"$report_remote_skip"
report_tags="$TMP/r_tags"; : >"$report_tags"

while IFS="$SEP" read -r br track up wt cdate; do
  [ -z "$br" ] && continue

  if [ "$br" = "$BASE" ] || [ "$br" = "$CURRENT" ] || [ -n "$wt" ] || matches_keep "$br"; then
    if [ "$br" = "$BASE" ]; then reason="default branch"
    elif [ "$br" = "$CURRENT" ]; then reason="current branch"
    elif [ -n "$wt" ]; then reason="checked out in worktree ${wt##*/}"
    elif matches_keep "$br"; then reason="--keep match"
    else reason="protected"; fi
    printf '  %-45s %s\n' "$br" "$reason" >>"$report_prot"
    n_prot=$((n_prot + 1)); continue
  fi

  state=$(gh_state "$br")

  if [ "$state" = MERGED ]; then
    if git merge-base --is-ancestor "$br" "$BASEREF" 2>/dev/null; then
      printf '%s\n' "$br" >>"$DEL_SAFE"
      printf '  %-45s PR merged\n' "$br" >>"$report_merged"
      n_merged=$((n_merged + 1)); continue
    fi
    rel=$(merged_tip_rel "$br")
    if [ "$rel" = safe ]; then
      printf '%s\n' "$br" >>"$DEL_SAFE"
      printf '  %-45s PR merged (squashed; tip in merged head)\n' "$br" >>"$report_merged"
      n_merged=$((n_merged + 1)); continue
    fi
    # gh says merged, but the tip is not provably contained in the merged head — force-delete
    # could discard local commits, so demote out of SAFE into a confirm tier.
    case "$rel" in
      '?') detail="merged head not fetched, can't verify it's contained" ;;
      1)   detail="tip is 1 commit past the merged head" ;;
      *)   detail="tip is $rel commits past the merged head" ;;
    esac
    echo "$br" >>"$DEL_AHEAD"
    printf '  %-45s PR merged, but %s; %s\n' "$br" "$detail" "$(push_state "$track" "$up")" >>"$report_ahead"
    n_ahead=$((n_ahead + 1)); continue
  fi

  if git merge-base --is-ancestor "$br" "$BASEREF" 2>/dev/null; then
    printf '%s\n' "$br" >>"$DEL_SAFE"
    printf '  %-45s merged into %s\n' "$br" "$BASEREF" >>"$report_merged"
    n_merged=$((n_merged + 1)); continue
  fi

  if [ "$track" = "[gone]" ]; then
    echo "$br" >>"$DEL_GONE"
    ahead=$(git rev-list --count "$BASEREF..$br" 2>/dev/null || echo 0)
    printf '  %-45s upstream gone; %s commit(s) ahead of %s\n' "$br" "${ahead:-0}" "$BASE" >>"$report_gone"
    n_gone=$((n_gone + 1)); continue
  fi

  if [ -n "$cdate" ] && [ "$cdate" -lt "$STALE_CUTOFF" ]; then
    age_days=$(( (NOW - cdate) / 86400 ))
    echo "$br" >>"$DEL_STALE"
    printf '  %-45s last commit %sd ago; %s\n' "$br" "$age_days" "$(push_state "$track" "$up")" >>"$report_stale"
    n_stale=$((n_stale + 1)); continue
  fi

  printf '  %-45s active\n' "$br" >>"$report_active"
  n_active=$((n_active + 1))
done < <(git for-each-ref refs/heads \
  --format="%(refname:short)${SEP}%(upstream:track)${SEP}%(upstream:short)${SEP}%(worktreepath)${SEP}%(committerdate:unix)")

cat "$DEL_SAFE" >"$DEL_SELECTED"
[ "$FORCE_MERGED" = 1 ] && cat "$DEL_AHEAD" >>"$DEL_SELECTED"
[ "$FORCE_GONE" = 1 ] && cat "$DEL_GONE" >>"$DEL_SELECTED"
[ "$DO_STALE" = 1 ] && cat "$DEL_STALE" >>"$DEL_SELECTED"

short_oid() {
  git rev-parse --short "$1" 2>/dev/null || printf '%s' "$1"
}

remote_delete_reason() { # branch local-oid
  local b="$1" local_oid="$2" remote_oid rel
  remote_oid=$(git rev-parse --verify --quiet "refs/remotes/$REMOTE/$b") || { echo "no $REMOTE/$b tracking ref"; return 1; }
  if [ -n "$local_oid" ] && [ "$remote_oid" = "$local_oid" ]; then
    echo "same tip as local branch ($(short_oid "$remote_oid"))"; return 0
  fi
  if git merge-base --is-ancestor "$remote_oid" "$BASEREF" 2>/dev/null; then
    echo "remote tip merged into $BASEREF ($(short_oid "$remote_oid"))"; return 0
  fi
  rel=$(merged_oid_rel "$b" "$remote_oid")
  if [ "$rel" = safe ]; then
    echo "PR merged (remote tip in merged head, $(short_oid "$remote_oid"))"; return 0
  fi
  echo "remote tip differs from local and is not provably merged ($(short_oid "$remote_oid"))"
  return 1
}

if [ "$DO_REMOTE" = 1 ] && [ "$HAS_REMOTE" = 1 ]; then
  while IFS= read -r b; do
    [ -n "$b" ] || continue
    local_oid=$(git rev-parse --verify --quiet "refs/heads/$b" 2>/dev/null || true)
    if detail=$(remote_delete_reason "$b" "$local_oid"); then
      printf '  %-45s will delete; %s\n' "$REMOTE/$b" "$detail" >>"$report_remote"
    elif [ "$detail" != "no $REMOTE/$b tracking ref" ]; then
      printf '  %-45s skip; %s\n' "$REMOTE/$b" "$detail" >>"$report_remote_skip"
    fi
  done <"$DEL_SELECTED"
fi

TAG_PRUNE_STATE=off
TAG_PRUNE_REASON=""
if [ "$PRUNE_TAGS" = 1 ]; then
  TAG_PRUNE_STATE=ready
  if [ "$HAS_REMOTE" != 1 ]; then
    TAG_PRUNE_STATE=blocked
    TAG_PRUNE_REASON="no remote configured"
  else
    remote_tags="$TMP/remote_tags"; : >"$remote_tags"
    if git ls-remote --tags --refs "$REMOTE" 2>/dev/null | awk '{ sub("^refs/tags/", "", $2); print $2 }' >"$remote_tags"; then
      while IFS= read -r t; do
        [ -n "$t" ] || continue
        if ! grep -Fxq "$t" "$remote_tags"; then
          printf '%s\n' "$t" >>"$DEL_TAGS"
          printf '  %-45s absent from %s\n' "$t" "$REMOTE" >>"$report_tags"
        fi
      done < <(git for-each-ref refs/tags --format='%(refname:strip=2)')
    else
      TAG_PRUNE_STATE=blocked
      TAG_PRUNE_REASON="could not list tags from $REMOTE"
    fi
  fi
fi

# --- report -----------------------------------------------------------------
echo
echo "Repo: $(git rev-parse --show-toplevel)"
echo "Default branch: $BASE (base ref: $BASEREF)   Current: ${CURRENT:-<detached>}"
if [ "$GH_OK" = 1 ]; then echo "GitHub: $(grep -c . "$MERGED_HEADS") merged PRs known via gh"
else echo "GitHub: gh unavailable — squash-merge detection limited to [gone] + ancestor checks"; fi
[ "$FETCH_FAILED" = 1 ] && echo "⚠ fetch failed — gone/stale tiers computed from possibly-stale local refs (re-run with network, or --no-fetch to silence)"
echo

show() { # title file
  local n; n=$(grep -c . "$2" 2>/dev/null) || true
  [ "${n:-0}" -eq 0 ] && return 0
  echo "$1 ($n):"; cat "$2"; echo
}
show "SAFE TO DELETE — merged"           "$report_merged"
show "CONFIRM — merged, local tip advanced (--force-merged)" "$report_ahead"
show "CONFIRM — gone upstream (--force-gone)" "$report_gone"
show "CONFIRM — stale > ${AGE_DAYS}d (--stale)"   "$report_stale"
show "CONFIRM — matching remote branches (--remote)" "$report_remote"
show "REMOTE SKIP — not provably safe to delete" "$report_remote_skip"
show "CONFIRM — local tags absent from $REMOTE (--prune-tags)" "$report_tags"
if [ "$PRUNE_TAGS" = 1 ] && [ "$TAG_PRUNE_STATE" = blocked ]; then
  echo "CONFIRM — local tags absent from ${REMOTE:-remote} (--prune-tags): skipped ($TAG_PRUNE_REASON)"
  echo
fi
show "PROTECTED — never touched"          "$report_prot"
echo "ACTIVE (kept): $n_active branch(es)"
echo

# --- apply ------------------------------------------------------------------
if [ "$APPLY" != 1 ]; then
  echo "Dry run. Re-run with --apply to delete the SAFE tier; add --force-merged/--force-gone/--stale/--remote/--prune-tags/--gc to opt into the rest."
  exit 0
fi

deleted_remote=0
del_branch() { # branch (force -D; SAFE-tier containment already proven, confirm tiers are opt-in)
  local b="$1" local_oid detail remote_oid
  local_oid=$(git rev-parse --verify --quiet "refs/heads/$b" 2>/dev/null || true)
  if git branch -D "$b" >/dev/null 2>&1; then
    echo "  deleted $b"
    if [ "$DO_REMOTE" = 1 ] && [ "$HAS_REMOTE" = 1 ] && detail=$(remote_delete_reason "$b" "$local_oid"); then
      remote_oid=$(git rev-parse --verify --quiet "refs/remotes/$REMOTE/$b" 2>/dev/null || true)
      if [ -n "$remote_oid" ] && git push --force-with-lease="refs/heads/$b:$remote_oid" "$REMOTE" ":refs/heads/$b" >/dev/null 2>&1; then
        echo "    deleted remote $REMOTE/$b"; deleted_remote=$((deleted_remote + 1))
      else
        echo "    SKIP remote $REMOTE/$b (lease failed)"
      fi
    elif [ "$DO_REMOTE" = 1 ] && [ "$HAS_REMOTE" = 1 ] && [ -n "${detail:-}" ] && [ "$detail" != "no $REMOTE/$b tracking ref" ]; then
      echo "    SKIP remote $REMOTE/$b ($detail)"
    fi
  else
    echo "  SKIP $b (git refused)"
  fi
}

echo "Applying:"
while IFS= read -r b; do [ -n "$b" ] && del_branch "$b"; done <"$DEL_SAFE"

if [ "$FORCE_MERGED" = 1 ]; then
  while IFS= read -r b; do [ -n "$b" ] && del_branch "$b"; done <"$DEL_AHEAD"
elif [ "$n_ahead" -gt 0 ]; then echo "  (kept $n_ahead merged-but-advanced branch(es); pass --force-merged to delete)"; fi

if [ "$FORCE_GONE" = 1 ]; then
  while IFS= read -r b; do [ -n "$b" ] && del_branch "$b"; done <"$DEL_GONE"
elif [ "$n_gone" -gt 0 ]; then echo "  (kept $n_gone gone branch(es); pass --force-gone to delete)"; fi

if [ "$DO_STALE" = 1 ]; then
  while IFS= read -r b; do [ -n "$b" ] && del_branch "$b"; done <"$DEL_STALE"
elif [ "$n_stale" -gt 0 ]; then echo "  (kept $n_stale stale branch(es); pass --stale to delete)"; fi

if [ "$PRUNE_TAGS" = 1 ]; then
  if [ "$TAG_PRUNE_STATE" = blocked ]; then
    echo "  skipped tag prune ($TAG_PRUNE_REASON)"
  elif ! grep -q . "$DEL_TAGS"; then
    echo "  no local tags absent from $REMOTE"
  else
    while IFS= read -r t; do
      [ -n "$t" ] || continue
      if git tag -d "$t" >/dev/null 2>&1; then
        echo "  deleted tag $t"
      else
        echo "  SKIP tag $t (git refused)"
      fi
    done <"$DEL_TAGS"
  fi
fi

WT_PRUNED=$(git worktree prune -v 2>&1 || true)
[ -n "$WT_PRUNED" ] && echo "  worktree prune: $WT_PRUNED"

if [ "$DO_GC" = 1 ]; then echo "  git gc --prune=now..."; git gc --prune=now --quiet && echo "  gc done"; fi

echo
echo "Done. Remote branches deleted: $deleted_remote. Re-run without --apply to verify the plan is empty."
