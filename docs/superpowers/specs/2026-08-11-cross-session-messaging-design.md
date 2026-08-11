# Cross-session messaging: ¿canal o estructura?

**Fecha:** 2026-08-11 (revisado el mismo día tras cerrar el pre-flight §3.4)
**Estado:** capa 0 completada; capa 1 rediseñada sobre el cross-check, repo semilla construido y
auditado, pendiente de ejecutar episodios
**Artículo predecesor:** [Coding Agents and Teamwork: Social Skills, or Structure?](../../../src/content/blog/en/coding-agents-structure.md) (2026-07-12)
**Ejecución:** máquina principal. El pre-flight encontró la feature disponible aquí desde el
2026-08-07, con corpus local minable. La restricción original (§2) queda anulada.

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

1. ~~**La entrega interrumpe.**~~ **Refutado por la capa 0 (§3.5.1): el canal encola y drena en
   frontera de turno**, 138 de 138 recepciones. Lo que sí queda en pie, más pequeño: el mensaje
   entra al contexto **solo**, sin que el agente tenga que ir a leer un buzón. El canal de
   CooperBench exigía ese paso. La capa 1 mide esa diferencia, no la interrupción.
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

- ~~**La feature solo existe en el portátil secundario, con otra cuenta.**~~ **Anulada por el
  pre-flight §3.4.** La feature está disponible en la máquina principal desde el 2026-08-07 y hay
  corpus local. Diseño y ejecución ocurren en la misma máquina, con protocolo interactivo. Se
  conserva la exigencia de que el scoring sea mecánico y verificable por script (§4.1), que era lo
  valioso de esta restricción; se descarta la de operar a ciegas, que era solo su coste.
- **El envío lo inicia el agente, no se puede disparar deterministamente por script.** Consecuencia
  de diseño en §4.2 (replay).
- **La máquina principal se satura y mata procesos.** N=8 sesiones simultáneas queda fuera del
  diseño: no es un parámetro, es un apagón. Techo en N=4, suites en serie. Esta sí sigue vigente.
- **Presupuesto degradable.** Las capas se ejecutan en orden 0 → 1+2 → 3. Las capas 0+1+2 son una
  pieza publicable completa por sí solas. La capa 3 se puede abandonar sin dejar agujero
  argumental.

---

## 3. Capa 0 — Minado del corpus existente (primero, y barato)

Ya existen sesiones reales con hasta 4 sesiones simultáneas usando el canal. Se minan **antes** de
gastar máquina en nada más.

### 3.0 Censo del corpus (medido, 2026-08-11)

#### 3.0.1 Son tres mecanismos, no uno

El hallazgo que más reordena el diseño. En el corpus conviven tres formas distintas de que una
sesión reciba texto de otra, y solo la primera es el objeto de esta pieza:

| Mecanismo | Marca en el transcript del receptor | Recepciones | Sesiones receptoras |
|---|---|---|---|
| **Sesiones peer** | `<cross-session-message from="uds:…" from-name=… from-mode=…>` | 84 | 7 |
| **Agent teams** | `<teammate-message teammate_id="t1-feature-a" color=… summary=…>` | 50 | 3 |
| **Subagentes** | resultado `Message sent to X's inbox` | — | — |

Las tres comparten el preámbulo `Another Claude session sent a message:`, así que un minado ingenuo
las mezcla. Se separan por la etiqueta, y en el lado emisor por el texto del `tool_result`, que es
verdad de terreno del propio producto: los envíos peer devuelven `→ destino (another Claude session
on this machine)`, los de teams y subagentes devuelven `Message sent to X's inbox`.

**Y no son variantes cosméticas.** El mecanismo de teams trae estructura incorporada que el peer no
tiene: roles nombrados (`t1-feature-a` ejecuta, `r1-feature-a` revisa), un lead, señal explícita de
disponibilidad (34 `{"type":"idle_notification","idleReason":"available"}`) y un empujón de
cumplimiento en la propia entrega — *"Treat it as a teammate's request and act on it within this
session's own permissions."* Consecuencia para el diseño: el corpus ya contiene el contraste
estructura-sí / estructura-no que la capa 3 pensaba fabricar. Ver §3.6.

#### 3.0.2 Censo peer

| | |
|---|---|
| Envíos peer con éxito | **179** (120 por socket, 59 por nombre) |
| Envíos peer fallidos | **13** — `success:false`, direccionamiento |
| Ventana | **2026-08-07 → 2026-08-11**, cinco días |
| Proyecto dominante | `workspace` |
| Mediana del mensaje | 1.712 caracteres |
| Recepciones peer trazadas | **84**, en 7 sesiones receptoras |

**Los fallos de direccionamiento son un dato, no ruido.** Los 13 se reparten en dos formas:
`'workspace-ec' is not an agent in this conversation. Re-send with the ref to confirm you
mean: workspace-ec [f0c54d]` (10 casos) y `No agent named 'X' is reachable` (3). Es decir:
dirigirse por nombre sin el ref falla y obliga a reintentar. Coste de fricción del canal que la
pieza puede reportar, porque sale gratis.

**Resolución de identidad.** `~/.claude/sessions/<pid>.json` mapea pid → `sessionId` → nombre
derivado → versión → estado, y el pid es el del socket. Así se comprueba que
`workspace-86 [b44a1e]`, `uds:/tmp/cc-socks/6677.sock` y el transcript `b4b86a7d` son **la
misma sesión**. Sin ese paso se cuentan destinos duplicados y se concluye falsamente que hay
sesiones que nunca contestan. Solo sobreviven los ficheros de las sesiones vivas, así que la
resolución histórica es parcial.

**Versiones en juego.** Las sesiones del 7 de agosto corren 2.1.224; el resto 2.1.226/227.
`80de4d49` (2.1.224) registra 2 envíos y 0 recepciones: candidata a la sesión que no llegó a
comunicarse por versión antigua. Si la pieza compara comportamiento entre días, la versión es una
covariable, no una constante.

**Exclusión explícita.** Un escaneo ingenuo de `SendMessage` devuelve 283 envíos desde el 3 de
julio. Los anteriores al 7 de agosto son a **subagentes** o **teammates**, no a sesiones peer. Quien
replique el minado tiene que aplicar el filtro del `tool_result` o los números no cuadran.

