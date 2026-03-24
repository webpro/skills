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

## Object shapes & inline caches

- Initialize objects with the same properties in the same order — V8 assigns hidden classes (shapes); consistent shapes keep functions monomorphic (fastest), 5+ shapes = megamorphic (hash-table fallback)
- Never conditionally add properties — always set the property (to `undefined` if needed) to keep shapes consistent
- Avoid `delete obj.prop` — mutates hidden class, forces dictionary mode; set to `undefined` instead
- Watch for megamorphism in shared utility functions — a helper called with many different object shapes across the codebase goes megamorphic; split into shape-specific fast paths or use a type-tag `switch` to recover monomorphic performance
- Keep function parameter types stable — mixed types prevent TurboFan specialization
- Prefer integer/numeric enums over string enums — integer comparison is O(1) by value, strings are O(n) character-by-character; small integers are stored as Smi (no heap allocation)

## Strings & regex

- Avoid `.split()` for simple parsing — scan with `indexOf`/`slice` instead (one pass, no intermediate array allocation)
- Use `.includes()` or `.startsWith()` before regex — avoids regex engine for the common non-matching case
- Avoid unnecessary `.trim()`, `.replace()` — forces V8 to materialize internal rope/cons-string representations
- Prefer `String.fromCharCode()` over `String.fromCodePoint()` for BMP characters (< 0x10000) — faster path, and characters outside BMP are rare
- Use `charCodeAt()` for character classification in hot loops — numeric comparison is faster than string operations
- Accumulate ranges, then `.substring()` once — avoid character-by-character string concatenation
- Pre-compute character code constants — avoid runtime `charCodeAt()` on string literals in hot paths
- Prefer manual character scanning (`indexOf`, `charCodeAt`, loops) over regex for simple patterns — regex has engine overhead (backtracking, state machines) that manual parsing avoids
- Cache compiled regexes outside loops — dynamic `new RegExp()` in a loop recompiles every iteration
- Reuse a single `Intl.Collator` instance over repeated `localeCompare()` calls

## Collections

- Prefer `Map` over plain objects for dynamic key-value collections — large Maps are faster for insertion, key lookup and iteration; use objects only for static/known-shape data
- Keep arrays homogeneous — all integers = `PACKED_SMI` (fastest), adding a float transitions to `PACKED_DOUBLE`, adding a string transitions to `PACKED_ELEMENTS` (slowest); transitions are one-way
- Prefer array literals over `new Array(n)` — `new Array(n)` creates permanently "holey" arrays requiring prototype chain lookups; when you need a pre-sized array, use `new Array(n).fill(0)` to avoid holes
- Don't read out-of-bounds — forces V8 prototype chain walk
- Use `Set.has()` over `Array.includes()` for repeated lookups — O(1) vs O(n)
- Cache repeated lookups over static data — a linear scan (`.find()`, `.filter()`) called per item in an outer loop becomes O(n × m); memoize when the underlying data doesn't change between calls
- Use binary search on sorted arrays instead of `.findIndex()` — O(log n) vs O(n)
- Prefer TypedArrays for large numeric data — contiguous memory enables CPU prefetching

## Functions & control flow

- Don't create functions inside hot loops — closure allocation + prevents V8 inlining; also watch for closure nesting in merge/compose patterns where `merged = (x) => { prev(x); next(x) }` applied N times creates N-deep call chains — flatten into an array and iterate instead
- Deduplicate repeated registrations in multi-tenant loops — when the same handler/callback is registered once per iteration (e.g. per workspace, per route, per config entry), identical work multiplies; track what's already registered and skip duplicates
- Keep hot functions small — TurboFan won't inline functions above \~600 AST nodes; extract cold/error paths into separate functions to keep the hot function inlineable
- Prefer `for`/`while` over `.forEach()` in hot paths — the callback creates per-iteration scope frames that prevent TurboFan from inlining
- Avoid the `arguments` object — use rest params (`...args`); even referencing `arguments` inhibits optimization
- Match function arity at call sites — mismatched arity creates arguments adaptor frames
- Generators have inherent overhead — provide array-returning alternative for callers that need all results; use generators only when lazy evaluation is needed
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

- Avoid unnecessary `async`/`await` — each `await` internally creates 2 extra promises and needs 3 microtick round-trips; don't `await` non-promise values, don't wrap already-async functions in redundant `async` wrappers
- Cap concurrency on `Promise.all` over dynamic-length arrays — unbounded parallel I/O exhausts memory, file descriptors, and connection pools; use `p-limit` or `p-map` with an explicit concurrency limit

## Modules

- Lazy-load non-critical modules — dynamic `import()` or `require()` inside conditional blocks avoids loading unused code
- Avoid barrel files (`index.ts` re-exporting everything) — each re-export adds to the module graph
