---
title: "Hace falta un producto para mandar mensajes"
description: "El trabajo que nunca se automatiza no es el difícil. Es el repetitivo que además pide un juicio en cada fila, y que ya se hace a mano dentro de una ventana de chat. Cualquier forma de dejar de hacerlo a mano te obliga a montar antes un producto: una cuenta con factura por tokens, un prompt que ahora hay que probar llamada a llamada de pago, y una interfaz para quien tenga que leer los resultados."
pubDate: 2026-09-13
tags: ["IA", "Automatización", "LLM", "Herramientas", "Producto"]
lang: es
translationKey: too-small-to-automate
heroImage: "/blog/too-small-to-automate.png"
linkedinLinks:
  - label: "Prompt Scripter — Chrome Web Store"
    url: "https://chromewebstore.google.com/detail/aamjoicocabhfkomhejfkmnkjkdomadg"
  - label: "Prompt Scripter"
    url: "https://promptscripter.javieraguilar.ai"
---

Ciento cincuenta mensajes de soporte, cada uno con una decisión: ¿problema de facturación o problema de acceso? Noventa campos de texto libre que hay que reescribir en el tono de la casa sin inventarse nada. El trabajo se repite y cada fila pide un juicio, y por eso ya se está haciendo dentro de una ventana de chat: mensaje a mensaje, a mano, con alguien que lee cada respuesta según llega y que en la fila treinta se daría cuenta de que el tono se ha torcido.

Casi nadie automatiza eso. Y no es porque sea difícil.

## Dos cosas que llamamos difíciles

Hay dos dificultades que comparten palabra, y el argumento se rompe si se dejan mezclar. Una es la intelectual: el problema que todavía no sabes resolver. Esa es la que de verdad se resiste a un script, porque no se puede escribir un procedimiento que no tienes — y encima es la que se lleva la atención, porque es interesante.

Lo de arriba es la otra cosa, y no se parece en nada. Cada fila es fácil: una decisión, dos segundos, evidente para cualquiera que conozca el dominio. Lo que la vuelve insoportable es que hay ciento cincuenta y que en todas tiene que haber una persona delante. No tiene nada de difícil. Es repetitiva *y* pide juicio, y lo que la deja varada es la pareja: quita cualquiera de las dos mitades y estaría resuelta desde hace años.

Ya he escrito que cuando un equipo copia el contexto a un chat y devuelve la respuesta a mano, [la persona es la capa de integración](/es/blog/stop-being-the-cable). Allí la solución suele ser un conector que nadie se acordó de pedir. Aquí no hay nada que instalar, porque lo que se repite no es una llamada a un sistema. Es un mensaje.

## La desproporción

¿Por qué sigue siendo manual, entonces? Por lo que te piden construir a cambio. El trabajo consiste en pegar una fila en un chat, leer la respuesta y pegar la siguiente. En cuanto quieres dejar de hacerlo con las manos, todas las salidas disponibles te sacan del chat y te ponen delante un producto que montar. Una cuenta de proveedor, una clave de API y una factura que cuenta tokens. Un prompt que ahora hay que probar como se prueba el código, salvo que cada prueba es una llamada que se paga y al final no hay ninguna marca verde esperando. Y una salida que tiene que leer una persona, lo que significa una presentación, lo que significa una interfaz con sus filas, su paginación y un inicio de sesión por delante.

Eso es un producto. Para mandar mensajes por un chat.

