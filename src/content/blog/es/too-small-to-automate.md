---
title: "Demasiado pequeño para automatizar"
description: "El trabajo que nunca se automatiza no es el difícil. Es el lote de cuatrocientas filas que queda justo por debajo de la línea a partir de la cual compensa escribir el script — y esa línea se ha movido dos veces, en direcciones opuestas, sin que casi nadie haya vuelto a calcular dónde está."
pubDate: 2026-09-13
tags: ["IA", "Automatización", "Productividad", "Ingeniería", "Herramientas"]
lang: es
translationKey: too-small-to-automate
heroImage: "/blog/too-small-to-automate.png"
linkedinLinks:
  - label: "Prompt Scripter"
    url: "https://promptscripter.javieraguilar.ai"
---

Tengo una carpeta mental de cosas que nunca automaticé. Las difíciles no están ahí. Los problemas difíciles tuvieron script hace años, porque un problema difícil es interesante y un script es una buena excusa para resolverlo.

Lo que hay en la carpeta es pequeño. Cuatrocientas descripciones cortas que necesitan una decisión cada una. Una columna de texto libre que hay que reescribir en el tono de la casa. Doscientos algos, una decisión por cada uno, ninguna difícil.

Sé automatizar todo lo que hay en esa carpeta. Lo sé desde hace años. Esa es la parte que merece explicación.

La lectura habitual es pereza, y algo de eso hay. Pero mira la mecánica un segundo, porque la pereza no explica por qué la carpeta tiene una *forma* — por qué los trabajos pesados-y-grandes se automatizaron y los pesados-y-medianos no lo hicieron nunca. **El trabajo que nunca se automatiza no es el difícil. Es el que queda justo por debajo de la línea a partir de la cual compensa escribir el script.** Y casi nadie ha vuelto a calcular dónde está esa línea, aunque se ha movido dos veces desde la última vez que lo miraron.

## La aritmética que todo el mundo recuerda a medias

La versión que la gente lleva en la cabeza es la de la tabla famosa de xkcd: automatiza cuando el tiempo que ahorrarás supere al que cuesta construirlo. El coste manual total son filas por segundos; el automatizado es la construcción, más un coste por fila mucho menor. Cruzas la línea, escribes el script.

Es una buena regla y tiene un agujero. La fórmula tiene tres términos, no dos:

- **Construir.** Escribir la cosa.
- **Ejecutar.** Correrla, por fila.
- **Comprobar.** Establecer que la salida es correcta, por fila.

En la automatización con la que se crió la mayoría de los ingenieros, el tercer término era invisible, y lo era por un buen motivo: era genuinamente casi cero. Un script que renombra ficheros según una regla o implementa la regla o no. Inspeccionas tres salidas, te convences de que la regla está bien, y las otras trescientas son correctas por construcción. Determinismo significa que verificas el *programa*, una vez, no la *salida*, N veces.

Así que todos aprendimos una fórmula de dos términos, en un mundo donde el tercero se redondeaba a nada. Después el tercer término dejó de redondearse a nada, y seguimos usando la fórmula.

## Qué cambió, y cambió dos veces

**Construir se abarató.** Esta es la parte que todo el mundo notó. Un agente de código escribe el bucle sobre un CSV de cuatrocientas filas más rápido de lo que tú lo especificas. El término de construcción, que antes era el argumento entero, se hundió. Tomado en solitario, eso empuja el umbral hacia abajo: hay más cosas que compensa automatizar de las que compensaban antes, y en ese hueco hay trabajo real.

**Y una clase nueva de tarea entró en la banda.** Esta parte importa más y se discute menos. Existe ahora una categoría de trabajo por filas que es automatizable *en principio* y no lo era hace tres años: las filas donde la operación es un juicio. Si este mensaje describe un problema de facturación o uno de acceso. Si esta cláusula es inusual para un contrato de este tipo. Reescribe esto en nuestro tono sin inventarte una afirmación. Resume esto en una línea que entienda alguien que no es del gremio.

Nadie tiene un hábito para esa categoría, porque hasta hace poco no tenía forma automatizada ninguna. O era una persona, o era nada. Nunca necesitaste una regla de umbral para eso, así que nunca la construiste, y ahora las tareas están llegando y la regla no está.

## El único término que no se abarató

Aquí es donde los dos cambios apuntan en direcciones opuestas.

