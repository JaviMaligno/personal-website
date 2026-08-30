---
name: blog-writer
description: Write bilingual blog articles for the personal website. Use when creating a new blog post, article, or writing content for the blog. Handles EN/ES translations, frontmatter, and content structure.
---

# Blog Article Writer

Create bilingual (English/Spanish) blog articles for javieraguilar.ai.

## File Locations

- English: `src/content/blog/en/[slug].md`
- Spanish: `src/content/blog/es/[slug].md`
- Images: `public/blog/[image-name].png` (referenced as `/blog/[image-name].png`)

## Required Frontmatter Format

Both EN and ES files must include this exact frontmatter:

```yaml
---
title: "Article Title Here"
description: "A concise description for SEO and preview cards (1-2 sentences)."
pubDate: YYYY-MM-DD
tags: ["Tag1", "Tag2", "Tag3"]
lang: en  # or es
translationKey: article-slug
heroImage: "/blog/article-slug.png"
---
```

### Field Requirements

| Field | Required | Notes |
|-------|----------|-------|
| `title` | Yes | Translated per language |
| `description` | Yes | Translated, SEO-friendly, 1-2 sentences |
| `pubDate` | Yes | Same date for both languages. **Must be the date the article actually gets merged to `main`** — if the publication is scheduled via `scheduled-publish-<slug>.yml`, use that cron's date, and update it if the schedule moves. The blog index sorts and displays by `pubDate`, so a stale draft date makes the article appear under an older date instead of as the newest post. |
| `tags` | Yes | Translated (e.g., "AI" → "IA") |
| `lang` | Yes | Must be `en` or `es` |
| `translationKey` | Yes | Same value for EN/ES pair (kebab-case) |
| `heroImage` | Yes | Path to thumbnail (e.g., `/blog/my-article.png`). Generate with script below. |

### LinkedIn Automation (Optional)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `linkedinImage` | string | Ruta a imagen para LinkedIn (ej: `/blog/linkedin-card.png`) |
| `repoUrl` | string | URL del repo/código del artículo (ej: `https://github.com/JaviMaligno/...`) |

**`linkedinImage`:**
- Campo opcional
- Solo se usa para auto-publicación en LinkedIn
- Si se omite, **se usa `heroImage` como fallback** (`publish-to-linkedin.js:92` hace `linkedinImage || heroImage`); el post solo sale sin imagen si tampoco hay hero
- Ruta debe apuntar a archivo en `public/blog/`
- Formatos: PNG, JPG, WEBP
- Tamaño recomendado: 1200x627px

**`repoUrl` (importante para artículos con código):**
- Si el artículo tiene un repo/fork asociado, **ponlo siempre** en el frontmatter de EN y ES.
- `buildPostText` en `scripts/linkedin/utils.js` añade una línea `💻 Code: <url>` al post de LinkedIn **solo si este campo existe**. Sin él, el enlace al código no sale y hay que editar el post a mano tras publicar (le pasó a `coding-agents-structure` y `restart-vs-iterate`).
- Regla: cualquier enlace externo relevante (repo, fork, paper) debe llegar al post de LinkedIn — `repoUrl` para el código, `linkedinLinks` para papers/preprints.

**Decide la imagen de LinkedIn ANTES de publicar.** El post se genera en el push del merge; una vez publicado no se puede cambiar la imagen — hay que borrar el post en LinkedIn y repostearlo a mano con `scripts/linkedin/post-standalone.js`. Así que la elección se hace en el frontmatter, no después.

Recorre las imágenes del artículo y pregúntate cuál para más el scroll. Si alguna es más fuerte que el hero, ponla como `linkedinImage` en EN y ES:

- **Gráficos generados** (resultados, curvas, benchmarks): un dato concreto suele ganar a una ilustración. Precedente: `forgetting-you-dont-measure` usa `linkedinImage: /blog/forgetting-mixing-curve.png` (la curva de mixing del experimento) mientras el hero es una ilustración.
- **Memes y capturas** (tuits, pantallazos, imágenes citadas en el artículo): si el artículo se apoya en un meme o una captura reconocible, casi siempre es la mejor imagen para el feed. Precedente: `death-of-prompt-engineering` salió con el hero porque el campo estaba vacío, y hubo que borrar el post y repostearlo con `/blog/conjecture-disproved-meme.jpg` (la captura del tuit original que cita el artículo).

Si eliges una imagen que ya está *dentro* del artículo, usa el archivo original (la captura o figura real), no una versión regenerada.

