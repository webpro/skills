# Skills

Everything is skill issues

## Options

| Option                   | Description                                                                  |
| ------------------------ | ---------------------------------------------------------------------------- |
| -g, --global             | Install to user directory instead of project                                 |
| -a, --agent \<agents...> | Target specific agents (e.g., claude-code, codex), see [Available Agents][1] |
| -l, --list               | List available skills without installing                                     |

## In This Repo

### clean-git-repo

Prune a git repository's merged, gone, and stale branches (squash-merges
included), plus stale remote-tracking refs, worktrees, and local-only tags.
Reports as a dry run first; never touches current, default, or protected
branches, nor locally modified worktrees, including ones with ignored files.

```sh
npx skills add webpro/skills --skill clean-git-repo
```

### configure-knip

Set up and optimize Knip configuration to find unused files, dependencies, and
exports. Use when configuring knip.json or cleaning up a JavaScript or
TypeScript codebase.

```sh
npx skills add webpro/skills --skill configure-knip
```

### optimize-javascript

V8/Node.js performance patterns for hot paths, parsers, and core libraries in
JavaScript/TypeScript. Use when writing or reviewing performance-sensitive JS/TS
code.

```sh
npx skills add webpro/skills --skill optimize-javascript
```

### send-ntfy-notification

Send a plain-text ntfy notification after a task is verified complete and the
notification is authorized.

```sh
npx skills add webpro/skills --skill send-ntfy-notification
```

### suggest-pr-reviewers

Find relevant PR reviewers based on code ownership and recency of contributions.
Use when creating PRs or needing to identify who should review code changes.

```sh
npx skills add webpro/skills --skill suggest-pr-reviewers
```

### triage-issues

Guides bug report and pull request investigation and reproduction. Confirms
reported behavior is wrong, reproduces issues locally, and checks for
correct-by-design behavior before writing fixes. Use when given a bug report,
issue, or error report to investigate.

```sh
npx skills add webpro/skills --skill triage-issues
```

### using-git

House commit, pull request, and rebase workflow, including commit style, issue
references, and commit-signing failures.

```sh
npx skills add webpro/skills --skill using-git
```

### using-git-worktrees

Resolve regular checkouts and single- or mixed-repository worktree containers
from cwd while preserving their shared `.agents` workspace.

```sh
npx skills add webpro/skills --skill using-git-worktrees
```

## Good Skills Elsewhere

| Repository                                        | Install                                                                   |
| ------------------------------------------------- | ------------------------------------------------------------------------- |
| [openclaw/agent-skills][2]                        | `npx skills add openclaw/agent-skills --skill autoreview`                 |
| [mcollina/skills][3]                              | `npx skills add mcollina/skills --skill node --skill typescript-magician` |
| [theclaymethod/unslop][4]                         | `npx skills add theclaymethod/unslop`                                     |
| [mattpocock/skills][5]                            | `npx skills add mattpocock/skills`                                        |
| [currents-dev/playwright-best-practices-skill][6] | `npx skills add currents-dev/playwright-best-practices-skill`             |

[1]: https://github.com/vercel-labs/skills#supported-agents
[2]: https://github.com/openclaw/agent-skills
[3]: https://github.com/mcollina/skills
[4]: https://github.com/theclaymethod/unslop
[5]: https://github.com/mattpocock/skills
[6]: https://github.com/currents-dev/playwright-best-practices-skill
