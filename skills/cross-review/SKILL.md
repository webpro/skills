---
name: cross-review
description: >
  Hands work produced in the current session to a different coding agent for an
  independent review, so the implementer never reviews its own work. Use only
  when the user explicitly asks for another agent's review: "cross-review this",
  "second opinion", "fresh eyes on this", "have Codex review it", "have Claude
  review it", "independent review", "review this with another agent". A plain
  review request, including "final review" or "review this PR", is the current
  agent's own review; do not add a cross-review to it.
---

# Cross Review

Hand the repository directly to a different coding agent; never have the
implementer review its own work. Reuse the CLI's Git, sandboxing, streaming, and
review machinery. General engineering policy comes from `AGENTS.md`.

## Choose the reviewer and model

- From Codex use Claude; from Claude use Codex; otherwise use another installed
  independent agent. Never use the invoking agent. Run one reviewer; panels and
  repeated reviews require explicit authorization.
- Verify the selected CLI version, required flags, and model policy once per
  session; reuse that evidence while the CLI, provider, and requested policy are
  unchanged. Read only missing facts from relevant help and official catalog
  sections, separately from large repository output. Retain a short result and
  source URL.
- Prefer stable capability aliases and documented tier roles over release IDs.
  For Claude, the [model-alias table][1] supplies the selection facts; do not
  load the full configuration guide. Use only names from the selected reviewer's
  catalog.
- Honor a user-named model exactly, with high effort unless max was explicitly
  requested. Otherwise select:

| Reviewer | Normal review                        | Explicit max request        |
| -------- | ------------------------------------ | --------------------------- |
| Claude   | `opus`, high                         | `best`, max                 |
| Codex    | Current balanced model, high         | Current flagship model, max |
| Other    | Tier immediately below premium, high | Premium tier, max           |

If relying on Codex's configured default, verify that it meets this policy.
Treat `turn.failed` as failure regardless of closing prose; retry only under the
model-negotiation rule below.

Record the requested model and effort, plus Claude's resolved model from its
`system` or `assistant` messages. Codex does not report its resolved model, so
label it unconfirmed. Neither CLI confirms applied effort: report it as
requested.

For a normal review, do not enable premium service tiers, max effort, automatic
fallback, or enlarged output budgets. Set `CLAUDE_CODE_MAX_OUTPUT_TOKENS` only
when the user explicitly requests a larger response budget.

Check installed alternatives such as Gemini, Copilot, or Pi only when the
preferred reviewer is unavailable. Do not install tools, guess flags, or run
another review without authorization. The same target, handoff, observability,
and cost rules apply; a different CLI using the invoking agent's model is not
independent.

## Define the target and handoff

Choose one target and pin its commit IDs in the handoff:

| Target                                  | Review scope                                                                                           |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Committed branch or PR                  | Merge-base with its actual base through the target commit; excludes dirty work                         |
| One commit                              | Parent through commit; use the empty tree for a root commit and name the comparison parent for a merge |
| Local work                              | HEAD through the index and working tree, plus untracked files                                          |
| Complete candidate including local work | Pinned branch merge-base through the index and working tree, plus untracked files                      |
| Named paths, symbols, or lines          | Explicit revisions or local states, with callers and tests as supporting evidence                      |

For committed targets, read the pinned revisions rather than overlying dirty
files. For local targets, inspect staged and unstaged states separately: a
defect in the index remains actionable even if the working tree fixes it. Label
such findings as index-only. Supporting context does not expand the selected
target.

Choose the review unit before invoking the reviewer. Keep a commit separate when
its behavior or risk is independently testable, or when attribution matters.
Group consecutive commits when they change the same subsystem or hot call graph
and the important question is their final interaction. A whole-session diff is
often the better performance target after correctness has already been reviewed:
the reviewer pays repository orientation once and measures the code users will
run. Treat test-only commits as evidence rather than mandatory standalone
reviews. Always name the exact immutable range inside the grouped target.

Resolve an omitted base from local repository configuration. For a remote branch
or pull request, fetch only its target and base refs when they are absent. Do
not substitute a source archive, create a commit, or modify tracked files solely
for review.

Use one coherent Git checkout with the target materialized and its base object
available. From its root, verify the target diff and named paths before
invocation. Never pair an archive or copied tree with a separate base checkout,
or borrow another checkout's `node_modules`.

Before every reviewer invocation, snapshot repository status, target refs and
diffs, and in-scope untracked contents outside the repository. Keep review
inputs unchanged; compare snapshots after every terminal outcome. Report
unexpected changes without reverting them. If reviewed evidence changed, the
verdict cannot establish that the current target is clean.

Resolve applicable instruction files before starting a safe-mode reviewer. Give
their exact paths in the handoff; when none exist in the target checkout, say so
and tell the reviewer not to search unrelated worktrees.

Give a candid handoff using the template below. Distinguish evidence from
assumptions; the reviewer must verify the coordinator's claims. Label
pre-existing risks and include them when the change depends on, exposes, or
worsens them. Never include secret values.

Budget for a delivered verdict. Allocate roughly 20% to orientation, 50% to
investigation and testing, 20% to the final verdict, and 10% to delivery
overhead. This puts the tool cutoff at 70% and the response deadline at 90% of
the total. Adjust the allocation before launch when the target warrants it;
activity alone does not extend it.

Convert those shares to elapsed-time checkpoints from reviewer launch in the
prompt:

