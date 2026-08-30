# Relevancia diferida: dónde se rompe el estado explícito

**Fecha:** 2026-08-30
**Estado:** spec aprobado, pendiente de plan de implementación

**Estructura en tres bloques.** El eje que separa los bloques no es la dificultad sino qué
permite cada entorno:

| Bloque | Contenido | Entornos |
|---|---|---|
| **1. Réplica** | Los 4 runtimes originales + control de presupuesto igualado | Los **cuatro** suyos: Warehouse, Software Repository, InterCode CTF, τ-Bench (Retail y Airline) |
| **2. Expansión** | Sondas A, B, C + eje de esquema | Los dos sintéticos **+ τ-Bench Retail** (variante derivada, ver abajo) |
| **3. Generalización** | Sondas sobre repositorio de código real | Posterior y condicionado al resultado del bloque 2 |

**Qué hace falta para manipular `k`.** No control sobre el entorno, como parecía a primera
vista, sino control sobre **algún canal que transporte el hecho latente** hasta el agente, y
un evaluador que sepa si la acción posterior fue correcta. Eso admite tres respuestas
distintas según el entorno:

- **Warehouse y Software Repository:** controlamos la generación entera. `k` se fija de
  forma exacta y el ground truth es perfecto. Son el entorno principal de las sondas.
- **τ-Bench:** no controlamos el entorno, pero **sí el simulador de usuario**, y ese es un
  canal suficiente. Ver §4.5. `k` se fija en turnos de usuario, no en pasos, y el evaluador
  oficial ya comprueba si el estado final viola la intención — que es exactamente la
  pregunta que hace la sonda.
- **InterCode CTF:** descartado para sondas. Se puede inyectar en la salida del shell, pero
  la trayectoria la decide el modelo: no podemos garantizar que llegue al paso dependiente en
  `t+k`, así que `k` sería una variable observada y dispersa, no fijada. Con 100 retos la
  potencia estadística no da. Queda como plan B si τ-Bench se complica.

Esta es la restricción real, y es del método. Conviene declararla así en el artículo, porque
es la primera pregunta que hará un revisor.

## 1. Contexto y objetivo

