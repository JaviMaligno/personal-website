# Javier Aguilar - Personal Website

Professional one-pager website for AI Agent Architect services.

## Tech Stack

- **Framework**: Astro 5.x
- **Styling**: Vanilla CSS with custom properties
- **i18n**: English (en) and Spanish (es)
- **Deployment**: Vercel / GitHub Pages

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
├── components/      # Astro components (Hero, Services, Projects, etc.)
├── i18n/           # Translation files (en.json, es.json)
├── layouts/        # Base layout with header/footer
├── pages/          # Route pages
│   ├── en/         # English pages
│   └── es/         # Spanish pages
└── styles/         # Global CSS
```

## Configuration

### Formspree
Update the form action in `src/components/Contact.astro` with your Formspree form ID:
```astro
action="https://formspree.io/f/YOUR_FORM_ID"
```

### Domain
Update `astro.config.mjs` with your domain:
```js
site: 'https://javieraguilar.ai',
```

### Social Links
Update footer links in `src/layouts/Layout.astro` with your actual GitHub and LinkedIn URLs.

## Deployment

### Vercel
1. Connect repository to Vercel
2. Astro configuration auto-detected
3. Configure custom domain in Vercel dashboard

### GitHub Pages
Add `.github/workflows/deploy.yml` with Astro GitHub Action.

## License

MIT
