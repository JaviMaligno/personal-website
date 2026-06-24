---
title: "Programación orientada a resultados"
description: "Revisar solía significar leer la implementación. Cada vez más verifico lo que el modelo produjo, no el camino que tomó — y lo que significa 'verificar el resultado' cambia muchísimo según si ese resultado es un número o un comportamiento."
pubDate: 2026-06-24
tags: ["IA", "Software", "Ingeniería", "Testing", "Agentes"]
lang: es
translationKey: results-oriented-programming
heroImage: "/blog/results-oriented-programming.png"
publishToDevto: true
---

Hay una frase que dejé caer casi de pasada en [un artículo reciente](/es/blog/how-much-should-you-still-know) y que me lleva rondando desde entonces: la programación sigue derivando de verificar *cómo* funciona el código a verificar *qué* produce. Quiero tirar de ese hilo en condiciones, porque es uno de los cambios más silenciosos pero más consecuentes en cómo funciona este oficio ahora mismo.

Y para que quede claro qué es lo que deriva: no es que antes no comprobáramos los resultados. Los tests han existido siempre, y escribirlos ha sido siempre buena práctica —incluso en las largas etapas en que la industria escribía bastantes menos de los que debería—. El cambio es de *centro de gravedad*. Durante casi toda mi carrera el peso de "revisar" caía sobre la implementación: leías el diff, seguías la lógica, decidías si el *camino* que tomaba el código era sólido, y los tests iban al lado como red de seguridad. El camino era el artefacto que escrutabas en primer lugar.

Ese equilibrio se está invirtiendo. Cada vez más, la comprobación del resultado es el plato principal, y dejo que el camino sea problema del modelo mientras el resultado se sostenga. Lo llamo programación orientada a resultados, a falta de un nombre mejor. No es una metodología que fuera buscando; es en lo que el trabajo se convirtió sin avisar.

La parte interesante no es el eslogan. Es lo que resulta significar "verificar el resultado", porque significa cosas radicalmente distintas según *qué* sea el resultado.

## El extremo fácil: cuando el resultado es un número

La versión más limpia es cuando la salida se ancla a un valor. Mi [sistema de pricing](/es/projects/steel-pricing-platform) da un número: o es el correcto para ese material, ese origen y ese cliente, o no lo es. No leo el código que lo calculó —mantengo un golden set que el cliente aprobó y tests que comprueban que la salida coincide—. El *oráculo* que decide "correcto o no" es exacto y auditable, sin ningún juicio en el bucle en el momento de la verdad; Claude puede refactorizar el motor tres veces en un fin de semana y me dará igual, mientras el set siga en verde. Cuando puedas llegar hasta aquí, llega —es la forma más fuerte de la idea—.

## El extremo difícil: cuando el resultado es un comportamiento

Pero la mayor parte de lo que construimos no se reduce a un número.

Un motor de reglas que tiene que llegar a la *decisión* correcta a través de mil condiciones que interactúan. Un clasificador que mete un negocio en una categoría regulatoria. Una rutina de planificación cuya salida es "razonable" o "no" de maneras que ninguna aserción suelta captura. Un agente que elige, a mitad de tarea, si pedir una aclaración o simplemente seguir. Un resumen que tiene que ser fiel sin ser una transcripción. Algunos son código puramente determinista, otros van dirigidos por un modelo, pero comparten la propiedad que importa aquí: "el resultado" es un *comportamiento* o una *decisión*, y no hay número de oro contra el que hacer diff. Dos salidas perfectamente buenas pueden no parecerse en nada.

La tentación es replegarse al hábito viejo: si no puedo fijar la salida, vuelvo a leer cómo llegó hasta ahí. Y a menudo puedes leerlo. Las ramas de un motor de reglas están ahí mismo; incluso un modelo deja un rastro —su razonamiento, sus llamadas a herramientas, los pasos intermedios—. El camino no es la caja negra sellada que resulta cómodo llamarlo, e inspeccionarlo sirve de verdad para depurar y para calibrar cuánto fiarte de la cosa. Pero te dice *cómo* llegó, no *que* llegó a algo correcto. Un rastro de aspecto limpio puede aterrizar en una respuesta errónea, y uno enmarañado en una correcta —lo cual fue siempre cierto del código, y es justo por lo que escribíamos tests en vez de releer la función—. En este extremo del espectro, leer el camino te informa; no zanja la corrección. Eso sigue teniendo que pasar en el resultado.

Así que la orientación a resultados no se rompe aquí, solo cambia de *oráculo*. En lugar de un match exacto construyes una comprobación más rica, y sube por una escalera de subjetividad: specs de comportamiento, property tests y una batería de escenarios para el motor de reglas; un eval set de casos representativos con las decisiones que defenderías; y para las salidas genuinamente de juicio, a veces un LLM puntuando contra criterios que tú escribiste. Ya argumenté antes sobre [cuándo un LLM-como-juez es siquiera fiable como para apoyarte en él](/es/blog/llm-as-judge-three-decisions); aquí es justo donde importa, porque en el extremo lejano tu juez *es* tu verificación. El resultado sigue siendo lo que está bajo prueba —solo has cambiado un comparador determinista por uno definido-pero-subjetivo, y el trabajo de ingeniería se traslada a hacer esa comprobación lo más principista y repetible posible—.

