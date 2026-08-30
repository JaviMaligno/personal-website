# Blog publishing & scheduling

How a bilingual blog article goes from a branch to live — and how automatic
distribution (Vercel deploy, Dev.to, LinkedIn) is wired. Read this before
scheduling or publishing an article.

## The core rule: merge to `main` = publish (irreversible)

Each article lives on its own branch, **created from an up-to-date `main`**.
Merging that branch into `main` is the publish action: the push to `main`
triggers, in parallel, three independent workflows:

| Workflow | Trigger | What it does |
|---|---|---|
| `.github/workflows/deploy.yml` | push to `main` | Production deploy to Vercel |
| `.github/workflows/devto-post.yml` | push to `main`, path `src/content/blog/en/**/*.md` | Cross-posts the new EN article to Dev.to |
| `.github/workflows/linkedin-post.yml` | push to `main`, path `src/content/blog/en/**/*.md` | Auto-generates and publishes a LinkedIn post |

There is no un-publish. Stagger articles **one per day** — never merge two on the
same day.

## Scheduling a publication

Publishing is driven by **one manifest and one daily workflow**:

- `.github/publish-schedule.json` — the schedule. One entry per pending article:
  `slug`, `branch`, `article` (the EN path) and `date`.
- `.github/workflows/scheduled-publish.yml` — runs four times a day, merges the
  oldest article that is **due and not yet in `main`**, and pushes, so the
  deploy/Dev.to/LinkedIn workflows fire on that push.

To schedule an article, add an entry to the manifest and commit it to `main`.
That is the whole procedure — no new workflow file per article.

Selection lives in `scripts/publish/select-due-article.mjs` as a pure function,
covered by `scripts/publish/select-due-article.test.mjs` (`npm test`). That
matters: the previous design could only be tested by waiting for a specific
calendar date to arrive.

### Due, not "today" — and why that is the whole point

The workflow publishes everything with `date <= today` that is not yet in `main`,
oldest first. A date-pinned cron that misses its day is simply lost; this one
picks the article up the next day, and the day after, until it is published.

The guards it keeps:

- **One article per day.** If `main` already carries a `Publish: …` merge dated
  today, the run stops. A backlog drains one per day rather than putting two
  LinkedIn posts out at once.
- **`main` is the source of truth for "published".** The check is whether the
  article file exists, not a flag in the manifest — a flag can drift, the file
  cannot. Re-running is therefore always safe.
- **`blockIfMatches`** (optional, per entry): a regexp that must *not* appear in
  the article on its branch. Used for placeholders that must never ship — e.g.
  `being-wrong-can-be-free` and `the-bug-nobody-can-reach` cite paper 3's
  preprint and carry the literal `XXXX.XXXXX` until its arXiv ID is substituted.
  A match fails the run and opens an issue instead of publishing.
- **Branch deletion is conditional.** The branch is deleted only when it carries
  nothing that is not already in `main`. On 2026-08-30 `blog/what-has-already-happened`
  — an article published on 08-13 — turned out to hold 6,759 lines of research
  documentation committed after publication. Unconditional deletion would have
  thrown that away.
- **The push uses `secrets.PUBLISH_PAT`**, a user PAT. A push made with the
  default `GITHUB_TOKEN` does **not** re-trigger other workflows, so the article
  would merge without being distributed anywhere.

`workflow_dispatch` takes an optional `slug` to publish one article immediately,
skipping the date but none of the other guards.

### The cron runs late — and can be dropped entirely

Measured on 2026-07-25 over 20 consecutive days of this repo's daily 08:00 UTC
cron (`linkedin-scheduled-posts.yml`, which nobody ever triggers by hand): it
fired **every single day**, and **never on time** — between 1h21m and 4h02m late,
median ~2h13m. The `scheduled-publish` crons showed the same shift: `09:19` UTC
consistently ran at ~11:20 UTC. This matches GitHub's own docs — *"the `schedule`
event can be delayed during periods of high loads […] High load times include the
start of every hour"*.

