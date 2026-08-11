# Cross-session messaging: ¿canal o estructura?

**Fecha:** 2026-08-11
**Estado:** diseño aprobado, pendiente de ejecución
**Artículo predecesor:** [Coding Agents and Teamwork: Social Skills, or Structure?](../../../src/content/blog/en/coding-agents-structure.md) (2026-07-12)
**Ejecución:** portátil secundario (única máquina con la feature disponible)

---

## 1. Motivación y tesis

Claude Code ha anunciado que las sesiones pueden mensajearse entre sí: una sesión envía un
**resumen** (no el historial, no los ficheros) y la otra lo recoge a mitad de tarea.

El artículo previo de este blog ya midió algo muy cercano, y su resultado hace de prior fuerte:

- CooperBench da a los agentes **un canal de mensajes desde el minuto cero**.
- La condición C1 (obligar a un handshake antes de tocar código) **nunca llegó a dispararse**:
  los agentes ya se hablaban solos, primer mensaje en el turno 2, primera edición en el turno 6.
- Conclusión textual: *"el problema no es si intercambian información, sino qué hacen con ella"*.
- El fallo más nítido documentado fue de **follow-through**: el agente 2 leyó la petición, escribió
  en su razonamiento privado "debería coordinarme", y nunca respondió ni hizo la línea que le
  tocaba. Con la fontanería del canal verificada como inocente.
- La palanca que sí recuperó rendimiento fue **que un agente sea dueño de la integración final**
  (secuenciación C3, integrador C4). No el canal.

Por tanto la feature nueva envía exactamente lo que el experimento anterior mostró que **no** era el
cuello de botella. Una pieza que celebre el canal se contradice con datos ya publicados aquí.

### 1.1 Las tres cosas que sí son nuevas

1. **La entrega interrumpe.** El canal de CooperBench era buzón: el mensaje entra al contexto y el
   agente decide. Aquí el mensaje llega **a mitad de tarea**. Eso ataca directamente el fallo de
   follow-through. Hipótesis con mecanismo plausible y prior fuerte — el mejor tipo de experimento.
2. **El payload es un resumen redactado por el modelo emisor.** Compresión con pérdida entre dos
   contextos que han divergido. El canal anterior pasaba mensajes, no resúmenes de historial.
3. **No hay lead.** La coordinación es entre pares. Nadie posee el estado integrado final — que es
   justo la única palanca fiable del artículo anterior.

### 1.2 La observación del autor, y por qué hay que someterla a prueba

Impresión tras usarlo en sesiones reales de hasta 4 simultáneas: *los agentes se avisan, detectan
colisiones, se esperan para no chocar, y de forma natural se formaban secuencias donde cada uno
mergeaba con el que se topaba*. Efectivo, degradando con N.

Eso es la **capa sintáctica**. El artículo anterior demostró que ahí no se gana la tarea: la
propiedad forzada llevó los conflictos de merge a 0/19 en ambos tiers y **no compró aprobados**;
los conflictos estaban *tapando* fallos semánticos. Que las sesiones no colisionen es visible y
satisfactorio, y puede ser irrelevante.

La pieza debe abrir declarando esta impresión y luego someterla a prueba. Es el movimiento
retórico más fuerte disponible y cumple la regla de no recomendar más fuerte que los datos.

### 1.3 El merge emergente: una condición que nunca se ha probado

Lo observado —*secuencias que se forman solas, cada uno mergea con el que se topa*— no es C3
(secuenciación impuesta) ni C4 (integrador dedicado). Es **propiedad de integración transitoria y
negociada por colisión**: un dueño distinto por cada choque, nadie con la vista del estado final.

Hay precedente incómodo en los propios datos: el modo `team` de CooperBench (lead responsable de
integrar) sacó **0% en ambos tiers, por debajo de coop libre**, porque el hand-off manual resultó
más frágil que dejar mergear a la herramienta. Más estructura de coordinación, más sitios donde
fumarla. El merge distribuido tiene la misma silueta: muchos hand-offs pequeños.

**Pregunta central de la capa 3:** ¿el merge distribuido por colisión da el beneficio del
integrador, o es otra vez la ilusión de la capa sintáctica?

---

