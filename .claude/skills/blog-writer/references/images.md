# Images: hero and LinkedIn

## Hero image

Every article must have a `heroImage`. Generate it using Codex CLI, which has access to OpenAI's image generation models (gpt-image-2).

### How to generate

**Delegate the final prompt to Codex.** Codex knows its own image model better than we do: don't hand it a rigid pre-baked prompt — give it the article context plus the style constraints below and let it write and run the final image prompt itself.

```bash
codex exec -s workspace-write "Read the article at src/content/blog/en/article-slug.md. Craft an image-generation prompt for its hero image following these style constraints: [STYLE CONSTRAINTS BELOW]. Then generate the image with your image_gen tool and save it to public/blog/article-slug.png. Finally, print the exact prompt you used."
```

`--full-auto` was removed in codex-cli 0.164; `-s workspace-write` is the equivalent (writes only inside the repo). Close stdin (`< /dev/null`) so it can't hang waiting for input.

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

1. Together with the draft (workflow step 4), run Codex with the article path + style constraints (command above)
2. **Show the generated image to the user for review** (use Read tool on the PNG)
3. If approved, add `heroImage: "/blog/article-slug.png"` to **both** EN and ES frontmatter
4. If not approved, adjust the constraints and regenerate
5. **Record the exact prompt used** in `docs/marketing/image-prompts.md` (article path, image path, generation date, prompt in a code block — follow the existing entries' format; create the file if missing)
6. Codex image quality is trusted — no need for comparison with other generators

### Requirements

- Codex CLI installed (`codex` command available)
- OpenAI API key configured in Codex

## LinkedIn image

The LinkedIn auto-post uses `linkedinImage || heroImage` (`publish-to-linkedin.js`). The post is
generated on the merge push and its image cannot be changed afterwards (it takes deleting the post
and reposting by hand with `scripts/linkedin/post-standalone.js`), so the choice is made in the
frontmatter, before publishing.

Go through the article's images and ask which one stops the scroll. When one is stronger than the
hero, set it as `linkedinImage` in EN and ES:

- **Generated charts** (results, curves, benchmarks): a concrete number usually beats an
  illustration. Precedent: `forgetting-you-dont-measure` uses
  `linkedinImage: /blog/forgetting-mixing-curve.png` (the experiment's mixing curve) while its hero
  is an illustration.
- **Memes and screenshots** (tweets, captures, images the article quotes): when the article leans on
  a recognisable meme or capture, it is almost always the best image for the feed. Precedent:
  `death-of-prompt-engineering` went out with the hero because the field was empty, and had to be
  deleted and reposted with `/blog/conjecture-disproved-meme.jpg`.
- **A card composed in code over a real figure** (the question on top, the figure below), as
  `sport-from-motion` did, when the figure alone needs its question to land.

If the image is already *inside* the article, use the original file (the real capture or figure),
not a regenerated version. Format PNG, JPG or WEBP in `public/blog/`, ideally 1200×627.

Show Javier finished candidates only: each one rendered and ready to ship as it is, so the choice
is between real options.
