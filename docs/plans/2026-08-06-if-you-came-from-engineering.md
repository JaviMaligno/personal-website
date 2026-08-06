# If You Came From Engineering Implementation Plan

**Goal:** Finish the third mentoring-series article as a bilingual, illustrated, build-verified publication package for 2026-08-14.

**Architecture:** Keep the completed English article as the source of truth, add a native Spanish translation with locale-correct internal links, and derive a Spanish hero image from the existing English artwork while preserving its composition. Add a one-shot publication workflow matching the repository's established scheduled-merge pattern, but do not publish or push anything as part of implementation.

**Tech Stack:** Astro 5 content collections, Markdown frontmatter, PNG blog assets, GitHub Actions.

**Risks:** The prior article is scheduled from another branch and therefore its links are intentionally unresolved in this checkout; image-localization text must be checked visually; the scheduled workflow only becomes active once committed to `main` and the article branch exists on `origin`.

---

### Task 1: Spanish article

**Files:**
- Create: `src/content/blog/es/if-you-came-from-engineering.md`
- Reference: `src/content/blog/en/if-you-came-from-engineering.md`

**Step 1: Define structural checks**

Confirm both variants use the same `translationKey`, publication date, section hierarchy, and equivalent internal links.

**Step 2: Confirm the check fails before implementation**

Run: `Test-Path src/content/blog/es/if-you-came-from-engineering.md`

Expected: `False`.

**Step 3: Implement the translation**

Translate the article idiomatically into Spanish, preserve the author's first-person voice, localize `/en/` links to `/es/`, and reference a Spanish-specific hero image.

**Step 4: Verify content parity**

Run a local script that compares frontmatter keys, `translationKey`, `pubDate`, heading counts, and internal-link locale.

Expected: matching metadata and heading counts; no `/en/` links in the Spanish file.

### Task 2: Localized hero artwork

**Files:**
- Existing: `public/blog/if-you-came-from-engineering.png`
- Create: `public/blog/if-you-came-from-engineering-es.png`

**Step 1: Inspect the existing artwork**

Check its dimensions, composition, typography, and exact English copy.

**Step 2: Create the Spanish variant**

Use image editing in `text-localization` mode, changing only the copy and preserving the visual design.

**Step 3: Verify the result**

Inspect the generated image at full resolution and confirm legibility, absence of stray English text, and dimensions suitable for the blog card and LinkedIn.

Expected: a clean 2:1 Spanish counterpart with unchanged visual concept.

### Task 3: Scheduled publication definition

**Files:**
- Create: `.github/workflows/scheduled-publish-if-you-came-from-engineering.yml`
- Reference: `.github/workflows/scheduled-publish-if-youre-starting-from-zero.yml`

**Step 1: Copy the established one-shot workflow behavior**

Target `blog/came-from-engineering`, article path `src/content/blog/en/if-you-came-from-engineering.md`, and publication date `2026-08-14` with non-conflicting retry times.

**Step 2: Validate static references**

Run searches for the branch, slug, date, article path, and cron expressions.

Expected: all references consistently identify this article; no stale previous-article identifiers.

**Step 3: Record activation prerequisite**

The workflow must be committed to `main`, and the completed article branch must be pushed to `origin`, before the scheduled date.

### Task 4: Production verification

**Files:**
- Verify: all files above

**Step 1: Run tests**

Run: `npm test`

Expected: all repository tests pass.

**Step 2: Build the site**

Run: `npm run build`

Expected: Astro completes successfully and emits both localized article routes.

**Step 3: Browser-check both pages**

Serve the production build locally and inspect desktop and mobile layouts, hero images, headings, links, and footer CTA.

Expected: both pages render without layout regressions; locale switching and internal links are correct.

**Step 4: Review the final diff**

Run: `git diff --check` and `git status --short`.

Expected: no whitespace errors; only the intended article package and plan are changed.
