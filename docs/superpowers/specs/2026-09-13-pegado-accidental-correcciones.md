# Correcciones de trazabilidad — pegado accidental

Fecha: 2026-09-13
Origen: auditoría adversarial de cinco lentes + crítico de completitud sobre el
plan `2026-09-13-pegado-accidental-fase-0.md` y el código ya construido.

Este documento fija **las decisiones de diseño** que resuelven los hallazgos. El
plan y el código se actualizan contra él.

---

## D1. Prefijo compartido, autoría fija (resuelve 4 hallazgos de golpe)

**Problema.** El eje x depende de quién conteste: `conversation_text` incluía los
turnos de asistente, que los genera el modelo bajo prueba. Opus diluye el
embedding con mil tokens de prosa y `luna` no, así que el mismo artefacto contra
el mismo tema recibe cosenos distintos según el modelo. Eso invalida la
comparación de curvas entre modelos, que es el eje declarado del spec §9.
Además el spec §6 exige prefijo compartido y el código regeneraba uno por celda.

**Decisión.** El prefijo se genera **una vez por (tema, longitud)**, con el
usuario simulado y un **modelo de asistente fijo** (`PREFIX_MODEL =
gpt-5.6-terra-tst`, el mismo que hace de usuario), se persiste en
`runs/prefixes/<prefix_id>.json` y **se reproduce idéntico a todos los modelos
evaluados**.

- `prefix_id = sha256(topic_id + n_turns + prefix_model + serialización)[:16]`
- Todos los modelos ven exactamente el mismo contexto antes del pegote.
- Las réplicas comparten prefijo **y** artefacto: varían solo el muestreo de la
  respuesta, que es lo que las réplicas deben medir.

**Coste declarado de la decisión.** El modelo evaluado no está reaccionando a sus
propias palabras anteriores, sino a las de otro. Es menos natural. Se acepta a
cambio de que el eje x sea idéntico entre modelos, que es la única forma de que
las curvas sean comparables. **Se escribe en el artículo como limitación**, no se
esconde.

## D2. La similaridad se mide sobre el lado del usuario

**Problema.** Embeber la conversación entera (a) se pasa del límite de 8.191
tokens del embedder en el brazo de 10 turnos, con truncado silencioso del final,
y (b) mezcla texto del modelo evaluado.

**Decisión.** La similaridad **primaria** se mide contra la concatenación de los
**turnos de usuario** (apertura + turnos del usuario simulado). Es corta, es
independiente del modelo evaluado y es la definición correcta de "de qué va esta
conversación" para un pegado accidental.

Se registran **las dos**: `similarity_user` (primaria, la que estratifica) y
`similarity_full` (secundaria, sobre la conversación entera). Si divergen, el
análisis lo verá.

Guarda de longitud obligatoria: antes de embeber, si el texto supera 6.000
tokens estimados (≈24.000 caracteres), se recorta **por el principio**
conservando el final, y se registra `similarity_text_truncated: true`.

## D3. Rotación de ejes: se acabó la confusión

**Problema.** `LENGTHS[i % 2]` sobre el índice del tema y `stratum = i % STRATA`
sobre el índice global hacían estrato ≡ tema ≡ longitud.

**Decisión.** En `plan_phase0`, con `t` = índice de tema (0-7) y `m` = índice de
modelo (0-2):

```
stratum  = (t + 3 * m) % 8
n_turns  = LENGTHS[(t + m) % 2]
```

Cada estrato cae en tres temas distintos y cada tema aparece en ambas longitudes.
`stratum` va **en el dict del plan**, no se deriva del orden de iteración.

**Orden de ejecución**: round-robin de modelos dentro de cada tema, no
modelo-mayor. Con ~2 h de tirada contra un gateway compartido, el orden
modelo-mayor confunde el modelo con la hora de reloj.

## D4. Cobertura de `kind` garantizada

**Problema.** El muestreo era solo por estrato; el género del artefacto salía a
suerte. Con 24 celdas y 11 kinds, la rúbrica podía derivarse sin ver nunca un
`prompt` pegado — y los cinco artefactos `prompt` son el caso donde el pegote es
literalmente una instrucción ejecutable. **Ejecutarla es una sexta conducta que
no está en las cinco categorías del spec §5**, y es donde el experimento roza el
encuadre de prompt injection que el §2 dice explícitamente que no es.

**Decisión.** Dentro del estrato asignado, se elige el artefacto cuyo `kind` esté
**menos representado** hasta ese momento en la tirada. Test: los 11 kinds
aparecen al menos una vez en las 24 celdas.

## D5. Identidad y cabecera de tirada

