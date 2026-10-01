# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

This is a personal portfolio website for Javier Aguilar, an AI Agent Architect. The site has two audiences:

### Main Site (/)
Technical audience - CTOs, engineering leads, AI teams. Markets:
- **AI Agent Pipelines**: Multi-agent orchestration for research, coding, and review workflows
- **MCP Development**: Custom Model Context Protocol servers
- **Compliance Automation**: Risk assessment and classification systems

The goal is to position the brand ("AGILabs") as a specialized AI orchestration consultancy, showcasing architecture diagrams and demos rather than code.

### Business Landing (/business)
Non-technical audience - SME owners, business managers. Markets:
- **Process Automation**: Eliminating repetitive manual tasks
- **Data Analysis**: Insights without complex spreadsheets
- **Document Generation**: Automatic reports and documentation

This is a validation landing page for testing the SME market. See `docs/business-landing-strategy.md` for details.

## Commands

```bash
npm run dev      # Start development server (default: localhost:4321)
npm run build    # Build for production (output: dist/)
npm run preview  # Preview production build locally
npm test         # Node test runner over scripts/**/*.test.mjs (incl. publish-schedule date collisions)
npm run test:pages     # build + rendered-page checks (scripts/publications/rendered-page.check.mjs)
npm run test:linkedin  # LinkedIn script checks (also test:detect, test:summary, test:gemini)
```

Visual/CSS changes (layout, styling, KaTeX formula rendering) must be verified in a
real browser before committing: `npm run dev` → open the page → screenshot → confirm.
A clean build or grepping the HTML is not enough — broken KaTeX rendering has reached
production that way.

## Architecture

### Tech Stack
- **Astro 5.x** - Static site generator with component islands
- **Mermaid.js** - Architecture diagrams rendered client-side
- **TypeScript** - Strict mode via Astro's tsconfig

### Project Structure
```
src/
├── data/
│   └── projects.ts        # Centralized project definitions
├── diagrams/
│   └── index.ts           # Mermaid diagram registry
├── i18n/
│   ├── index.ts           # Translation utilities
│   ├── en.json            # English strings
│   └── es.json            # Spanish strings
├── layouts/
│   ├── Layout.astro       # Base layout with header/footer
│   └── ProjectLayout.astro # Layout for project detail pages
├── pages/
│   ├── index.astro        # Redirect to /en/
│   ├── en/
│   │   ├── index.astro    # English homepage
│   │   ├── business/index.astro  # Business landing (EN)
│   │   └── projects/[slug].astro  # Dynamic project pages (EN)
│   └── es/
│       ├── index.astro    # Spanish homepage
│       ├── business/index.astro  # Business landing (ES)
│       └── projects/[slug].astro  # Dynamic project pages (ES)
├── components/
│   ├── Hero.astro
│   ├── Services.astro
│   ├── Projects.astro         # Project cards grid
│   ├── ArchitectureTeaser.astro # Links to flagship project
│   ├── ProjectDetail.astro    # Case study layout
│   ├── MermaidDiagram.astro   # Reusable diagram component
│   ├── TechStack.astro        # Technology tags display
│   ├── Process.astro
│   ├── Contact.astro
│   └── business/              # SME landing components
│       ├── BusinessHero.astro
│       ├── BusinessProblems.astro
│       ├── BusinessInsight.astro
│       ├── BusinessServices.astro
│       ├── BusinessCases.astro
│       ├── BusinessProcess.astro
│       └── BusinessCTA.astro
└── styles/
    └── global.css         # CSS variables and base styles
```

### Internationalization Pattern

The site uses a prefix-based i18n routing (`/en/`, `/es/`). Key utilities in `src/i18n/index.ts`:

- `getLangFromUrl(url)` - Extract language from URL path
- `useTranslations(lang)` - Returns typed translation getter `t('key')`
- `getLocalizedPath(path, lang)` - Generate localized URLs

All text content is centralized in JSON files. Components access translations via:
```typescript
const lang = getLangFromUrl(Astro.url) as Language;
const t = useTranslations(lang);
// Usage: t('hero').title, t('projects').dataSourceAutomator.title
```

### Project Pages System

Individual project pages use a case study format with sections:
- Problem, Solution, Architecture (optional), Tech Stack, Outcomes

**Data Layer** (`src/data/projects.ts`):
```typescript
interface Project {
  slug: string;           // URL slug (e.g., 'data-source-automator')
  key: string;            // Translation key
  category: 'agentPipelines' | 'mcp' | 'compliance';
  tags: string[];
  github: string | null;
  hasDiagram: boolean;    // Controls Architecture section visibility
}
```

**Diagram Registry** (`src/diagrams/index.ts`):
- Mermaid diagrams are defined in TypeScript with translation support
- Only projects with `hasDiagram: true` show the Architecture section
- To add a new diagram: create entry in registry, set `hasDiagram: true` in project

### Adding New Projects

1. Add project to `src/data/projects.ts` array
2. Add translations in `en.json` and `es.json`:
   - Under `projects.<key>`: `title`, `description`
   - Under `projectDetails.<key>`: `problem`, `solution`, `outcomes[]`
3. (Optional) Add diagram to `src/diagrams/index.ts` if `hasDiagram: true`

### Component Architecture

Each page section is a self-contained `.astro` component with:
1. Frontmatter (TypeScript logic, i18n setup)
2. HTML template with translation calls
3. Scoped `<style>` block
4. Optional `<script>` for client-side interactivity

## Deployment

