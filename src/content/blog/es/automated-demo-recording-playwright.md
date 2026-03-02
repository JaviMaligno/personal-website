---
title: "Hice un Video de Demo de Producto Enteramente con IA"
description: "Cómo usé Claude Code para construir un pipeline de grabación, edge-tts para la narración, ffmpeg para el ensamblaje, y Gemini para validar el resultado — sin tocar un editor de vídeo."
pubDate: 2026-03-02
tags: ["IA", "Automatización", "Playwright", "Productividad", "Vídeo"]
lang: es
translationKey: automated-demo-recording-playwright
heroImage: "/blog/automated-demo-recording-playwright.png"
---

Necesitaba un vídeo de demo para una plataforma de automatización de RFPs que estoy construyendo. El enfoque típico: grabar la pantalla, hacer clics rezando para que nada falle, re-grabar cuando algo se rompe, y luego pasar una hora en un editor de vídeo sincronizando la voz. Ya lo he hecho antes. Es un dolor.

Así que probé un enfoque diferente: **dejar que la IA hiciera todo**.

- **Claude Code** escribió todo el pipeline de grabación — scripts de Playwright, ensamblaje con ffmpeg, control de velocidad, generación de subtítulos
- **edge-tts** generó la narración con las voces neuronales de Microsoft
- **Gemini 3.1 Pro** revisó el vídeo final buscando problemas de sincronización audio/vídeo

El resultado: una demo narrada de 3 minutos con 14 escenas, segmentos de velocidad variable y subtítulos. Sin editor de vídeo. Sin app de grabación de pantalla. Sin locución manual.

<div style="position: relative; padding-bottom: 56.25%; height: 0;"><iframe src="https://www.loom.com/embed/b17966fe959e41cabf4b02b12ddccac4" frameborder="0" webkitallowfullscreen mozallowfullscreen allowfullscreen style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"></iframe></div>

Así es como funcionó todo el proceso — incluyendo las partes que fallaron.

## El Pipeline

```
Playwright (grabar) → edge-tts (voz) → ffmpeg (ensamblar) → Gemini (QA)
```

### Paso 1: Claude Code Escribe el Grabador

Describí lo que quería: un vídeo de demo usando Playwright para grabar el navegador, con text-to-speech para la voz coordinada con el vídeo, cubriendo todo el flujo de trabajo de la aplicación. Claude Code decidió la estructura — 14 escenas desde el dashboard hasta los API docs — escribió los scripts de escena, y generó los módulos. Cada uno es una función TypeScript que guía el navegador por una funcionalidad específica:

```typescript
export const scene: SceneFn = async (page) => {
  await page.getByText("Generate Answer").click();

  // Esperar a que termine la IA
  const indicator = page.getByText("Generating AI answer...");
  await indicator.waitFor({ state: "hidden", timeout: 90_000 });

  // Hacer scroll suave por la respuesta
  const scrollPanel = page.locator("[data-demo-scroll=true]");
  await scrollPanel.evaluate((el) => {
    el.scrollTo({ top: el.scrollHeight / 3, behavior: "smooth" });
  });
  await longPause(page);
};
```

Un wrapper de test ejecuta las 14 escenas en secuencia, guardando timestamps:

```typescript
for (const id of sceneIds) {
  const start = (Date.now() - videoStartTime) / 1000;
  await SCENES[id](page);
  timestamps.push({ id, start, end: (Date.now() - videoStartTime) / 1000 });
}
```

Output: un vídeo `.webm` + un fichero `scene-timestamps.json`. Esta separación es clave — permite manipular cada escena independientemente durante el ensamblaje.

### Paso 2: Voz IA con edge-tts

