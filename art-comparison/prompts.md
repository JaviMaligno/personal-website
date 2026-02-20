# Art Comparison — Prompt Registry

All prompts used across models and modalities for reproducibility.

---

## 1. Image Generation (Text-to-Image)

Used for both Flux (API) and Gemini (manual). Same prompts for fair comparison.

### 01 - Op Art
```
Op art black and white optical illusion, concentric circles creating 3D sphere bulge effect, Victor Vasarely style, high contrast, geometric precision, hypnotic pattern
```

### 02 - Japanese Landscape
```
Minimalist Japanese landscape, single cherry blossom tree on gentle hill, soft pink and grey palette, negative space, ukiyo-e influenced, serene atmosphere, distant misty mountains, falling petals, contemplative mood
```

### 03 - Retro Poster
```
Vintage 1960s Swiss International Style jazz festival poster, bold Helvetica typography, geometric shapes, limited color palette of deep orange red cream and charcoal, abstract saxophone player silhouette, Zurich 1965, Bauhaus influenced grid layout
```

### 04 - Abstract Expressionist
```
Abstract expressionist painting, bold dramatic brush strokes in deep blue and gold amber, Franz Kline inspired black gestures, Rothko color field areas, emotional intensity, paint splatter and drips, layered textures, large canvas feel
```

### 05 - Isometric Coffee Shop
```
Isometric illustration of a cozy coffee shop interior, flat design style, warm pastel colors, espresso machine on wooden counter, small tables with chairs, pendant lighting, potted plants, shelves with coffee jars, warm and inviting atmosphere
```

### 06 - Pixel Art Cyberpunk
```
16-bit pixel art cyberpunk city street at night, neon signs in Japanese katakana, hot pink and cyan neon glow, wet street with reflections in puddles, rain, dark building silhouettes, retro SNES game aesthetic, atmospheric lighting
```

### 07 - Botanical Butterfly
```
Hyperdetailed watercolor botanical illustration, monarch butterfly perched on purple coneflower echinacea, scientific accuracy, delicate wing veins and patterns, soft natural light, warm cream paper background, Danaus plexippus, botanical art style
```

### 08 - Fractal Mandelbrot
```
Mandelbrot fractal zoom into Seahorse Valley, vibrant rainbow gradient coloring, deep purple blue cyan green gold orange red palette, mathematical beauty, cosmic colors, high detail spiraling tendrils, smooth color transitions, dark interior
```

---

## 2. Gemini Image Editing (Image-to-Image)

Pass the existing Gemini image + these edit prompts via nano banana.

### 02 - Japanese Landscape (edit `gemini/02-japanese-landscape.png`)
```
Make the cherry blossom tree fuller with more branches and denser flowers. Add more delicate sub-branches. Keep the minimalist style and negative space. The tree should feel more alive and graceful while maintaining the ukiyo-e spirit.
```

### 04 - Abstract Expressionist (edit `gemini/04-abstract-expressionist.png`)
```
Add more visible canvas texture showing through the paint. Make the gold tones more metallic and luminous. Add some thin palette knife scratch marks. Increase the contrast between the dark gestures and lighter areas. Keep the moody intimate atmosphere.
```

### 07 - Botanical Butterfly (edit `gemini/07-botanical-butterfly.png`)
```
Make the butterfly wings more detailed — add more visible cell structure between the black veins. Increase the number of white spots along the wing margins. Make the echinacea flower petals slightly more droopy and natural. Enhance the watercolor paper texture in the background.
```

### 01 - Op Art (edit `gemini/01-op-art.png`)
```
Transform the concentric circles into a checkerboard grid pattern distorted by a sphere pushing through from behind. The grid lines should bend around the sphere. Keep it black and white, high contrast. Victor Vasarely Vega series style.
```