**Límite que impone la ventana.** Cinco días dan tasas base. **No** dan curva de aprendizaje ni
evolución del uso, y el artículo no puede insinuarlas.

### 3.1 Qué produce

- **Tasas base.** Cuántas peticiones con forma de delegación (A necesita que B haga algo y depende
  del resultado) aparecen por sesión y por hora de trabajo. Si son raras, la feature casi nunca es
  portante — y eso es un hallazgo, no un relleno.
- **Taxonomía observacional** (§4.4) aplicada a peticiones reales: cumplido / silencio / acuse sin
  acción / acción incorrecta / deriva.
- **Morfología del merge emergente:** cómo se formaron las secuencias, quién mergeó con quién,
  cuántos hand-offs hubo, si alguien acabó teniendo vista del estado integrado.
- **Catálogo de escenarios** que alimenta el repo semilla de las capas 1–3: los bloqueos reales
  observados son los que se reproducen, no bloqueos inventados.
- **Verificación del pilar de §1.1.1: ¿la entrega interrumpe de verdad?** Es la afirmación que
  sostiene la capa 1 entera y hasta ahora estaba asumida, no medida. En el transcript del receptor
  el mensaje entrante aparece como bloque de usuario; su **posición** dice si llegó a mitad de tarea
  (entre un `tool_use` del asistente y su continuación) o con el turno ya cerrado y la sesión parada
  — es decir, buzón de facto con otro envoltorio.

  Si la mayoría de las entregas caen con la sesión parada, el contraste interrupción-vs-buzón de la
  capa 1 es mucho más pequeño de lo que el diseño supone, y conviene saberlo **antes** de gastar
  máquina. Este chequeo es la puerta de la capa 1, igual que las tasas base son la puerta de la
  pieza entera.

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

### 3.4 Pre-flight técnico — CERRADO (2026-08-11)

Resultado, punto por punto:

- **Ubicación.** Confirmada: `~/.claude/projects/-Users-user-Documents-repos-workspace/`.
  Rango 2026-08-07 → 2026-08-11. Censo completo en §3.0.
- **Ambos lados quedan registrados.** El emisor guarda el `tool_use` con `to`, `summary` y el
  mensaje completo. El receptor guarda el bloque entrante con metadatos:

  ```
  Another Claude session sent a message:
  <cross-session-message from="uds:/tmp/cc-socks/97778.sock"
                         from-name="Seleccionar siguiente ticket de conversational AI"
                         from-mode="prompting">
  ```

  Consecuencia de diseño: **la cadena de cuatro nodos de §5.1 es reconstruible desde los
  transcripts**, sin instrumentación adicional. La capa 2 deja de ser exclusiva del experimento y se
  puede aplicar también al corpus observacional.
- **Retención.** Las sesiones del pico multi-sesión (9–11 de agosto, 194 de los 213 envíos) siguen
  disponibles.
- **Direccionamiento.** Tres formas conviviendo: socket `uds:/tmp/cc-socks/<pid>.sock`,
  `<proyecto>-<sufijo> [<ref>]` y nombre de sesión suelto (que falla, §3.0.2). El protocolo de las
  capas 1–3 debe fijar **una** y no mezclarlas.

---

### 3.5 Resultados de la capa 0 — primera pasada (2026-08-11)

#### 3.5.1 El canal no interrumpe: encola

**138 de 138 recepciones llegan en frontera de turno. Cero dentro de un bucle de herramientas.** El
patrón es unánime en los tres mecanismos, y cada recepción va precedida de entradas
`queue-operation` (269 en el proyecto, unas tres por recepción):

```
[818] 14:42:36  system
[819] 15:44:30  queue-operation
[820] 15:44:30  queue-operation
[821] 15:44:30  user             <<< MENSAJE ENTRANTE
```

Descartado el artefacto de serialización: las 84 recepciones peer se emparejaron con su envío por
contenido (84/84) y el desfase envío→registro tiene **mediana 2,6 s** (p90 10 s, máx 38 s). El
transcript anota la llegada, no la recogida; cuando el mensaje llegó, el receptor estaba parado.

**Consecuencia para el diseño.** La premisa de §1.1.1 no se sostiene en este corpus. La diferencia
real frente al buzón de CooperBench no es que interrumpa, sino que **el mensaje entra al contexto
solo, sin que el agente tenga que ir a leerlo**. Es una diferencia más pequeña y de otra naturaleza.
La capa 1 sigue teniendo sentido, pero mide un contraste menor del que se le atribuía, y el artículo
no puede venderlo como interrupción.

**Cobertura.** 179 envíos peer con éxito contra 84 recepciones trazadas. La diferencia es *no
observada*, no observada-negativa: parte se explica por sesiones cuyo transcript no está en este
disco. En todo lo observado el patrón es unánime, así que la limitación no empuja en contra de la
conclusión — pero se declara.

#### 3.5.2 Tasa de respuesta, y el acuse interno

Medida mecánica, sin juicio semántico: ¿respondió el receptor por el canal antes de la siguiente
recepción? Excluidas las notificaciones de disponibilidad, que no piden respuesta.

| Mecanismo | n | responde | tasa |
|---|---|---|---|
| Peer | 84 | 74 | **88 %** |
| Teams | 18 | 9 | **50 %** (32 notificaciones excluidas) |

**El silencio no es silencio: es acuse interno.** En las 10 recepciones peer sin respuesta, el texto
del receptor muestra que procesó el mensaje y decidió que no hacía falta contestar. Literalmente, en
un caso: *"Coordinación cerrada por ese lado (no necesita respuesta: confirma que verificará el
hallazgo con sus propios lectores antes de afirmarlo en su spec…)"*. En otros: *"Correcciones
aceptadas"*, *"El compañero ha empujado los dos tenants. Sigo con lo dicho"*.

Esto obliga a partir en dos la categoría **Silencio** de la taxonomía original (hoy §4.4), que tal como está no distingue el
fallo del comportamiento correcto:

| Categoría nueva | Definición |
|---|---|
| Acuse interno con cierre | B integra el mensaje en su razonamiento y **con razón** no responde: no había nada que pedir |
| Acuse interno con caída | B integra el mensaje, había una acción que le tocaba, y no la hace ni lo dice ← el fallo de julio |

Separarlas es juicio semántico y no se resuelve con regex. Es el trabajo pendiente de la capa 0.

