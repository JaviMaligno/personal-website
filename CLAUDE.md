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
```

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
