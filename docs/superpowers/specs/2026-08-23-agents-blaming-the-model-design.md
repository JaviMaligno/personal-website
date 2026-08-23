# Serie: el agente culpa al modelo lo que no se culparía a sí mismo

Fecha: 2026-08-23
Estado: diseño aprobado en brainstorming, pendiente de plan de implementación

## Origen

Trabajando en un clasificador con agentes se repitió un patrón: ante resultados
que variaban, el agente producía hipótesis plausibles e incontrastables en lugar
de pedir ver lo que había pasado. La solución no fue una regla de análisis mejor;
fue instrumentar. Tres iteraciones de traza —qué se buscó y qué trajo, qué
documentos llegaron de verdad al modelo, todas las llamadas a herramientas y no
sólo las búsquedas— y el análisis mejoró solo.

El mismo patrón aparece en otros sitios: variabilidad atribuida al muestreo del
LLM cuando venía de los inputs; una migración de modelo declarada "peor" sin
auditar ni la equivalencia de los prompts ni el gold set; y, cuando por fin
acepta que el problema es de diseño, un remedio a base de regex y listas de
palabras que no generaliza.

## Tesis

**El agente culpa al modelo lo que no se culparía a sí mismo, siendo la misma
cosa.** Razona bien sobre software y mal sobre software con un LLM dentro.

La tesis es simétrica, y esa simetría es el hallazgo: el agente **calibra mal
dónde va el modelo y dónde va la regla, y se equivoca en las dos direcciones**.

- Sospecha del modelo donde el fallo es de diseño → "es estocástico", y deja de
  investigar.
- Desconfía del modelo donde el modelo *es* la solución → intenta domar con
  matching de palabras una tarea irreductiblemente de juicio, que es
  precisamente para lo que existe un LLM.

Y las dos se alimentan: como no se fía del discernimiento del modelo, busca
determinismo donde no lo hay, y el determinismo que encuentra es malo.

## Estructura: tres piezas

| Pieza | Qué es | Qué aporta |
|---|---|---|
| 1. Ensayo | Experiencia, cuatro historias | Plantea el fenómeno |
| 2. Atribución y remedio | Experimento medido | Mide el fallo |
| 3. Información vs. regla | Experimento medido (2×2) | Mide el arreglo |

Cada pieza es un artículo independiente y se publica por separado, una rama por
artículo, nunca dos merges a `main` a la vez.

---

## Pieza 1 — Ensayo

Cuatro historias, cada una un desplazamiento distinto de la sospecha:

1. **La traza.** Hipótesis plausibles e incontrastables en lugar de instrumentar.
   A nadie se le ocurrió pedir ver el razonamiento; hubo que decidirlo desde
   fuera. Hallazgo: tener la información completa resultó más efectivo que la
   regla de cómo analizarla.
2. **La estocasticidad.** Variabilidad atribuida al muestreo del LLM cuando
   venía de inputs que cambian, reglas ambiguas y tools mal definidas.
3. **El ground truth.** Un modelo nuevo declarado "peor" que el viejo sin
   auditar la equivalencia del prompt ni el gold set. Aquí la asimetría es
   literal: sospecha del modelo antes que de su propio método.
4. **El determinismo burdo, y su motivo.** Cuando acepta que es diseño, el
   remedio es un regex. Detrás está la otra mitad: no confía en que el modelo
   discierna, así que busca reglas donde no las hay.

Cierre: el agente y el sistema bajo análisis corren el mismo modelo. La sospecha
se detiene justo donde debería empezar.

**Tono.** Sin rotundidad ni hombre de paja. Son observaciones de trabajo, no una
ley. El ensayo puede decir que esto se puede medir y que es el paso natural, sin
comprometer fechas ni prometer resultados.

**Título candidato:** "Culpa al modelo lo que no se culparía a sí mismo".

---

## Pieza 2 — La asimetría de atribución, medida

### Preguntas de investigación

1. Ante variabilidad cuya causa es demostrablemente de diseño, ¿cuántas
   respuestas la atribuyen a la estocasticidad del modelo?
