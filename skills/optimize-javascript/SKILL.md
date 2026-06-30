---
name: optimize-javascript
description: V8/Node.js performance patterns for hot paths, parsers, and core libraries in JavaScript/TypeScript. Use when writing or reviewing performance-sensitive JS/TS code.
---

## Core principles

Keep V8 on the fast path:

1. Consistent shapes — same properties, same order, never `delete`
2. Stable types — don't mix parameter types across calls
3. Minimize allocations — every `{}`, `[]`, spread is GC work
4. Simple operations first — manual scanning over regex, `for` over iterators

## Optimization workflow

- Profile before changing code — identify whether the bottleneck is CPU, I/O, allocation/GC, startup/module graph, or algorithmic complexity
- Benchmark the smallest representative workload — warm up, consume results so dead-code elimination cannot remove the work, and compare baseline/change in the same run to avoid drift
- Use the right Node/V8 diagnostic for the question — `node --prof`/`--prof-process` for CPU, `--trace-deopt` for deoptimizations, `--trace-turbo-inlining` for inlining, `--log-ic` for inline-cache state, heap snapshots or GC traces for memory
- Treat every rule below as a hypothesis — keep the change only when profiler output, benchmark output, or simpler asymptotic behavior pays for the added complexity in the target workload

## Object shapes & inline caches

- Initialize objects with the same properties in the same order — V8 assigns hidden classes (shapes); consistent shapes keep functions monomorphic (fastest), 5+ shapes = megamorphic (hash-table fallback)
- Never conditionally add properties — always set the property (to `undefined` if needed) to keep shapes consistent
- Avoid `delete obj.prop` — mutates hidden class, forces dictionary mode; set to `undefined` instead
- Watch for megamorphism in shared utility functions — a helper called with many different object shapes across the codebase goes megamorphic; split into shape-specific fast paths or use a type-tag `switch` to recover monomorphic performance
- Keep function parameter types stable — mixed types prevent TurboFan specialization
- Prefer integer/numeric enums over string enums — integer comparison is O(1) by value, strings are O(n) character-by-character; small integers are stored as Smi (no heap allocation)

## Strings & regex

