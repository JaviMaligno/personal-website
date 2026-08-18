# Publish checklist — "An LLM Can Infer the Rule You Forgot — in One Dimension"

The article is written and builds, but it **must not be merged as-is**: it carries
placeholders that only resolve once arXiv announces the preprint (submitted
2026-08-18 as `submit/7965524`, primary cs.LG).

## Blocking, in order

1. **arXiv ID.** Replace every `ARXIV_PENDING` and every `arXiv:PENDING` with the
   real identifier. They appear in:
   - `src/content/blog/en/infer-the-rule-in-one-dimension.md` (body, footer, `linkedinLinks`)
   - `src/content/blog/es/infer-the-rule-in-one-dimension.md` (same places)
   - `docs/marketing/x-thread-infer-the-rule-in-one-dimension.md`

   ```bash
   grep -rn 'ARXIV_PENDING\|arXiv:PENDING' src/content/blog docs/marketing
   ```

2. **`pubDate`.** Currently `2026-08-20` in both languages as a placeholder. Set it
   to the actual merge date — the blog index sorts by it, so a stale date buries the
   post under older ones.

## Decided

3. **`linkedinImage`: leave it unset — the hero is the right feed image.** The plan was
   to export the article's first figure (105/111 vs 0/156) because a concrete number
   beats an illustration in the feed. The generated hero already *is* that contrast:
   it carries both figures in large type beside the two experiments. Exporting the SVG
   would add a weaker duplicate, so the fallback (`linkedinImage || heroImage`) is the
   correct outcome here rather than an omission.

## Already done

- Hero image generated, reviewed at 1020x510 and saved to
  `public/blog/infer-the-rule-in-one-dimension.png`; exact prompt recorded in
  `docs/marketing/image-prompts.md`.
- Both language files written, `npm run build` passes, both pages generated.
- Every number in the article checked against the paper's result JSONs in the
  `code-world-models` repo (one error caught and fixed that way: the blind planner's
  return at the headline knob is 0.02, not 2e-5 — that figure belongs to the smaller
  knobs).
- LinkedIn body written by hand and pinned via the new `linkedinSummary` frontmatter
  field, so Gemini is not called for this post. Dry run composes to 2070/3000 chars
  with the preprint link, companion link, code link and hashtags appended.
- X thread drafted in `x-thread-infer-the-rule-in-one-dimension.md`, 11 tweets, each
  verified under 280 characters. No X automation exists — post it by hand.

## Order on the day

Merge to `main` (this publishes the blog, dev.to and LinkedIn automatically) → then
post the X thread by hand → then update the `code-world-models` README and paper 3's
`references.bib` with the real arXiv ID.
