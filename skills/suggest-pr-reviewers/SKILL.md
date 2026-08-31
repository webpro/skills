---
name: suggest-pr-reviewers
description: >-
  Ranks candidate reviewers for a change by who actually wrote the lines it
  touches, combining code ownership with recency from chunk-level git blame. Use
  whenever a reviewer has to be chosen: "who should review this", "who knows this
  code best", "who has the most context on these files", "find me a reviewer",
  "add reviewers", "who should I request review from", or when opening a pull
  request and deciding whom to assign.
---

# Suggest PR Reviewers

Find the most relevant reviewers for a pull request based on who has contributed to the changed files, using a weighted score that combines code ownership and recency.

## Usage

```
reviewers [-n limit] [branch] [base]
```

- `-n limit`: Maximum reviewers to show (default: 10)
- `branch`: Branch to analyze (default: HEAD)
- `base`: Base branch to diff against (default: `main`)

## Quick Start

Resolve [scripts/reviewers.sh][1] to an absolute path once and run it from the
repository under review. In Claude Code:
`SCRIPT="${CLAUDE_SKILL_DIR}/scripts/reviewers.sh"`. A skill directory installed
globally is not reachable by a relative path from the repository you are in.

```bash
"$SCRIPT"                               # current branch vs main, top 10
"$SCRIPT" -n 5 feature-branch main      # pick branches and limit
```

The script resolves the repository root itself, so any directory inside the
target repository works.

## Metrics Explained

Uses **chunk-level git blame** to identify who wrote the specific lines being modified, not just who committed to the file.

| Metric      | Description                                         | Formula                                 |
| ----------- | --------------------------------------------------- | --------------------------------------- |
| **Score**   | Combined score (60% ownership, 40% recency)         | `ownership × 0.6 + recency × 0.4`       |
| **Own**     | Log-scaled authorship with expert decay, capped     | `min(100, 100 × log(lines+1)/log(100) × decay)`          |
| **Recency** | Score 15-100, higher = more recent                  | `max(15, 100 × e^(-days × 0.693 / 30))` |
| **Lines**   | Lines of code being modified that this author wrote | Raw count from `git blame`              |
| **Files**   | Number of changed files this author touched         | Unique file count                       |
| **Days**    | Days since author last touched these lines          | `(now - last_blame_timestamp) / 86400`  |

### Scoring Features

- **Recency floor (15)**: Historical experts don't drop to 0
- **Ownership cap (100)**: Prevents prolific authors from dominating
- **Expert decay**: Ownership decays at 4× slower rate than recency (120-day half-life)

## Task Instructions

When this skill is invoked:

1. **Determine branches**
   - If branch specified in args, use it; otherwise use current branch
   - If base specified, use it; otherwise use `main`

2. **Run the reviewers script**

   ```bash
   "$SCRIPT" [-n limit] [branch] [base]
   ```

3. **Present results**
   - Show the full table of reviewers sorted by score
   - Note: The current git user can be found with `git config user.name`

4. **Provide recommendations**
   - Recommend 2-3 reviewers based on scores
   - If scores are close, mention both as equally qualified
   - If a reviewer has high recency but low ownership, note they have recent context
   - If a reviewer has high ownership but low recency, note they have deep knowledge

## Example Output

```
Suggested reviewers for: feature-branch vs main
Files: 44 | Lines: 705

Author                    | Score |   Own | Recency | Lines | Files | Days
--------------------------|-------|-------|---------|-------|-------|-----
John                      |    99 |   100 |      97 |   210 |    15 |    1
Maria                     |    77 |    82 |      70 |    85 |     8 |   12
Steve                     |    66 |   100 |      15 |   205 |    20 |  180
Rose                      |    58 |    75 |      32 |    50 |     5 |   45
```

## Algorithm Details

### Recency Score (Exponential Decay with Floor)

Uses a 30-day half-life with a minimum floor of 15:

- 0 days ago = 100
- 30 days ago = 50
- 60 days ago = 25
- 90+ days ago = 15 (floor)

```
recency = max(15, 100 × e^(-days × ln(2) / 30))
```

### Ownership Score (Logarithmic Scale with Decay and Cap)

Based on lines of code authored (from git blame), with:

- Logarithmic scaling (diminishing returns)
- Expert decay (120-day half-life, 4× slower than recency)
- Cap at 100

```
raw = 100 × log(lines + 1) / log(100)
decay = e^(-days × ln(2) / 120)
ownership = min(100, raw × decay)
```

### Score (Weighted Combination)

```
score = ownership × 0.6 + recency × 0.4
```

The 60/40 weighting slightly favors code owners over recent-but-minor contributors.

## Notes

- Uses **chunk-level git blame** on the exact lines being modified (not file-level)
- Pure additions (new files/lines) have no blame data and don't contribute to scores
- Ownership capped at 100; recency floored at 15 to keep historical experts visible
- Current user (from `git config user.name`) should typically be excluded from recommendations
- Works best with repositories that have >3 months of history

[1]: scripts/reviewers.sh
