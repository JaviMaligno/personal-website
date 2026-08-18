# Blog hero image prompts

Exact prompts used to generate blog hero images (via Codex `image_gen`), for reproducibility and iteration. Newest first.

---

## three-judges-three-rankings

- **Article:** `src/content/blog/en/three-judges-three-rankings.md`
- **Image:** `public/blog/three-judges-three-rankings.png`
- **Generated:** 2026-07-28 (Codex `image_gen`, editorial-illustration guide)

```text
Use case: infographic-diagram
Asset type: 1020x510 (exact 2:1 aspect ratio) blog hero image
Primary request: Create a refined technical editorial bitmap illustration of an LLM evaluation harness in action: three different anonymous LLM judges score the exact same blinded pair of answers, yet produce three different rankings. This must be a concrete system scene, not an abstract metaphor.
Scene/backdrop: Dark graphite developer workstation / evaluation dashboard, dark but not monochrome, with subtle grid structure and crisp panel borders.
Subject and composition: Clean wide geometric composition with several distinct zones. Center-left: two prominent side-by-side off-white answer cards labeled exactly “A” and “B”, with short neutral placeholder lines and no identifying names; a clear bidirectional swap arrow between the cards shows that presentation order is reversed. Upper-right: one scoreboard/ranking panel split into three equal columns labeled exactly “JUDGE 1”, “JUDGE 2”, “JUDGE 3”. Each column evaluates the same A/B pair but visibly disagrees: JUDGE 1 shows “A > B”, JUDGE 2 shows “B > A”, JUDGE 3 shows “A = B”; use compact score bars or ranked rows so the differing order is immediately legible. Thin connector lines lead from the same answer pair to all three judge columns. Lower-left: a compact terminal window with only these readable generic lines: “run.py --judges 3”, “blinded: true”, “swap_order: true”. Lower-right: a small, clearly legible bar chart titled exactly “BIAS DELTA”, with three unequal teal/amber bars and minimal axis marks. Keep every element within generous safe margins.
Style/medium: Crisp bitmap illustration with vector-like precision, refined technical editorial illustration, professional AI/developer blog aesthetic, clean sans-serif UI typography, sharp edges, restrained fine texture, high contrast, polished and publication-ready.
Color palette: Balanced teal, amber, graphite, charcoal, and off-white accents on a dark background; each zone is distinct while the whole image remains cohesive.
Lighting/mood: Controlled screen-like illumination, analytical, serious, elegant.
Text requirements: Render only the specified generic labels and lines, spelled exactly; no extra headline, prose, captions, model names, or decorative pseudo-text. Readable generic labels are good, but this must not become a text-heavy poster.
Constraints: 2:1 landscape hero composition; three anonymous judge modules must clearly receive the same two blinded answer cards; the ranking order/outcome must differ across all three columns; include the A/B swap arrow, small bias bar chart, and terminal window; no people, faces, hands, mascots, logos, brand names, real model names, trademarks, or watermark.
Avoid: abstract metaphor as the main concept, purple gradient blobs, purple-dominant palette, bokeh, lens flare, glossy sci-fi holograms, excessive glow, clutter, tiny unreadable text, photorealistic office scene, poster-like wall of text.
```

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

## expensive-form (2026-07-25)

- Article: `src/content/blog/en/expensive-form.md`
- Image: `public/blog/expensive-form.png`
- Generated with: Codex (gpt-image), prompt delegated to Codex from style constraints

