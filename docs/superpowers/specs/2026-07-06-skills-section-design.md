# Skills Section + Public Reusable-Skills Repo — Design

**Date:** 2026-07-06
**Branch:** `feat/skills-section`
**Status:** Design — pending user review

## Purpose

Add a new "Skills" section to javieraguilar.ai that positions *skills* (encapsulated,
reusable agent workflows) as Javier's primary way of packaging capabilities — deliberately
placed **above** the MCP content to reflect that he considers them more important than MCP.

The section mixes:
- **Public skills** — tangible proof; link to a public GitHub repo.
- **Internal skills** — anonymized as capability/pattern cards (proof of real production
  experience) with no client names and no exposed code.

Scope of this work (chosen: **option 2**):
1. The web section on the site.
2. A public repo **v1** containing the 8 fully-generic skills + a README, so the section's
   CTA and "Public" badges link to something real from day one.

Follow-up (out of scope here, documented for later): extracting generic cores from the
🟡/🔒 skills (deploy, unified demo, microservice lifecycle, e2e-testing, responsible-ai-audit)
into the public repo as v2+.

## Skills inventory (source data)

Only skills authored by Javier are included. Third-party/marketplace/plugin skills
(`gws-*`, `browser-use`, `superpowers:*`, `vercel:*`, `slack:*`, `atlassian:*`, `Notion:*`,
`deep-research`, etc.) are excluded.

Legend: 🌍 generic/reusable · 🟡 generic core + company-specific layer · 🔒 internal

| Skill | Source location | Class | Site card | Repo v1 |
|---|---|---|---|---|
| demo-video | `~/.claude/skills` | 🌍 | ✅ Content & media | ✅ |
| spotify-upload | `~/.claude/skills` | 🌍 | ✅ Content & media | ✅ |
| tailor-cv | `personal-website/.claude/skills` | 🌍 | ✅ Content & media | ✅ |
| blog-writer | `personal-website/.claude/skills` | 🌍 | ✅ Content & media | ✅ |
| feature-dev | `oss-agent/.claude/skills` | 🌍 | ✅ Dev workflow | ✅ |
| code-review | `oss-agent/.claude/skills` | 🌍 | ✅ Dev workflow | ✅ |
| commit-pr | `oss-agent/.claude/skills` | 🌍 | ✅ Dev workflow | ✅ |
| playwright-cli | `sds_analysis/.claude/skills` | 🌍 | ✅ QA & testing | ✅ |
| deploy | `~/.claude/skills` (+ dup in sds_analysis) | 🔒 (core generic) | ✅ Dev workflow (anonymized) | ❌ v2 |
| microservice-lifecycle | fusion of `microservice-implementation` + `sds-service-generation` + `service-bug-fix` | 🔒 | ✅ Dev workflow (anonymized) | ❌ v2 |
| verify-test | `~/.claude/skills` (+ dup in sds_analysis) | 🔒 | ✅ QA & testing (anonymized) | ❌ v2 |
| verify-env | `verify/.claude/skills` | 🔒 | ✅ QA & testing (anonymized) | ❌ v2 |
| rfp-e2e-testing | `rfp-automation/.claude/skills` | 🟡 | ✅ QA & testing (anonymized) | ❌ v2 |
| responsible-ai-audit | `~/.claude/skills` | 🟡 | ✅ Governance (anonymized) | ❌ v2 |

Notes:
- `demo-record` (rfp-automation) is a variant of `demo-video`; represented by the single
  `demo-video` card. Not duplicated.
- `deploy` and `verify-test` have duplicate copies across repos; represented once.
- The `microservice-lifecycle` card merges three internal SDS skills into one pattern card
  to avoid over-listing internal specifics.

## Part 1 — Web section

### Placement & layout
- New component `src/components/Skills.astro`, inserted between `<Services />` and
  `<Projects />` in `src/pages/en/index.astro` and `src/pages/es/index.astro`.
  (MCP is a *category* inside `Projects`, so "above MCP" == before `Projects`.)
- Card grid styled like `Projects`, **grouped by capability** with a per-group subheading.
- Section footer CTA: "View all on GitHub →" / "Ver todas en GitHub →" linking to the
  public repo.

### Categories (4)
1. **Content & media** — demo-video, blog-writer, spotify-upload, tailor-cv
2. **Dev workflow** — feature-dev, code-review, commit-pr, deploy 🔒, microservice-lifecycle 🔒
3. **QA & testing** — verify-test 🔒, verify-env 🔒, playwright-cli, rfp-e2e-testing 🔒
4. **Governance** — responsible-ai-audit