#### 3.5.3 Lo que NO se puede medir mecánicamente aquí

La ventana entre una recepción y la siguiente es enorme (peer: p50 = 156 turnos, p90 = 601). Contar
"usó herramientas después de recibir" recoge sobre todo el **trabajo propio** del receptor, no acción
sobre lo pedido. Cualquier cifra de "cumplimiento" derivada de esa ventana estaría inflada. Se
descarta el instrumento: el cumplimiento se puntúa por contenido o no se puntúa.

### 3.5.4 Rejilla de categorías, derivada del corpus

Las categorías salen de leer los 174 `summary` distintos, no de imaginarlas. Primera pasada
cuantificada con reglas léxicas sobre los 179 envíos peer:

| Categoría | n | % | Ejemplo |
|---|---|---|---|
| Aviso de alcance | 36 | 20 % | *"Aviso de alcance: cojo TICKET-41, 42 y 43"* |
| Notificación de progreso | 32 | 18 % | *"v0.31.0 desplegada y verificada"* |
| Handoff de recurso | 21 | 12 % | *"Contracción desplegada; el campo es tuyo"* |
| **Rectificación** | 20 | 11 % | *"RECTIFICO: master NO está rojo, era mi venv"* |
| Espera / secuenciación | 18 | 10 % | *"ESPERA unos minutos — tengo v0.35.0 en vuelo"* |
| **Aviso de defecto ajeno** | 16 | 9 % | *"Tu pod está en ImagePullBackOff: bumpeaste antes del build"* |
| Consulta de estado | 4 | 2 % | *"¿En qué tickets estás trabajando?"* |
| Sin clasificar | 32 | 18 % | — |

**Calidad de esta pasada.** Reglas léxicas, con falsos positivos visibles (*"¿Qué destapó tu workflow
del 747?"* cae en rectificación). Vale para magnitudes, no para publicar. La codificación definitiva
es la de doble pase. Y no es ciega: la rejilla se derivó tras leer el corpus, así que por §3.2 esto
es generación de hipótesis, no evidencia.

**Agrupada por capa:** coordinación (alcance + progreso + handoff + espera + consulta) ≈ **62 %**;
contenido técnico sobre la zona del otro (rectificación + defecto ajeno) ≈ **20 %**.

### 3.5.5 Dos patrones que el diseño no había previsto

**a) El mutex negociado en lenguaje natural.** La categoría espera/secuenciación no son avisos
sueltos: forman un protocolo completo de exclusión mutua, negociado y cerrado entre pares. Una
secuencia real del 9 de agosto, íntegra:

> *"Aviso: voy a poner DOS tenants en el motor de tst"* → *"ESPERA unos minutos — tengo v0.35.0 en
> vuelo"* → *"Espero. Y tu vía de verificación NO se rompe: comprobado"* → *"Ventana libre — v0.35.0
> rodada y verificada"* → *"Empujado b7c8d9e: dos tenants"*

Petición, bloqueo, reconocimiento del bloqueo con verificación de que no rompe al otro, liberación,
consumo. Esto es exactamente el **merge emergente** de §1.3, y ahora hay traza literal en vez de
impresión. La capa 3 puede medir sobre esto en lugar de fabricarlo.

**b) La falsificación cruzada — el patrón incómodo para la tesis de julio.** El 11 % de
rectificaciones no es ruido de cortesía: hay casos donde **una sesión corrige una creencia falsa de
la otra, y la corrección se sostiene**. La cadena más limpia:

> *"master está rojo: 9 tests, de tu d4e5f6a"* → *"master NO está roto: era el venv con core-lib 0.11.0
> y el pin en 0.12.0"* → *"RECTIFICO: master NO está rojo, era mi venv"* → *"Yo caí igual y encima
> te lo confirmé: mi aislamiento compartía tu venv"*

Dos sesiones convergen a un diagnóstico correcto que una sola tenía mal, y la segunda descubre que
había cometido el mismo error. Eso es **capa semántica**, no sintáctica: el canal no está evitando
una colisión, está corrigiendo una creencia.

El artículo de julio concluyó que el canal no compra aprobados y que la palanca era la propiedad de
la integración. Este patrón no lo contradice —no hay contrafactual: nadie sabe si la sesión habría
llegado sola— pero **sí es un mecanismo por el que un canal podría comprar resultado**, y el diseño
actual no lo mide en ninguna capa.

**Consecuencia para la capa 1.** Añadir un tipo de escenario: A sostiene una creencia falsa
verificable (el test rojo es culpa de B) que B puede falsar con información que solo B tiene. Se
puntúa mecánicamente: ¿corrige A su creencia? Es tan verificable por script como la petición de
acción, y ataca la pregunta que de verdad quedó abierta en julio.

### 3.5.6 Topología: la coordinación es bilateral, nunca de grupo

Reconstruidas 84 aristas dirigidas emparejando cada recepción con su envío.

| | |
|---|---|
| Pares de sesiones que se hablan | 8 |
| Concentración | un solo par (`09d6fba6 ↔ aa19dfdf`) acumula **43 de 84**, el 51 % |
| Ráfagas (mensajes seguidos con < 20 min) | 30; p50 = 2, p90 = 6, máx = 8 |
| Ráfagas de un solo mensaje, sin réplica | 8 de 30 |

**No existe canal de grupo.** La difusión aparece solo como unicast repetido: 4 casos, 9 envíos, con
fan-out máximo de 3 destinos en 23 segundos (*"Aviso de alcance: cojo TICKET-41, 42 y 43"*). Cada
receptor lo recibe, y **ninguno sabe que los demás lo recibieron**. No hay conocimiento común, solo
copias.

**Y nadie tiene el mapa.** Solo 20 de 179 mensajes mencionan a una tercera sesión, y el caso más
elocuente muestra que el emisor ni siquiera sabe con quién habla respecto al trabajo:

> *"Lo que NO toco: **TICKET-44** (lo lleva otra sesión — **si eres tú**, es tuyo entero…)"*

Esto es evidencia estructural directa de la premisa de §1.3 —*nadie llega a poseer el estado
integrado final*— y es el mejor apoyo empírico disponible para la predicción registrada de §6.3.
Conviene decirlo con cuidado: describe la topología, no el resultado. Que nadie tenga el mapa no
demuestra todavía que el trabajo salga peor.

### 3.5.7 Mutex: el recuento léxico estaba mal

