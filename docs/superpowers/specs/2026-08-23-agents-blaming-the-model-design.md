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
LLM cuando venía de los inputs; el reflejo de bajar la temperatura como remedio;
una migración de modelo declarada "peor" sin auditar ni la equivalencia de los
prompts ni el gold set; y, cuando por fin acepta que el problema es de diseño,
un remedio a base de regex y listas de palabras que no generaliza.

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
| 1. Ensayo | Experiencia, cinco historias | Plantea el fenómeno |
| 2. Atribución y remedio | Experimento medido | Mide el fallo |
| 3. Información vs. regla | Experimento medido (2×2) | Mide el arreglo |

Cada pieza es un artículo independiente y se publica por separado, una rama por
artículo, nunca dos merges a `main` a la vez.

---

## Pieza 1 — Ensayo

Cinco historias, cada una un desplazamiento distinto de la sospecha:

1. **La traza.** Hipótesis plausibles e incontrastables en lugar de instrumentar.
   A nadie se le ocurrió pedir ver el razonamiento; hubo que decidirlo desde
   fuera. Hallazgo: tener la información completa resultó más efectivo que la
   regla de cómo analizarla.
2. **La estocasticidad.** Variabilidad atribuida al muestreo del LLM cuando
   venía de inputs que cambian, reglas ambiguas y tools mal definidas.
3. **El interruptor.** El tratamiento reflejo de la historia anterior: bajar la
   temperatura. Falla en dos capas — no es la causa, y en muchos modelos
   actuales ni siquiera es un parámetro disponible; se entera cuando la API
   devuelve un error. Es falta de metaconocimiento factual sobre los modelos que
   él mismo usa, en su forma más literal.
4. **El ground truth.** Un modelo nuevo declarado "peor" que el viejo sin
   auditar la equivalencia del prompt ni el gold set. Aquí la asimetría es
   literal: sospecha del modelo antes que de su propio método.
5. **El determinismo burdo, y su motivo.** Cuando acepta que es diseño, el
   remedio es un regex. Detrás está la otra mitad de la tesis: no confía en que
   el modelo discierna, así que busca reglas donde no las hay.

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
4. Cuando propone un remedio, ¿es un interruptor, es frágil o es estructural — y
   cuánta variabilidad elimina realmente?
5. Ante una tarea irreductiblemente de juicio, ¿deja juzgar al modelo o intenta
   sustituirlo por reglas?

### La tarea nuclear

Todos los escenarios comparten una misma tarea, y eso es lo que los hace
comparables y lo que garantiza que un LLM es genuinamente necesario.

Un agente clasificador recibe **un repositorio de software** (nombre y poco
más), dispone de `search`, `fetch_page` y `lookup_taxonomy`, lee documentos de
prosa libre —README, `docs/`, la web del proyecto— de longitud y calidad muy
variables, y devuelve un código de una **taxonomía jerárquica de dominio de
aplicación** de dos niveles (p. ej. infraestructura → observabilidad; datos →
ETL; IA → agentes; negocio → pagos), una **confianza declarada** y una
justificación.

No lo resuelve un regex: hay que leer prosa, distinguir la actividad principal
de las secundarias y mapear a una taxonomía con reglas de precedencia.

**Corpus:** repositorios de cola larga (baja popularidad, y preferentemente
recientes) para minimizar la contaminación por memorización. El ground truth de
la clasificación se etiqueta por consenso sobre una muestra; nótese que el
ground truth del **diagnóstico** no depende de ese etiquetado, porque la causa
de cada fallo está plantada por construcción.

**El sistema descrito en los escenarios usa un modelo de razonamiento que no
expone parámetro de temperatura.** Es realista, y convierte el reflejo del
interruptor en un error atrapable en vez de una opinión discutible.

### Clase A — la variabilidad es de diseño

La causa está en el código o en el prompt y es invisible sin traza.

- **A1. Orden de recuperación inestable.** Los empates de score se resuelven por
  orden de inserción; el documento decisivo cae en posición 1 o en 5 según la
  corrida y, con el truncado de contexto, a veces no llega al modelo.
