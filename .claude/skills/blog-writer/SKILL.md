---
name: blog-writer
description: Write bilingual blog articles for the personal website and handle their publication workflow, including the article video and the native LinkedIn article. Use when creating, preparing, publishing, or scheduling a blog article, including when an experiment has just finished and the next step is "write it up". Handles the brief, EN/ES translations, frontmatter, figures, hero image and scheduling.
---

# Blog Article Writer

Create bilingual (English/Spanish) blog articles for javieraguilar.ai.

## Roles

- **Javier is the author.** The thesis, the story, the why and the voice are his. The article is
  written in his first person.
- **You are his writer and editor.** You gather what he has said, find the facts, put the words
  down, draw the figures and carry out every mechanical step of the skill on your own initiative.
  He reads a finished draft, not a questionnaire: you decide, write, and tell him what you
  decided.
- **The sources rank in this order:** what Javier has told you (in this session or earlier ones),
  then the data and the scripts that produce it, then the repo's docs. See
  [references/voice-and-sources.md](references/voice-and-sources.md).

Writing or reviewing a draft alone does not authorize publication.

## Workflow

### 0. Brief: gather before outlining

Javier usually starts with a short "ok, write it" at the end of an experiment, or with a dictated
paragraph. Everything else he expects you to know. Gather it first:

1. **His words.** Run
   `python3 .claude/skills/blog-writer/scripts/session_brief.py <slug> <topic terms>` (~10 s). It
   prints every message he sent in the sessions that touched the topic: typed, queued while you
   were working, and from before any compaction. Turn it into a short list of directives (what to
   keep, what confused him, the examples he values, the sources and URLs he gave) and keep it next
   to the draft.
2. **The thesis, in his words.** One sentence, quoting or closely paraphrasing his opening message
   ("la idea es principalmente hablar del concepto…"). The title and the description are written
   from this sentence. What he adds later (a remark sent while you work, a number from another
   session) refines a section of it; the title and the spine stay on the thesis.
3. **The inventory.** Every arm, model and condition in the experiment's data; which model plays
   which role (agent, judge, validator) and its family; the numbers of the previous article in the
   series that this one should be compared against.
4. **His published positions.** Grep `src/content/blog/en/` for the concepts of the thesis. Link the
   related articles, and make sure the new thesis builds on what he has already argued.
5. **What is on his site.** `src/data/projects.ts`, `src/content/blog/`, `/skills`, `/mentoring`:
   anything the article mentions that lives there gets linked, by name.
6. **Timing.** If the article answers a tweet, a paper or a current event, propose the first free
   date in `.github/publish-schedule.json`; otherwise the next slot of the cadence.

### 1. Outline, then straight on

Write the outline for yourself: the thesis line, the axes he named (each one appears in the text
and in the figures), the figure plan (see [references/figures.md](references/figures.md)). Then
write the draft in the same turn.

**Deciding.** Each open point gets settled in this order: his words (`session_brief.py`), the data,
this skill and its references, the precedent of his published articles. Take the decision, write
the draft with it, and list it in the hand-off under "Decisions I took", one line each, so he can
overturn any of them in one sentence. Examples that are decided, not asked: whether to name a
colleague (anonymise, as the voice rules say), whether to include extra numbers (if they serve
the thesis), the date (the schedule rules), what an unreadable branch contains (say you could not
read it and link it). He has already told you why things happened: use it.

A question goes to him only when the answer changes the thesis itself and nothing above settles
it; then ask that one question with your recommended answer, and still deliver the draft written
with that recommendation.

### 2. Draft

Branch from an up-to-date `main` (`blog/<slug>`), then write EN and ES following
[references/voice-and-sources.md](references/voice-and-sources.md).

### 3. Self-check before handing over

- **Numbers:** recompute every figure in the text with a script from the raw data, including the
  ones that came from another session.
- **Inventory:** every arm and model in the data appears in the text; every judge is named with its
  family.
- **Directives:** each item of the brief list is reflected in the draft.
- **Links:** every mention of his work and every real thing cited (tweet, paper, game, tool) is a
  link; slugs verified.
- **Thesis:** the title and the description state the thesis sentence of phase 0.
- **Axes:** every axis he named (cost, quality, speed…) is encoded in a figure: a 3D view, small
  multiples, or colour or size for the extra axis.
- **First mentions:** each dataset, model, product and tool is introduced (one clause of what it
  is) the first time it appears, including inside a summary sentence that lists several of them.
- **Detail:** implementation detail appears only where the story needs it to make its point.
- **Figures:** rendered, screenshotted and read in the browser (see `references/figures.md`).

### 4. Assets, done as part of the draft

Generate these with the draft and show them with it:

- the hero image through Codex, and the LinkedIn image choice
  ([references/images.md](references/images.md));
