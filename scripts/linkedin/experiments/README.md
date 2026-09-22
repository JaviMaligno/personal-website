# Experimentos del generador de posts de LinkedIn

Tres scripts para no discutir de oídas cuando un post automático sale mal. Se
lanzan desde Actions con **Experimento — generador de posts de LinkedIn**
(`.github/workflows/summary-experiment.yml`), que es manual y no publica nada:
el resultado se lee en el log del run. La clave `GEMINI_API_KEY` vive en los
secretos del repo y **no está en el `.env` local**, así que en local no corren.

| Script | Qué contesta |
|---|---|
| `summary-matrix.mjs` | ¿La culpa es del prompt o del modelo? Matriz de 3 artículos × 4 prompts × 4 modelos, con conteo de defectos. `P3_produccion` **importa** el prompt desplegado de `scripts/linkedin/prompt.js`, así que el banco no puede medir un texto distinto del que sale. |
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

## Lo medido el 2026-09-18, sobre lo que se publicó de verdad

Los cinco posts que salieron entre el 12 y el 17 de septiembre, pasados por los
detectores nuevos. No son salidas de laboratorio: es el texto que LinkedIn tiene
publicado.

| Post | Caracteres de la 1ª línea | Se corta | Abre definiendo | Acaba en pregunta |
|---|---|---|---|---|
| `when-the-fact-stops-being-true` | 185 | no | no | **sí** |
| `the-bug-nobody-can-reach` | 151 | no | no | **sí** |
| `being-wrong-can-be-free` | 293 | **sí** | no | **sí** |
| `knew-it-wasnt-the-model` | 445 | **sí** | no | no |
| `benchmaxing` | 543 | **sí** | **sí** | no |

Tres defectos, todos de **forma**, que el prompt anterior no nombraba:

- **La apertura no sobrevive al corte.** LinkedIn esconde tras "…ver más" todo
  lo que pase de unos 200 caracteres. Tres de las cinco primeras líneas miden
  293, 445 y 543: se publican partidas a media frase, y esa mitad es lo único
  que ve quien pasa por el feed.
- **La pregunta final sigue saliendo**, 3 de 5, aunque el prompt la prohibía en
  una línea entera. Prohibirla solo como *última frase* no basta; ahora se
  prohíbe en todo el párrafo de cierre.
- **`benchmaxing` abrió definiendo el tema en tercera persona** ("Benchmaxing
  directs model optimization toward…"), y el post entero se lee como un
  abstract. Es el único de los cinco que lo hace, y el único que el detector
  `apertura_definicion` marca.

Y una cosa que conviene no re-derivar: **lo que hace "catchy" a un post no es
una fórmula de apertura**. Eso ya se probó el 09-09 y sale plantilla 12 de 12.
Lo que lo hace catchy es que el hecho más concreto del artículo quepa antes del
corte. Por eso P3 no añade ni un ejemplo de gancho; añade un límite de longitud
y una orden sobre *qué* va en esa primera línea.

### Un detector descartado, y por qué

La primera versión miraba si el primer párrafo tenía `I/my/me`, suponiendo que
un arranque sin narrador era el síntoma del abstract. Marcaba justo los dos
ganchos **buenos** (`the-bug-nobody-can-reach`, `when-the-fact-stops-being-true`),
cuya primera línea es una escena sin narrador, y no marcaba `benchmaxing`, que
sí dice "a pilot set of probes I conducted". El que quedó mira el sujeto y el
verbo de la primera frase, y de los cinco posts marca solo el que falla.

## Lo medido el 2026-09-21 (cupo, y por que este banco puede dejar sin post)

Dos tiradas de `component-rule.mjs` perdidas seguidas, ninguna por culpa de lo
que se queria medir:

| Tirada | Celdas con texto | Que las mato |
|---|---|---|
| 1a | 15 de 40 | `gemini-3.8-flash` (503/429) + cupo agotado a mitad |
| 2a | 0 de 40 | cupo agotado del todo: 429 en las 20 parejas |

Tres cosas que conviene no volver a descubrir:

- **`gemini-3.8-flash` sigue sin servir**, dos semanas despues de medirlo la
  primera vez. Un experimento que elija modelos solo ("los mas nuevos que
  ofrezca la API") volvera a cogerlo. Los modelos se fijan a mano, y se fijan
  a los de produccion.
- **El orden del recorrido decide que se pierde.** Con el recorrido secuencial,
  el cupo se agoto a mitad y se llevo por delante justo los dos articulos de
  control, que iban al final: el brazo que medía el riesgo se quedo en n=1. De
  ahi que las celdas vayan emparejadas y barajadas con semilla fija.
- **Un 200 al sondear no dice que quepa un articulo.** `model-probe` respondio
  200 con los dos modelos de produccion y el experimento siguiente devolvio 429
  en todas sus celdas: seis palabras cabian en lo que quedaba de cupo, 2.000
  tokens no.

Y lo que hay que tener presente antes de lanzar nada aqui: **`GEMINI_API_KEY` es
la misma clave que usa `generate-summary.js` en produccion**. Un run de 40
llamadas con el articulo entero agota el cupo del dia, asi que si ese dia se
publica un articulo, el post de LinkedIn no se genera. Mirar
`.github/publish-schedule.json` antes de gastar el cupo en un experimento.

## Lo medido el 2026-09-22 (la regla de componentes)

Run 35723543236: 14 parejas completas de 20 (las 6 perdidas se llevaron entero
el articulo del prototipo RLM). Cifras ya con el detector corregido:

| | responsabilidad propia | posts con TODOS | amontonados | listas en los controles |
|---|---|---|---|---|
| sin regla | 16/32 (50%) | 0/8 | 2/8 | 0/6 |
| con regla | 23/32 (72%) | 4/8 | 0/8 | 0/6 |

Por articulo, que es donde se ve lo que pasa:

- **tres bloques** (el caso que motivo la regla): 2/3 en las cuatro tiradas sin
  ella, 3/3 en las cuatro con ella. Cuatro de cuatro contra cero de cuatro.
- **cinco capas**: 2, 2, 1, 3 sin regla; 3, 3, 4, 1 con ella. Sube la media y
  no la fiabilidad — con cinco capas el post sigue dejandose alguna.

Nada de lo ganado en septiembre se pierde (apertura cortada, definicion, muro
y pregunta de cierre siguen a 0 de 14 en los dos brazos), y los dos articulos
de control no reciben ninguna lista inventada.

**El detector medía al reves de lo que creía.** La primera lectura de este run
daba 50% contra 53%, o sea nada. El motivo: `frases()` partia tambien por ":",
y la regla induce justamente el formato "Frontend: handles interaction…", asi
que el nombre quedaba en una frase y su responsabilidad en otra y el componente
contaba como NO atribuido. El sesgo iba en contra de la regla, y el test no lo
cogia porque estaba escrito con guion largo en vez de dos puntos. Corregido, con
un test por cada uno de los dos formatos.

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
