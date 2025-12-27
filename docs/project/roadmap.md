# Future Actions Roadmap

This document tracks planned improvements and future features for the personal website.

## Priority: High

### 1. Synthetic Data for Demos
Create fake datasets for interactive demos:
- [ ] **Compliance Classifier**: Generate 50 fake Australian companies with ABNs
- [ ] **Data Source Automator**: Create sample data requirements scenarios

### 2. Video Recordings
Record "black box" demos for each project:
- [ ] **DevOps Agent Suite**: Terminal recording of issue resolution
- [ ] **Compliance Classifier**: Screen recording of risk report generation
- [ ] **Data Source Automator**: Demo of spec document creation

### 3. Frontend Demos (Streamlit/Gradio)
Build simple UIs for backend-only projects:
- [ ] **Compliance Classifier**: Input ABN → Output risk report PDF
- [ ] **Data Source Automator**: Input data need → Output spec document
- [ ] **Medical Doc Parser**: Upload medical doc → View extracted data

---

## Priority: Medium

### 4. Content Expansion
- [ ] Add blog section with technical articles
- [ ] Write case studies (anonymized client work)
- [ ] Create architecture deep-dive posts per project

### 5. Architecture Diagrams
Create SVG/Mermaid diagrams for:
- [ ] Data Source Automator (multi-agent flow)
- [ ] Compliance Classifier (registry + scoring)
- [ ] DevOps Agent Suite (issue → PR flow)

### 6. Analytics & SEO
- [ ] Set up Plausible or Simple Analytics
- [ ] Add structured data (JSON-LD)
- [ ] Create sitemap.xml

---

## Priority: Low

### 7. Integrations
- [ ] Calendly/Cal.com booking widget
- [ ] Newsletter signup (Buttondown/ConvertKit)
- [ ] Chat widget for quick questions

### 8. Additional Features
- [ ] Dark/light mode toggle
- [ ] Testimonials section (when available)
- [ ] Pricing/packages page (when services are defined)

---

## Formspree Setup

1. Go to [formspree.io](https://formspree.io)
2. Create a free account
3. Create a new form
4. Copy the form ID (looks like `xabcdefg`)
5. Replace `YOUR_FORM_ID` in `src/components/Contact.astro`

---

## Domain & Deployment

### Domain Registration
1. Register `javieraguilar.ai` at [nic.ai](https://nic.ai) or Namecheap
2. Configure DNS to point to Vercel/GitHub Pages

### Vercel Deployment
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel
```

### GitHub Actions (Alternative)
Create `.github/workflows/deploy.yml`:
```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: withastro/action@v2
```

---

## GitHub Profile Updates

Update your GitHub profile for brand consistency:
- [ ] Update username if needed (javieraguilarmartin → javieraguilar?)
- [ ] Pin relevant repos: oss-agent, bitbucket-mcp, personal-website
- [ ] Update profile README with services summary
- [ ] Add profile picture matching website branding