- the figure PNGs for Dev.to;
- `repoUrl` for any article with code, proposing to publish the repo when it is still private;
- the article video script, with the `article-video` skill of the AGILabs video studio plugin.

### 5. Render and hand over

```bash
npm run build   # validates frontmatter against the content schema and catches broken pages
npm run dev     # run in background; serves on http://localhost:4321
```

Give Javier both URLs, with the trailing slash (`astro.config` sets `trailingSlash: 'always'`, so
the bare path is a 404):

- `http://localhost:4321/en/blog/<slug>/`
- `http://localhost:4321/es/blog/<slug>/`

Check `ls dist/en/blog/ | grep <slug>` (and `es`) after the build, and show the hero inline (Read
the PNG), calling out any mangled text in it. The hand-off is the URLs, the hero, and "Decisions I
took". The article is done once he has reviewed the rendered pages.

When he sends corrections, change exactly what he points at and keep the rest as approved.

### 6. Publish or schedule

Follow [references/publishing.md](references/publishing.md): website schedule, video on the same
day, native LinkedIn article last, X texts.

## File Locations

- English: `src/content/blog/en/[slug].md`
- Spanish: `src/content/blog/es/[slug].md`
- Images: `public/blog/[image-name].png` (referenced as `/blog/[image-name].png`)
- Slugs are in English, both files, regardless of the article's language.

## Required Frontmatter Format

Both EN and ES files must include this exact frontmatter:

```yaml
---
title: "Article Title Here"
description: "A concise description for SEO and preview cards (1-2 sentences)."
pubDate: YYYY-MM-DD
tags: ["Tag1", "Tag2", "Tag3"]
lang: en  # or es
translationKey: article-slug
heroImage: "/blog/article-slug.png"
---
```

| Field | Required | Notes |
|-------|----------|-------|
| `title` | Yes | Translated per language |
| `description` | Yes | Translated, SEO-friendly, 1-2 sentences, first person |
| `pubDate` | Yes | Same date for both languages. Use the website publication date in `.github/publish-schedule.json`, or today for immediate publication; update it if the schedule moves. See `docs/blog-publishing.md` for backlog behavior. The native LinkedIn article has its own publication date and does not change this field. |
| `tags` | Yes | Translated (e.g., "AI" → "IA") |
| `lang` | Yes | Must be `en` or `es` |
| `translationKey` | Yes | Same value for EN/ES pair (kebab-case) |
| `heroImage` | Yes | Path to thumbnail (e.g., `/blog/my-article.png`). See `references/images.md`. |
| `linkedinImage` | No | Image for the LinkedIn auto-post; falls back to `heroImage`. See `references/images.md`. |
| `repoUrl` | For code | Adds `💻 Code: <url>` to the LinkedIn post (`buildPostText` in `scripts/linkedin/utils.js`), only when present. |
| `linkedinLinks` | No | `[{ label, url }]`, one `🔗 <label>: <url>` line each, for papers and preprints. |

Tag translations: AI → IA, Automation → Automatización, Development → Desarrollo,
Architecture → Arquitectura; Machine Learning stays.

## Checklist Before Publishing

- [ ] Brief list from `session_brief.py` reflected in the draft
- [ ] `npm run build` passes and both pages appear in `dist/en/blog/` and `dist/es/blog/`
- [ ] **Rendered pages reviewed by Javier** at `localhost:4321` (both languages, trailing slash)
- [ ] Every number recomputed from the data; every arm, model and judge of the inventory present
- [ ] **Figure sweep run against the outline** (see `references/figures.md`): every case of the trigger test has a figure or a one-sentence reason
- [ ] **Each figure pre-rendered to `public/blog/<slug>-fig-<n>.png`** (EN order) and the Dev.to swap dry-run shows no surviving `<svg`/`<style`
- [ ] **Every figure inspected rendered in a browser**, present in both EN and ES
- [ ] Both EN and ES files, matching `translationKey`, same `pubDate`, `lang` matching the folder, tags translated
- [ ] **`pubDate` matches the website publication schedule** (`.github/publish-schedule.json`, or today if merging manually)
- [ ] Hero image generated, shown to Javier, in `public/blog/`, set in both frontmatters, prompt recorded in `docs/marketing/image-prompts.md`
- [ ] **`linkedinImage` decided before publishing** (see `references/images.md`)
- [ ] **`repoUrl:` set in both EN and ES** when the article involves code
- [ ] **Every mention of Javier's own work is a link** with language-matched paths, and every real thing cited links to its source
- [ ] Article video planned for the same day (see `references/publishing.md`)

## Publication Completion

- [ ] For an authorized publication or scheduling task, the same agent has completed the native LinkedIn article workflow in [references/linkedin-articles.md](references/linkedin-articles.md), unless the user excluded that channel.
- [ ] Report the native article's verified URL or scheduled date and time separately from the automated feed post. If blocked, report the saved draft and the specific blocker; do not claim publication or scheduling succeeded.
