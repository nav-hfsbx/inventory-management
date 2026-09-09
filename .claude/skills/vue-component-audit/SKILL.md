---
name: vue-component-audit
description: Audits Vue component structure across client/src and reports ranked, file-anchored findings on cross-component duplication, render-path cost, and oversized components. Diagnostic only - it reports, it does not edit. Use this skill when asked to analyze, audit, or find optimization and reuse opportunities in the Vue frontend, or before a refactor to decide what is worth changing.
---

# Vue Component Audit

Finds where `client/src` has drifted from its own conventions, and ranks what is
worth fixing. **Analysis only** - this skill produces a report. It never edits
`.vue` files.

## Scope, and what this skill is not

This skill is deliberately narrow. Three things it does **not** do:

1. **It does not teach Vue principles.** `client/CLAUDE.md` is auto-loaded in the
   client subtree and already covers computed-vs-methods, `v-show` vs `v-if`,
   `v-for` keys, extraction thresholds, and when to write a composable. Do not
   restate any of that. This skill contributes the *detection procedure and the
   ranking*: `client/CLAUDE.md` says what good looks like, this says how to find
   where the code isn't that and which gap to fix first.
2. **It does not apply fixes.** Findings that touch a `.vue` file must be handed
   to **vue-expert** - the root `CLAUDE.md` makes that mandatory for any creation
   or significant modification of a `.vue` file. Produce the report; let the user
   decide what gets delegated.
3. **It is not the general `optimize` skill.** That one sweeps the whole
   codebase. This one only looks at Vue component structure in `client/src`.

## The detection pass

Run these from `client/src`. They are cheap; run all of them before forming any
conclusion, because the ranking in the next section depends on comparing their
results against each other.

### 1. Cross-component duplication

The highest-value sweep. Find helpers defined independently in more than one
component:

```bash
# Named helpers that recur across files
for name in currencySymbol formatDate formatCurrency formatNumber formatMonth \
            getStatusClass calculatePercentage; do
  n=$(grep -rl "const $name" views components 2>/dev/null | wc -l | tr -d ' ')
  [ "$n" -gt 1 ] && echo "$name: $n files" && grep -rl "const $name" views components
done
```

To find candidates this list doesn't name, pull every local helper and count:

```bash
grep -rhoE '^\s*const [a-zA-Z][a-zA-Z0-9]* = (\(|computed\()' views components \
  | sed -E 's/^\s*const ([a-zA-Z0-9]+).*/\1/' | sort | uniq -c | sort -rn | head -20
```

### 1c. Inventory the shared layers first

Do this before proposing anything. A helper that looks like a missing
abstraction is often a shared module that most files simply do not import:

```bash
ls composables/ utils/
grep -rn "from '\.\./utils\|from '\.\./composables" views components \
  | sed -E "s/.*from '([^']+)'.*/\1/" | sort | uniq -c | sort -rn
```

A shared module imported by only one or two files is the strongest signal in this
whole audit: it means an abstraction exists and the rest of the codebase is
re-implementing it. Compare the re-implementations against it - they are usually
not equivalent.

### 2. Diff the copies - this is where the bugs are

A duplicate count alone is not a finding. **Always read every copy before
reporting.** Identical copies are debt; copies that have *diverged* are usually a
live bug, because one variant got a fix the others never received.

```bash
for f in $(grep -rl "const formatDate" views components); do
  echo "--- $f"; grep -A8 "const formatDate" "$f"
done
```

### 3. Composable usage inside function bodies

`useI18n()` / `useFilters()` are module-level singletons meant to be called once
in `setup()`. Calling them inside a function body re-invokes the composable on
every call:

```bash
grep -rnE "^ {6,}(const .*= )?use(I18n|Filters)\(\)" views components
```

The indentation threshold is what makes this work: a legitimate call sits at 4
spaces directly inside `setup()`, while a call nested in a function body sits at
6 or more. Filtering on the text `setup()` instead does **not** work - that
string is on a different line from the call - and returns every top-level call as
a false positive. Confirm each hit by eye before reporting.