**On 2026-08-30 that 20-day sample was falsified.** This document previously
concluded "it does not get dropped… a genuine dropped run, which has never been
observed here". That day `scheduled-publish-infer-the-rule-in-one-dimension.yml`
ended with **0 runs**: all four of its departures (08:19, 09:07, 09:59, 13:53
UTC) were dropped, not delayed. The workflow was `active` and had been on `main`
since 08-23. The article was published by hand, ~4h late.

So: the queue is late *most* of the time and absent *some* of the time, and a
schedule that only fires on one calendar date has no answer to the second case.
That is why the current design keys on **due**, not on today.

The lateness data still holds, and still shapes the cron slots. **The lateness
shrinks as the day goes on**, and so does its spread. Same repo, three different
cron slots, 07-21 … 07-25:

| Cron (UTC) | Mean lateness | Spread | n |
|---|---|---|---|
| 09:19 | 1h53m | 1h28m – 2h03m (±35m) | 5 |
| 11:37 | 1h28m | 1h24m – 1h33m (±5m) | 4 |
| 14:53 | 1h17m | 1h15m – 1h22m (±4m) | 4 |

Consequences to keep in mind:

- **Cron times are departure times, not arrival times.** The first slot is set
  ~1-2h before the article is actually wanted out.
- **Scheduling earlier buys less than it looks, and costs predictability.** An
  early slot is queued during the European-morning peak, so it is both later *and*
  much noisier (±35m at 09:19 vs ±5m at 11:37).
- **Retries are spread across the day, not bunched.** The old per-article files
  used a ~45m chain, on the theory that only delay mattered. Once a whole day's
  worth of departures can vanish together, four attempts inside 45 minutes all
  fall in the same hole; the current slots sit hours apart (08:19, 11:07, 13:53,
  16:41), and the daily re-run is the real backstop.

### The `image-prompts.md` conflict, and why merges no longer break on it

Every article branch appends its hero-image prompt to the same file,
`docs/marketing/image-prompts.md`. Branches cut before other articles landed
insert at the same point, and git aborts the merge — even though the changes are
pure insertions with nothing in genuine disagreement.

This broke publications repeatedly and was resolved by hand each time; the commit
messages still carry the scar (`wheres-the-ball-3`, `bring-your-app-to-the-agent`,
`writing-a-paper-with-ai`, all with `# Conflicts: docs/marketing/image-prompts.md`).
On 2026-08-30, four of the seven pending articles were measured (`git merge-tree`)
to be heading for the same failure.

`.gitattributes` now declares:

```
docs/marketing/image-prompts.md merge=union
```

The `union` merge driver keeps both sides and produces no conflict. The trade-off
is that the order of the blocks is left to git for branches that insert near the
top of the file — acceptable for a reference archive.

Checklist when scheduling:

1. Add the entry to `.github/publish-schedule.json` on **`main`**. This does
   **not** publish the article; it arms the future merge.
2. The **article branch must be pushed to `origin`** under exactly the `branch`
   name in the entry. The workflow validates this with `git ls-remote` and fails
   with an explicit error listing the real `blog/*` branches — a typo here
   previously surfaced only on publication day as an opaque `couldn't find remote
   ref` (2026-07-23).
3. Pick a **free date** — and free means free in **two** calendars:
   - the other `date` values in `.github/publish-schedule.json` (one article per day);
   - the dates in `scripts/linkedin/posts/schedule.json`, read daily by
     `linkedin-scheduled-posts.yml`. That workflow is legacy for *articles*, but it
     is very much alive. Publishing an article also fires `linkedin-post.yml`, so a
     date carrying a `schedule.json` entry puts **two LinkedIn posts out the same
     day**, which the alternating pattern of those dates exists to avoid.

   Both collisions are now enforced by `npm test`, so a clash fails in CI instead
   of on publication day. It went unnoticed once by hand: on 2026-08-23,
   `infer-the-rule-in-one-dimension` was nearly scheduled for 08-24, which looked
   free against the article crons alone while `schedule.json` held
   `you-were-right-to-be-sceptical-en` that day.
