# PR #25 Article Review Implementation Plan

**Goal:** Finish the two bilingual articles in PR #25, verify their claims and visual rendering locally, and leave publication scheduling in a safe, explicit state.

**Architecture:** Keep EN/ES pairs aligned through matching frontmatter, links, claims, and assets. Add one shared hero image per article under `public/blog/`, remove unlicensed scratch media, and validate the Astro output in both languages. Treat publication as a separate release operation because both articles currently share one branch and cannot be merged on different days as-is.

**Tech Stack:** Astro 5, Markdown content collections, static assets, Node test runner, npm, local browser automation.

**Risks:** The mathematical counterexample is a very recent public claim; image rights are unclear; model/product details are time-sensitive; merging the current combined branch would publish both articles simultaneously.

---

### Task 1: Correct and source-check both bilingual article pairs

**Files:**
- Modify: `src/content/blog/en/death-of-prompt-engineering.md`
- Modify: `src/content/blog/es/death-of-prompt-engineering.md`
- Modify: `src/content/blog/en/routing-engineering.md`
- Modify: `src/content/blog/es/routing-engineering.md`

**Step 1: Record primary-source findings**

Verify the DGG announcement and transcript, Cursor swarm costs, Cursor Router claims, RouteLLM and FrugalGPT figures, GPT-5.6 tiers/effort, and Claude effort levels against public primary sources.

Expected: each numeric or product-specific claim has direct support; uncertainty around the new mathematical result is stated rather than hidden.

**Step 2: Apply minimal synchronized edits**

Correct temporal language, unsupported certainty, model effort enums, and any wording that differs between EN and ES. Add direct links where they help readers inspect the evidence.

Expected: EN and ES make the same factual claims and preserve the original two-part thesis.

**Step 3: Check cross-language parity**

Run:

```powershell
rg -n "2026|58|60|1,339|10,565|411|9,373|85%|95%|98%|30.?50%|effort|max|xhigh" src/content/blog/en/death-of-prompt-engineering.md src/content/blog/es/death-of-prompt-engineering.md src/content/blog/en/routing-engineering.md src/content/blog/es/routing-engineering.md
```

Expected: matching facts and qualifications appear in both languages.

### Task 2: Replace the meme with an original embedded illustration and remove the scratch note

**Files:**
- Delete: `public/blog/conjecture-disproved-meme.jpg`
- Create: `public/blog/prompt-breakthrough-loop.png`
- Delete: `docs/egress-blocked-hosts.md`
- Modify: `src/content/blog/en/death-of-prompt-engineering.md`
- Modify: `src/content/blog/es/death-of-prompt-engineering.md`

**Step 1: Replace the unlicensed embedded meme**

Generate and embed an original editorial illustration of increasingly blunt prompts driving a research loop. Do not reproduce the third-party faces, tweet screenshot, layout, or other protected expression; keep source links for the underlying public posts.

Expected: both languages include the same locally hosted original image and the argument remains visually clear without shipping third-party artwork.

**Step 2: Remove the temporary infrastructure note**

Delete `docs/egress-blocked-hosts.md` after its verification checklist has been completed.

Expected: neither temporary file appears in `git diff --name-status`.

### Task 3: Generate and integrate two original hero images

**Files:**
- Create: `public/blog/death-of-prompt-engineering.png`
- Create: `public/blog/routing-engineering.png`

**Step 1: Generate the prompt-engineering hero**

Create an original landscape editorial illustration of rough human language dissolving into a structured agent loop. Avoid logos, copied meme composition, text, and watermarks.

**Step 2: Generate the routing-engineering hero**

Create a matching landscape editorial illustration of one intent being routed through model/effort paths with visibly different cost and complexity. Avoid logos, UI text, and watermarks.

**Step 3: Validate the files**

Run:

```powershell
Get-ChildItem public/blog/death-of-prompt-engineering.png,public/blog/routing-engineering.png | Select-Object Name,Length
```

Expected: both PNG files exist, are non-empty, and match the frontmatter paths.

### Task 4: Build and visually review all four pages locally

**Files:**
- Verify: `src/content/blog/en/death-of-prompt-engineering.md`
- Verify: `src/content/blog/es/death-of-prompt-engineering.md`
- Verify: `src/content/blog/en/routing-engineering.md`
- Verify: `src/content/blog/es/routing-engineering.md`

**Step 1: Run automated verification**

Run:

```powershell
npm test
npm run build
```

Expected: both commands exit 0 with no test or build failures.

**Step 2: Start the local frontend**

Run:

```powershell
npm run dev -- --host 127.0.0.1
```

Expected: Astro reports a local HTTP URL.

**Step 3: Inspect desktop rendering**

Open all four routes in the local browser and inspect titles, hero images, prose flow, blockquotes, inline code, links, attribution, and the EN/ES switch.

Expected: no missing assets, broken internal links, encoding errors, overflow, or unexpected console errors.

**Step 4: Capture review screenshots**

Capture representative screenshots of both article designs after the final reload.

Expected: the screenshots show the final local rendering and are included in the handoff.

### Task 5: Leave publication scheduling safe and explicit

**Files:**
- Review: `docs/blog-publishing.md`
- Review: `.github/workflows/scheduled-publish-*.yml`

**Step 1: Confirm the structural constraint**

Verify that PR #25 contains both articles on a single branch and that merge-to-main publishes all new English articles immediately.

Expected: no scheduling workflow is added to the combined PR branch.

**Step 2: Define the release split**

Prepare a handoff recommending two publication branches, one containing the first article for 2026-07-25 and one based on the first plus the second for 2026-07-26, with their one-shot workflows committed to `main` separately.

Expected: no merge, push, or publication occurs during this review without explicit authorization.
