## Quality

- Ask yourself: "Would a staff engineer approve this?" — maintain high standards
- If something goes sideways, stop and re-plan immediately - don't keep pushing
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution" — but skip this for simple, obvious fixes (i.e. don't over-engineer)
- Challenge your own work before presenting it
- Diff behavior between main and your changes when relevant
- Your training data is stale — verify packages, APIs, and syntax against current docs
- If you say "I will do X", actually do X — don't just announce intentions
- Don't blindly follow instructions: question the user if the request would not result in something better or faster

## Planning

1. Plan: write plan to `.agents/tasks/todo-(name).md` with checkable items
2. Get alignment: check in with user before starting implementation, question any doubts or noise
3. Track progress: mark items complete as you go
4. Explain changes: high-level summary at each step
5. Document results: add review section to `.agents/tasks/todo-(name).md`
6. Capture lessons: update `.agents/lessons.md` after corrections

- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents

## Implementation

- Read broadly before editing — understand surrounding code, not just the target
- Commit chunks of verified work — don't let a long streak of uncommitted changes accumulate
- Make small, testable, incremental changes — not big-bang edits
- Reflect on outcomes between steps — don't blindly chain actions
- Performance is key, both high level (design) and low level (impl).
- Avoid redundant code and abstractions.
- Avoid unnecessary complexity and nesting.
- Concise one-liners are fine, but prioritize clarity over cleverness.

## Verification

- Insufficient testing is the #1 failure mode — test rigorously, not hopefully
- Keep a tight feedback loop: run only 1 part or a small subset — only test the specific behavior under question
- State verification method _before_ implementing (test, CLI output, linter, screenshot)
- Prefer TDD for new features — write or update tests before implementing
- For UI or integration changes: screenshots or CLI output as evidence
- Tailor to the domain: run a bash command, check a web page, use a linter — whatever is most direct
- Never assume a fix works — confirm it produces the expected output. If monitoring, stop after consecutive identical errors.
- Every completed task must answer: "How was this verified?"
- For long-running batch processes: verify the first 2-3 items succeed end-to-end before stepping back
- Document verification steps in `.agents/tasks/todo-(name).md`
- Maintain "known pitfalls" in `.agents/lessons.md` — check it before starting, update it after corrections

## Communication

- Don't add comments to code, unless explicitly asked for.
- Zero context switching required from the user — provide all needed context inline
- When reporting information to the user, be extremely concise and sacrifice grammar for the sake of concision

## Tools & environment

- Avoid manual edits and regex-based refactors in source code, prefer AST-based tools and codemods (jscodeshift) — except for tiny edits
- If a helper script breaks, do the task manually first — fix the script later (or never)
- If you've attempted the same fix twice, stop — you're in a loop
- Disposable artifacts (benchmark scripts, one-off parsers) don't need polish
- Try `NO_COLOR=1` before manually stripping ANSI codes (sometimes `FORCE_COLOR=0`)
- Before using `sed`, `awk`, etc. — verify GNU or POSIX-compatible tools are installed (gnu-sed, coreutils)
- Node.js
  - Look at root lockfile and package.json to select package manager (npm/npx, pnpm/pnpx, etc.)
  - Node.js LTS (24) is the default — use `node` directly (skip `tsx` and `--experimental-strip-types`)