### 05 - Isometric Coffee Shop (edit `gemini/05-isometric-coffee-shop.png`)
```
Add more warm ambient lighting — pendant lamps with visible glow halos. Add a few more small details: a cake under a glass dome on the counter, a small chalkboard menu on the wall, steam rising from a coffee cup. Keep the isometric perspective and pastel palette.
```

### 03 - Retro Poster (edit `gemini/03-retro-poster.png`)
```
Add the artist names "MILES DAVIS • JOHN COLTRANE • THELONIOUS MONK" in the lower portion of the poster. Ensure the text is clearly legible. Add a small Swiss cross symbol at the bottom. Keep the vintage 1960s Swiss design style.
```

---

## 3. Video Generation (Text-to-Video)

For Veo 3.1 / Sora. Comparing against Claude's CSS/JS animations.

### 01 - Op Art (animated breathing)
**Text-to-video:**
```
Seamless loop animation of a black and white op art pattern, Victor Vasarely style, concentric checkerboard grid with a sphere bulge that slowly pulses in and out, creating a breathing optical illusion effect. High contrast, hypnotic, smooth motion. 4 second loop.
```

**Image-to-video (base: `gemini/01-op-art.png` or `flux/01-op-art.png`):**
```
Animate this op art pattern with a slow, subtle pulsing effect. The sphere/circles should appear to breathe — slowly expanding and contracting. Keep the black and white contrast. Smooth seamless loop, hypnotic, 4 seconds.
```

### 02 - Japanese Landscape (falling petals)
**Text-to-video:**
```
Minimalist Japanese landscape, single cherry blossom tree on a gentle hill, soft pink and grey palette, ukiyo-e style. Cherry blossom petals gently falling and drifting in a light breeze, slowly rotating as they fall. Distant misty mountains, subtle moon. Serene contemplative mood, very slow gentle motion. 6 second loop.
```

**Image-to-video (base: `gemini/02-japanese-landscape.png`):**
```
Animate this Japanese landscape with cherry blossom petals gently falling from the tree. Petals drift slowly, rotating softly as they descend. Very subtle breeze. Minimal movement — the scene is contemplative and still except for the petals. 6 second seamless loop.
```

### 06 - Pixel Art Cyberpunk (rain animation)
**Text-to-video:**
```
16-bit pixel art cyberpunk city street at night, retro SNES game aesthetic. Rain falling continuously with neon reflections shimmering in wet puddles on the street. Hot pink and cyan neon signs glowing on dark building walls. Pixel art style animation, lo-fi aesthetic. 4 second seamless loop.
```

**Image-to-video (base: `gemini/06-pixel-art-cyberpunk.png`):**
```
Animate this pixel art cyberpunk scene with rain falling vertically in pixel-sized streaks. Neon sign reflections shimmer in puddles on the wet street. Keep the pixel art aesthetic — no smoothing or interpolation. Lo-fi animated pixel rain. 4 second seamless loop.
```

---

## 4. Evaluation Criteria

### Image comparison (Claude scripts vs Flux vs Gemini)
- **Fidelity to brief**: Did it follow the prompt accurately?
- **Artistic quality**: Composition, color, mood, emotional impact
- **Technical execution**: Text legibility, perspective accuracy, mathematical correctness
- **Style authenticity**: Does it convincingly represent the target art style?

### Video comparison (Claude animations vs Veo/Sora)
- **Style fidelity**: Does it maintain the original art style or "interpret" it?
- **Temporal coherence**: Smooth natural motion without glitches/morphing?
- **Seamless loop**: Clean loop or visible cut/jump?
- **Controllability**: Did it do exactly what was prompted or add unexpected elements?
- **Pixel preservation**: (for pixel art) Does it maintain crisp pixels or smooth them?

### Editing comparison (Claude script iteration vs Gemini editing)
- **Precision of edit**: Did it change only what was asked?
- **Style preservation**: Does the edited version maintain consistency with the original?
- **Iterability**: Can the result be further refined?
- **Predictability**: Was the outcome what you expected from the prompt?