**Ejemplo:**
```yaml
---
title: "Mi Artículo"
description: "Descripción del artículo"
pubDate: 2026-01-07
tags: ["AI", "Automation"]
lang: en
translationKey: mi-articulo
heroImage: "/blog/mi-articulo.png"
linkedinImage: /blog/linkedin-card.png  # Opcional
---
```

## Hero Image Generation

Every article must have a `heroImage`. Generate it using Codex CLI, which has access to OpenAI's image generation models (gpt-image-2).

### How to Generate

**Delegate the final prompt to Codex.** Codex knows its own image model better than we do: don't hand it a rigid pre-baked prompt — give it the article context plus the style constraints below and let it write and run the final image prompt itself.

```bash
codex exec --full-auto "Read the article at src/content/blog/en/article-slug.md. Craft an image-generation prompt for its hero image following these style constraints: [STYLE CONSTRAINTS BELOW]. Then generate the image with your image_gen tool and save it to public/blog/article-slug.png. Finally, print the exact prompt you used."
```

Codex will use its built-in `image_gen` tool, generate the image, and copy it to the specified path in the project.

### Prompt Style Constraints

**Do NOT use the old "minimalist isometric illustration" template.** It produced images that were visually clean but simplistic and schematic. The proven style is a rich technical editorial illustration (see `public/blog/bootstrap-cloud-environments.png` on main as the reference result, and `docs/marketing/image-prompts.md` for its exact prompt).

Anatomy of a good prompt (based on the reference):

```
Create a 1020x510 blog hero image for a technical article titled "[TITLE]".
Style: refined technical editorial illustration, dark but not monochrome, showing [CONCRETE SCENE — the article's core concept as a working system, not an abstract metaphor].
Visual motifs: [3-6 SPECIFIC ELEMENTS — e.g. terminal window with readable but generic lines like "session-start.sh", labeled package boxes, arrows between components, a laptop, a CI runner], clean geometric composition.
No logos, no brand names, no people, no text-heavy poster.
Use crisp bitmap illustration, high contrast, professional AI/developer blog aesthetic, balanced teal, amber, graphite, and off-white accents, no purple gradient blobs, no bokeh.
```

Key learnings vs the old template:

