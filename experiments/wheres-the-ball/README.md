# Where's the ball? 🔎⚽

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

Pendiente (requiere datos/APIs): adaptador SoccerNet real (Fase 1), clientes
API de Claude/GPT/Gemini/Qwen-VL (Fase 3), proyección con homografía a metros,
inpainting con control de fuga, interfaz del estudio humano (Fase 4).

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
