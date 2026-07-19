# Esqueleto del artículo de blog (Nivel 1)

> Para escribir con la skill `blog-writer` de personal-website (EN/ES).
> Los huecos `[RESULTADO]` se rellenan tras la Fase 3; cada figura mapea a una
> función de `wheresball.analysis.figures`. Citas: ver
> [`referencias.md`](./referencias.md).

## Título (candidatos)

- EN: *Where's the ball? Testing whether AI has spectator's intuition*
- ES: *¿Dónde está el balón? Poniendo a prueba la intuición de espectador de la IA*

## Estructura

1. **La anécdota** (gancho). Ver un partido desde lejos, no ver el balón, y aun
   así saber dónde está — por cómo se mueven los jugadores. La intuición del
   espectador. Pregunta: ¿la tienen los modelos multimodales generalistas?

2. **Lo que ya se sabe** (honestidad + posicionamiento). Los sistemas
   especialistas ya infieren el balón desde los jugadores [cita: Maksai 2016;
   Kim 2023; TranSPORTmer]. Lo que nadie ha medido: si un modelo *generalista*
   —que "conoce el juego" como una persona— puede hacerlo sin entrenamiento
   específico. Los benchmarks deportivos de VLMs no cubren este task
   [cita: SPORTU].

3. **El experimento en una imagen.** Figura: un ítem de ejemplo (frame con el
   balón oculto + jugadores). `viz.render_item` sobre un frame real.
   Explicar: 500 ítems de SoccerNet, estratificados por estado del balón,
   balón oculto por oclusión natural (sin trucos de edición), pregunta en JSON
   estricto, hash del conjunto congelado publicado antes de ejecutar.

4. **Los rivales.** Los VLMs contra baselines geométricos que cualquiera
   programaría en una tarde (centroide, jugador más rápido, Voronoi) y contra
   el techo especialista [cita: Kim 2023]. Punto clave para el lector técnico:
   si un VLM no supera al centroide, no está "entendiendo el juego".
   (+ el control del centro del encuadre: la cámara de TV ya apunta al balón.)

5. **Resultados.**
   - `[RESULTADO]` Ranking principal — figura `ranking_figure`.
   - `[RESULTADO]` ¿Ayuda el movimiento? (frame único vs multi-frame, RQ2).
   - `[RESULTADO]` ¿Ayuda saber que es fútbol? (prompt neutro vs informado, RQ3).
   - `[RESULTADO]` ¿Dónde fallan? Por estado del balón — figura
     `stratum_figure` (H4: posesión fácil, pelotazo imposible).
   - `[RESULTADO]` ¿Saben cuándo no saben? — figura `calibration_figure` (RQ4).
   - Ejemplos cualitativos: 2–3 aciertos y 2–3 fallos con el razonamiento
     literal del modelo (`render_item` con predicción superpuesta).

6. **Qué significa.** Según el desenlace:
   - Si los VLMs funcionan: "la IA generalista tiene intuición de espectador"
     → implicaciones para percepción de objetos latentes (conducción autónoma,
     robótica).
   - Si fallan: "cualquier aficionado hace algo que los mejores VLMs no pueden"
     → qué les falta (¿localización precisa? ¿razonamiento social-espacial?).
   Ambos son artículo; el diseño está hecho para que ambos informen.

7. **Qué viene después.** Teaser del Nivel 2 (¿transfiere entre deportes?) y
   Nivel 3 (¿es pura geometría?). Link al repo y al benchmark reejecutable.

## Notas de producción

- Fechar los resultados y fijar versiones exactas de modelos (los VLMs rotan;
  el benchmark reejecutable importa más que el ranking del mes).
- Mapas de error sobre el campo (`error_map_figure`) funcionan muy bien como
  imagen de portada/social.
- La versión ES no es traducción literal: la anécdota de la grada da más juego
  en ES ("desde la grada de un campo de tierra…").
