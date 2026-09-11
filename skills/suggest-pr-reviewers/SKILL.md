---
name: suggest-pr-reviewers
description: >-
  Ranks reviewers for a change by who reviewed and authored earlier pull
  requests touching the same files and their sibling files, resolved to GitHub
  logins with the change author and bots excluded. Use whenever a reviewer has
  to be chosen: "who should review this", "who knows this code best", "find me
  a reviewer", "add reviewers", "who should I request review from", or when
  opening a pull request and deciding whom to assign.
---

# Suggest PR Reviewers

Rank reviewers from who reviewed earlier pull requests on the same paths. Do not fall back to `git blame` of the changed lines: people mostly edit their own code, so blame largely returns the change author, who cannot review their own work.

## Usage

```text
reviewers [-n LIMIT] [--since DAYS] [--exclude LOGIN] [--no-github] [branch] [base]
```

- `-n LIMIT`: maximum reviewers to show (default: 5)
- `--since DAYS`: history window (default: 365)
- `--exclude LOGIN`: leave someone out; repeatable
- `--no-github`: commit authorship only, no `gh` calls
- `branch`: branch to analyze (default: `HEAD`)
- `base`: branch to diff against (default: the pull request base if the branch has one, else `main`, `master`, or the remote HEAD; the remote-tracking ref such as `origin/main` wins over a local branch, which falls behind in worktrees nobody pulls)

Resolve [scripts/reviewers][1] to an absolute path once and run it from inside the repository under review. In Claude Code: `SCRIPT="${CLAUDE_SKILL_DIR}/scripts/reviewers"`. A globally installed skill directory is not reachable by a relative path from the repository you are in.

```bash
"$SCRIPT"                        # current branch, top 5
"$SCRIPT" -n 3 feature-branch    # pick the branch and limit
"$SCRIPT" --exclude alice        # alice is away
```

Requires `git` and Python 3. With `gh` authenticated, the ranking includes review history; without it, the script says so and ranks by commit authorship.

## Workflow

1. Run the script from the repository under review. It diffs the branch against the merge base, excludes lockfiles, and reads the history of the changed files and their directories on the base branch. With nothing committed yet it ranks the working tree instead, and says so.
2. Read the header. It names who was excluded and why, how much of the path history carried review data, whether a pull request already exists for the branch and who has reviewed or been requested, and whether GitHub data was available.
3. Recommend up to three reviewers from the table. Prefer `files` matches over `dirs`; treat `repo` rows as a last resort, since they carry no evidence about these paths. Explain each pick from the columns: how many pull requests on these paths the person reviewed or authored and how recently.
4. Drop anyone known to be unavailable and rerun with `--exclude` if that empties the list. Do not infer availability from history.
5. If the header reports no GitHub data, say so: authorship alone is a weaker signal, and names may be git author names rather than GitHub logins.

## Ranking

| Column   | Meaning |
| -------- | ------- |
| Score    | Review evidence plus a quarter of authoring evidence, relative to the top candidate |
| Reviewed | Pull requests on these paths the person approved or requested changes on |
| Authored | Pull requests (or commits) on these paths the person wrote |
| Last     | Days since the person's most recent activity on these paths |
| Match    | `files`: touched the same files; `dirs`: sibling files only; `repo`: repository-wide recent reviews |

With GitHub data the ranking reads the fifty most path-relevant pull requests. Each contributes the share of the changed files it touched, or a quarter of the share it sits beside, halved every 90 days. Reviews count when the reviewer approved or requested changes, is not the pull request author, and is not a bot. A pull request whose reviews could not be read contributes nothing at all, including for its author, so that both signals rest on the same evidence. The change author (by commit email and, once the branch is pushed, GitHub login), the local git user, and `--exclude` logins are left out.

## How well this works

[tests/backtest][2] replays merged pull requests as if they were open, ranking against history older than each one, and scores the result against the people who actually reviewed it. It also scores a control that ignores the changed paths and names the busiest recent reviewers. Two hundred pull requests per repository, one year of history each:

| Repository | Busiest reviewer covers | Ranked hit@1 / hit@3 | Control hit@1 / hit@3 |
| ---------- | ----------------------- | -------------------- | --------------------- |
| grafana/grafana | 4% of reviewed pull requests | 29% / 54% | 4% / 16% |
| apache/airflow | 26% of reviewed pull requests | 46% / 74% | 47% / 58% |
| vitejs/vite | 63% of reviewed pull requests | 72% / 99% | 72% / 97% |

Path evidence decides the answer where review is spread across the codebase, and the more concentrated review is, the more a repository-wide guess catches up with it. That is what the `repo` rows are for. Reproduce any row inside a blobless clone of that repository:

```bash
git clone --filter=blob:none --no-checkout https://github.com/grafana/grafana.git
tests/backtest -n 200 --since 365
```

`--set NAME=VALUE` overrides a scoring constant, which is how to check that a term still earns its place before changing one.

[1]: scripts/reviewers
[2]: tests/backtest
