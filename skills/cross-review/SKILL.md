---
name: cross-review
description: >
  Hands the current change to a different coding agent for an independent
  pre-commit or pre-ship review, so the implementer never reviews its own work.
  Use whenever the review should come from another model or agent: "cross-review
  this", "second opinion", "fresh eyes on this", "have Codex review it", "have
  Claude review it", "independent review", "review this with another agent", or
  a final, pre-ship, or max-effort review of a branch, a commit, uncommitted
  work, or named paths before committing, merging, or shipping non-trivial
  changes.
---

# Cross Review

Hand the repository directly to a different coding agent; never have the
implementer review its own work. Reuse the CLI's Git, sandboxing, streaming, and
review machinery. General engineering policy comes from `AGENTS.md`.

## Choose the reviewer and model

- From Codex use Claude; from Claude use Codex; otherwise use another installed
  independent agent. Never use the invoking agent.
- Run one reviewer. Panels and repeated reviews require explicit authorization.

Resolve the model when invoking the installed reviewer instead of hardcoding a
release ID:

- Honor a user-named model exactly. Do not substitute another model if it is
  rejected. Use high effort unless the user also explicitly requests max.
- Otherwise inspect the installed CLI's current `--help` and the reviewer's
  current official model catalog before constructing the command. Prefer stable
  capability aliases and documented tier roles; never invent a release ID.
- For every reviewer, a normal review uses the tier immediately below best or
  premium at high effort; only an explicit max request uses the best or premium
  tier at max effort.
- For Claude this means `opus`/high normally and `best`/max explicitly. For
  Codex, use the current balanced model/high normally and flagship/max
  explicitly.

Model names belong to one CLI only. Claude's aliases (`opus`, `sonnet`, `best`,
any `claude-*` id) are not Codex models, and passing one to `codex --model`
starts a turn, spends tokens, and then fails at the API with `The 'sonnet' model
is not supported when using Codex with a ChatGPT account` plus a `turn.failed`.
Its closing message reads "Review was interrupted. Please re-run". That failure
looks like a result, so treat `turn.failed` as fatal rather than retrying.

Resolve each reviewer's model from that reviewer's own catalog. When Codex's
current tier names are not certain, omit `--model` entirely: Codex then uses the
`model` in `~/.codex/config.toml`, which is valid by construction. Omitting the
flag beats guessing one.

Record the requested alias or default. Claude also reports the concrete model on
its initial `system` event and again on every `assistant` message, so record that
resolved id as the review evidence. Codex reports no model in its stream, so
there the request is the only record: say the model is unconfirmed rather than
implying the stream verified it.

Neither CLI reports the reasoning effort it actually applied. Both accept the
flag, so report effort as requested, never as observed.

For a normal review, do not enable premium service tiers, max effort, automatic
fallback, or enlarged output budgets. Set `CLAUDE_CODE_MAX_OUTPUT_TOKENS` only
when the user explicitly requests a larger response budget.

Check for installed alternatives such as Gemini, Copilot, or Pi, but do not
install tools, guess flags, or run another review without authorization. Apply
the same target, handoff, observability, and cost rules. A different CLI using
the invoking agent's model is not an independent review.

## Define the target and handoff

Identify one target:

- branch against its actual base;
- one commit;
- staged, unstaged, and untracked local work; or
- named paths, symbols, or lines plus relevant callers and tests.

Resolve an omitted base from local repository configuration. For a remote branch
or pull request, fetch only its target and base refs when they are absent. Do
not substitute a source archive, create a commit, or modify tracked files solely
for review.

Use one coherent Git checkout with the target materialized and its base object
available. From its root, verify the target diff and named paths before
invocation. Never pair an archive or copied tree with a separate base checkout,
or borrow another checkout's `node_modules`.

Give a candid handoff: intent and acceptance criteria; complexity and tradeoffs;
vulnerabilities and brittle areas; accepted or deferred risks; uncertain
assumptions; test evidence and gaps; and prior finding dispositions. Label
pre-existing risks, but include them when the change depends on, exposes, or
worsens them. Never include secret values. Accurate transfer matters more than
a clean verdict.

Use a compact prompt:

```text
Read the applicable AGENTS.md. Review <target> and relevant surrounding code.

Intent and acceptance criteria: <...>
Known complexity, vulnerabilities, weak points, and accepted/deferred risks: <...>
Tests, evidence, assumptions, and gaps: <...>
Prior findings and dispositions: <none, or ID/status/rationale/evidence>
User-requested focus or evidence (verbatim, if any): <...>

Keep progress observable: announce the starting phase and give one-sentence
updates at meaningful phase changes or completed checks, especially before long
analysis or test runs. Do not narrate routine tool calls or speculate. Claude
honors this and streams the updates as it works; Codex answers once at the end
regardless, so expect its progress to arrive as its plan and command events
instead.

Find concrete regressions introduced by the change. Give severity, file and
line, failure scenario, and smallest coherent fix. Distinguish disclosed
pre-existing risks from new regressions. Omit style-only observations and say
explicitly when there are no actionable findings. Do not create or touch files.
```

## Invoke the reviewer

From Codex, run Claude from the repository root with observable output:

