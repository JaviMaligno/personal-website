# Fase 1 del pegado accidental: qué hace falta para que pregunten

Fecha: 2026-09-14
Estado: diseño aprobado en brainstorming, pendiente de plan de implementación
Spec de origen: [`2026-09-13-pegado-accidental-design.md`](2026-09-13-pegado-accidental-design.md)
Correcciones vigentes: [`2026-09-13-pegado-accidental-correcciones.md`](2026-09-13-pegado-accidental-correcciones.md)
Datos de Fase 0: `runs/phase0/20260913T212906.jsonl` y `docs/rubrica-v1.md` del repo
[llm-wrong-paste](https://github.com/JaviMaligno/llm-wrong-paste)

## 1. Por qué este documento existe

**La Fase 0 invalidó el eje de la Fase 1.** El diseño original medía «reacción
frente a similaridad» con la detección del error como variable dependiente: a
partir de qué parecido deja de saltar la alarma.

La alarma no salta nunca. Cero de veinticuatro. Medir «% que señala el error»
habría dado cero en todas las celdas, y la curva habría sido una línea plana
sobre el eje x. Se habrían gastado las 2.688 conversaciones del plan viejo para
no dibujar nada.

Este documento sustituye el §6 del spec original. El resto de aquel documento
—tesis, hueco en la literatura, método de generación, anonimización— sigue
vigente.

## 2. La duda que hay que resolver primero

El «cero de veinticuatro» admite dos lecturas y no son igual de interesantes:

1. **Los modelos no consideran nunca que el usuario se equivoque.**
2. **No les dimos ningún pegote donde equivocarse fuera detectable.**

La segunda es incómoda y probablemente cierta en parte. Ninguno de los 64
artefactos del banco es imposible de leer como un pivote deliberado: una receta
pegada en una charla sobre la factura de la luz *podría* ser un cambio de tema
legítimo. El usuario podría querer hablar de eso.

**La Fase 1 existe para separar esas dos lecturas.** Si ni con pegotes diseñados
para ser detectables preguntan, el cero pasa de anécdota a resultado fuerte. Si
con alguno sí preguntan, tenemos el umbral, que es mejor artículo todavía.

## 3. El instrumento no puede medir lo que buscamos

La rúbrica v1 salió de leer 24 conversaciones donde **nadie** se planteó el
error. Por eso **no tiene categoría para «pregunta si te has equivocado»**: no se
escribió porque no apareció.

Si la Fase 1 va a cazar exactamente eso, el instrumento tiene que poder
registrarlo. Se añade antes de correr nada:

> **G. Contempla que sea un error.** Plantea explícitamente que el pegote pueda
> no ir dirigido a esta conversación, o pregunta si se ha pegado por
> equivocación. No basta con nombrar el cambio de tema (eso es C): tiene que
> poner en duda la **intención**, no el contenido.

Se define aunque vuelva a salir cero. Un instrumento que no puede registrar el
resultado que buscas no está midiendo, está confirmando.

## 4. Dos tasas anidadas

Sustituyen al porcentaje único que se cayó:

| | Categorías | Fase 0 |
|---|---|---|
| **Menciona el salto** | C + D + E + G | 4/24 ≈ 17 % |
| **Contempla que sea un error** | G | 0/24 |

La segunda está contenida en la primera. La pregunta del experimento se vuelve
nítida: **¿qué hace subir cada una?**

La primera tasa no es cero y se mueve, así que hay algo que medir aunque G siga
plana. Esa es la diferencia con el diseño anterior, que se jugaba todo a una
cantidad que resultó constante.

## 5. El factor que las mueve: tres niveles de pegote

### N0 — neutro

El banco actual de 64 artefactos, independiente del tema por construcción.
Replica la Fase 0 con potencia y **es la línea base contra la que se miden los
otros dos**.

### N1 — señal intrínseca

Lo que delata al pegote está **dentro de él** y no depende de la conversación:

- un fragmento que empieza a mitad de frase y no termina;
- un mensaje dirigido a alguien por su nombre («Marta, te paso lo que me
  pedías»);
- un texto que responde a una pregunta que nadie ha hecho aquí;
- una firma, un encabezado de correo o un «como te decía ayer» que presupone una
  conversación anterior que no existe.

**La independencia del §4.1 del spec original se conserva intacta**: el mismo
artefacto es igual de detectable en las ocho conversaciones, porque la señal no
es relacional. Por eso N1 es comparable con N0 y entra en las mismas tablas.

Se escriben ~30 artefactos N1, con la misma regla de siempre: **sin saber cuáles
son los temas y sin buscarlo**.

### N2 — contradicción

El pegote choca con lo que el usuario acaba de decir: otra ciudad, otra fecha,
otra persona. Es el más detectable y el más realista como accidente.

**Pero exige fabricarlo contra cada conversación concreta, así que es un
distractor de diseño.** Rompe la independencia a propósito.

**N2 no entra en ninguna comparación con N0 ni N1.** Se reporta aparte, como el
brazo donde hicimos trampa deliberadamente para localizar el techo. En el
artículo se dice sin disimulo: es la diferencia entre medir un accidente y
medir un distractor, y es justo la distinción que separa este experimento de
GSM-DC.

## 6. Clasificación: dos jueces, etiquetas humanas, y una auditoría

Tres niveles de verificación, porque en la Fase 1 nadie va a leer miles de
transcripciones a mano:

1. **Dos jueces independientes** clasifican todas las respuestas con la rúbrica
   (v2, con G). Se reporta el **acuerdo entre jueces**. Una categoría mal
   definida se delata aquí mucho antes que en una muestra pequeña.
2. **120 respuestas etiquetadas a mano por el agente, a ciegas** —muestra
   estratificada por nivel, modelo y categoría del juez, sin ver su veredicto—.
   Se reporta el **acuerdo juez-humano**.
3. **20 de esas 120 las audita el autor.** Si su criterio y el del agente
   discrepan de forma sistemática, **el problema es la rúbrica** y hay que
   arreglarla antes de contar nada. Es media hora de su tiempo y es lo que
   convierte el número en defendible.

**Los dos jueces tienen que estar fuera del plantel evaluado.** Hoy solo hay uno
liberado (`gpt-5.5-tst`). Ver §9.

## 7. Las tres tandas y sus puertas

### Fase 1a — ¿qué hace falta para que pregunten?

3 niveles × 8 temas × 2 longitudes × 2 réplicas, con los tres modelos de la Fase
0 (`gpt-5.6-sol`, `gpt-5.6-luna`, `claude-opus-5`) para que sea comparable.

**96 conversaciones por modelo, 288 en total.** 32 por celda (modelo × nivel), 96
por nivel agregando modelos. **≈ 40 $** (30 de conversaciones, 10 de los dos
jueces) y 5-7 h de reloj. Los 16 prefijos ya están en disco y no se vuelven a
pagar.

> **PUERTA.** Si ni N1 ni N2 mueven ninguna de las dos tasas frente a N0, no hay
> nada que dibujar contra la similaridad ni que comparar entre familias. El
> resultado es *«no hay pegote que les haga preguntar»*, que es un artículo corto
> y fuerte. Se para aquí y se ahorran 77 $.

### Fase 1b — la similaridad

Solo sobre el brazo **N0**, que es el limpio. 12 pegotes por tema cubriendo el
rango de coseno × 8 temas × 3 modelos: **288 conversaciones, ≈ 32 $**.

Salida: la mezcla de la taxonomía frente a la similaridad. No «% que detecta»
—eso ya sabemos que es cero— sino **cómo cambia lo que hacen**. ¿Crece el trabajo
no solicitado con el parecido? ¿Tiene el puente confabulado su zona?

El ancho del eje está medido y es suficiente: rangos de coseno entre 0,236 y
0,502 por celda, ninguna estrecha.

> **PUERTA.** Si la curva sale plana, se dice tal cual y se decide si 1c aporta.

### Fase 1c — el plantel completo (opcional por diseño)

Los nueve modelos sobre N0 y N1: **288 conversaciones, ≈ 45 $**, más caras porque
entran `sol`, `opus-5` y `gemini-2.5-pro`.

**Solo tiene sentido si el contraste por familia aguanta en 1a**, que ya lleva
tres modelos y por tanto le da su primera prueba real. 1c añade los otros seis.

El contraste a comprobar, medido en Fase 0 sobre 8 conversaciones por modelo:

| | Hace el trabajo | Pregunta por el formato | Menciona el salto |
|---|---|---|---|
| GPT-5.6 sol | 5 | **3** | 0 |
| GPT-5.6 luna | 5 | **2** | 0 |
| Claude Opus 5 | 4 | **0** | **2** |

Los cinco «¿qué quieres que haga con esto?» salieron de los dos GPT, que nunca
mencionan el salto. Opus no preguntó por el formato ni una vez y es el único que
lo nombra. **Ocho por modelo no sostienen nada**; esto es la hipótesis, no el
hallazgo.

### Coste total

**110-130 $** si se corren las tres. Bastante más que los 20-35 $ del plan viejo,
y la razón es honesta: aquel plan medía una sola cantidad y esa cantidad resultó
ser constante.

## 8. Lo que NO se hace

- **No se replica la Fase 0 tal cual.** N0 con potencia ya cumple esa función.
- **No se usan las conversaciones de la Fase 0 en el recuento.** Su rúbrica era
  la v1, sin categoría G, y reetiquetarlas contaminaría el análisis. Siguen
  sirviendo como material citable para el artículo 1.
- **No se toca el turno de reparación.** Eso es la Fase 2 y su propio artículo.

## 9. Prerrequisito bloqueante: el segundo juez

`gpt-5.5-tst` ya está liberado y verificado. Falta el segundo, y **tiene que
estar fuera del plantel**. Lo ideal es que sean de familias distintas, para que
un sesgo de familia no pase desapercibido. Tres salidas:

1. **Habilitar `claude-haiku-4-5` en Vertex** como juez 2. Está en el catálogo de
   `us-central1`. Cuesta otra compra de Marketplace con su cuestionario y su
   firma, como Opus y Sonnet.
2. **Sacar `gemini-2.5-flash` del plantel evaluado** y usarlo de juez. Gratis en
   trámite, pero se pierde un modelo de los nueve.
3. **Usar `gpt-5-mini-tst`**, ya registrado en el gateway. Sin trámite, pero es
   de la misma familia que tres de los evaluados y es débil para una tarea de
   clasificación con rúbrica de siete categorías.

Recomendación: la 1. El coste es un trámite que ya sabemos hacer, y tener jueces
de dos familias distintas es lo que hace que el acuerdo entre ellos signifique
algo.

## 10. Riesgos

- **Que N1 no sea realmente detectable.** Es posible que un fragmento cortado a
  mitad de frase se lea como «el usuario pegó algo mal» sin que eso lleve a
  preguntar. Mitigación: N2 existe precisamente como techo, y si N2 tampoco
  mueve nada, el resultado es mucho más fuerte.
- **Que la categoría G sea ambigua frente a C.** «Nombra el salto» y «pone en
  duda la intención» se pueden confundir. Mitigación: el acuerdo entre jueces la
  delataría, y la definición del §3 pone el criterio en la intención, no en el
  contenido.
- **Que el etiquetado a ciegas del agente arrastre el sesgo de quien escribió la
  rúbrica.** Es el motivo de la auditoría del autor sobre 20 casos (§6.3).
- **Colinealidad registro↔similaridad**, heredada de la D15 de las correcciones:
  sigue viva en 1b y sigue siendo una limitación declarada, no arreglada.

## 11. Estructura tentativa del artículo 2

1. El artículo 1 decía «nadie se plantea que te hayas equivocado». Faltaba una
   pregunta: ¿y si no les dimos ocasión?
2. Los tres niveles de pegote, y por qué N2 es trampa declarada.
3. Las dos tasas, y qué las mueve.
4. Si algo mueve G: el umbral, y qué señal hace falta.
   Si no: por qué un cero con 288 conversaciones y tres niveles pesa mucho más
   que un cero con 24.
5. El reparto por familia, ahora con potencia.
6. La curva, si la hay.
