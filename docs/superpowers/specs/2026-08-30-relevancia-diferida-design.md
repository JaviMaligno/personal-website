# Relevancia diferida: dónde se rompe el estado explícito

**Fecha:** 2026-08-30
**Estado:** spec aprobado, pendiente de plan de implementación
**Fase:** F1 de 3 (F2 = InterCode CTF, F3 = repositorio de código real)

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

1. **Réplica parcial y cruzada de modelo.** Parcial en dos sentidos que hay que declarar en
   el artículo, no esconder: cubrimos **uno de sus cuatro entornos** (Warehouse, no Software
   Repository ni InterCode CTF ni τ-Bench), y **no existe código público de SkillExecBench**
   — reimplementamos desde la descripción de su §4.1. Ellos usan Gemini-3-Flash, Gemma-4-31B
   y Qwen-3-8B; nosotros Claude Haiku 4.5 y Sonnet 5. Que el efecto sobreviva a otra familia
   de modelos es resultado por sí solo.

   La ausencia de código es la principal amenaza a la validez de todo el trabajo: cualquier
   discrepancia con sus números es indistinguible de un error nuestro de reimplementación.
   Por eso la calibración (§6) no es un preliminar sino el resultado del que dependen los
   demás, y por eso publicamos nuestra reimplementación completa.
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

Reimplementación de su **Warehouse Management** (§4.1): dominio de inventario discreto y
determinista, 500 estanterías independientes, acciones `Store`, `Move`, `Ship`, `Wait`,
transiciones con ground truth exacto. Elegido porque es el que ellos usan para la Tabla 1
(nuestra calibración) y porque el determinismo permite puntuación programática sin
LLM-judge.

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

## 6. Calibración antes de cualquier sonda

Reproducimos Warehouse T ∈ {10, 25, 50, 100} de su Tabla 1 con los cuatro runtimes
originales (ReAct, Memory, Stateful, SKILL.state), 5 seeds, ambos modelos.

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

### 8.1 Criterios de parada y paso a F2

Fijados antes de correr, para que la decisión de seguir no dependa de lo apetecible que
parezca el resultado a mitad de camino:

| Resultado de F1 | Decisión |
|---|---|
| La calibración no reproduce la dirección de su Tabla 1 | Parar las sondas. El artículo es la réplica fallida, y antes hay que descartar error propio de reimplementación auditando contra su §4.1 y su Apéndice A. |
| Calibración reproduce, sonda A da efecto con `k` y el brazo de presupuesto igualado **no** falla igual | Resultado principal conseguido. F2 (InterCode CTF) sirve para generalizar a un entorno público y no sintético. |
| Calibración reproduce, sonda A no da efecto | Réplica positiva + frontera más robusta de lo previsto. Se escribe igual; F2 pasa a opcional y F3 se descarta. |
| El brazo de presupuesto igualado falla igual que el estado | El efecto era de presupuesto, no de descarte. Se reporta como tal y **no** se escribe la tesis de la relevancia diferida. |

## 9. Presupuesto

Modelos: `claude-haiku-4-5` ($1/$5 por MTok, 200K contexto) y `claude-sonnet-5`
($2/$10, 1M contexto).

| Bloque | Coste estimado |
|---|---|
| Calibración (4 runtimes × 4 horizontes × 5 seeds × 2 modelos) | ~$70 |
| Control de presupuesto igualado a T=100 (§5.6) | ~$15 |
| Sonda A (5 valores de `k` × 7 brazos × 5 seeds × 2 modelos) | ~$93 |
| Sonda B | ~$19 |
| Sonda C (3 lags × 7 brazos × 5 seeds × 2 modelos) | ~$58 |
| Margen de depuración y recorridas | ~$100 |
| **Total** | **$350–450** |

**Palanca de recorte si hace falta:** Sonnet 5 solo en la calibración, sondas con Haiku.
Baja a ~$150 sin tocar ninguna conclusión sobre `k`.

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
- **R4 — sobreajuste a un solo entorno.** F1 mide un único dominio sintético. Se declara
  como limitación en el artículo; F2 y F3 existen precisamente para eso.
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

## 12. Fuera de alcance de F1

- InterCode CTF (F2) y repositorio de código real (F3).
- Modelos de pesos abiertos: requieren ejecución local y la máquina está saturada.
- Horizonte T=200.
- Escenario multiagente (el paper también lo excluye).
