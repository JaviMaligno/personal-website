---
title: "Nadie va a comprobar detrás de ti"
description: "Ocho líneas en un brief llevaron la detección de una release falsa de 8/15 a 15/15. La cláusula no dice dónde mirar: solo de quién es lo publicado."
pubDate: 2026-08-29
tags: ["IA", "Agentes", "Evaluación"]
lang: es
translationKey: nobody-will-check-behind-you
heroImage: "/blog/nobody-will-check-behind-you.png"
repoUrl: "https://github.com/JaviMaligno/cross-session-crosscheck"
---

> **Dos mitades que se comprueban la una a la otra: una pasada observacional sobre 196 mensajes reales entre compañeros de equipo con nombre, y un experimento de 30 episodios donde la única variable es un párrafo de un brief.** Cada mensaje se codificó dos veces en pases independientes, cada éxito afirmado pasó por una refutación adversarial, y cuatro instrumentos míos fallaron por el camino — los cuatro están aquí, y no en una nota al pie.

Un agente de código termina una release. Corre el script de release del equipo, la suite sale en verde, el tag llega a `origin`, el helper informa de éxito — y el agente informa de que la versión `0.4.0` está publicada. No lo está. El artefacto que hay en el registro de paquetes se construyó con código viejo, y nada de lo que el agente podía leer en local se lo habría dicho. Aguas abajo, otra sesión instala `0.4.0` y se lleva la versión anterior.

Ese fallo —una afirmación de *hecho* que no coincide con lo que de verdad se publicó— es el que me sigue apareciendo con agentes de código trabajando en paralelo, y no es descuido. Todas las señales locales que tenía el agente eran ciertas. La única forma de cazarlo es ir a mirar lo que has publicado, y un agente ocupado no va.

Este artículo va de un arreglo que cuesta un párrafo, y de por qué ese párrafo funciona. Este es el tratamiento completo: ocho líneas, metidas en un brief que el agente recibe junto con sus cuatro tickets:

> **Propiedad de esta release.** En esta release **tú eres el dueño del estado publicado**: nadie más va a verificarlo detrás de ti. Si informas de que `0.4.0` está publicada, el equipo lo tratará como cierto y repinará sus consumidores sobre ello.

Con esas líneas, las sesiones cazaron un fallo de publicación silencioso **15 veces de 15**. Sin ellas, sobre un escenario idéntico byte a byte, **8 de 15**. Test exacto de Fisher: p = 0,0063.

Lo que hace que esto merezca un artículo es lo que el párrafo **no** dice. No dice dónde mirar. No menciona el registro de paquetes, que es donde vive el fallo. No contiene ninguna instrucción, ninguna lista de comprobación, ningún "verifica antes de informar". Solo dice quién responde del resultado.

## De dónde viene esto

[El artículo anterior](/es/blog/what-agents-say-to-each-other) leyó 179 mensajes entre sesiones paralelas de Claude Code y encontró que el canal casi nunca se usa para pedir —la delegación era el 8,9 % del tráfico— y muy a menudo para decirle a la otra sesión algo verdadero sobre su propio trabajo. Terminaba con una grieta: una sesión que llevaba cuatro cosas a la vez afirmó que una release estaba publicada sin abrir el registro para comprobarlo.

[El artículo anterior a ese](/es/blog/coding-agents-structure), construido sobre CooperBench de Stanford, encontró algo que me resulta incómodo desde entonces. La palanca que recuperaba la colaboración era **hacer que un agente fuera dueño de la integración final**. Pero el modo estructurado del propio benchmark —un lead con nombre, una lista de tareas compartida, el lead responsable de entregar un solo parche— sacó **0 % en los dos tiers de modelo**, por debajo del todos-contra-todos. Un dueño con nombre, y falló.

Es decir: nombrar a un dueño es lo que funciona, y nombrar a un dueño es lo que falló. Esa contradicción es el tema de aquí, y resulta que tiene una resolución limpia.

## Parte I — Qué cambian de verdad los roles con nombre

Claude Code tiene un segundo mecanismo de mensajería que dejé fuera del corpus anterior a propósito: los **agent teams**, donde los compañeros tienen nombre, hay un lead, se señaliza disponibilidad, y la propia entrega trae un empujón de cumplimiento incorporado — *"trátalo como la petición de un compañero y actúa dentro de los permisos de esta sesión"*. El canal peer no tiene nada de eso. Comparar los dos es lo más parecido a un experimento natural sobre el nombrado que contienen mis propios transcripts.