- Avoid `.split()` for simple parsing — scan with `indexOf`/`slice` instead (one pass, no intermediate array allocation)
- Don't hand-roll char-by-char splitting to avoid `.split()` — native `.split()` is a C++ builtin and beats a JS accumulation loop (`cur += s[i]`); even an `indexOf`/`slice` loop that still builds the array loses to it. Only skip `.split()` when you can extract what you need in a single `indexOf`/`slice` pass with no array materialization (`"".split(sep)` returns `[""]` not `[]`, so guard if you need `[]`)
- Use `.includes()` or `.startsWith()` before regex — avoids regex engine for the common non-matching case
- Avoid unnecessary `.trim()`, `.replace()` — forces V8 to materialize internal rope/cons-string representations
- Prefer `String.fromCharCode()` over `String.fromCodePoint()` for BMP characters (< 0x10000) — faster path, and characters outside BMP are rare
- Use `charCodeAt()` for character classification in hot loops — numeric comparison is faster than string operations
- Accumulate ranges, then `.substring()` once — avoid character-by-character string concatenation
- Pre-compute character code constants — avoid runtime `charCodeAt()` on string literals in hot paths
- Hoist invariant string building out of hot-loop comparisons — `arr.find(d => path.startsWith(`${d}/`))` rebuilds `${d}/` every iteration; precompute the concatenated forms once and compare against the pre-built strings (applies to any `+`/template in a loop that doesn't vary with the iteration)
- Prefer manual character scanning (`indexOf`, `charCodeAt`, loops) over regex for simple patterns — regex has engine overhead (backtracking, state machines) that manual parsing avoids
- Cache compiled regexes outside loops — dynamic `new RegExp()` in a loop recompiles every iteration
- Reuse a single `Intl.Collator` instance over repeated `localeCompare()` calls

## Collections

- Prefer `Map` over plain objects for dynamic key-value collections — large Maps are faster for insertion, key lookup and iteration; use objects only for static/known-shape data
- Keep arrays homogeneous — all integers = `PACKED_SMI` (fastest), adding a float transitions to `PACKED_DOUBLE`, adding a string transitions to `PACKED_ELEMENTS` (slowest); transitions are one-way
- Prefer array literals over `new Array(n)` — pre-sized arrays start holey and can stay on slower paths; when you need a pre-sized dense array, initialize it immediately with `.fill(value)`
- Don't read out-of-bounds — forces V8 prototype chain walk
- Use `Set.has()` over `Array.includes()` for repeated lookups — O(1) vs O(n)
- Don't double-look up a Map — `if (map.has(k)) map.get(k).add(v)` hashes the key twice (`has` and `get` each run the lookup); take the value once with `const inner = map.get(k); if (inner) inner.add(v)` (or `map.get(k)?.add(v)`). Caveat: the single-lookup form treats a missing key as falsy, so only use it when `undefined`/falsy isn't a valid stored value
- Cache repeated lookups over static data — a linear scan (`.find()`, `.filter()`) called per item in an outer loop becomes O(n × m); memoize when the underlying data doesn't change between calls
- Use binary search on sorted arrays instead of `.findIndex()` — O(log n) vs O(n)
- Prefer TypedArrays for large numeric data — contiguous memory enables CPU prefetching

## Functions & control flow

- A function created per hot-loop iteration only costs when it *escapes* — stored, registered, or passed where its identity is observed. V8 often inlines or elides the rest (immediately-invoked callbacks, args to builtins like `.map`/`.then`, object-property callbacks), so don't flag a non-escaping callback as a cost without evidence it's retained. For merge/compose fan-out, prefer an array of handlers + a plain iteration loop over nested `merged = (x) => { prev(x); next(x) }` wrappers applied N times: the nested chain gets progressively slower as it deepens, while the array loop stays flat. A one-off 2-way compose is fine (it inlines to two direct calls); don't build deeper wrapper chains expecting a speedup
- Push, don't poll, on growing shared collections — when a producer mutates a Set/Array the consumer needs to react to, fire a callback on each add; polling "did the size grow? then re-iterate" is O(N×M) because each consumer pass re-walks the full collection from the start
- Deduplicate repeated registrations in multi-tenant loops — when the same handler/callback is registered once per iteration (e.g. per workspace, per route, per config entry), identical work multiplies; track what's already registered and skip duplicates
- Keep hot functions small — V8's inlining budgets change by version and code shape; extract cold/error paths when it keeps the hot path simple enough to inline
- Prefer `for`/`while` over `.forEach()` in measured tight loops — callback overhead and inlining limits can matter, but don't flag non-escaping callbacks without profiler or benchmark evidence
- Avoid the `arguments` object — use rest params (`...args`); even referencing `arguments` inhibits optimization
- Match function arity at call sites — mismatched arity creates arguments adaptor frames
- Generators have inherent overhead — provide array-returning alternative for callers that need all results; use generators only when lazy evaluation is needed
- A generator's cost is the per-element `yield` suspend/resume itself — V8 inlines surrounding identity wrappers, nested closures, and dead constant-guarded branches (`if (DEBUG) …`) to \~0, so stripping that wrapping for speed does nothing. To remove the cost, return an array instead of yielding (trades a one-time allocation for no per-element suspension). Eliminate the generator, not the wrapping
- Don't use try/catch for expected control flow — use APIs that return null/undefined (e.g. `fs.statSync(file, { throwIfNoEntry: false })`) because Error objects capture stack traces, which is expensive
- Keep try blocks small — V8 optimizes code outside try blocks more aggressively
- Avoid `Proxy` in hot paths — V8 falls back from JIT to interpreter

## Allocation & GC pressure

- Minimize object allocations in hot paths — every `{}`, `[]`, `new` is GC work
- Avoid `{...spread}` for copying objects in hot paths — allocates + copies all properties; mutate or use a dedicated clone function; `structuredClone` is even worse — for shallow copies, `Object.assign`/spread is dramatically faster than `structuredClone`
- Cache deep property chains in local vars — `const x = obj.a.b.c` avoids repeated pointer dereferences
- Short-circuit common cases to avoid allocations — e.g. return single element directly instead of `.join()` on a one-element array
- Reuse objects with `reset()`/`copyFrom()` instead of allocating new ones — swap references instead of creating
- Measure before reusing allocations — object pooling/reuse adds complexity; V8 handles short-lived same-shape objects efficiently via young-generation GC, so per-call `new Set()` may be cheaper than maintaining reusable state
- Memoize allocators whose output is deterministic from their input — a function returning a fresh `Set`/array/object built from its args (e.g. `getDependencies(name) { return new Set([...a, ...b]) }`) reallocates an identical result on every call; cache by input when the same inputs recur. Caveats: the cached value is now shared, so callers must treat it as immutable, and it only pays off when inputs actually repeat
- Defer expensive work with lazy getters — use `null` sentinel to distinguish "not computed" from "no value", parse on first access only
- Never use an unbounded `Map`/object as a cache — it's a memory leak; use `lru-cache` with `max` + `ttl` to bound growth, or `WeakMap` when keys are objects with independent lifetimes

## Loops & state machines

- Use numeric state variables — integer comparison is cheaper than string/object state
- Use index-based `while` loops for tight scanning — faster than iterators
- Pre-compute lookup tables (Map/object) for classification — trade O(1) build time for O(1) lookups in hot paths
- Pack multiple boolean flags into a `Uint8Array` lookup table — use bitwise `& 1`, `& 2` to test individual flags from a single byte
- Cache `indexOf` results and search forward from last position — avoid rescanning from the start
- Split fast path / slow path — check for the common simple case first and return early, only fall through to complex parsing when needed
- Use character lookahead before committing to state changes — peek at next char(s) to decide the operation without advancing position

## Async

- Avoid unnecessary `async`/`await` — async boundaries are not free, especially in hot loops; don't `await` non-promise values, don't wrap already-async functions in redundant `async` wrappers, and measure before contorting readable code
- Cap concurrency on `Promise.all` over dynamic-length arrays — unbounded parallel I/O exhausts memory, file descriptors, and connection pools; use `p-limit` or `p-map` with an explicit concurrency limit

## Modules

- Lazy-load non-critical modules — dynamic `import()` or `require()` inside conditional blocks avoids loading unused code
- Avoid barrel files (`index.ts` re-exporting everything) — each re-export adds to the module graph

## Resources

V8 internals — the "why" behind most of the rules above:

- [Sparkplug][1] — baseline compiler: why simple code gets fast quickly before top-tier optimization
- [Maglev][2] — mid-tier optimizer: how modern V8 reaches optimized code without going straight to TurboFan
- [TurboFan][3] — optimizing compiler: function inlining, dead-code elimination, and version-dependent inlining budgets
- [Fast properties in V8][4] — hidden classes (shapes); why consistent property order and avoiding `delete` keep objects monomorphic
- [Elements kinds in V8][5] — packed vs holey arrays and the one-way SMI → double → elements transitions
- [What's up with monomorphism?][6] — Vyacheslav Egorov on inline caches and mono/poly/megamorphic call and property sites
- [Speculative optimization in V8][7] — Benedikt Meurer on feedback vectors driving the fast path
- [Trash talk: the Orinoco garbage collector][8] — generational GC; why short-lived, same-shape allocations are cheap
- [Built-in functions][9] — native methods (`.split()`, etc.) are CSA/Torque builtins, hard to beat with hand-written JS

Specific patterns:

- [Faster async functions and promises][10] — async/promise optimization history; treat old microtask-cost rules as version-sensitive
- [Speeding up spread elements][11] — iterator-protocol overhead vs. the array fast path
- [ECMAScript generators from a performance perspective][12] — Andy Wingo on the `yield` suspend/resume cost

Reference:

- [Node.js profiling][13] — official `node --prof` workflow
- [Node.js flame graphs][14] — official guide for CPU flame graph analysis
- [Node.js heap snapshots][15] — official memory diagnostics workflow
- [ECMA-262][16] — the language spec, e.g. `String.prototype.split` edge cases

Measure before trusting any rule here — V8 behavior shifts between versions; use a harness that defeats dead-code elimination such as [mitata][17].

[1]: https://v8.dev/blog/sparkplug
[2]: https://v8.dev/blog/maglev
[3]: https://v8.dev/docs/turbofan
[4]: https://v8.dev/blog/fast-properties
[5]: https://v8.dev/blog/elements-kinds
[6]: https://mrale.ph/blog/2015/01/11/whats-up-with-monomorphism.html
[7]: https://benediktmeurer.de/2017/12/13/an-introduction-to-speculative-optimization-in-v8/
[8]: https://v8.dev/blog/trash-talk
[9]: https://v8.dev/docs/builtin-functions
[10]: https://v8.dev/blog/fast-async
[11]: https://v8.dev/blog/spread-elements
[12]: https://wingolog.org/archives/2013/06/11/ecmascript-generators-from-a-performance-perspective
[13]: https://nodejs.org/en/learn/getting-started/profiling
[14]: https://nodejs.org/en/learn/diagnostics/flame-graphs
[15]: https://nodejs.org/en/learn/diagnostics/memory/using-heap-snapshot
[16]: https://tc39.es/ecma262/
[17]: https://github.com/evanwashere/mitata