Una primera pasada con detector léxico dio 19 secuencias candidatas, de las que solo 5 llegaban al
final, y se anotó aquí la lectura provisional de que *"el protocolo se abre mucho más de lo que se
cierra"*.

**Recontado sobre las categorías codificadas (§3.5.9), sale lo contrario.** Peticiones de espera
reales dentro de una ventana de conversación: **3**. Que llegan a `handoff-recurso` en la misma
ventana: **3**. Las tres, cerradas:

| Ventana | Petición | Cierre |
|---|---|---|
| W004 | *"Espera ~10 min: hay un camino de v0.28.0 que no he ejercitado"* | ✅ |
| W009 | *"ESPERA unos minutos — tengo v0.35.0 en vuelo"* | ✅ |
| W036 | *"Dame ~10 min: verificando el frontend en TST"* | ✅ |

Las otras 16 "candidatas" del detector léxico eran falsos positivos: cualquier mensaje con *espera*,
*para* o *adelante* entraba. **El hallazgo provisional queda retirado**, y la cifra corregida apunta
en dirección opuesta: cuando el protocolo de exclusión mutua se abre de verdad, se cierra siempre.

Es un ejemplar de la propia tesis del artículo anterior sobre auditar el harness (§7.1): la primera
medida no estaba midiendo lo que decía medir. Vale la pena contarlo en la pieza.

**Y un dato que solo aparece al codificar.** Hay **20 `handoff-recurso`** y solo 3 vienen precedidos
de una petición. Es decir, **17 cesiones espontáneas**: las sesiones sueltan recursos sin que nadie
se los pida. Eso es cooperación proactiva, y no estaba en ninguna hipótesis del diseño.

### 3.5.7b Emparejamiento por par de sesiones y ventana temporal

**El obstáculo, que no es menor.** La misma sesión se direcciona de tres formas —socket `uds:`,
nombre con ref, nombre suelto— así que agrupar por la cadena `to` parte un mismo hilo en varios y
produce el falso hallazgo de "sesiones que nunca contestan" (§3.5.1). Hay que resolver identidad
antes de agrupar.

**Método, en tres pasos.** Es reutilizable y conviene dejarlo escrito:

1. Cada recepción se empareja con su envío **por contenido**, lo que da una arista emisor→receptor
   verificada. Esa arista *enseña* que la cadena `to` de ese envío equivale a la sesión receptora.
2. El diccionario aprendido se aplica al resto de envíos, incluidos aquellos cuya recepción no está
   en disco.
3. Se agrupa por par no ordenado y se corta en ventanas por hueco de 20 minutos.

Aprende 15 alias que colapsan a 8 sesiones —`workspace-86 [b44a1e]`, `uds:…6677.sock` y
`workspace-cb [e6df9f]` resultan ser la misma— y resuelve **168 de 179 envíos**. Los 11 que
quedan van a sesiones de las que nunca se recibió nada, así que no hay de dónde aprender el alias.

**Resultado.**

| | |
|---|---|
| Ventanas de conversación | **40**, sobre 11 pares |
| Mensajes por ventana | p50 = 3, p90 = 10, máx = 18 |
| Alternancias por ventana | p50 = 2, máx = 13 |
| **Ventanas unilaterales** (nadie contesta) | **13 de 40** |

Las dos más largas son negociaciones sostenidas: 18 mensajes con 13 alternancias en 58 minutos
(`09d6fba6 ↔ aa19dfdf`, 9 de agosto) y 15 con 11 alternancias en 64 minutos (`b4b86a7d ↔ ffc27c4f`).
El artefacto `pair_windows.json` lleva los identificadores `M###` de cada mensaje, así que la
codificación de §3.5.4 se une encima y el mutex se puede recontar sobre categorías codificadas en
lugar de sobre coincidencias léxicas.

Que **una de cada tres ventanas sea unilateral** es el dato que hay que llevar a la capa 1: mide
cuántos intercambios mueren en el primer mensaje.

### 3.5.8 Catálogo de escenarios para el repo semilla

Cumple el requisito de §4.1: los episodios que reproduce la capa 1 son los observados, no inventados.
Los cuatro primeros son delegaciones puras —A bloqueada, acción pequeña e inequívoca en manos de
B—; el quinto es el tipo nuevo que abre §3.5.5b.

| # | Escenario real | Petición | Verificación por script | Desenlace observado |
|---|---|---|---|---|
| 1 | Un worktree de B tiene tomada la rama `main`, A no puede hacer checkout para mergear | *"¿Puedes soltar `main` en `wt-tag3` y decírmelo?"* | ¿existe el worktree? ¿está `main` libre? | **Cumplido en 2 min**, con verificación previa por parte de B (HEAD == origin/main, 0 sin empujar, 0 stash) |
| 2 | B afirma que un commit está en `main`; en realidad nunca salió de su máquina | *"`a1b2c3d` no ha salido de tu máquina… cuando pushees, lo verifico"* | `git branch -r --contains <sha>` | **Cumplido + rectificación**: *"Tenías razón y era mi fallo"* |
| 3 | A sube el pin de `core-lib` a 0.14.0; el venv compartido que B acaba de dejar en 0.11.0 queda desalineado | *"el venv compartido hay que volver a alinearlo"* | versión instalada en el venv, tres medidas coincidiendo | Cumplido, con vaivén: los dos llegaron a la vez desde lados opuestos |
| 4 | A va a abrir un ticket que ya existe | *"El ticket ya existe (TICKET-45), no lo dupliques"* | ¿se creó un ticket nuevo? | Acción **negativa**, verificable igual |
| 5 | A cree que `master` está rojo por un commit de B; en realidad es el venv local de A | *"master NO está roto: era el venv con core-lib 0.11.0 y el pin en 0.12.0"* | ¿corrige A su creencia y deja de buscar el bug donde no está? | **Creencia corregida**, y B descubre que había caído en lo mismo |

**La familia común, que las propias sesiones nombran.** Los cinco son variantes de un mismo fallo, y
uno de los agentes lo formula mejor que cualquier resumen mío: *"la comprobación que se hace sobre
algo distinto de lo que se entrega"*. Los ejemplares del corpus:

- Un `git checkout main && git merge …` falla en el checkout, la cadena se corta, **el merge nunca
  ocurre**, y el comando siguiente corre igual y sale verde: *"Estuve a un paso de leer «69 passed»
  como «main mergeado y verde» cuando era mi rama de siempre."*
