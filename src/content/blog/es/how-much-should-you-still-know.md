---
title: "¿Cuánto necesitas seguir sabiendo?"
description: "Construyo sistemas cuya lógica de negocio no sabría recitar si me despertaras a las 3 de la mañana. El modelo la sostiene por mí, y está bien. La pregunta difícil no es cuánto delegas, sino si todavía sabes distinguir cuándo la respuesta está mal."
pubDate: 2026-06-23
tags: ["IA", "Deuda Cognitiva", "Claude", "Software", "Ingeniería"]
lang: es
translationKey: how-much-should-you-still-know
heroImage: "/blog/how-much-should-you-still-know.png"
publishToDevto: true
---

Ahora mismo estoy construyendo un [sistema de pricing](/es/projects/steel-pricing-platform) para un cliente, y tengo que admitir una cosa: no sabría explicarte la mayor parte de cómo calcula los precios.

No porque el código sea opaco —lo escribí yo, o más bien lo escribimos Claude y yo—. Es porque la *lógica de negocio* es enorme. Los precios dependen del cliente, del material, del origen, y de una larga cola de extras y excepciones que tienen cada uno sus propias reglas. Hay más de las que me caben en la cabeza, y además cambian. Cada vez que me topo con un hueco —un precio cuya lógica no encuentro, un caso que la documentación no cubre— Claude Code y yo lo anotamos en un documento de "datos pendientes". Ese documento se revisa y se manda al cliente.

Y aquí viene la parte que debería incomodarme más de lo que lo hace. Alguna vez el cliente ha vuelto a preguntarme para aclarar cómo se calcula un precio, y para responderle he tenido que preguntarle antes a Claude. Soy el consultor externo. No tengo el conocimiento de negocio, y honestamente no creo que deba intentar tenerlo. Claude tiene acceso a toda la documentación y es mucho más fiable recuperando la regla correcta de lo que yo lo sería intentando internalizarlo todo.

El instinto es sentirse culpable por eso. He decidido que la culpa apunta, en su mayor parte, a la pregunta equivocada.

## Externalizar conocimiento no es nuevo, y no es deuda automáticamente

Llevamos mucho tiempo externalizando la memoria. Casi todos dejamos de memorizar números de teléfono hace dos décadas. No memorizamos datos que podemos consultar; recordamos *dónde* buscarlos. Los psicólogos tienen un nombre para esto —el "efecto Google"— y el mundo no se vino abajo. Saber cómo encontrar algo es en sí mismo una forma de conocimiento, y a menudo es la más útil.

Un LLM es el siguiente peldaño de esa escalera. No solo te dice dónde vive la respuesta; la recupera, la aplica a tu caso concreto y te la explica. Para algo como un libro de reglas de pricing inmenso y específico de un cliente, eso no es una degradación de mi trabajo. Es la única forma sensata de hacerlo. Memorizar miles de reglas volátiles que pertenecen al negocio de otro sería malgastar lo único por lo que realmente me pagan.

Hay un término que circula —"deuda cognitiva"— tomado prestado de la deuda técnica, y un estudio del MIT muy compartido ("Your Brain on ChatGPT") que midió una menor actividad neuronal en personas que escribían ensayos con un LLM. Es una expresión útil. Pero creo que se aplica con demasiada amplitud. No todo lo que externalizas es deuda. Comprar comida en vez de cultivarla no es "deuda agrícola". La pregunta nunca es *si* delegas conocimiento. Es cuánto, cuándo y —la parte que todo el mundo se salta— de qué sigues siendo responsable.

## Lo que de verdad cambia: la responsabilidad

Un estudiante que delega su aprendizaje en un LLM solo se perjudica a sí mismo. Si no entiende el ensayo, el coste recae sobre él, más tarde, en privado. Es un trato limpio que es libre de hacer.

Yo no tengo esa salida. Soy responsable de un sistema de pricing que va a dar números reales a clientes reales. Si calcula mal un precio, "me lo dijo Claude" no es una respuesta que pueda darle al cliente. El conocimiento es delegable. La responsabilidad no.

Eso reformula todo el asunto. La pregunta que me hacía a mí mismo —*¿cuánto de esto debería saber?*— es la equivocada. La pregunta correcta es: **¿sé lo suficiente para responder por ello?** Y esos son listones muy distintos.

## Tres preguntas, y dónde cae realmente la línea