```text
Use case: infographic-diagram
Asset type: 1020x510 technical blog hero image for the article "I Built an Expensive Form"
Primary request: Create a refined technical editorial illustration showing a concrete side-by-side scene that contrasts two ways of collecting the same regulatory-report information. The image must communicate that a sequential conversational form is slower and more expensive, while a single free-text narrative can populate many structured fields and leave only genuine gaps.
Scene/backdrop: dark graphite developer-workspace backdrop, not monochrome, divided into several distinct connected zones across a wide 2:1 landscape canvas.
Subject and composition: On the left third, show a long vertical chain of seven small chat bubbles/cards, each containing only one tiny field row; each step has a small circular loading spinner and an amber token-cost meter that visibly climbs from step to step. Add a subtle small latency clock beside this chain. In the center-right, show one large open free-text narrative panel with several short abstract text lines; clean teal arrows carry extracted values from that narrative into a compact structured form panel on the far right. In that compact form, most rows are visibly completed with teal checks or filled bars, while exactly two rows remain empty and highlighted in amber as gaps. Across the lower middle, integrate a graph/DAG of connected phase nodes: "intake" flows into "phase 1" and onward toward "confirm"; several intermediate phase nodes are greyed out and bypassed by a prominent curved teal arrow labeled "skip". Include a compact status chip reading "missing: 2 fields". Keep the zones visually connected but clearly separated, with the left side feeling repetitive and costly and the right side feeling efficient and resolved.
Style/medium: crisp bitmap editorial illustration with precise vector-like geometry, sharp UI panels, clean arrows, restrained subtle texture, professional AI/developer blog aesthetic; high contrast and polished, not a literal product screenshot.
Lighting/mood: controlled luminous edge highlights and quiet technical depth; analytical, elegant, calm.
Color palette: dark graphite background, balanced teal for successful extraction and bypass flow, amber for cost/latency/gaps, off-white for primary structure and readable labels, muted grey for skipped nodes.
Text (verbatim, render only these short generic labels): "intake", "phase 1", "missing: 2 fields", "confirm", "skip".
Constraints: exact wide 2:1 composition intended to be delivered at 1020x510; several distinct zones rather than one centered icon; readable hierarchy at blog-card scale; exactly two highlighted missing fields on the right; visibly multiple sequential chat steps on the left; preserve generous safe margins; no people, no logos, no brand names, no title text, no watermark.
Avoid: text-heavy poster, purple gradients or purple blobs, bokeh, neon cyberpunk clutter, photorealism, 3D mascots, generic centered chatbot icon, decorative code snippets, excessive tiny labels, illegible typography.
```

**Regenerated once.** The first attempt rendered the amber chip as `missing: 2 fields` followed by stray quote-like artefacts. Re-running the *same* prompt with this single sentence appended fixed it — and the second pass also came out richer (per-step latency column with a running total, labelled cost meters, four greyed phase nodes):

```text
Render the amber status chip text exactly as "missing: 2 fields" and end the text immediately after the final "s" in "fields"; do not add any trailing characters, quotation marks, punctuation, glyphs, or artefacts.
```

Lesson worth reusing: when an image model mangles a short label, re-run the same prompt with an explicit "end the text after this character, add nothing further" instruction. No need to redesign the composition.
## wheres-the-ball-3 (2026-07-26)

- Article: `src/content/blog/en/wheres-the-ball-3.md`
- Image: `public/blog/wheres-the-ball-3.png`
- Generated with: Codex (gpt-image), prompt delegated to Codex from style constraints

```text
Use case: infographic-diagram. Asset type: 1020 × 510 pixel landscape blog hero image (exact 2:1 aspect ratio).
Primary request: A refined technical editorial illustration that opens a machine-learning "black box" and reveals that it is computing interpretable geometry: a velocity-weighted centroid, where the running mass of players is heading. Show that elaborate topology is secondary and that the model has one overconfident blind spot around a loose ball in open space.
Scene/backdrop: A stylized top-down sports pitch on a deep graphite-blue field, with restrained pitch markings and generous clean margins. No stadium, crowd, or realistic people.
Subject: Abstract player dots distributed across the pitch, each with a crisp motion-vector arrow. Their arrows and visual weight converge toward a bright weighted-centroid crosshair. A small dark translucent rectangular "black box" is opening or peeling apart and transitioning seamlessly into a clean geometric diagram; inside/revealed from it are the centroid construction, weighted guide lines, and the inferred ball marker sitting precisely where the dominant arrows point. Include a very faint Voronoi/Delaunay-style triangulation mesh across part of the player cloud, visibly subordinate to the centroid. In a separate patch of open pitch, place a loose-ball marker ahead of trailing player vectors and flag that region with a subtle amber uncertainty/warning motif: a thin dashed halo or small caution notch, understated rather than alarmist.
Style/medium: Crisp bitmap illustration with vector-like precision; refined technical editorial art; professional AI/developer research blog aesthetic; diagrammatic but concrete.
Composition/framing: Wide 2:1 top-down composition. Make the box-opening-into-diagram transition the central visual idea. Keep the weighted-centroid crosshair as the strongest focal point, the topology mesh light and secondary, and the open-space warning region small but legible.
Lighting/mood: Dark, analytical, high contrast, quietly cinematic, precise; not monochrome.
Color palette: Deep graphite and blue-black background, balanced teal motion vectors, warm amber centroid and warning accents, off-white construction lines and pitch marks. No purple.
Text: at most one tiny compact legend-like label reading exactly "WEIGHTED CENTROID", clean uppercase technical sans-serif. No other text.
Avoid: purple gradient blobs, bokeh, glossy 3D rendering, photorealism, neon cyberpunk overload, clutter, illegible microtext, decorative topology dominating the image, large warning icons, generic circuit-board imagery.
## wheres-the-ball-4 (2026-07-27)

- Article: `src/content/blog/en/wheres-the-ball-4.md`
- Image: `public/blog/wheres-the-ball-4.png`
- Generated with: Codex (gpt-image), prompt delegated to Codex from style constraints

```text

