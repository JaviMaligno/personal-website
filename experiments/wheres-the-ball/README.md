# Where's the ball? 🔎⚽

> **⚠️ Este directorio debe migrarse a su propio repositorio**
> (`JaviMaligno/wheres-the-ball`). Vive temporalmente dentro de
> `personal-website` por límites de permisos de la sesión que lo creó.
> Instrucciones paso a paso: [MIGRATION.md](./MIGRATION.md).
> Trabajo pendiente (incluido lo que requiere ejecución local): [TODO.md](./TODO.md).

¿Puede un modelo de visión-lenguaje generalista localizar el balón que **no ve**,
infiriendo su posición a partir del movimiento de los jugadores, como hace un
espectador desde la grada?

Este repo implementa el **Nivel 1** del proyecto: el benchmark "Where's the
ball?" para VLMs. El diseño experimental completo está en [`docs/`](./docs/)
(documento maestro + diseños de los niveles 1–3).

## Estado

Fase actual: **pre-API** — todo lo que no requiere llamar a un modelo real:

| Módulo | Qué implementa | Diseño |
|---|---|---|
| `wheresball.schema` | Tipos (ítems, predicciones, condiciones, estratos), manifiesto congelado con hash | §3, §7 |
| `wheresball.baselines` | Baselines geométricos B0–B4 + B0' (centro del frame) | §4, §8 |
| `wheresball.masking` | Oclusión natural (criterios de selección) y degradación global | §3 |
| `wheresball.metrics` | Error de localización, PCK, acierto de poseedor, calibración (Spearman, cobertura, ECE) | §6 |
| `wheresball.stats` | Bootstrap CIs, Wilcoxon pareado, corrección de Holm | §7 |
| `wheresball.prompts` | Prompts versionados (neutro/informado) + parseo JSON estricto | §5 |
| `wheresball.harness` | Runner de la matriz experimental, caché de respuestas, cliente VLM mock | §5, §10 |
| `wheresball.dataset` | Generador sintético estratificado, muestreo, congelado/verificación del conjunto | §3 |
| `wheresball.dataset.mot` | Parser MOT/SoccerNet Tracking → ítems (velocidades, poseedor, heurística de estado) | §3 |
| `wheresball.geometry` | Homografías: ajuste (DLT), proyección a campo, error en metros | §3, §6 |
| `wheresball.viz` | Render esquemático de ítems (imágenes sintéticas para el pipeline + figuras cualitativas) | §9.3 |
| `wheresball.harness.api_clients` | Clientes REST de Claude/GPT/Gemini (temperatura 0, reintentos, multi-imagen) — testeados offline, sin ejecutar | §4, §5 |
| `wheresball.harness.leakcheck` | Control de fuga del inpainting (detector + tasa de descarte) | §3 |
| `wheresball.analysis.figures` | Figuras del artículo: ranking con CIs, error por estrato, calibración, mapa de error | §9.3 |

Lo pendiente está detallado en [TODO.md](./TODO.md) — en esencia: descarga
real de SoccerNet y validación del parser (local, credenciales), ejecución de
los clientes API (local, claves), cliente de VLM abierto, condición de vídeo
nativo, estudio humano, y análisis final sobre datos reales.

Para escribir los artículos: referencias en
[`docs/referencias.md`](./docs/referencias.md) /
[`docs/referencias.bib`](./docs/referencias.bib) y esqueleto del post en
[`docs/articulo-esqueleto.md`](./docs/articulo-esqueleto.md).

## Uso

```bash
pip install -e ".[dev]"
pytest                       # suite completa, sin red ni APIs
python -m wheresball.demo    # pipeline end-to-end sobre datos sintéticos
```

La demo genera un conjunto sintético estratificado (40/25/20/15 por estado del
balón), lo congela con hash, ejecuta B0–B4 y el VLM mock por la matriz de
condiciones con caché, y produce el informe con CIs bootstrap y comparaciones
pareadas — exactamente el flujo que correrá sobre SoccerNet con los modelos
reales.

## Principios del diseño que el código impone

- **Pre-registro**: el conjunto de evaluación se congela con hash *antes* de
  ejecutar modelos (`dataset.freeze` / `load_frozen` verifican manipulación).
- **Los baselines miden información, no detección**: consumen el tracking del
  dataset, nunca la imagen.
- **Sin fuga por enmascarado**: la condición primaria es oclusión natural; la
  degradación es global (sin artefactos locales que delaten el balón).
- **Robustez**: mediana e IQR (no medias), bootstrap por ítems, Wilcoxon
  pareado con Holm.
- **Reproducibilidad**: prompts versionados, caché por (modelo, ítem,
  condición, versión de prompt), semillas deterministas por ítem.
