---
title: "Demasiado pequeño para automatizar"
description: "El trabajo que nunca se automatiza no es el difícil. Es el lote de ciento cincuenta filas que queda justo por debajo de la línea a partir de la cual compensa escribir el script — y esa línea se ha movido dos veces, en direcciones opuestas, sin que casi nadie haya vuelto a calcular dónde está."
pubDate: 2026-09-13
tags: ["IA", "Automatización", "Productividad", "Ingeniería", "Herramientas"]
lang: es
translationKey: too-small-to-automate
linkedinLinks:
  - label: "Prompt Scripter"
    url: "https://promptscripter.javieraguilar.ai"
---

Tengo una carpeta mental de cosas que nunca automaticé. Las difíciles no están ahí. Los problemas difíciles tuvieron script hace años, porque un problema difícil es interesante y un script es una buena excusa para resolverlo.

Lo que hay en la carpeta es pequeño. Ciento cincuenta descripciones cortas que necesitan una decisión cada una. Una columna de texto libre que hay que reescribir en el tono de la casa. Noventa cosas, una decisión por cada una, ninguna difícil.

Sé automatizar todo lo que hay en esa carpeta. Lo sé desde hace años. Esa es la parte que merece explicación.

Ordena la carpeta por lo pesada que es cada tarea y no cuadra nada: los trabajos que sí acabaron en script, hace años, eran igual de pesados que los que no. Lo que ordena la carpeta es el tamaño, y el corte es más limpio de lo que debería: los pesados y grandes acabaron todos en un script; los medianos, ninguno; y la frontera entre unos y otros está en un sitio que nunca he calculado. **El trabajo que nunca se automatiza no es el difícil. Es el que queda justo por debajo de la línea a partir de la cual compensa escribir el script.** Esa línea es lo único de todo esto que nadie recalcula, y se ha movido dos veces desde la última vez que la miramos.

## La aritmética que todo el mundo recuerda a medias

La versión que la gente lleva en la cabeza es la de la tabla famosa de xkcd: automatiza cuando el tiempo que ahorrarás supere al que cuesta construirlo. El coste manual total son filas por segundos; el automatizado es la construcción, más un coste por fila mucho menor. Cruzas la línea, escribes el script.

Es una buena regla y tiene un agujero. La fórmula tiene tres términos, no dos:

- **Construir.** Escribir la cosa.
- **Ejecutar.** Correrla, por fila.
- **Comprobar.** Establecer que la salida es correcta, por fila.

En la automatización con la que se crió la mayoría de los ingenieros, el tercer término era invisible, y lo era por un buen motivo: era genuinamente casi cero. Un script que renombra ficheros según una regla o implementa la regla o no. Inspeccionas tres salidas, te convences de que la regla está bien, y las otras trescientas son correctas por construcción. Determinismo significa que verificas el *programa*, una vez, no la *salida*, N veces.

Así que todos aprendimos una fórmula de dos términos, en un mundo donde el tercero se redondeaba a nada. Después el tercer término dejó de redondearse a nada, y seguimos usando la fórmula.

## Qué cambió, y cambió dos veces

**Construir se abarató.** Esta es la parte que todo el mundo notó. Un agente de código escribe el bucle sobre el CSV más rápido de lo que tardas en especificárselo. El término de construcción, que antes era el argumento entero, se hundió. Por sí solo, eso empuja el umbral hacia abajo: hay más cosas que compensa automatizar de las que compensaban antes, y en ese hueco hay trabajo real.

**Y una clase nueva de tarea entró en la banda.** Esta parte importa más y se discute menos. Es el trabajo por filas donde la operación es un juicio. Clasifica este mensaje como problema de facturación o de acceso. Señala si esta cláusula es inusual para un contrato de este tipo. Reescribe esto en nuestro tono sin inventarte una afirmación. Resume esto en una línea que entienda alguien que no es del gremio.

Lo que ha llegado tarde no es la capacidad: es una manera barata y corriente de apuntarla a una lista, algo a lo que se llega sin una integración, sin una partida de presupuesto y sin que lo firme nadie. Por eso nadie tiene un hábito para esta categoría. Para casi todo el mundo nunca tuvo una forma automatizada que mereciera la pena: o era una persona, o era un proyecto que nadie iba a financiar. Nunca hizo falta una regla de umbral, así que no se construyó, y ahora las tareas están llegando y la regla no está.

## El único término que no se abarató

Aquí es donde los dos cambios apuntan en direcciones opuestas.

Las tareas que acaban de volverse automatizables son exactamente aquellas cuyo criterio de aceptación es difuso. No hay un `assert` para *¿se lee bien esto?*. No hay test unitario para *¿es esta la categoría correcta, dada una taxonomía que vive en parte dentro de la cabeza de alguien?*. Lo que significa que el término de comprobación no se hunde como se hundió el de construcción. Se queda más o menos lineal en el número de filas, y la constante es una persona leyendo.

