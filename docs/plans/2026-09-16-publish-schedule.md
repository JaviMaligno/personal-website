# Pending publication schedule implementation plan

**Goal:** Merge independent schedule entries automatically and retain only unpublished articles.

**Architecture:** A JSON-aware Git merge driver reconciles entries by slug against the common ancestor. Publication and rehearsal prune entries whose article exists in the merged tree before committing; genuine disagreements fail rather than choosing a side.

**Tech Stack:** Node.js built-ins, Git merge drivers, GitHub Actions.

**Risks:** Old branches resurrecting completed entries; duplicate dates; delete/edit disagreements; invalid JSON; a cleanup commit bypassing the daily publication guard; a rehearsal reporting success despite blockers.

---

### Task 1: Merge and prune behavior

Create `scripts/publish/schedule.test.mjs` and run `node --test scripts/publish/schedule.test.mjs` to demonstrate missing behavior. Cover independent insertions, key ordering, identical edits, one-sided edits/deletions, incompatible edits, date collisions, published entries, empty queues, and real Git merges. Implement `schedule.mjs`, `merge-schedule.mjs`, and `prune-schedule.mjs`. Re-run until all pass.

### Task 2: Workflow integration and retry semantics

Configure `.gitattributes` and both publication/rehearsal workflows to use the driver. Merge without committing, prune and validate, then create the existing publication commit. Preserve forced retry no-op behavior after an entry has been pruned, with CLI regression tests in `select-due-article.test.mjs`. Ensure canary failures are visibly red after reporting.

### Task 3: Migration and verification

Prune `.github/publish-schedule.json` once against main; document the pending-only contract and local driver setup in `docs/blog-publishing.md`. Run `node --test scripts/publish/*.test.mjs`, the full built-in test suite, and rehearse real pending branches in an isolated checkout without pushing article merges. Review the diff for deletion/resurrection and failure rollback. Integrate the verified maintenance change and run the canary; do not publish future articles.