El espectro es justo el quid. De "assert igual a 4.200,00" a "un panel de criterios dice que esta decisión de triaje fue razonable", es el mismo movimiento a distinta resolución: especifica el resultado, construye algo que lo compruebe, deja de vigilar el camino.

## Por qué pasa esto

Nada de esto es una filosofía que adoptara. Es una respuesta a que el camino se abarató.

Cuando un modelo escribe la implementación, dos cosas se invierten a la vez. El camino se vuelve casi gratis de producir —y caro, a veces inútil, de leer—. Un diff de 600 líneas que Claude generó en un minuto puede llevarme una hora revisar línea a línea, y al final de esa hora a menudo sé *menos* sobre si es correcto de lo que un vistazo de cinco segundos a la suite de tests me diría. La economía de la atención se ha invertido: leer el *cómo* ya no escala al ritmo al que lo producimos.

Mientras tanto, el resultado es lo único que el usuario o el cliente tocan de verdad. No experimentan tu flujo de control; experimentan el precio, la decisión, el resumen. La verificación migra hacia donde viven de verdad el valor y el riesgo —la frontera entre la entrada y la salida— porque esa es la parte que no se abarató. Definir qué significa "correcto" sigue siendo trabajo duro y humano. El modelo solo se quedó con la parte de en medio.

## El matiz que arruina el eslogan

Aquí es donde la programación orientada a resultados se vuelve peligrosamente fácil de malinterpretar. Si lo único que importa es la salida, ¿importa algo el código de en medio? ¿Puede ser un lodazal de duplicación y trucos ingeniosos, mientras pasen los tests?

No. Y la razón es más afilada que "los buenos ingenieros cuidan el oficio".

La calidad interna —modularidad, fronteras claras, seguridad, convenciones— sigue importando, puede que más que antes. Pero el *motivo* por el que importa ha cambiado, y también el público. Antes manteníamos el código limpio para los humanos que lo leerían después. Cada vez más, el siguiente lector es un agente. La mantenibilidad está derivando de mantenibilidad-para-humanos a mantenibilidad-para-agentes. Un modelo produce mejores resultados, de forma más fiable, en un código con costuras limpias, nombres honestos y módulos ajustados —por las mismas razones, más o menos, que un humano: menos contexto que sostener, menos formas de equivocarse, sitios más claros donde hacer un cambio—. Los internos desordenados no solo ofenden al gusto; degradan los mismísimos resultados que estás optimizando, solo que con retraso. El precio malo que sacas el trimestre que viene a menudo lo paga el enredo que dejaste que el modelo abandonara en este.

Así que la orientación a resultados no es "la calidad interna da igual". Es "la calidad interna importa *por* su efecto en los resultados, no como un fin que inspeccionas por sí mismo". Es un cambio de prioridad y de marco, no una licencia para abandonarla. Dejas de revisar el diff buscando elegancia. No dejas de preocuparte por si el sistema sigue siendo manejable —solo sostienes ese listón por otros medios: linters, tests de arquitectura, convenciones codificadas donde el agente las vaya a ver de verdad—.

## Hacia dónde va esto

Sigue la línea lo bastante lejos y el oficio empieza a verse distinto.

Si la verificación vive en la frontera, y la calidad interna está codificada como reglas que el agente tiene que respetar, entonces lo que de verdad estás escribiendo ya no es la implementación en absoluto. Es un *objetivo* más un conjunto de *restricciones*: el resultado que quieres, y las reglas dentro de las que el sistema tiene que mantenerse mientras lo alcanza —el stack, las reglas de negocio, los requisitos de seguridad, las convenciones, la definición operativa de "bueno"—. Luego se lo entregas a un modelo dentro de un buen harness y dejas que optimice hacia el objetivo sin salirse de las restricciones.

Ese es el punto final lógico de la programación orientada a resultados: especificas la meta y las guardas, y el modelo busca el camino. Tu palanca deja de ser el código que escribes y pasa a ser la calidad del objetivo que defines y del harness que le pones alrededor —los tests, los evals, los jueces, las reglas, los puntos de control—. Equivócate en eso y un modelo capaz optimizará con toda confianza hacia lo equivocado. Acierta y habrás construido algo que mejora el resultado sin que tú toques la parte de en medio.

Por eso no creo que "orientado a resultados" signifique "vago". Significa que la parte difícil se movió. Antes vivía en la escritura. Ahora vive en definir —con la precisión suficiente para que una máquina pueda quedar sujeta a ello— qué querías de verdad, y en construir el aparato que lo mantiene ahí. El camino se abarató. Decir qué significa "correcto" se volvió más importante que nunca.

---

*Un acompañante de [¿Cuánto necesitas seguir sabiendo?](/es/blog/how-much-should-you-still-know), que se topó con esta misma idea desde el ángulo de la delegación y la responsabilidad.*
