# Blog hero image prompts

Exact prompts used to generate blog hero images (via Codex `image_gen`), for reproducibility and iteration. Newest first.

---

## wheres-the-ball

- **Article:** `src/content/blog/en/wheres-the-ball.md`
- **Image:** `public/blog/wheres-the-ball.png`
- **Generated:** 2026-07-23 (Codex `image_gen`, editorial-illustration guide)

```text
Use case: infographic-diagram
Asset type: 1020x510 px website blog hero image, exact wide 2:1 composition.
Primary request: Create a refined technical editorial illustration for an article titled “Where’s the Ball? Testing Whether a VLM Has a Spectator’s Intuition.” Show a concrete computer-vision experiment in which the football has been removed from broadcast footage and an AI must infer its location only from the players, while statistical controls expose how easy it is to reach the wrong conclusion.
Scene/backdrop: A dark graphite sports-analysis workstation seen from a slightly elevated three-quarter top-down view, divided into three connected zones. The dominant central zone is a broadcast-analysis monitor containing a crisp oblique view of a green football pitch with small generic player figures clustering, leaning, and orienting toward one area. The ball itself is completely absent. Subtle teal gaze/orientation traces converge near a small dashed off-white prediction reticle, while an amber crosshair at the geometric center represents the misleading camera-center baseline. A compact scan/status strip reads “BALL: HIDDEN”.
Supporting zone one: at one side, show the inpainting and inference pipeline as two small stacked frame cards: an input crop with a tiny ball-sized marker, then a clean reconstructed grass patch labeled “INPAINT”, feeding into a coordinate panel labeled “PREDICTION”. Keep it operational and visually plausible, not decorative.
Supporting zone two: at the other side, show the methodology audit: a small confidence-interval plot with a wide amber interval crossing a dashed “CHANCE” line and a tighter teal interval beside it, plus a short label “BOOTSTRAP CI”. Beneath it, four miniature football-frame cards appear in deliberately shuffled order “1 4 2 3”, connected to a compact “MULTI-VIEW” node while a motion-path icon is crossed out, conveying that extra views help but temporal order does not.
Style/medium: refined technical editorial illustration; crisp bitmap rendering with vector-like geometric forms, precise linework, subtle print grain and restrained screen glow; mature engineering/science-magazine aesthetic; no photorealism.
Composition/framing: exact panoramic 2:1 hero ratio; central pitch monitor occupies roughly 55% of the frame, flanked by the smaller pipeline and audit zones; clear left-to-right experimental flow, balanced asymmetry, comfortable margins, dense enough to reward inspection but readable at card size. No title typography.
Lighting/mood: dark but not monochrome, analytical, curious, slightly skeptical; controlled contrast and high legibility.
Color palette: deep graphite and blue-black base, believable muted pitch green, balanced teal inference signals, amber baseline/warning accents, warm off-white surfaces and type, tiny muted coral only for the crossed-out motion symbol.
Text (render only these short generic labels, readable where possible): “BALL: HIDDEN”, “INPAINT”, “PREDICTION”, “BOOTSTRAP CI”, “CHANCE”, “MULTI-VIEW”, and frame numbers “1 4 2 3”. Omit a label rather than rendering garbled pseudo-text.
Constraints: the football must be visibly absent from the main pitch; communicate inference from player orientation, camera-center confounding, statistical uncertainty, and shuffled multi-view frames. No people outside the tiny anonymous player figures on the pitch. No faces. No logos, brand names, product names, team crests, model names, mascots, watermark, text-heavy poster, giant centered icon, floating robot, glowing brain, purple gradient blobs, bokeh, glossy neon cyberpunk, stock-photo look, or decorative nonsense.
```

---

## bring-your-app-to-the-agent

- **Article:** `src/content/blog/en/bring-your-app-to-the-agent.md`
- **Image:** `public/blog/bring-your-app-to-the-agent.png`
- **Generated:** 2026-07-19 (Codex `image_gen`, editorial-illustration guide)

```text
Use case: infographic-diagram
Asset type: blog hero image, 1020x510 px, horizontal 2:1.
Primary request: refined technical editorial illustration showing three stacked paradigms of software design, with the emphasis on the third: an application being plugged INTO an AI agent instead of standing alone. Convey the inversion — not an agent inside an app, but an app inside the agent the user already uses.
Scene/backdrop: a dark technical workbench arranged as three left-to-right zones that layer forward. Zone one (back, faded): a standalone application window labeled "app" facing a small generic user glyph — the classic destination. Zone two (middle): the same app window with a small assistant chip docked inside it labeled "copilot", a chat bubble embedded in a corner. Zone three (front, brightest, largest): a central assistant/agent panel labeled "agent" acting as a hub, with several small capability modules labeled "tools" docking into it through clean socket connectors; teal connector lines flow from the app's capabilities into the agent panel, and one off-white response card reads a short generic result. A thin connector rail labeled "MCP" links the app's tools to the agent socket to signal the current plumbing.
Composition/framing: wide 2:1 editorial hero, three distinct depth-layered zones receding back-to-front, diagonal flow of capability lines from the app into the agent, balanced negative space, clear hierarchy suitable for a blog header.
Style/medium: refined technical editorial illustration, crisp vector-like raster rendering, precise linework, subtle grain, mature engineering-magazine aesthetic.
Lighting/mood: dark but not monochrome, low-contrast graphite grid background, restrained luminous panel screens with the front agent zone most lit.
Color palette: balanced teal, amber, graphite, and off-white accents on a dark base.
Text: sparse, readable, generic UI/label text only: "app", "copilot", "agent", "tools", "MCP".
Constraints: no people (a single tiny abstract user glyph is fine), no logos, no brand names, no product names, no mascots, no purple gradient blobs, no bokeh, no stock-photo look, no text-heavy poster, no giant centered icon. Keep all text minimal and generic.
```

