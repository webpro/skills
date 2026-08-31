// Detector adapted from Simon Willison's Apache-2.0 LLM cliche highlighter: https://github.com/simonw/tools/blob/aabd3c5b1258a20ea2d512269ea72a7f083b07a6/llm-cliche-highlighter.html

import { readFileSync, realpathSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

// ==== impl start ====
// Each pattern: { id, name, description, find(text) -> [{ start, end, badge?, badgeTitle?, count? }] }
// Add new patterns to this array and they get a checkbox, per-pattern count, and highlighting for free.
// makeChainFinder builds a detector for "HEAD X, HEAD Y, ..." lists and counts the items;
// makeRegexFinder wraps a plain regex (must use the g flag); makeEchoFinder builds a
// detector for runs of consecutive sentences repeating the same multi-word skeleton;
// makeQuestionChainFinder flags runs of consecutive question sentences; and
// makeAnaphoraFinder flags runs of consecutive sentences opening on the same word.

const CHAIN_BODY = String.raw`[^,.;:!?\n\u2013\u2014\u2026]*`;
const CHAIN_SEP = String.raw`(?:\s*,\s*(?:and\s+|or\s+)?|\s+(?:and|or)\s+|\s*[;&\u2013\u2014]\s*(?:and\s+|or\s+)?|\s+-{1,2}\s+)`;
const CHAIN_SPLIT = new RegExp(CHAIN_SEP, 'i');

function makeChainFinder(head, headTest, itemLabel) {
  const item = head + CHAIN_BODY;
  const chain = new RegExp(String.raw`\b${item}(?:${CHAIN_SEP}${item})+`, 'gi');
  return function (text) {
    const found = [];
    for (const m of text.matchAll(chain)) {
      let end = m.index + m[0].length;
      while (end > m.index && /\s/.test(text[end - 1])) end -= 1;
      const count = m[0].split(CHAIN_SPLIT).filter(p => headTest.test(p.trim())).length;
      found.push({
        start: m.index,
        end,
        count,
        badge: String(count),
        badgeTitle: count + ' ' + itemLabel + (count === 1 ? '' : 's')
      });
    }
    return found;
  };
}

function makeRegexFinder(re) {
  return function (text) {
    const found = [];
    for (const m of text.matchAll(re)) {
      found.push({ start: m.index, end: m.index + m[0].length });
    }
    return found;
  };
}

// makeEchoFinder builds a detector for runs of consecutive sentences that
// repeat the same multi-word skeleton -- the "X does A. Y does B." triad.
// The badge counts the echoing sentences.
function makeEchoFinder({ minGram = 3, minRun = 2 } = {}) {
  const SENT = /[^.!?\n]+[.!?]?/g;
  const grams = (s, n) => {
    const w = s.toLowerCase().match(/[a-z0-9'’-]+/g) || [];
    const out = new Set();
    for (let i = 0; i + n <= w.length; i++) out.add(w.slice(i, i + n).join(' '));
    return out;
  };
  return function (text) {
    const sents = [];
    for (const m of text.matchAll(SENT)) {
      if ((m[0].match(/\S+/g) || []).length >= 4) {
        sents.push({ start: m.index, end: m.index + m[0].length, text: m[0] });
      }
    }
    const found = [];
    let i = 0;
    while (i < sents.length) {
      let j = i;
      let shared = null;
      while (j + 1 < sents.length) {
        if (sents[j + 1].start - sents[j].end > 3) break; // adjacent prose only
        const a = grams(sents[j].text, minGram);
        const b = grams(sents[j + 1].text, minGram);
        const common = [...a].filter(g => b.has(g));
        if (!common.length) break;
        shared = common.sort((x, y) => y.length - x.length)[0];
        j += 1;
      }
      const run = j - i + 1;
      if (run >= minRun && shared) {
        let end = sents[j].end;
        while (end > sents[i].start && /\s/.test(text[end - 1])) end -= 1;
        found.push({
          start: sents[i].start,
          end,
          count: run,
          badge: String(run),
          badgeTitle: run + ' sentences echoing “' + shared + '”'
        });
        i = j + 1;
      } else {
        i += 1;
      }
    }
    return found;
  };
}

// Flags runs of consecutive question sentences -- the stacked rhetorical
// interrogation. The badge counts the questions.
function makeQuestionChainFinder({ minRun = 2 } = {}) {
  const chain = /[^.!?\n]+\?(?:\s+[^.!?\n]+\?)+/g;
  return function (text) {
    const found = [];
    for (const m of text.matchAll(chain)) {
      const count = (m[0].match(/\?/g) || []).length;
      if (count < minRun) continue;
      let start = m.index;
      while (start < m.index + m[0].length && /\s/.test(text[start])) start += 1;
      found.push({
        start,
        end: m.index + m[0].length,
        count,
        badge: String(count),
        badgeTitle: count + ' questions in a row'
      });
    }
    return found;
  };
}

// Flags runs of consecutive sentences opening on the same word -- "Maybe X.
// Maybe Y. Maybe Z." Pronouns and articles are skipped, since repeating those
// is just ordinary prose. The badge counts the sentences.
const ANAPHORA_SKIP = /^(?:i|it|the|a|an|this|that|we|you|they|he|she|there|but|and|so|in|as|if|my|his|her|their|its|these|those|for|at|on|of|to|is|was)$/i;
function makeAnaphoraFinder({ minRun = 3 } = {}) {
  const SENT = /[^.!?\n]+[.!?]/g;
  return function (text) {
    const sents = [];
    for (const m of text.matchAll(SENT)) {
      const w = m[0].match(/[A-Za-z'’-]+/);
      if (w) {
        sents.push({
          start: m.index + m[0].indexOf(w[0]),
          end: m.index + m[0].length,
          head: w[0].toLowerCase()
        });
      }
    }
    const found = [];
    let i = 0;
    while (i < sents.length) {
      let j = i;
      while (j + 1 < sents.length && sents[j + 1].head === sents[i].head
             && sents[j + 1].start - sents[j].end < 4) j += 1;
      const run = j - i + 1;
      if (run >= minRun && !ANAPHORA_SKIP.test(sents[i].head)) {
        found.push({
          start: sents[i].start,
          end: sents[j].end,
          count: run,
          badge: String(run),
          badgeTitle: run + ' sentences opening “' + sents[i].head + '”'
        });
        i = j + 1;
      } else i += 1;
    }
    return found;
  };
}

// Patterns in this group are adapted from Wikipedia's "Signs of AI writing"
// guide: https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing
const WIKI_GROUP = 'Signs of AI writing (Wikipedia)';

const patterns = [
  {
    id: 'no-chain',
    name: '“No X, no Y” chains',
    description: 'Two or more “no …” items in a row, e.g. “No fluff, no filler, no jargon.” The badge counts the “no” items.',
    find: makeChainFinder(String.raw`no[-\s]`, /^no[-\s]/i, '\u201cno\u201d item')
  },
  {
    id: 'whole',
    name: '“That’s the whole …”',
    description: '“That / this is the whole point, game, thing …”',
    find: makeRegexFinder(/\b(?:that|this)(?:['\u2019]s|\s+(?:is|was))\s+the\s+whole\b(?:\s+\w+)?/gi)
  },
  {
    id: 'did-not-chain',
    name: '“Did not X, did not Y” chains',
    description: 'Two or more “did not …” or “didn’t …” items in a row. The badge counts the items.',
    find: makeChainFinder(String.raw`(?:did\s+not|didn['\u2019]t)\s`, /^(?:did\s+not|didn['\u2019]t)\s/i, '\u201cdid not\u201d item')
  },
  {
    id: 'dont-verb-it',
    name: '“Don’t VERB it … VERB it”',
    description: '“Don’t call it X. Call it Y.” — a negated verb + “it”, then the same verb + “it” again.',
    find: makeRegexFinder(/\b(?:do\s+not|don['\u2019]t)\s+(?:just\s+|simply\s+|merely\s+)?(\w+)(?:\s+(?:of|about|at|on|for|with|to))?\s+it\b[^.!?\n]*?[.!?;,:\u2013\u2014]['"\u201d\u2019]*\s*(?:just\s+|simply\s+|merely\s+)?\1(?:\s+(?:of|about|at|on|for|with|to))?\s+it\b/gi)
  },
  {
    id: 'sit-with',
    name: '“Sit with that”',
    description: 'The reflective “sit with that / this / it (for a moment)”, plus “sit with the discomfort” and friends.',
    find: makeRegexFinder(/\bsit(?:s|ting)?\s+with\s+(?:that|this|it|(?:the|your)\s+(?:discomfort|feelings?|tension|weight|uncertainty|ambiguity|grief|silence|unease))\b(?:\s+for\s+a\s+\w+)?/gi)
  },
  {
    id: 'already-know',
    name: '“You already know”',
    description: '“You already know” — the answer, what to do, or standing alone before a full stop.',
    find: makeRegexFinder(/\byou\s+already\s+knows?\s+(?:the\s+answer|what|how|why|this|that|it|who|where)\b|\byou\s+already\s+knows?\b(?![ \t]+\w)/gi)
  },
  {
    id: 'is-the-entire',
    name: '“Is the entire …”',
    description: '“X is the entire point / game / business model.”',
    find: makeRegexFinder(/(?:\b(?:is|was|are|were)|['\u2019]s)\s+the\s+entire\b(?:\s+\w+)?/gi)
  },
  {
    id: 'the-entire-is',
    name: '“The entire … is”',
    description: '“The entire point / game / business model is …” — the flipped twin of “is the entire”.',
    find: makeRegexFinder(/\bthe\s+entire\s+[\w'\u2019-]+(?:\s+[\w'\u2019-]+){0,4}?\s+(?:is|was|are|were)\b/gi)
  },
  {
    id: 'is-real',
    name: '“Is real … and / not”',
    description: '“The X is real, and / not …”, including “is the real … and it”. Skips “real estate”, “real time”, and similar.',
    find: makeRegexFinder(/\bis\s+(?:(?:the|a)\s+real\b(?![\s-]+(?:estate|time|life|world|quick)\b)[^.!?\n]*?\b(?:and|not)\s+it\b|real\b(?![\s-]+(?:estate|time|life|world|quick)\b)[^.!?\n]*?\b(?:and|not)\b)/gi)
  },
  {
    id: 'punchline',
    name: '“The punchline is”',
    description: '“The punchline is …”, “the punchline:”, or “the punchline?”.',
    find: makeRegexFinder(/\bthe\s+punchline(?:\s+(?:is|was|being)\b|\s*[:?])/gi)
  },
  {
    id: 'worth-naming',
    name: '“Worth naming”',
    description: 'The therapist-voiced “that loss is real and it’s worth naming”, “it’s worth naming that …”, or a “Worth naming:” opener. Skips “naming names”.',
    find: makeRegexFinder(/(?:\b(?:is|are|was|were|feels?|felt|seems?|seemed)|['\u2019]s)\s+(?:\w+\s+){0,2}?worth\s+naming\b(?!\s+names\b)|\bworth\s+naming\s*:/gi)
  },
  {
    id: 'not-nothing',
    name: '\u201cThat\u2019s not nothing\u201d',
    description: '\u201cThat is not nothing\u201d / \u201cthat\u2019s not nothing\u201d, plus the \u201cthis / it / which is not nothing\u201d variants.',
    find: makeRegexFinder(/\b(?:that|this|it|which)(?:['\u2019]s|\s+(?:is|was))\s+not\s+nothing\b/gi)
  },
  {
    id: 'is-the-whole',
    name: '“Is the whole …”',
    description: 'Any subject + “is the whole point / trick / pitch / idea”, plus the “here is the whole …” opener. The twin of “is the entire …”, and a generalisation of “That’s the whole …” to subjects other than that/this.',
    find: makeRegexFinder(/(?:\b(?:is|was|are|were)|['’]s)\s+the\s+whole\b(?:\s+\w+)?|\bhere(?:['’]s|\s+is)\s+the\s+whole\b(?:\s+\w+)?/gi)
  },
  {
    id: 'echo-triad',
    name: 'Echoing sentence runs',
    description: 'Consecutive sentences built on the same repeated skeleton — “A shopping cart is an object in the system. A chat room is an object in the system.” The badge counts the echoing sentences.',
    find: makeEchoFinder({ minGram: 4, minRun: 2 })
  },
  {
    id: 'performative-honesty',
    name: 'Performative honesty',
    description: 'Sincerity announced rather than demonstrated: “I won’t pretend”, “I’ll be honest”, “let’s be honest”, “to be clear”, and sentence-initial “Honestly,” or “Look,”.',
    find: makeRegexFinder(/\bI\s+(?:will\s+not|won['’]t)\s+pretend\b|\b(?:I['’]ll|let['’]s|to)\s+be\s+(?:honest|clear|blunt|real)\b|(?:^|[.!?–—]\s+|\n)(?:Honestly|Look|Truthfully|Frankly)\s*,/gi)
  },
  {
    id: 'thats-the-part',
    name: '“That’s the part …”',
    description: 'Gesturing at a favoured detail instead of stating it: “that is the part a counter can’t reach”, “the part that makes me trust the rest”, “my favourite part of …”.',
    find: makeRegexFinder(/\b(?:that|this|it)(?:['’]s|\s+(?:is|was))\s+the\s+part\b|\bthe\s+part\s+that\s+(?:makes|made|gets|got|keeps|kept)\s+(?:me|you|us|it)\b|\bmy\s+favou?rite\s+part\s+of\b/gi)
  },
  {
    id: 'the-only-i-trust',
    name: '“The only X I trust”',
    description: 'The narrowing superlative reveal: “the only marketing I trust”, “the only thing it needs”, “the only X that matters”.',
    find: makeRegexFinder(/\bthe\s+only\s+[\w'’-]+(?:\s+[\w'’-]+){0,2}?\s+(?:I|you|we|it|he|she|they)\s+(?:trust|need|needs|care|want|wants|use|uses|believe)\b|\bthe\s+only\s+[\w'’-]+\s+that\s+(?:matters|counts|works|survives)\b/gi)
  },
  {
    id: 'take-my-word',
    name: '“Don’t take my word for it”',
    description: 'The stock invitation to verify: “you don’t have to take my word for it”, “don’t take my word for any of this”.',
    find: makeRegexFinder(/\b(?:you\s+)?(?:do\s+not|don['’]t)\s+(?:have\s+to\s+)?take\s+my\s+word\s+for\s+(?:it|any\s+of\s+(?:it|this|that))\b/gi)
  },
  {
    id: 'turns-out',
    name: '“Turns out …”',
    description: 'The casual-revelation opener, almost always bolted to a tidy conclusion: “Turns out X”, “it turns out that X”.',
    find: makeRegexFinder(/(?:^|[.!?–—]\s+|\n)Turns\s+out\b|\bit\s+turns\s+out\s+that\b/gi)
  },
  {
    id: 'fits-in-your-head',
    name: '“Fits in your head”',
    description: 'Dev-blog boilerplate for simplicity: “small enough to hold in your head”, “batteries included”, “it just works”, “zero config”, “sane defaults”.',
    find: makeRegexFinder(/\b(?:hold|fit|fits|holds|held)\s+(?:it\s+)?in\s+your\s+head\b|\bbatteries[-\s]included\b|\bit\s+just\s+works\b|\bzero[-\s]config(?:uration)?\b|\bsane\s+defaults\b/gi)
  },
  {
    id: 'stacked-questions',
    name: 'Stacked rhetorical questions',
    description: 'Two or more questions fired in a row, usually fragments after the first: “Do I know how it works? Where it breaks? Which corners it cut?” The badge counts the questions.',
    find: makeQuestionChainFinder({ minRun: 2 })
  },
  {
    id: 'sentence-anaphora',
    name: 'Repeated sentence openers',
    description: 'Three or more consecutive sentences starting on the same word — “Maybe nobody needed it. Maybe it introduced … Maybe a small convenience …” Pronouns and articles are ignored. The badge counts the sentences.',
    find: makeAnaphoraFinder({ minRun: 3 })
  },
  {
    id: 'colon-triple',
    name: 'Colon into a triple',
    description: 'A colon opening onto three or more comma-separated items: “separate ports, processes, and local state”. The most common shape LLM prose uses to sound concrete. Noisy in technical writing — leave it off by default if your corpus is documentation.',
    find: makeRegexFinder(/:\s+[^.!?;:\n]{2,40},\s+[^.!?;:\n]{2,40},\s+(?:and\s+|or\s+)?[^.!?;:\n]{2,40}(?=[.!?\n])/g)
  },
  {
    id: 'heres-the-twist',
    name: '“Here’s the twist”',
    description: 'The stage-managed reveal: “here’s the twist”, “here’s the thing”, “here’s the catch / kicker / rub”, “here’s the first example:”.',
    find: makeRegexFinder(/\bhere(?:['’]s|\s+is)\s+(?:the|a|my|one)\s+(?:twist|thing|catch|kicker|rub|problem|first|second|third|next|recent|real|best|worst|surprising|interesting|key|important)\b[\w\s-]{0,20}[:.]/gi)
  },
  {
    id: 'x-is-dead',
    name: '“X is dead”',
    description: 'The obituary headline and its sequel: “peer code review is dead”, “botd is dead; long live botd”.',
    find: makeRegexFinder(/\b[\w\s]{3,30}\s+(?:is|are)\s+dead\b|\blong\s+live\s+\w+/gi)
  },
  {
    id: 'thats-why-mattered',
    name: '“That’s why X mattered”',
    description: 'Retroactively assigning significance: “that’s why being able to open the environment mattered”, “this is why preserving every conversation mattered”.',
    find: makeRegexFinder(/\b(?:that|this)(?:['’]s|\s+(?:is|was))\s+why\b[^.!?\n]{0,80}?\b(?:matter(?:s|ed)?|count(?:s|ed)?)\b/gi)
  },
  {
    id: 'stranded-auxiliary',
    name: 'Stranded auxiliary contrast',
    description: 'A clause that lands on a bare auxiliary for the reversal: “The tool died; the data didn’t.”, “Reading mostly passed … Writing didn’t”, “Maybe it wouldn’t have.”',
    find: makeRegexFinder(/[;:,]\s+[^.;:!?\n]{2,50}\s(?:did|does|do|was|were|is|are|has|have|had|can|could|would|will)(?:n['’]t)?\s*[.;]|\b(?:Maybe|Perhaps)\s+\w+[^.!?\n]{0,40}\s(?:would|could|might|should|did|had|was|is)(?:n['’]t)?\s+(?:have\s*)?\./g)
  },
  {
    id: 'ai-vocab',
    group: WIKI_GROUP,
    name: 'AI vocabulary words',
    description: 'Words LLMs lean on far more than people do: \u201cdelve\u201d, \u201ctapestry\u201d, \u201cmeticulous\u201d, \u201cpivotal\u201d, \u201cintricate\u201d, \u201cinterplay\u201d, \u201cunderscore\u201d, \u201cgarner\u201d, \u201cbolster\u201d, \u201cvibrant\u201d, \u201cbustling\u201d, \u201cmultifaceted\u201d, \u201cseamless\u201d, \u201cever-evolving\u201d. One hit can be coincidence \u2014 several is a tell.',
    find: makeRegexFinder(/\b(?:delv(?:e|es|ed|ing)|tapestr(?:y|ies)|meticulous(?:ly)?|pivotal|intricate(?:ly)?|intricacies|interplay|underscor(?:e|es|ed|ing)|garner(?:s|ed|ing)?|bolster(?:s|ed|ing)?|vibrant|bustling|multifaceted|seamless(?:ly)?|commendable|ever-evolving)\b/gi)
  },
  {
    id: 'not-just',
    group: WIKI_GROUP,
    name: '\u201cNot just X, but Y\u201d',
    description: 'Negative parallelisms: \u201cnot just X, but (also) Y\u201d, \u201cnot only \u2026 but \u2026\u201d, and the \u201cit\u2019s not X \u2014 it\u2019s Y\u201d contrast.',
    find: makeRegexFinder(/\bnot\s+(?:just|only|merely|simply)\s+[^.!?\n;]*?\bbut(?:\s+also)?\b|\b(?:it|this|that)(?:['\u2019]s|\s+(?:is|was))\s+not\s+[^.!?\n,;\u2014\u2013]{1,60}[,;\u2014\u2013]\s*(?:it|this|that)(?:['\u2019]s|\s+(?:is|was))\b/gi)
  },
  {
    id: 'note-that',
    group: WIKI_GROUP,
    name: '\u201cIt\u2019s important to note\u201d',
    description: 'Didactic hedging: \u201cit is important to note that\u201d, \u201cit\u2019s worth noting\u201d, \u201cit should be noted\u201d, plus the \u201cworth pausing / considering / asking\u201d family.',
    find: makeRegexFinder(/\bit(?:['\u2019]s|\s+(?:is|was))\s+(?:also\s+)?(?:important|worth|crucial|essential|vital)\s+(?:to\s+(?:note|remember|understand|recognize|mention|pause|consider|ask)|noting|mentioning|remembering|pausing|considering|asking)\b(?:\s+that\b)?|\bit\s+should\s+be\s+noted\b/gi)
  },
  {
    id: 'testament',
    group: WIKI_GROUP,
    name: '\u201cStands as a testament\u201d',
    description: '\u201cStands / serves as a testament (or reminder)\u201d, \u201cis a testament to\u201d \u2014 inflating significance instead of saying what happened.',
    find: makeRegexFinder(/\b(?:stand|stands|stood|serve|serves|served|standing|serving)\s+as\s+(?:a|an)\s+(?:\w+\s+)?(?:testament|reminder)\b|\b(?:is|was|are|were|remain|remains)\s+a\s+(?:\w+\s+)?testament\s+to\b/gi)
  },
  {
    id: 'crucial-role',
    group: WIKI_GROUP,
    name: '\u201cPlays a crucial role\u201d',
    description: '\u201cPlays a crucial / pivotal / vital / key / significant role in \u2026\u201d.',
    find: makeRegexFinder(/\bplay(?:s|ed|ing)?\s+(?:a|an)\s+(?:\w+\s+)?(?:crucial|pivotal|vital|key|significant|central|critical|important)\s+role\b/gi)
  },
  {
    id: 'landscape',
    group: WIKI_GROUP,
    name: '\u201cEver-evolving landscape\u201d',
    description: 'Scene-setting boilerplate: \u201cthe ever-evolving / changing / shifting landscape\u201d, \u201cin today\u2019s fast-paced world\u201d.',
    find: makeRegexFinder(/\b(?:ever-)?(?:evolving|changing|shifting)\s+landscape\b|\bin\s+today['\u2019]s\s+(?:fast-paced|ever-changing|ever-evolving|digital|modern|competitive)\s+\w+/gi)
  },
  {
    id: 'vague-experts',
    group: WIKI_GROUP,
    name: '\u201cExperts argue\u201d',
    description: 'Vague attribution to unnamed authorities: \u201cexperts argue\u201d, \u201csome critics have noted\u201d, \u201cobservers suggest\u201d, \u201cindustry reports indicate\u201d.',
    find: makeRegexFinder(/\b(?:many|some|several|most|numerous)?\s*(?:experts|critics|observers|scholars|analysts|commentators)\s+(?:have\s+|often\s+|widely\s+)?(?:argu(?:e|es|ed)|not(?:e|es|ed)|suggest(?:s|ed)?|believ(?:e|es|ed)|agree[ds]?|contend(?:s|ed)?|observ(?:e|es|ed)|caution(?:s|ed)?|claim(?:s|ed)?|cit(?:e|es|ed)|point(?:s|ed)?\s+out)\b|\bindustry\s+reports?\s+(?:suggest|indicate|show)\w*\b/gi)
  },
  {
    id: 'despite-challenges',
    group: WIKI_GROUP,
    name: '\u201cDespite these challenges\u201d',
    description: 'The boilerplate challenges-and-outlook formula: \u201cdespite these challenges\u201d, \u201cfaces several challenges\u201d, \u201cchallenges remain\u201d, \u201cremains to be seen\u201d, \u201ctime will tell\u201d.',
    find: makeRegexFinder(/\bdespite\s+(?:these|those|such|its|their|the|numerous|significant|ongoing)\s+(?:\w+\s+)?challenges\b|\bfac(?:e|es|ed|ing)\s+(?:several|numerous|many|significant|various|a\s+number\s+of)\s+challenges\b|\bchallenges\s+remain\b|\bremains\s+to\s+be\s+seen\b|\b(?:only\s+)?time\s+will\s+tell\b/gi)
  },
  {
    id: 'participle-tail',
    group: WIKI_GROUP,
    name: 'Participle sentence tails',
    description: 'Superficial analysis bolted onto a sentence end: \u201c\u2026, highlighting / underscoring / showcasing / reflecting the \u2026\u201d.',
    find: makeRegexFinder(/,\s+(?:highlighting|underscoring|emphasizing|showcasing|reflecting|demonstrating|illustrating|signaling|solidifying|cementing|reinforcing|underlining)\s+(?:its|his|her|their|our|the|a|an|how|that|what|both)\b[^.!?\n]*/gi)
  },
  {
    id: 'promo',
    group: WIKI_GROUP,
    name: 'Promotional boilerplate',
    description: 'Travel-brochure tone: \u201cnestled in\u201d, \u201cin the heart of\u201d, \u201crich tapestry / heritage\u201d, \u201chidden gem\u201d, \u201cboasts a\u201d, \u201cbreathtaking\u201d, \u201cstunning views\u201d.',
    find: makeRegexFinder(/\bnestled\s+(?:in|on|among|between|along|at)\b|\bin\s+the\s+heart\s+of\b|\brich\s+(?:cultural\s+|historical\s+)?(?:heritage|history|tapestry)\b|\bhidden\s+gem\b|\bmust-(?:visit|see|try)\b|\bbreathtaking\b|\bboasts?\s+(?:a|an|the)\b|\bstunning\s+(?:views?|scenery|architecture|backdrop)\b/gi)
  },
  {
    id: 'ai-leftovers',
    group: WIKI_GROUP,
    name: 'Chatbot leftovers',
    description: 'Artifacts pasted straight from a chatbot: \u201cas an AI language model\u201d, \u201cas of my last update\u201d, \u201cknowledge cutoff\u201d, plus markup debris like \u201coaicite\u201d, \u201ccontentReference\u201d, \u201cturn0search\u201d and \u201cutm_source=\u201d tracking parameters.',
    find: makeRegexFinder(/\bas\s+an\s+ai(?:\s+language)?\s+model\b|\bas\s+of\s+my\s+last\s+(?:update|training)\b|\bknowledge\s+cutoff\b|\bI\s+(?:cannot|can['\u2019]t|do\s+not|don['\u2019]t)\s+(?:browse\s+the\s+internet|access\s+real-?time)\b|contentReference|oaicite|turn0(?:search|news|image)\d*|attributableIndex|utm_source=/gi)
  }
];

const patternsById = Object.fromEntries(patterns.map(p => [p.id, p]));

// ==== local CLI adapter start ====
function maskRange(chars, start, end) {
  for (let index = start; index < end; index += 1) {
    if (chars[index] !== '\n' && chars[index] !== '\r') chars[index] = ' ';
  }
}

export function maskMarkdown(text) {
  const chars = text.split('');
  let fenced = false;
  let fenceCharacter = '';
  let fenceLength = 0;
  let indentedCode = false;
  let offset = 0;
  let previousBlank = true;

  for (const lineWithBreak of text.match(/[^\n]*(?:\n|$)/g) ?? []) {
    if (lineWithBreak.length === 0) continue;
    const line = lineWithBreak.replace(/\r?\n$/, '');
    const fence = line.match(/^\s*(`{3,}|~{3,})/);

    if (fence) {
      const marker = fence[1];
      maskRange(chars, offset, offset + line.length);
      if (!fenced) {
        fenced = true;
        fenceCharacter = marker[0];
        fenceLength = marker.length;
      } else if (marker[0] === fenceCharacter && marker.length >= fenceLength) {
        fenced = false;
      }
      indentedCode = false;
      offset += lineWithBreak.length;
      previousBlank = false;
      continue;
    }

    const blank = /^[ \t]*$/.test(line);
    const indented = /^(?: {4}|\t)/.test(line);
    if (!fenced && indented && (indentedCode || previousBlank)) {
      maskRange(chars, offset, offset + line.length);
      indentedCode = true;
      offset += lineWithBreak.length;
      previousBlank = false;
      continue;
    }
    if (indentedCode && blank) {
      offset += lineWithBreak.length;
      previousBlank = true;
      continue;
    }
    indentedCode = false;

    if (fenced || /^\s*\|.*\|\s*$/.test(line) || /^\s*\[[^\]]+\]:\s+\S+/.test(line)) {
      maskRange(chars, offset, offset + line.length);
      offset += lineWithBreak.length;
      previousBlank = blank;
      continue;
    }

    let prefixLength = 0;
    let remaining = line;
    while (true) {
      const prefix = remaining.match(/^\s{0,3}(?:#{1,6}\s+|>\s*|(?:[-+*]|\d+[.)])\s+(?:\[[ xX]\]\s+)?)/);
      if (!prefix) break;
      prefixLength += prefix[0].length;
      remaining = remaining.slice(prefix[0].length);
    }
    maskRange(chars, offset, offset + prefixLength);
    offset += lineWithBreak.length;
    previousBlank = blank;
  }

  for (let index = 0; index < text.length; index += 1) {
    if (text[index] !== '`' || chars[index] === ' ') continue;
    let markerLength = 1;
    while (text[index + markerLength] === '`') markerLength += 1;
    const marker = '`'.repeat(markerLength);
    const end = text.indexOf(marker, index + markerLength);
    if (end === -1) continue;
    maskRange(chars, index, end + markerLength);
    index = end + markerLength - 1;
  }

  for (let start = text.indexOf('<!--'); start !== -1; start = text.indexOf('<!--', start + 1)) {
    const end = text.indexOf('-->', start + 4);
    maskRange(chars, start, end === -1 ? text.length : end + 3);
    if (end === -1) break;
    start = end + 2;
  }

  for (let start = text.indexOf(']('); start !== -1; start = text.indexOf('](', start + 2)) {
    if (chars[start] === ' ') continue;
    const end = text.indexOf(')', start + 2);
    if (end === -1) break;
    maskRange(chars, start, end + 1);
    start = end;
  }

  return chars.join('');
}

export function analyzeText(text, { markdown = false } = {}) {
  const matches = [];
  const scanText = markdown ? maskMarkdown(text) : text;

  for (const pattern of patterns) {
    for (const match of pattern.find(scanText)) {
      matches.push({
        pattern: pattern.id,
        name: pattern.name,
        start: match.start,
        end: match.end,
        text: text.slice(match.start, match.end),
        ...(match.count === undefined ? {} : { count: match.count })
      });
    }
  }

  return matches.sort((left, right) =>
    left.start - right.start || left.end - right.end || left.pattern.localeCompare(right.pattern)
  );
}


function usage() {
  console.error('Usage: llm-cliche-highlighter.mjs [--markdown] [FILE]');
}

function main() {
  const args = process.argv.slice(2);
  const markdown = args.includes('--markdown');
  const positional = args.filter(arg => arg !== '--markdown');

  if (positional.length > 1 || (positional.length === 0 && process.stdin.isTTY)) {
    usage();
    process.exitCode = 2;
    return;
  }

  const text = positional.length === 1 ? readFileSync(resolve(positional[0]), 'utf8') : readFileSync(0, 'utf8');
  const matches = analyzeText(text, { markdown });
  console.log(JSON.stringify({
    mode: markdown ? 'markdown' : 'raw',
    match_count: matches.length,
    pattern_count: new Set(matches.map(match => match.pattern)).size,
    matches
  }, null, 2));
}

if (process.argv[1] && realpathSync(process.argv[1]) === fileURLToPath(import.meta.url)) main();
