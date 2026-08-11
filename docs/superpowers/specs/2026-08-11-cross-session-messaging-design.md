# Cross-session messaging: ¿canal o estructura?

**Fecha:** 2026-08-11 (revisado el mismo día tras cerrar el pre-flight §3.4)
**Estado:** diseño aprobado, capa 0 en ejecución
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
| **Agent teams** | `<teammate-message teammate_id="t1-core-kinds" color=… summary=…>` | 50 | 3 |
| **Subagentes** | resultado `Message sent to X's inbox` | — | — |

Las tres comparten el preámbulo `Another Claude session sent a message:`, así que un minado ingenuo
las mezcla. Se separan por la etiqueta, y en el lado emisor por el texto del `tool_result`, que es
verdad de terreno del propio producto: los envíos peer devuelven `→ destino (another Claude session
on this machine)`, los de teams y subagentes devuelven `Message sent to X's inbox`.

**Y no son variantes cosméticas.** El mecanismo de teams trae estructura incorporada que el peer no
tiene: roles nombrados (`t1-core-kinds` ejecuta, `r1-core-kinds` revisa), un lead, señal explícita de
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
| Proyecto dominante | `conversational-ai` |
| Mediana del mensaje | 1.712 caracteres |
| Recepciones peer trazadas | **84**, en 7 sesiones receptoras |

**Los fallos de direccionamiento son un dato, no ruido.** Los 13 se reparten en dos formas:
`'conversational-ai-ec' is not an agent in this conversation. Re-send with the ref to confirm you
mean: conversational-ai-ec [f0c54d]` (10 casos) y `No agent named 'X' is reachable` (3). Es decir:
dirigirse por nombre sin el ref falla y obliga a reintentar. Coste de fricción del canal que la
pieza puede reportar, porque sale gratis.

**Resolución de identidad.** `~/.claude/sessions/<pid>.json` mapea pid → `sessionId` → nombre
derivado → versión → estado, y el pid es el del socket. Así se comprueba que
`conversational-ai-86 [b44a1e]`, `uds:/tmp/cc-socks/6677.sock` y el transcript `b4b86a7d` son **la
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
- **Taxonomía observacional** (§4.3) aplicada a peticiones reales: cumplido / silencio / acuse sin
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

- **Ubicación.** Confirmada: `~/.claude/projects/-Users-javieraguilarmartin1-Documents-repos-conversational-ai/`.
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

Esto obliga a partir en dos la categoría **Silencio** de §4.3, que tal como está no distingue el
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
| Aviso de alcance | 36 | 20 % | *"Aviso de alcance: cojo DATS-772, 774 y 775"* |
| Notificación de progreso | 32 | 18 % | *"v0.31.0 desplegada y verificada"* |
| Handoff de recurso | 21 | 12 % | *"Contracción desplegada; el campo es tuyo"* |
| **Rectificación** | 20 | 11 % | *"RECTIFICO: master NO está rojo, era mi venv"* |
| Espera / secuenciación | 18 | 10 % | *"ESPERA unos minutos — tengo v0.35.0 en vuelo"* |
| **Aviso de defecto ajeno** | 16 | 9 % | *"Tu pod está en ImagePullBackOff: bumpeaste antes del build"* |
| Consulta de estado | 4 | 2 % | *"¿En qué tickets DATS estás trabajando?"* |
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
> rodada y verificada"* → *"Empujado 9c06e66: dos tenants"*

Petición, bloqueo, reconocimiento del bloqueo con verificación de que no rompe al otro, liberación,
consumo. Esto es exactamente el **merge emergente** de §1.3, y ahora hay traza literal en vez de
impresión. La capa 3 puede medir sobre esto en lugar de fabricarlo.

**b) La falsificación cruzada — el patrón incómodo para la tesis de julio.** El 11 % de
rectificaciones no es ruido de cortesía: hay casos donde **una sesión corrige una creencia falsa de
la otra, y la corrección se sostiene**. La cadena más limpia:

> *"master está rojo: 9 tests, de tu cf0e53f"* → *"master NO está roto: era el venv con core 0.11.0
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
fan-out máximo de 3 destinos en 23 segundos (*"Aviso de alcance: cojo DATS-772, 774 y 775"*). Cada
receptor lo recibe, y **ninguno sabe que los demás lo recibieron**. No hay conocimiento común, solo
copias.

**Y nadie tiene el mapa.** Solo 20 de 179 mensajes mencionan a una tercera sesión, y el caso más
elocuente muestra que el emisor ni siquiera sabe con quién habla respecto al trabajo:

> *"Lo que NO toco: **DATS-790** (lo lleva otra sesión — **si eres tú**, es tuyo entero…)"*