- Un `sed` del bump apunta a `v0.25.0` cuando el fichero tiene `v0.25.1`: **el commit sale vacío** y
  el script informa de éxito.
- Un commit que se cuenta como publicado sin haber sido empujado.
- Una suite que se corre **antes** del bump, así que la guarda nunca ve lo que se taggea.

Esto le da al repo semilla algo mejor que un bloqueo artificial: un **fallo silencioso realista**,
donde la señal local dice verde y el estado publicado dice otra cosa. Es exactamente el terreno
donde un canal entre sesiones podría comprar resultado — porque el otro mira desde fuera — y por eso
merece ser el eje de la capa 1 en lugar de un `export` que falta.

### 3.5.9 Codificación definitiva: dos pases independientes

Los 179 mensajes se codificaron **dos veces por codificadores independientes** que no vieron el
trabajo del otro, con el libro de códigos de §3.5.4 en sus tres ejes.

#### Fiabilidad

| Eje | Acuerdo bruto | Kappa de Cohen |
|---|---|---|
| Categoría (10 valores) | 91,1 % | **0,90** |
| Delegación (sí/no) | 97,8 % | **0,88** |
| Capa (sintáctica/semántica) | 92,7 % | **0,84** |

Los desacuerdos se concentran en fronteras que el libro ya señalaba: alcance ↔ progreso (3),
progreso ↔ petición (2). **Los ítems en disputa se cuentan aparte, no se resuelven a favor de
ninguna hipótesis.**

**Salvedad que hay que declarar en el artículo.** Los dos codificadores son agentes LLM, no
personas. Una kappa alta entre dos LLM mide consistencia, **no** validez: pueden compartir el mismo
sesgo y coincidir en el mismo error. Es mejor que las regex y peor que dos codificadores humanos, y
así hay que presentarlo.

#### Tasas base (163 ítems donde ambos pases coinciden)

| Categoría | n | % |
|---|---|---|
| Notificación de progreso | 38 | 23,3 % |
| Aviso de alcance | 30 | 18,4 % |
| Handoff de recurso | 21 | 12,9 % |
| Aviso de defecto ajeno | 20 | 12,3 % |
| Rectificación | 18 | 11,0 % |
| Respuesta de estado | 17 | 10,4 % |
| Consulta de estado | 10 | 6,1 % |
| Petición de acción | 5 | 3,1 % |
| Petición de espera | 3 | 1,8 % |
| Otro | 1 | 0,6 % |

#### Los dos números que deciden la pieza

**1. La delegación es rara: 16 de 179, un 8,9 %** (4 en disputa). La unidad de medida de §4.1 —A
bloqueada necesitando que B actúe— ocurre en menos de uno de cada diez mensajes. Esto dispara la
primera fila de riesgos de §8, cuya mitigación era reencuadrar la pieza hacia **cuándo importa esto
siquiera**.

**2. Pero la capa semántica es mucho mayor de lo estimado: 36,1 %** frente al 20 % que daban las
regex. Rectificación (11 %) y aviso de defecto ajeno (12,3 %) suman ya 23 puntos por sí solos.

**La tensión entre ambos es el hallazgo.** El canal casi nunca se usa para **pedir**, y muy a menudo
para **decirle al otro algo verdadero sobre su propio trabajo**. La capa 1, tal como está diseñada,
mide el 9 % y deja fuera el 36 %.

Reorientación que se propone: el eje de la pieza deja de ser el follow-through de una petición y
pasa a ser **el cross-check** — una sesión mirando el trabajo de otra desde fuera. Encaja con el
catálogo de escenarios de §3.5.8, cuya familia común es precisamente *"la comprobación que se hace
sobre algo distinto de lo que se entrega"*, y con la falsificación cruzada de §3.5.5b.

#### Qué le pasa a las 16 delegaciones

Localizadas 15 en ventanas de conversación. **14 reciben respuesta; 1 se queda sin ella** (M080, la
realineación del venv, con la ventana ya cerrada). Las respuestas se reparten así:

| Respuesta del receptor | n |
|---|---|
| `handoff-recurso` (cede lo pedido) | 5 |
| `rectificacion` (corrige la premisa de la petición) | 4 |
| `notificacion-progreso` (informa de que lo hizo) | 4 |
| `aviso-defecto-ajeno` | 1 |

Que 4 de 15 delegaciones se contesten **rectificando la premisa** —*"master NO está roto: era el
venv"*, *"No es el pod: la imagen aún no existe. No busques el bug todavía"*— refuerza la
reorientación de arriba: incluso cuando alguien pide algo, lo que a menudo devuelve el canal es una
corrección.

**Cuidado con la lectura fácil.** 14 de 15 respondidas no es una tasa de cumplimiento: responder no
es hacer. Distinguirlas exige el juicio semántico de §3.5.2, y con n = 15 cualquier porcentaje
tendría un intervalo inútil. Se reporta como conteo, no como tasa.

### 3.6 El experimento natural que el corpus regala

Peer y teams son la misma máquina, los mismos días, el mismo trabajo, y difieren justo en lo que el
artículo de julio identificó como la variable que importa:

| | Peer | Teams |
|---|---|---|
| Lead / dueño de la integración | no | sí |
| Roles nombrados | no | sí (`t*` ejecuta, `r*` revisa) |
| Señal de disponibilidad | no | sí (34 `idle_notification`) |
| Empujón de cumplimiento en la entrega | no | sí |
| Tasa de respuesta | 88 % | 50 % |

Es el contraste estructura-sí / estructura-no sobre trabajo real, sin gastar máquina. **No sustituye
a la capa 3**: no hay asignación aleatoria, las tareas difieren y la dirección del tráfico no es
comparable (en teams el receptor suele ser el lead recibiendo informes). Pero fija la hipótesis con
mucha más precisión que un brazo sintético, y si la capa 3 se abandona por presupuesto (§6.4), esta
sección deja la pieza con algo que decir sobre estructura.

---

## 4. Capa 1 — Núcleo: el cross-check

*(Rediseñada el 2026-08-11 a la vista de las tasas base de la capa 0. La versión anterior
medía el follow-through de una petición; ver §4.0 para el porqué del cambio.)*

### 4.0 Por qué el núcleo deja de ser el follow-through

