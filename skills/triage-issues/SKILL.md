---
name: triage-issues
description: >-
  Guides bug report and pull request investigation and reproduction. Confirms
  reported behavior is wrong, reproduces issues locally, and checks for
  correct-by-design behavior before writing fixes. Use when given a bug report,
  issue, or error report to investigate.
---

- When given a bug report or a link to issue or pull request, first confirm current behavior is actually wrong
- Reproduce, then check if the reported behavior is correct-by-design before writing any fix
- Find repositories/CodeSandbox/StackBlitz source files and local fixtures to actually reproduce the issue at hand
- To fetch stackblitz.com reproduction url: `pnpx stackblitz-zip https://stackblitz.com/edit/{name} {filename}.zip`
- If no reproduction provided, create a minimal one from the report
- Trace the full code path end-to-end for full context and consider options — don't blindly apply a local fix
- Look up relevant fixtures and tests to better understand scope and context
- Check `git blame`/`git log` around the affected area for recent changes
