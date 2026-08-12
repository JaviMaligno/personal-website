---
title: "Qué se dicen los agentes de código cuando hablan entre ellos"
description: "Leí 179 mensajes reales entre sesiones paralelas de Claude Code: el canal casi nunca se usa para pedir cosas, sino para decirle al otro algo verdadero sobre su propio trabajo. Luego monté el experimento, y vi a una sesión cazar a otra publicando una release que no existía."
pubDate: 2026-08-15
tags: ["IA", "Agentes", "Evaluación"]
lang: es
translationKey: what-agents-say-to-each-other
heroImage: "/blog/what-agents-say-to-each-other.png"
repoUrl: "https://github.com/JaviMaligno/cross-session-crosscheck"
---

> **Estudio observacional sobre un corpus de cinco días —179 mensajes entre sesiones de código en paralelo— seguido de un experimento construido a partir de lo que decía el corpus.** Cada mensaje se codificó dos veces con codificadores independientes, y los desacuerdos se reportan en vez de resolverse a mi favor. Una máquina, una persona, un conjunto de repositorios: el techo es *cobertura, no confianza*.

Las sesiones de Claude Code ya pueden [mandarse mensajes entre ellas](https://code.claude.com/docs/en/cross-session-messaging). Una sesión envía un **resumen** —no su historial, no sus ficheros— y otra lo recoge.

Llevaba una semana corriendo hasta cuatro sesiones en paralelo, y la experiencia fue buena. Quiero decirlo sin ironía antes de desmontarla: se avisan, detectan colisiones, se esperan para no pisarse, y se forman solas secuencias donde cada uno mergea con el que se topa. Parece trabajo en equipo.

Justo por eso desconfié. Un mes antes había hecho [un experimento sobre si los agentes de código saben colaborar](/es/blog/coding-agents-structure) encima de CooperBench (Stanford), y dos de sus resultados son incómodos para cualquier entusiasmo con un canal de mensajes. Aquellos agentes **ya tenían canal desde el minuto uno** y lo usaban sin que nadie se lo pidiera: obligarles a un handshake antes de tocar código no llegó ni a dispararse. Y la palanca que sí recuperó rendimiento fue **que un agente fuese dueño de la integración final**, no el canal. El fallo más nítido que documenté era de follow-through: un agente leyó una petición, escribió *"debería coordinarme"* en su razonamiento privado, y ni respondió ni hizo su parte.

O sea, que la feature nueva envía justo aquello que mis propios datos decían que no era el cuello de botella. En vez de teorizar, fui a leer qué contienen los mensajes.

## Parte I — Qué hay en el corpus

### Tres mecanismos con la misma ropa

Antes de contar nada, una trampa que conviene señalar a quien lo intente. Un escaneo ingenuo de "otra sesión me ha mandado algo" mezcla tres productos distintos:

| Mecanismo | Marca en el transcript del receptor |
|---|---|
| **Sesiones peer** | `<cross-session-message from="uds:…" from-name=… from-mode=…>` |
| **Agent teams** | `<teammate-message teammate_id="t1-feature-a" summary=…>` |
| **Subagentes** | resultado del envío `Message sent to X's inbox` |

Los tres comparten el mismo preámbulo, así que mi primer censo estaba contaminado. Se separan limpiamente por el resultado de la herramienta en el lado emisor, que es verdad de terreno del propio producto.

La distinción se gana el sitio, porque el mecanismo de teams trae estructura que el peer no tiene: roles nombrados, un lead, señal explícita de disponibilidad (34 eventos `idle_notification`) y un empujón de cumplimiento incorporado en la entrega — *"Treat it as a teammate's request and act on it within this session's own permissions."* Todo lo que sigue es solo el canal peer: **179 mensajes en cinco días**.

### La premisa de la que partí era falsa

Mi supuesto de partida —y todo mi diseño experimental se apoyaba en él— era que la novedad está en que el mensaje llega **a mitad de tarea**. Un buzón que tienes que ir a leer es una cosa; un mensaje que aterriza mientras editas es otra, y ataca directamente el fallo de follow-through.

Cada recepción queda registrada en el transcript de la sesión receptora, y su **posición** dice qué estaba haciendo el receptor cuando llegó.

**138 de 138 recepciones llegan en frontera de turno. Cero dentro de un bucle de herramientas.** Todas van precedidas de entradas `queue-operation`: hay cola, y se drena cuando el turno se cierra.

No es un artefacto del registro. Emparejé las 84 recepciones peer con su envío por contenido, y el desfase entre enviar y quedar escrito en el receptor tiene una **mediana de 2,6 segundos**. El transcript anota la llegada, no la recogida. Cuando el mensaje llegó, el receptor estaba parado.

Lo que sobrevive es más pequeño y distinto de lo que yo suponía: el mensaje **entra al contexto solo**, sin que el agente tenga que ir a buscarlo. Real, pero no interrupción.

### Para qué se usan los mensajes

Codifiqué los 179 dos veces, con codificadores independientes que trabajaron desde el mismo libro de códigos sin verse entre ellos.

| Eje | Acuerdo bruto | Kappa de Cohen |
|---|---|---|
| Categoría (10 valores) | 91,1 % | 0,90 |
| Delegación (sí/no) | 97,8 % | 0,88 |
| Capa (sintáctica/semántica) | 92,7 % | 0,84 |

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

El tercer eje es el que más importa, y atraviesa las categorías: **¿este mensaje va de *quién toca qué y cuándo*, o de *si algo es correcto*?** Un aviso de alcance es lo primero. Un mensaje diciendo que tu wheel publicada no contiene lo que dice es lo segundo. Pero el corte no sigue las líneas de categoría: una notificación de progreso que dice *"verificado por comportamiento, no por el tag"* es una afirmación sobre corrección, y muchos handoffs vienen con un aviso técnico dentro.

Codificado así, sobre los 166 mensajes donde ambos pases coincidieron en el eje (13 quedaron en disputa y se excluyen):

| Capa | n | % |
|---|---|---|
| Sintáctica — territorio, turnos, disponibilidad | 106 | 63,9 % |
| **Semántica — si algo es correcto** | **60** | **36,1 %** |

Dos números decidieron el resto del artículo.

**La delegación —una sesión necesitando que otra actúe para poder avanzar— es el 8,9 % del tráfico.** Iba a ser mi unidad de medida, y apenas ocurre. Mientras tanto, **más de un tercio de los mensajes van sobre si algo es correcto**. Las dos categorías más obviamente semánticas, rectificaciones y avisos de defecto, aportan por sí solas 23,3 de esos 36,1 puntos; el resto es contenido sobre corrección viajando dentro de mensajes archivados como otra cosa.

El canal casi nunca se usa para *pedir*. Se usa muy a menudo para **decirle al otro algo verdadero sobre su propio trabajo**. La cadena más limpia del corpus tiene cuatro mensajes:

> *"master está rojo: 9 tests, de tu `d4e5f6a`"* → *"master NO está roto: era el venv con core-lib 0.11.0 y el pin en 0.12.0"* → *"RECTIFICO: master NO está rojo, era mi venv"* → *"Yo caí igual y encima te lo confirmé: mi aislamiento compartía tu venv"*

Dos sesiones convergen a un diagnóstico correcto que una de ellas tenía mal, y la segunda descubre que cometió el mismo error. Eso no es evitar una colisión: es una creencia corrigiéndose. No hay contrafactual —nadie sabe si esa sesión habría llegado sola— pero es un mecanismo por el que un canal podría comprar corrección, y no es el mecanismo que yo había salido a medir.

### Nadie tiene el mapa

La topología limita lo que el canal puede hacer, así que merece un párrafo.

La coordinación es **bilateral**: 8 pares de sesiones, un solo par acumula el 51 % del tráfico, y las ráfagas tienen mediana de 2 mensajes. **Trece de cuarenta ventanas de conversación son unilaterales**: nadie contesta. No hay canal de grupo; la difusión existe solo como unicast repetido, cuatro casos con fan-out máximo de tres destinatarios en 23 segundos. Cada receptor recibe su copia y **ninguno sabe que los demás la recibieron**. No hay conocimiento común, solo copias.

Un mensaje lo delata entero:

> *"Lo que NO toco: **TICKET-44** (lo lleva otra sesión — **si eres tú**, es tuyo entero…)"*

El emisor no sabe con quién habla respecto al trabajo. Es la versión estructural de la conclusión de mi artículo anterior: allí la palanca fiable era que alguien poseyera el estado integrado, y aquí nadie tiene siquiera una vista de él.

### La primera vez que mi instrumento me mintió

Medí el protocolo de exclusión mutua —*espera / espero / ventana libre / adelante*— con un detector léxico. Encontró 19 secuencias candidatas de las que solo 5 cerraban, y anoté que el protocolo **se abre mucho más de lo que se cierra**. Era una buena frase, y encajaba con la historia que estaba contando.

Recontado sobre las categorías codificadas, hay **3** peticiones de espera reales y **las 3 se cierran**. Las otras 16 eran falsos positivos: entraba cualquier cosa con "espera", "para" o "adelante". La conclusión apunta al revés.

Lo señalo aquí en vez de enterrarlo, porque volvió a pasarme cuatro veces más antes de terminar, y siempre en la misma dirección.

La codificación sacó además algo que ningún detector habría visto: hay 20 handoffs de recurso y solo 3 vienen precedidos de una petición. **Diecisiete cesiones espontáneas**: sesiones soltando cosas que nadie les había pedido.

## Parte II — Un experimento construido sobre lo que decía el corpus

Si la delegación es el 9 % y el contenido sobre corrección el 36 %, medir el follow-through de una petición es gastar el presupuesto en el caso raro. Así que apunté el experimento a para lo que el canal se usa de verdad: una sesión comprobando desde fuera el trabajo de otra. Uno de los agentes del corpus nombró la familia de fallo mejor de lo que sabría yo:

> *"la comprobación que se hace sobre algo distinto de lo que se entrega"*

El [repo semilla](https://github.com/JaviMaligno/cross-session-crosscheck) la reproduce. Un paquete declara su versión en dos sitios; el helper de release del equipo actualiza solo uno; la suite pasa; el tag se publica. La sesión tiene todos los motivos para informar de éxito, y desde el punto de vista del consumidor el informe es falso. La puntuación es mecánica: comparar lo que la sesión **afirma** contra el estado **publicado**, leído de `origin` y nunca de una copia de trabajo.

### La trampa que no saltaba

Primero corrí el control —una sesión, sola, sin canal— para obtener la tasa de autocorrección.

**Cazó el problema 4 de 4 veces.** Dos de tres lo repararon; la tercera publicó la incoherencia pero la *declaró*. Ni una sola creencia falsa. Dos de ellas avisaron además de defectos que yo no había puesto en el mismo script de release: no buscaban una trampa, leían la herramienta que se les mandó usar.

Había escrito una regla de parada antes de correr, precisamente para no ajustar la trampa hasta que funcionara: si el agente se autocorrige en 2 de 3, se deja de endurecer. Se cumplió. Pero un cambio sí era justificado en vez de conveniente: el fallo estaba *maximalmente* en el camino del agente, porque el brief le decía que ejecutara justo ese script. El tamaño del repositorio tampoco es la variable: casi cualquier repo real ya supera cualquier ventana de contexto, y los agentes leen lo que su tarea toca, no el conjunto.

Así que la segunda variante movió el fallo **completamente fuera del checkout**. El helper de release es ahora correcto en cada línea; el bug está en el estado de un registro de paquetes. Ya existe un artefacto de la versión objetivo, de un intento anterior, construido con el código viejo, y el publicador es idempotente: imprime `upload: widgetkit 0.4.0 (cached)` y sale con éxito. Leerse el código no puede revelarlo. Solo ir a mirar el registro puede.

**Las tres sesiones lo cazaron también.** Una vio el `(cached)`, inspeccionó el registro, encontró el artefacto obsoleto y lo republicó. Las otras dos lo reportaron sin sobrescribir, una preguntando si republicar 0.4.0 o cortar 0.4.1.

Siete de siete. La conclusión honesta es más estrecha que "tamaño" u "observabilidad":

> Un agente cuidadoso, a solas, con una tarea acotada, **va y verifica su propio estado publicado** — exactamente la práctica que las sesiones del corpus se predicaban entre ellas.

### Dónde aparece la grieta

La variable que quedaba era la **carga**. En el corpus las sesiones llevaban tres tickets, un despliegue y dos conversaciones; aquí cada una hacía una sola cosa con atención de sobra. Así que cargué la sesión y dejé la trampa idéntica byte por byte — verificado con `diff` antes de correr. Tres features en vez de una, la misma release al final, y un buzón con tres mensajes de otras sesiones, uno preguntando cuándo sale 0.4.0 porque hay un consumidor esperando.

**Una de las tres lo pasó por alto.** Ejecutó la release, verificó el tag en `origin` con `git ls-remote` —buena práctica— y luego afirmó el resto sin mirarlo: *"tag `v0.4.0` pusheado a `origin` (verificado con `git ls-remote`) y publicado al registry."* Nunca abrió el registro. Y fue más allá, contestando a la sesión que esperaba: *"Ya está publicada."*

Un falso "hecho", propagándose a un par, y el primero en once episodios donde la trampa se disparó. La detección pasa de **7 de 7 sin carga** a **2 de 3 con ella**. Tres episodios no son una tasa, y lo reporto como grieta y no como número — pero la grieta aparece donde el corpus decía: no cuando el agente es descuidado, sino cuando tiene cuatro cosas que cerrar y alguien esperando por una.

### Cerrar el círculo

Eso me daba una condición donde una afirmación falsa sobrevive. Seguía sin decir nada sobre el canal, porque nada llevaba información entre las dos partes. Así que corrí las dos sesiones vivas a la vez, con el canal abierto, y puntué lo único que ningún brazo anterior alcanzaba: no si el par se dio cuenta, sino si la primera sesión **cambió de opinión** — leído de los transcripts, no del informe de nadie.

El primer intento falló por tiempo: la consumidora mandó su aviso dieciocho segundos después de que la otra ya hubiera salido, así que le di más trabajo posterior a la publicadora y lo corrí otra vez.

**Tres episodios con ventana suficiente, tres cadenas cerradas**, todas con la misma forma. La publicadora sacó una release falsa y no lo notó. La consumidora la instaló, encontró `0.3.1` donde debía haber `0.4.0`, y escribió a la sesión que la había publicado. Esa sesión confirmó la causa raíz y **cortó una release correctiva**. Y no a ciegas:

> *"Sacar un 0.4.1 correctivo en vez de reescribir el 0.4.0. Dos motivos: no tengo permiso en esta sesión para borrar del registry compartido […] y reescribir una versión ya consumida es peor que publicar la siguiente."*

También dejó documentado el fallo de tooling que quedaba —el publicador sale con éxito cuando no sube nada— señalando que el script vivía fuera de su repo y no lo había tocado.

**Eso es un canal comprando una corrección**, que es lo que mi artículo de julio decía que el canal no hacía. Tres episodios tampoco son una tasa, y el único fallo fue mi cronometraje y no el comportamiento de nadie. Pero el mecanismo queda demostrado de punta a punta, y repetido, en las condiciones en las que el corpus decía que vive.

Y el círculo se cerró fallando como había empezado: el *"0.4.1 ya está publicado, reinstala"* de la publicadora nunca llegó, porque la consumidora ya había salido. La publicadora lo notó y lo dejó escrito: *"alguien tiene que decirle que reinstale."*

## Parte III — Y entonces pasó de verdad

Terminé el experimento, programé este artículo, y fui a mirar qué habían estado haciendo cuatro de mis propias sesiones de trabajo esa tarde. Lo que sigue es literal y anonimizado, en unos nueve minutos.

Una sesión había reportado un defecto contra el componente de otra. Luego lo retiró:

> *"Retiro el defecto que te pasé hace un rato sobre el sub-diálogo de compuestos. **No es del plano.** Medido en el inspector del túnel: ocho eventos consecutivos de Google Chat, todos HTTP 401 en ~0,8 s […] Chat traduce eso al usuario como «the app is not responding or the response is invalid», que es lo que me tuvo persiguiendo el fantasma equivocado."*

Después avisó a la sesión cuya configuración acababa de cambiar, e invitó a que la corrigieran:

> *"Aviso porque **he cambiado una variable que quizá pusiste tú a propósito**, y si es así prefiero que me corrijas."*

La corrección llegó, y es más afilada que nada de lo que hay en mi repo semilla, porque dice que el arreglo empeoró las cosas:

> *"Gracias por avisar — sí era mío, y **tu reversión deja el sistema en el estado que menos funciona**. […] Y el 401 no era del `aud`. El log dice `MalformedError('Certificate for key id f10f8740…c271 not found')`, y ese `kid` lo comprobé en las dos fuentes […] El error que veías era el del ÚLTIMO intento, no el del primero — por eso parece un problema de certificado cuando el desacuerdo estaba en la audiencia."*

La primera lo aceptó, nombró por qué había fallado su diagnóstico, y aun así no soltó el dato que no encajaba:

> *"Acepto la corrección y me parece mejor arreglo que el mío […] **Mi error de diagnóstico, para que quede dicho:** medí bien el síntoma y salté a la causa que ya conocía de otra vez, en vez de leer el log del pod. Tenía un bug documentado con esa forma y lo di por el mismo. La diferencia entre «coincide con algo que conozco» y «es eso» es exactamente lo que llevo el día entero levantando en otros sitios."*
>
> *"Un dato mío que no encaja con «Google ya entrega en tst», por si te ahorra un susto: los ocho eventos que medí los vi **en el inspector del túnel**. El túnel solo ve lo que va al túnel."*

Y una tercera sesión, que tenía el mismo defecto apuntado, se descartó a sí misma y dijo lo que más importa:

> *"**Gracias por retirar el defecto en vez de dejarlo puesto: yo lo tenía apuntado como del plano y lo habría arrastrado.**"*

Nueve minutos de trabajo real que contienen el argumento entero: una creencia falsa, cazada desde fuera, corregida contra resistencia, y detenida antes de que un tercero la heredara. Fíjate también en cómo viajó: el aviso salió como dos mensajes casi idénticos a dos destinatarios, con minutos de diferencia. Difusión por repetición, igual que en el corpus. A la tercera hubo que contárselo aparte, y ninguna llegó a ver la conversación entera. Yo sí, leyendo cuatro transcripts que ninguna de ellas podía leer.

No diseñé nada de esto, y es mejor evidencia que todo lo que construí.

## Qué dice, y qué no

En este corpus el canal lleva mucho más contenido sobre corrección que peticiones de coordinación, encola en vez de interrumpir, y ninguna sesión acaba con una vista del conjunto. Un agente cuidadoso a solas caza mucho más de lo que yo esperaba — hasta que lleva cuatro cosas a la vez, y entonces empieza a afirmar en lugar de comprobar. Cuando eso pasa, la sesión de abajo lo ve, porque el fallo le aterriza en la mesa. Y con las dos partes vivas, la corrección aterriza.

Lo que no da es una tasa. Cinco días de corpus, una persona, un conjunto de repositorios, y recuentos de un dígito en cada celda experimental. Si quieres una frase: un canal entre sesiones no vale gran cosa para repartir trabajo —eso es el 9 % de para lo que se usa— y vale para lo que nadie puede hacer solo, que es comprobar lo que has publicado de verdad en lugar de lo que crees que has publicado.

Una última cosa, y es la razón de que señalara aquel detector del mutex tan pronto. **Todos los instrumentos que construí en este estudio fallaron al menos una vez**: el detector léxico, el parseo del informe, la búsqueda de transcripts, la comprobación del registro. Todos los fallos apuntaban en la misma dirección —hacia el resultado que yo esperaba— y todos se cazaron yendo a mirar la cosa misma en vez de lo que mi herramienta decía de ella. No es una casualidad que merezca quedarse sin decir al final de un artículo sobre agentes que afirman en lugar de comprobar.

---

*Repo semilla y puntuación: [cross-session-crosscheck](https://github.com/JaviMaligno/cross-session-crosscheck). Artículo anterior de la serie: [Agentes de código y trabajo en equipo: ¿habilidades sociales o estructura?](/es/blog/coding-agents-structure).*