Entonces, ¿cuándo *basta* con poder preguntar en el momento? ¿Qué deberías saber sin tener que preguntar? ¿Y hasta qué profundidad necesita llegar ese entendimiento? Déjame responder con el sistema de pricing, porque la línea cae en un sitio concreto.

**Los datos puntuales — pregunta sin reparos.** ¿Cuál es el recargo de este material desde aquel origen? Eso nunca lo voy a tener en la cabeza, y no debería. Es volátil, es el dominio del cliente, y el modelo lo recupera de forma más fiable de lo que lo haría yo. Poder preguntar en el momento es genuinamente suficiente aquí. Esta es la capa donde delegar no solo es aceptable, sino correcto.

**La forma del sistema — sábela sin preguntar.** Qué *categorías* de reglas existen, cómo se componen, qué entradas pueden mover un precio y cuáles no, dónde están las interacciones peligrosas. No puedo recitar cada recargo, pero tengo que saber que los recargos-por-origen son algo que existe, o ni siquiera sabré que tengo que preguntar. No puedes consultar un espacio cuya existencia desconoces. Este es el mapa, y el mapa me toca sostenerlo a mí.

**Lo bastante hondo para cazar una respuesta mala — y honesto sobre lo que eso significa.** Este es el umbral de verdad, y no va de *cuánto* sabes sino de *qué tipo* de cosa sabes. Y aquí tengo que ser honesto: no puedo validar cada output a mano, y fingir que sí sería otra forma de deshonestidad. No voy a calcular un precio manualmente, y muchas veces ni siquiera sé cuál es el precio *correcto* —eso es negocio del cliente, no mío—. Lo que sí puedo cazar directamente es lo grueso: un número que se desvía un orden de magnitud, una regla aplicada a un caso que no debería tocar nunca, dos extras que se acumulan sin deber. Las violaciones de la lógica básica.

La aplicación exacta —la parte que no puedo ver de un vistazo— no la valida mi juicio en absoluto. La validan los *tests*, y un golden set que el cliente aprueba. Ese es el movimiento que de verdad escala: no guardo la respuesta correcta en la cabeza, guardo un *mecanismo* que la comprueba. La validación misma se delega —pero a algo determinista y auditable, no a la intuición—. Es parte de por qué la programación sigue derivando hacia estar orientada a resultados: cada vez más especificas y verificas el comportamiento, no el camino que tomó el modelo para producirlo.

Así que la línea es un poco más amplia que "¿puedo darme cuenta yo de que está mal?". Es: **¿tengo *alguna* forma de cazar una respuesta errónea —mi propio ojo para los errores burdos, un test o un golden set para los exactos—?** Si no tengo ninguna, no estoy delegando, estoy abdicando. Delegar mantiene en el bucle a un humano, o a una comprobación de la que el humano es dueño. Abdicar elimina ambos. Se ven idénticos hasta el momento en que la respuesta es errónea, y entonces no podrían ser más distintos.

## El síntoma silencioso: documentación que solo leen los agentes

Aquí es donde noto que la línea se difumina en mi propio trabajo. Cada vez más, el conocimiento sobre mis sistemas vive en archivos escritos para máquinas. `CLAUDE.md`. `AGENTS.md`. Skills. Y en este proyecto, ese documento de "datos pendientes" —mitad especificación, mitad lista de preguntas, escrito para que el agente y yo podamos navegar un dominio que ni el cliente ni yo tenemos del todo escrito en ningún otro sitio—.

Escribí sobre esta deriva desde otro ángulo en [El software se está disolviendo en el modelo](/es/blog/software-dissolving-into-the-model): la capa que solíamos llamar software se colapsa en instrucciones por un lado y salida generada por el otro. La otra cara de esa comodidad es esta: cuando la documentación se escribe *para el agente*, ¿quién mantiene un mapa para los humanos que siguen siendo responsables? Es fácil acabar con un sistema perfectamente legible para Claude y que se va apagando lentamente para todos los que responden por él.

Lo interesante es que mi documento de "datos pendientes" hace, sin querer, lo correcto. No es solo contexto para el agente; es un punto de control humano-en-el-bucle. Obliga a un momento en el que una persona —yo, y luego el cliente— tiene que mirar lo que falta y decidir. Ese es el patrón que merece la pena conservar. La respuesta a "docs que solo leen los agentes" probablemente no sea escribir menos. Es diseñar a propósito los puntos donde un humano responsable tiene que parar y validar, en lugar de dejar que el bucle se cierre sin él.