### 4. Render-path cost

Functions called from the template run on **every render**. Inside a `v-for` they
run once per row per render. A function that loops over a collection to derive a
value that does not change per-row belongs in a `computed`:

```bash
# What the template calls
grep -ohE '\{\{ *[a-zA-Z]+\(' views/*.vue components/*.vue | sort | uniq -c | sort -rn

# For each recurring name, check whether the body scans a collection
grep -A12 "const <name> = " views/<File>.vue
```

Flag it when a template-called function contains a loop, `.reduce(`, `.filter(`,
`.map(`, or `Math.max(...)` over a ref. Ignore pure formatters and `t()`.

### 5. Component size against the repo's own thresholds

`client/CLAUDE.md` sets the bar: extract when the template exceeds ~100 lines or
the logic exceeds ~150.

```bash
for f in views/*.vue components/*.vue; do
  awk -v F="$f" '/^<template>/{t=NR} /^<script/{if(!s)s=NR} /^<style/{st=NR}
    END{ if (s-t>100 || st-s>150) printf "%-45s template:%4d script:%4d style:%4d\n", F, s-t, st-s, NR-st }' "$f"
done
```

Match `/^<script/`, not `/^<script>/` - seven components here open with
`<script setup>`, and the stricter pattern silently scores them `template: -1`
instead of flagging them.

## Ranking

Report in this order. The ordering matters more than the count - a long flat list
reads as padding.

1. **Divergent duplicates.** The same helper copied N times where the copies do
   not agree. One of them is wrong. Name which behaviour differs and which file
   is the odd one out.
2. **Correctness risks in the render path.** Unguarded date parsing, formatters
   that throw on `null`, anything the root `CLAUDE.md` "Common Issues" list warns
   about.
3. **Identical duplicates.** Pure debt, zero behaviour change to fix. Cheap and
   safe, so worth listing - but it is not a bug.
4. **Render-path cost.** Real but usually invisible at this data scale; say so
   rather than implying a user-visible slowdown.
5. **Oversized components.** Always true, rarely urgent. Only worth raising with
   a specific extraction proposal attached.

## Where extractions should land

Do not emit "consider extracting this." Name the destination:

| Duplicated thing | Destination |
|---|---|
| Money rendering | `utils/currency.js` - **it already exists**; see the warning below |
| `formatDate` / date to locale string | `useI18n()` - it already owns `currentLocale` |
| `translateX` name mappers | `useI18n()`, beside the existing `translateWarehouse` |
| Filter-to-query-param shaping | `useFilters()` / `api.js` |
| Repeated card, badge, table shell markup | `components/`, or the global styles in `App.vue` |
| Anything reading shared state across views | a composable, per `client/CLAUDE.md` |

Check `utils/` before proposing any new home. It is easy to miss - only two files
import from it - and proposing a fresh helper that duplicates something already
there is the worst outcome an audit can produce.

`useI18n()` is the right home for the rest: it is a module-level singleton, every
component already imports it, and it holds `currentLocale`, which the duplicated
formatters each re-derive.

### Two implementations of one concept

The most valuable thing this audit finds is not a helper copied N times - it is
**two different helpers doing the same job differently.** Step 1's per-name sweep
will not catch it, because the names differ. Look for it whenever a domain
concept (money, dates, status) is rendered in more than one place.

This audit's first run found one, since fixed - kept here because it is the
clearest illustration of the method. `utils/currency.js` `formatCurrency()`
*converted* USD to JPY at a fixed rate before formatting, and was imported by
exactly two files. Eight other files hand-rolled a `currencySymbol` computed that
swapped `$` for `¥` and prefixed the **unconverted** number. So in Japanese the
Dashboard rendered `¥4,675,027,950` while Reports rendered `¥31,166,853.09` for
the same underlying figure - one converted, one not. Six views and three modals
were labelling dollar amounts as yen.

Neither side looks wrong in isolation. Only rendering both and comparing reveals
it, which is why step 1c (inventory the shared layers) comes before any
proposal: a shared module imported by 2 of 16 files is the tell.