### Card anatomy
- Skill name
- One-line description (pattern/capability, no client names)
- Badge: **Public** (links to repo) or **Internal / proprietary** (no link)
- 2–3 tags
- Internal cards describe *what the skill does* without naming SDS/LOCO/Simple KYC/Verify
  or exposing any code.

### Data layer & i18n (follows existing project pattern)
- `src/data/skills.ts`:
  ```ts
  export interface Skill {
    slug: string;
    key: string;                                              // i18n key under `skills.<key>`
    category: 'content' | 'devWorkflow' | 'qa' | 'governance';
    visibility: 'public' | 'internal';
    repoUrl: string | null;                                   // public → repo URL; internal → null
    tags: string[];
  }
  export const skills: Skill[] = [ /* 14 entries per table above */ ];
  ```
- Strings added to `src/i18n/en.json` and `src/i18n/es.json`:
  - `skills.section` → `title`, `subtitle`, `ctaLabel`
  - `skills.categories` → `content`, `devWorkflow`, `qa`, `governance`
  - `skills.badges` → `public`, `internal`
  - `skills.<key>` → `title`, `description` (both EN and ES) for each of the 14 skills

### Rendering logic
- `Skills.astro` reads `skills` from `skills.ts`, groups by `category` (fixed display order:
  content → devWorkflow → qa → governance), and renders a subheading + card grid per group.
- Public cards render as `<a href={repoUrl}>`; internal cards render as a non-link `<div>`
  with the "Internal / proprietary" badge.

## Part 2 — Public repo v1

### Repo
- **Name:** `agilabs-skills`.
- **Owner:** `JaviMaligno` (matches existing project GitHub links).
- **Visibility:** public.
- **License:** MIT.

### Contents (v1 = 8 fully-generic skills)
demo-video, spotify-upload, tailor-cv, blog-writer, feature-dev, code-review, commit-pr,
playwright-cli.

Each skill copied as a top-level directory containing its `SKILL.md` and supporting
`scripts/`/assets.

### Structure
```
agilabs-skills/
├── README.md              # what skills are, install path, per-skill index table
├── LICENSE
├── content-media/
│   ├── demo-video/
│   ├── spotify-upload/
│   ├── tailor-cv/
│   └── blog-writer/
├── dev-workflow/
│   ├── feature-dev/
│   ├── code-review/
│   └── commit-pr/
└── qa-testing/
    └── playwright-cli/
```
(Grouping mirrors the site categories; `blog-writer`/`tailor-cv` are personal-but-publishable.)

### Pre-publish safety scan (MANDATORY before making the repo public)
Publishing is an outward-facing, hard-to-reverse action. Before pushing, scan every copied
file for:
- Secrets / API keys / tokens / credentials.
- Internal URLs, hostnames, client names (SDS/LOCO/Simple KYC/Verify/RFP), private repo paths.
- Personal data beyond what Javier already publishes on the site.
Any hit → sanitize or drop the file. If a skill can't be cleaned without gutting it, defer it
to v2 and note it.

### Wiring back to the site
- `repoUrl` for the 8 published skills → deep-link to each skill's subdirectory, e.g.
  `https://github.com/JaviMaligno/agilabs-skills/tree/main/content-media/demo-video`.
- Section CTA → repo root (`https://github.com/JaviMaligno/agilabs-skills`).

## Testing / verification
- `npm run build` succeeds.
- Local dev (`npm run dev`): Skills section renders between Services and Projects, on both
  `/en/` and `/es/`, grouped correctly; public cards link out, internal cards don't; badges
  correct; responsive.
- Verify visual result in a real browser before pushing (per project convention).
- Repo: `README` renders, links resolve, safety scan clean.

## Out of scope (YAGNI)
- Per-skill detail pages on the site.
- Interactive filters/chips.
- Publishing any 🔒/🟡 skill before its generic core is extracted (that is repo v2+).
- Extracting generic cores (v2+ follow-up).

## Confirmed decisions
1. Public repo name: **`agilabs-skills`**.
2. License: **MIT**.
3. `repoUrl` **deep-links to each skill's subdirectory** within the repo (e.g.
   `.../agilabs-skills/tree/main/content-media/demo-video`). Section CTA still points to repo root.
