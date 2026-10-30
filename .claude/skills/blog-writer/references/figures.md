# Figures

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
| The argument runs along N axes (cost, quality, speed) | A figure that shows all N: a 3D view, a density, small multiples, or colour/size for the extra axis. |
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
   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu \
     --hide-scrollbars --force-device-scale-factor=1 --window-size=1200,<H> \
     --screenshot="public/blog/<slug>-fig-<n>.png" "file://<abs-path>/fig-<n>.html"
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
- Screenshot the rendered page (step 5 of the workflow in `SKILL.md`) and look at each figure. Do not ship a
  figure you have only read as source.

### Read every figure as a newcomer would

A figure is right when a reader who skipped the text gets its point:

- **It matches the text's definitions.** If the text defines a Pareto frontier as the
  non-dominated points, the curve passes through those points only, and the dominated ones sit
  visibly off it. Same for any term the figure draws.
- **It covers what the text compares.** Every axis, arm and model the paragraph discusses is in
  the figure, with the same names.
- **Its takeaway fits in one sentence.** Write that sentence (it is the `figcaption`); if the
  picture does not show it at a glance, simplify the picture.
- **Breakdowns are explicit.** A multiplier made of steps ("10× the token price, 6.4× the cost,
  +23 % on the task") shows or states each step.

### Prose maths

KaTeX renders `$…$` in the prose too, so two dollar amounts in one paragraph ("$0.02 … $0.20")
become a formula. Escape currency in prose and tables as `\$0.02` (as `there-is-no-best-model`
does); inside an inline SVG `$` is plain text. Look at the prose in the browser, not only the
figures. On Dev.to, maths is sent as `{% katex %}` tags by
`scripts/devto/publish-to-devto.js`; LinkedIn has no maths (see `linkedin-articles.md`).