The fix collapsed both into one path - `formatMoney()` on `useI18n()` - so the
duplication and the bug were the same defect.

When you find a split like this, rank it top and say which side is correct.

## Do not flag

As of this skill's writing the codebase is already clean on the things a generic
Vue audit reaches for first. Re-run the checks, but do not manufacture findings:

- `:key="index"` - zero occurrences
- Options API (`data()`) components - none
- Direct `axios` imports bypassing `api.js` - none
- `console.*` left in components - one, in `views/Spending.vue`
- Missing loading/error states - all views have them
- **Mixed `<script setup>` and `setup()`** - this looks like drift but is a
  convention: all 8 views use `export default { setup() }`, all 7 components in
  `components/` use `<script setup>`. `components/FilterBar.vue` is the single
  exception, using `setup()`. Do not report the split as an inconsistency, and
  do not propose converting either group.

- **`const close = () => emit('close')` in six modals.** These *are*
  byte-identical, so a name-count sweep flags them - but do not propose
  extracting them. `emit` is bound to the component instance, so a shared helper
  would have to take it as an argument, trading three obvious lines for
  indirection. Identical does not imply extractable; the test is whether the
  extraction removes a place a bug can hide, and here it does not.

If a sweep returns nothing, say so. "No findings in this category" is a useful
result and keeps the report honest.

## Output

A ranked list. Every finding needs a `file:line`, what is wrong, and the concrete
change. No diffs, no applied edits.

```
### 1. formatDate has diverged across 6 copies  [divergent duplicate]
components/ProductDetailModal.vue:112 hardcodes 'en-US', so it never
localizes - the other five derive the locale from currentLocale.
views/Orders.vue:201 has no null guard where views/Dashboard.vue:637 returns '-'.
Fix: move one guarded, locale-aware formatDate into useI18n(); delete 6 copies.
Touches .vue files -> delegate to vue-expert.
```

Close with a one-line summary of what was swept and what came back empty.

## Worked example

A run of steps 1, 2, and 5 against this repo produced:

- **`currencySymbol` in 8 files, byte-identical**, *and* competing with
  `utils/currency.js`. The name-count sweep reads this as harmless debt; reading
  the bodies against the util showed it was a user-visible bug, because the eight
  copies never converted USD to JPY. Ranked first, above the six-copy
  `formatDate`, because it rendered wrong numbers rather than merely inconsistent
  ones. **Fixed** - the eight copies and both direct util imports now go through
  `formatMoney()` on `useI18n()`.

  Re-run step 1 before citing this: it should now come back clean. If it does
  not, the fix regressed.
- **`formatDate` in 6 files, three variants.** Divergent, and therefore ranked
  above the eight-copy one: `ProductDetailModal.vue` hardcodes `'en-US'` and
  never localizes; `Orders.vue` lacks the null guard `Dashboard.vue` has.
- **`useI18n()` called inside a function body** at `views/Dashboard.vue:637`,
  `views/Orders.vue:201`, `views/Demand.vue:194`. The first two are inside
  `formatDate` and disappear once that helper is hoisted; the third is inside
  `translatePeriod`, an unrelated function, and needs its own fix. Do not assume
  hits in the same list share a cause - open each one.
- **Eight components over the thresholds**, led by `views/Dashboard.vue` at
  template 298 / script 430 / style 542 - roughly 3x the repo's own limits - and
  `views/Spending.vue` at 173 / 320 / 358. Note that style is the largest block
  in both; extraction proposals should say whether they move markup, logic, or
  CSS, since those are different jobs.

Note the shape: the *smaller* duplicate outranked the larger one because it
disagreed with itself. That is the point of step 2.

## Verifying a run

Before reporting, confirm each finding is real:

- Read the actual copies. A grep count is not evidence of duplication.
- Check the finding is not already fixed - this codebase changes under
  concurrent sessions; re-read a file before citing a line number.
- If claiming a render-path cost, point at the loop in the function body.
- Prefer "no findings" over a padded list.