Primera línea de cada JSONL, `{"kind": "run_header", ...}`:
`run_id`, `phase`, `plan_path`, `spec_path`, `code_sha`, `bank_sha`,
`topics_sha`, `master_seed`, `roster`, `planned_cells`, `embedding_model`,
`prefix_model`, `user_model`, `user_system_prompt`, `started_at`.

En cada `ConversationRecord`, además de lo que ya tenía:
`schema_version`, `run_id`, `conversation_id` (determinista y legible:
`p0-{model}-{topic}-{n_turns}-r{replicate}`), `cell_index`, `replicate_idx`,
`prefix_id`, `stratum`, `n_strata`, `similarity_user`, `similarity_full`,
`similarity_rank`, `similarity_pct`, `ranking` (los 64 pares
`{artifact_id, similarity}`), `artifact_text`, `model_label`, `request_params`,
`system_prompt`, `response_model` (el que devuelve el proveedor),
`stop_reasons` por turno, `started_at`, `ended_at`, `latency_ms`,
`status`, `condition`, `arm`, `parent_id`, `paste_index`, `post_indices`.

Cada mensaje del transcript lleva `tag`:
`opening | user_sim | paste | repair | assistant | post`.

`started_at` se pasa como argumento desde fuera o se toma con `time.time()` en el
runner (no en el workflow, donde `Date.now()` está prohibido).

## D6. Fallos como datos, no como caída

**Problema.** `raise_for_status()` sin reintento y sin `try` por celda: un 429 o
un filtro de contenido aborta la tirada y deja un JSONL truncado indistinguible
de uno completo. El sesgo es predecible: fallan más las conversaciones largas y
los pegotes de coseno alto, justo la zona interesante.

**Decisión.**
- `chat()` reintenta 429 y 5xx con backoff exponencial (3 intentos), y devuelve
  `Reply` con `stop_reason` y `response_model`.
- `main()` envuelve cada celda en `try/except` y **siempre** escribe una fila, con
  `status` ∈ `ok | http_error | timeout | refusal | empty`, más `error_code`,
  `error_body` y `attempts`.
- `main()` es idempotente: lee los `conversation_id` ya presentes en el fichero de
  salida indicado y los salta.
- Al terminar imprime y registra: celdas planificadas, completadas y fallidas.

**Que un modelo se niegue a responder al pegote es un resultado**, no un error.

## D7. La Fase 0 continúa dos turnos después del pegote

**Problema.** La rúbrica se derivaba observando un único turno posterior al
pegote, y "pivota en silencio" frente a "puente confabulado" a menudo solo se
separa en el turno +1. Además la segunda métrica de la Fase 2 (reaparición de
entidades en +1..+3) no se pilotaba nunca antes de comprometer el grueso del
presupuesto.

**Decisión.** Tras la reacción, dos turnos más con el usuario simulado **sin
reparación** (variante (a) del spec §7), etiquetados `post`. Sobre esas 24
conversaciones se corre ya el recuento de entidades y se reporta en la Task 8.
Coste: ~20 % más sobre una tirada de 4 $.

## D8. Casado de entidades, especificado y probado

**Problema.** Toda la métrica automática de fuga se apoya en las `entities`
escritas a mano y no había ni función ni especificación de casado.

**Decisión.** `entity_hits(text, entities) -> list[str]` en `artifacts.py`:
comparación sobre texto normalizado (minúsculas, sin acentos, espacios
colapsados), coincidencia de subcadena con fronteras de palabra. Con tests.

Paso nuevo en la Task 8: correr `entity_hits` sobre los prefijos **pre-pegote** de
las 24 conversaciones. **Toda entity que aparezca ahí es ruido de base** y hay que
sustituirla en el banco antes de la Fase 2. Sospechosas conocidas: `45 minutos`,
`12 horas de fermentación en frío`.

## D9. Parámetros de muestreo explícitos, y Sonnet con thinking

**Problema.** Ninguno de los tres cuerpos mandaba `temperature`; se delegaba en
defaults distintos por proveedor que pueden cambiar sin avisar. Y `_anthropic_body`
no manda `thinking`, así que **Sonnet 5 correría sin razonamiento mientras Opus 5
lo lleva por defecto**: los dos Claude no serían comparables.

**Decisión.** `temperature=1.0` explícito en los tres cuerpos.
`thinking: {"type": "adaptive"}` para los modelos Claude. `request_params` (el
cuerpo enviado sin `messages`) va en cada fila.

**Ojo:** `budget_tokens` devuelve 400 en Opus 5 y Sonnet 5. Dos auditores
propusieron usarlo; aplicar su sugerencia tumbaría la tirada.

## D10. Caché: medir lo correcto y declarar el breakpoint