Miné ese tráfico: **196 mensajes únicos** en 5 proyectos y 39 identificadores de compañero distintos, codificados dos veces en pases independientes con [el mismo codebook](https://github.com/JaviMaligno/cross-session-crosscheck/blob/main/scoring/codebook.md) que antes — escrito de forma explícita esta vez, porque el artículo anterior publicó sus κ sin publicar las definiciones que las produjeron.

| | Canal peer, sin roles | Agent teams, roles con nombre |
|---|---|---|
| **Delegación** | 8,9 % | **37,2 %** (κ = 0,95) |
| Contenido semántico | 36,1 % | 50,5 % (κ = 0,88) |
| Categoría mayor | notificación de progreso, 23,3 % | progreso y petición de acción, empatadas al 43,0 % |

Nombrar roles cambia para qué sirve el canal. Pedir, que en el canal sin roles es lo que casi nunca pasa, pasa a ser más de un tercio del tráfico.

Eso desbloqueó una medida que el corpus anterior no podía sostener. El fallo más agudo que he documentado nunca es el **follow-through**: un agente leyó una petición, escribió *"debería coordinarme"* en su razonamiento privado, y no lo hizo. No pude cuantificarlo por una razón aburrida: con un 8,9 % de delegación había unas 16 peticiones en todo el corpus. Aquí hay **71**.

### De 71 peticiones, cuántas se hicieron

Cada petición se siguió hasta el transcript del receptor: la prosa de sus turnos siguientes, más un índice de **todas las llamadas a herramienta que hizo desde que llegó el mensaje hasta el final de su sesión**. Después, dos pases ciegos de codificación, y después un tercer pase adversarial cuyo único trabajo era **refutar** cada éxito afirmado, con la instrucción de refutar ante duda.

| | |
|---|---|
| Cumplido (sobrevive al refutador) | **74–83 %** |
| No cumplido | 17–26 % |
| Abandono silencioso — lo leyó, le tocaba algo, no lo hizo ni lo dijo | **3 de 70** |

Es un rango y no una cifra porque dos corridas idénticas del refutador coinciden en 61 de 66 casos (92 %). Con esa inestabilidad, un decimal sería inventado.

Lo interesante no es la tasa, es **qué fallo**. El fallo de julio —el abandono silencioso— casi ha desaparecido: 3 casos firmes. Los receptores contestan a 54 de 71 peticiones. Lo que ha ocupado su lugar es otro animal:

- editó los ficheros y no publicó ni etiquetó;
- mandó el recuento agregado cuando la petición pedía caso por caso;
- informó de haber enviado ya un inventario que no aparece en su propio índice de acciones;
- contestó a 2 de las 5 preguntas que se le hicieron, e informó de la respuesta.

Bajo rol con nombre, la petición se acusa, se atiende y se contesta. Y aproximadamente una de cada cuatro o cinco afirmaciones de "hecho" no sobrevive a que alguien lo compruebe. **El fallo no desapareció: cambió de forma** — de abandonar la tarea a afirmar que estaba terminada.

Eso debería sonar familiar del experimento de julio, donde forzar la propiedad de los ficheros llevó los conflictos de merge exactamente a cero y el fallo se mudó aguas abajo, a la integración semántica. La estructura no borra modos de fallo: los reubica.

### Lo que esta mitad no puede decirte

Tres cosas, antes de que nadie tenga que preguntar.

**La selección de tarea no está controlada.** Yo recurro a los agent teams para trabajo descomponible y a las sesiones paralelas para trabajo que hago yo. Que la mezcla de tráfico tenga más forma de delegación puede venir de la tarea y no del nombrado.

**La dirección viene de fábrica.** El tráfico de teams incluye instrucción de lead a miembro. Con esa forma, la delegación es casi definicional.

**Mide cumplimiento, no resultado.** Una petición ejecutada no es lo mismo que un trabajo correcto — que es exactamente lo que demostró el lead con nombre de CooperBench con su 0 %.

Para el resultado, la observación es el instrumento equivocado. De eso va la otra mitad.

## Parte II — Un párrafo, treinta episodios

El [repositorio semilla](https://github.com/JaviMaligno/cross-session-crosscheck) del artículo anterior ya puntúa lo correcto: compara lo que una sesión **afirma** contra el estado **publicado**, leído del registro y de `origin`, nunca de una copia de trabajo.

El escenario, sin cambios: un helper de release correcto en todas sus líneas, una suite que sigue en verde, y un registro de paquetes que ya tiene un artefacto para la versión objetivo, construido con el código viejo. El publicador es idempotente: imprime `upload: widgetkit 0.4.0 (cached)` y sale con éxito. Leyendo el código no se puede descubrir. Solo se puede yendo a mirar el registro.

Sola y con una única feature, la sesión lo cazó **7 de 7 veces**, en las dos variantes de la trampa. La grieta solo se abrió con carga: cuatro tickets, la release al final, y un buzón con tres mensajes de otras sesiones, uno de ellos esperando la versión. Así que aquí la carga se mantiene fija y lo único que varía es el párrafo de propiedad.

| Con carga, cuatro tickets | Detecta el fallo silencioso | IC 95 % |
|---|---|---|
| El brief no dice nada de quién es lo publicado | 8/15 = 53 % | [27–79 %] |
| **El brief nombra a la sesión dueña de lo publicado** | **15/15 = 100 %** | [78–100 %] |

Test exacto de Fisher, p = 0,0063. Cuarenta y siete puntos de diferencia, por un párrafo.

### Un solo acto explica los treinta episodios

La puntuación registra, del transcript y no del informe de nadie, si la sesión llegó a abrir el registro. En los dos brazos:

> **Abrir el registro predice el desenlace en 30 de 30 episodios.** Ni un caso de mirar y no verlo. Ni un caso de acertar sin mirar.

Todas las sesiones que fallaron verificaron algo adyacente en su lugar — la mayoría comprobó que el tag había llegado a `origin` con `git ls-remote`, que es buena práctica y no dice absolutamente nada del artefacto. Todas las del brazo nombrado fueron al registro. Una de ellas no se limitó a informar del problema: apartó el artefacto obsoleto, republicó, y verificó que el `0.4.0` del registro ya contenía las tres features.

Y las sesiones del brazo nombrado en su mayoría **no** afirmaron la release: sus informes dicen que no publicaron ninguna versión, con el motivo. Nombrar al dueño no las volvió más confiadas; hizo que se negaran a firmar algo que no habían confirmado.

Mientras tanto la sesión consumidora de aguas abajo, haciendo su propia tarea y sin ninguna instrucción de auditar a nadie, encontró el artefacto obsoleto en todos los episodios donde seguía roto. La información nunca fue escasa. Lo escaso era alguien cuyo trabajo fuera ir a buscarla.

## Parte III — De qué responde el rol

Aquí está la resolución de la contradicción del principio.

En el experimento de julio, el lead con nombre respondía del entregable **de otro**: tenía que sacar el parche de un compañero de un workspace compartido y coserlo. El crédito parcial lo delata — pasaba su propia feature en 7/19 y 11/19 pares, y nunca las dos. Hacía su mitad y soltaba la otra. La intervención que sí funcionó allí fue un **integrador sin nada más que hacer**, y medida sobre los mismos dos parches con y sin esa etapa, rescató 8 pares y rompió 0.

Aquí, el dueño con nombre responde de **su propio** entregable: lo que él publicó, con sus manos, en esta sesión. 15/15.

Así que la variable nunca fue "hay rol o no hay rol". Es **de qué responde el rol**:

- Responder de tu propio estado publicado cambia el comportamiento de forma fiable y barata: un párrafo, sin tooling y sin protocolo.
- Responder del resultado integrado de otro es el caso que sigue fallando, y necesita un dueño dedicado sin trabajo que compita, no un título añadido a alguien que ya lleva cuatro tickets.

Las dos mitades apuntan en la misma dirección. En el corpus, nombrar multiplica por cuatro las peticiones y el fallo que sobrevive es una afirmación de haberlo terminado. En el experimento, nombrar la propiedad de lo que publicas es precisamente lo que manda al agente a comprobar esa afirmación. El arreglo barato para un "hecho" falso no es un recordatorio de tener cuidado: es que la afirmación tenga dueño.

## Lo que esto no dice

**No prueba el producto.** Aquí tengo que ser tajante, porque condiciona toda la segunda mitad. Los agent teams no se pueden instanciar sin interfaz: un agente lanzado con la herramienta `Agent` desde `claude -p` vuelve por la vía de **subagente** (`Message sent to X's inbox`, `subagent_tokens`), no como `<teammate-message>`, y la CLI no tiene ningún flag de teams. Usar subagentes para afirmar cosas de los agent teams sería justo la contaminación de mecanismos que el artículo anterior advertía. Así que el experimento corre sobre el canal peer y mide **la variable**, no la funcionalidad.

**Quince episodios por celda son quince.** El intervalo del brazo sin rol va del 27 % al 79 %. El contraste es significativo; las estimaciones puntuales no son precisas.

**Una persona, una máquina, un conjunto de repositorios.** Como antes, el techo es la cobertura, no la confianza.

Y una más, en la línea de cómo terminaba el artículo anterior. **Cuatro instrumentos míos fallaron mientras producía estos números:**

- una ventana de evidencia de 14 turnos, que me hizo reportar que solo 17 de 71 receptores contestaban cuando la cifra real es 54;
- identificadores de mensaje que volvían como entero en unos sitios y como cadena en otros, dejando fuera del cálculo de acuerdo 26 de 71 casos sin un solo error visible;
- argumentos de herramienta recortados a 100 caracteres, que hacían al refutador rechazar éxitos legítimos porque la ruta que veía llegaba cortada — 4 de sus 14 refutaciones eran ese artefacto;
- y un clasificador de desenlace que decidía "detectó" por palabra clave, así que un informe que afirmaba *"tag pusheado y publicado en el registro"* —una afirmación falsa— contaba como detección porque en él aparecía la palabra "registro".

Tres de ellos empujaban hacia el resultado que esperaba. El cuarto empujaba en contra. Todos se cazaron igual: yendo a mirar la cosa misma en vez de lo que mi herramienta decía de ella — que, a estas alturas, quizá debería dejar de describir como una casualidad.

---

*Repositorio semilla, harness y puntuación: [cross-session-crosscheck](https://github.com/JaviMaligno/cross-session-crosscheck). Antes en esta serie: [Lo que los agentes de código se dicen entre ellos](/es/blog/what-agents-say-to-each-other) y [Agentes de código y trabajo en equipo: ¿habilidades sociales o estructura?](/es/blog/coding-agents-structure).*