- **Readable generic text is GOOD**: terminal lines, box labels, checklists with plausible-but-generic content make the image concrete and credible. Only avoid *text-heavy posters* (the image shouldn't be a wall of text).
- **Concrete scene over abstract metaphor**: depict the actual system/workflow the article describes (terminals, workspaces, pipelines, charts) rather than floating nodes and glowing cubes.
- **Density is a feature**: several distinct zones (a terminal, a diagram, a desk with objects) beat a single centered icon.
- **Palette**: balanced teal, amber, graphite, off-white on dark — explicitly ban purple gradient blobs and bokeh.
- **Size**: 1020x510 (≈2:1 hero ratio).

### Workflow

1. After writing the article content, run Codex with the article path + style constraints (command above)
2. **Show the generated image to the user for review** (use Read tool on the PNG)
3. If approved, add `heroImage: "/blog/article-slug.png"` to **both** EN and ES frontmatter
4. If not approved, adjust the constraints and regenerate
5. **Record the exact prompt used** in `docs/marketing/image-prompts.md` (article path, image path, generation date, prompt in a code block — follow the existing entries' format; create the file if missing)
6. Codex image quality is trusted — no need for comparison with other generators

### Requirements

- Codex CLI installed (`codex` command available)
- OpenAI API key configured in Codex

## Bilingual Workflow

1. **Always create both files** with matching `translationKey`
2. Use the same `pubDate` for synchronized release
3. Translate tags appropriately (common: AI→IA, Automation→Automatización)
4. Keep `translationKey` identical in both files

## Content Structure

Follow this pattern:

```markdown
Opening paragraph establishing context and the problem/topic.

## Section Heading

Content with clear explanations. Focus on "why" not just "how".

### Subsection (if needed)

- Bullet points for lists
- Keep them concise

## Another Section

Include practical examples:

```language
code block with syntax highlighting
```

## Conclusion/Next Steps

Wrap up with actionable takeaways or links.

---

*Footer with links to resources, repos, etc.*
```

## Writing Style

- **Tone**: Professional but conversational
- **Focus**: Practical value, real examples
- **Length**: 800-2000 words typically
- **Structure**: Clear headings, scannable sections
- **Code**: Include relevant code snippets with language identifiers
- **Images**: Always use **absolute URLs** for inline images: `https://www.javieraguilar.ai/blog/image-name.png`. Dev.to cannot resolve relative paths (`/blog/...`), and the publish script auto-converts relative paths but using absolute URLs from the start avoids issues. The `heroImage` frontmatter field can remain a relative path (it's converted by the publish script).

## Figures — Draw It, Don't Only Describe It

**If the article argues about something with a shape, the article must show that shape.**
Javier has repeatedly had to ask for a figure that should have been in the first draft, so
treat this as a default, not an enhancement: decide about figures *while outlining*, before
writing prose, not after the draft is finished.

### The trigger test

Sweep the outline. A figure is **required**, not optional, whenever a section contains any of:

| Signal in the draft | The figure it owes the reader |
|---|---|
| You describe a diagram, architecture or slide that circulates elsewhere | **Redraw it.** The reader cannot follow a critique of a picture they can't see. Reconstruct it programmatically — never paste someone else's image. |
| Literal geometry: distance, angle, dimension, boundary, region, projection, rotation, a space | The geometry itself. Prose about a shape is a translation of a picture; ship the picture. This is the case most often missed — it came up on the papers. |
| A traversal, dependency, pipeline, or "A → B → C" chain in the text | The graph, with the edges labelled. |
| Two things compared along an axis (before/after, cheap/expensive, bounded/unbounded) | A side-by-side, one panel each, same scale. |
| A set relationship: overlap, containment, "they agree on only two of eleven" | A matrix or set diagram. A matrix is usually more legible than a Venn and far easier to get right. |
| Any experimental result with more than ~3 numbers | A chart. A table of six numbers is a chart you didn't draw. |
| A layered stack, ladder, or hierarchy | The stack, top to bottom. |

If a section trips the test and you decide *not* to draw it, that's a judgement you should be
able to defend in one sentence ("the three-item list is already the clearest form"). Silence is
not a decision.

### How to draw them

**Inline SVG is the house style for conceptual figures** — hand-written, no library, no build
step. Precedent: `verified-world-model-still-loses.md`, and `you-already-have-an-ontology.md`
for diagrams. Pattern:

1. One `<style>` block near the top of the article, with an article-specific class prefix
   (`.cwm-fig`, `.ont-fig`) so styles never collide between posts.
2. Each figure is `<figure class="…-fig">` + `<svg viewBox="0 0 600 H">` + `<figcaption>`.
3. `viewBox` width 600, height to taste; the SVG scales to the column via `width:100%`.
4. **Always a `role="img"` and a real `aria-label`** describing the finding, not the shape.
5. The `figcaption` states what the reader should take away, not what the picture contains.

Palette (matches the site and the generated hero images): background `#1a1a24`, borders
`rgba(255,255,255,0.1)`, primary text `#f8fafc`/`#e2e8f0`, muted `#94a3b8`, teal `#2dd4bf`
(with `#5eead4` for text on dark), amber `#f59e0b` (`#fbbf24` for text), slate connectors
`#64748b`. Monospace for identifiers: `ui-monospace,'JetBrains Mono',monospace`.

Use a rendered PNG instead of SVG when the figure is a **data** chart produced by a script
(matplotlib etc.) — commit the script, and reference the image with an absolute URL.

### Inline SVG does NOT survive to Dev.to on its own

Dev.to renders neither inline SVG nor the scoped `<style>` block, so
`scripts/devto/publish-to-devto.js` strips the styles and swaps each
`<figure class="…-fig">` for a hosted PNG at
`public/blog/<slug>-fig-<n>.{gif,png}`, **in document order**, using the SVG's
`aria-label` as alt text and the `<figcaption>` as the caption. That means:

1. **Pre-render every figure** to `public/blog/<slug>-fig-<n>.png` before publishing,
   numbered in the order they appear in the EN article (only EN goes to Dev.to).
   No extra dependency needed — wrap the SVG in a 1200px-wide page on `#1a1a24`
   and rasterise with headless Chrome:
   ```bash
   "/c/Program Files/Google/Chrome/Application/chrome.exe" --headless --disable-gpu \
     --hide-scrollbars --force-device-scale-factor=1 --window-size=1200,<H> \
     --screenshot="public/blog/<slug>-fig-<n>.png" "file:///<abs-path>/fig-<n>.html"
   ```
   `<H>` = `1200 × viewBoxHeight / viewBoxWidth` plus your vertical padding. Chrome's
   `--screenshot` needs an **absolute** output path; a relative one silently writes nothing.
2. **Miss the PNG and Dev.to gets a broken image link**, so verify the swap before
   publishing by running the same regex over the article and checking that zero
   `<svg` and zero `<style` survive and that every replacement points at a file
   that exists.
3. The `aria-label` is not just accessibility — it becomes the Dev.to alt text.
   Write it as a sentence describing the finding.

### Verify every figure in the browser

SVG you wrote by hand is code, and it has bugs that only appear rendered:

- **Check every arrow lands on the box it means.** A `<path>` at the wrong `y` will silently
  connect the wrong two nodes and the diagram will confidently say something false.
- **Check for overlaps**: labels crossed by connector lines, text escaping the `viewBox`,
  boxes colliding. A small `<rect>` in the background colour behind a label fixes a crossing line.
- Screenshot the rendered page (see *Render for Review*) and look at each figure. Do not ship a
  figure you have only read as source.

## Link Javier's Own Work — Every Mention Is a Link

**Whenever the draft refers to something Javier has made, that mention must be a link.** Not a
"nice to have": a naked reference to his own work is a bug in the draft. Sweep for it before
handing the article over, because it is the single most common thing missing from first drafts.

What counts, and where it points:

| The draft says… | Link to |
|---|---|
| a previous article, "as I wrote before", "the previous article", any of its findings | `/en/blog/<slug>` · `/es/blog/<slug>` |
| "I've written some skills", any named skill of his | `/en/skills` · `/es/skills` |
| a project or case study | `/en/projects/<slug>` · `/es/projects/<slug>` |
| mentoring, teaching, the starter session | `/en/mentoring` · `/es/mentoring` |
| an experiment's code or data | the public repo, plus `repoUrl:` in the frontmatter |

Rules:

- **Use language-matched paths.** `/en/...` in the English file, `/es/...` in the Spanish one.
  Copy-pasting the English link into the Spanish article sends Spanish readers to English pages.
- **Link the first substantive mention**, not every one. Two links to the same article in one
  post is noise; zero is a lost reader.
- **Link the claim, not the boilerplate.** `[the previous article](/en/blog/slug), where
  declaring provenance only moved the strongest model` beats a bare "see my previous post".
- **Verify the slug exists** (`ls src/content/blog/en/`) before linking. A 404 in your own
  article is worse than no link.
- Series articles should link **backwards to their predecessor**; when a new one supersedes or
  qualifies an older finding, say so at the point where it does.

## Video Embeds

### For the Website (javieraguilar.ai)

Use HTML iframe embeds for video platforms. The website supports full HTML.

**Loom example:**
```html
<div style="position: relative; padding-bottom: 56.25%; height: 0;">
  <iframe src="https://www.loom.com/embed/VIDEO_ID"
          frameborder="0"
          webkitallowfullscreen
          mozallowfullscreen
          allowfullscreen
          style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;">
  </iframe>
</div>
```

**YouTube example:**
```html
<div style="position: relative; padding-bottom: 56.25%; height: 0;">
  <iframe src="https://www.youtube.com/embed/VIDEO_ID"
          frameborder="0"
          allowfullscreen
          style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;">
  </iframe>
</div>
```

### Dev.to Compatibility

**Important:** Dev.to filters HTML iframes for security. The publish script (`scripts/devto/publish-to-devto.js`) automatically transforms video embeds:

- **Loom iframes** → Markdown links with note
- **YouTube iframes** → Could be transformed to `{% youtube %}` liquid tags (not implemented yet)

**What gets sent to Dev.to:**
```markdown
**🎥 [Watch the video demo on Loom](https://www.loom.com/share/VIDEO_ID)**

> _Note: Interactive video player available on the [original article](CANONICAL_URL)_
```

**Best Practice:**
- Always use iframe embeds in the markdown
- The Dev.to publish script handles the transformation automatically
- Don't manually create different versions for Dev.to

## Tag Conventions

Common tag translations:

| English | Spanish |
|---------|---------|
| AI | IA |
| Automation | Automatización |
| Machine Learning | Machine Learning |
| Development | Desarrollo |
| Architecture | Arquitectura |

## Example Frontmatter Pair

**English** (`src/content/blog/en/my-new-post.md`):
```yaml
---
title: "Building Something Cool"
description: "How I built a tool that solves a real problem."
pubDate: 2025-01-03
tags: ["AI", "Automation", "Claude"]
lang: en
translationKey: my-new-post
heroImage: "/blog/my-new-post.png"
---
```

**Spanish** (`src/content/blog/es/my-new-post.md`):
```yaml
---
title: "Construyendo Algo Genial"
description: "Cómo construí una herramienta que resuelve un problema real."
pubDate: 2025-01-03
tags: ["IA", "Automatización", "Claude"]
lang: es
translationKey: my-new-post
heroImage: "/blog/my-new-post.png"
---
```

## Writing from LinkedIn Posts

When repurposing a LinkedIn post into a blog article:

1. **Fetch the post** using WebFetch to extract the content
2. **Download any images** from the post to `public/blog/`
3. **Expand the content** - LinkedIn posts are short; blog articles should:
   - Add more context and background
   - Include code examples if relevant
   - Expand on points that were condensed
   - Add sections the post didn't have room for
4. **Keep the core message** but make it more comprehensive
5. **Use original post date** as `pubDate` for authenticity

### LinkedIn Image Download

Images from LinkedIn posts should be:
- Downloaded to `public/blog/[descriptive-name].png`
- Named descriptively (e.g., `azure-content-filter-demo.png`)
- Referenced in markdown as `/blog/[name].png`

## Render for Review (do this by default)

**Never hand back a finished article as raw markdown and stop there.** Always render it and give the user a URL, so they review it the way a reader will see it — typography, headings, code blocks, hero image in place, links resolving.

```bash
npm run build   # validates frontmatter against the content schema and catches broken pages
npm run dev     # run in background; serves on http://localhost:4321
```

Then give the user both language URLs explicitly:

- `http://localhost:4321/en/blog/<slug>`
- `http://localhost:4321/es/blog/<slug>`

Rules:
- **Build before serving.** A frontmatter or schema error fails the build; catching it here beats the user hitting an error page.
- **Verify the article actually generated**: `ls dist/en/blog/ | grep <slug>` and the same for `es`.
- **Show the hero image inline** (Read tool on the PNG) as well, since it is easy to miss in a page scroll, and call out any visible text artefacts in the generated image — image models frequently mangle labels.
- Only after the user has reviewed the rendered pages should you consider the article done, commit it, or schedule publication.

## Checklist Before Publishing

- [ ] `npm run build` passes and both pages appear in `dist/en/blog/` and `dist/es/blog/`
- [ ] **Rendered pages reviewed by the user** at `localhost:4321` (both languages) — not just the markdown
- [ ] **Figure sweep run against the outline** (see *Figures*): every redrawn diagram, literal geometry, traversal, comparison, set relationship, result table and layered stack either has a figure or a defensible reason not to
- [ ] **Each figure pre-rendered to `public/blog/<slug>-fig-<n>.png`** (EN order) and the Dev.to swap dry-run shows no surviving `<svg`/`<style`
- [ ] **Every figure inspected rendered in a browser** — arrows landing on the right nodes, no label/line overlaps, nothing escaping the `viewBox` — and present in both EN and ES
- [ ] Both EN and ES files created
- [ ] Matching `translationKey` in both
- [ ] Same `pubDate` in both
- [ ] **`pubDate` equals the actual publication date** (the `scheduled-publish-<slug>.yml` cron date, or today if merging manually) — not the date the draft was written
- [ ] Tags translated appropriately
- [ ] `lang` field matches file location
- [ ] Hero image generated, reviewed by user, and placed in `public/blog/`
- [ ] `heroImage` field set in both EN and ES frontmatter
- [ ] Image prompt recorded in `docs/marketing/image-prompts.md`
- [ ] **`linkedinImage` decidido antes de publicar** — revisadas todas las imágenes del artículo (gráficos, memes, capturas) y puesta la más llamativa en EN y ES si supera al hero. Sin este campo se publica el hero (`linkedinImage || heroImage`), y cambiarlo después obliga a borrar el post y repostearlo a mano.
- [ ] **If the article involves code, `repoUrl:` set in both EN and ES frontmatter** — the LinkedIn auto-post (`scripts/linkedin/utils.js`) adds a "💻 Code:" line only when this field is present. Omitting it means editing the LinkedIn post by hand after publish.
- [ ] Links are valid and functional
- [ ] **Every mention of Javier's own work is a link** — previous articles, skills, projects, mentoring, experiment repos — with language-matched paths (`/en/...` in EN, `/es/...` in ES) and slugs verified to exist
