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

Publishing is scheduled with a **one-shot cron workflow per article**,
`.github/workflows/scheduled-publish-<slug>.yml`, that merges the article branch
into `main` on a given date so the workflows above fire on the resulting push.

Pattern (copy an existing one, e.g. `scheduled-publish-internal-context-leakage.yml`):

- `on.schedule.cron: '19 8 <DAY> <MONTH> *'` plus two later retries. See
  **"The cron runs late, it does not get dropped"** below before picking a time.
- Checks out `main` **with `secrets.PUBLISH_PAT`** (a user PAT). This is required:
  a push made with the default `GITHUB_TOKEN` does **not** re-trigger other
  workflows, so deploy/LinkedIn/Dev.to would silently not run.
- `git merge --no-ff origin/<article-branch>` then `git push origin main`.
- Guards with `git merge-base --is-ancestor` (no-op if already merged) and a
  `concurrency` group (never runs twice).
- Checks the branch exists first: if it is gone **and** the article is already in
  `main`, it exits 0 as a no-op (published by hand, branch deleted). It only errors
  when the branch is missing *and* the article is absent — i.e. a real typo.
- Opens a GitHub issue on success/failure as a notification.

### The cron runs late, it does not get dropped

Measured on 2026-07-25 over 20 consecutive days of this repo's daily 08:00 UTC
cron (`linkedin-scheduled-posts.yml`, which nobody ever triggers by hand): it
fired **every single day**, and **never on time** — between 1h21m and 4h02m late,
median ~2h13m. The `scheduled-publish` crons show the same shift: `09:19` UTC
consistently ran at ~11:20 UTC. This matches GitHub's own docs — *"the `schedule`
event can be delayed during periods of high loads […] High load times include the
start of every hour"* — and cannot be eliminated, only compensated.

**The lateness shrinks as the day goes on**, and so does its spread. Same repo,
three different cron slots, 07-21 … 07-25:

| Cron (UTC) | Mean lateness | Spread | n |
|---|---|---|---|
| 09:19 | 1h53m | 1h28m – 2h03m (±35m) | 5 |
| 11:37 | 1h28m | 1h24m – 1h33m (±5m) | 4 |
| 14:53 | 1h17m | 1h15m – 1h22m (±4m) | 4 |

Consequences to keep in mind:

- **Cron times are departure times, not arrival times.** Set the cron ~1-2h before
  you actually want the article out.
- **Scheduling earlier buys less than it looks, and costs predictability.** An
  early slot is queued during the European-morning peak, so it is both later *and*
  much noisier (±35m at 09:19 vs ±5m at 11:37). If you want a *predictable*
  publication hour, schedule **later**, not earlier.
- **Retries are cheap, so keep them close (~45m).** They do not help with the
  delay — only with a genuine dropped run, which has never been observed here. But
  a no-op run opens no issue and costs seconds, so a tight retry chain is free
  insurance: if a run is ever dropped, the next attempt is 45m behind instead of
  2h+.
- **As of 2026-07-25, no article had ever been published by its cron.** The first
  six (07-20 … 07-25) all went out via a manual `workflow_dispatch` or a manual
  merge, because the cron ran ~2h late and somebody always got there first. When
  that happens the late cron run is a harmless no-op (`already merged`).
- So the automatic path is **not yet validated end-to-end**. The merge step itself
  is proven (the manual dispatches published fine, deploy + Dev.to + LinkedIn
  included); what has never been observed is a cron firing *and* publishing.
- Two things that did break, both fixed: `PUBLISH_PAT` was missing on 07-20
  (`Input required and not supplied: token`), and the 07-23 workflow pointed at a
  branch name that did not exist.

Checklist when scheduling:

1. The workflow file must live on **`main`** (GitHub only runs `schedule`
   triggers from the default branch). Commit it to `main` directly — this does
   **not** publish the article, it only arms the future merge.
2. The **article branch must be pushed to `origin`** with the exact name the
   workflow's `git fetch origin <branch>` expects, or the scheduled merge fails.
   The workflow validates this with `git ls-remote` and fails with an explicit
   error listing the real `blog/*` branches — a typo here previously surfaced only
   on publication day as an opaque `couldn't find remote ref` (2026-07-23).
3. Pick a **free date** — check the crons of the other `scheduled-publish-*.yml`
   files first (one article per day).
4. **Set the article's `pubDate` to the cron date, in both EN and ES.** The blog
   index sorts *and displays* by `pubDate` (`src/pages/*/blog/index.astro`), not by
   the merge date, so a draft date left in the frontmatter makes the article show
   up under an older date — and, if it ties with older posts, buried below them.
   This is what happened to the 07-22/07-23/07-24 publications (fixed in
   `fix/blog-pubdates`). If the schedule is later moved, move the `pubDate` too.

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