4. **Set the article's `pubDate` to the scheduled date, in both EN and ES.** The
   blog index sorts *and displays* by `pubDate` (`src/pages/*/blog/index.astro`),
   not by the merge date, so a draft date left in the frontmatter makes the
   article show up under an older date — and, if it ties with older posts, buried
   below them. This is what happened to the 07-22/07-23/07-24 publications (fixed
   in `fix/blog-pubdates`). If the schedule is later moved, move the `pubDate` too.

   Note the one case this does not cover: an article recovered from a backlog is
   merged *after* its `date`, so its `pubDate` will read earlier than the day it
   actually went live. That is the intended trade — the alternative is silence.


## Retrying a failed cross-post

**You get told when this happens.** `devto-post.yml` and `linkedin-post.yml` each
open a GitHub issue on failure (`❌ Dev.to cross-post FAILED` / `❌ LinkedIn
cross-post FAILED`) carrying the article path, the run URL and the retry
instructions. This matters because an article only reaches `main` once: the push
is already done, so nothing retries by itself and a red run would otherwise sit
unnoticed among the green ones.

Note the asymmetry in what you can do about it: Dev.to has `workflow_dispatch`
and can be replayed from `main` (see below), while LinkedIn is push-only — there
the options are re-running the failed run or posting by hand.

The three publish workflows are independent, so one can fail while the others
succeed — on 2026-07-28 `expensive-form` went out to Vercel and LinkedIn but
Dev.to failed with `Failed to fetch articles (401)`: the `DEVTO_API_KEY` secret
held a key Dev.to no longer accepted (it had worked the day before). The 401
comes from the *check-for-duplicates* `GET` that runs before the `POST`, so a
failure there leaves nothing half-published on Dev.to.

`devto-post.yml` has a **`workflow_dispatch`** trigger for exactly this: run it
from the Actions tab with `post_path` set to the EN article
(`src/content/blog/en/<slug>.md`) and it publishes that one article, without
needing to re-run the original push. Fix the cause first (usually: regenerate
the key at https://dev.to/settings/extensions and update the repo secret).

Re-running is safe. `publish-to-devto.js` looks the article up by
`canonical_url` and issues a `PUT` when it already exists, so a double run
updates rather than duplicates.

## LinkedIn auto-post (the real mechanism)

The post that goes out on publish is generated by **`linkedin-post.yml`**
(push-triggered), not by any pre-written file. Flow:

1. `scripts/linkedin/detect-new-posts.js` finds the new EN article in the push.
2. `scripts/linkedin/generate-summary.js` writes a 2–3 paragraph summary with
   Gemini (URLs and hashtags are deliberately excluded from the summary).
3. `buildPostText` (`scripts/linkedin/utils.js`, unit-tested in
   `utils.test.mjs`) composes the final text:

   ```
   <Gemini summary>

   🔗 <label>: <url>      ← one line per frontmatter linkedinLinks entry
   💻 Code: <repoUrl>     ← only if frontmatter.repoUrl is set
   📖 Read more: <article URL>

   <#hashtags from tags>
   ```
4. Image = `linkedinImage` or, failing that, `heroImage`.

> **Note — two separate LinkedIn workflows.** `linkedin-post.yml` (push-triggered,
> above) is the one that publishes new articles. `linkedin-scheduled-posts.yml`
> reads `scripts/linkedin/posts/schedule.json` and is a **separate, legacy** path
> not used by recent articles. Don't confuse them.

### Getting extra links into the post

The only links guaranteed in the auto-post are the article URL and (via
`repoUrl`) the code repo. To add others (product page, preprint, fork…), use the
optional **`linkedinLinks`** frontmatter field — a list of `{ label, url }`,
each rendered as a `🔗 <label>: <url>` line with a generic 🔗 emoji:

```yaml
linkedinLinks:
  - label: "Connect your AI"
    url: "https://getvitamind.app/connect"
```

The field is declared in the blog schema (`src/content/config.ts`) and consumed
by `publish-to-linkedin.js`. It's optional and additive — articles without it are
unaffected.

## Related

- Article authoring, frontmatter, hero images: `.claude/skills/blog-writer/`
- Hero-image prompts archive: `docs/marketing/image-prompts.md`
