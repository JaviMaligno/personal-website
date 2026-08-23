# Publish checklist — "An LLM Can Infer the Rule You Forgot — in One Dimension"

The article is scheduled for **2026-08-30** via
`.github/workflows/scheduled-publish-infer-the-rule-in-one-dimension.yml`. Both
blockers below are resolved; what is left is the manual work after the merge.

The date is the first day free in *both* calendars. 08-24 was the obvious slot,
but `linkedin-scheduled-posts.yml` already holds `you-were-right-to-be-sceptical-en`
that day, and publishing here fires `linkedin-post.yml` too — two LinkedIn posts on
one day, against the alternation the schedule deliberately keeps. 08-25/27/29 carry
other articles, 08-26/28/31 carry legacy LinkedIn posts.

## Was blocking, now resolved

1. **arXiv ID — done.** The preprint was announced as
   [`arXiv:2608.17956`](https://arxiv.org/abs/2608.17956) (submitted 2026-08-18 as
   `submit/7965524`, primary cs.LG). Every `ARXIV_PENDING` / `arXiv:PENDING`
   placeholder was replaced with it in both language files (body, footer,
   `linkedinLinks`) and in `x-thread-infer-the-rule-in-one-dimension.md`.

2. **`pubDate` — done.** Set to `2026-08-30` in both languages, matching the cron
   date, so the blog index sorts it at the top rather than burying it under older
   posts.

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

The cron merges to `main`, which publishes the blog, Dev.to and LinkedIn
automatically. What still has to be done by hand, afterwards:

- Post the X thread (`x-thread-infer-the-rule-in-one-dimension.md`, 11 tweets) — no
  X automation exists.
- Update the `code-world-models` README and paper 3's `references.bib` with
  `arXiv:2608.17956`.
