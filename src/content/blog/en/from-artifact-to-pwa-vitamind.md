---
title: "From Claude Artifact to Production PWA: Building VitaminD Explorer"
description: "How a simple question about vitamin D synthesis turned into a Claude artifact, then a full PWA with D3.js visualizations, push notifications, and 6 languages."
pubDate: 2026-04-29
tags: ["Claude", "PWA", "Next.js", "D3.js", "Side Project"]
lang: en
translationKey: from-artifact-to-pwa-vitamind
heroImage: "/blog/from-artifact-to-pwa-vitamind.png"
---

It started with a simple question: **can I synthesize vitamin D today in London?**

I'd been reading about how latitude, season, and skin type determine whether sunlight can actually trigger vitamin D production. The science is clear — below a certain [solar elevation angle](https://en.wikipedia.org/wiki/Solar_zenith_angle) (~45–50°), UVB radiation is too weak for synthesis regardless of how long you stay outside. But figuring out *when* that window opens for a given city on a given day? That's a calculation involving [solar declination](https://en.wikipedia.org/wiki/Position_of_the_Sun#Declination_of_the_Sun), hour angles, and spherical trigonometry.

So I asked Claude.

## The Artifact That Started Everything

Claude didn't just answer the question — it generated an [interactive artifact](https://claude.ai/public/artifacts/e1377c30-3b83-47bd-938f-6e107c21231a) with a solar elevation curve, a day-of-year scrubber, and a threshold line showing when synthesis was possible. It used [Spencer's 1971 formula](https://doi.org/10.1016/0038-092X(71)90055-1) for solar declination and the equation of time, projected onto a clean SVG chart. 

I expected a paragraph with some numbers. Instead I got a working prototype.

I played with it for a few minutes — scrubbing through the year, watching the synthesis window expand in summer and vanish in winter — and thought: *this is actually useful*. Not just for me, but for anyone living at high latitudes wondering if they should bother going outside for their vitamin D.

That's when I decided to build it for real.

## From Toy to Product: The Technical Decisions

### Next.js App Router as the Foundation

I went with Next.js 16 and the App Router. The app needed client-side interactivity (D3 charts, geolocation, animations) but also server-side API routes (weather data proxying, push notification delivery, city search). App Router gives you both in one project without stitching together separate services.

### D3.js on Canvas: Performance Over Convenience

The original artifact used SVG for everything. That works for a single chart, but I wanted three visualizations: a daily solar curve, an interactive world map, and a latitude × day-of-year heatmap (130 latitudes × 365 days = 47,450 cells).

SVG can't handle that on mobile. So I moved to Canvas rendering with an SVG overlay for interactive elements — hover tooltips, click targets, threshold adjusters. The world map uses an equirectangular projection with pan and pinch-to-zoom, rendering 195 countries from TopoJSON on every frame. Device pixel ratio scaling keeps it sharp on Retina displays.

The tradeoff is complexity. Canvas means manual coordinate transforms, hit-testing, and redraw management. But it was necessary — the heatmap alone would have created 47K DOM nodes as SVG rectangles.

### The Vitamin D Math: Not Just Solar Angles

The artifact only calculated *when* synthesis was possible. I wanted to answer *how long you need to stay outside* for a given dose — say, 1000 IU.

This required modeling the actual photobiology. The rate depends on:

- **UVI** (UV index at the current hour)
- **Skin type** ([Fitzpatrick scale](https://en.wikipedia.org/wiki/Fitzpatrick_scale) I–VI, each with a different [MED](https://en.wikipedia.org/wiki/Minimal_erythema_dose) — Minimal Erythemal Dose)
- **Exposed body area** (face and hands vs. t-shirt and shorts)
- **Age** (synthesis efficiency drops ~1.3% per year after 20, per [Holick et al. 1989](https://doi.org/10.1016/S0140-6736(89)92611-4))

And critically, it's not linear. [Previtamin D3](https://en.wikipedia.org/wiki/Previtamin_D3) doesn't just accumulate — it [photodegrades](https://en.wikipedia.org/wiki/Photodegradation) under continued UVB into inert compounds (lumisterol and tachysterol). This is your body's built-in overdose protection, and it means there's a ceiling on how much you can produce per session.

I modeled this as a saturating exponential:

```
IU(t) = IU_sat × (1 - e^(-R×t / IU_sat))
```

Where `IU_sat` is the photodegradation ceiling (19,200 IU for full-body 1 MED, per [Holick 1982](https://doi.org/10.1126/science.6281884), scaled by area and age) and `R` is the production rate based on [Dowdy et al. 2010](https://doi.org/10.1111/j.1365-2133.2010.09888.x) MED tables. At low doses, it matches Holick's linear rule. At higher doses, diminishing returns kick in. The model agrees with [Young et al. 2021](https://doi.org/10.1073/pnas.2015867118) (n=75, in-vivo validation).

### Real Weather Data: Open-Meteo

Solar geometry gives you clear-sky estimates, but clouds matter enormously. A 70% cloud cover can reduce UVB by 60%. I integrated the [Open-Meteo API](https://open-meteo.com/) for hourly UV index and cloud cover — no API key needed, free for non-commercial use.

The tricky part: Open-Meteo's UV index *already includes cloud cover*. If you apply a cloud penalty on top, you double-count it. I caught this bug after noticing that exposure times on cloudy days were absurdly high. The fix: only apply the cloud factor to theoretical (solar geometry) estimates, never to real API data.

## Why a PWA and Not a Native App

This was a deliberate choice. A vitamin D calculator needs to work on any device — iOS, Android, desktop — and I'm a solo developer. Building and maintaining native apps for two platforms plus a web version was out of the question.

[PWAs](https://en.wikipedia.org/wiki/Progressive_web_app) close most of the gap that used to matter:

- **Installation**: "Add to Home Screen" works on both iOS and Android — no app store, no review process, no $99/year Apple Developer fee
- **Push notifications**: Supported on Android since 2015 and [on iOS since 16.4](https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/) (March 2023) — the last major blocker is gone
- **Offline**: Service workers cache everything needed for core functionality
- **Updates**: Deploy to Vercel, users get the new version on next visit — no "please update the app" friction

What you *don't* get: background location tracking, health app integrations (Apple Health, Google Fit), and a presence in the App Store for discoverability. The first two could matter for future features (wearable integrations, automatic daily tracking). The third is a real distribution disadvantage — people search app stores, not the web.

For now, the tradeoff is clearly worth it. If the app grows to need native APIs (wearables, health data), a hybrid approach with [Capacitor](https://capacitorjs.com/) or a thin native wrapper around the existing web app would be the natural next step — not a rewrite.

### Offline Support

A vitamin D calculator is most useful when you're already outside — potentially with no signal. The service worker caches all pages and static assets at install time, with a network-first strategy for dynamic content and an offline fallback page.

### Push Notifications

This was the feature that felt most "app-like." A Vercel cron job runs daily at 8 AM UTC, fetches real UV data for each subscriber's saved location, calculates their personal synthesis window, and sends a Web Push notification:

> *"London · 12 min for 1000 IU · Best hour: 13:00 (UVI 4.5) · Window: 11:00–15:00"*

The implementation uses VAPID keys with the `web-push` library, and subscriptions are stored in Supabase. One gotcha that cost me 53 days of broken push notifications: `echo "$KEY" | vercel env add` appends a newline that Vercel stores literally inside the VAPID key. The fix is `printf '%s'` instead of `echo`. A subtle shell behavior that silently corrupted a cryptographic key.

## Six Languages and 5,000+ Cities

The app supports English, Spanish, French, German, Russian, and Lithuanian via `next-intl`. Each language file is ~480 lines covering UI labels, Fitzpatrick skin descriptions, and a full educational FAQ about vitamin D science.

City search combines a built-in database of 50+ major cities with Supabase full-text search (`pg_trgm`) over GeoNames' 200K+ city dataset. City names are localized — "Londres" in Spanish, "Лондон" in Russian.

## What I Learned

**Claude artifacts are underrated as prototyping tools.** The artifact wasn't a mockup or a diagram — it was working code with real solar math. That head start meant I could focus on product decisions (what visualizations? what user flow?) instead of re-deriving spherical trigonometry.

**Canvas D3 is worth the pain for data-dense visualizations.** If you're rendering fewer than 1,000 elements, stick with SVG. Beyond that, Canvas is the only way to keep mobile smooth.

**PWA push notifications are surprisingly powerful and surprisingly fragile.** The Web Push spec works well, but the operational surface area (VAPID keys, cron timing, subscription cleanup, error handling for uninstalled apps) is larger than the code suggests.

**Photobiology is more nuanced than "go outside for 15 minutes."** The difference between Fitzpatrick I (pale, Celtic) and VI (deeply pigmented) is a factor of 6× in MED. Body area exposure matters more than most people think — face and hands alone (10% body area) can require 5× longer than a t-shirt and shorts (25%).

## Try It

**[VitaminD Explorer](https://getvitamind.app)** is free, open source, and works on any device. Search your city, set your skin type and exposure, and see exactly when and how long you need for your daily vitamin D.

The [original Claude artifact](https://claude.ai/public/artifacts/e1377c30-3b83-47bd-938f-6e107c21231a) is still live if you want to see where it all began.

---

*Built with Next.js 16, D3.js, Supabase, and Vercel. [Source on GitHub](https://github.com/JaviMaligno/vitamind).*