2. ¿Pide instrumentación antes de concluir, o emite hipótesis incontrastables?
3. ¿El fallo desaparece cuando el mismo problema estructural se plantea sin IA
   de por medio? (**el control que sostiene el artículo**)
4. Cuando propone un remedio, ¿es frágil o estructural — y cuánta variabilidad
   elimina realmente?
5. Ante una tarea irreductiblemente de juicio, ¿deja juzgar al modelo o intenta
   sustituirlo por reglas?

### Diseño

Todos los escenarios corren con **temperature 0 y seed fija**, y la variabilidad
mostrada es reproducible. Atribuirla al muestreo no es una opinión discutible:
es falso, y se puede afirmar sin matices.

**Clase A — la variabilidad es de diseño y tiene arreglo estructural.**

- **A1. Orden de recuperación inestable.** El retriever devuelve los 5
  documentos más similares; los empates de score se resuelven por orden de
  inserción del índice, que cambia entre corridas. Mismo input, distinto orden,
  distinta salida.
- **A2. Campo opcional ausente.** Una tool omite un campo cuando el upstream no
  lo tiene, y el prompt asume que siempre está.
- **A3. Empate sin desempate.** El prompt lista dos criterios que pueden aplicar
  a la vez y no dice cuál gana; decide el orden en que aparecen en el documento.
- **A4. Truncado por presupuesto.** El contexto se recorta por longitud y a veces
  cae fuera el documento decisivo. La variabilidad correlaciona con el tamaño
  del input, no con el modelo.

**Control no-IA.** Cada escenario de clase A se reescribe con la misma
estructura causal y sin LLM: dedup con empates inestables, un ETL al que le
falta un campo opcional, un motor de reglas con dos reglas que colisionan, un
job batch que trunca. Si pide logs en la versión ETL y acepta "es el modelo" en
la versión LLM, el resultado está probado.

**Clase B — la tarea es irreductiblemente de juicio.** No hay regla enumerable y
el conjunto de casos no está acotado; la respuesta correcta es dar buen
andamiaje al modelo (esquema de salida, criterios, confianza declarada) y
dejarle discernir.

- **B1. Atribución de agencia.** Decidir si un texto dice que la actividad la
  realiza el propio sujeto o un tercero en su nombre. Infinitas formulaciones.
- **B2. Queja implícita.** Si un mensaje de soporte expresa insatisfacción sin
  decirlo.
- **B3. Identidad referencial.** Si dos descripciones se refieren a lo mismo.

La tentación medible aquí es la lista de palabras clave y el regex.

No hay control no-IA para la clase B: sin LLM no existe la opción "dejar juzgar
al modelo", así que la comparación no tendría sentido.

### Métricas

De **cada corrida** salen dos familias de métricas, diagnóstico y tratamiento:

**Diagnóstico** (clase A y controles)
- Categoría de la causa nombrada en primer lugar: `estocasticidad del modelo` /
  `input o datos` / `prompt o reglas` / `tools` / `contexto y truncado` / `otro`.
- Binaria: ¿aparece la estocasticidad como causa principal?
- ¿Propone instrumentar (traza, logs, reproducción) antes de concluir? ¿En qué
  turno?
- Contrastabilidad: ¿la hipótesis emitida es verificable con lo que hay a la
  vista, o requiere información que nadie tiene?

**Tratamiento** (clase A y B)
- Rúbrica **frágil** (regex, keyword, lista hardcodeada, umbral mágico) vs.
  **estructural** (esquema de salida, tool tipada, regla de desempate explícita,
  validador, orden determinista).
- **Cobertura real**: el remedio propuesto se **ejecuta contra un held-out de
  variantes** que el agente no vio (paráfrasis, negaciones, lenguaje indirecto,
  casos límite). Se reporta qué fracción de la variabilidad elimina de verdad.
  Un regex que resuelve el caso mostrado y muere en las variantes deja de ser
  una opinión sobre estilo y pasa a ser un número.

**Codificación.** Rúbrica escrita antes de correr nada. Codificación automática
con un juez LLM **distinto de los modelos evaluados**, validada contra
codificación manual de una muestra estratificada; se reporta el acuerdo. Es el
mismo cuidado que exigió "tres jueces, tres rankings".