## La parte que nadie quiere admitir en voz alta

Hay una capa social en todo esto que el enfoque técnico se salta. Contarte que a veces le pregunto a Claude antes de responderle a mi propio cliente me cuesta algo. Roza de lleno el síndrome del impostor —el miedo silencioso a que, en cuanto la gente vea cómo se hace la salchicha, decidan que no soy el experto que contrataron—.

Lo curioso es que la transparencia es la cura de esa sensación, no el detonante. El síndrome del impostor crece en la brecha entre la imagen que proyectas y cómo trabajas de verdad. Decir en voz alta "le pregunté al modelo y luego verifiqué que la regla aplica" cierra esa brecha. Ya no queda nada por descubrir.

Pero no voy a fingir que el coste es imaginario. Con algunos clientes vas a quedar genuinamente peor por ser abierto al respecto —no porque hayas hecho nada mal, sino porque todavía no entienden cómo es un buen uso de la IA—. Oyen "le pregunté a Claude" y lo asocian a "no lo sabía", cuando debería asociarse a "recuperé la regla autorizada y la comprobé". La ironía es afilada: esos son a menudo exactamente los clientes a los que me contratan para ayudarles a integrar la IA en sus propios procesos. La misma brecha de comprensión que hace arriesgada la transparencia es la razón por la que existe el trabajo.

Por eso la línea de validación también importa aquí, y no solo en lo técnico. Transparencia no es confesar "no sé nada, lo hace Claude". Es ser preciso sobre *qué* delegas y, crucialmente, sobre que conservaste la capacidad de comprobarlo. "Le pregunté a Claude y confirmé que la regla aplica a este caso" es una frase completamente distinta de "le pregunté a Claude". Una describe a un profesional usando bien una herramienta. La otra describe justo lo que el cliente teme. Poder validar es lo que hace defendible la honestidad —y, con el tiempo, mostrar esa distinción es parte de cómo los clientes aprenden a diferenciar una de la otra—.

## Dónde he aterrizado

No te voy a decir que delegues menos. En el proyecto de pricing, delegar el conocimiento de negocio es la decisión correcta, y fingir lo contrario solo me haría más lento sin hacerme más fiable. La línea que trazo no está entre "implementación que puedes descargar" y "conocimiento que debes conservar". Está entre el conocimiento que todavía puedes *validar* y el conocimiento ante el que te has quedado ciego.

Tres cosas que estoy haciendo de verdad al respecto:

1. **Sostén el mapa, no el territorio.** No memorices los datos; sí sabe qué categorías de cosas existen y cómo interactúan. No puedes hacer una pregunta sobre un espacio que no sabes que está ahí.
2. **Trata "¿puedo comprobar esto?" como el test real.** Antes de dejar que el modelo se quede con una decisión, me pregunto si tengo una *forma* de pillar el error si lo cometiera —mi propio ojo para los errores burdos, un test o golden set para los exactos—. Ojo: "comprobar" rara vez significa "calcularlo yo mismo"; normalmente significa ser dueño del mecanismo que lo hace. Si no hay mecanismo alguno, eso no es delegar, y o construyo uno o no lo pongo a funcionar sin supervisión.
3. **Diseña los puntos de control, no solo los prompts.** Cuando el conocimiento se muda a documentos legibles para el agente, vuelve a meter el momento humano a propósito —un paso de revisión, un documento de preguntas pendientes, una firma— para que el bucle no pueda cerrarse en silencio sin nadie responsable dentro.

La respuesta honesta a "¿cuánto necesitas seguir sabiendo?" resulta no ser una cantidad en absoluto. Es una capacidad: la suficiente para saber cuándo la respuesta está mal. Todo lo que esté por encima de esa línea, pregúntalo sin reparos. Por debajo, no estás ahorrando esfuerzo: solo estás aplazando el momento en que te enteras.

Hay una versión más radical de esta idea, en la que en lugar de fiarte del juicio del modelo lo obligas a externalizar su razonamiento en código que puedes leer y testear de verdad. Ese es el experimento del próximo artículo: delegación que puedes auditar, línea a línea.

---

*Este es el primero de dos artículos sobre delegación y entendimiento. El siguiente se pone concreto: un experimento para hacer que un modelo escriba su mundo como código verificable en lugar de guardarlo en la cabeza. Lectura relacionada: [El software se está disolviendo en el modelo](/es/blog/software-dissolving-into-the-model).*