|  | construir una vez | ejecutar por fila | comprobar por fila |
|---|---|---|---|
| Script determinista, 2019 | horas | ~0 | ~0 — verificas el programa |
| Script determinista, 2026 | minutos | ~0 | ~0 — verificas el programa |
| Juicio del modelo por fila | minutos | segundos, más tokens | el trabajo entero |

Esa tabla es estructura, no medición — no he cronometrado nada de esto y no voy a fingir lo contrario. Pero la forma es el argumento. La automatización solía mover trabajo de *hacer* a *construir*. En el trabajo difuso por filas lo mueve de *hacer* a *comprobar*, y comprobar es el término que no se paraleliza, no se amortiza y no se delega. Es el mismo recurso que ya llamé la moneda real de [las decisiones de construir o comprar](/es/blog/build-vs-buy-attention): tu atención, el único insumo que no se abarató cuando se abarató todo lo demás.

Por eso también la actualización ingenua — *construir es gratis ahora, así que automatiza todo* — produce malas decisiones. Optimiza el término que ya se hundió e ignora el que ahora manda. He tenido que hacer [la misma corrección en cómo reviso la salida de un agente](/es/blog/results-oriented-programming): la pregunta dejó de ser *¿está bien la implementación?* y pasó a ser *¿está bien el resultado?*, y responder a una y a otra cuesta cantidades muy distintas.

## Por qué el script sale más caro que el script

Soy parte interesada en los tres costes que vienen a continuación, y conviene que los descuentes.

Hay una segunda razón por la que la banda es más ancha de lo que sugiere la fórmula, y es la que un lector técnico se va a resistir a aceptar, porque desde dentro parece una excusa.

«Eso lo hago yo en veinte líneas de Python.» Cierto. Pero las veinte líneas no son el coste.

**La cuenta es un coste.** Para pasar filas por un modelo desde un script necesitas elegir un proveedor, conseguir una clave de API y aceptar una factura que cuenta tokens. En casa eso es dar de alta un método de pago y ponerle un límite de gasto para el trabajo de una tarde. En el trabajo es una conversación con compras, y si no controlas lo que te dejan usar, puede ser una conversación que no ganas. Ya escribí sobre [qué cambia cuando la herramienta no la eliges tú](/es/blog/the-tool-youre-allowed-to-use); este es uno de los sitios donde más aprieta, porque el bloqueo no es técnico y no hay ingeniería que lo quite.

**El prompt es un coste, y no donde crees.** El prompt que funciona de verdad no es el que escribirías en un fichero. Es al que llegaste tras seis rondas de corregirlo en una ventana de chat, mirando una salida, viendo que se desviaba, ajustando una frase. Ese bucle es la razón de que funcione. Congelarlo en un script es comprometerte con él justo en el momento en que menos seguro estás de que sea el bueno — y lo que el script elimina es precisamente el bucle que te llevó hasta ahí.

**La forma de la salida es un coste.** Un script quiere salida estructurada que pueda escribir a un fichero. Lo que significa que ahora estás especificando esquemas JSON, gestionando fallos de parseo y decidiendo qué hacer con la fila 90, y le has añadido un problema de serialización a una tarea que no lo tenía, porque quien va a consumir esas ciento cincuenta respuestas es una persona que iba a leerlas.

Suma todo eso y el término de construcción honesto para un trabajo difuso de ciento cincuenta filas no son las veinte líneas. Es una decisión que quizá no estés autorizado a tomar, un prompt con el que tienes que comprometerte mientras todavía lo estás editando y un problema de serialización que te has inventado por el camino. Por eso existe la carpeta.

## Qué quiere realmente esta banda

Vista esa forma, la pregunta interesante no es *cómo construyo el pipeline más rápido*. Es *qué quiere esta banda, si no es un pipeline*.

Quiere que se quite la repetición sin que se cierre el bucle. Eso es una propiedad, no una lista de características: lo que repita tiene que dejar el juicio exactamente donde ya está, viendo la salida según llega y pudiendo parar en la fila treinta porque la fila treinta ha revelado que el prompt estaba mal. Vale cualquier cosa que mantenga la comprobación así de barata. No vale ningún montaje que recoja la salida para revisarla después, porque ese es justo el montaje que te obliga a comprometerte con la ejecución entera antes de saber si el prompt es el bueno.

Es una ambición más pequeña que un pipeline y es la correcta para esta banda. Un pipeline es la respuesta buena cuando el trabajo se repite para siempre, y entonces sus reintentos, sus logs y su capacidad de retomar se ganan el sitio. Por debajo de eso vale [el mismo argumento que hice sobre pruebas de navegador exploratorias frente a scripts](/es/blog/playwright-cli-vs-scripts-ai-agents): el script es el artefacto correcto cuando vas a ejecutarlo muchas veces y el criterio es estable, y el equivocado cuando todavía estás descubriendo qué significa «correcto».

