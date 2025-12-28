# Javier Aguilar - Personal Website

Professional portfolio website for AI Agent Architect services, featuring individual project case studies with architecture diagrams.

## Tech Stack

- **Framework**: Astro 5.x (Static Site Generator)
- **Diagrams**: Mermaid.js (client-side rendering)
- **Styling**: Vanilla CSS with custom properties
- **i18n**: English (en) and Spanish (es)
- **CI/CD**: GitHub Actions → Vercel

## Development

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
src/
├── data/
│   └── projects.ts      # Centralized project definitions
├── diagrams/
│   └── index.ts         # Mermaid diagram registry
├── components/
│   ├── ProjectDetail.astro   # Case study layout
│   ├── MermaidDiagram.astro  # Reusable diagram component
│   └── ...                   # Section components
├── i18n/                # Translation files (en.json, es.json)
├── layouts/
│   ├── Layout.astro         # Base layout
│   └── ProjectLayout.astro  # Project page layout
├── pages/
│   ├── en/
│   │   ├── index.astro
│   │   └── projects/[slug].astro  # Dynamic project pages
│   └── es/
│       ├── index.astro
│       └── projects/[slug].astro
└── styles/
    └── global.css
```

## Adding Projects

1. Add entry to `src/data/projects.ts`
2. Add translations in `en.json` and `es.json`:
   - `projects.<key>`: title, description
   - `projectDetails.<key>`: problem, solution, outcomes[]
3. (Optional) Add diagram to `src/diagrams/index.ts`

## Configuration

### Environment Variables
Copy `.env.example` to `.env` (if needed for local testing):
```
VERCEL_TOKEN=<your-token>
VERCEL_ORG_ID=<from .vercel/project.json>
VERCEL_PROJECT_ID=<from .vercel/project.json>
```

### Formspree
Contact form configured in `src/components/Contact.astro`.

### Domain
Site URL in `astro.config.mjs`:
```js
site: 'https://javieraguilar.ai',
```

## Deployment

### Automatic (CI/CD)
Push to `main` triggers automatic deployment via GitHub Actions.
Pull requests create preview deployments.

**Required GitHub Secrets:**
- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`

### Manual
```bash
vercel          # Preview
vercel --prod   # Production
```

## URLs

- **Production**: https://personal-website-lime-one-42.vercel.app
- **Domain**: https://javieraguilar.ai

## License

MIT