```sh
claude -p --safe-mode --permission-mode plan --no-session-persistence \
  --model opus --effort high --output-format stream-json \
  --include-partial-messages --verbose "<review prompt>" < /dev/null
```

Redirect stdin: without it Claude waits three seconds for piped input before
proceeding.

`--safe-mode` disables project customizations and instruction discovery, so the
prompt must tell Claude to read `AGENTS.md`. Plan mode plus the no-file prompt
provides only best-effort read-only behavior: it is not a filesystem sandbox and
may still save a report in Claude's user state. Snapshot repository status and
the target diff before invocation, compare them again after every terminal
outcome, and report unexpected changes without reverting them.

Use `--model best --effort max` for explicit max requests.

From Claude, use Codex's native observable review command:

```sh
codex exec review --json --ephemeral \
  --model "<current balanced-tier model>" -c model_reasoning_effort=high \
  "<review prompt, naming the target in its first line>"
```

`--base`, `--commit`, and `--uncommitted` are each rejected alongside a prompt
(`error: the argument '--base <BRANCH>' cannot be used with '[PROMPT]'`), and
stdin (`-`) is refused the same way. A custom handoff therefore rules out the
target flags: state the target in the prompt instead ("Review the changes on the
current branch against base branch `main`"), and confirm from the streamed tool
events that it diffed the intended range. Reach for `--base`/`--commit`/
`--uncommitted` only when handing over no prompt at all, which forfeits the
handoff. For explicit max, use the current flagship model and
`-c model_reasoning_effort=max`.

Codex applies `model_reasoning_effort` from `~/.codex/config.toml` unless
overridden, so pass it explicitly on every run; a config default of `xhigh`
otherwise turns each ordinary review into a max-effort one.

For another reviewer, use its verified equivalent of non-interactive, read-only,
live structured output. If it lacks structured output, preserve stdout and
stderr and report that observability is weaker.

Treat an unrecognized, unavailable, or access rejection of a skill-selected
model before review work starts as negotiation. Retry the same prompt once at
the next lower documented tier and the same effort. For Claude, `opus` falls
back to `sonnet`, and max `best` to `opus`; never escalate an ordinary review.
Report both selections. Do not use automatic fallback or retry a user-named
model, blocking rate-limit or capacity response, failure after work starts, or
any other failure.

## Subsequent rounds

Use a fresh invocation and a compact carry-forward, not the transcript. Include
the prior reviewed commit when available, changed paths or symbols, unresolved
risks, and each finding's stable ID, status (`fixed`, `rejected`, `deferred`, or
`accepted risk`), rationale, and evidence. Assign and preserve IDs such as
`AR-1`.

Ask the reviewer to verify fixed findings and report them only when incomplete
or regressed; avoid repeating rejected findings without new evidence; keep
deferred and accepted risks visible without re-arguing them; and focus on the
new delta, its interaction with the original change, and regressions introduced
by fixes.

## Observe and finish

Monitor the structured stream. For Claude, track `system` status, the visible
text it streams as it works, review-relevant tool events, rate limits, and the
terminal `result`, which carries `total_cost_usd`, `num_turns`, and `modelUsage`.
For Codex, track the `todo_list` item it emits early and each `item.completed`
command execution, then the single closing `agent_message` and `turn.completed`;
its usage counters report zeros, so cost and token figures are unavailable on
that side and belong in no report.

Keep display filtering separate from liveness tracking. For Claude, preserve
`assistant` messages containing `tool_use` blocks and `user` messages containing
their `tool_result` blocks in the liveness path even when neither is relayed to
the user. A text-only filter hides active work and creates false stalls.

Progress therefore looks different by reviewer: relay Claude's narrated phases as
they arrive, and Codex's plan with the checks it completes. Treat a Codex run
that has emitted its plan and is still running commands as progressing, not
stalled.

Keep the relayed progress equally concise for either; never relay hidden
reasoning or raw event noise. Success requires a terminal success result, not
exit code zero or silence.

Treat liveness as adaptive and bounded. Before starting, choose a soft stall
window and a hard run limit from target breadth, requested effort, and known
long-running checks. Three minutes normally and six at max are initial soft
windows for a small target, not fixed entitlements. Review-relevant text and
tool events reset the soft window; adapt it to their observed cadence, but never
extend the hard limit. Active tools use their own timeout, and hidden thinking
does not count. At the soft limit, grant one bounded grace window only when
completed checks and an explicit synthesis phase show useful progress. Cancel
otherwise, at the hard limit, or when the same infrastructure failure repeats.

On failure or cancellation, report the reviewer, model, effort, target, elapsed
time, exit code, last meaningful event, and provider state. Validate and present
any coherent reviewer-authored findings as an explicitly incomplete review; do
not reconstruct one from tool activity, hidden reasoning, or fragments. A
partial result is not success and does not authorize a retry.

Apart from model negotiation, do not retry, change model, or fall back without
authorization. Use a temporary `--debug-file` only when structured events cannot
explain a failure. Claude logs may expose local configuration: keep them outside
the repository, never quote them wholesale, and move them to Trash after use.

Validate every finding against the code. Apply accepted fixes separately, run
relevant checks, and repeat the independent review only when the target
materially changed.
