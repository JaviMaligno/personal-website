# Blog hero image prompts

Exact prompts used to generate blog hero images (via Codex `image_gen`), for reproducibility and iteration. Newest first.

---

## restart-vs-iterate

- **Article:** `src/content/blog/en/restart-vs-iterate.md`
- **Image:** `public/blog/restart-vs-iterate.png`
- **Generated:** 2026-07-17 (Codex `image_gen`, editorial-illustration guide)

```text
Use case: infographic-diagram
Asset type: 1020×510 website blog hero image, wide 2:1 composition.
Primary request: Create a refined technical editorial illustration of an AI coding agent's iterative development loop with visible test feedback. Make the scene concrete and operational, not metaphorical.
Scene/backdrop: A dark graphite developer workstation/interface shown as a clean cutaway workflow. Divide the wide frame into several distinct but connected zones. The dominant center lane is a terminal and code workspace progressing through three visible rounds: “round 1” with “tests: 2/5”, “round 2” with “tests: 4/5”, and “round 3” with “tests: 5/5 pass”. Connect these states with restrained arrows or loop traces that visibly preserve and refine the same working tree. Add a small label “iterate”.
Subject: In the center, tangible terminal windows, code diff panels, test checkmarks and failure marks improving across rounds. In a narrower side lane, show discarded clean restart attempts as ghosted terminal sheets and a few crumpled paper-like code drafts dropping away, each resetting to an empty clean state; label one control “restart(all)” or “clean restart”. In a third small precision zone, show a surgical file-level revert: one file card being delicately plucked from a stack by a fine mechanical tweezer/tool, with the compact label “restart(file)”, while the rest of the working tree remains intact.
Style/medium: Refined technical editorial illustration; crisp geometric 2D/2.5D vector-like forms, subtle print texture, precise interface details, sophisticated data-journalism aesthetic, high visual hierarchy, no photorealism.
Composition/framing: Wide panoramic 2:1 layout, balanced asymmetry. Central iterate lane occupies about 60% of the image; discarded restart lane is clearly separate on one side; small surgical revert vignette balances the other side. Several distinct zones, not one centered icon. Leave comfortable margins and avoid tiny clutter.
Lighting/mood: Dark, focused, analytical, quietly optimistic as tests converge; high legibility and controlled contrast.
Color palette: Dark graphite and deep blue-black base, balanced teal for passing progress, amber for warnings/restarts, warm off-white for terminal surfaces and type, muted coral only for failed tests. Dark but not monochrome.
Text (verbatim where shown): “iterate”, “round 1”, “tests: 2/5”, “round 2”, “tests: 4/5”, “round 3”, “tests: 5/5 pass”, “restart(file)”. Text must be readable, generic, and limited to these short interface labels; omit a label if needed rather than rendering garbled text.
Constraints: Clearly communicate that iterative feedback improves one persistent attempt while repeated clean restarts discard work, and that a rare scoped file revert is precise and useful. No people or humanoid agents. No logos or brand names. No abstract metaphor as the primary scene. No text-heavy poster. No purple gradient blobs, no bokeh, no glossy neon cyberpunk look, no giant central icon, no decorative nonsense.
```

---

## coding-agents-structure

- **Article:** `src/content/blog/en/coding-agents-structure.md`
- **Image:** `public/blog/coding-agents-structure.png`
- **Generated:** 2026-07-12 (Codex `image_gen`, editorial-illustration guide)