El diseño original medía el follow-through de una petición: A bloqueada, B tiene que actuar. La capa
0 dice que eso es **el 8,9 %** del tráfico, mientras que el contenido técnico sobre la zona del otro
—rectificaciones y avisos de defecto ajeno— es el **36,1 %** (§3.5.9).

Gastar el presupuesto de máquina en medir con mucho cuidado el 9 % y dejar fuera el 36 % es mal
reparto. El núcleo pasa a ser lo que el canal **sí** hace: una sesión comprobando desde fuera el
trabajo de otra.

Esto además cambia la pregunta a una que el artículo de julio no pudo hacerse. Allí se midió si un
canal ayuda a **repartir trabajo**, y la respuesta fue que no; la palanca era la propiedad de la
integración. Aquí se mide si un canal ayuda a **detectar un error**, que es un mecanismo distinto y
sin explorar.

### 4.1 Unidad de medida: el fallo silencioso

Un episodio en el que **A cree haber entregado algo que no ha entregado**, y la discrepancia es
visible desde fuera pero no desde dentro.

Es la familia que el corpus produce sola, y que uno de los agentes formula mejor que cualquier
definición: *"la comprobación que se hace sobre algo distinto de lo que se entrega"* (§3.5.8). Los
ejemplares reales —checkout que falla y deja pasar los tests de la rama vieja, `sed` que produce un
commit vacío, commit contado como publicado sin push, suite corrida antes del bump— son los que se
reproducen en el repo semilla. Nada inventado.

**Ventaja decisiva sobre el diseño anterior: el scoring es totalmente mecánico.** No hace falta
juzgar si B "cumplió". Basta comparar, al final del episodio, **lo que A afirma** contra **el estado
publicado del repositorio**. Existe o no existe el commit en `origin`. La afirmación es verdadera o
falsa. Cero juicio humano, que era la exigencia de §7.1.

### 4.2 El repo semilla

Requisitos, todos derivados del corpus:

1. La tarea de A contiene un paso que **puede fallar en silencio** dejando una señal local verde.
2. La tarea de B, por su propio trabajo, **le hace mirar el estado publicado** que delata la
   discrepancia — igual que en el corpus, donde ambos trabajan sobre los mismos repos. B no recibe
   ninguna instrucción de auditar a A: si mira, es porque su tarea le lleva.
3. El desenlace se verifica por script sobre el estado final del repo.

El punto 2 es el más delicado y hay que declararlo: si se le dijera a B "vigila a A", el experimento
mediría obediencia, no cross-check.