Las tareas que acaban de volverse automatizables son exactamente aquellas cuyo criterio de aceptación es difuso. No hay un `assert` para *¿se lee bien esto?*. No hay test unitario para *¿es esta la categoría correcta, dada una taxonomía que vive en parte dentro de la cabeza de alguien?*. Lo que significa que el término de comprobación no se hunde como se hundió el de construcción. Se queda más o menos lineal en el número de filas, con una constante del tamaño de una persona.

|  | construir una vez | ejecutar por fila | comprobar por fila |
|---|---|---|---|
| Script determinista, 2019 | horas | ~0 | ~0 — verificas el programa |
| Script determinista, 2026 | minutos | ~0 | ~0 — verificas el programa |
| Juicio del modelo por fila | minutos | segundos, más tokens | el trabajo entero |

Esa tabla es estructura, no medición — no he cronometrado nada de esto y no voy a fingir lo contrario. Pero la forma es el argumento. La automatización solía mover trabajo de *hacer* a *construir*. En el trabajo difuso por filas lo mueve de *hacer* a *comprobar*, y comprobar es el término que no paraleliza, no amortiza y no se delega. Es el mismo recurso que he defendido que es la moneda real en [las decisiones de construir o comprar](/es/blog/build-vs-buy-attention): tu atención, el único insumo que no se abarató cuando se abarató todo lo demás.

Por eso también la actualización ingenua — *construir es gratis ahora, así que automatiza todo* — produce malas decisiones. Optimiza el término que ya se hundió e ignora el que ahora manda. He tenido que hacer [la misma corrección en cómo reviso la salida de un agente](/es/blog/results-oriented-programming): la pregunta dejó de ser *¿está bien la implementación?* y pasó a ser *¿está bien el resultado?*, y responder a cada una cuesta cosas muy distintas.

## Por qué el script sale más caro que el script

Hay una segunda razón por la que la banda es más ancha de lo que sugiere la fórmula, y es la que un lector técnico va a rechazar, porque desde dentro parece una excusa.

«Eso lo hago yo en veinte líneas de Python.» Cierto. Pero las veinte líneas no son el coste.

**La cuenta es un coste.** Para pasar filas por un modelo desde un script necesitas una clave de API, una decisión de proveedor y una factura por tokens — encima de la suscripción que ya pagas y que ya estás usando. En casa eso es una segunda factura por algo que ya tienes. En el trabajo es una conversación con compras, y si no controlas lo que te dejan usar, puede ser una conversación que no ganas. Ya escribí sobre [qué cambia cuando la herramienta no la eliges tú](/es/blog/the-tool-youre-allowed-to-use); este es uno de los sitios donde más aprieta, porque el bloqueo no es técnico y no hay ingeniería que lo quite.

**El prompt es un coste, y no donde crees.** El prompt que funciona de verdad no es el que escribirías en un fichero. Es al que llegaste tras seis rondas de corregirlo en una ventana de chat, mirando una salida, viendo que se desviaba, apretando una cláusula. Ese bucle es la razón de que funcione. Congelarlo en un script es comprometerte con él justo en el momento en que menos seguro estás de que sea el bueno — y lo que el script elimina es precisamente el bucle que te llevó hasta ahí.

**La forma de la salida es un coste.** Un script quiere salida estructurada que pueda escribir a un fichero. Lo que significa que ahora estás especificando esquemas JSON, gestionando fallos de parseo y decidiendo qué hacer con la fila 213, y le has añadido un problema de serialización a una tarea que no lo tenía, porque quien va a consumir esas cuatrocientas respuestas es una persona que iba a leerlas.

Suma todo eso y el término de construcción honesto para un trabajo difuso de cuatrocientas filas no son veinte minutos. Es una tarde, una decisión que quizá no estés autorizado a tomar, y un compromiso con un prompt que todavía estabas editando. Por eso existe la carpeta.

## Qué quiere realmente esta banda

Con esa forma, la pregunta interesante no es *cómo construyo el pipeline más rápido*. Es *qué quiere esta banda, si no es un pipeline*.

Quiere que se quite la repetición y que el bucle siga entero. La misma interfaz, el mismo modelo, el mismo historial de conversación, los mismos ojos sobre la salida según aparece — solo que sin tu mano en el pegar. El término de comprobación se queda donde comprobar es más barato, que es una persona leyendo resultados en el sitio donde ya lee resultados, en el orden que ella controla, y pudiendo parar en la fila treinta porque la fila treinta reveló que el prompt estaba mal.