Use case: infographic-diagram
Asset type: 1020×510 landscape blog hero image
Primary request: Create a refined technical editorial illustration that explains the counterintuitive finding: a motionless hidden ball is the hardest to locate because player motion provides no signal, while a ball in flight has a readable direction of travel from the players’ runs.
Scene/backdrop: A single top-down stylized football/soccer pitch on a dark graphite ground, with subtle pitch markings and restrained data-visualization overlays.
Subject: In open central space, show one small STILL off-white ball sitting alone, far from every player. Players are scattered around it and explicitly NOT converging; nearby player dots are static with no velocity arrows. Surround this ball with a faint broken/dashed undetermined halo and a subtle quiet greyed zone, communicating a blind spot and no usable signal. Elsewhere on the same pitch, show a ball IN FLIGHT moving fast, with a bright amber motion trail, a crisp teal-and-amber direction cone/arrow, and a clearly legible heading. Several player dots lean and run into that projected path, each with crisp velocity arrows aligned toward the flight corridor. Make the contrast between quiet stillness and directional energy unmistakable.
Style/medium: Crisp bitmap illustration; refined technical editorial art; clean geometric shapes; precise linework; high contrast; professional AI/developer research-blog aesthetic; dark but not monochrome; sophisticated and restrained, not a literal scientific chart.
Composition/framing: Exact 2:1 wide hero composition, designed to crop cleanly at 1020×510. Balanced visual weight across one continuous pitch. The isolated still-ball blind spot should be the central conceptual anchor; the flying-ball action should occupy a distinct secondary zone elsewhere without creating a split-screen or two separate panels. Keep generous breathing room and strong thumbnail readability.
Color palette: Balanced teal, amber, graphite, and off-white on a dark ground. Quiet zone in muted graphite-grey; flight zone brighter and energetic. Absolutely no purple.
Text (verbatim): “STILL = NO SIGNAL” — optional, at most once, tiny and unobtrusive near the dashed halo. No other text.
Constraints: Top-down view only. Player dots and abstract directional marks only; no realistic people. Static players around the still ball must have no arrows and must not converge. Flying ball must have a visible motion trail and an unambiguous direction cone. No logos, no brand names, no watermark, no decorative statistics, no text-heavy poster.
Avoid: purple; bokeh; photorealism; stadium crowds; realistic human figures; split-screen panels; neon cyberpunk glow; clutter; excessive labels; extra balls beyond the one still ball and one flying ball.
Exact prompt used:

