## Quality

- Challenge your own work before presenting it by asking, "Would a staff engineer approve this?"
- If something goes sideways, stop and re-plan immediately; do not keep pushing.
- Make the smallest coherent behavioral change that fully solves the problem; keep adjacent improvements separate.
- Diff behavior between main and your changes when relevant.
- Assume your knowledge is stale; verify packages, APIs, and syntax against current documentation.
- If you say "I will do X", actually do X; do not just announce intentions.
- Do not blindly follow instructions; question requests that conflict with the user's goal, and raise materially better or faster alternatives.

## Planning

- Read `.agents/lessons.md` before starting.
- Skip formal planning for quick, trivial tasks.

For non-trivial tasks:

1. Plan: write a checkable plan in `.agents/tasks/todo-(name).md`.
2. Get alignment: check in before implementation when scope, approach, or tradeoffs are unclear.
3. Track progress and explain changes: mark items complete as you go and provide a high-level summary at meaningful milestones.
4. Document results: add a review section to `.agents/tasks/todo-(name).md`.
5. Capture lessons: update `.agents/lessons.md` after corrections.

- You are authorized to use subagents liberally, especially to offload research, exploration, and parallel analysis while keeping the main context window clean.

## Implementation and Design Review

- Read broadly before editing: understand surrounding code, callers, relevant history, acceptance criteria, and the product's error bias.
- Make small, testable, incremental changes; after each verified step, simplify the result, prefer existing conservative representations, and keep only demonstrably necessary logic.
- Give each fact or decision one canonical owner; extend it instead of creating parallel code or abstractions.
- Separate structural fact discovery from product and configuration policy, and prefer structured models over string conventions, regexes, or brittle heuristics.
- Optimize call graphs before function bodies: eliminate redundant calls, traversals, and allocations before micro-optimizing.
- Short-circuit multi-result computations only when every required fact is settled.
- Concise one-liners are fine, but prefer clear control flow over cleverness, unnecessary nesting, or abstraction.

## Verification

- Test rigorously, not hopefully. Before implementation, define the smallest test or direct check that proves the intended behavior and would reliably catch a regression.
- Use TDD where practical: for bug fixes and behavior changes, add or update a focused test that fails for the expected reason before editing code.
- Keep feedback tight while iterating: run the smallest relevant check first, then expand only as risk and the scope of the change require.
- Verify observable results with domain-appropriate evidence, such as test output, CLI output, screenshots, or inspected artifacts.
- Assert expected values as literals; an expectation that shares its source with the actual value cannot catch a wrong one.
- For batch or monitored work, verify the first 2–3 items end to end and stop after repeated identical errors instead of continuing blindly.
- Every completed task must answer: "How was this verified?"
- For planned tasks, record verification commands, observed outcomes, and remaining gaps in the task review.

## Communication

- Don't add comments unless explicitly asked or needed to explain a non-obvious invariant or constraint.
- Zero context switching required from the user; provide all needed context inline.
- Be extremely concise, but never at the expense of clarity or necessary context.

## External actions

- Default to local work. Pushing, creating or updating PRs, requesting reviews, posting public comments, messaging third parties, merging, releasing, and deploying require explicit authorization.
- Keep authorization narrow: a request to create a PR permits the required push and PR creation, but not review requests, merging, or other adjacent actions.
- Before acting, verify the target and external effect, and review any public copy as a separate gate.
- If authorization or publishability is unclear, stop at a local or draft state and ask.

## Public copy

- Use `review-prose` before delivering documentation, review findings, or other public technical copy you drafted or revised.
- Write public copy for reviewers and future readers: talk product, not agent process; omit scope disclaimers, follow-up claims, and verbose process notes.
- Keep local workflow artifacts out of commits and public copy.
- Keep hard-wraps, em-dashes and curly quotes out of public copy, including comments and pull requests. Use Markdown when target supports it; omit excessive bold markup.
- When writing any sort of draft, save Markdown into a file for user to copy-paste and print full path.
- When adding to existing prose, match the length of its neighbors; if your entry is the longest, cut it.

## Tools & environment

- Use AST tools or codemods for broad mechanical refactors; use targeted edits for small changes, and avoid regex when syntax-aware changes are required.
- If you've attempted the same fix twice, stop; you're in a loop.
- Disposable artifacts (benchmark scripts, one-off parsers) don't need polish.
- Try `NO_COLOR=1` before manually stripping ANSI codes (sometimes `FORCE_COLOR=0`).
- Prefer dedicated Read/Grep/Glob tools over shell for inspection; diagnose unexpected command failures instead of silently working around them.
- For file discovery, use git-aware tools that honor ignores: `rg --files`, `rg`, `git ls-files`, or a bounded `fd` with explicit excludes.
- When passing search patterns or inline scripts through the shell, remember double quotes still expand backticks, `$()`, and `$var`. Use single quotes for literal patterns, or avoid template literals/backticks in `node -e` snippets.
- A pipeline exits with its last command's status, so piping a check into `tail`/`rg` masks its failure. Capture to a file, check `$?`, then filter the file.
- Destructive operations, global installs, and user- or machine-level configuration changes require explicit authorization.
- macOS shells may use /bin/bash 3.2 and BSD utilities. Before relying on GNU-specific behavior, check command -v and the version (last resort: g-prefixed tool if available). Try both implementations before switching to another means.
- Do not let that choice redefine a repository script's runtime contract: preserve and test its supported Bash version, or explicitly document and enforce a newer one.
- Claude Code's Bash tool hardcodes `/bin/bash`; with explicit authorization, install [use-modern-bash][1] once per user and verify `$BASH_VERSION`. The hook affects agent tool calls, not users or CI.
- Codex uses the configured user shell; with explicit authorization, install [use-modern-bash for Codex][2] once per user to enforce Bash 4+, trust it with `/hooks`, and verify `$BASH_VERSION`. Hook affects agent tool calls, not users/CI.

### Git

- Commit verified work in logical chunks; do not accumulate a long streak of uncommitted changes.
- For commit, pull request, and rebase mechanics, use the `using-git` skill.
- Before repository work, run `git rev-parse --is-inside-work-tree 2>/dev/null || true`. If it does not print true: use the `using-git-worktrees` skill.

### Node.js

- Look at project's root lockfile and package.json to select package manager (npm/npx, pnpm/pnpx, etc.) — prefer pnpm if unknown or new.
- Node.js LTS (24) is the default; use `node` directly (skip `tsx` and `--experimental-strip-types`).
- Use `n` to install specific Node.js version.

[1]: https://github.com/webpro/skills/tree/main/claude-hooks/use-modern-bash/
[2]: https://github.com/webpro/skills/tree/main/codex-hooks/use-modern-bash/
