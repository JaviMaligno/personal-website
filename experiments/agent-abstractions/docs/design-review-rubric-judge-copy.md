# Design review rubric (judge copy)

You judge the DESIGN of a code change, not whether its behaviour is correct. Answer exactly
the questions listed in the packet's `questions.json`, each as defined below, and nothing
else. Read the packet's request (`statement.md`), its change (`diff.patch`) and the code
tree the change applies to (`tree.txt`), with read/grep only. A refactor packet also has
`sites.json`, the copy sites its request is about.

## Scores (1 = poor … 5 = excellent), each with a one-sentence justification
1. **reuse** — uses the helpers/abstractions that already exist in this tree instead of
   re-implementing them.
2. **duplication** — the diff does not duplicate logic (within itself or with existing code).
3. **placement** — logic lives in the module/layer where this tree puts that kind of logic;
   respects the existing layering.
4. **scope** — the change is focused; no unrelated edits.
5. **maintainability** — overall, a maintainer would be comfortable owning this design.

Flags: `bypasses_abstraction` `{"value": bool, "where": str}` (the change goes around an
abstraction the tree already has); `duplicated_blocks` (int, blocks of logic the change
duplicates); `would_merge` (`"yes"` | `"with_changes"` | `"no"`).

## Further questions

- `t2_reuse`: `"helper"` when the new consumer
  calls a shared function that also serves the pre-existing consumers (including one an
  earlier change in this tree created); `"copy"` when it copies existing logic;
  `"reimplements"` when it writes its own version of that logic without copying it.
- `one_place` (packets whose request changes a rule): `{"value": bool, "where": str}`: does the rule change land in one
  shared definition that every code path applying the rule uses?
- `abstraction_drift` (packets that span several changes): `{"value": bool, "parameters_added": int,
  "special_case_branches": int, "bypassing_call_sites": int, "where": str}`: over the
  packet's changes, flags/parameters added to a shared helper, special-case branches added inside
  it, call sites that bypass or re-implement it.
- `disguised_duplication`: `{"value": bool,
  "where": str}`: is logic this diff duplicates (within itself or with the tree)
  disguised (renamed, reordered, split or reshaped) rather than removed or shared?
- `interface` (refactor packets): `{"score": 1–5, "why": str}`: parameters for the real variation, no
  speculative options, the preserved inconsistencies made explicit.
- `completeness` (refactor packets): per site of `sites.json`, as below.

## Completeness of a refactor, per site

**What a site's decision is.** The `decision` and each site's `decides` text in `sites.json`. A site's own data handling is *not* part of the decision: reading its own
fields (the same setting may be named differently at different sites), converting its own
formats (a day string to a date and back), awaiting or not, logging. A variation that
exists only at that one site in the original code (an option no other site has) may stay
at the site.

**Levels, per site** (`per_site`: `{site id: "full" | "partial" | "none"}`):
- **full (1)** — every element of the site's decision is taken by the shared definition;
  the site only passes its own data, plus at most an explicit argument that selects a
  variation the definition names (a preserved inconsistency made explicit).
  Examples: every month-wide budget action takes its category set from one selection
  function, with a parameter for the hidden-category rule, and the sign of an average
  from one function. Each ranged-amount site calls the existing exported amount helper
  with the raw value (missing, number or range), and the one site that rounds
  differently calls it with an explicit rounding-mode argument. Each date site passes its
  own schedule's enable flag and mode, under its own field names, to one function that
  decides whether and how to move the date.
- **partial (0.5)** — the site calls the shared definition, but still decides part of the
  decision itself: a filter, condition, branch, dispatch or flag computation that the
  shared definition takes, or should take, for the other sites. Anchors:
  - the shared category selection is called with "exclude hidden", but the query that
    feeds the site still filters hidden categories and hidden groups in its own SQL, so
    the hidden rule is still decided there (twice);
  - the date site calls the shared weekend function, which now takes the enable flag,
    but keeps its own outer `enabled ? adjust(…) : date` ternary around the call;
  - the shared function covers only the range arithmetic; each site keeps its own
    `missing ? 0 : number ? value : shared(range)` dispatch, while the decision includes
    the missing and numeric cases (and an existing helper decides all three);
  - one caller computes the flag the shared function decides on with its own expression
    (its own strict comparison combined with another option), where the other callers
    pass their raw field, so "whether the rule applies" is still settled differently at
    that site.
- **none (0)** — the site still decides locally (does not call the shared definition for
  the decision, or calls it only for something that was already shared), or it was not
  touched. Anchors: a refactor that converts two of five provider functions and leaves
  three as they were (the three are none); a site deliberately left out to keep a
  inconsistency listed as one to preserve ("unifying it would change results") is **none**, with the
  reason recorded (`left_out`); the same inconsistency carried as an explicit parameter
  of the shared definition is **full**.

When a site is between two levels, choose the lower one and say why in `why`.

**Value.** `completeness = (n_full + 0.5 × n_partial) / sites_total`. Output:
`{"per_site": {id: level}, "left_out": {id: "preserve_inconsistency" | "missed" |
"other"}, "sites_full": int, "sites_partial": int, "sites_total": int, "value": float,
"why": str}` (`left_out` lists only sites scored none that the diff did not route through
the definition).


## Output

One JSON object per packet with `"id"` and exactly the keys its `questions.json` lists.
Scores `{"score": 1-5, "why": str}`; flags `{"value": bool, "where": str}`;
`duplicated_blocks` an int; `would_merge` a string; `t2_reuse` one of `"helper"`,
`"copy"`, `"reimplements"`; `abstraction_drift` and `completeness` objects as defined
above.
