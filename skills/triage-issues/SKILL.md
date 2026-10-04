---
name: triage-issues
description: >-
  Investigate bug reports and review pull requests, including re-reviews and batches.
  Validate the premise, reproduce defects, and assess product fit before recommending fixes or approval.
  Use when given a bug report, issue, or error report to investigate, or a pull request to review or re-review.
---

# Investigate issues and review pull requests

For a queue of issues or PRs, also read [Batch reviews](references/batch-reviews.md).

## Establish the premise first

Read the report, discussion, and original fixtures. Before judging the implementation or proposing fixes, establish what fails, for whom, and why it violates the intended contract. State this and the evidence limits in the first substantive update and the verdict; if unproven, withhold endorsement.

- For bugs, reproduce the failure on a pinned baseline and rule out correct-by-design behavior. For features, establish intended behavior and product fit.
- Type-check or run fixtures with the relevant compiler, runtime, or format checker, including files outside the test's assertions. Repair invalid inputs minimally, keeping original and corrected evidence distinct.
- Use required settings, defaults, and an ordinary supported case as controls to separate an opt-in edge case from a general failure.
- When a representative fixture establishes the defect and scope, do not request a project link or flag its absence.
- Create a minimal reproduction when none exists, and label synthetic cases; proving behavior or finding matching syntax elsewhere does not establish prevalence or project impact.

For StackBlitz: `pnpx stackblitz-zip https://stackblitz.com/edit/{name} {filename}.zip`.

## Assess the solution

- Trace the failing input or changed behavior through callers; for PRs, read the whole diff.
- Use documentation, tests, and history to identify existing policy and the layer that owns the behavior.
- Compare identical valid inputs on pinned base and head. Preserve original acceptance cases, verify the added path, and inspect complete results; fallbacks can hide untested machinery.
- Assess whether the proposed solution satisfies the intended contract, including edge cases. Weigh its user benefit and maintenance cost against simpler alternatives.
- Judge correctness and design necessity separately: passing tests do not justify added shared state, services, caches, or abstractions.
- Separate regressions, incomplete intended behavior, and inherited limitations. Before recommending broader scope, explain the affected workflow and consequence.

## Reach a verdict

- Report defects, test gaps, and design questions distinctly, with severity, trigger, consequence, location, and evidence. Rank findings by user impact.
- When a material design trade-off remains unresolved, explain the options, benefits, costs, and limits. Recommend a direction and let the user decide.
- Approval requires a verified premise, product fit, justified design, correct behavior, and relevant checks. State unresolved design concerns in the verdict, ahead of secondary test improvements.
- On re-review, refresh revisions and record each prior material concern, including the user's, as open, resolved with evidence, or deferred by the user. Explain downgrades and reuse valid checks.
- Verify reviewer claims and proposed fixes; agreement is not evidence. Save bulk logs as files and return conclusions with verification limits.