Construí una cosa que hace exactamente esto: **Prompt Scripter ejecuta el mismo prompt sobre una lista dentro del chat que ya usas — ChatGPT, Claude o Gemini —, sin clave de API propia y sin factura por tokens: la llamada al modelo ocurre en la sesión que ya pagas.** Ese es todo el argumento de venta y no lo voy a adornar. Es una extensión de Chrome, es nueva y tiene cuenta propia — que también es un coste, solo que no una clave de API. Y cuando has entrado con esa cuenta, tus filas viajan por HTTPS a un servidor mío para abrir la ejecución. El registro de conjunto de datos que crea se queda solo con el recuento y con los nombres de columna — pero la entrada de cada fila y la respuesta del modelo a esa fila sí se guardan, como resultados de esa ejecución, que es justo de donde sale la exportación de la cuenta. En un texto cuya postura entera es la precisión, callármelo saldría barato — y yo mismo lo di por bueno al revés antes de mirar la segunda ruta. No tengo ninguna medición de tiempo ahorrado, así que no voy a afirmar ninguna. El razonamiento de arriba es la razón por la que la construí. Si el razonamiento está mal, la herramienta está mal también, y deberías decirlo.

## Dónde seguiría escribiendo el script

Que el umbral se mueva no significa que haya desaparecido. Cuatro sitios donde el pipeline es sencillamente la respuesta mejor:

- **Cuando el trabajo vuelve solo, cada semana o cada mes.** La amortización es real. Una vez al mes durante años le gana a cualquier bucle interactivo, y el coste de construcción se divide entre todas las ejecuciones futuras.
- **Cuando la salida alimenta a un sistema, no a una persona.** Si la respuesta de la fila 90 acaba en una base de datos, necesitas esquemas, validación y una política de reintentos, y una ventana de chat es mal sitio para conseguir cualquiera de las tres.
- **Cuando el juicio es en realidad determinista.** Una cantidad sorprendente de «que decida el modelo» es una regla que todavía no has escrito. Escribe la expresión regular. Es más rápida, es gratis y se puede probar.
- **Cuando N es de verdad grande.** A cierta escala la comprobación por fila tiene que pasar de leer a muestrear y hacer estadística, y en cuanto muestreas quieres la infraestructura que hace que muestrear signifique algo.

Y el límite del otro extremo, que importa igual: **por debajo de cierto número de filas, hazlo a mano.** Convertir el prompt en plantilla, separar las columnas y decidir qué significa una fila de cabecera es preparación, y la preparación se paga una vez tanto si la lista tiene treinta filas como si tiene trescientas — así que hay un tamaño por debajo del cual la preparación *es* el trabajo. No he medido dónde cae, y dependerá de la tarea, pero el criterio es fácil de aplicar: si habrías terminado la lista antes de terminar de describirla, describirla sobraba. La banda tiene suelo además de techo, y olvidarse del suelo es lo que lleva a automatizar algo que habrías terminado en diez minutos.

## Límites

Quiero ser exacto sobre en qué se apoya este argumento y en qué no.

Se apoya en la estructura, no en datos. No he medido tiempo de construcción, ni de comprobación, ni rendimiento de nada de lo descrito aquí, y la tabla de arriba es una forma, no un resultado. Cuando sí tengo cifras lo digo, y enseño tanto las que encogieron como las que crecieron — eso fue lo que pasó cuando [medí qué compra realmente el andamiaje prescriptivo](/es/blog/the-scaffolding-you-pay-for), y la versión honesta era menos favorecedora que la corazonada. Este texto no tiene detrás una medición equivalente, así que léelo como un razonamiento que puedes contrastar con tu propia carpeta, no como un hallazgo.

También asume que el término de comprobación es real, lo cual solo es cierto si de verdad compruebas. Si nadie lee las ciento cincuenta salidas, el argumento se cae — pero también se cae el valor del trabajo, y [ese fallo es más silencioso de lo que la gente espera](/es/blog/nobody-will-check-behind-you).

## La pregunta que ordena la carpeta

Resulta que el número de filas es la pregunta equivocada por la que empezar. Antes de escribir nada, me pregunto qué tendría que leer para saber que ha funcionado.

Si la respuesta es «tres salidas y después me fío de la regla», es un trabajo determinista. Escribe el script. El término de comprobación es casi cero y la aritmética que todo el mundo recuerda a medias es la aritmética correcta.

Si la respuesta es «todo», no hay un problema de pipeline. Hay una cola, y lo único que merece la pena quitarle a una cola es la parte que no es leer.

Eso resultó ser mi carpeta, casi entera. Me apostaría algo a que la tuya también.

---

*Relacionado: [la atención como moneda real en construir o comprar](/es/blog/build-vs-buy-attention), [verificar resultados en vez de implementaciones](/es/blog/results-oriented-programming), [cuándo un script le gana a la exploración interactiva](/es/blog/playwright-cli-vs-scripts-ai-agents), y [por qué envolver una secuencia fija en una conversación es solo un formulario caro](/es/blog/expensive-form).*
