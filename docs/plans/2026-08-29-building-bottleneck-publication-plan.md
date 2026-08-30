# Building Is No Longer the Bottleneck Publication Plan

**Goal:** Schedule the bilingual article for a conflict-free date with enough separation from the official Prompt Scripter launch.

**Architecture:** Keep the article and its hero on a dedicated `blog/*` branch created from current `main`. Arm publication separately by committing a one-shot scheduled merge workflow to `main`; the workflow merges the article branch on the chosen date, which triggers deploy, Dev.to, and LinkedIn.

**Tech Stack:** Git worktrees, GitHub Actions cron, Astro content collections, existing LinkedIn publication automation.

**Risks:** Merging the article into `main` publishes immediately; the workflow must reference the exact pushed branch; `pubDate` must match the cron date; the date must be free in both article workflows and the legacy LinkedIn schedule.

---

### Task 1: Select the publication date

**Files:**
- Inspect: `.github/workflows/scheduled-publish-*.yml`
- Inspect: `scripts/linkedin/posts/schedule.json`

**Step 1:** Fetch current `origin/main` and list future publication dates from both calendars.

**Step 2:** Reserve a date that leaves several clear days after the expected Prompt Scripter launch activity.

**Expected:** One date is absent from both calendars and has sufficient spacing from existing posts.

### Task 2: Create and verify the article branch

**Files:**
- Create: `src/content/blog/en/building-is-no-longer-the-bottleneck.md`
- Create: `src/content/blog/es/building-is-no-longer-the-bottleneck.md`
- Create: `public/blog/building-is-no-longer-the-bottleneck.png`
- Modify: `docs/marketing/image-prompts.md`

**Step 1:** Create an isolated worktree and `blog/building-is-no-longer-the-bottleneck` from current `origin/main`.

**Step 2:** Copy only the reviewed article assets and prompt documentation into it.

**Step 3:** Set both `pubDate` values to the selected date and confirm the Prompt Scripter link exists in both frontmatters.

**Step 4:** Run `npm run build`.

**Expected:** Exit 0; both localized routes are generated.

**Step 5:** Commit and push the exact article branch to `origin`.

### Task 3: Arm the scheduled merge on main

**Files:**
- Create: `.github/workflows/scheduled-publish-building-is-no-longer-the-bottleneck.yml`

**Step 1:** Create an isolated `main` worktree from current `origin/main`.

**Step 2:** Copy the established one-shot workflow pattern and substitute the selected date, article path, branch, labels, and notification text.

**Step 3:** Validate the YAML and confirm its branch/path strings match the pushed article branch.

**Step 4:** Commit and push the workflow to `origin/main`.

**Expected:** Only the scheduler reaches `main`; the article remains absent until the cron merge.

### Task 4: Verify remote state

**Step 1:** Confirm the article branch exists remotely.

**Step 2:** Confirm the workflow exists on `origin/main` and the article does not.

**Step 3:** Report the selected date, cron times, branch, and outstanding Prompt Scripter launch dependency.