- **A2. Campo ausente intermitente.** La descripción oficial del repositorio
  llega sólo cuando existe, y el prompt asume que siempre está. Al faltar, el
  modelo infiere del nombre — y el nombre puede ser genérico.
- **A3. Empate de reglas sin precedencia.** "Clasifica por el dominio de
  aplicación principal" y "si es una librería para desarrolladores, usa
  herramientas de desarrollo" aplican a la vez sobre un SDK de pagos. Nadie
  declaró cuál gana; decide qué documento se leyó antes.
- **A4. Presupuesto descontado dos veces.** El agente tiene N búsquedas y una
  parte del código las descuenta doble, así que a veces se queda sin presupuesto
  antes de encontrar la web del proyecto. La confianza declarada no baja, porque
  el techo se calcula sobre un valor fijo. El síntoma parece del modelo; la
  causa está en la contabilidad del presupuesto.

A4 es el más representativo del conjunto.

**Control sin IA.** Cada escenario de clase A se reescribe pareado, con la misma
estructura causal, la misma evidencia disponible y sin modelo: dedup con empates
inestables, un ETL al que le falta un campo opcional, un motor de reglas con dos
reglas que colisionan, un job batch con el presupuesto mal contado. Si pide logs
en la versión ETL y acepta "es el modelo" en la versión LLM, el resultado está
probado.

### Clase B — juicio irreductible

No hay regla enumerable y el conjunto de casos no está acotado; lo correcto es
dar buen andamiaje al modelo y dejarle discernir. En los tres, la tentación
determinista es evidente y se hunde de inmediato.

- **B1. Atribución de agencia.** ¿El proyecto *hace* X, o es un cliente de X?
  "Wrapper de la API de", "bindings para", "integración con". El espacio de
  formulaciones no lo cubre ninguna lista.
- **B2. Actividad vigente vs. histórica.** "Originalmente un fork de", "ahora
  deprecado en favor de", "reescrito desde cero en la v3". Hay que decidir qué
  manda hoy.
- **B3. Distintividad del nombre.** ¿Es este nombre lo bastante distintivo para
  que un resultado de búsqueda sea *este* proyecto y no un homónimo? La
  tentación es contar palabras o mantener una lista de términos genéricos.

No hay control sin IA para la clase B: sin modelo no existe la opción de "dejar
juzgar al modelo", así que la comparación no tendría sentido.

### Métricas

De **cada corrida** salen dos familias, diagnóstico y tratamiento.

**Diagnóstico** (clase A y controles)
- Categoría de la causa nombrada en primer lugar: `estocasticidad del modelo` /
  `input o datos` / `prompt o reglas` / `tools` / `contexto y truncado` /
  `código del harness` / `otro`.
- Binaria: ¿aparece la estocasticidad como causa principal?
- ¿Propone instrumentar (traza, logs, reproducción) antes de concluir? ¿En qué
  turno?
- Contrastabilidad: ¿la hipótesis emitida es verificable con lo que hay a la
  vista, o requiere información que nadie tiene?

**Tratamiento** (clase A y B) — rúbrica de tres categorías:
- **Interruptor**: temperature, top_p, seed, "usa un modelo mejor". Parámetros
  que no tocan el diseño.
- **Frágil**: regex, keyword, lista hardcodeada, umbral mágico.
- **Estructural**: esquema de salida, tool tipada, regla de desempate explícita,
  validador, orden determinista, corregir el bug del presupuesto.

Más dos métricas propias:
- **Interruptor imposible**: ¿propone tocar la temperatura de un sistema cuyo
  modelo no la acepta? Binaria y limpia; mide metaconocimiento factual.
- **Cobertura real**: el remedio propuesto se **ejecuta contra un held-out de
  variantes** que el agente no vio (paráfrasis, negaciones, lenguaje indirecto,
  otros ecosistemas). Se reporta qué fracción de la variabilidad elimina de
  verdad. Un regex que resuelve el caso mostrado y muere en las variantes deja
  de ser una opinión sobre estilo y pasa a ser un número.

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