Es una ambición más pequeña que un pipeline y es la correcta para esta banda. Un pipeline es la respuesta buena cuando el trabajo se repite para siempre, y entonces sus reintentos, sus logs y su capacidad de retomar se ganan el sitio. Por debajo de eso vale [el mismo argumento que hice sobre pruebas de navegador exploratorias frente a scripts](/es/blog/playwright-cli-vs-scripts-ai-agents): el script es el artefacto correcto cuando vas a ejecutarlo muchas veces y el criterio es estable, y el equivocado cuando todavía estás descubriendo qué significa «correcto».

Debería decir dónde estoy parado, porque es una razón para descontar esta sección. Construí una cosa que hace exactamente esto: **Prompt Scripter ejecuta un prompt sobre una lista de filas dentro del chat que ya usas — ChatGPT, Claude o Gemini — sin mover el trabajo a una hoja de cálculo ni pasar por una API.** Ese es todo el argumento de venta y no lo voy a adornar. Es una extensión de Chrome, es nueva, y no tengo ninguna medición de tiempo ahorrado, así que no voy a afirmar ninguna. El razonamiento de arriba es la razón por la que la construí. Si el razonamiento está mal, la herramienta está mal también, y deberías decirlo.

## Dónde seguiría escribiendo el script

Que el umbral se mueva no significa que haya desaparecido. Cuatro sitios donde el pipeline es sencillamente la respuesta mejor:

- **Cuando el trabajo se repite con un calendario.** La amortización es real. Semanal para siempre le gana a cualquier bucle interactivo, y el coste de construcción se divide entre todas las ejecuciones futuras.
- **Cuando la salida alimenta a un sistema, no a una persona.** Si la respuesta de la fila 213 acaba en una base de datos, necesitas esquemas, validación y una política de reintentos, y una ventana de chat es mal sitio para conseguir cualquiera de las tres.
- **Cuando el juicio es en realidad determinista.** Una cantidad sorprendente de «que decida el modelo» es una regla que todavía no has escrito. Escribe la expresión regular. Es más rápida, es gratis y la puedes testear.
- **Cuando N es de verdad grande.** A cierta escala la comprobación por fila tiene que pasar de leer a muestrear y hacer estadística, y en cuanto muestreas quieres la infraestructura que hace que muestrear signifique algo.

Y el límite del otro extremo, que importa igual: **por debajo de unas pocas decenas de filas, hazlo a mano.** Plantillar el prompt, separar las columnas y decidir qué significa una fila de cabecera te va a costar más que treinta pegados. La banda tiene suelo además de techo, y fingir lo contrario es como se acaba automatizando una tarea que habrías terminado en diez minutos.

## Límites

Quiero ser exacto sobre en qué se apoya este argumento y en qué no.

Se apoya en la estructura, no en datos. No he medido tiempo de construcción, ni de comprobación, ni rendimiento de nada de lo descrito aquí, y la tabla de arriba es una forma, no un resultado. Cuando sí tengo cifras lo digo, y enseño tanto las que encogieron como las que crecieron — eso fue lo que pasó cuando [medí qué compra realmente el andamiaje prescriptivo](/es/blog/the-scaffolding-you-pay-for), y la versión honesta era menos favorecedora que la corazonada. Este texto no tiene detrás una medición equivalente, así que léelo como un razonamiento que puedes contrastar con tu propia carpeta, no como un hallazgo.

También asume que el término de comprobación es real, lo cual solo es cierto si de verdad compruebas. Si nadie lee las cuatrocientas salidas, el argumento se cae — pero también se cae el valor del trabajo, y [ese fallo es más silencioso de lo que la gente espera](/es/blog/nobody-will-check-behind-you).

## La prueba

Antes de escribir el script, hazte una pregunta: **¿qué tendría que leer para saber que ha funcionado?**

Si la respuesta es «tres salidas y después me fío de la regla», tienes un trabajo determinista. Escribe el script. El término de comprobación es casi cero y la aritmética que todo el mundo recuerda a medias es la aritmética correcta.

Si la respuesta es «todo», no tienes un problema de pipeline. Tienes una cola, y lo único que merece la pena quitarle es la parte que no es leer.

Mira lo que hay en tu carpeta. Casi todo está en la segunda categoría.

---

*Relacionado: [la atención como moneda real en construir o comprar](/es/blog/build-vs-buy-attention), [verificar resultados en vez de implementaciones](/es/blog/results-oriented-programming), [cuándo un script le gana a la exploración interactiva](/es/blog/playwright-cli-vs-scripts-ai-agents), y [por qué envolver una secuencia fija en una conversación es solo un formulario caro](/es/blog/expensive-form). Si estás calculando dónde cae esta línea en tu equipo, [eso es de lo que me ocupo](/es/mentoring).*
