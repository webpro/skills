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

- For issues, RFCs, and pull requests, first establish the practical need and whether solving it justifies the added complexity. If that is not shown, ask for a representative use case or recommend declining before assessing the solution.
- For bugs, reproduce the failure on a pinned baseline and rule out correct-by-design behavior. For features, establish intended behavior and product fit.
- If discussions or guidance conflict with the project's implementation or API, agree on the intended behavior with the maintainer before judging the change against it.
- Type-check or run fixtures with the relevant compiler, runtime, or format checker, including files outside the test's assertions. Repair invalid inputs minimally, keeping original and corrected evidence distinct.
- Use required settings, defaults, and an ordinary supported case as controls to separate an opt-in edge case from a general failure.
- When a representative fixture establishes the defect and scope, do not request a project link or flag its absence.
- Create a minimal reproduction when none exists, and label synthetic cases; proving behavior or finding matching syntax elsewhere does not establish prevalence or project impact.

For StackBlitz: `pnpx stackblitz-zip https://stackblitz.com/edit/{name} {filename}.zip`.

## Assess the solution

- Trace the failing input or changed behavior through callers; for PRs, read the whole diff.
- Use documentation, tests, and history to identify existing policy and the layer that owns the behavior. Logic placed outside that layer is a design finding even when it works.
- Compare identical valid inputs on pinned base and head. Preserve original acceptance cases, verify the added path, and inspect complete results; fallbacks can hide untested machinery.
- Assess whether the proposed solution satisfies the intended contract, including edge cases. Weigh demonstrated benefits against complexity, maintenance cost, and simpler alternatives; recommend declining when the added complexity is not justified.
- Judge correctness and design necessity separately: passing tests do not justify added shared state, services, caches, or abstractions.
- Challenge changes to shared infrastructure made solely to accommodate one component's special case. Look for a solution within that component or the existing extension points first.
- Separate regressions, incomplete intended behavior, and inherited limitations. Before recommending broader scope, explain the affected workflow and consequence.
- For JavaScript or TypeScript performance concerns, use the measurement guidance in the optimize-javascript skill when available.

## Reach a verdict

- Report defects, test gaps, and design questions distinctly, with severity, trigger, consequence, location, and evidence. Rank findings by user impact.
- Duplicated or misplaced logic that a change adds to core code is a required fix, not an optional suggestion. Keep later rounds narrow by limiting new edge-case requests, not by lowering code quality. Check co-author trailers; when a weak model wrote core logic, say so in the review and read the code more critically.
- When a material design trade-off remains unresolved, explain the options, benefits, costs, and limits. Recommend a direction and let the user decide.
- In a first round, raise structural requests and leave helper or style choices until the structure is settled. Structural rewrites belong before merge, by the author or as a fix-up on their branch; never offer "merge now, refactor later".
- For a stalled contribution, offer a maintainer fix-up on the author's branch as an alternative to another round.
- A pull request without check runs, because it conflicts or awaits approval for a first-time contributor, is untested: run its checks locally on the head.
- Recommend closing a pull request as superseded only after the replacement has landed, citing the commit. For a duplicate, recommend closure with a pointer to the preferred pull request.
- Approval requires a verified premise, product fit, justified design, correct behavior, and relevant checks. State unresolved design concerns in the verdict, ahead of secondary test improvements.
- On re-review, refresh revisions and record each prior material concern, including the user's, as open, resolved with evidence, or deferred by the user. Explain downgrades and reuse valid checks.
- Verify reviewer claims and proposed fixes; agreement is not evidence. Before recommending an alternative fix, compare it with the base on the same and adjacent cases, including inputs it newly excludes. Save bulk logs as files and return conclusions with verification limits.
- Store reports and evidence under the workspace `.agents/reviews/` with the issue or PR id and date in the path, as in `pr-2151.md` or `batch-2086-2090/2086/`, so the next round finds the prior review by id. Sessions share these names: check that the path does not exist and give each re-review its own.
