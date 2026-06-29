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

Prune a git repository's merged, gone, and stale branches (squash-merges included), plus stale remote-tracking refs, worktrees, and local-only tags. Reports as a dry run first; never touches the current, default, protected, or worktree-checked-out branches.

```sh
npx skills add webpro/skills --skill clean-git-repo
```

### configure-knip

Set up and optimize Knip configuration to find unused files, dependencies, and exports. Use when configuring knip.json or cleaning up a JavaScript or TypeScript codebase.

```sh
npx skills add webpro/skills --skill configure-knip
```

### optimize-javascript

V8/Node.js performance patterns for hot paths, parsers, and core libraries in JavaScript/TypeScript. Use when writing or reviewing performance-sensitive JS/TS code.

```sh
npx skills add webpro/skills --skill optimize-javascript
```

### suggest-pr-reviewers

Find relevant PR reviewers based on code ownership and recency of contributions. Use when creating PRs or needing to identify who should review code changes.

```sh
npx skills add webpro/skills --skill suggest-pr-reviewers
```

### triage-issues

Guides bug report and pull request investigation and reproduction. Confirms reported behavior is wrong, reproduces issues locally, and checks for correct-by-design behavior before writing fixes. Use when given a bug report, issue, or error report to investigate.

```sh
npx skills add webpro/skills --skill triage-issues
```

## Good Skills Elsewhere

- [mcollina/skills][2]
- [theclaymethod/unslop][3]
- [mattpocock/skills][4]
- [currents-dev/playwright-best-practices-skill][5]

[1]: https://github.com/vercel-labs/skills#supported-agents
[2]: https://github.com/mcollina/skills
[3]: https://github.com/theclaymethod/unslop
[4]: https://github.com/mattpocock/skills
[5]: https://github.com/currents-dev/playwright-best-practices-skill