La aritmética que casi todos llevamos encima es [la tabla de xkcd](https://xkcd.com/1205/), *Is It Worth the Time?*: cuánto tiempo puedes dedicarle a automatizar algo antes de gastar más de lo que ahorras. Es una buena tabla y nada de esto la contradice. Lo que pasa es que le pone precio al único término que ya se ha desplomado. Escribir el bucle no es el problema: un agente de código lo escribe antes de que termines de especificarlo, que es buena parte de lo que quiero decir cuando digo que [construir ya no es el cuello de botella](/es/blog/building-is-no-longer-the-bottleneck). Los tres costes de arriba sobreviven intactos a eso, y ninguno de ellos es código.

## Lo que construí en su lugar

[Prompt Scripter](https://promptscripter.javieraguilar.ai) — [en la Chrome Web Store](https://chromewebstore.google.com/detail/aamjoicocabhfkomhejfkmnkjkdomadg) — coge un prompt con huecos — `{{ sector }}`, `{{ pais }}` — y una lista de filas, y manda un mensaje por fila a la conversación que ya tienes abierta, en ChatGPT, Claude o Gemini. Espera a que cada respuesta termine antes de mandar la siguiente. Las respuestas caen en el hilo, que es donde ya las estabas leyendo.

Lo que no es, dicho sin adornos, porque esta categoría está llena de cosas que prometen más: no encadena pasos, no tiene ramas ni reglas, y ninguna fila ve la respuesta de la anterior — todos los mensajes se renderizan antes de que salga el primero. No puntúa nada, no decide qué respuestas son buenas y no corre desatendida: si cierras la pestaña, la ejecución muere con ella. El juicio se queda donde ya estaba, delante de una persona que lee un hilo.

El resto del artículo son los tres costes que la extensión viene a evitar. Ninguno de los tres es el bucle de veinte líneas de Python.

## La factura que antes no tenías

Para pasar una fila por un modelo desde un script hace falta una credencial propia. Elegir proveedor, dar de alta un método de pago, guardar una clave en algún sitio que no sea el repositorio — y a partir de ahí cada fila y cada reintento tienen precio unitario. Una tarde de trabajo de oficina se convierte en una partida presupuestaria con alguien vigilando el gasto. En casa es una molestia; en una empresa es una conversación con compras, y si no eres tú quien decide qué te dejan usar, es una conversación que puedes perder.

La forma obvia de hacer soportable esa factura es bajar de modelo, y es justo el movimiento contra el que más avisaría. Llevé la misma tarea por modelos cada vez más flojos y medí que [lo caro era la capacidad](/es/blog/it-was-never-the-restriction): el más débil no fue a mirar ni una sola vez y firmó catorce informes dando por publicada una versión que no existía. Los tokens baratos, en un trabajo que pide juicio, compran respuestas muy seguras de sí mismas que nadie ha comprobado.

La extensión se salta la partida entera porque su llamada al modelo no es una llamada de red suya. Escribe en la página y pulsa enviar: la inferencia la hace ChatGPT, Claude o Gemini, en tu pestaña, con la suscripción que ya pagas. Ni clave que conseguir, ni proveedor que elegir. Cuenta propia sí tiene, y prefiero decir lo que cuesta: una tarifa plana con topes de plantillas, ejecuciones y filas, no un contador de tokens; un bucle que, en una página de chat, corre igual sin haber iniciado sesión; y, cuando sí la has iniciado, tus filas viajando por HTTPS a un servidor mío, con la entrada de cada fila y la respuesta del modelo guardadas como resultados de esa ejecución.

## Un prompt es código que no se puede leer

Meter un prompt en un fichero y versionarlo no es el problema, y quiero ser exacto aquí porque la versión chapucera de este argumento dice que el fichero congela algo. No congela nada. Para eso está el control de versiones: un prompt vive en un repositorio como cualquier otra cosa y se edita como cualquier otra cosa.

El coste es que un prompt es código no determinista, y el código no determinista no se comprueba leyéndolo. Se comprueba ejecutándolo, y una ejecución no vuelve como una aserción que ha pasado. Vuelve como un texto que alguien tiene que juzgar. Ni rojo ni verde: una persona leyendo salidas y decidiendo si están bien, que es exactamente la actividad que la automatización venía a quitar, mudada al banco de pruebas. Y el bucle que hace que un prompt acabe funcionando — reformular, quitar la frase que lo volvía farragoso, añadir un ejemplo, volver a probar — son N ejecuciones sobre M casos, todas facturadas, antes de que salga la primera fila útil.

Por eso [el prompt es el último 10%](/es/blog/llm-as-judge-three-decisions): el primer 90% es decidir qué mides, sobre qué y con qué a la vista. Y es también lo que sobrevivió a la muerte del prompt engineering como artesanía — [el valor nunca estuvo en el fichero de texto](/es/blog/death-of-prompt-engineering), está en la estructura alrededor del bucle, y esa estructura es justamente el producto que no querías montar.

El atajo tentador es poner a otro modelo a juzgar, para que el bucle se cierre sin ti dentro. Eso también lo medí: [las mismas 45 comparaciones ciegas, tres jueces, tres rankings distintos](/es/blog/three-judges-three-rankings), cada juez prefiriendo sus propias respuestas y, en las tareas subjetivas, coincidiendo al nivel del azar. Cada uno de esos 378 juicios fue una llamada de pago, y justo en el tipo de pregunta del que va este artículo el juez resulta ser un participante y no un instrumento. Construir la referencia contra la que comparar tampoco sale más barato: en tres estudios [todos los instrumentos que construí se rompieron al menos una vez, siempre hacia el resultado que esperaba](/es/blog/the-instrument-fails-in-your-favour), y una referencia generada a la ligera te devuelve [el número que querías](/es/blog/the-grader-knew-less).

Lo que evita la extensión no es probar. Es tener que montar el banco de pruebas en otro sitio y pagar cada vuelta aparte. El prompt que automatizas es el que ya afinaste a mano en ese mismo chat, mirando respuestas reales, dentro de una tarifa plana: hay un botón en tus propios mensajes que convierte uno en plantilla. La prueba y el error ocurren donde ya ocurrían; la herramienta los recoge al final en vez de abrir un segundo sitio donde hacerlos.

## Alguien tiene que leer esto

Serializar JSON es trivial, y lo es desde hace veinte años. El problema es para quién es ese JSON. Quien tiene que leer ciento cincuenta respuestas no va a abrir un array de objetos. Quiere la entrada al lado de la salida, saltar a la fila 90, releer una respuesta larga sin tropezar con comillas escapadas y encontrarlo todo ahí mañana. Eso es una vista: emparejar, paginar, texto legible. Es una aplicación. Y una aplicación que guarda las filas de otra gente arrastra todo lo demás — cuentas, permisos, retención.

Esa factura la he pagado. Montando un flujo de KYC conversacional acabamos manteniendo a mano [nuestro propio formato de interrupt y un registro de widgets](/es/blog/ag-ui-third-protocol), hasta que apareció un estándar que lo hacía por nosotros. Ese es el precio honesto de presentarle la salida de un modelo a alguien que no eres tú.

La extensión no construye nada de eso, porque la salida aparece donde ya se estaba leyendo: las respuestas llegan al hilo como mensajes normales, con el formato de la propia plataforma — títulos, listas, bloques de código, botón de copiar. No hubo que diseñar ninguna pantalla, porque la pantalla ya estaba puesta. Hay una exportación a CSV en el servidor para cuando quieras el fichero. Pantalla no hay, porque la pantalla ya estaba puesta.

## Dónde sí escribiría el script

Nada de esto elimina el umbral; simplemente no es el punto, así que aquí va en corto. Escribe la tubería cuando el trabajo se repite en un calendario para siempre y el coste de construirla se divide entre todas las veces futuras. Escríbela cuando la salida alimenta a un sistema y no a una persona, porque entonces sí quieres esquemas, validación y política de reintentos. Escríbela cuando el juicio resulta ser determinista después de todo — buena parte de "que decida el modelo" es una regla que nadie ha escrito todavía, y la expresión regular es más rápida y gratis. Y escríbela cuando N es tan grande que comprobar deja de ser leer y pasa a ser muestrear.

Hay suelo además de techo, y del suelo se acuerda menos gente: por debajo de cierto número de filas, describir el trabajo *es* el trabajo. Si habrías terminado la lista antes de terminar de explicarla, había que terminar la lista.

## La dirección

Lo que no dejo de ver es que todas las salidas disponibles apuntan hacia fuera. El trabajo ocurre en un chat, y cualquier forma de dejar de hacerlo a mano propone un destino nuevo: una consola, un panel, una plataforma con su inicio de sesión, su factura y su pestaña en el navegador de alguien. He defendido lo contrario para los productos en general — [meter tu aplicación dentro del agente que tus usuarios ya usan](/es/blog/bring-your-app-to-the-agent) en vez de pedirles que vengan a ti — y esto es ese mismo argumento girado hacia dentro, hacia el trabajo propio. Si el trabajo vive en el chat, la automatización se queda en el chat.

Prompt Scripter es ese argumento con una herramienta detrás. Es nuevo, no he medido nada sobre el tiempo ahorrado y no voy a afirmar una cifra que no tengo. La desproporción de arriba es la razón entera de que exista; si la desproporción no es real, la herramienta tampoco, y prefiero que me lo digan.

La prueba que le aplicaría a tu propia versión de este montón de trabajo: escribe lo que tendrías que construir para dejar de hacerlo a mano. Si la lista sale como una cuenta de proveedor, un banco de pruebas y una interfaz — y el trabajo es mandar mensajes por un chat —, la lista es el argumento.

---

*Relacionado: [la persona como capa de integración](/es/blog/stop-being-the-cable), [lo que cuesta de verdad un juez LLM](/es/blog/three-judges-three-rankings), [lo que cuesta construir la referencia](/es/blog/the-instrument-fails-in-your-favour) y [meter tu aplicación dentro del agente](/es/blog/bring-your-app-to-the-agent). [Prompt Scripter](https://promptscripter.javieraguilar.ai) está en la [Chrome Web Store](https://chromewebstore.google.com/detail/aamjoicocabhfkomhejfkmnkjkdomadg).*