Use case: infographic-diagram
Asset type: 1020×510 landscape blog hero image
Primary request: Create a refined technical editorial illustration that explains the counterintuitive finding: a motionless hidden ball is the hardest to locate because player motion provides no signal, while a ball in flight has a readable direction of travel from the players’ runs.
Scene/backdrop: A single top-down stylized football/soccer pitch on a dark graphite ground, with subtle pitch markings and restrained data-visualization overlays.
Subject: In open central space, show one small STILL off-white ball sitting alone, far from every player. Players are scattered around it and explicitly NOT converging; nearby player dots are static with no velocity arrows. Surround this ball with a faint broken/dashed undetermined halo and a subtle quiet greyed zone, communicating a blind spot and no usable signal. Elsewhere on the same pitch, show a ball IN FLIGHT moving fast, with a bright amber motion trail, a crisp teal-and-amber direction cone/arrow, and a clearly legible heading. Several player dots lean and run into that projected path, each with crisp velocity arrows aligned toward the flight corridor. Make the contrast between quiet stillness and directional energy unmistakable.
Style/medium: Crisp bitmap illustration; refined technical editorial art; clean geometric shapes; precise linework; high contrast; professional AI/developer research-blog aesthetic; dark but not monochrome; sophisticated and restrained, not a literal scientific chart.
Composition/framing: Exact 2:1 wide hero composition, designed to crop cleanly at 1020×510. Balanced visual weight across one continuous pitch. The isolated still-ball blind spot should be the central conceptual anchor; the flying-ball action should occupy a distinct secondary zone elsewhere without creating a split-screen or two separate panels. Keep generous breathing room and strong thumbnail readability.
Color palette: Balanced teal, amber, graphite, and off-white on a dark ground. Quiet zone in muted graphite-grey; flight zone brighter and energetic. Absolutely no purple.
Text (verbatim): “STILL = NO SIGNAL” — optional, at most once, tiny and unobtrusive near the dashed halo. No other text.
Constraints: Top-down view only. Player dots and abstract directional marks only; no realistic people. Static players around the still ball must have no arrows and must not converge. Flying ball must have a visible motion trail and an unambiguous direction cone. No logos, no brand names, no watermark, no decorative statistics, no text-heavy poster.
Avoid: purple; bokeh; photorealism; stadium crowds; realistic human figures; split-screen panels; neon cyberpunk glow; clutter; excessive labels; extra balls beyond the one still ball and one flying ball.
```

## confident-about-unreadable-text (2026-07-30)

- Article: `src/content/blog/en/confident-about-unreadable-text.md`
- Image: `public/blog/confident-about-unreadable-text.png`
- Generated with: Codex (gpt-image), prompt delegated to Codex from style constraints

Came out clean on the first pass, including every label — unusual for this many
short strings in one image. The winning move was giving Codex the article's
*mechanism* (three machines emitting confident verdicts about text they cannot
read) rather than a mood: it turned that into three literally labelled machine
zones on one conveyor, which is the article's thesis readable at feed scale.
Chosen over the kappa chart as the LinkedIn image for that reason.

```text
Use case: stylized-concept
Asset type: 1020×510 wide blog hero image (exact 2:1 aspect ratio), designed to crop cleanly at the edges.
Primary request: Create a refined technical editorial illustration of a working three-stage inspection and scoring pipeline in which three machines confidently issue structured outputs about text they cannot actually read.
Scene/backdrop: A dense, dark industrial-computing workbench viewed in a slightly elevated three-quarter perspective. One continuous conveyor or data rail carries narrow off-white strips of visibly garbled encoded text through three distinct adjacent machine zones. Zone 1 is a content-safety scanner inspecting a strip marked "base64" with a short cipher string such as "cmVwbHkgd2l0aA=="; despite the unreadable input, its crisp output card is stamped "severity: medium" and an amber confidence gauge is high. Zone 2 is an evaluation judge inspecting a visibly half-decoded, broken reply; its scanner head confidently stamps a compact verdict card reading "label: garbled" with a teal/amber gauge. Zone 3 is a base language-model terminal or mechanical text emitter taking cipher strips as input and streaming fluent-looking ciphertext onward even though its comprehension gauge reads empty or disconnected; show neat patterned cipher output but no actual understanding. Include small cables, rollers, scan beams, status lamps, card trays, terminal panes, meter ticks, and encoded strips so the scene feels like a real operating system rather than an abstract metaphor.
Style/medium: Crisp bitmap technical editorial illustration; precise hard-edged forms, subtle pixel-level texture, clean diagrammatic machinery, professional AI/developer blog aesthetic, high contrast, sophisticated and serious. Dark but not monochrome.
Composition/framing: Wide cinematic 2:1 layout with three clearly distinct zones across the frame, connected left-to-right by the data conveyor. Several focal clusters rather than one centered icon. Dense but legible, balanced negative space around the key verdict cards, strong visual hierarchy. No people.
Lighting/mood: Controlled low-key workstation lighting, scanner glows and instrument lamps; confident machinery contrasted with visibly nonsensical input. No dreamy atmosphere.
Color palette: Graphite and deep blue-black background; balanced teal, amber, warm off-white, muted steel and small restrained red warning accents. No purple.
Text (verbatim, only these short generic labels where useful): "base64", "severity: medium", "label: garbled". Ciphertext may be short generic alphanumeric fragments. Keep all text sparse, crisp, correctly spelled, and secondary to the scene.
Constraints: The core idea must read immediately: three operational machines give confident, structured outputs about unreadable text. Depict a concrete inspection/scoring pipeline with visible input strips, scanner heads, gauges, output verdict cards, and terminal output. Maintain exact 1020×510 / 2:1 hero composition. No logos, no brand names, no real company names, no people.
Avoid: abstract metaphor, single centered icon, text-heavy poster, purple gradient blobs, bokeh, photorealism, glossy 3D render, generic sci-fi spaceship interface, excessive neon, illegible wall of UI text, watermark, logo, brand marks.
```

## what-you-still-need-to-know-to-ship (2026-08-02)

- Article: `src/content/blog/en/what-you-still-need-to-know-to-ship.md`
- Images: `public/blog/what-you-still-need-to-know-to-ship.png` (hero, the loop),
  `public/blog/what-you-still-need-to-know-map.png`,
  `public/blog/what-you-still-need-to-know-toy-vs-production.png`
- Generated with: Codex (gpt-image), prompt delegated to Codex from a brief

Three **diagrams**, not editorial illustrations — a different job from the usual
hero. The style constraints that carried over: 1020x510, dark but not
monochrome, teal/amber/graphite/off-white, no logos, no people, no purple blobs,
no bokeh. The constraint that mattered most and is worth reusing for diagrams:
*legibility at small size beats density — this is a diagram people will
screenshot*. All three came out with correctly spelled labels on the first pass.

### 1. Hero — the loop

Codex's full prompt (delegated from the brief below):

```text
Use case: infographic-diagram
Asset type: hero image and LinkedIn social card for a technical editorial article, final canvas 1020x510 (2:1 landscape)
Primary request: Create a refined technical editorial DIAGRAM of a four-phase clockwise working loop: "Specify" -> "Build" -> "Check" -> "Correct" -> back to "Specify". The central idea must be instantly clear: the agent participates in ALL FOUR phases, while each phase leaves a different human residue. Show one continuous agent-presence track or visual system running through all four nodes. Pair each phase with exactly one concise human-residue label:
Specify — "Intent stays human"
Build — "Fully delegated"
Check — "Know what to check"
Correct — "Fix / rebuild / drop"
Visually mark Build as the unique phase fully handed over: a filled or strongly highlighted teal node, a clear handover marker, and the small label "FULLY DELEGATED". The other three nodes retain a subtle human-residue marker. Do not depict people.
Scene/backdrop: deep graphite editorial canvas with restrained grid or fine technical linework only if useful.
Style/medium: polished flat vector-like systems diagram, crisp geometric forms, precise arrows, modern editorial typography, sophisticated but minimal.
Composition/framing: wide 2:1 canvas; a large balanced clockwise loop centered on the page; four generously spaced phase nodes; unambiguous arrow returning Correct to Specify; clear hierarchy; ample negative space; all text comfortably inside safe margins and readable at LinkedIn-card size.
Color palette: dark graphite background, balanced teal, amber, warm off-white, and muted graphite-gray accents; not monochrome.
Text (verbatim): "Specify", "Build", "Check", "Correct", "Intent stays human", "Fully delegated", "Know what to check", "Fix / rebuild / drop", "FULLY DELEGATED"
Constraints: diagram, not decorative illustration; spell every label exactly; agent visibly participates in all four phases; Build is visibly the only fully handed-over phase; concise labels only; clean line weights; strong contrast; screenshot-worthy at small size.
Avoid: logos, brand names, people, hands, faces, characters, purple gradient blobs, bokeh, photorealism, 3D objects, ornamental clutter, dense prose, poster styling, extra labels, illegible microtext, watermarks.
```

**Regenerated once, for a conceptual correction.** The first pass marked only
Build as fully delegated. Correcting is building again — the agent does it end
to end — so `Correct` is delegated too, and a failure that makes you rebuild or
drop the whole thing isn't a correction, it's a return to Specify. The loop
therefore halves: Specify and Check keep a human residue, Build and Correct
don't. The regeneration brief asked for that halving to be *visible*, and the
model resolved it well: the two delegated nodes on the horizontal axis in teal
with a shared FULLY DELEGATED bracket each side, the two residue nodes on the
vertical axis in dark with amber labels, joined by a dashed line, plus a legend.

The first version also rendered "Fully delegated" twice on the same node
(inside it and in a side callout); the regeneration brief named that duplication
explicitly and it went away.

### 2. The map — regenerated once, for a colour-coding fault

The first pass was compositionally good (the title *"Your level is a vector, not
a number"* carries the thesis without the article, five grouped family cards,
the Taste row detached below a dashed rule) but **colour encoded two
contradictory things at once**: the legend assigned colours to levels while the
meters used a different colour per row, and one colour (blue) appeared in the
meters but not in the legend.

The regeneration brief, whose fix is the reusable part:

```text
Colour and level must be strictly separated:
- EVERY meter is three equal segments. The NUMBER of filled segments — and
  nothing else — encodes the level: 1 = Aware, 2 = Fluent, 3 = Opinionated.
