# Publish checklist — "Being Wrong Can Be Free — Until the Planner Can Reach It"

Paper 3's companion article. Scheduled for **2026-09-02** via
`.github/workflows/scheduled-publish-being-wrong-can-be-free.yml`, which
**refuses to publish while the arXiv placeholder is still in the files** (see
"The one blocker" below) — so an un-filled ID means no publication and a
failure issue, never a broken post.

The date is the first day free in *both* calendars. 08-29 (`nobody-will-check-behind-you`),
08-30 (paper 2's `infer-the-rule-in-one-dimension`) and 09-01 (`stop-being-the-cable`)
carry articles; 08-28, 08-31 and 09-03 carry standalone LinkedIn posts in
`scripts/linkedin/posts/schedule.json`, and publishing here fires
`linkedin-post.yml` too, which would put two posts out on one day.

## The blocker, now resolved

**The arXiv ID — done.** Paper 3 was announced as
[`arXiv:2608.28541`](https://arxiv.org/abs/2608.28541) (submitted 2026-08-28 as
`submit/8006768`, primary cs.LG, cross-list cs.AI). Every `XXXX.XXXXX`
placeholder was replaced with it in both language files and in the X thread, so
the scheduled-publish workflow's guard now passes. The announced v1 is the
corrected source: the `tab:ndim` cell fixed after the first submission is in
the published PDF, verified against its own text stream.

## Already done

- Both language files written, frontmatter validated against the content
  collection schema (all keys known, both languages same `translationKey`,
  `pubDate` 2026-09-02 matching the cron).
- `linkedinSummary` written by hand and pinned in the EN frontmatter, so
  Gemini is not called for this post. This required the same 5-line
  `src/content/config.ts` schema addition that paper 2's branch carries; the
  two additions are byte-identical, so the 08-30 merge and this one do not
  conflict.
- Hero image at `public/blog/being-wrong-can-be-free.png`, 1020x510 exact,
  reviewed. Deterministic source at
  `docs/marketing/hero-sources/being-wrong-can-be-free.py`; entry and a
  fallback `image_gen` prompt recorded in `docs/marketing/image-prompts.md`.
- X thread drafted in `x-thread-being-wrong-can-be-free.md`, 13 tweets, each
  verified under 280 characters. No X automation exists — post it by hand.
- Every number in the article checked against the result JSONs in the
  `code-world-models` repo. **Two errors caught that way:**
  - The first draft compared the scripted blind model's closed-ring play cost
    (0.999) against the *synthesis arm's* hidden-channel value (1.116) and
    called them identical. They are not the same series. The article now uses
    one series per comparison and states the hidden-channel contrast at equal
    gamma: 0.029 facing vs 1.116 hidden at gamma = 0.6, with 1.116 also being
    the closed band's own value to four decimals.
  - The article repeated the paper's claim of "censored zeros at n = 5 and 6"
    for ShellField contact rarity. The JSON records 1 contact in 600 rollouts
    at n = 6; only n = 5 is a real zero. **This was an error in the paper**,
    fixed there in the same session with a new numbers audit
    (`scripts/audit_paper3_numbers.py`) and logged in
    `docs/paper3/CHANGELOG-corrections.md`.

## Not done, deliberately

- **`linkedinImage`: left unset.** The hero already *is* the article's central
  figure with both play costs in large type, so the fallback
  (`linkedinImage || heroImage`) is the right feed image; an exported SVG would
  be a weaker duplicate.
- **`npm run build` not run locally**: this checkout has no `node_modules` and
  installing them on that machine competes with the research runs. The
  frontmatter was validated against the zod schema by hand instead, and Vercel
  builds the branch preview on push.

## Order on the day

The cron merges to `main`, which publishes the blog, Dev.to and LinkedIn
automatically. By hand afterwards:

- Post the X thread (13 tweets), with the real arXiv ID substituted.
- Check the two internal links resolve: the article links to
  `/en/blog/infer-the-rule-in-one-dimension` (and its `/es/` twin), which
  publishes 08-30. If paper 2's publication slipped, those links 404.