```text
Use case: infographic-diagram
Asset type: blog hero image, 1020x510 px, horizontal 2:1.
Primary request: refined technical editorial illustration showing structured coordination between two coding agents: chaotic concurrent collaboration failing at merge, contrasted with ordered recovery through sequential handoff and an integrator.
Scene/backdrop: a dark technical desktop/workbench split into several concrete zones. Left zone: two separate developer workspaces/terminal panes labeled "agent A" and "agent B", with teal and amber diff lines flowing at the same time into a central graphite merge node labeled "merge conflict"; overlapping diff strips collide with small red/amber conflict markers and tangled commit lines. Right zone: clean recovery structures: top lane is a sequential pipeline labeled "feature 1" then "feature 2", where an "agent A" commit feeds into an "agent B" terminal; lower lane is an "integrator" terminal reconciling two patch streams into a single off-white build panel labeled "resolved build". Show concrete terminals, file diffs, commit graph lines, merge arrows, small status chips, and code-review-like panels; not an abstract icon-only metaphor.
Composition/framing: wide 2:1 editorial hero, multiple distinct zones rather than one centered icon, chaotic collision on the left and orderly pipeline/reconciliation on the right, diagonal flow from left to right, balanced negative space and clear hierarchy suitable for a blog header.
Style/medium: refined technical editorial illustration, crisp vector-like raster rendering, precise linework, subtle grain, mature engineering-magazine aesthetic.
Lighting/mood: dark but not monochrome, low-contrast graphite grid background, restrained luminous terminal screens.
Color palette: balanced teal, amber, graphite, and off-white accents on a dark base; tiny red conflict marks only where needed.
Text: sparse, readable, generic terminal/label text only: "agent A", "agent B", "feature 1", "feature 2", "merge conflict", "sequential handoff", "integrator", "resolved build".
Constraints: no people, no logos, no brand names, no product names, no mascots, no purple gradient blobs, no bokeh, no stock-photo look, no text-heavy poster, no abstract metaphor, no giant centered icon. Keep all text minimal and generic.
```

---

## Bootstrap the Environment, Not the Agent

- **Article:** `src/content/blog/en/bootstrap-the-environment-not-the-agent.md`
- **Image:** `public/blog/bootstrap-cloud-environments.png`
- **Generated:** 2026-07-08

```text
Create a 1020x510 blog hero image for a technical article titled "Bootstrap the Environment, Not the Agent". Style: refined technical editorial illustration, dark but not monochrome, showing a cloud development workspace being initialized by a small terminal script. Visual motifs: terminal window with readable but generic lines like "session-start.sh", package boxes labeled "TeX", "Python", "Build", arrows into cloud workspaces, a laptop and CI runner, clean geometric composition. No logos, no brand names, no people, no text-heavy poster. Use crisp bitmap illustration, high contrast, professional AI/developer blog aesthetic, balanced teal, amber, graphite, and off-white accents, no purple gradient blobs, no bokeh.
```

## repetition-edges-of-language (2026-07-15)

- Article: `src/content/blog/en/repetition-edges-of-language.md`
- Image: `public/blog/repetition-edges-of-language.png`
- Generated with: Gemini (Imagen) — Codex credits unavailable

```
Create a 1020x510 blog hero image for a technical article titled "Repetition at the Edges of Language". Style: refined technical editorial illustration, dark but not monochrome. Concrete scene: two side-by-side chat/terminal panels on a dark graphite desk. The LEFT panel shows a clean, composed assistant reply — a short line trailing into an ellipsis; the RIGHT panel shows the same interface degenerating into a runaway loop of one repeated token ("table table table…"), one line glitching. A faint input bubble at the top feeds both panels; a repetition-count meter climbs along the side. Readable generic monospace text, clean geometric composition. No logos, no people, no text-heavy poster. Crisp bitmap illustration, high contrast; teal, amber, graphite and off-white on dark; no purple gradient blobs, no bokeh.
```

## Ciphers at the Edges of Language (Part 2)

- Article: `src/content/blog/en/ciphers-edges-of-language.md`
- Image: `public/blog/ciphers-edges-of-language.png`
- Generated: 2026-07-18 with Codex CLI (gpt-image), delegated prompt

```
Create a 1020x510 blog hero image for a technical article about language models decoding ciphers and hitting a safety boundary. Style: refined technical editorial illustration, dark but not monochrome, concrete terminal/workspace scene. LEFT: panels of scrambled ciphertext ("Wklv", "uryyb", "... --- ...", "01001000") wired through a central lock/key motif (the Rosetta-stone key). RIGHT: decoded readable words ("This", "hello") pass a translucent barrier as teal signal streams, while other decoded messages ("SOS", "H") bounce off the barrier as amber blocked/refused streams with ✕ marks. Text (verbatim, only these): "Wklv", "uryyb", "... --- ...", "01001000", "This", "hello", "SOS", "H". Lighting: high contrast, controlled screen glow, analytical, ordered. Palette: deep graphite/blue-black foundation, balanced teal decoding signals, restrained amber refusal accents, off-white terminal text. No people, no logos, no brand names, no watermark, no title typography, no purple gradient blobs, no bokeh, no neon overload, clean geometric composition.
```