### CI/CD Pipeline

GitHub Actions workflow (`.github/workflows/deploy.yml`) handles automatic deployments:
- **Push to `main`** → Production deployment to Vercel
- **Pull requests** → Preview deployment

Required GitHub Secrets:
- `VERCEL_TOKEN` - API token from vercel.com/account/tokens
- `VERCEL_ORG_ID` - From `.vercel/project.json`
- `VERCEL_PROJECT_ID` - From `.vercel/project.json`

### Manual Deployment

```bash
vercel          # Preview deployment
vercel --prod   # Production deployment
```

### URLs
- **Production**: https://personal-website-lime-one-42.vercel.app
- **Domain**: https://javieraguilar.ai (configured)

### Blog publishing & scheduling

**Full details in [`docs/blog-publishing.md`](docs/blog-publishing.md)** — read it
before scheduling, moving or fixing an article. Key rules:

- **Merging an article branch into `main` is the (irreversible) publish action.** The
  push triggers in parallel the Vercel deploy (`deploy.yml`), the Dev.to cross-post
  (`devto-post.yml`) and the LinkedIn auto-post (`linkedin-post.yml`).
- **Always branch a new article from an up-to-date `main`**
  (`git checkout main && git pull && git checkout -b blog/<slug>`), never from another
  unmerged article branch — merging it would publish the other article too. Before
  merging any blog PR, check `gh pr diff` contains only the intended article's files.
- **Scheduling:** add an entry (`slug`, `branch`, `article`, `date`) to
  `.github/publish-schedule.json` **on `main`**. The single
  `.github/workflows/scheduled-publish.yml` runs several times a day and publishes the
  oldest *due* entry (`date <= today`) not yet on `main`, one per day. The `branch` must
  exist on `origin` with exactly that name. The push uses `secrets.PUBLISH_PAT` (a push
  with the default `GITHUB_TOKEN` would not trigger the cross-post workflows).
- **Moving a date touches three places:** the manifest entry on `main`, the article's
  `pubDate` in **both** EN and ES (the blog index sorts and displays by `pubDate`), and
  the manifest copy carried by the article branch itself — the `merge=schedule` driver
  (`scripts/publish/merge-schedule.mjs`) stops the merge on conflicting edits of the same
  entry. Simulate locally: configure the driver, `git merge --no-ff --no-commit`,
  `node scripts/publish/prune-schedule.mjs`, then `git merge --abort`.
- **Cron runs arrive hours late** (GitHub queue delay, sometimes dropped): an article
  dated D lands on `main` in the afternoon/evening UTC of D. Do not promise mornings.
- **Editing an already-published article:** `detect-new-posts.js` only picks up added
  (`A`) files, so a modification produces no duplicate LinkedIn post but also never
  reaches Dev.to. Re-run `devto-post.yml` via `workflow_dispatch` with
  `post_path=src/content/blog/en/<slug>.md` (it updates by `canonical_url`). The original
  LinkedIn post has no automatic fix.

### LinkedIn automation

Use the API tooling in the repo, not browser automation, for posting:

- `linkedin-post.yml` publishes new articles. Text = Gemini summary
  (`scripts/linkedin/generate-summary.js`, prompt in the dependency-free module
  `scripts/linkedin/prompt.js`, shared with the experiment bench) + `buildPostText` in
  `scripts/linkedin/utils.js` (tested by `utils.test.mjs`). Keep the first line short:
  LinkedIn truncates with "see more" at ~200 characters.
- Frontmatter controls links: `repoUrl` adds `💻 Code: <url>`; optional
  `linkedinLinks: [{ label, url }]` (declared in `src/content/config.ts`) adds one
  `🔗 <label>: <url>` line each. Every article with code should set `repoUrl` in EN and ES.
  Image = `linkedinImage` || `heroImage`.
- `linkedin-scheduled-posts.yml` is legacy *for articles* but still live: it posts
  standalone `.txt` posts from `scripts/linkedin/posts/schedule.json` via
  `scripts/linkedin/post-standalone.js` (supports `--dry-run`, multi-image, mentions as
  `@[Name](urn:li:organization:ID)`, and media at the repo root: `video-linkedin.*` or
  `image.png`). It uses the legacy v2 `ugcPosts` API.
- LinkedIn messaging/chat is not available through the API for independent apps; replies
  to messages have to be done by hand in the browser.
- To preview generated posts without publishing, dispatch the
  "Experimento — generador de posts de LinkedIn" workflow (`summary-experiment.yml`)
  with option `preview-posts` (~5 min). `summary-matrix` takes over an hour. The Gemini
  key only exists in repo secrets.
- `LINKEDIN_ACCESS_TOKEN` expires every 60 days and cannot be auto-refreshed (no
  programmatic refresh token). `linkedin-token-check.yml` checks expiry daily and opens
  a `linkedin-token` issue near expiry (it does not close it). Renew with
  `node scripts/linkedin-oauth-setup.js` (browser OAuth login) + `gh secret set
  LINKEDIN_ACCESS_TOKEN`, and update the local gitignored `.env`; see
  `scripts/linkedin/README.md`. Check current status with
  `gh run list --workflow=linkedin-token-check.yml` rather than trusting notes.

### Claude Code skills

- `.claude/skills/blog-writer/` — article writing checklist; native LinkedIn article
  editor mechanics in `references/linkedin-articles.md`.
- `.claude/skills/tailor-cv/` — CV tailoring (AGILabs goes in its own section, never
  under EXPERIENCE).