- ALL filled segments across the whole image use the SAME single colour (teal).
  Empty segments are dark grey outlines. No amber, no blue, no other colour
  anywhere in any meter.
- The legend shows three example meters with 1, 2 and 3 teal segments filled,
  labelled Aware / Fluent / Opinionated. Same teal as the meters.
- Family header colours may still differ from each other to group the cards, but
  no family colour may ever appear inside a meter.
Fill levels unevenly on purpose so the profile reads as jagged.
```

Lesson worth reusing: when a diagram carries both a *grouping* dimension and a
*magnitude* dimension, say explicitly which visual channel owns which, and ban
the other channel by name. "Use colour consistently" is not enough — the model
will happily invent a second, contradictory colour scheme.

### 3. Toy vs production

Brief given to Codex (its expanded prompt was not captured in full):

```text
A two-column comparison DIAGRAM: the same project as a toy versus as a
production system. Six rows, each contrasting left (toy) with right (production):
1. runs on my laptop -> lives on the internet
2. key inside the code -> key in a secret manager
3. data in a local file -> remote database with backups
4. anyone can call the API -> auth and limits in place
5. nobody checks this box -> every box has someone checking it
6. nothing written down -> documentation the agent reads

Row 5 is the thesis of the whole image and should read as the most important
one: production is not better code, it is that no category is left unchecked.
Give that row visual emphasis.