## 2. Restricciones de ejecución

Estas restricciones son vinculantes y el protocolo debe respetarlas.

- **La feature solo existe en el portátil secundario, con otra cuenta.** El diseño se cierra aquí;
  la ejecución ocurre allí. El protocolo debe ser **mecánico**: scripts y pasos, sin depender de
  criterio en caliente.
- **El envío lo inicia el agente, no se puede disparar deterministamente por script.** Consecuencia
  de diseño en §4.2 (replay).
- **La máquina principal se satura y mata procesos.** N=8 sesiones simultáneas queda fuera del
  diseño: no es un parámetro, es un apagón. Techo en N=4, suites en serie.
- **Presupuesto degradable.** Las capas se ejecutan en orden 0 → 1+2 → 3. Las capas 0+1+2 son una
  pieza publicable completa por sí solas. La capa 3 se puede abandonar sin dejar agujero
  argumental.

---

## 3. Capa 0 — Minado del corpus existente (primero, y barato)

Ya existen sesiones reales en el portátil secundario con hasta 4 sesiones simultáneas usando el
canal. Se minan **antes** de gastar máquina en nada más.

### 3.1 Qué produce

- **Tasas base.** Cuántas peticiones con forma de delegación (A necesita que B haga algo y depende
  del resultado) aparecen por sesión y por hora de trabajo. Si son raras, la feature casi nunca es
  portante — y eso es un hallazgo, no un relleno.
- **Taxonomía observacional** (§4.3) aplicada a peticiones reales: cumplido / silencio / acuse sin
  acción / acción incorrecta / deriva.
- **Morfología del merge emergente:** cómo se formaron las secuencias, quién mergeó con quién,
  cuántos hand-offs hubo, si alguien acabó teniendo vista del estado integrado.
- **Catálogo de escenarios** que alimenta el repo semilla de las capas 1–3: los bloqueos reales
  observados son los que se reproducen, no bloqueos inventados.

### 3.2 Qué NO produce, y por qué no basta

1. **No hay brazo de control.** No existe la corrida de las mismas tareas sin canal. La pregunta
   "¿ayudó el canal?" no tiene contrafactual. El estándar metodológico del artículo anterior era
   comparación pareada (McNemar por tarea y semilla); un corpus observacional no lo produce.
2. **No hay replay.** El brazo de buzón nunca existió; interrupción-vs-buzón no es recuperable.
3. **El humano está dentro del bucle.** Esas sesiones se corrieron para sacar trabajo, con
   intervenciones cuando algo se torcía. No separa efecto-del-canal de efecto-del-humano.
4. **La impresión ya está formada.** Sin predicción registrada de antemano, el análisis vale como
   generación de hipótesis, no como evidencia.
5. **Falta verdad de terreno semántica**, salvo que los repos tengan suite por ticket y se sepa
   cuáles pasaron.

### 3.3 Precedente

Es el mismo movimiento que en la pieza anterior con las 1.806 trayectorias minadas para la pregunta
restart-vs-iterate: el corpus se minó, dio cero, y se reportó honestamente que el cero era artefacto
del montaje y no hallazgo. Aquí igual: **el corpus fija la pregunta, el experimento la contesta.**

### 3.4 Pre-flight técnico

Antes de nada, verificar en el portátil secundario:

- **Las sesiones a minar ocurrieron en `Documents/repos/conversational-ai`.** Claude Code guarda los
  transcripts bajo `~/.claude/projects/<ruta-slugificada>/*.jsonl`, así que el directorio a abrir es
  el slug de esa ruta. Confirmar que existe y qué rango de fechas cubre.
- Si los mensajes entre sesiones aparecen en esos transcripts con emisor, receptor y timestamp, o
  solo se ve el lado que recibe.
- Retención: cuántas de las sesiones de hasta 4 simultáneas siguen disponibles.
- Cómo se direcciona una sesión a otra (nombre, id, registro) — necesario para el protocolo de las
  capas 1–3.

---

## 4. Capa 1 — Núcleo: follow-through, interrupción vs buzón

### 4.1 Unidad de medida

