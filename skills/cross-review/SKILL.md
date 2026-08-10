---
name: cross-review
description: >
  Hand the current change to an independent coding agent for a focused
  pre-commit or pre-ship review. Use for cross-review, second-model review,
  review by Claude, Codex, or another installed coding agent, maxed-out review,
  branch or commit review, or final review after non-trivial code changes.
---

# Cross Review

Hand the repository directly to a different coding agent. Do not have the
implementer review its own work. Do not duplicate Git, sandboxing, streaming, or
review machinery already provided by its CLI. General engineering policy comes
from the repository `AGENTS.md`.

## Choose the reviewer

- From Codex → use Claude. From Claude → use Codex, etcetera.
- Never use the invoking agent.
- Run one reviewer. Panels and repeated reviews require explicit authorization.

| Reviewer | Normal default                  | Explicit max request         |
| -------- | ------------------------------- | ---------------------------- |
| Claude   | `opus-4.8`, high effort         | `fable`, max effort          |
| Codex    | `gpt-5.6-terra`, high reasoning | `gpt-5.6-sol`, max reasoning |

Do not enable premium service tiers, fallbacks, or enlarged output budgets by
default. Set `CLAUDE_CODE_MAX_OUTPUT_TOKENS` only when the user explicitly
requests a larger response budget.

Check for installed alternatives such as Gemini, Copilot or Pi. Discovery does
not authorize another review. Do not install tools or guess flags. Apply this
skill's target, handoff, observability, and balanced-cost rules. A different CLI
using the invoking agent's model is not an independent second-model review.

## Define the target and handoff

Identify one target:

- branch against its actual base;
- one commit;
- staged, unstaged, and untracked local work; or
- named paths, symbols, or lines plus relevant callers and tests.

Resolve an omitted base from local repository configuration. For a remote branch
or pull request, fetch only its target and base refs when they are absent. Do
not substitute a source archive, commit, or modify tracked files solely for
review.

Review from one coherent Git checkout with the target materialized and its base
object available. Before invocation, verify from its root that the target diff
and every named path resolve. Do not combine an extracted archive or copied tree
with a separate base checkout, and never borrow another checkout's
`node_modules`.

Give the reviewer a candid handoff: intent and acceptance criteria; non-obvious
complexity and tradeoffs; known vulnerabilities, weak points, brittle areas, and
accepted or deferred risks; uncertain assumptions; test evidence and gaps; and
every prior finding's disposition. Label pre-existing risks, but do not hide
them when the change depends on, exposes, or worsens them. Describe risks
without secret values. Accurate transfer matters more than a clean verdict.

Use a compact prompt:

```text
Read the applicable AGENTS.md. Review <target> and relevant surrounding code.

Intent and acceptance criteria: <...>
Known complexity, vulnerabilities, weak points, and accepted/deferred risks: <...>
Tests, evidence, assumptions, and gaps: <...>
Prior findings and dispositions: <none, or ID/status/rationale/evidence>
User-requested focus or evidence (verbatim, if any): <...>

Find concrete regressions introduced by the change. Give severity, file and
line, failure scenario, and smallest coherent fix. Distinguish disclosed
pre-existing risks from new regressions. Omit style-only observations and say
explicitly when there are no actionable findings. Do not create or touch files.
```

## Invoke the reviewer

From Codex, run Claude from the repository root with observable output:

```sh
claude -p --safe-mode --permission-mode plan --no-session-persistence \
  --model sonnet --effort high --output-format stream-json \
  --include-partial-messages --verbose "<review prompt>"
```

`--safe-mode` disables project customizations and automatic instruction
discovery, so the prompt must tell Claude to read the applicable `AGENTS.md`.
Plan mode may still save a report artifact in Claude's user state despite the
no-file instruction. For an explicit max request, replace the model and effort
with, for instance, `--model fable --effort max`.

From Claude, use Codex's native observable review command:

```sh
codex exec review --json --ephemeral --base "<base>" \
  --model gpt-5.6-terra -c model_reasoning_effort=high \
  "<review prompt>"
```

Choose one target flag: `--base "<base>"`, `--commit "<sha>"`, or
`--uncommitted`. Put narrower paths or symbols in the prompt. For an explicit
max request, use `--model gpt-5.6-sol -c model_reasoning_effort=max`.

For another reviewer, use its verified equivalent of non-interactive, read-only,
live structured output. If it lacks structured output, preserve stdout and
stderr and report that observability is weaker.

## Subsequent rounds

Reuse the compact prompt above in a fresh invocation, replacing its
prior-findings field with a compact carry-forward rather than replaying the
transcript. Include the prior reviewed commit when one already exists, the paths
or symbols changed since, unresolved risks, and each finding's stable ID, status
(`fixed`, `rejected`, `deferred`, or `accepted risk`), rationale, and evidence.
Assign an ID such as `AR-1` when first recording a finding and preserve it.

Ask the reviewer to verify fixed findings and report them only when incomplete
or regressed; avoid repeating rejected findings without new evidence; keep
deferred and accepted risks visible without re-arguing them; and focus on the
new delta, its interaction with the original change, and regressions introduced
by fixes.

## Observe and finish

For Claude, monitor `system` status, visible text deltas, rate-limit events, and
the terminal `result`; do not relay hidden-thinking or raw event noise. For
Codex, monitor its JSON events and terminal status. Success requires a terminal
success result, not merely exit code zero or silence.

Set a proportional no-progress expectation before starting. Repeated path or ref
failures, cwd drift, and tool activity without review-relevant progress count as
a stall. For a small target, cancel after three minutes without review-relevant
progress even at max effort and report the stall. Max effort increases depth,
not an elapsed-time entitlement.

On failure or cancellation, report reviewer, model, effort, target, elapsed
time, exit code, last meaningful event, and provider error or rate-limit state.
Do not retry, change model, or fall back without authorization. Use a temporary
`--debug-file` only when structured events cannot explain a failure; Claude
debug logs can expose sensitive local configuration, so never store them in the
repository or quote them wholesale, and move them to Trash immediately after
diagnosis.

Validate every finding against the code. Apply accepted fixes separately, run
relevant checks, and repeat the independent review only when the target
materially changed.