Two clearly separated columns with headers 'TOY' and 'PRODUCTION'; short
readable labels; the toy column in muted graphite/amber, the production column
in teal. Legible at LinkedIn card size.
```

Giving one row an explicit "this is the thesis" instruction worked: the model
boxed and brightened row 5 without being told how.

### Spanish versions (2026-08-02)

All three regenerated with Spanish text rather than reused, because a map full
of English labels inside a Spanish article reads badly. Files carry an `-es`
suffix. The briefs are the English ones translated, with one instruction added
that turned out to matter: **point Codex at the English PNG as the visual
reference** ("look at that file: reproduce the same concept, layout, palette and
quality, with all text in Spanish"). The map and the comparison came out right
first time that way.

The loop needed one regeneration, for two faults worth remembering:

1. **It drew a cartoon robot** for the agent. "No people" does not imply "no
   robots" — the English version's abstract node glyph had to be asked for by
   name. Ban mascots explicitly when a diagram has an agent in it.
2. **Amber leaked onto the cycle arrows**, where it meant nothing, while the
   legend used amber for "human residue". Same class of fault as the map's first
   pass: a reserved colour has to be reserved *out loud*, naming the elements
   that must not use it.

Fixed with: "Cycle arrows must be neutral off-white/grey. Amber is reserved
exclusively for the two human-residue phases and their labels. Teal is reserved
exclusively for the two fully delegated phases."

## if-youre-starting-from-zero (2026-08-05)

- Article: `src/content/blog/en/if-youre-starting-from-zero.md`
- Images: `public/blog/if-youre-starting-from-zero.png`, `...-es.png`
- Generated with: Codex (gpt-image), prompt delegated from a brief

The brief described the article's *structure* rather than its topic: four tiers
in priority order, derived from "when this goes wrong, who pays", with the
irreversible group weighted heaviest. That is what made the image carry an idea
instead of decorating one — the hierarchy is the content.

Per-tier motifs were specified concretely (database with a restore arrow, key
and padlock and users, invoice with a rising curve and a warning sign,
checklist), which is what keeps a diagram from drifting into generic icons.

Both came out right first time. The Spanish one leans more typographic than the
English one — heavier labels, thinner icons — but the hierarchy and colour
coding match, so they were kept as they are.

**Codex failed once mid-run** with `stream disconnected before completion` after
exhausting five reconnect attempts against its own backend. Nothing to fix: the
same command re-run produced the image. Worth knowing so a failed generation
isn't mistaken for a bad prompt.

## `what-has-already-happened` — Your Agent Doesn't Know What Has Already Happened

- Article: `src/content/blog/{en,es}/what-has-already-happened.md`
- Hero: `public/blog/what-has-already-happened.png` — **generated with ChatGPT**
  (gpt-image), 12-ago-2026, from the prompt below. Codex was unavailable (workspace
  spend cap), so the prompt was written here and run there by hand.
- LinkedIn: `public/blog/what-has-already-happened-data.png` — a typeset HTML card
  with the study's actual numbers, source at
  `docs/marketing/hero-sources/what-has-already-happened.html`.

**Why two images.** The hero is an editorial illustration, consistent with the rest
of the blog. The LinkedIn card carries the four real percentages and two verbatim
strings from the study, because in the feed a concrete number stops the scroll
better than an illustration — same split as `forgetting-you-dont-measure`.

The prompt, verbatim:

```
Create a 1536x1024 blog hero image for a technical article titled "Your Agent
Doesn't Know What Has Already Happened".

Style: refined technical editorial illustration, dark but not monochrome. Concrete
scene: a project workspace where a coding agent is reasoning about a schedule and
getting the sequence wrong.

Composition, left to right:
- A horizontal timeline dividing the board: the left half solid and stamped
  "FROZEN — JULY" over a small stack of bound documents; the right half drawn only
  in outline, an empty booked studio slot still ahead.
- In the centre, a document page with one sentence highlighted in amber, and a red
  dotted arrow that jumps over the highlighted sentence instead of through it.