Una **petición que obliga a la otra sesión a actuar en tu nombre**: la forma exacta del mensaje que
recibió silencio en el artículo anterior ("estoy bloqueado en la región que posees, añade tú la
línea de export").

Repo semilla en el que la sesión A queda **estructuralmente bloqueada** y necesita de B una acción
pequeña, inequívoca y **verificable por script** (existe la línea / pasa el test). Cero juicio
humano en el scoring.

Los escenarios de bloqueo salen del catálogo de la capa 0, no de la imaginación.

### 4.2 Brazos, y el problema del envío agéntico

Como el envío lo decide A, los brazos no comparan solo el mecanismo de entrega: comparan también dos
textos distintos. Confundido. Solución: **replay**.

| Brazo | Procedimiento |
|---|---|
| **Interrupción** | A usa el canal nuevo. Se captura el texto exacto que A envió. |
| **Buzón** | Se inyecta *ese mismo texto capturado* en un fichero que B tiene instrucción de consultar. Replica la entrega de CooperBench. |
| **Sin canal** | A bloqueada, sin forma de pedir. Línea base: ¿se hace la tarea igual? |

El replay deja los brazos **pareados por construcción** (mismo mensaje, entrega distinta) y es más
barato que generar dos mensajes. Consecuencia operativa: dentro de un escenario los brazos son
**secuenciales**, no paralelos — buzón depende del texto capturado en interrupción. Encaja con el
límite de concurrencia de la máquina.

Que A componga el mensaje deja de ser un obstáculo: convierte la primera arista de §5 en una
variable real y medida en vez de un artefacto del montaje.

### 4.3 Taxonomía de resultado

El resultado no es binario. Se puntúa con la taxonomía derivada del artículo anterior:

| Categoría | Definición |
|---|---|
| Cumplido | B ejecutó la acción pedida |
| Silencio | B nunca acusó recibo |
| **Acuse sin acción** | B respondió que sí y no lo hizo ← el fallo documentado |
| Acción incorrecta | B hizo algo, pero no lo pedido |
| Deriva | B lo hizo y rompió su propia tarea |

### 4.4 Métrica en dirección contraria: el coste de interrumpir

Obligatoria. Si el mensaje entra a mitad de edición, ¿B lo atiende y pierde el hilo de lo suyo? La
interrupción puede arreglar el follow-through y pagarlo en coherencia. Medir solo lo primero sería
vender en vez de medir.

Instrumentos: turnos de B entre recepción y acción; si B retoma su propia tarea al nivel donde
estaba; si la suite propia de B se degrada respecto al brazo sin canal.

### 4.5 Réplicas

Tres semillas por celda. Es el estándar ya establecido en el artículo anterior, y existe
precisamente para cazar el tipo de sobre-afirmación que allí ya se cazó (el 42% de
territorio+integrador que se desplomó a 33% [21–42] con dos semillas más).

---

## 5. Capa 2 — Instrumento: qué sobrevive al resumen

**No va al lado de la capa 1: va dentro.** Antes de puntuar si B actuó, se captura qué recibió y qué
entendió.

### 5.1 La cadena de cuatro nodos

```
intención de A  →  texto que A decide enviar  →  lo que B entiende  →  lo que B hace
```

Tres aristas, tres sitios donde perder. Se miden las tres:

1. **Compresión de A.** La intención existe y es conocida: A está bloqueada por una causa concreta y
   necesita una acción concreta, definida por el escenario. Se compara la lista de elementos de la
   intención (fichero, símbolo exacto, restricción, motivo, orden requerido) contra los que
   aparecen en el texto que A envió.
2. **Recepción de B.** Tras la entrega, se sondea a B pidiéndole que reformule lo que le han pedido,
   antes de dejarle actuar. Se puntúa qué elementos sobrevivieron. El sondeo lo escribe el operador
   directamente en la sesión de B (el envío entre sesiones no es disparable por script, pero
   escribir en una sesión sí), con un texto fijo idéntico en todos los brazos.
3. **Acción de B.** La taxonomía de §4.3.

### 5.2 Por qué esto importa

Separa dos fallos que el artículo anterior **no podía** separar: *no se enteró* vs *se enteró y no
actuó*. Allí la fontanería se verificó a mano, caso por caso, para declararla inocente. Aquí queda
instrumentada y automática. Es una mejora metodológica sobre la propia pieza previa, y conviene
decirlo en el artículo.

---

## 6. Capa 3 — Validación externa: la épica (desechable)

Repo semilla, 4 tickets, **colisiones registradas antes de correr**. N=2 y N=4. N=8 fuera.

### 6.1 Brazos

| Brazo | Descripción |
|---|---|
| **Aislado** | Sin canal, merge al final. Control. |
| **Emergente** | Con canal, comportamiento natural. Lo que el autor ya hace: secuencias espontáneas, merge por colisión. |
| **Integrador impuesto** | Con canal, más una sesión dueña del estado integrado final. La palanca conocida del artículo anterior. |

### 6.2 Métricas: dos columnas que nunca se mezclan

- **Sintáctica:** conflictos de merge, colisiones de fichero, esperas, mensajes de aviso.
- **Semántica:** suite por ticket + **suite integrada**. El aprobado exige ambas, igual que el
  criterio de CooperBench exigía que pasaran las dos features.

### 6.3 Predicción registrada (antes de correr)

> El canal hunde la columna sintáctica y **no mueve** la semántica. El merge emergente se parecerá
> más a aislado que a integrador impuesto en la columna semántica, porque nadie llega a poseer el
> estado integrado final.

Publicar la predicción antes del resultado es lo que convierte una confirmación aburrida en un
artículo. Si sale al revés, mejor artículo todavía.

### 6.4 Condición de abandono

Si el presupuesto de máquina se agota, esta capa se abandona. Capas 0+1+2 quedan como pieza
completa. Se declara explícitamente en el artículo qué no se llegó a medir — sin truncado
silencioso.

---

## 7. Estructura del artículo

1. **La impresión.** Declarar la experiencia positiva con hasta 4 sesiones: se avisan, se esperan,
   no chocan. Sin ironía.
2. **El prior incómodo.** Mi propio experimento de julio dice que el canal no era el problema, y que
   la capa donde estoy viendo mejoras es la que ya demostré que no compra aprobados.
3. **Lo que sí es nuevo.** Interrupción vs buzón; resumen con pérdida; ausencia de lead.
4. **Tasas base** (capa 0): con qué frecuencia esto es siquiera portante en trabajo real.
5. **Predicciones registradas.**
6. **Resultados** por capa, con la cadena de cuatro nodos como hilo.
7. **El coste de interrumpir** — la métrica que va en contra.
8. **Qué dice y qué no dice.** Cobertura vs confianza, igual que en la pieza anterior.

### 7.1 Reglas de honestidad heredadas

- Ninguna recomendación más fuerte que los datos que la sostienen.
- Rangos [min–max] sobre semillas, no números sueltos.
- Auditoría adversarial del propio harness antes de publicar cifras. En la pieza anterior dos
  condiciones puntuaron un 0% falso por bugs de composición del eval; la fontanería de scoring
  merece tanto test como las condiciones.
- Declarar explícitamente el techo: cobertura, no confianza.

---

## 8. Riesgos

| Riesgo | Mitigación |
|---|---|
| Las tasas base de la capa 0 salen ridículas: la feature casi nunca es portante | Es un hallazgo publicable. Reencuadra la pieza hacia "cuándo importa esto siquiera" y ahorra las capas 2–3. |
| El envío agéntico no ocurre cuando el escenario lo requiere (A no pide ayuda) | Es un dato, no un fallo: "A ni siquiera pidió" entra en la taxonomía como categoría cero. |
| La capa 3 se come el presupuesto y queda a medias | Orden de ejecución 0 → 1+2 → 3; condición de abandono en §6.4. |
| Los transcripts de las sesiones antiguas ya no existen | Pre-flight §3.4 antes de comprometer el diseño de la capa 0. |
| El scoring de "fallo semántico" requiere juicio | Suite por ticket + suite integrada, definidas en el repo semilla antes de correr. |

---

## 9. Alcance excluido

- N=8 sesiones o más.
- Comparación con otros productos (Cursor, Codex, agentes multi-proceso ajenos).
- Reejecución del benchmark CooperBench completo.
- Cualquier afirmación sobre coste en dólares salvo que se instrumente explícitamente.
