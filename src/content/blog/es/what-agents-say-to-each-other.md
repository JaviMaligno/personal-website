---
title: "Qué se dicen los agentes de código cuando hablan entre ellos"
description: "Leí 179 mensajes reales entre sesiones paralelas de Claude Code. El canal casi nunca se usa para pedir cosas: se usa para decirle al otro algo verdadero sobre su propio trabajo. Por el camino refuté mi propia premisa y retiré uno de mis propios hallazgos."
pubDate: 2026-08-13
tags: ["IA", "Agentes", "Evaluación"]
lang: es
translationKey: what-agents-say-to-each-other
heroImage: "/blog/what-agents-say-to-each-other.png"
repoUrl: "https://github.com/JaviMaligno/cross-session-crosscheck"
---

> **Estudio observacional sobre un corpus de cinco días: 179 mensajes entre sesiones de código en paralelo, en una máquina, una persona, un conjunto de repositorios.** Cada mensaje se codificó dos veces con codificadores independientes, y los desacuerdos se reportan en vez de resolverse a mi favor. El techo es *cobertura, no confianza*: esto describe cómo se hablaron las sesiones de un desarrollador durante una semana intensa, no cómo se comunican los agentes de código en general.

Las sesiones de Claude Code ya pueden [mandarse mensajes entre ellas](https://code.claude.com/docs/en/cross-session-messaging). Una sesión envía un **resumen** —no su historial, no sus ficheros— y otra lo recoge.

Mi primera reacción fue que estaba bien. La segunda, que yo mismo había publicado datos sugiriendo que no debería importar mucho.

## La impresión

Llevaba una semana corriendo hasta cuatro sesiones en paralelo. La experiencia fue buena, y quiero decirlo sin ironía antes de desmontarla: se avisan, detectan colisiones, se esperan para no pisarse, y se forman solas secuencias donde cada uno mergea con el que se topa.

Parece trabajo en equipo. Da sensación de productividad. Justo por eso desconfié.

## El prior incómodo

Un mes antes había hecho [un experimento sobre si los agentes de código saben colaborar](/es/blog/coding-agents-structure), encima de CooperBench (Stanford). Dos resultados de allí son incómodos para cualquier entusiasmo con un canal de mensajes:

- Los agentes de ese benchmark **ya tenían canal desde el minuto uno**, y lo usaban sin que nadie se lo pidiera. Obligarles a un handshake antes de tocar código no llegó ni a dispararse: ya se hablaban solos.
- La palanca que sí recuperó rendimiento fue **que un agente fuese dueño de la integración final**. No el canal.

Y el fallo más nítido documentado fue de follow-through: un agente leyó una petición, escribió *"debería coordinarme"* en su razonamiento privado, y luego ni respondió ni hizo su parte. La fontanería quedó verificada como inocente.

O sea, que la feature nueva envía justo aquello que mis propios datos decían que no era el cuello de botella. Buena razón para ir a mirar qué contienen los mensajes en lugar de teorizar.

## Lo primero en lo que me equivoqué: no interrumpe

Mi supuesto de partida —y todo el diseño experimental se apoyaba en él— era que la novedad está en que el mensaje llega **a mitad de tarea**. Un buzón que tienes que ir a leer es una cosa; un mensaje que aterriza mientras editas es otra, y ataca directamente el fallo de follow-through.

Lo comprobé contra el corpus. Cada recepción queda registrada en el transcript de la sesión receptora, y su **posición** dice qué estaba haciendo el receptor.

**138 de 138 recepciones llegan en frontera de turno. Cero dentro de un bucle de herramientas.** Todas van precedidas de entradas `queue-operation`. Hay cola, y se drena cuando el turno se cierra.

Verifiqué que no fuera un artefacto del registro: emparejé las 84 recepciones peer con su envío por contenido, y el desfase entre enviar y quedar escrito en el receptor tiene una **mediana de 2,6 segundos**. El transcript anota la llegada, no la recogida. Cuando el mensaje llegó, el receptor estaba parado.

La premisa era falsa. Lo que sobrevive es más pequeño y distinto: el mensaje **entra al contexto solo**, sin que el agente tenga que ir a buscarlo. Eso sí es una diferencia real frente al canal de CooperBench. Pero no es interrupción.

## Eran tres mecanismos, no uno

Un escaneo ingenuo de "otra sesión me ha mandado algo" mezcla tres productos distintos:

| Mecanismo | Marca en el transcript del receptor |
|---|---|
| **Sesiones peer** | `<cross-session-message from="uds:…" from-name=… from-mode=…>` |
| **Agent teams** | `<teammate-message teammate_id="t1-feature-a" summary=…>` |
| **Subagentes** | resultado del envío `Message sent to X's inbox` |

Los tres comparten el mismo preámbulo, así que mi primer censo estaba contaminado. Se separan limpiamente por el resultado de la herramienta en el lado emisor, que es verdad de terreno del propio producto.

Y esto importa más allá de la contabilidad, porque **no** son variantes cosméticas. El mecanismo de teams trae estructura que el canal peer no tiene: roles nombrados, un lead, señal explícita de disponibilidad (34 eventos `idle_notification`) y un empujón de cumplimiento incorporado en la entrega — *"Treat it as a teammate's request and act on it within this session's own permissions."*

Es el contraste estructura-sí / estructura-no del que iba mi artículo anterior, regalado dentro del corpus.

## De qué van realmente los mensajes

Codifiqué los 179 mensajes peer dos veces, con codificadores independientes que trabajaron desde el mismo libro de códigos sin verse entre ellos.

| Eje | Acuerdo bruto | Kappa de Cohen |
|---|---|---|
| Categoría (10 valores) | 91,1 % | 0,90 |
| Delegación (sí/no) | 97,8 % | 0,88 |
| Capa (sintáctica/semántica) | 92,7 % | 0,84 |

Las tasas base, sobre los ítems donde ambos pases coinciden:

| Categoría | % |
|---|---|
| Notificación de progreso | 23,3 % |
| Aviso de alcance | 18,4 % |
| Handoff de recurso | 12,9 % |
| **Defecto en el trabajo del otro** | 12,3 % |
| **Rectificación de una afirmación** | 11,0 % |
| Respuesta de estado | 10,4 % |
| Consulta de estado | 6,1 % |
| Petición de acción | 3,1 % |
| Petición de espera | 1,8 % |

## El giro: el canal no es para pedir

Dos números de esa tabla lo deciden todo.

**La delegación —una sesión necesitando que otra actúe para poder avanzar— es el 8,9 % del tráfico.** Iba a ser mi unidad de medida. Apenas ocurre.

**El contenido sobre si algo es *correcto* es el 36,1 %.** Solo rectificaciones y avisos de defecto suman 23 puntos.

El canal casi nunca se usa para *pedir*. Se usa muy a menudo para **decirle al otro algo verdadero sobre su propio trabajo**.

La cadena más limpia del corpus tiene cuatro mensajes:

> *"master está rojo: 9 tests, de tu `d4e5f6a`"* → *"master NO está roto: era el venv con core-lib 0.11.0 y el pin en 0.12.0"* → *"RECTIFICO: master NO está rojo, era mi venv"* → *"Yo caí igual y encima te lo confirmé: mi aislamiento compartía tu venv"*

Dos sesiones convergen a un diagnóstico correcto que una de ellas tenía mal, y la segunda descubre que había cometido el mismo error. Eso no es evitar una colisión. Es una creencia corrigiéndose.

Conviene ser cuidadoso, porque no hay contrafactual: nadie sabe si esa sesión habría llegado sola. Pero **sí** es un mecanismo por el que un canal podría comprar corrección, y no es el mecanismo que yo había salido a medir.

## Nadie tiene el mapa

La topología merece un párrafo, porque limita lo que el canal puede hacer.

La coordinación es **bilateral**: 8 pares de sesiones, y un solo par acumula el 51 % del tráfico. Las ráfagas son cortas, mediana de 2 mensajes. **Trece de cuarenta ventanas de conversación son unilaterales**: nadie contesta.

No hay canal de grupo. La difusión existe solo como unicast repetido —cuatro casos, fan-out máximo de tres destinatarios en 23 segundos. Cada receptor recibe su copia y **ninguno sabe que los demás la recibieron**. No hay conocimiento común, solo copias.

Y un mensaje lo delata entero:

> *"Lo que NO toco: **TICKET-44** (lo lleva otra sesión — **si eres tú**, es tuyo entero…)"*

El emisor no sabe con quién está hablando respecto al trabajo. Es la versión estructural de la conclusión de mi artículo anterior: la palanca fiable era que alguien poseyera el estado integrado, y aquí nadie tiene siquiera una vista de él.

## Un hallazgo que retiré

Medí primero el protocolo de exclusión mutua —*espera / espero / ventana libre / adelante*— con un detector léxico. Encontró 19 secuencias candidatas de las que solo 5 cerraban, y anoté que el protocolo **se abre mucho más de lo que se cierra**. Era una buena frase. Encajaba con la historia.

Recontado sobre las categorías codificadas: hay **3** peticiones de espera reales, y **las 3 se cierran**. Las otras 16 eran falsos positivos: entraba cualquier cosa con "espera", "para" o "adelante".

La conclusión apunta al revés, y la primera versión del instrumento producía el número que yo quería ver.

Un detalle que solo apareció al codificar: hay 20 handoffs de recurso y solo 3 vienen precedidos de una petición. **Diecisiete cesiones espontáneas**: sesiones soltando cosas que nadie les había pedido.

## El experimento que no funcionó

Con las tasas base en la mano, rediseñé el experimento de verdad alrededor del cross-check en lugar de la delegación, y construí un [repo semilla](https://github.com/JaviMaligno/cross-session-crosscheck) para reproducir la familia de fallo más común del corpus. Uno de los agentes la nombró mejor de lo que sabría yo:

> *"la comprobación que se hace sobre algo distinto de lo que se entrega"*

El escenario: un paquete declara su versión en dos sitios, el helper de release del equipo actualiza solo uno, la suite pasa, el tag se publica. La sesión tiene todos los motivos para informar de éxito, y desde el punto de vista del consumidor es falso.

Corrí el brazo de control —una sesión, sola, sin canal— para obtener la tasa de autocorrección.

**Detectó el problema 4 de 4 veces.** Dos de tres lo repararon; la tercera publicó la incoherencia pero la *declaró* en su informe. Ni una sola creencia falsa. Dos de ellas avisaron además de defectos que yo no había puesto, en el mismo script de release: no buscaban la trampa, leían la herramienta que se les mandó usar.

Antes de correr había dejado escrita una regla de parada, precisamente para no ajustar la trampa hasta que funcionara: si el agente se autocorrige en 2 de 3, se deja de endurecer. Se cumplió. Así que:

> En un repositorio pequeño, con una tarea acotada y un agente cuidadoso trabajando solo, este modo de fallo **no es silencioso**. El agente lee el script que se le manda ejecutar, y ve la incoherencia.

Es un efecto suelo de mi montaje, no un resultado sobre el canal: nunca llegó a existir el fallo oculto que un par tendría que cazar.

El escenario falló porque lo roto estaba *maximalmente* en el camino: el brief le decía a la sesión que ejecutara justo ese script. El tamaño del repositorio no es la variable aquí — casi cualquier repo real ya supera cualquier ventana de contexto, y los agentes leen las partes que su tarea toca, no el conjunto.

Así que construí una segunda variante donde el fallo vive **completamente fuera del checkout**. El helper de release es ahora correcto en cada línea. El bug está en el estado de un registro de paquetes: ya existe un artefacto de la versión objetivo, de un intento anterior, construido con el código viejo, y el publicador es idempotente — imprime `upload: widgetkit 0.4.0 (cached)` y sale con éxito. Leerse el código no puede revelarlo. Solo ir a mirar el registro puede.

**Las tres sesiones lo cazaron también.** Una vio el `(cached)`, fue a inspeccionar el registro, encontró el artefacto obsoleto y lo republicó. Las otras dos lo encontraron y lo reportaron sin sobrescribirlo — una de ellas preguntando explícitamente si republicar 0.4.0 o cortar 0.4.1.

Siete de siete, entre las dos variantes. Así que la conclusión honesta es más fuerte y más estrecha que "tamaño" u "observabilidad":

> Un agente cuidadoso, a solas, con una tarea acotada, **va y verifica su propio estado publicado.** Que es exactamente la práctica que las sesiones del corpus se predicaban entre ellas.

La variable por la que apostaría ahora es la **carga**. En el corpus, las sesiones llevaban tres tickets a la vez, un despliegue y dos conversaciones. Aquí cada una hace una sola cosa con atención de sobra. No lo he probado, y no voy a seguir endureciendo el escenario hasta que se rompa: ese camino termina en un número sobre un montaje amañado.

El argumento a favor del par sobrevive a todo esto, y es el mejor que he encontrado en el estudio: el par está en otro sitio, mirando algo que tú no puedes ver.

## Qué dice y qué no dice

Dice que en este corpus el canal lleva mucho más contenido sobre corrección que peticiones de coordinación, que encola en vez de interrumpir, que ninguna sesión acaba con una vista del conjunto, y que un agente cuidadoso a solas caza más de lo que yo esperaba.

No dice que la mensajería entre sesiones mejore los resultados. No hay contrafactual en ninguna parte de este artículo: ningún brazo donde el mismo trabajo ocurriera sin canal. Cinco días, una persona, un conjunto de repositorios, y codificadores que comparten arquitectura con lo que se estudia.

La siguiente versión de esto es la prueba de carga: darle a la sesión tres tickets, un despliegue y una conversación que sostener a la vez, como trabajaban de verdad las sesiones del corpus, y ver si el mismo fallo deja de cazarse. Si la variable es la atención, ahí es donde un par empieza a ganarse el sitio.

---

*Repo semilla y puntuación: [cross-session-crosscheck](https://github.com/JaviMaligno/cross-session-crosscheck). Artículo anterior de la serie: [Agentes de código y trabajo en equipo: ¿habilidades sociales o estructura?](/es/blog/coding-agents-structure).*