- Two numbered cards, "V3" and "V4", joined by a red dotted dependency arrow that
  clearly should not be there — the cards are already stamped as finished.
- Top right, a small wall calendar with a date, drawn faded and set aside, visibly
  not connected to anything else on the board.

Keep text extremely sparse: only the short labels FROZEN, JULY, V3, V4. No
paragraphs, no dense UI text, no poster of words.

No logos, no brand names, no people, no faces, no purple gradient blobs, no bokeh.
Crisp bitmap illustration, high contrast, professional AI/developer blog aesthetic,
balanced teal, amber, graphite and off-white accents on a dark background.
```

What worked, worth reusing:

- **Asking for four short labels only.** FROZEN, JULY, V3, V4 all rendered
  perfectly, no artefacts. The failure mode of image models is dense text, not text
  as such — naming the exact strings allowed is what keeps them clean.
- **Describing the composition left-to-right** instead of listing motifs. The
  timeline going from solid to dashed, and the arrow *jumping over* the highlighted
  sentence rather than through it, both came out exactly as specified.
- **Stating the semantics of each element** ("a dependency arrow that clearly should
  not be there", "already stamped as finished") rather than just its appearance.

Crop: the source is 3:2 (1536x1024) and the hero needs 2:1, so 256px of height come
off. Crop from `top=100`, keeping the full width:

```python
from PIL import Image
src = Image.open("<downloaded>.png")
W, _ = src.size
src.crop((0, 100, W, 100 + W // 2)).resize((1020, 510), Image.LANCZOS)    .save("public/blog/what-has-already-happened.png", optimize=True)
```

`top=100` over `top=30`: the higher crop keeps the whole wall calendar but cuts the
V3/V4 cards off at the bottom edge, and those cards are the article's central image
while the calendar is the secondary finding.
---

## `perception-edges-of-language` — "One Grey Level Out of 255"

- **Article**: `src/content/blog/en/perception-edges-of-language.md`
- **Image**: `public/blog/perception-edges-of-language.png` (also used as `linkedinImage`)
- **Generated**: 2026-08-06
- **Generator**: none — **rendered programmatically from the experiment's own code**, not
  from an image model.

Every automated route was unavailable that day, which is worth recording because two of the
three are still broken:

- **Codex**: `ERROR: Your workspace is out of credits.`
- **Hugging Face**: `scripts/generate-thumbnails.py` targets `FLUX.1-schnell` on
  `hf-inference`, which now returns *"The requested model is deprecated and no longer
  supported by provider hf-inference"*. FLUX.1-dev and SDXL return the same; Qwen-Image and
  SD 3.5 return *"Model not supported by provider"*. **That script is dead as written** and
  needs a different provider route before it works again.
- **Gemini**: no `GEMINI_API_KEY` present in `.env` or the environment (the key the LinkedIn
  scripts expect is for text summaries and was not set).

So the hero is the stimulus itself: the seven contrast levels of the study rendered by
`llm_language_limits.render`, with the human threshold and the faintest machine-readable row
marked. Two rules made it work, both learned by getting them wrong first:

1. **Crop, never resize.** Rescaling averages neighbouring pixels and destroys precisely the
   faint grey the image exists to show — the first attempt rescaled 768x192 panels to 580x40
   and made every level below 0.04 invisible *because of the hero*, not because of the data.
2. **The annotation has to match the published number.** The first version drew the human
   threshold between 0.02 and 0.012, which is the contaminated batch-1 figure (0.016) that
   the article itself spends a section retracting. The correct 0.030 sits between 0.04 and
   0.02.

The prompt drafted for the image models, kept here in case one of those routes comes back:

```
A 1020x510 blog hero image, refined technical editorial illustration, dark but not
monochrome. A psychophysics reading bench: stacked white panels each showing the same
short line of text at descending contrast, crisp black at the top fading to a blank
panel at the bottom. Small labelled tags reading "contrast 0.004", "grey 254/255",
"threshold 50%". To the right, a threshold curve crossing a dashed 50% line, and two
small boxes marked OCR and MODEL with arrows pointing at the faintest panel. A magnifier
resting on the desk. Clean geometric composition, several distinct zones. No logos, no
brand names, no people, no text-heavy poster. Crisp bitmap illustration, high contrast,
professional AI/developer blog aesthetic, balanced teal, amber, graphite and off-white
accents on dark, no purple gradient blobs, no bokeh.

---

## the-scaffolding-you-pay-for

- **Artículo:** `src/content/blog/{en,es}/the-scaffolding-you-pay-for.md`
- **Imagen:** `public/blog/the-scaffolding-you-pay-for.png` (1020×510)
- **Generada:** 2026-08-15, Codex 0.147.0 (`codex exec -s workspace-write`)

Dos pasadas. La primera salió compositivamente bien a la primera, pero **Codex se
inventó las métricas** (5 vs 14 turnos, $0,04 vs $0,42 — una diferencia de 10×).
En un artículo cuyo tema es medir, unas cifras inventadas en el hero se leen como
resultados del estudio. La segunda pasada reusa la composición y sustituye los
números por los reales, pidiendo además que la proporción visual sea honesta
(2,3× en tokens y 1,6× en coste, no 10×).

**Lección para el resto de artículos con datos: si el hero lleva cifras, hay que
dárselas explícitamente y comprobarlas en la imagen final.** El modelo rellena
huecos numéricos con lo que resulta visualmente vistoso.

Prompt de la segunda pasada:

```text
The hero at public/blog/the-scaffolding-you-pay-for.png is very good
compositionally: two lanes (LEAN vs PROCEDURAL), same task, terminals, metrics
panels, file trees. Keep that exact composition and style.

One thing must change: the numbers shown are invented, and this article is about
measured results, so the figures in the image have to be the REAL ones:

LEAN LANE (label it 'FREE'):   turns 26, tokens 9.7K, cost $1.16,
                               outcome: source updated, '19 passed'
PROCEDURAL LANE (label 'SKILL'): turns 31, tokens 22.5K, cost $1.88,
                               outcome: docs/plans/plan.md written, source untouched

Keep the difference visually legible but proportionate to those real values — the
procedural lane is roughly 2.3x the tokens and 1.6x the cost, NOT ten times.

Everything else stays: same 1020x510 size, same dark graphite + teal + amber
palette, same readable generic terminal lines and file trees, no logos, no people.
```

---

## `infer-the-rule-in-one-dimension` — PENDIENTE DE GENERAR

- Artículo: `src/content/blog/en/infer-the-rule-in-one-dimension.md`
- Imagen destino: `public/blog/infer-the-rule-in-one-dimension.png`
- Estado: **no generada**. El intento con Codex falló con *"Your workspace is out
  of credits"*, así que el prompt queda escrito para ejecutarlo desde otra cuenta.

Las cifras van explícitas en el prompt siguiendo la lección del artículo anterior
(el modelo rellena huecos numéricos con lo que le resulta vistoso). Las dos que
aparecen son las reales del paper: **105/111** en la regla 1D y **0/156** en la 2D.
El `8.0` del panel izquierdo es la constante verdadera del muro y el `2.0` del
derecho es el semiplano que los artefactos escriben de verdad, en el borde oeste
del disco — conviene mantenerlos.

Comando (desde la raíz del repo, con créditos disponibles):

```bash
codex exec -s workspace-write "$(cat docs/marketing/prompt-infer-the-rule.txt)"
```

Prompt:

```text
Create a 1020x510 blog hero image for a technical article titled "An LLM Can Infer
the Rule You Forgot - in One Dimension". Save it to
public/blog/infer-the-rule-in-one-dimension.png

Style: refined technical editorial illustration, dark but not monochrome. A
CONCRETE SCENE contrasting two control experiments side by side, split down the
middle.

LEFT PANEL - "1D", the success:
A cart on a straight horizontal rail meeting a solid vertical wall. Above it a
small code panel with the readable line:  if x >= 8.0: stop()  marked with a green
check. A short caption strip reading  105 / 111.

RIGHT PANEL - "2D", the failure:
A top-down view of a plane with a circular region. A moving dot enters the circle.
Contact dots are scattered around only ONE arc of the circle, leaving the rest of
the circumference bare. A small code panel with the readable line:
if x >= 2.0:  marked with a red cross, and a straight dashed line cutting the plane
to show a half-plane guessed where a circle belongs. A caption strip reading  0 / 156.

Those two figures, 105/111 and 0/156, are real measured results and must appear
exactly as written. Do not invent any other numbers or statistics anywhere in the
image.

Visual motifs: the rail and the wall, the circle with contacts on a partial arc,
the two small code panels with readable but generic text, thin measurement
annotations with tick marks.
No logos, no brand names, no people, no text-heavy poster.
Crisp bitmap illustration, high contrast, professional AI/developer blog
aesthetic, balanced teal, amber, graphite and off-white accents on dark. No purple
gradient blobs, no bokeh.
```

Al recibir la imagen: revisarla (sobre todo que `105 / 111`, `0 / 156`, `8.0` y
`2.0` estén bien escritos — los modelos de imagen destrozan etiquetas), colocarla
en `public/blog/infer-the-rule-in-one-dimension.png` y mover esta entrada a
generada con la fecha.