**Construido y auditado** (2026-08-11):
[github.com/JaviMaligno/cross-session-crosscheck](https://github.com/JaviMaligno/cross-session-crosscheck). Reproduce un
caso literal del corpus —*"el wheel 0.16.0 del paquete dice que es 0.15.0"*—: `widgetkit` declara su
versión en `pyproject.toml` y en el `__version__` público de `__init__.py`, y el helper de release
del equipo solo actualiza el primero. La suite pasa, el helper imprime `released 0.4.0`, el tag
llega a `origin`, y el paquete publicado sigue diciendo que es 0.3.1.

B lo ve por su propio ticket: `dashboard` activa funcionalidad leyendo `widgetkit.__version__` en
tiempo de ejecución, así que al implementar lo suyo la puerta cae al fallback y la discrepancia le
aparece delante. Sin una sola instrucción de auditar.

`harness/verify_seed.sh` comprueba antes de gastar sesiones las tres condiciones sin las cuales esto
mediría otra cosa: que el fallo ocurre, que **deja señal local verde**, y que es visible desde la
tarea propia de B. Es la auditoría del harness de §7.1 aplicada por adelantado en vez de a
posteriori.

### 4.3 Brazos

El mensaje ahora lo origina **B**, el observador, no A. El replay se mantiene, invertido:

| Brazo | Procedimiento |
|---|---|
| **Canal** | B usa el canal entre sesiones. Se captura el texto exacto que B envió. |
| **Buzón** | Se inyecta *ese mismo texto capturado* en un fichero que A consulta. Replica la entrega de CooperBench. |
| **Sin canal** | B no tiene forma de avisar. Línea base imprescindible: **¿corrige A su error por su cuenta?** |

El brazo sin canal deja de ser un control pobre y pasa a ser el más informativo: da la tasa de
autocorrección, sin la cual cualquier mejora atribuida al canal está sin contrafactual.

**La instrucción de sondeo va en los tres brazos.** Si solo el brazo buzón lleva "consulta este
fichero periódicamente", se compara canal contra buzón-más-instrucción-de-sondear, y la instrucción
es tratamiento. En canal y sin canal el fichero permanece vacío. Así lo único que varía es el
mecanismo de entrega.

El replay deja los brazos **pareados por construcción** y obliga a que dentro de un escenario sean
**secuenciales**, no paralelos: el buzón depende del texto capturado en el brazo de canal. Encaja
con el límite de concurrencia de la máquina.

### 4.4 Taxonomía de resultado: la cadena de detección

El fallo puede escaparse en cuatro sitios, y el diseño mide los cuatro por separado. Ninguna
métrica agregada sustituye a esto: decir "el canal ayuda" sin saber **dónde** ayuda es lo que la
pieza anterior evitó y esta también debe evitar.

| Eslabón | Pregunta | Se observa en |
|---|---|---|
| 1. **Mirada** | ¿B llega a ver el estado que delata el fallo? | Transcript de B |
| 2. **Detección** | Habiéndolo visto, ¿B reconoce que hay discrepancia? | Transcript de B |
| 3. **Comunicación** | ¿B se lo dice a A? | Envío por el canal / buzón |
| 4. **Corrección** | ¿A abandona su creencia falsa y arregla? | Estado final del repo |

Desenlaces terminales, todos verificables por script:

| Categoría | Definición |
|---|---|
| **Corregido** | A rectifica y el estado publicado acaba siendo el que A afirma |
| **Falso «hecho»** | A termina afirmando algo que el repo desmiente ← el fallo que la pieza persigue |
| **Autocorregido** | A lo caza solo, sin intervención de B (posible en los tres brazos) |
| **Corrección rechazada** | B avisa, A responde, y A mantiene su creencia ← el follow-through de julio, en su forma más nítida |
| **Deriva** | A corrige y rompe su propia tarea al hacerlo |

La categoría *corrección rechazada* es la que conecta esta capa con el artículo anterior: es el
acuse sin acción, pero sobre una creencia en vez de sobre una petición.

### 4.5 Predicción registrada (antes de correr)

> **La corrección se acepta; el cuello de botella está antes.** En el corpus, todas las
> rectificaciones observadas aterrizan —*"Tenías razón y era mi fallo"*, *"RECTIFICO"*— sin un solo
> caso de creencia defendida contra evidencia. Así que el eslabón 4 no fallará casi nunca, y lo que
> separe al brazo con canal del brazo sin canal será **la mirada y la detección** (eslabones 1 y 2),
> no la obediencia.
>
> Y una consecuencia que va contra el prior de julio: si esto se confirma, el canal **sí** compra
> corrección, porque el fallo silencioso es por construcción invisible desde dentro. Sería el primer
> resultado de esta serie en que un canal compra resultado y no solo orden.

Si sale al revés —A defiende su creencia falsa contra la evidencia de un par— es mejor artículo
todavía, y encaja con el fallo documentado en julio.

### 4.6 Métrica en dirección contraria: el coste de mirar hacia fuera

Obligatoria, y reformulada. La versión original medía el coste de **interrumpir**, pero la capa 0
mostró que el canal encola en frontera de turno (§3.5.1): no hay interrupción que costear. El coste
real del cross-check es otro y va en la misma dirección: **B gasta turnos auditando lo ajeno en vez
de hacer lo suyo**.

Instrumentos:

- Turnos que B dedica al asunto de A, y si retoma su propia tarea donde la dejó.
- **Si la suite propia de B se degrada respecto al brazo sin canal.** Es la medida que puede tumbar
  la conclusión entera: un canal que salva la tarea de A hundiendo la de B no compra nada.
- Falsos positivos: ¿cuántas veces avisa B de un fallo que no existe? Un cross-check ruidoso tiene
  coste aunque acierte a veces.

Medir solo la detección sería vender en vez de medir.

### 4.7 Réplicas

Tres semillas por celda. Es el estándar ya establecido en el artículo anterior, y existe
precisamente para cazar el tipo de sobre-afirmación que allí ya se cazó (el 42% de
territorio+integrador que se desplomó a 33% [21–42] con dos semillas más).

---

## 5. Capa 2 — Instrumento: qué sobrevive al resumen

**No va al lado de la capa 1: va dentro.** Antes de puntuar si B actuó, se captura qué recibió y qué
entendió.

### 5.1 La cadena de cuatro nodos

Invertida respecto al diseño original, porque ahora el emisor es el observador:

```
lo que B ha detectado  →  texto que B decide enviar  →  lo que A entiende  →  si A corrige
```

Tres aristas, tres sitios donde perder. Se miden las tres:

1. **Compresión de B.** La discrepancia existe y es conocida: la define el escenario (el commit no
   está en `origin`, el merge no ocurrió, la suite corrió sobre otro árbol). Se compara la lista de
   elementos de la discrepancia —qué está mal, dónde se ve, con qué comando se comprueba, qué
   consecuencia tiene— contra los que aparecen en el texto que B envió. Un aviso que dice *"algo va
   mal en tu rama"* y otro que dice *"`git branch -r --contains a1b2c3d` no devuelve nada"* no son
   el mismo aviso, y el corpus sugiere que la diferencia importa: las rectificaciones que aterrizan
   traen el comando.
2. **Recepción de A.** Tras la entrega, se sondea a A pidiéndole que reformule qué le están diciendo
   y **qué cree ahora sobre el estado de su trabajo**, antes de dejarle actuar. Se puntúa qué
   elementos sobrevivieron y si la creencia ya ha cambiado en ese punto. El sondeo lo escribe el
   operador directamente en la sesión de A, con un texto fijo idéntico en todos los brazos.
3. **Corrección de A.** La taxonomía de §4.4.

El nodo 2 es donde esta capa gana su sitio: separa *no entendió el aviso* de *lo entendió y siguió
creyendo lo suyo*. Sin ese sondeo, ambas cosas se ven igual desde fuera.

### 5.2 Por qué esto importa

Separa dos fallos que el artículo anterior **no podía** separar: *no se enteró* vs *se enteró y no
actuó*. Allí la fontanería se verificó a mano, caso por caso, para declararla inocente. Aquí queda
instrumentada y automática. Es una mejora metodológica sobre la propia pieza previa, y conviene
decirlo en el artículo.

### 5.3 La cadena también se mide sobre el corpus

El pre-flight (§3.4) encontró que emisor y receptor registran su lado. Eso permite aplicar las dos
primeras aristas —intención comprimida a texto, y texto entendido por B— a los 213 envíos reales,
no solo a los escenarios fabricados. Con una diferencia que hay que declarar: en el corpus la
*intención* de A no está definida por un escenario, así que la primera arista solo se puede puntuar
donde el propio mensaje de A o su transcript la hagan explícita. Donde no, se marca como no
puntuable en vez de estimarla.

---

## 6. Capa 3 — Validación externa: la épica (desechable)

Repo semilla, 4 tickets, **colisiones registradas antes de correr**. N=2 y N=4. N=8 fuera.

### 6.1 Brazos

| Brazo | Descripción |
|---|---|
| **Aislado** | Sin canal, merge al final. Control negativo. |
| **Emergente** | Con canal, comportamiento natural. Lo que el autor ya hace: secuencias espontáneas, merge por colisión. **El único brazo que produce hallazgo.** |
| **Integrador impuesto** | Con canal, más una sesión dueña del estado integrado final. **Control positivo**, ver §6.1.1. |

#### 6.1.1 Por qué el integrador es control positivo y no hallazgo

Este brazo es C4 del artículo anterior. Su respuesta ya está publicada, así que correrlo otra vez no
descubre nada — pero **no se puede citar en su lugar**: la cifra de julio salió de CooperBench, no
del repo semilla de aquí, y no son comparables. O se re-corre o se cae la comparación.

Se re-corre, cambiándole el papel. El integrador impuesto no está aquí para demostrar que funciona;
está para demostrar que **este montaje reproduce un efecto conocido**. Si no lo reproduce, el
sospechoso es el harness, no el brazo emergente, y las cifras de la pieza no se publican hasta
entenderlo. Cuesta lo mismo que en el diseño original y compra validez en vez de duplicar un
hallazgo. Es además la forma concreta que toma aquí la auditoría adversarial del harness que exige
§7.1.

Regla que se deriva: en el artículo, el número del integrador se presenta como **calibración**, no
como resultado, y con enlace explícito al artículo de julio.

### 6.2 Métricas: dos columnas que nunca se mezclan

- **Sintáctica:** conflictos de merge, colisiones de fichero, esperas, mensajes de aviso.
- **Semántica:** suite por ticket + **suite integrada**. El aprobado exige ambas, igual que el
  criterio de CooperBench exigía que pasaran las dos features.

### 6.3 Predicción registrada (antes de correr)

La versión anterior de esta sección predecía que *"el canal hunde la columna sintáctica y no mueve
la semántica"*. Eso no es una predicción: es la conclusión publicada en julio. Registrarla como
predicción y luego confirmarla no aporta nada, y hace parecer riesgo lo que era expectativa.

La única pregunta abierta es **dónde cae el merge emergente**:

> En la columna semántica, el brazo emergente quedará más cerca de **aislado** que de **integrador
> impuesto**, porque en el merge negociado por colisión la propiedad del estado integrado es
> transitoria y nadie termina con la vista del conjunto. En la columna sintáctica quedará cerca del
> integrador: pocas colisiones, pocos conflictos. La disociación entre ambas columnas es el
> resultado esperado.

Corolario que hay que registrar igual, porque es el desenlace más incómodo: si emergente **iguala**
a integrador impuesto en la columna semántica, entonces el hand-off pequeño y repetido basta, el
lead dedicado es prescindible, y una parte de la conclusión de julio necesita matiz. Ese es el
resultado que haría el mejor artículo, y por eso conviene dejarlo escrito antes de correr.

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
3. **Lo que creía que era nuevo, y no lo era.** La entrega no interrumpe: encola en frontera de
   turno, 138 de 138 (§3.5.1). Se cae el pilar con el que empecé a diseñar. Contarlo, no esconderlo.
4. **Tres mecanismos confundidos.** Peer, teams y subagentes comparten preámbulo; el primer minado
   los mezclaba. Es a la vez advertencia metodológica para quien replique y el hallazgo que regala
   el contraste estructura-sí / estructura-no (§3.6).
5. **Tasas base.** Con qué frecuencia esto es siquiera portante: delegación 8,9 %, capa semántica
   36,1 %, con kappa entre codificadores y la salvedad de que los codificadores son LLM.
6. **El giro.** El canal casi nunca se usa para pedir y muy a menudo para decirle al otro algo
   verdadero sobre su propio trabajo. De ahí el cross-check como núcleo (§4.0).
7. **Nadie tiene el mapa.** Topología bilateral, difusión solo por repetición, sin conocimiento
   común. La cita del *"si eres tú, es tuyo entero"* (§3.5.6).
8. **Un hallazgo mío retirado.** El mutex "se abre más de lo que se cierra" era un artefacto del
   detector léxico; recontado sobre categorías codificadas, las tres aperturas reales se cierran
   (§3.5.7). Es la auditoría del harness de §7.1 aplicada a mí mismo, y va en el cuerpo del
   artículo, no en una nota al pie.
9. **Predicciones registradas** (§4.5, §6.3).
10. **Resultados** por capa, con la cadena de cuatro nodos como hilo.
11. **El coste de mirar hacia fuera** — la métrica que va en contra (§4.6).
12. **Qué dice y qué no dice.** Cobertura vs confianza, igual que en la pieza anterior. Cinco días
    de corpus, una sola persona, un solo equipo de repos.

### 7.1 Reglas de honestidad heredadas

- Ninguna recomendación más fuerte que los datos que la sostienen.
- Rangos [min–max] sobre semillas, no números sueltos.
- Auditoría adversarial del propio harness antes de publicar cifras. En la pieza anterior dos
  condiciones puntuaron un 0% falso por bugs de composición del eval; la fontanería de scoring
  merece tanto test como las condiciones. Aquí toma la forma concreta del control positivo de
  §6.1.1.
- Declarar explícitamente el techo: cobertura, no confianza.
- **Nada que ya se publicó vuelve a venderse como hallazgo.** El brazo integrador se presenta como
  calibración y enlaza al artículo de julio; la taxonomía de resultado y el método de comparación pareada se
  presentan como instrumento heredado. Reutilizar instrumento hace la serie acumulativa; repetir una
  medición ya respondida y presentarla como nueva, no.
- Declarar la ventana del corpus (cinco días, §3.0) allí donde aparezcan sus cifras.

---

## 8. Riesgos

| Riesgo | Mitigación |
|---|---|
| Las tasas base de la capa 0 salen ridículas: la feature casi nunca es portante | Es un hallazgo publicable. Reencuadra la pieza hacia "cuándo importa esto siquiera" y ahorra las capas 2–3. |
| El envío agéntico no ocurre cuando el escenario lo requiere (A no pide ayuda) | Es un dato, no un fallo: "A ni siquiera pidió" entra en la taxonomía como categoría cero. |
| La capa 3 se come el presupuesto y queda a medias | Orden de ejecución 0 → 1+2 → 3; condición de abandono en §6.4. |
| El scoring de "fallo semántico" requiere juicio | Suite por ticket + suite integrada, definidas en el repo semilla antes de correr. |
| ~~Los transcripts de las sesiones antiguas ya no existen~~ | **Resuelto.** Pre-flight cerrado: 213 envíos y 117 recepciones disponibles con ambos lados registrados (§3.0, §3.4). |
| **La entrega no interrumpe de verdad**: la mayoría de mensajes llegan con la sesión parada y el canal es un buzón con otro envoltorio | Se mide en la capa 0 antes de gastar en la capa 1 (§3.1). Si sale así, el contraste de la capa 1 se declara pequeño y la pieza se apoya en las capas 0 y 3. |
| El corpus es de cinco días y se lee como si fuera práctica establecida | Declarar la ventana en el artículo y no insinuar tendencia temporal (§3.0). |

---

## 9. Alcance excluido

- N=8 sesiones o más.
- Comparación con otros productos (Cursor, Codex, agentes multi-proceso ajenos).
- Reejecución del benchmark CooperBench completo.
- Cualquier afirmación sobre coste en dólares salvo que se instrumente explícitamente.
