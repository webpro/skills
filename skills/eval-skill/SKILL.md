---
name: eval-skill
description: >-
  Measures whether an agent skill fires when it should and whether its output
  beats no skill at all, then fixes what the measurement exposes. Use when asked
  to eval, evaluate, test, benchmark, or score a skill, to check if a skill
  triggers or activates, to find why a skill is ignored or fires on the wrong
  prompts, to compare with-skill against without-skill, or to decide whether a
  skill or one of its rules still earns its place.
---

# Eval a Skill

Measure routing and quality separately. A skill that never loads and a skill
that loads but adds nothing fail for different reasons.

- **Routing:** Does the agent load it on prompts it owns and stay quiet on near
  misses? The name, description, catalog and policy context, competing skills,
  agent, and model can all affect selection. The body contributes only after the
  skill loads.
- **Quality:** With the skill explicitly available, does the result beat the
  previous skill or no skill? Use observable postconditions and a no-skill arm.

Start with the model that will perform the real task. Run other supported target
models separately. A cheaper model is useful for iteration or as an additional
stress case, but its result does not predict a stronger model's result.

## Routing

Start with `skills/<name>/evals/trigger.json` containing 5 realistic positives
and 5 near-miss negatives:

```json
[
  {
    "query": "tokenize() in tokenizer.js is too slow. Speed up the hot path.",
    "should_trigger": true,
    "files": { "tokenizer.js": "export function tokenize(src) { ... }" }
  },
  {
    "query": "Rename `cur` in tokenizer.js to something clearer.",
    "should_trigger": false,
    "files": { "tokenizer.js": "export function tokenize(src) { ... }" }
  }
]
```

Ten cases are a smoke set, not a statistical estimate. Grow the corpus from real
usage, including typical, edge, and adversarial requests. Keep held-out cases
when tuning a description so the same prompts do not serve as both training and
proof.

Resolve [scripts/eval-trigger][1] to an absolute path once and keep it in
`$EVAL`. Run one target agent and model per report:

```sh
"$EVAL" skills/<name> --agent claude --model <target-model> --runs 3 \
  --json skills/<name>/evals/results/routing-claude.json

"$EVAL" skills/<name> --agent codex --model <target-model> --runs 3 \
  --json skills/<name>/evals/results/routing-codex.json
```

The runner verifies that the installed `SKILL.md` has the same SHA-256 as the
source under test. It checks the normal personal skill roots for the selected
agent. Pass `--installed-skill <path>` for a plugin cache or another nonstandard
installation; normal roots remain part of the conflict check.

Before scoring cases, the runner:

1. verifies the agent CLI and source identity;
2. links the verified source into a disposable agent profile without user
   instructions or configuration;
3. checks Claude's advertised skill catalog when that event is available;
4. runs an explicit positive control using the same model and tool policy.

Only instructions authored in a fixture belong to the routing context. Claude
runs in restricted mode from an isolated home with a temporary plugin containing
only the target skill. Codex runs with an isolated home and `CODEX_HOME`, its
existing authentication only, and user config and rules disabled. The report
records this policy context so a score cannot silently depend on the evaluator's
global instructions.

That isolated home also hides Claude's credentials, and the run fails preflight
with `Not logged in` rather than falling back to ambient policy. Set
`ANTHROPIC_API_KEY`, or opt in to reusing the credentials you already hold:

```sh
"$EVAL" skills/<name> --agent claude --model <target-model> --auth-passthrough
```

The flag links `~/.claude/.credentials.json` into the disposable profile when
that file exists. macOS keeps the blob in the login keychain instead, and the
keychain lives under `$HOME/Library`, so an isolated home cannot reach it; there
the runner reads the keychain once and writes the blob `0600` into the profile,
removing it when the process exits. That second path puts an access and refresh
token on disk for the length of the run, which is why the flag is opt-in rather
than automatic. It fails closed when no credential is found. Codex passes its
own `auth.json` through already and ignores the flag. The report names the
mechanism under `agent.auth`.

Claude requires its authoritative `Skill` event. The current Codex stream has no
advertised catalog or dedicated skill event, so that adapter accepts a skill
item when available or a tool input that reads the exact verified `SKILL.md`.
Its positive control must prove that signal before case scoring starts.

