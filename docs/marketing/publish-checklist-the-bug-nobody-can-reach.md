# Publish checklist — "The Bug Nobody Can Reach"

The digestible companion to `being-wrong-can-be-free`: one idea, ~1400 words,
no Betti numbers, no `play_cost` jargon, written to answer "what is the paper
about?" on its own. Scheduled for **2026-09-17** via
`.github/workflows/scheduled-publish-the-bug-nobody-can-reach.yml`, which
**refuses to publish while the arXiv placeholder is still in the files**.

## Order matters here

It publishes **after** the long post (2026-09-14), not before, and that is
deliberate: the opening paragraph links `/en/blog/being-wrong-can-be-free` as
"the same story with the numbers", so publishing first would ship two dead
links. That rule is why this article moved when the long one did: both were
pushed back from 09-02/09-05 when the postponed VitaminD launch landed on the
2nd, and they kept their three-day gap.

Calendar: the article queue is full from 09-04 to 09-11, and 09-03 carries a
standalone LinkedIn post (publishing an article fires `linkedin-post.yml`, so
that day would go out with two), which leaves 09-12 as the first free day in
both calendars and 09-14/09-17 as the first free weekdays.

## The blocker, now resolved

**The arXiv ID — done.** Paper 3 was announced as
[`arXiv:2608.28541`](https://arxiv.org/abs/2608.28541) (submitted 2026-08-28 as
`submit/8006768`, primary cs.LG, cross-list cs.AI). Every `XXXX.XXXXX`
placeholder was replaced with it in both language files and in the X thread, so
the scheduled-publish workflow's guard now passes. The announced v1 is the
corrected source: the `tab:ndim` cell fixed after the first submission is in
the published PDF, verified against its own text stream.

## Already done

- Both languages written and validated against the content collection schema.
  `linkedinSummary` hand-written in the EN frontmatter (this branch carries the
  same byte-identical `config.ts` schema line as the two sibling branches, so
  the merges do not conflict).
- Hero at `public/blog/the-bug-nobody-can-reach.png`, 1020x510 exact,
  deterministic source in `docs/marketing/hero-sources/`, entry in
  `image-prompts.md`. It uses the doughnut pair (0.019 / 0.898) so it does not
  duplicate the long post's hero, which uses the ring pair (0.029 / 1.116).
- X thread drafted, 8 tweets, each verified under 280 characters.
- Every number checked against the result JSONs in `code-world-models`
  (`tubefield_mechanism.json` for 0.019 / 0.898,
  `continuous_ring2d_open_sweep_summary.json` for 0.029 / 1.116).

## One thing worth knowing if you edit the text

The article deliberately keeps **two different wrong models** apart, and an
edit that blurs them makes it wrong:

- the **filled-disc** model invents a forbidden region where nothing can go —
  that one is uncatchable *and* free (the theorem);
- the **blind** model does not know the fence exists at all — that one costs
  1.116 when the fence sits on the route, and 0.029 when a gap in front lets
  the route through.

The first draft of this post merged them into "the same mistake, moved", which
reads well and is false: what moves between 1.116 and 0.029 is the world, not
the model's error. The section is now titled "The same blindness, a different
world" for that reason.

## Order on the day

The cron merges to `main`, which publishes blog, Dev.to and LinkedIn
automatically. By hand afterwards:

- Post the 8-tweet X thread with the real arXiv ID.
- Check the two internal links to `being-wrong-can-be-free` resolve (they will,
  if the long post published on 09-14 as scheduled).