Esto es evidencia estructural directa de la premisa de §1.3 —*nadie llega a poseer el estado
integrado final*— y es el mejor apoyo empírico disponible para la predicción registrada de §6.3.
Conviene decirlo con cuidado: describe la topología, no el resultado. Que nadie tenga el mapa no
demuestra todavía que el trabajo salga peor.

### 3.5.7 Mutex: cuántas secuencias se cierran

Detector léxico sobre las ráfagas, buscando petición-de-espera → bloqueo reconocido → liberación →
consumo:

| Forma | n |
|---|---|
| Petición de espera **sin cierre** | 6 |
| Petición → liberación → consumo (completa) | 5 |
| Petición → liberación (sin consumo trazado) | 5 |
| Petición → bloqueo reconocido (se queda ahí) | 3 |

**5 de 19 llegan al final.** Pero el detector tiene falsos positivos visibles (marca *"Gracias por el
dato del hub; frontend v0.7.103 en build"* como petición de espera), así que la cifra vale como
magnitud, no como medida. La codificación definitiva es la de doble pase.

La lectura provisional, que hay que confirmar: el protocolo de exclusión mutua **se abre mucho más
de lo que se cierra**. Si aguanta, es el hallazgo que conecta con julio — el mismo hand-off pequeño
y repetido que hundió el modo `team` de CooperBench, con muchos sitios donde fumarla.

### 3.5.8 Catálogo de escenarios para el repo semilla

Cumple el requisito de §4.1: los bloqueos que reproduce la capa 1 son los observados, no inventados.
Los cuatro primeros son delegaciones puras —A bloqueada, acción pequeña e inequívoca en manos de
B—; el quinto es el tipo nuevo que abre §3.5.5b.

| # | Escenario real | Petición | Verificación por script | Desenlace observado |
|---|---|---|---|---|
| 1 | Un worktree de B tiene tomada la rama `main`, A no puede hacer checkout para mergear | *"¿Puedes soltar `main` en `wt-tag3` y decírmelo?"* | ¿existe el worktree? ¿está `main` libre? | **Cumplido en 2 min**, con verificación previa por parte de B (HEAD == origin/main, 0 sin empujar, 0 stash) |
| 2 | B afirma que un commit está en `main`; en realidad nunca salió de su máquina | *"`6549ae4` no ha salido de tu máquina… cuando pushees, lo verifico"* | `git branch -r --contains <sha>` | **Cumplido + rectificación**: *"Tenías razón y era mi fallo"* |
| 3 | A sube el pin de `agentic-core` a 0.14.0; el venv compartido que B acaba de dejar en 0.11.0 queda desalineado | *"el venv compartido hay que volver a alinearlo"* | versión instalada en el venv, tres medidas coincidiendo | Cumplido, con vaivén: los dos llegaron a la vez desde lados opuestos |
| 4 | A va a abrir un ticket que ya existe | *"El ticket ya existe (DATS-804), no lo dupliques"* | ¿se creó un ticket nuevo? | Acción **negativa**, verificable igual |
| 5 | A cree que `master` está rojo por un commit de B; en realidad es el venv local de A | *"master NO está roto: era el venv con core 0.11.0 y el pin en 0.12.0"* | ¿corrige A su creencia y deja de buscar el bug donde no está? | **Creencia corregida**, y B descubre que había caído en lo mismo |

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

**La instrucción de sondeo va en los tres brazos.** Si solo el brazo buzón lleva "consulta este
fichero periódicamente", no se compara entrega contra entrega: se compara interrupción contra
buzón-más-instrucción-explícita-de-sondear, y la instrucción es tratamiento. B recibe la misma
instrucción en todos los brazos; en interrupción y sin canal el fichero simplemente permanece
vacío. Así lo único que varía entre brazos es el mecanismo de entrega.

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
| ~~Silencio~~ | Se parte en dos, ver abajo — la capa 0 mostró que casi nunca es silencio real |
| **Acuse interno con cierre** | B integró el mensaje en su razonamiento y con razón no respondió: no había acción que le tocara |
| **Acuse interno con caída** | B integró el mensaje, había acción que le tocaba, y no la hizo ni lo dijo ← el fallo de julio, §3.5.2 |
| **Acuse sin acción** | B respondió que sí y no lo hizo ← el fallo documentado |
| Acción incorrecta | B hizo algo, pero no lo pedido |
| Deriva | B lo hizo y rompió su propia tarea |

La distinción entre las dos formas de acuse interno es semántica y no admite regex; es el trabajo
pendiente de la capa 0. Sin ella, cualquier "tasa de silencio" mezcla un fallo con un acierto.

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
  merece tanto test como las condiciones. Aquí toma la forma concreta del control positivo de
  §6.1.1.
- Declarar explícitamente el techo: cobertura, no confianza.
- **Nada que ya se publicó vuelve a venderse como hallazgo.** El brazo integrador se presenta como
  calibración y enlaza al artículo de julio; la taxonomía §4.3 y el método de comparación pareada se
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
