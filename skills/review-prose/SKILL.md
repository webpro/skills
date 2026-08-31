---
name: review-prose
description: >-
  Draft, audit, or revise durable technical prose intended for repository files
  or external readers, including documentation, READMEs, changelogs, release
  notes, pull request or issue descriptions, review comments, and other public
  copy. Use when asked to preserve facts while proofreading, tightening,
  polishing, or removing mechanical phrasing. Do not use for ordinary
  conversational replies, to conduct code review, or to publish copy.
---

# Review Prose

Produce durable technical prose that is concrete, natural, and easy to read, with claims calibrated to the evidence. Preserve the author's meaning, voice, and established technical terms. Use neighboring prose as the style reference where available instructions are silent.

## Choose the requested mode

- Draft: Write from verified source material and the user's constraints.
- Audit: Identify material problems without rewriting the copy.
- Revise: Reconstruct weak passages while preserving the author's meaning.

Use draft when the request requires new copy, revise when it asks to change existing copy, and otherwise audit. A request to publish or submit existing copy is not revision authorization. For a revision, change only what improves fidelity, clarity, or naturalness, and do not flatten an intentional voice into generic professional prose.

## Review in risk order

1. Source fidelity: Verify names, links, quantities, attribution, causal claims, consequences, and requested constraints. Preserve code blocks, commands, file paths, identifiers, quoted error text, numbers, and links exactly unless the user requests a change or a verified source requires correction. Distinguish sourced facts, author-provided claims, and inference. Never invent benefits, implementation details, validation, or follow-up work to make the copy sound complete. In a draft, use supported claims and calibrate their certainty to the evidence. In a revision, preserve an author-provided claim when no source contradicts it and report the verification gap outside the copy. When a source contradicts a draft or revision, correct the copy to the sourced fact and report the change outside the copy; never swap wording silently. In an audit, report contradictions and verification gaps without changing the copy.
2. Active policy: Apply any available user or project instructions, especially their communication, public-copy, draft-file, and external-action rules. When present, those instructions own house style; do not replace them with this skill's preferences.
3. Reader value: Lead with the result, behavior, or concern. Keep the detail a future reader needs and remove agent process, local workflow, and ceremonial reporting unless the artifact genuinely calls for it.
4. Naturalness: Edit structure and cadence only after the copy is true and useful.

This order is deliberate. Smooth prose must not hide a factual error or unsupported claim. Complete every applicable pass before delivering; the order controls priority, not when to stop looking.

Determine the intended reader, purpose, and information budget from the request and neighboring artifact. Tightening does not authorize an audience shift or the loss of technical detail. When the user explicitly requests a higher-level summary, lead with the supported outcome, impact or risk, and decision or ask; omit implementation mechanics only to fit that reader.

Before writing the result, make an explicit internal checklist from the source facts, requested constraints, and active policy. Check each item against the exact final text. In particular:

- account for every substantive claim, qualifier, and consequence as sourced, author-provided but unverified, clearly inferred, or unsupported;
- verify requested length and structure rather than estimating them;
- inspect literal characters and line layout covered by public-copy rules;
- check that the ending does not restate the conclusion or invent follow-up work.

Do not claim that the remaining copy is sound unless every substantive statement was checked.

## Recognize mechanical prose

Look beyond stock phrases. Modern model output often sounds generated without matching a cliché list. Check for:

- generic benefit framing before the concrete point;
- excessive headings, summary sections, status banners, or emoji badges;
- repeated conclusions or advisory language after the point is already clear;
- uniform paragraph or sentence shapes that read like a report template;
- exaggerated certainty or consequences not supported by the source;
- suspense, reveal, kicker, or grand-metaphor framing that inflates an ordinary result or concern;
- speculative next steps added only to create a tidy ending;
- an entry that is longer or more formal than its neighbors.

Prefer concrete nouns and verbs, direct transitions, and enough structure to scan the artifact. Do not manufacture informality, sentence fragments, arbitrary variation, or any punctuation or line wrapping that active policy forbids merely to appear human.

For review comments, preserve the structure required by any active review or publishing workflow, including priority and verdict labels. Where no workflow owns the format, a natural shape is usually the observed behavior, its supported consequence, and the ownership-level correction. Keep it to one concern and do not strengthen the consequence beyond the evidence.

## Use the highlighter as evidence, not authority

For substantial Markdown prose, run the bundled [`scripts/llm-cliche-highlighter/llm-cliche-highlighter.mjs`](scripts/llm-cliche-highlighter/llm-cliche-highlighter.mjs) with Node, passing `--markdown` and the draft path.

Inspect each match in context. A match is a review candidate, not an error, and zero matches says nothing about factual fidelity or naturalness. Do not auto-rewrite copy from highlighter output. Short inline comments usually do not benefit from this scan.

## Deliver the result

- For an audit, report factual and policy problems before stylistic ones. Quote only enough text to locate each issue and explain its consequence.
- For a draft or revision, keep unresolved source questions and verification gaps outside the copy. Do not insert warning markers unless the user requests them. Inspect the exact final copy separately from any explanation, save Markdown to a file when active instructions require it, and return its full path.
- Do not include the audit trail, highlighter results, tools, or process narration in public copy.
- Never publish, submit, or update external copy without explicit authorization. Publication authorization for user-supplied copy applies to the exact wording the user approved. If this review changes that wording, or an audit finds a material problem in it, return the copy and findings for a decision instead of handing them to a publishing workflow. When copy is drafted as a necessary part of an authorized external action, follow the active instructions' external-action rules.

## Acknowledgements

- [Unslop][1]: fact-preserving rewrites and structural checks for mechanical prose.
- [LLM cliche highlighter][2]: deterministic candidates for the optional highlighter pass.
- [NoBuzz's `debuzz` skill][3]: audience-aware editing and checks for theatrical framing.

[1]: https://github.com/theclaymethod/unslop
[2]: https://tools.simonwillison.net/llm-cliche-highlighter
[3]: https://github.com/adnanakil/nobuzz/blob/main/debuzz/SKILL.md