---

## internal-context-leakage

- **Article:** `src/content/blog/en/internal-context-leakage.md`
- **Image:** `public/blog/internal-context-leakage.png`
- **Generated:** 2026-07-19 (Codex `image_gen`, editorial-illustration guide)

```text
Use case: infographic-diagram
Asset type: 1020×510 website blog hero image, wide 2:1 composition.
Primary request: Create a refined technical editorial illustration contrasting how internal working context leaks into a client-facing deliverable versus how an isolated pipeline keeps it out. Make the scene concrete and operational, not metaphorical.
Scene/backdrop: A dark graphite developer workstation shown as a clean cutaway workflow, split into two horizontal lanes that both flow left-to-right from a shared "internal context" source panel toward a "deliverable" panel. On the left, a single source container labeled "internal context" holds several tagged chips: "spec 3.2", "codename F-12", "feedback note". Top lane ("leak"): those internal chips flow unfiltered straight through into a client document panel labeled "client email", where they appear embedded inside the text with small amber/coral warning markers; label this lane "leak". Bottom lane ("isolated"): the same chips flow toward the deliverable but hit a clear vertical boundary — a membrane/gate labeled "isolate" with a small deterministic filter labeled "lint gate" — where the internal chips are stopped and held back, so the client document panel on the right emerges clean with a teal check labeled "clean".
Subject: tangible interface elements — a source panel with tagged chips, connective flow arrows/traces, a boundary membrane, a small filter/gate node, and two client-document panels (one contaminated with embedded internal chips, one clean). Not an abstract icon-only metaphor.
Style/medium: Refined technical editorial illustration; crisp geometric 2D/2.5D vector-like forms, subtle print texture, precise interface details, sophisticated data-journalism aesthetic, high visual hierarchy, no photorealism.
Composition/framing: Wide panoramic 2:1 layout, balanced asymmetry, two clearly separated horizontal lanes sharing one source on the left, diagonal left-to-right flow, comfortable margins, no tiny clutter.
Lighting/mood: Dark, focused, analytical; controlled contrast, high legibility.
Color palette: Dark graphite and deep blue-black base, balanced teal for clean/passing state, amber for internal chips and warnings, warm off-white for document surfaces and type, muted coral only for the leak markers. Dark but not monochrome.
Text (verbatim where shown): "internal context", "spec 3.2", "codename F-12", "feedback note", "leak", "isolate", "lint gate", "client email", "clean". Text must be readable, generic, and limited to these short interface labels; omit a label if needed rather than rendering garbled text.
Constraints: Clearly communicate that unfiltered internal context contaminates the deliverable while an isolation boundary + deterministic gate keeps it out. No people or humanoid agents. No logos or brand names. No abstract metaphor as the primary scene. No text-heavy poster. No purple gradient blobs, no bokeh, no glossy neon cyberpunk look, no giant central icon, no decorative nonsense.
```

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

## writing-a-research-paper-with-ai (2026-07-19)

- Article: `src/content/blog/en/writing-a-research-paper-with-ai.md`
- Image: `public/blog/writing-a-research-paper-with-ai.png`
- Generated with: Codex (gpt-image), prompt delegated to Codex from style constraints

```text
Use case: scientific-educational. Asset type: 1020x510 landscape blog hero image for a technical AI/developer article.
Primary request: Show that advanced AI intelligence matters in planning science and peer review, not prose writing. Depict a concrete researcher's workspace where a flawed experimental-design document is being reviewed and materially improved.
Scene: Dark graphite desktop, slightly elevated three-quarter top-down perspective, organized like a real research workstation.
Subject: A before-versus-after scientific plan. Left: a rough "EXPERIMENTAL DESIGN (DRAFT)" page with a red-flagged error and a struck-through line. Right: a cleaner "EXPERIMENTAL DESIGN (REVISED)" plan reorganized into controlled stages with an oracle-baseline check. Review marks connect the flaw to the correction.
Scientific motif: a compact geometry diagram of a curved boundary reconstructed from scattered sample points — sparse teal/amber points around a smooth closed region, dashed attempt on the flawed side, cleaner solid reconstruction on the revised side.
Reviewer structure: two distinct review lenses/panels ("CAUSAL", "INFORMATION") examining the plan from separate angles; a human researcher's hands and pen at the bottom edge (no face); a "HUMAN JUDGMENT" sticky note. Three viewpoints legible through separate annotation colors.
Supporting detail: a small terminal window with exactly one commit line: "spec: redesign per expert review". A couple of short callouts: "CONFOUND", "ADD CONTROL". Text minimal and generic.
Style: crisp bitmap technical editorial illustration, precise geometric shapes, subtle paper/screen texture, high contrast, professional AI/developer blog aesthetic.
Composition: exact 2:1 wide hero, distinct-but-unified zones. Palette: dark graphite / deep blue-black base with balanced teal, amber, off-white, restrained red error accents. Dark but not monochrome.
Avoid: purple gradient blobs, bokeh, glowing brain imagery, robot characters, floating abstract metaphors, excessive equations, dense paragraphs, decorative pseudo-text, cyberpunk neon, photorealistic stock-photo look. No logos, no brand names, no real AI model names, no watermark.
```