### Calibración, congelación y confirmación

El diseño de los escenarios se itera, pero con una separación estricta de fases
y de criterios. Sin esa separación, iterar hasta reproducir el fenómeno
esperado es indistinguible de fabricarlo.

**Fase 1 — calibración.** Pocos escenarios, pocos modelos, muchas pasadas
manuales. Se reproducen los bugs y se observa qué investiga el agente y qué
arregla. Aquí se itera libremente el escenario, el bug elegido y el contexto de
la tarea.

El criterio de iteración es de **fidelidad, no de resultado**: la pregunta es
"¿es este el bug que aparece en producción y el contexto que tiene delante un
ingeniero real?", nunca "¿sale el porcentaje que esperaba?". Un escenario se
descarta por poco realista, por trivial o por mal instrumentado. **No se
descarta por dar un resultado incómodo.**

El juez de fidelidad es Javier: él tiene la experiencia que esto pretende
replicar, así que revisa los escenarios antes de congelarlos. Si al final de la
calibración los agentes no fallan como él los ha visto fallar, la primera
hipótesis es que el escenario está mal construido; la segunda, que el fenómeno
es más estrecho de lo que parecía. Ambas son publicables, pero sólo la segunda
después de haber agotado la primera.

**Fase 2 — congelación.** Escenarios, prompts, rúbrica y métricas quedan fijos y
commiteados con su hash antes de lanzar nada. A partir de ahí no se tocan.

**Fase 3 — confirmación.** El run completo corre sobre el conjunto congelado y
se reporta lo que salga, incluido un resultado nulo.

**Escenarios reservados.** Un subconjunto se construye *después* de congelar y
no participa en la calibración. Si el hallazgo se sostiene también ahí, no es
un artefacto de la iteración. Es la prueba más barata contra ese sesgo y se
reporta por separado.

### Amenazas a la validez

- **El enunciado señaliza.** Preguntar "¿por qué varía?" invita a explicar en vez
  de investigar. Mitigación: framing neutro, encargo de investigar, y medir la
  primera acción, no la primera frase.
- **La palabra "LLM" en el enunciado** es exactamente la variable manipulada en
  el control; hay que mantener el resto del texto lo más pareado posible.
- **Contaminación del corpus**: repositorios muy conocidos podrían clasificarse
  de memoria. Mitigación: cola larga y verificación de que la dificultad real se
  mantiene.
- **Sesgo del juez codificador**: mitigado con juez ajeno al panel y validación
  manual.
- **El held-out hay que ejecutarlo**, no estimarlo. Si no se ejecuta, la métrica
  de cobertura no se publica.
- **Sobreajuste del escenario durante la calibración**: es la amenaza más seria
  de todo el diseño, porque el fenómeno se busca a sabiendas. Mitigada por la
  separación de fases y por los escenarios reservados.

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

**Tarea:** sobre la misma tarea nuclear, dado un conjunto de clasificaciones
fallidas con causas plantadas y conocidas, diagnosticar la causa raíz de cada
una.

**Métricas:** precisión del diagnóstico contra la causa real, tasa de hipótesis
inventadas o incontrastables, y coste en turnos y tokens.

**Hipótesis a contrastar:** el efecto principal de la traza domina al de la
instrucción; es decir, dar la información rinde más que dar la regla.

**Título candidato:** "Dale la traza, no la regla".

---

## Anonimización

Los escenarios son sintéticos en su causa y se montan sobre un corpus público de
repositorios de software. No entra nada del trabajo real: ni dominio, ni
taxonomía, ni nombres de repositorio internos, ni referencias a tickets. El repo
del blog y el del experimento son públicos.

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
- Criterio concreto de selección del corpus de repositorios de cola larga.
- Si la clase B se solapa demasiado con la pieza 3 al escribir, la salida limpia
  es moverla entera allí y dejar la pieza 2 puramente sobre atribución.
- Si la pieza 3 reutiliza el mismo repo y el mismo runner que la pieza 2.
