# Experimentos del generador de posts de LinkedIn

Tres scripts para no discutir de oídas cuando un post automático sale mal. Se
lanzan desde Actions con **Experimento — generador de posts de LinkedIn**
(`.github/workflows/summary-experiment.yml`), que es manual y no publica nada:
el resultado se lee en el log del run. La clave `GEMINI_API_KEY` vive en los
secretos del repo y **no está en el `.env` local**, así que en local no corren.

| Script | Qué contesta |
|---|---|
| `summary-matrix.mjs` | ¿La culpa es del prompt o del modelo? Matriz de 3 artículos × 3 prompts × 4 modelos, con conteo de defectos. |
| `p2-newest.mjs` | ¿El prompt bueno aguanta en los modelos más nuevos? Un prompt, los flash recientes, con reintentos. |
| `model-probe.mjs` | ¿Por qué falla un modelo? Llama a `v1beta` y a `v1` y enseña el status y el cuerpo del error. |

`gemini.mjs` es el ayudante común: llama por REST, reintenta los 503 y **deja el
código HTTP a la vista**.

## Lo medido el 2026-09-09

El prompt de producción llevaba tres ganchos como *ejemplo*, y el modelo los
copiaba: **12 de 12 aperturas** eran una de esas tres familias, con cuatro
modelos distintos. Una era el ejemplo literal con dos palabras cambiadas.

| Prompt | Fórmula de gancho | Acaba en pregunta | CTA | Algo concreto del artículo |
|---|---|---|---|---|
| El de producción | 12/12 | 7/12 | 4/12 | 10/12 |
| Igual, sin los ejemplos | 0/11 | 9/11 | 3/11 | 9/11 |
| Reescrito | 0/10 | 0/10 | 0/10 | 10/10 |

Dos conclusiones que conviene no volver a re-derivar:

- **Son dos defectos independientes.** Quitar los ejemplos mata la fórmula del
  gancho, pero las preguntas siguen, porque el prompt exigía una llamada a la
  acción en otra línea.
- **Cambiar de modelo no arregla nada.** `gemini-3.6-flash` esquiva los ganchos
  del prompt y abre sus tres respuestas con "When…"; `gemini-flash-latest`
  reproduce la familia "Most…". Sustituyen una plantilla por otra.

Y un fallo que no se buscaba: el prompt viejo **fabricaba esfuerzo del autor**
("I spent five days analyzing…") que el artículo no dice.

## La trampa que hay que recordar

La primera versión de la matriz usaba el SDK `@google/generative-ai` 0.21.0, que
envuelve cualquier respuesta no-2xx en un genérico `Error fetching from
https://…`, sin status ni cuerpo. Eso llevó a concluir que `gemini-3.8-flash` no
era llamable con nuestra clave. Falso: por REST responde **200 en 2,3 s** a una
petición mínima, y con el artículo entero devuelve **503 UNAVAILABLE** por
saturación y **429 RESOURCE_EXHAUSTED** por cupo. No hace falta clave nueva;
falta cupo. De ahí que todo pase ahora por `gemini.mjs`.

## Cómo interpretar los conteos

Los detectores de `summary-matrix.mjs` son deliberadamente literales y **pueden
quedarse cortos**: la primera versión daba 3 de 12 fórmulas donde leyendo las
frases había 12 de 12, porque el patrón solo cubría una de las tres familias.
Los números sirven para ordenar; la decisión se toma leyendo las aperturas, que
el script imprime siempre.
