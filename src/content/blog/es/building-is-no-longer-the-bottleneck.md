---
title: "Construir ya no es el cuello de botella"
description: "La IA ha abaratado radicalmente construir software, pero no encontrar clientes, validar el valor ni conseguir atención. Cuando hacer otra feature es lo fácil, el trabajo incómodo empieza al salir del editor."
pubDate: 2026-09-06
tags: ["IA", "Producto", "Distribución", "Emprendimiento", "Side Projects"]
lang: es
translationKey: building-is-no-longer-the-bottleneck
heroImage: "/blog/building-is-no-longer-the-bottleneck.png"
linkedinLinks:
  - label: "Prompt Scripter"
    url: "https://prompt-scripting-website.vercel.app"
---

Nunca había sido tan fácil construir software. Puedo describir una idea, pedir un prototipo y tener algo funcionando antes de haber decidido del todo para quién es. Con algo más de trabajo, ese prototipo puede convertirse en un MVP; con bastante menos trabajo del que habría requerido hace unos años, puede incluso acabar en producción.

Lo que no puedo pedirle a la IA es que haga que alguien lo quiera.

Puede ayudarme a escribir mensajes, preparar una landing o buscar posibles usuarios. Pero alguien tiene que abrir el mensaje. Alguien tiene que confiar lo suficiente para probar una herramienta nueva, dedicarle tiempo y contarme qué parte le sirve. Y yo tengo que salir a buscar a esa persona, escuchar una respuesta que quizá no me guste y distinguir un cumplido educado de una señal real de valor.

La IA ha comprimido el tiempo de construcción mucho más que el tiempo de distribución. El cuello de botella se ha movido. El problema es que muchos de los que sabemos construir —yo incluido— seguimos actuando como si no se hubiera movido.

## Dos relojes que ya no avanzan a la misma velocidad

Antes, una nueva funcionalidad tenía un coste suficientemente alto como para obligarte a pensarlo. Había que diseñarla, programarla, probarla y desplegarla. Hoy puedo poner a un agente a trabajar en ella mientras otro revisa los casos límite. La distancia entre «se me ha ocurrido» y «ya existe» se ha reducido de forma brutal.

La distancia entre «ya existe» y «alguien lo usa» no.

Conseguir diez conversaciones relevantes sigue requiriendo encontrar a diez personas, darles una razón para escucharte y encajar en sus agendas. Una prueba de cinco minutos puede costar días de coordinación. Un cliente no aparece porque el coverage haya subido o porque el onboarding tenga mejores animaciones.

Son dos relojes distintos:

- El reloj de construcción se ha acelerado con la IA.
- El reloj humano —atención, confianza, adopción— apenas lo ha hecho.

Eso cambia qué significa avanzar. Un día entero programando puede producir mucho software y cero evidencia. Una conversación de veinte minutos puede no producir una sola línea de código y cambiar por completo lo que merece la pena construir.

## La procrastinación que parece trabajo

Cuando no tienes experiencia vendiendo ni distribuyendo, la asimetría se vuelve una trampa perfecta.

Construir es cómodo. Sé cuándo he terminado una tarea. Hay un diff, una pantalla nueva, un test que pasa. Incluso cuando algo falla, el fallo suele ser legible: puedo reproducirlo, aislarlo y corregirlo. Cada sesión deja una prueba visible de progreso.

Distribuir es ambiguo. Puedo escribir a veinte personas y no recibir respuesta. Puedo enseñar el producto y no saber si el «está muy bien» significa interés o cortesía. Puedo elegir mal el canal, el mensaje, el público o el momento. No hay una consola que me diga cuál de los cuatro falló.

Así que resulta facilísimo negociar conmigo mismo: antes de enseñarlo, arreglo este caso límite; antes de publicarlo, rehago la landing; antes de pedir una prueba, añado exportación; antes de venderlo, necesito que se vea más profesional.

Todo suena responsable. Todo genera trabajo real. Y todo puede ser una forma sofisticada de no arriesgarme a descubrir que nadie lo necesita.

La IA hace esta evasión todavía más peligrosa porque abarata cada excusa. Antes, la feature innecesaria al menos dolía lo suficiente para frenarte. Ahora puedes acumularlas a una velocidad que se siente como impulso.

## VitaminD Explorer: mucho producto no equivale a mucha validación