**Problema.** El chequeo de la Task 8 mezclaba lecturas de caché dentro de
conversación con las de entre celdas, así que habría salido en verde validando
algo que no es el ahorro de la Fase 1. Y `_anthropic_body` no emite
`cache_control`, así que Claude leería cero **siempre** — y el plan instruía a
buscar durante horas un invalidador que no existe.

**Decisión.** `cache_control: {"type": "ephemeral"}` en el último bloque del
prefijo para Claude. El chequeo se reescribe con criterio explícito: *dos celdas
con el mismo `prefix_id` deben mostrar `cache_read > 0` en la llamada del pegote*,
desglosado por proveedor.

## D11. Brazo de control sin pegote

`artifact_id`, `artifact_kind`, `artifact_entities` y `similarity_*` pasan a ser
opcionales (`| None`) y se añade `condition: "paste" | "no_paste"`. Tres celdas de
control sin pegote en la Fase 0 (céntimos) para demostrar que el formato, el
runner y el verificador lo soportan. El valor real es de Fase 2: sin tasa base,
un recuento de fuga no se interpreta.

## D12. Medir el ancho del eje antes de gastar

Paso nuevo **antes** de la tirada: embeber los 64 artefactos y los 8 prefijos
(una llamada, céntimos) e imprimir min/mediana/máx de coseno por tema.

Si algún tema tiene rango < 0,15 o cola alta vacía, se completa el banco con
artefactos de portapapeles plausibles que rocen ese dominio **sin estar escritos
como distractores**. Comprobado: `viaje-japon`, `elegir-camara` y `mudanza` no
tienen hoy ningún artefacto del dominio.

El ancho de rango observado entra como **criterio explícito del GO/NO-GO**.

## D13. `Topic` con hueco para la tarea verificable

`Topic` gana `task`, `expected` y `verifier` (a `None` en Fase 0). Que el campo no
exista rompería el enganche con la Fase 2, que exige temas con tarea verificable
aguas abajo; y si la Fase 2 corre sobre temas nuevos, deja de estar pareada con la
Fase 1 y la rúbrica se habrá derivado leyendo temas que no vuelven a aparecer.

## D14. Anotaciones manuales con formato

`runs/phase0/annotations-<run_id>.jsonl`, con
`{conversation_id, annotator, category_guess, quote, notes}`. Es el único conjunto
etiquetado a mano que va a existir y el que semilla el acuerdo juez-humano del
spec §6. Va al commit.

## D15. Limitación que se documenta, no se arregla

**Colinealidad registro↔similaridad.** Los 8 temas son domésticos y 26 de los 64
artefactos son de registro técnico (8 stacktrace, 5 sql, 5 config, 5 changelog)
más 5 `prompt`. Esos caerán sistemáticamente en los estratos bajos para todos los
temas. "Similaridad semántica" y "cambio de registro" son **colineales por
construcción**.

Un modelo que señala un stacktrace en una charla sobre pan puede estar
reaccionando al registro, no a la distancia semántica. No se puede eliminar sin
rehacer el banco; se **mide** (registrando `artifact_kind` en cada fila, que ya se
hace) y se **declara en el artículo** como límite de la interpretación. Es la
forma concreta del riesgo que el spec §12 ya anticipaba.

## D16. Incoherencia del spec: 7 frente a 9 modelos

El §6 presupuesta 2.688 = 384 × 7 modelos; el §9 lista nueve verificados; el
prerrequisito del juez propone sacar a `claude-sonnet-5` del plantel. **Se
resuelve al planificar la Fase 1**, no ahora. Queda anotado aquí para que no se
pierda.

## D17. Repo público

`runs/` se versiona en un repo público y cada fila lleva alias internos
(`gpt-5.6-sol-tst`), y `config.py` versiona el endpoint del gateway y el proyecto
GCP. No es secreto, pero es material de trabajo interno
(`feedback_anonymise_work_material`). Se añade `model_label` (ya existe en
`Model.label` y nunca llegaba al JSONL) junto a `model_id`, y **antes de la
primera tirada** se decide si endpoint y proyecto van a variables de entorno.

---

## Errores de los auditores, para que no se reintroduzcan

- `budget_tokens` **no** se puede usar: devuelve 400 en Opus 5 y Sonnet 5.
- El modo `"w"` del fichero de salida **no** pisa nada: el nombre lleva
  timestamp. El problema real es el fichero parcial sin marcar.
- La Fase 0 **no** usa `stratified_pick`; `main()` inlinea su propia lógica.
  El fichero a tocar es `run_phase0.py`, no `similarity.py`.
- El brazo de control **no** hace falta para juzgar si el usuario simulado suena
  a persona: el prefijo pre-pegote de cada conversación ya es exactamente eso.
  La mitad válida del hallazgo es la tasa base de entidades (D11).