[SKILL.state](https://arxiv.org/abs/2608.26263) (Badhe et al., Google/Purdue, EMNLP 2026)
sustituye el historial conversacional acumulado por un estado de ejecución explícito y
mutable. En cada paso el modelo recibe solo `(P, Σ_t, O_t)` — especificación inmutable,
estado estructurado, última observación — emite un parche JSON validado por el runtime, y
**la traza de razonamiento se descarta de forma permanente**. Prompt O(1), coste acumulado
O(T) en lugar de O(T²).

Sus resultados son sólidos, en particular el control con presupuesto igualado (§5.6): a
~1.800 tokens, truncado 0.18, resumen capado 0.52, LLMLingua 0.22, SKILL.state 0.94. La
ganancia no viene de tener el prompt más corto, viene de la estructura.

Su sección 7 dice que el supuesto de estadístico suficiente **"falla en tres escenarios
distintos"**. No mide ninguno de los tres.

**Objetivo:** réplica cruzada de modelo + caracterización cuantitativa de esa frontera.
Formato realista: workshop paper o preprint corto, más artículo divulgativo bilingüe en el
blog. No es contribución de track principal y el diseño no debe pretenderlo.

## 2. Contribución declarada

1. **Réplica cruzada de modelo sobre sus cuatro entornos.** Warehouse y Software Repository
   (SkillExecBench), InterCode CTF y τ-Bench (Retail y Airline). Ellos usan Gemini-3-Flash,
   Gemma-4-31B y Qwen-3-8B; nosotros Claude Haiku 4.5 y Sonnet 5. Que el efecto sobreviva a
   otra familia de modelos es resultado por sí solo, y cubrir los cuatro es lo que separa
   una réplica de una anécdota.

   **No existe código público de SkillExecBench**: sus dos entornos sintéticos los
   reimplementamos desde la descripción de su §4.1, y cualquier discrepancia con sus números
   ahí es indistinguible de un error nuestro. Los otros dos no tienen ese problema —
   InterCode CTF y τ-Bench son benchmarks públicos con evaluador programático propio, así
   que los integramos en vez de reimplementarlos. Esa asimetría es un argumento a favor de
   incluirlos: son los dos entornos donde nadie puede acusarnos de habernos construido el
   rival a medida.
2. **Operacionalización de sus tres limitaciones declaradas** (sondas A, B y eje de esquema).
3. **Una cuarta dimensión que no está en su lista: irrecuperabilidad** (sonda C). El paper
   reporta tasas de error y nunca su reversibilidad. Con historia, un error de razonamiento
   es recuperable porque la observación cruda sigue presente; con estado, un borrado
   erróneo es definitivo. Su propia taxonomía (§5.7) dice que el 68% de los fallos en
   modelos abiertos son borrado o sobrescritura prematura del estado.

## 3. Mapa sonda ↔ limitación

| Sonda | Limitación del paper (§7) | Variable barrida |
|---|---|---|
| **A. Regla contingente latente** | L2: "el update correcto depende de una observación cuya relevancia no se reconoció al observarla" | lag `k` ∈ {1, 5, 10, 20, 40} |
| **B. Objetivo sobre la trayectoria** | L3: "auditar, depurar procedencia, explicar acciones pasadas" | tipo de consulta final (3 tipos) |
| **C. Invalidación retroactiva** | ninguna — aportación propia | lag de invalidación ∈ {5, 15, 30} |
| **Eje de esquema** | L1: "no se conoce un esquema fijo de antemano" | sin escotilla / `notes` libre / oráculo |

## 4. Entorno

**Bloque 1 (réplica)** corre sobre los cuatro:

- **Warehouse Management** (SkillExecBench §4.1) — reimplementado. Inventario discreto y
  determinista, 500 estanterías independientes, acciones `Store`, `Move`, `Ship`, `Wait`,
  transiciones con ground truth exacto. Es el de su Tabla 1.
- **Software Repository** (SkillExecBench §4.1) — reimplementado. Grafo relacional de ramas,
  commits, PRs y estados de CI; acciones `CherryPick`, `Merge`, `RunTests`, `CreateRelease`,
  `Rollback`. Dependencias densas: una sola acción altera el estado de la rama destino y de
  las PRs dependientes.
- **InterCode CTF** — integrado, no reimplementado. 100 retos de bash en Docker.
- **τ-Bench Retail y Airline** — integrados. Evaluador oficial programático que verifica que
  el estado final de la base de datos satisface la intención del usuario sin violar política.

**Bloque 2 (sondas)** corre sobre Warehouse, Software Repository y τ-Bench Retail. Warehouse
es el entorno principal —variables de estado independientes, más fácil aislar el efecto del
lag—; Software Repository actúa como control de generalización dentro del bloque: si el
efecto aparece en uno y no en el otro, eso acota la tesis. τ-Bench Retail es el que impide
que la expansión entera sea sintética (ver §4.5).

El determinismo de los dos primeros permite puntuación programática sin LLM-judge; τ-Bench
trae su propio evaluador programático.

**Ruido de fondo.** Reutilizamos su inyector de distractores (telemetría de sistema,
actividad irrelevante, overrides de reglas). Diferencia central: en nuestras sondas
**algunos eventos inyectados llegan a ser portantes**. Su experimento de ruido y el nuestro
se diferencian en un bit — si el evento inyectado acaba importando o no.

Por defecto las sondas corren **sin ruido de fondo** y con exactamente un evento latente,
para no confundir relevancia diferida con robustez al ruido. Condición secundaria con ruido
a su tasa baja (5 eventos/turno) para comprobar que el efecto sobrevive al desorden realista.

### 4.1 Sonda A — regla contingente latente

En el paso `t` el entorno emite un boletín de fondo: p. ej. *"el escáner de la estantería 17
está descalibrado: sus lecturas van +3"*. En el momento en que llega es indistinguible de la
decoración y no afecta a la acción en curso. En el paso `t+k` el agente debe operar sobre la
estantería 17 y la acción correcta exige aplicar la corrección.

**`k` es la variable controlada, no la posición del boletín.** La posición absoluta `t` se
aleatoriza por seed dentro del primer tercio del episodio; lo que se fija por celda
experimental es la distancia `k` hasta el paso dependiente. Así el efecto medido es el lag,
no el momento del episodio en que ocurre.

**Requisito de justicia, verificable:** ni `P` ni el esquema pueden insinuar que los
boletines importarán. Auditoría explícita del prompt antes de correr (ver §10, riesgo R3).

### 4.2 Sonda B — objetivo definido sobre la trayectoria

Al final del episodio se formula una consulta que no es función del estado final sino de la
trayectoria. Tres tipos:

- **Auditoría:** "lista todas las estanterías que tocaste y en qué orden".
- **Procedencia:** "¿qué acciones, por índice de paso, produjeron el contenido actual de la
  estantería 42?"
- **Explicación:** "¿qué acción tomaste inmediatamente después de la alerta del paso N?"

**Las tres se formulan para tener respuesta comprobable por máquina** — una secuencia de IDs
de estantería, un conjunto de índices de paso, un nombre de acción — no prosa libre. Esto es
requisito, no detalle: §7 prohíbe el LLM-judge, y una consulta de auditoría en texto abierto
lo haría inevitable.

Predicción de bajo riesgo. Su función principal es doble: cubrir L3 y servir de sanity check
de que el entorno y la puntuación funcionan.

### 4.3 Sonda C — invalidación retroactiva

En el paso `t+k` llega un mensaje: *"la lectura del paso `t` venía de un sensor averiado;
rehaz lo que dependiera de ella"*. Un runtime con historia conserva la lectura cruda y puede
recomputar. Un runtime de estado tiene solo el valor derivado, sin procedencia.

Es la sonda más cercana a la vida real de un agente de código ("el fichero que leí antes
estaba obsoleto").

### 4.4 Eje de esquema

Solo aplica a los brazos de estado. Tres condiciones:

| Condición | Esquema | Qué mide |
|---|---|---|
| Sin escotilla | Campos fijos del dominio, ninguno para `F` | El caso del paper tal cual |
| Escotilla libre | Añade un campo `notes` de texto libre | ¿Se arregla dejando acumular? |
| Oráculo | Incluye un campo específico para `F` | Cota superior |

**La condición interesante es la del medio.** Si la escotilla libre recupera la pérdida, la
recupera reinventando la historia: Σ deja de estar acotado y se pierde el O(1) que era todo
el punto. Medimos `|Σ_t|` frente a `t` para cuantificarlo, no solo para afirmarlo.

### 4.5 Sonda A sobre τ-Bench Retail (variante derivada)

El canal que transporta el hecho latente es **el simulador de usuario**, no el entorno. En
τ-Bench el agente atiende a un usuario simulado mientras consulta y modifica una base de
datos relacional bajo restricciones de política; el evaluador oficial verifica que el estado
final satisface la intención sin violar política.

**Construcción.** Partimos de tareas existentes de Retail y creamos pares de variantes que
difieren en una sola cosa:

- **Control:** el usuario enuncia su restricción (*"no me sirve si no llega antes del
  viernes"*, *"no quiero que se cargue a la tarjeta que acaba en 4471"*) **en el turno de la
  decisión**, donde es inmediatamente accionable.
- **Diferida:** el usuario enuncia la misma restricción **`k` turnos antes**, enterrada bajo
  gestiones intermedias que no la usan.

La diferencia de éxito entre las dos variantes, con la misma tarea y el mismo evaluador, es
el efecto de relevancia diferida en un benchmark público. `k` ∈ {2, 5, 10} turnos de usuario.

**Diferencias que hay que declarar y no disimular:**

- `k` se mide en **turnos de usuario**, no en pasos de entorno. Comparable dentro de τ-Bench,
  no directamente comparable con la `k` de los sintéticos. Las dos curvas no se superponen
  en la misma figura.
- Controlamos cuándo se enuncia la restricción, pero no exactamente en qué paso el agente
  llega a la decisión. El lag realizado se registra por episodio y los episodios se agrupan
  por lag real, no por lag nominal.
- Es **τ-Bench modificado**, no τ-Bench. Se etiqueta como variante derivada en todas las
  tablas y se publican las variantes de tarea junto con el código.

**Subconjunto por coste.** 30 tareas de Retail, no las ~115. La sonda completa sobre el
benchmark entero multiplicaría por cuatro la partida más cara del proyecto sin cambiar la
dirección del resultado. La reducción de potencia se declara.

## 5. Runtimes — 7 brazos

Plantillas de prompt tomadas de su Apéndice A, para que la réplica sea fiel.

1. **ReAct (Prompt).** Añade toda observación, razonamiento y acción a un transcript
   creciente. Es su baseline y nuestro control de historia completa.
2. **Compaction realista.** Sustituye a su baseline "Memory (Summary)", que es una ventana
   de 3 pasos más un resumen — no se parece a ningún harness de producción. El nuestro imita
   lo que hacen Claude Code y Codex CLI: resumen disparado por umbral de tokens, más
   re-lectura del estado del entorno tras compactar, más un bloque de instrucciones
   persistente que sobrevive intacto a la compactación. Sin este brazo el artículo compara
   contra algo que nadie usa.
3. **SKILL.state, sin escotilla.**
4. **SKILL.state, escotilla `notes`.**
5. **SKILL.state, esquema oráculo.**
6. **CWL** ([Beyond Compaction](https://arxiv.org/pdf/2606.11213), Semenov y Dorofeev,
   2026): episodios tipados anotados por el agente, grafo de dependencias explícito y
   política de eviction determinista y sin LLM. Es el rival conceptual directo — conserva la
   historia y evicta con estructura, en vez de sustituirla. Su evidencia publicada es floja
   (una sola sesión, sin baselines), así que medirlo contra los demás tiene valor propio.

7. **Historia truncada a presupuesto igualado.** Ventana deslizante recortada al mismo
   número de tokens que consume el brazo de estado. Es su control de §5.6 — el resultado que
   hace su paper defendible, y que ningún revisor nos perdonaría omitir en algo que se
   presenta como réplica.

   Pero aquí cumple una segunda función, y es la razón de que sea imprescindible: **sin él,
   la sonda A no significa nada**. Si SKILL.state pierde accuracy a `k` grande, hay dos
   explicaciones — que descartar la observación fue lo que la perdió, o simplemente que
   trabaja con menos tokens que ReAct. Este brazo separa las dos: comparte presupuesto con
   el estado y conserva la observación cruda. Si el truncado también falla a `k` grande, la
   pérdida es de presupuesto; si el truncado acierta y el estado no, la pérdida es del
   descarte, que es la tesis.

Su baseline "Stateful (LangGraph)" — estado estructurado **junto al** transcript completo —
queda cubierto: es punto de comparación en la calibración (§6) pero no se arrastra a las
sondas, donde no añade nada que ReAct no dé ya.

## 6. Bloque 1 — réplica, antes de cualquier sonda

Con los cuatro runtimes originales (ReAct, Memory, Stateful, SKILL.state) y ambos modelos:

- **Su Tabla 1** — Warehouse a T ∈ {10, 25, 50, 100}, 5 seeds. Es la celda de calibración
  principal: si nuestros baselines están mal implementados, aquí se ve.
- **Software Repository** a los mismos horizontes, 5 seeds. Ellos lo relegan al Apéndice 7;
  nosotros lo tratamos igual que Warehouse porque es el segundo entorno donde luego corren
  las sondas.
- **Su Tabla 4** — InterCode CTF (100 tareas) y τ-Bench Retail y Airline. Sin seeds, igual
  que ellos: reportan un número único por celda. Aquí replicamos pass@1 / pass rate, tamaño
  de prompt y tokens acumulados.

- Si reproduce la dirección de sus resultados → la réplica cruzada de modelo ya es resultado
  publicable y sabemos que nuestros baselines están bien implementados.
- Si no reproduce → **eso** es el artículo, y las sondas pasan a segundo plano.

Añadimos también su **control de presupuesto igualado** (§5.6) a T=100: truncado por ventana
deslizante, resumen capado y — si el coste de integrarlo es razonable — LLMLingua, todos
fijados al presupuesto que consume SKILL.state. Es el resultado más fuerte del paper y el
que un revisor esperará ver replicado.

**Se omite T=200** deliberadamente: son 5–6M tokens por run de baseline con historia y no
dice nada que T=100 no diga ya.

La calibración es además el único test que tenemos de que los baselines no están
saboteados por implementación descuidada (riesgo R1).

## 7. Métricas

1. **Accuracy** — su métrica de SkillExecBench: acciones correctas / eventos accionables.
   Puntuación programática y determinista. Sin LLM-judge.
2. **Tamaño medio de prompt** por invocación y **tokens acumulados** por episodio.
3. **`|Σ_t|` frente a `t`** — tamaño del estado. Distingue O(1) real de O(1) nominal.
4. **Sonda de estado (instrumentación propia).** Inspeccionamos Σ en `t+k` para determinar
   si `F` estaba presente. Separa **pérdida de representación** (el hecho nunca se
   comprometió) de **fallo de razonamiento** (estaba y no se usó). Los baselines con
   historia no admiten esta lectura, y es lo que convierte el resultado en explicativo en
   lugar de descriptivo.
5. **Tasa de fallo irrecuperable** (sonda C): fracción de episodios donde, tras la
   invalidación, el runtime no converge al estado correcto en ningún paso posterior.

## 8. Protocolo y predicciones preregistradas

**Protocolo:** 5 seeds por celda, media ± desviación estándar muestral, paired t-test entre
brazos — igualamos su rigor estadístico (§5.1). Temperatura 0. Todas las corridas en serie.

**Límite de potencia, declarado por adelantado.** Con 5 seeds detectamos diferencias grandes
entre brazos, pero **no localizamos `k*` con precisión de punto**. El artículo debe reportar
`k*` como intervalo ("entre 10 y 20") y nunca como valor puntual. Si el cruce resulta ser el
hallazgo central y merece precisión, se amplían seeds solo en las dos celdas que lo rodean
— más barato que subir seeds en toda la rejilla.

**Predicciones registradas antes de ejecutar nada:**

- **P1.** La calibración reproduce la dirección de su Tabla 1 en ambos modelos: estado ≥
  baselines en accuracy y muy por debajo en tokens.
- **P2.** En la sonda A, la accuracy de SKILL.state sin escotilla decrece de forma monótona
  con `k`, mientras ReAct se mantiene plano hasta agotar ventana. Existe un `k*` de cruce.
- **P3.** La escotilla `notes` recupera parte sustancial de la pérdida, pero `|Σ_t|` crece
  con `t`. Cuantificamos la pendiente.
- **P4.** El esquema oráculo elimina casi toda la pérdida → la pérdida es atribuible al
  desconocimiento del esquema, no al estado en sí.
- **P5.** En la sonda B, todos los brazos de estado fallan y los de historia no.
- **P6.** En la sonda C, la tasa de fallo irrecuperable es mayor en estado que en historia,
  con CWL en posición intermedia.

**El experimento vale igual si las predicciones fallan.** Si P2 no se cumple y no hay
degradación con `k`, el resultado es que el supuesto de estadístico suficiente aguanta más
de lo esperado — réplica negativa, igual de publicable y más útil para el lector que tiene
que decidir si adopta esto.

### 8.1 Criterios de parada y paso al bloque 3

Fijados antes de correr, para que la decisión de seguir no dependa de lo apetecible que
parezca el resultado a mitad de camino:

| Resultado | Decisión |
|---|---|
| El bloque 1 no reproduce la dirección de sus tablas **en los dos entornos reimplementados**, pero sí en los dos públicos | Es error nuestro de reimplementación, no fallo de réplica. Auditar contra su §4.1 y su Apéndice A antes de seguir. Este es el diagnóstico que hace valiosa la asimetría entre entornos reimplementados e integrados. |
| El bloque 1 no reproduce en ninguno de los cuatro | Parar las sondas. El artículo es la réplica fallida. |
| Bloque 1 reproduce, sonda A da efecto con `k` y el brazo de presupuesto igualado **no** falla igual | Resultado principal conseguido. El bloque 3 pasa a estar justificado. |
| Bloque 1 reproduce, sonda A no da efecto en ninguno de los dos entornos | Réplica positiva + frontera más robusta de lo previsto. Se escribe igual; el bloque 3 se descarta. |
| Sonda A da efecto en Warehouse pero no en Software Repository (o al revés) | La tesis existe pero está acotada al tipo de estado. Hay que caracterizar la diferencia antes de generalizar nada. |
| El brazo de presupuesto igualado falla igual que el estado | El efecto era de presupuesto, no de descarte. Se reporta como tal y **no** se escribe la tesis de la relevancia diferida. |

## 9. Presupuesto

Modelos: `claude-haiku-4-5` ($1/$5 por MTok, 200K contexto) y `claude-sonnet-5`
($2/$10, 1M contexto).

Cifras extrapoladas de sus Tablas 1 y 4; sus consumos son con Gemini-3-Flash y Gemma, así
que los nuestros pueden desviarse. Tratar como orden de magnitud, no como presupuesto cerrado.

| Bloque | Coste estimado |
|---|---|
| **1.** Warehouse, 4 horizontes × 5 seeds × 2 modelos | ~$70 |
| **1.** Software Repository, ídem | ~$70 |
| **1.** InterCode CTF (~3,5M tokens × 2 modelos) | ~$11 |
| **1.** τ-Bench Retail + Airline (~34M tokens × 2 modelos) | ~$100 |
| **1.** Control de presupuesto igualado a T=100 (§5.6) | ~$15 |
| **2.** Sonda A en los dos sintéticos (5 valores de `k` × 7 brazos × 5 seeds × 2 modelos) | ~$185 |
| **2.** Sonda A en τ-Bench Retail derivado (3 valores de `k` × 7 brazos × 30 tareas × 2 modelos) | ~$70 |
| **2.** Sonda B (2 entornos sintéticos) | ~$38 |
| **2.** Sonda C (3 lags × 7 brazos × 5 seeds × 2 modelos × 2 entornos) | ~$115 |
| Margen de depuración y recorridas | ~$150 |
| **Total** | **$800–900** |

τ-Bench es la partida cara del bloque 1 y no admite recorte sin dejar de ser réplica: sus
prompts llegan a 5.000 tokens por paso en Airline, y ese es justamente el caso donde su
método más luce.

**Palancas de recorte, en orden de menor daño:**

1. Sondas solo en Warehouse, dejando Software Repository para después (−$170). Se pierde el
   control de generalización interna del bloque 2.
2. Sonnet 5 solo en el bloque 1, sondas con Haiku (−$150). No toca ninguna conclusión sobre
   `k`, pero se pierde el eje de escala en las sondas, que era medio artículo.
3. Bloque 1 con un solo modelo (−$130). No lo recomiendo: la réplica cruzada de modelo es la
   mitad de la contribución declarada.

Nada corre en local. Todo contra la API, en serie.

## 10. Riesgos

- **R1 — baselines mal implementados.** Si nuestro ReAct está mal hecho, todo el resultado
  es artefacto. Mitigación: la calibración contra su Tabla 1 es exactamente ese test, y va
  antes que cualquier sonda.
- **R2 — desbordamiento de contexto en Haiku.** 200K de ventana; a T=100 los brazos con
  historia pueden no caber. No es un bug: se reporta como hallazgo ("el baseline de historia
  no llega"), que es precisamente la razón de existir de la compactación. Se registra
  explícitamente en vez de recortarse.
- **R3 — fuga de la regla latente.** Si `P` o el esquema insinúan que los boletines
  importan, la sonda A queda invalidada. Mitigación: auditoría del prompt por lectura
  independiente antes de la primera corrida, y una condición de control donde el boletín
  nunca llega a ser portante (debe dar accuracy plana en todos los brazos).
- **R4 — generalización de las sondas.** Dos de los tres entornos de sondas los generamos
  nosotros. Mitigación: τ-Bench Retail derivado aporta un entorno público con evaluador
  ajeno, y Software Repository actúa como control de generalización interna. Sigue siendo
  limitación declarable; el bloque 3 existe para cerrarla.
- **R6 — benchmark modificado.** Las variantes de τ-Bench las escribimos nosotros, así que
  podríamos construirlas —sin querer— de forma que favorezcan la hipótesis. Mitigaciones:
  las variantes control y diferida son **la misma tarea con la restricción movida de sitio**,
  no tareas distintas; se publican íntegras junto al código; y el par control/diferida a `k`
  mínimo funciona como condición nula, donde no debe haber diferencia entre runtimes.
- **R5 — la novedad no está verificada.** Damos por hecho que nadie ha medido relevancia
  diferida en runtimes de agente a partir de una búsqueda superficial. Para un blog basta;
  para un preprint no. **Paso previo obligatorio antes de escribir una línea de código:**
  revisión de trabajo relacionado en condiciones sobre relevancia diferida, olvido inducido
  por compresión y benchmarks de horizonte largo, con el resultado registrado en el
  repositorio. Si alguien ya lo midió, el trabajo se reencuadra como réplica de dos papers
  en lugar de expansión de uno — sigue siendo publicable, pero con otra tesis.

## 11. Entregables

1. Repositorio público con entorno, runtimes, corredor de experimentos y datos crudos
   (patrón `repoUrl` del frontmatter, como `forgetting-you-dont-measure`).
2. Figura principal: accuracy frente a `k` por runtime.
3. Figura secundaria: `|Σ_t|` frente a `t` en la condición de escotilla libre.
4. Artículo bilingüe EN/ES en el blog.
5. Preprint corto, si la calibración y al menos una sonda dan resultado limpio.

## 12. Fuera de alcance

- **Sondas en InterCode CTF:** se replica (bloque 1) pero no se manipula — la trayectoria la
  decide el modelo y `k` no sería fijable. Plan B si τ-Bench se complica.
- **Sondas B y C sobre τ-Bench:** solo la sonda A cruza a τ-Bench. B exige consultas de
  trayectoria con respuesta comprobable por máquina y C exige procedencia sobre una
  observación concreta; ninguna de las dos encaja en su bucle usuario-agente sin rehacer el
  evaluador, que es más trabajo del que aportan.
- Repositorio de código real (bloque 3).
- Modelos de pesos abiertos: requieren ejecución local y la máquina está saturada.
- Horizonte T=200.
- Escenario multiagente (el paper también lo excluye).