Lo he vivido con [VitaminD Explorer](https://getvitamind.app). Empezó como un artifact de Claude que respondía a una pregunta que yo mismo tenía y acabó convertido en una PWA en seis idiomas, con visualizaciones, datos meteorológicos, notificaciones y un servidor MCP. [Ya conté cómo creció de prototipo a producto](/es/blog/from-artifact-to-pwa-vitamind); técnicamente, es el tipo de proyecto del que es fácil sentirse orgulloso.

Pero cada mejora técnica respondía a una pregunta que yo podía resolver dentro del proyecto. ¿Puedo hacer el cálculo más preciso? ¿Puedo añadir otra visualización? ¿Puedo hacer que un asistente consulte la app directamente? Casi siempre, la respuesta era sí.

La pregunta difícil estaba fuera: ¿quién vuelve mañana?, ¿qué problema concreto le resuelve?, ¿cómo descubre que existe?, ¿qué tendría que ocurrir para que se la recomendara a otra persona?

Ninguna cantidad de código responde eso. Y construir más puede incluso aplazar la respuesta, porque aumenta la sensación de que el producto todavía no está «listo» para exponerse.

No creo que las funcionalidades añadidas fueran inútiles. Creo algo más incómodo: no sabía cuáles eran valiosas hasta que las enfrentaba con uso real. La calidad técnica y el valor para el usuario no son la misma variable, por mucho que sea más agradable trabajar sobre la primera.

## Prompt Scripter y la tentación de llegar terminado al primer contacto

Me ocurrió de nuevo con [Prompt Scripter](https://prompt-scripting-website.vercel.app). La idea inicial era bastante estrecha: una extensión de navegador para guardar prompts como plantillas reutilizables e insertarlas directamente en ChatGPT o Gemini. Resolvía una fricción reconocible para quien repite tareas con IA y no quiere reconstruir el mismo prompt en cada conversación. Ya había algo que enseñar.

Pero también había una ampliación razonable detrás de otra. Las plantillas ganaron variables, organización, importación y exportación. Después llegó la posibilidad de ejecutar una secuencia sobre varias filas o textos. Eso pidió seguimiento de cada ejecución, contadores y estados. El producto sumó autenticación, límites mensuales, una web, una lista de espera y, finalmente, suscripciones y pagos. Incluso el backend y la extensión terminaron separados para poder desplegarlos y mantenerlos de forma independiente.

No hay una feature absurda en esa lista. Ese es precisamente el problema. Cada una podía justificarse técnicamente y cada una acercaba el producto a una versión más completa. Pero también desplazaba la prueba que ninguna de ellas podía sustituir: poner la extensión delante de personas que repiten trabajo en ChatGPT o Gemini y comprobar si de verdad convertían sus prompts en plantillas, volvían a usarlas y echaban de menos el producto cuando no estaba.

Cuando finalmente lancé Prompt Scripter, la lección no fue que hubiese construido demasiado en términos absolutos. Fue que había intentado resolver por adelantado preguntas —qué límites aceptarían los usuarios, qué parte merecía pago, qué flujo repetirían— que solo el uso podía contestar. La velocidad de construcción hacía que siempre hubiese una versión aparentemente cercana que justificaba esperar un poco más.

Pero el primer contacto con usuarios no es el examen final del producto. Es parte del proceso con el que se construye.

Intentar llegar «terminado» a ese contacto invierte el orden. Obliga a decidir en solitario qué importa y después pide al mercado que confirme la decisión. Lo razonable es exponer antes una versión más estrecha, observar dónde aparece la fricción y usar esa evidencia para decidir la siguiente inversión.

Esto no significa lanzar algo roto ni trasladar el trabajo básico al usuario. Significa distinguir entre la calidad necesaria para que una prueba sea honesta y la perfección que solo sirve para retrasarla. Un MVP no tiene que hacer poco: tiene que permitir aprender algo concreto.

## El valor se descubre fuera del repositorio

«La perfección es enemiga de lo bueno» se queda corta para describir el problema. La perfección no solo retrasa el lanzamiento. Puede empujarte a perfeccionar la cosa equivocada.

Sin distribución no hay feedback. Sin feedback, el backlog se llena con tus propias intuiciones. Y cuando implementar intuiciones cuesta tan poco, el producto puede hacerse cada vez más completo y cada vez menos informado.

El recurso escaso ya no es necesariamente la capacidad de convertir una idea en software. Es la capacidad de averiguar qué idea merece convertirse en software, para quién y con qué urgencia. Eso se descubre hablando, observando, intentando cobrar, viendo dónde abandonan las personas y aceptando que algunas hipótesis no sobreviven al contacto.

La distribución no es el paso que viene después de construir el producto. Es uno de los instrumentos con los que se construye el producto correcto.

## La regla que intento aplicarme ahora

Todavía me resulta más natural abrir el editor que escribir a un posible usuario. No tengo una fórmula que elimine esa incomodidad. Sí tengo una pregunta que empieza a ayudarme:

> **¿Esta tarea mejora el producto porque alguien me ha dado una señal, o evita que tenga que ir a buscar esa señal?**

No toda feature necesita una petición literal. La visión de producto sigue importando y hay trabajo de base que los usuarios nunca van a formular. Pero cuando varias tareas consecutivas no están conectadas con ninguna observación externa, probablemente no estoy avanzando: estoy permaneciendo en el terreno en el que me siento competente.

La disciplina, para mí, consiste en alternar los bucles. Construir lo suficiente para poder aprender; distribuir lo suficiente para saber qué construir después. No dejar que la velocidad del primero me ahorre la incomodidad del segundo.

Porque ahora puedo fabricar posibilidades casi sin límite. Lo difícil —y lo valioso— es elegirlas con evidencia.