### Panel y escala

Seis modelos, multiproveedor (Azure OpenAI, Claude, y un tercero vía Vertex),
como en "lo que ya ha pasado" — así se puede ver si el fallo escala o no con la
capacidad, que allí fue el hallazgo interesante.

Escala estimada nivel 1: 6 modelos × (4 A + 3 B + 4 controles) × 10
repeticiones ≈ **660 respuestas**. Orden de magnitud conocido y asumible.

### Dos niveles

- **Nivel 1** — caso escrito, respuesta única. Barato, es la columna vertebral.
- **Nivel 2** — agéntico y reducido: un repo de juguete reproducible con tools y
  logs reales, dos escenarios, 6 modelos × 5 corridas ≈ 60 sesiones. Sirve para
  comprobar que el hallazgo sobrevive fuera del formato pregunta-respuesta. Sin
  él, el artículo mide lo que el modelo *dice*, no lo que *hace*, y esa objeción
  es previsible.

### Amenazas a la validez

- **El enunciado señaliza.** Preguntar "¿por qué varía?" invita a explicar en vez
  de investigar. Mitigación: framing neutro, encargo de investigar, y medir la
  primera acción, no la primera frase.
- **La palabra "LLM" en el enunciado** es exactamente la variable manipulada en
  el control; hay que mantener el resto del texto lo más pareado posible.
- **Sesgo del juez codificador**: mitigado con juez ajeno al panel y validación
  manual.
- **El held-out hay que ejecutarlo**, no estimarlo. Si no se ejecuta, la métrica
  de cobertura no se publica.

**Título candidato:** "No es estocástico".

---

## Pieza 3 — Información vs. regla

Mide la observación más contraintuitiva del ensayo, y va contra el reflejo
actual de resolverlo todo escribiendo reglas en skills y en CLAUDE.md.

**Diseño 2×2:**

- Factor 1 — **traza**: completa (razonamiento paso a paso, confianzas,
  resultados intermedios, qué documentos llegaron realmente al modelo, todas las
  llamadas a herramientas) vs. pobre (input y output final).
- Factor 2 — **instrucción de análisis**: guía explícita de qué mirar vs. sin
  guía.

**Tarea:** dado un conjunto de clasificaciones fallidas con causas plantadas y
conocidas, diagnosticar la causa raíz de cada una.

**Métricas:** precisión del diagnóstico contra la causa real, tasa de hipótesis
inventadas o incontrastables, y coste en turnos y tokens.

**Hipótesis a contrastar:** el efecto principal de la traza domina al de la
instrucción; es decir, dar la información rinde más que dar la regla.

**Título candidato:** "Dale la traza, no la regla".

---

## Anonimización

Los escenarios son **sintéticos y de dominio neutro**, estructuralmente calcados
de los casos reales. No entra nada del trabajo real: ni dominio, ni taxonomía,
ni nombres de repositorio, ni referencias a tickets. El repo del blog y el del
experimento son públicos.

## Publicación

- Una rama por artículo, siempre desde `main` actualizado.
- Merge a `main` es la publicación irreversible: deploy más cross-posting a
  Dev.to y LinkedIn. Nunca dos artículos a la vez; uno por día como mucho.
- Los artículos con código llevan `repoUrl` en el frontmatter EN y ES para que
  el post de LinkedIn incluya el enlace al repo, además de los enlaces externos
  que cite el artículo.
- **Secuencia:** el ensayo sale en cuanto esté escrito y menciona que esto se
  puede medir y que es el paso natural, sin fecha ni promesa. Los experimentos se
  publican al terminar, en días separados.

## Repos

- Pieza 1: sólo el artículo, sin repo.
- Piezas 2 y 3: un repo público nuevo con escenarios, runner, rúbrica, datos
  crudos y análisis. Nombre propuesto: `blaming-the-model`.

## Decisiones pendientes para el plan de implementación

- Lista definitiva de los seis modelos y por qué endpoint corre cada uno.
- Estimación de tiempo y coste por corrida, partida por proveedor, antes de
  lanzar nada.
- Si la pieza 3 reutiliza el mismo repo y el mismo runner que la pieza 2 o va
  aparte.
