# Skills

Everything is skill issues

- [clean-git-repo][1]
- [configure-knip][2]
- [cross-review][3]
- [eval-skill][4]
- [optimize-javascript][5]
- [publish-pr-review][6]
- [review-prose][7]
- [send-ntfy-notification][8]
- [suggest-pr-reviewers][9]
- [triage-issues][10]
- [using-git][11]
- [using-git-worktrees][12]

## Options

| Option                   | Description                                                                      |
| ------------------------ | -------------------------------------------------------------------------------- |
| -g, --global             | Install to user directory instead of project                                     |
| -a, --agent \<agents...> | Target specific agents (e.g. `claude-code`, `codex`), see [Available Agents][13] |
| -s, --skill \<skills...> | Install specific skills by name (use `'*'` for all skills)                       |
| -l, --list               | List available skills without installing                                         |

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

### cross-review

Hand local work, a branch, commit, or focused code scope to a different coding
agent for an independent review with balanced model defaults.

```sh
npx skills add webpro/skills --skill cross-review
```

### eval-skill

Measure whether a skill fires when it should and whether its output beats no
skill at all, then fix what the measurement exposes. Bundles a trigger harness
that drives the installed skill against the rest of your skills.

```sh
npx skills add webpro/skills --skill eval-skill
```

### optimize-javascript

Optimize slow JavaScript and TypeScript hot paths, parsers, allocation-heavy
code, startup, and module loading for V8 and Node.js.

```sh
npx skills add webpro/skills --skill optimize-javascript
```

### publish-pr-review

Publish an already-completed pull request review as one concise verdict with
actionable findings attached inline.

```sh
npx skills add webpro/skills --skill publish-pr-review
```

### review-prose

Draft, audit, and revise documentation and public technical copy while
preserving facts, voice, and project style.

```sh
npx skills add webpro/skills --skill review-prose
```

### send-ntfy-notification

Send a plain-text ntfy notification after a task is verified complete and the
notification is authorized.

```sh
npx skills add webpro/skills --skill send-ntfy-notification
```

### suggest-pr-reviewers

Rank candidate reviewers by ownership and recency among authors of existing
lines changed in a diff, using chunk-level Git blame.

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

Discover, select, reuse, or create checkouts and worktrees from any starting
directory while keeping shared `.agents` state at the workspace root.

```sh
npx skills add webpro/skills --skill using-git-worktrees
```

## Good Skills Elsewhere

| Repository                                         | Install                                                                                      |
| -------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| [mcollina/skills][14]                              | `npx skills add mcollina/skills --skill node --skill typescript-magician`                    |
| [theclaymethod/unslop][15]                         | `npx skills add theclaymethod/unslop`                                                        |
| [mattpocock/skills][16]                            | `npx skills add mattpocock/skills`                                                           |
| [currents-dev/playwright-best-practices-skill][17] | `npx skills add currents-dev/playwright-best-practices-skill`                                |
| [obra/superpowers][18]                             | `npx skills add obra/superpowers --skill systematic-debugging --skill receiving-code-review` |

[1]: #clean-git-repo
[2]: #configure-knip
[3]: #cross-review
[4]: #eval-skill
[5]: #optimize-javascript
[6]: #publish-pr-review
[7]: #review-prose
[8]: #send-ntfy-notification
[9]: #suggest-pr-reviewers
[10]: #triage-issues
[11]: #using-git
[12]: #using-git-worktrees
[13]: https://github.com/vercel-labs/skills#supported-agents
[14]: https://github.com/mcollina/skills
[15]: https://github.com/theclaymethod/unslop
[16]: https://github.com/mattpocock/skills
[17]: https://github.com/currents-dev/playwright-best-practices-skill
[18]: https://github.com/obra/superpowers
