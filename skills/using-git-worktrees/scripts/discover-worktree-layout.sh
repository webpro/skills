#!/usr/bin/env bash

set -uo pipefail

PROG=${0##*/}

usage() {
  printf 'Usage: %s [directory]\n' "$PROG"
}

die() {
  printf '%s: %s\n' "$PROG" "$*" >&2
  exit 1
}

# A bare repository cannot hold a checkout, so its parent is the container that
# holds the sibling checkouts. Prints nothing for a repository with a work tree.
container_for() {
  [ "$(git --git-dir="$1" rev-parse --is-bare-repository 2>/dev/null)" = true ] || return 0
  (cd "${1%/*}" 2>/dev/null && pwd -P)
}

# The shared .agents root is the nearest ancestor of the starting point that
# already has one. Stops below $HOME so a personal ~/.agents is never adopted.
resolve_workspace() {
  local directory=$1 parent
  while [ -z "${HOME:-}" ] || [ "$directory" != "$HOME" ]; do
    if [ -d "$directory/.agents" ]; then
      printf '%s\n' "$directory"
      return 0
    fi
    parent=${directory%/*}
    [ -n "$parent" ] || parent=/
    [ "$parent" != "$directory" ] || break
    directory=$parent
  done
  printf '%s\n' "$1"
}

case $# in
  0) target_directory=. ;;
  1)
    case "$1" in
      -h|--help) usage; exit 0 ;;
      *) target_directory=$1 ;;
    esac
    ;;
  *) usage >&2; exit 2 ;;
esac

workspace_root=$(cd "$target_directory" 2>/dev/null && pwd -P) ||
  die "cannot access directory: $target_directory"

inside=$(git -C "$workspace_root" rev-parse --is-inside-work-tree 2>/dev/null || true)
if [ "$inside" = true ]; then
  worktree=$(git -C "$workspace_root" rev-parse --show-toplevel 2>/dev/null) ||
    die "cannot resolve worktree: $workspace_root"
  worktree=$(cd "$worktree" 2>/dev/null && pwd -P) ||
    die "cannot access worktree: $worktree"
  repository=$(git -C "$workspace_root" rev-parse \
    --path-format=absolute --git-common-dir 2>/dev/null) ||
    die "cannot resolve Git common directory: $workspace_root"
  repository=$(cd "$repository" 2>/dev/null && pwd -P) ||
    die "cannot access Git common directory: $repository"

  container=$(container_for "$repository")
  workspace=$(resolve_workspace "${container:-$worktree}")

  printf 'layout=worktree\nworkspace=%s\nworktree=%s\nrepository=%s\n' \
    "$workspace" "$worktree" "$repository"
  [ -n "$container" ] && printf 'container=%s\n' "$container"
  exit 0
fi

discover_repositories() {
  for git_directory in \
    "$workspace_root"/.bare "$workspace_root"/.git \
    "$workspace_root"/*/.bare "$workspace_root"/*/.git \
    "$workspace_root"/.[!.]*/.bare "$workspace_root"/.[!.]*/.git; do
    [ -d "$git_directory" ] || continue
    (cd "$git_directory" && pwd -P)
  done |
    sort -u |
    while IFS= read -r git_directory; do
      repository=$(git --git-dir="$git_directory" rev-parse \
        --path-format=absolute --git-common-dir 2>/dev/null) || continue
      printf '%s\n' "$repository"
    done |
    sort -u
}

repositories=()
while IFS= read -r repository; do
  [ -n "$repository" ] || continue
  repositories[${#repositories[@]}]=$repository
done < <(discover_repositories)

repository_count=${#repositories[@]}
[ "$repository_count" -gt 0 ] ||
  die "no Git worktree or container found at: $workspace_root"

if [ "$repository_count" -eq 1 ]; then
  layout=single-container
else
  layout=mixed-container
fi

printf 'layout=%s\nworkspace=%s\n' "$layout" "$(resolve_workspace "$workspace_root")"
for repository in "${repositories[@]}"; do
  printf 'repository=%s\n' "$repository"
  container=$(container_for "$repository")
  [ -n "$container" ] && printf 'container=%s\n' "$container"
done
