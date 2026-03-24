#!/bin/bash
#
# reviewers - Find PR reviewers using chunk-level git blame
#
# Usage: reviewers [-n limit] [branch=HEAD] [base=main]

set -euo pipefail

# --- Scoring weights ---
OWNERSHIP_WEIGHT=0.6     # Code ownership (how many lines you wrote)
RECENCY_WEIGHT=0.4       # How recently you touched those lines

# --- Scoring parameters ---
HALF_LIFE_DAYS=30        # Recency/expert decay half-life
LOG_BASE=100             # Ownership scale: 100 lines = score of 100
LN2=0.693147             # ln(2) for exponential decay
SECS_PER_DAY=86400
MAX_RESULTS=10           # Maximum reviewers to show
RECENCY_FLOOR=15         # Minimum recency score (historical experts)
OWNERSHIP_CAP=100        # Maximum ownership score

# Calculate terminal display width for unicode strings
# Wide chars (CJK, emoji) take 2 columns; returns total column count
display_width() {
  local str="$1"
  local chars wide
  chars=$(printf '%s' "$str" | perl -CSD -ne 'print length' 2>/dev/null) || chars=${#str}
  wide=$(printf '%s' "$str" | perl -CSD -ne 'print scalar(() = /[\x{1100}-\x{11FF}\x{2E80}-\x{9FFF}\x{F900}-\x{FAFF}\x{FE30}-\x{FE4F}\x{2600}-\x{27BF}\x{1F000}-\x{1FFFF}]/g)' 2>/dev/null) || wide=0
  echo $((chars + wide))
}

# --- Arguments ---
while getopts "n:" opt; do
  case $opt in
    n) MAX_RESULTS="$OPTARG" ;;
    *) echo "Usage: $0 [-n limit] [branch] [base]" >&2; exit 1 ;;
  esac
done
shift $((OPTIND - 1))

BRANCH="${1:-HEAD}"
BASE="${2:-main}"

# Run from repo root (diff paths are repo-relative)
cd "$(git rev-parse --show-toplevel)"

# Validate there are changes
git diff "$BASE"..."$BRANCH" --quiet 2>/dev/null && {
  echo "No changes between $BASE and $BRANCH"
  exit 0
}

file_count=$(git diff "$BASE"..."$BRANCH" --name-only | wc -l | tr -d ' ')
now=$(date +%s)

tmpfile=$(mktemp)
trap "rm -f $tmpfile" EXIT

# Parse diff hunks and blame each one
current_file=""
git diff "$BASE"..."$BRANCH" --unified=0 2>/dev/null | while IFS= read -r line; do
  # File header: diff --git a/path b/path
  if [[ "$line" == diff\ --git\ a/* ]]; then
    current_file="${line#diff --git a/}"
    current_file="${current_file%% b/*}"
    continue
  fi

  # Hunk header: @@ -start,count +start,count @@
  if [[ "$line" == @@* ]]; then
    hunk="${line#@@ -}"
    hunk="${hunk%% +*}"
    start="${hunk%%,*}"
    count="${hunk#*,}"
    [[ "$count" == "$start" ]] && count=1

    [[ "$count" -eq 0 || -z "$current_file" ]] && continue

    end=$((start + count - 1))

    git blame -L "$start,$end" --line-porcelain "$current_file" "$BASE" 2>/dev/null | \
      awk -v file="$current_file" '/^author / { a=substr($0,8) } /^author-time / { t=$2 } /^\t/ { if(a && t) print a"|"t"|"file }' \
      >> "$tmpfile" || true
  fi
done

[[ ! -s "$tmpfile" ]] && { echo "No blame data found"; exit 0; }

# Output
echo ""
echo "Suggested reviewers for: $BRANCH vs $BASE"
echo "Files: $file_count | Lines: $(wc -l < "$tmpfile" | tr -d ' ')"
echo ""
printf "%-25s | %5s | %5s | %7s | %5s | %5s | %4s\n" "Author" "Score" "Own" "Recency" "Lines" "Files" "Days"
printf "%-25s-|-%5s-|-%5s-|-%7s-|-%5s-|-%5s-|-%4s\n" "-------------------------" "-----" "-----" "-------" "-----" "-----" "----"

awk -F'|' -v now="$now" \
    -v half_life="$HALF_LIFE_DAYS" \
    -v own_w="$OWNERSHIP_WEIGHT" \
    -v rec_w="$RECENCY_WEIGHT" \
    -v log_base="$LOG_BASE" \
    -v ln2="$LN2" \
    -v spd="$SECS_PER_DAY" \
    -v rec_floor="$RECENCY_FLOOR" \
    -v own_cap="$OWNERSHIP_CAP" '
{
  lines[$1]++
  # POSIX-compatible multi-key: author SUBSEP filename
  author_file[$1, $3] = 1
  if ($2 > last[$1]) last[$1] = $2
}
END {
  for (a in lines) {
    # Count unique files for this author (POSIX workaround)
    nfiles = 0
    for (key in author_file) {
      split(key, parts, SUBSEP)
      if (parts[1] == a) nfiles++
    }

    days = int((now - last[a]) / spd)
    if (days < 0) days = 0

    # Recency with floor
    recency = int(100 * exp(-days * ln2 / half_life))
    if (recency < rec_floor) recency = rec_floor

    # Ownership with cap and expert decay
    raw_own = 100 * log(lines[a] + 1) / log(log_base)
    decay = exp(-days * ln2 / (half_life * 4))  # Slower decay for expertise
    ownership = int(raw_own * decay)
    if (ownership > own_cap) ownership = own_cap

    score = int(ownership * own_w + recency * rec_w)
    printf "%s|%d|%d|%d|%d|%d|%d\n", a, score, ownership, recency, lines[a], nfiles, days
  }
}' "$tmpfile" | sort -t'|' -k2 -rn | head -n "$MAX_RESULTS" | while IFS='|' read -r author score ownership recency lines files days; do
  padding=$((25 - $(display_width "$author")))
  [[ $padding -lt 0 ]] && padding=0
  printf "%s%*s | %5d | %5d | %7d | %5d | %5d | %4d\n" "$author" "$padding" "" "$score" "$ownership" "$recency" "$lines" "$files" "$days"
done