```text
Repository instructions: <read these exact AGENTS.md paths, or none exist in
the target checkout; do not search outside it>.
Review <target, pinned commit IDs, and included local states>.

Intent and acceptance criteria: <...>
Known complexity, tradeoffs, vulnerabilities, weak points, and accepted/deferred risks: <...>
Tests, evidence, assumptions, and gaps: <...>
Prior findings and dispositions: <none, or ID/status/rationale/evidence>
User-requested focus or evidence (verbatim, if any): <...>
Severity filter: <user-requested threshold, or all actionable severities>.

Total budget: <duration>. Elapsed checkpoints from launch:
orientation done by <duration>; stop all tools by <duration>;
return final response by <duration>; hard process limit <duration>.
Check elapsed wall time after orientation, after slow calls, and before another investigation.
Bound command timeouts by the tool cutoff, then use only collected evidence.

Read the whole diff, then prioritize changed behavior and its callers. Verify
handoff claims against the code. Reuse supplied check results unless stale or a
specific uncertainty needs independent testing. Stop probing a root cause once
reproduction, attribution, and correction are clear.

Announce the starting phase and give concise updates at meaningful phase changes
or completed checks, especially before long analysis or tests. Do not narrate
routine tool calls or speculate.

Find concrete regressions within the target; surrounding code supplies evidence.
Give severity, file and line in the reviewed state, failure scenario, supporting
evidence, and smallest coherent fix. Label index-only findings. Distinguish
disclosed pre-existing risks from new regressions. Omit style-only observations.
Do not create or touch files.

Return the verdict directly in your final response, without saving a report or
requesting plan approval. Identify the reviewed target and severity filter,
include findings and material coverage gaps, and state when no findings meet the
threshold. Omit an inventory of passing checks and implementation plans. Keep a
focused review under about 500 words when findings allow; retain the evidence
needed to assess each finding.
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
may still save a report in Claude's user state.

Use `--model best --effort max` for explicit max requests.

Use `scripts/run-claude-review.sh <seconds> <model> <effort> <prompt-file>` for
bounded Claude runs. It validates the filter, enforces the process-group
deadline, preserves raw JSONL, checks pipeline statuses, and requires terminal
success. Run it directly; inspect its implementation only when changing or
diagnosing it. Keep raw streams outside the repository and remove them after
extracting review evidence.

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
handoff. For explicit max, use the current flagship model and `-c
model_reasoning_effort=max`.

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

Start each round with a fresh process, `--no-session-persistence`, and a compact
handoff. Include the prior reviewed commit when available, changed paths or
symbols, unresolved risks, and findings with stable IDs (such as `AR-1`), status
(`fixed`, `rejected`, `deferred`, or `accepted risk`), rationale, and evidence.

Verify fixed findings and report only incomplete or regressed fixes. Revisit
rejected findings only with new evidence; keep deferred and accepted risks
visible without re-arguing them. Focus on the new delta, its interaction with
the original change, and regressions from fixes.

For sequential reviews sharing expensive context, optionally keep a local
context capsule containing:

- the reviewed base/target, changed paths, and stable repository map;
- canonical implementation owners and non-obvious invariants;
- verified commands, runtime constraints, benchmark method, and noise floor;
- test and measurement evidence, unresolved risks, and the finding ledger; and
- open questions for the next target.

Exclude transcripts, hidden reasoning, raw tool events, and abandoned
hypotheses. Before reuse, revalidate refs, worktree status, runtime, and other
mutable facts; mark stale entries and pass only relevant facts.

## Observe and finish

Monitor each reviewer's structured stream:

- Claude: `system` status, visible text, review-relevant tool events, rate
  limits, and terminal `result` with `total_cost_usd`, `num_turns`, and
  `modelUsage`.
- Codex: early `todo_list`, each `item.completed` command execution, closing
  `agent_message`, and `turn.completed`. Omit cost and token figures: its usage
  counters report zeros.

Relay Claude's narrated phases as they arrive and Codex's plan and completed
checks, equally concisely. Never relay hidden reasoning or raw event noise.

Track liveness independently of display filtering. Count Claude's `assistant`
messages containing `tool_use` blocks and `user` messages containing
`tool_result` blocks even when not displayed. A Codex run executing commands
after its plan is also progressing.

Validate the filter before a paid run. Preserve the raw structured stream before
filtering, check reviewer, capture, and filter statuses separately, and require
the reviewer's terminal success event in the raw stream. Exit code zero or
silence does not establish success.

Choose a soft stall window from the expected event cadence and longest planned
check. Review-relevant events reset that window, but never the phase cutoffs or
hard deadline. While a tool is active, honor its declared timeout within those
limits. Cancel on a stall that leaves insufficient time to finish, repeated
infrastructure failure, or the hard deadline.

Enforce the hard deadline across the reviewer process group. The watchdog
terminates the run; it does not tell the reviewer to wrap up. The handoff owns
the earlier tool cutoff and response deadline. Check progress against them, not
just liveness. Finish with explicit coverage gaps when the remaining evidence
cannot be gathered in time; a saved report alone is not terminal success.

On failure or cancellation, report the reviewer, model, effort, target, elapsed
time, exit code, last meaningful event, and provider state. Validate and present
any coherent reviewer-authored findings as an explicitly incomplete review; do
not reconstruct one from tool activity, hidden reasoning, or fragments. A
partial result is not success and does not authorize a retry.

Apart from model negotiation, do not retry, change model, or fall back without
authorization. Use a temporary `--debug-file` only when structured events cannot
explain a failure. Claude logs may expose local configuration: keep them outside
the repository, never quote them wholesale, and move them to Trash after use.

A terminal success event establishes execution success, not review completeness.
Validate findings against the reviewed source state and check coverage against
the requested target. Report material coverage gaps or unresolved evidence
needed for the verdict as an incomplete review. Qualify any no-findings verdict
by target and severity filter; findings excluded by that filter do not make the
change clean.

Apply accepted fixes separately, run relevant checks, and repeat the independent
review only when authorized and the target materially changed.

[1]: https://code.claude.com/docs/en/model-config#model-aliases
