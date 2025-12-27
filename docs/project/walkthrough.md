# Personal Brand Website - Walkthrough

## Summary

Built a professional one-pager website for **Javier Aguilar** as AI Agent Architect.

**Features:**
- ✅ Dark theme with glassmorphism effects
- ✅ Bilingual support (EN/ES)
- ✅ Hero, Services, Projects, Process, Contact sections
- ✅ Mobile-responsive design
- ✅ Deployed to Vercel

---

## 🚀 Production URLs

| Platform | URL |
|----------|-----|
| **Live Site** | https://personal-website-lime-one-42.vercel.app |
| **GitHub** | https://github.com/JaviMaligno/personal-website |

---

## Files Created

### Core

| File | Purpose |
|------|---------|
| `astro.config.mjs` | i18n routing config |
| `src/styles/global.css` | Design system |
| `src/layouts/Layout.astro` | Header, nav, footer |

### Components

| Component | Section |
|-----------|---------|
| `Hero.astro` | Animated headline |
| `Services.astro` | 3 service cards |
| `Projects.astro` | 6 project cards |
| `Process.astro` | 5-step timeline |
| `Contact.astro` | Formspree form |

### i18n

| File | Language |
|------|----------|
| `src/i18n/en.json` | English |
| `src/i18n/es.json` | Spanish |

---

## Build Output

```
✓ 3 pages built in 4.73s
  /en/index.html
  /es/index.html
  /index.html (redirect)
```

---

## Configuration

- ✅ Formspree endpoint: `maqyoqeg`
- ✅ Vercel auto-deploy connected
- ⏳ Custom domain: pending registration

---

## Next Steps

1. Register `javieraguilar.ai` at [nic.ai](https://nic.ai)
2. Configure domain in Vercel → Settings → Domains
3. Update GitHub/LinkedIn URLs in Layout.astro
