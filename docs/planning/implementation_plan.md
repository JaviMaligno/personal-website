# Personal Brand Website - Implementation Plan

## Overview

Build a professional one-pager website to position Javier Aguilar as an **AI Agent Architect** specializing in agentic automation, MCP development, and intelligent pipelines for enterprises and developers.

---

## 🎨 Brand Strategy

### Brand Architecture

> **Javier Aguilar** is the authority.  
> **AGILabs** is the creative/technical engine.

| Element | Value |
|---------|-------|
| **Primary Domain** | `javieraguilar.ai` |
| **Title** | Javier Aguilar |
| **Role Line** | AI Engineer · Automation · Agentic Systems |
| **Submarca** | AGILabs - *Experimental AI systems, tools & products* |

### Taglines

| Context | EN | ES |
|---------|----|----|
| **Hero** | *I design AI systems that actually work* | *Diseño sistemas de IA que funcionan en el mundo real* |
| **Secondary** | *Multi-agent systems and AI orchestration* | *Sistemas multi-agente y automatización con IA* |
| **Manifesto** | *Less hype. More working systems.* | *Hago que la IA trabaje por ti, no al revés* |

### Brand Placement

| Location | Content |
|----------|---------|
| **Hero** | Javier Aguilar + Primary tagline + "Founder of AGILabs" |
| **Labs Section** | AGILabs header + Labs tagline |
| **Footer** | © Javier Aguilar — Built with AGILabs |

---

## 🏗️ Technical Architecture

### Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Framework | **Astro 5.x** | Fast static sites, native i18n |
| Styling | **Vanilla CSS** | Full control, no build overhead |
| Forms | **Formspree** | Zero-backend contact form |
| Deployment | **Vercel** | Best Astro integration, free tier |
| i18n | **Astro i18n** | `/en/` and `/es/` paths |

### Project Structure

```
src/
├── components/      # Hero, Services, Projects, Process, Contact
├── i18n/           # en.json, es.json + utilities
├── layouts/        # Layout.astro with header/footer
├── pages/          # index.astro, en/, es/
└── styles/         # global.css design system
```

---

## 📄 One-Pager Sections

1. **Header** - Sticky nav with language switcher
2. **Hero** - Gradient title, taglines, CTAs
3. **Services** - 3 cards: Pipelines, MCP, Compliance
4. **Projects** - 6 project cards with tags
5. **Process** - 5-step timeline
6. **Contact** - Formspree form + AGILabs badge
7. **Footer** - Social links, copyright

---

## 🎨 Visual Design

### Color Palette (Dark Mode)

```css
--bg-primary: #0a0a0f
--accent-primary: #6366f1 (Indigo)
--accent-secondary: #8b5cf6 (Purple)
--text-primary: #f8fafc
```

### Effects
- Glassmorphism cards
- Gradient borders on hover
- Animated hero glow

---

## 🌍 Internationalization

```
/     → Redirect to /en/
/en/  → English version
/es/  → Spanish version
```

---

## 🚀 Deployment

**Vercel** (primary):
1. Auto-detect Astro config
2. Connect GitHub for auto-deploy
3. Add custom domain in dashboard

---

## ✅ Verification Checklist

- [x] Astro build succeeds
- [x] Both language pages render
- [x] Contact form submits to Formspree
- [ ] Lighthouse score > 90
- [ ] Custom domain configured