Cada escena tiene una línea de narración. [edge-tts](https://github.com/rany2/edge-tts) las convierte en ficheros MP3 usando las voces neuronales de Microsoft — gratis, sin API key, sorprendentemente naturales:

```bash
edge-tts --text "Let's generate an AI answer..." \
  --voice en-US-GuyNeural \
  --write-media voice/08-generate-answer.mp3
```

14 escenas, 30 segundos para generar todas las voces. Claude Code también escribió el guión de narración — yo revisé y ajusté la redacción, pero el borrador fue IA.

### Paso 3: Ensamblaje — Donde Todo Se Rompió

Claude Code también escribió el script de ensamblaje. En teoría es simple: dividir el vídeo por timestamps, superponer la voz, concatenar. En la práctica, aquí es donde pasé la mayor parte del tiempo iterando con Claude.

#### Velocidad Variable: 30 Segundos de Spinner → 2 Segundos

Nadie quiere ver un spinner de IA durante 30 segundos. La solución: segmentos de velocidad por escena.

```typescript
{
  id: "08-generate-answer",
  speed: [
    { from: 0, to: 1, speed: 1 },   // Clic en el botón a velocidad normal
    { from: 1, to: 6, speed: 15 },   // Generación IA: 30s → 2s
    { from: 6, to: 10, speed: 1 },   // Leer la respuesta a velocidad normal
  ],
}
```

Los valores `from/to` son proporcionales (escala 0-10). ffmpeg aplica esto mediante un filtergraph de split/trim/setpts/concat. El resultado: las esperas aburridas se comprimen 15x mientras las interacciones reales van a velocidad real.

#### La Pesadilla de la Sincronización de Audio

Esta es la lección que más iteraciones costó aprender. Al mezclar voz con vídeo por escena y luego concatenar:

**Problema 1:** Usar el flag `-shortest` de ffmpeg trunca silenciosamente el stream más largo. La voz se corta a mitad de frase.

**Problema 2 (el chungo):** ffmpeg empieza el audio de cada clip concatenado donde **terminó el audio del clip anterior**, no donde empieza el vídeo. Si el clip A tiene 30s de vídeo pero solo 13s de audio, el audio del clip B empieza en t=13 en vez de t=30. Esto causa un **drift progresivo** — para la escena 10, la voz va más de un minuto por detrás de lo visual.

**La solución:** La pista de audio de cada clip debe coincidir exactamente con la duración del vídeo:

```bash
ffmpeg -i video.mp4 -i voice.mp3 \
  -filter_complex "[1:a]adelay=500|500,apad=whole_dur=VIDEO_DURATION[audio]" \
  -map 0:v -map "[audio]" -c:v copy -c:a aac output.mp4
```

`apad=whole_dur` rellena el audio con silencio hasta igualar exactamente la duración del vídeo. Drift imposible.

## Gemini 3.1 Pro como QA de Vídeo

Aquí es donde se puso realmente interesante. Después de arreglar el pipeline, necesitaba verificar la sincronización audio/vídeo en 14 escenas. Ver el vídeo entero manualmente cada vez es tedioso y mis oídos no son fiables después de la décima iteración.

Subí el vídeo a Gemini 3.1 Pro y le pedí que analizara la sincronización — qué acciones ocurren visualmente vs. cuándo la narración las describe.

### En la Versión Rota

Gemini detectó cada problema de sincronización con timestamps precisos:

| Acción | Visual | Audio | Desfase |
|--------|--------|-------|---------|
| Crear RFP | 01:51 | 02:09 | 18s tarde |
| Asignar Style Guide | 02:20 | 03:05 | 45s tarde |
| Generar Respuesta | 02:22 | 03:31 | **1m 9s tarde** |
| Chat con diff | 03:22 | 03:58 | 36s tarde |
| Asignar equipo | 03:55 | 04:28 | 33s tarde |

Drift progresivo clásico. El audio de cada escena se desplaza más porque la pista de audio de la escena anterior era más corta que su vídeo.

### En la Versión Corregida

Después de aplicar el fix con `apad`, el análisis de Gemini: **13 escenas con sincronización perfecta, 1 marcada como ~2 segundos tarde.**

La escena marcada en realidad estaba bien — yo había añadido intencionalmente 1.5 segundos de delay para dejar que una transición visual se asentara antes de empezar la narración. Gemini fue ligeramente más estricto de la cuenta.

**Resultado: 0 problemas no detectados, 1 falso positivo de 14 escenas.** Eso es mejor QA del que obtendría viendo el vídeo yo mismo.

## El Bucle de Feedback Humano-IA

El proceso no fue "pedir una vez, obtener vídeo perfecto." Fue iterativo:

1. **Yo:** "Quiero un vídeo de demo usando Playwright con TTS, cubriendo todo el flujo de trabajo"
2. **Claude:** Decide 14 escenas, genera el pipeline. La primera grabación funciona.
3. **Yo:** "La voz se desincroniза a partir de la escena 5"
4. **Claude:** Depura, descubre el problema de `-shortest`. Lo arregla con `apad`.
5. **Yo:** "La respuesta no hace scroll — no se ven los bullet points"
6. **Claude:** Investiga el DOM, encuentra el contenedor de scroll equivocado. Lo arregla con descubrimiento programático del padre.
7. **Yo:** "Sigue sin haber bullet points en la respuesta generada"
8. **Claude:** Testea vía API, descubre que la IA devuelve texto plano a pesar de las instrucciones HTML. Añade post-procesador `normalizeAnswerHtml`.
9. **Yo:** "La escena de Knowledge Base tiene demasiado tiempo muerto, y la voz de style guide empieza demasiado pronto"
10. **Claude:** Aumenta la compresión de velocidad de 4x a 8x, añade 2s de delay a la voz del style guide.

Cada ronda: veo el vídeo, describo lo que está mal en lenguaje natural, Claude depura y arregla. El loop de feedback es rápido porque re-grabar tarda 4 minutos y ensamblar 1 minuto.

## Qué Hizo la IA vs. Qué Hice Yo

| Tarea | Quién |
|-------|-------|
| Escribir 14 scripts de escena Playwright | Claude Code |
| Escribir pipeline de ensamblaje (800 líneas) | Claude Code |
| Escribir lógica de segmentos de velocidad | Claude Code |
| Depurar problemas de sincronización de audio | Claude Code |
| Arreglar detección del contenedor de scroll | Claude Code |
| Añadir post-procesador de normalización HTML | Claude Code |
| Generar audio de narración | edge-tts |
| QA de sincronización audio/vídeo | Gemini 3.1 Pro |
| Escribir texto de narración | Claude Code (yo revisé y ajusté) |
| Revisar vídeo y dar feedback | Yo |
| Elegir qué mostrar y en qué orden | Yo |

La dirección creativa fue mía. Todo lo demás fue IA.

## Los Números Finales

```bash
# Grabar 14 escenas
npx playwright test e2e/tests/demo-record.spec.ts --headed  # ~4 min

# Generar voces
npx tsx scripts/demo-record.ts voice   # ~30 seg

# Ensamblar con control de velocidad + subtítulos
npx tsx scripts/demo-record.ts assemble  # ~1 min
```

- **Output:** vídeo narrado de 3:47, 14 escenas, velocidad variable, subtítulos
- **Código del pipeline:** ~800 líneas TypeScript (ensamblaje) + ~200 (escenas)
- **Tiempo para re-grabar:** menos de 6 minutos end-to-end
- **Editores de vídeo usados:** cero

Si la UI cambia mañana, actualizo un fichero de escena y re-ejecuto. Todo el pipeline está versionado y es reproducible.

## Trade-off Honesto: Manual vs. Automatizado

Para la **primera iteración**, grabar manualmente la pantalla mientras narras sería más rápido. Una herramienta de screen recording te da un vídeo en tiempo real — sin pipeline que construir.

Pero la grabación manual tiene sus propios costes: necesitas un entorno silencioso y un micrófono decente, cualquier tropiezo significa re-grabar, editar el timing de la voz en un editor de vídeo es tedioso, y la calidad de audio depende enteramente de tu hardware.

El enfoque automatizado compensa a partir de la **segunda iteración**. Cuando la UI cambió, actualicé un fichero de escena y re-ejecuté. Cuando la narración necesitó ajustes, edité un string de texto — sin re-grabar mi voz. Después de cinco rondas de feedback, habría pasado horas en un editor de vídeo haciendo lo mismo manualmente. Y si un cliente pide una demo el mes que viene después de un rediseño, son 6 minutos de re-ejecución, no una re-grabación completa.

## Más Allá de Demos: Vídeo como Evidencia de QA

Este pipeline se construyó para una demo de producto, pero el patrón — automatización de navegador produciendo vídeo narrado — tiene implicaciones más amplias.

Piensa en QA. Hoy, la evidencia de testing suele ser un log de CI que dice `PASS` o `FAIL`. Cuando un cliente pregunta "demuéstrame que el flujo de pago funciona," re-ejecutas el test y esperas que se fíen de un checkmark verde. Imagina en su lugar entregarles un vídeo narrado: el test se ejecuta, la voz explica cada paso, y el vídeo se genera automáticamente en cada release. El testing de regresión deja de ser solo un checkpoint técnico y se convierte en un artefacto revisable.

Lo mismo aplica a compliance y auditoría. Las industrias reguladas necesitan pruebas de que los sistemas funcionan según lo especificado. Un pipeline versionado que produce evidencia en vídeo con timestamps bajo demanda es fundamentalmente diferente de grabaciones de pantalla manuales enterradas en un drive compartido.

Y onboarding — los nuevos miembros del equipo podrían ver walkthroughs auto-generados que se mantienen al día con la UI real, no capturas de documentación de hace seis meses.

El cambio de fondo es que **el vídeo se está convirtiendo en un output programático**, no una producción creativa. Cuando el coste de producir un vídeo baja de horas a minutos, y re-producirlo es un solo comando, empiezas a usar vídeo en sitios donde nunca fue práctico.

## Conclusiones

1. **`recordVideo` de Playwright es calidad de producción** para demos — 720p/25fps, sin overhead
2. **Nunca uses `-shortest` en ffmpeg** al mezclar streams de audio para concatenación. Usa `apad=whole_dur` para igualar la duración del audio a la del vídeo.
3. **Los segmentos de velocidad variable** son la diferencia entre una demo aburrida y una que se puede ver. 15x de compresión para spinners, 1x para interacciones reales.
4. **Gemini 3.1 Pro es una herramienta legítima de QA de vídeo.** Sube un vídeo, pregunta "¿está el audio sincronizado con lo visual?" — te da un informe con timestamps y precisión casi perfecta.
5. **El bucle de feedback humano-IA importa más que acertar a la primera.** Describí problemas en lenguaje natural ("el scroll no funciona"), Claude depuró y arregló. Cinco iteraciones hasta un resultado pulido.
6. **La IA es genial para automatizar, los humanos para juzgar.** Yo escribí el guión de narración y decidí qué mostrar. La IA hizo todo lo demás.
7. **Cuando el vídeo se convierte en un comando, lo usas en todas partes.** El mismo pipeline que graba una demo puede generar evidencia de QA, walkthroughs de onboarding o artefactos de compliance — todo versionado y reproducible en cada release.

---

*Herramientas: [Claude Code](https://claude.ai/claude-code), [Playwright](https://playwright.dev/), [ffmpeg](https://ffmpeg.org/), [edge-tts](https://github.com/rany2/edge-tts), [Gemini 3.1 Pro](https://deepmind.google/technologies/gemini/)*