The corpus does not run if a control fails. Exit 0 means every case passed, exit
1 means the harness ran successfully and at least one routing expectation
failed, and exit 2 means input, setup, source identity, or agent infrastructure
failed. Never interpret an exit-2 report as a routing score.

### Author useful cases

- Give each case enough real context through `files`. A contextless query can
  make the agent search for a nonexistent target instead of making a routing
  decision.
- Make negatives adjacent tasks owned by neighboring skills. An obviously
  irrelevant negative tests little.
- Require every positive run to fire and every negative run to stay quiet for a
  strict regression gate. Preserve per-run rates when analyzing variance.
- Add more held-out prompts before optimizing a description against a 10-case
  smoke set.

`files` paths are confined to the temporary workspace. A case may also contain
an inline `setup` command, but that is arbitrary shell code. Review it as code
and opt in explicitly:

```sh
"$EVAL" skills/<name> --agent claude --model <target-model> \
  --allow-setup --runs 3
```

Setup runs with closed stdin and hermetic Git configuration. The flag authorizes
the authored setup commands, not other external effects. Agent tool restrictions
do not sandbox setup: it runs once per case and run, inherits most of the host
environment, can use the network, and can write absolute paths. Prefer `files`
for static fixtures. Run effectful setup only after reviewing every command and,
when needed, removing credentials or using a disposable environment.

### Diagnose routing failures

An exit-2 report names the failed phase and retains the agent return code,
stderr, and event trace when `--json` is used. Raw traces are written beside the
report and can contain prompts, paths, and tool arguments. Keep them under the
ignored `evals/results/` directory and inspect them before sharing.

For under-triggering, replace abstract capability language with the symptoms,
phrases, file types, and task boundaries users actually provide. Re-run both
positives and negatives after every description change; recall bought with false
positives is not an improvement.

## Quality

Use explicit skill invocation for quality so implicit-routing variance does not
contaminate the behavioral comparison. `claude plugin eval` provides a
with-skill and no-skill ablation path for Claude:

```sh
CLAUDE_CODE_WALNUT_SPIRE=1 claude plugin eval skills/<name> \
  --runs 3 --model <target-model> --judge-model <judge-model> \
  --no-publish --json skills/<name>/evals/results/quality.json
```

When a case has an authored `scaffold_script`, add `--scaffold` only after
reviewing it. Layout is `evals/<case>/case.yaml` and `prompt.md` plus one file
per grader under `evals/<case>/graders/`.

For Codex, build the same candidate, previous-skill, and no-skill arms in an
isolated fixture and grade their observable postconditions. Do not compare a
Codex run with a Claude baseline as though the agent were the only changed
variable.

- Prefer the deterministic graders `regex`, `file_exists`, `tool_used`, and
  `tool_order`. None runs a command, so a benchmark or linter has to surface
  through the files it writes or the agent's trace.
- Use pass/fail or pairwise LLM graders only for semantic criteria, with a
  detailed rubric and calibration against human judgments.
- Keep the judge model different from the subject model.
- Treat a skill-invocation grader as a routing diagnostic, not output quality.

### Read the delta

| Reading                 | Meaning                                  | Action                                  |
| ----------------------- | ---------------------------------------- | --------------------------------------- |
| with high, without low  | the skill carries the rule               | keep                                    |
| with high, without high | the case does not discriminate           | sharpen the case or reconsider the rule |
| with low, without low   | the rule is unclear or beyond this model | rewrite the rule or case                |
| with below without      | the skill causes harm on this case       | fix before shipping                     |

Compare the candidate against both the previous skill and no skill when changing
an established workflow. One model at three runs is a smoke result; repeat or
expand cases before drawing conclusions from a single flipped run.

## Keep the contract

Commit prompts, sanitized fixtures, graders, setup scripts, and thresholds.
Ignore generated reports, traces, temporary workspaces, secrets, and private or
large corpora. Re-run the source-controlled contract after changing the skill
and record exact before and after results rather than describing an impression.

[1]: scripts/eval-trigger
