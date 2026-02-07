---
description: How to create, publish, and update dual-language articles with automated pipelines to Dev.to and LinkedIn.
---

# Article Creation & Publishing Workflow

This workflow details the complete process for publishing content to your personal website and syndicating it to Dev.to and LinkedIn.

## 1. Preparation & File Structure

For each article, you must create two files (English & Spanish). They are linked by a shared `translationKey`.

### Directory
- English: `src/content/blog/en/`
- Spanish: `src/content/blog/es/`

### Images
1.  **Storage**: Save images in `public/blog/`.
    *   Example: `public/blog/ai-agents-v1.png`
2.  **Usage**: Reference them in markdown as `/blog/ai-agents-v1.png`.

## 2. Frontmatter Configuration

### English Version (`src/content/blog/en/my-post.md`)
```markdown
---
title: "Deep Dive into AI Agents"
description: "A comprehensive guide to building autonomous agents."
pubDate: 2024-03-20
tags: ["AI", "Agents", "LLM"]
lang: en
translationKey: ai-agents-deep-dive  # MUST MATCH SPANISH VERSION
heroImage: "/blog/ai-agents-v1.png"

# Platform-Specific Controls
publishToDevto: true       # Defaults to true. Set false to skip.
devtoPublished: false      # true = Public immediately, false = Draft (Recommended)
linkedinImage: "/blog/ai-agents-linkedin.png" # Optional: Specific image for LinkedIn post
---
```

### Spanish Version (`src/content/blog/es/my-post.md`)
```markdown
---
title: "Profundizando en Agentes de IA"
description: "Guía completa para construir agentes autónomos."
pubDate: 2024-03-20
tags: ["IA", "Agentes", "LLM"]
lang: es
translationKey: ai-agents-deep-dive  # MUST MATCH ENGLISH VERSION
heroImage: "/blog/ai-agents-v1.png"
---
```

## 3. Deployment Pipeline

The pipeline triggers automatically on `git push` to `main`.

### A. Personal Website (Vercel)
-   **Trigger**: Push to `main`.
-   **Action**: Deploys both English and Spanish versions.
-   **Image**: Uses `heroImage` for both the article header and Open Graph (social preview).

### B. Dev.to (Automation)
-   **Trigger**: New English post detected on `main`.
-   **Action**: Creates a new article on Dev.to.
-   **Image**: Uploads `heroImage` as the main cover image.
-   **Status**: Created as **Draft** by default (safer for review).
-   **Canonical URL**: Automatically set to your personal website to protect SEO.

### C. LinkedIn (Automation)
-   **Trigger**: New English post detected on `main`.
-   **Action**:
    1.  Generates a summary using Gemini AI.
    2.  **Image Logic**:
        -   If `linkedinImage` is defined: Uploads that image natively (Better reach).
        -   If not: Posts the link, and LinkedIn scrapes the `heroImage` from your site.
    3.  Publishes the post with the summary + link.

## 4. Editing & Post-Publishing

### Updating the Website
-   **Method**: Edit the markdown file and `git push`.
-   **Effect**: Vercel rebuilds the site. Changes are live in ~2 minutes.

### Updating Dev.to
-   **Method**: **Manual Script**. (Dev.to does not auto-update on push to avoid overwriting your manual edits there).
-   **Steps**:
    1.  Get Article ID (from Dev.to dashboard).
    2.  Run: `npm run update:devto -- <ID> <FILENAME>`
    3.  Example: `npm run update:devto -- 3227500 my-post.md`

### Updating LinkedIn
-   **Method**: **Manual on LinkedIn.com**.
-   **Note**: The API does not support editing posts. You must delete and repost or edit via the UI.

## 5. Troubleshooting Images

| Platform | Problem | Solution |
| :--- | :--- | :--- |
| **Website** | Image not showing | Ensure `heroImage` starts with `/` and file exists in `public/blog/`. |
| **Dev.to** | Cover image missing | Run update script again. Dev.to caches heavily; wait 5 mins. |
| **LinkedIn** | Wrong preview image | Use [Post Inspector](https://www.linkedin.com/post-inspector/) to clear cache for your URL. |

## 6. Summary Checklist
-   [ ] Created ES & EN files with same `translationKey`.
-   [ ] Added `heroImage` to `public/blog/`.
-   [ ] Configured frontmatter (title, desc, tags).
-   [ ] `git push origin main`.
-   [ ] (Optional) Review Dev.to draft and publish.
