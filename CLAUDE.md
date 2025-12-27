# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

This is a personal portfolio website for Javier Aguilar, an AI Agent Architect. The site serves as a "productized service" landing page to market:
- **AI Agent Pipelines**: Multi-agent orchestration for research, coding, and review workflows
- **MCP Development**: Custom Model Context Protocol servers
- **Compliance Automation**: Risk assessment and classification systems

The goal is to position the brand ("AGILabs") as a specialized AI orchestration consultancy, showcasing architecture diagrams and demos rather than code.

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
├── i18n/              # Internationalization (en/es)
│   ├── index.ts       # Translation utilities
│   ├── en.json        # English strings
│   └── es.json        # Spanish strings
├── layouts/
│   └── Layout.astro   # Base layout with header/footer
├── pages/
│   ├── index.astro    # Redirect page
│   ├── en/index.astro # English homepage
│   └── es/index.astro # Spanish homepage
├── components/        # Section components (Hero, Services, Projects, Architecture, Process, Contact)
└── styles/
    └── global.css     # CSS variables and base styles
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
// Usage: t('hero').title, t('services').agentPipelines.description
```

### Component Architecture

Each page section is a self-contained `.astro` component with:
1. Frontmatter (TypeScript logic, i18n setup)
2. HTML template with translation calls
3. Scoped `<style>` block
4. Optional `<script>` for client-side interactivity

The `Architecture.astro` component uses Mermaid.js for the pipeline diagram, with translations interpolated into the Mermaid syntax string.

### Adding New Projects

Projects are defined in `src/components/Projects.astro` with category mappings. To add a project:
1. Add translation keys in both `en.json` and `es.json` under `projects`
2. Add project entry in the `projects` array in `Projects.astro`
3. Map to existing category (`agentPipelines`, `mcp`, `compliance`) or create new one

## Deployment

Site is configured for `https://javieraguilar.ai` with sitemap integration. Static output in `dist/` can be deployed to any static host.
