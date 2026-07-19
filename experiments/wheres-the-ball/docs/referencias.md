# Referencias para los artículos

Bibliografía del proyecto, lista para citar en el artículo de blog (Nivel 1) y
en los papers de los Niveles 2–3. La versión BibTeX está en
[`referencias.bib`](./referencias.bib). Los títulos marcados ⚠️ se tomaron del
documento de diseño y conviene verificarlos contra arXiv antes de publicar.

## Inferencia del balón con modelos especialistas (punto de partida obligado)

- **Maksai, Wang & Fua (2016)** — *What Players do with the Ball: A Physically
  Constrained Interpretation of Trajectories.* Trabajo fundacional: infiere la
  trayectoria del balón en fútbol/vóley/basket desde tracking de jugadores +
  restricciones físicas. [arXiv:1511.06181](https://arxiv.org/abs/1511.06181)
- **Kim et al. (2023)** — *Ball Trajectory Inference from Multi-Agent Sports
  Contexts Using Set Transformer and Hierarchical Bi-LSTM.* La formulación más
  cercana a nuestra pregunta: primero poseedor, luego trayectoria, solo desde
  trayectorias de jugadores. [arXiv:2306.08206](https://arxiv.org/abs/2306.08206)
- **Capellera et al. (2024)** — *TranSPORTmer: A Holistic Approach to
  Trajectory Understanding in Multi-Agent Sports.* Estado del arte
  especialista; ~25% de mejora en inferencia del balón.
  [arXiv:2410.17785](https://arxiv.org/abs/2410.17785)
- ⚠️ **PathCRF** — detección de eventos de balón sin ver el balón, infiriendo
  la ruta de posesión. [arXiv:2602.12080](https://arxiv.org/abs/2602.12080)
- ⚠️ **Multi-Modal Soccer Scene Analysis** — pre-entrenamiento enmascarado que
  infiere poseedor, estado y trayectoria a la vez.
  [arXiv:2512.19528](https://arxiv.org/abs/2512.19528)

## Benchmarks de comprensión deportiva para VLMs (ninguno cubre nuestro task)

- **SPORTU** — *A Comprehensive Sports Understanding Benchmark for Multimodal
  Large Language Models.* [arXiv:2410.08474](https://arxiv.org/abs/2410.08474)
- ⚠️ **SoccerLens** — evaluación de VLMs en fútbol.
  [arXiv:2605.09598](https://arxiv.org/abs/2605.09598)
- ⚠️ **Inteligencia espacial en deportes** — evaluación espacial de VLMs.
  [arXiv:2603.09896](https://arxiv.org/abs/2603.09896)

## Dificultad del tracking del balón (motivación)

- ⚠️ **Tracking del balón como objeto más difícil** — diminuto, rápido,
  constantemente ocluido. [arXiv:2311.05237](https://arxiv.org/abs/2311.05237)

## TDA en deporte (relevante para el Nivel 3)

- ⚠️ **Scouting de fútbol con homología persistente** —
  [Research Square rs-7756175](https://www.researchsquare.com/article/rs-7756175/v1)
- ⚠️ **TDA en hockey** — [arXiv:1409.7635](https://arxiv.org/abs/1409.7635)

## Datos

- **SoccerNet** — familia de datasets/retos de fútbol (tracking, calibración,
  Game State Reconstruction). Portal: [soccer-net.org](https://www.soccer-net.org/).
  Citar el paper del split concreto que se use (p. ej. SoccerNet-Tracking,
  [arXiv:2204.06918](https://arxiv.org/abs/2204.06918); verificar cuál
  corresponde a la descarga).

## Cómo citar en el blog

El artículo del Nivel 1 debe citar como mínimo: Maksai (la pregunta ya
respondida con especialistas), Kim/TranSPORTmer (el techo), un benchmark VLM
(SPORTU) para el hueco "nadie evalúa VLMs generalistas en este task", y
SoccerNet (datos). El esqueleto del artículo con los puntos de cita marcados
está en [`articulo-esqueleto.md`](./articulo-esqueleto.md).
