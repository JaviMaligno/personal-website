---
title: "Lleva tu aplicación al agente"
description: "El próximo cambio de paradigma en el desarrollo de aplicaciones no es meter un agente en tu app — es meter tu app en el agente que tus usuarios ya usan. MCP es solo la fontanería actual para hacerlo."
pubDate: 2026-07-19
tags: ["Agentes IA", "MCP", "Diseño de Software"]
lang: es
translationKey: bring-your-app-to-the-agent
repoUrl: https://github.com/JaviMaligno/vitamind
---

Esta mañana le pregunté a mi asistente de IA cuándo debería salir a tomar vitamina D. Me respondió con datos de mi propia aplicación — la ventana de síntesis, la mejor hora, los minutos que necesitaría — y en ningún momento abrí la aplicación. El asistente la llamó directamente, a través del servidor MCP que le publiqué hace poco.

Ese pequeño momento es todo el argumento de este artículo. Creo que la pregunta más importante en el desarrollo de aplicaciones está cambiando silenciosamente de *"¿cómo interactúan los usuarios con mi app?"* a *"¿cómo interactúan los agentes con mi app?"* — y la respuesta a la segunda pregunta es donde va a estar la mayor parte de la palanca en los próximos años.

## Tres paradigmas, apilados

La forma en que el software se encuentra con la inteligencia ha pasado por dos fases, y creo que estamos al principio de una tercera. No son excluyentes — cada una se apila sobre la anterior — pero el centro de gravedad se mueve.

**Paradigma uno: apps para usuarios.** El modelo tradicional. Construyes una interfaz, el usuario viene a ella, la aprende y la maneja. Cada producto es su propio destino, con su propio onboarding, su propia navegación y su propio modelo mental que adquirir. Esto no va a desaparecer — pero ya no es la única puerta de entrada.

**Paradigma dos: agentes dentro de apps.** La ola que llevamos surfeando un par de años. Embebes una IA en tu producto: un chatbot, un copiloto, un asistente con herramientas que actúan sobre tu aplicación. Bien hecho, es genuinamente potente — he escrito sobre [interfaces conversacionales que renderizan sus propios widgets](/es/blog/ag-ui-third-protocol), y construyo estos sistemas para clientes. Pero fíjate en la dirección: el agente se trae *hacia dentro* de tu app. El usuario sigue teniendo que venir a ti.

**Paradigma tres: apps dentro de agentes.** La inversión. En vez de embeber un agente en tu herramienta, embebes tu herramienta en el agente — el que tu usuario ya usa todos los días. Expones las capacidades de tu aplicación para que Claude, ChatGPT o el agente custom de una empresa puedan llamarlas. El usuario no adopta una interfaz nueva, porque ya adoptó una: su IA.

## Por qué importa la inversión

**El usuario ya tiene una IA. No quiere otra app.** Cada aplicación nueva lleva un coste de adquisición: instalarla, crear una cuenta, aprender dónde está cada cosa, acordarse de que existe el martes que viene. Una herramienta añadida a un asistente que alguien ya usa a diario apenas lleva nada de eso. El asistente *es* la pantalla de inicio ahora, y conectarse a él es distribución.

**El onboarding colapsa a una descripción.** En el paradigma uno diseñas estados vacíos, tooltips y tutoriales para que un humano aprenda tu interfaz. En el paradigma tres, el "usuario" que lee tu interfaz es un modelo, y lee las descripciones de tus herramientas en milisegundos. Nadie tiene que aprender nada.

**Las capacidades componen; las pantallas no.** En cuanto tu app es un conjunto de herramientas dentro de un agente, se combina con todo lo demás que el agente alcanza. "Búscame un hueco en el calendario mañana cuando la ventana de vitamina D esté abierta" cruza mi app con un calendario — una funcionalidad que ningún producto construyó, ensamblada al vuelo por el agente. Tu app deja de ser un destino y se convierte en una capacidad, y las capacidades se multiplican entre sí.

## MCP es el estándar, no el punto

La forma obvia de hacer esto hoy es el [Model Context Protocol](https://modelcontextprotocol.io/): un servidor, y tus herramientas funcionan en Claude, en ChatGPT y en una lista creciente de runtimes de agentes. Ya he [construido servidores MCP antes](/es/blog/mcp-server-bitbucket), y es lo más parecido que tenemos a un enchufe universal para esto.

Pero el paradigma no depende de MCP. Los protocolos evolucionarán, y este tipo de conexión no tiene por qué quedarse atada a una spec. El cambio duradero es la decisión de diseño que hay debajo: *tu aplicación tiene una interfaz orientada a agentes como superficie de primera clase*, igual que el "API-first" convirtió la interfaz programática en superficie de primera clase hace quince años. Agent-first es API-first con un consumidor nuevo — uno que lee documentación de forma nativa y compone herramientas por su cuenta.

## No solo consumidores: agentes en producción

Es tentador leer esto como una historia de consumo — asistentes personales, apps de chat. En el lado empresarial es más grande.

Las empresas están metiendo agentes en sistemas productivos: pipelines que investigan, clasifican, concilian y ejecutan procesos de punta a punta. Esos agentes necesitan información y acciones, exactamente igual que un empleado humano necesita una pantalla. Si construyes una automatización para un cliente y solo tiene interfaz web, sirve a sus personas. Si además expone herramientas, sirve a sus *agentes* — ya sea Claude o ChatGPT en manos de sus empleados, o agentes custom corriendo dentro de sus flujos productivos.

Esa segunda integración es donde está el valor que compone. El software que los agentes pueden consumir se teje dentro de los procesos; el software que solo pueden consumir humanos espera a que alguien abra una pestaña.

## Un ejemplo concreto: el MCP de VitaminD Explorer

[VitaminD Explorer](https://getvitamind.app) es mi app para responder bien a una sola pregunta: *¿cuándo puede tu cuerpo sintetizar vitamina D de verdad, y cuánto tiempo necesitas fuera?* Ya conté [la historia de cómo pasó de artifact de Claude a PWA en producción](/es/blog/from-artifact-to-pwa-vitamind). Tiene gráficos, un mapa mundial, notificaciones push — una interfaz de paradigma uno completa.

Hace poco le di una interfaz de paradigma tres: un servidor MCP. Está en fase temprana — cinco herramientas de momento, todavía en desarrollo:

- `search_city` — resolver una ciudad a coordenadas
- `get_sun_times` — amanecer, atardecer, mediodía solar
- `get_current_status` — si *ahora mismo* es buen momento, con datos en vivo de UV y nubes
- `get_vitamin_d_window` — la ventana de síntesis para un día concreto y un perfil personal
- `get_vitamin_d_year` — el patrón de todo el año: meses, estaciones, "cuándo desaparece la ventana en mi latitud"

Con eso conectado, la interacción del principio de este artículo simplemente funciona. Le pregunto a mi asistente por hoy en Londres y llama a las herramientas y responde: ventana de 10:00 a 17:00, mejor hora las 13:00, unos 8 minutos de sol para 1000 UI con un índice UV máximo de cielo despejado de 6,8. Sin abrir la app, sin cambiar de pestaña. (Cada número de esa frase salió de una llamada real a las herramientas mientras escribía esto.)

La PWA no queda obsoleta — un heatmap de 47.000 celdas por latitud es trabajo para una interfaz de verdad, no para prosa. Ese es el punto de que los paradigmas se apilan: la experiencia visual y exploratoria se queda en la app; la pregunta diaria se va al agente.

## Diseñar para un lector que no es humano

Construir el servidor MCP me hizo concreta una cosa: **las descripciones de herramientas son el nuevo UX writing.** El modelo decide qué llamar, cuándo y con qué parámetros basándose únicamente en el texto que adjuntas a cada herramienta. Ese texto es tu interfaz.

Dos ejemplos de mis propias herramientas:

- La descripción de `get_vitamin_d_window` dice explícitamente: *"Solo para preguntas de un día concreto — para meses, estaciones o 'cuándo durante el año', llama a `get_vitamin_d_year` en vez de llamar a esta una vez por fecha."* Es un guardarraíl contra un agente haciendo un bucle de 365 llamadas — el equivalente a deshabilitar un botón con el que un usuario podría hacerse daño.
- Cada respuesta lleva embebido *"estimación de modelo de cielo despejado para adultos sanos; no es consejo médico"* en el propio payload, porque en un mundo mediado por agentes tu disclaimer tiene que viajar *dentro de los datos* — no controlas la pantalla en la que acaba.

Documentación de parámetros, defaults sensatos, qué herramientas separar y cuáles fusionar, qué contexto devolver para que la *siguiente* llamada sea más fácil — esto es diseño de interfaz. Las habilidades se transfieren desde UX más directamente de lo que esperarías; solo ha cambiado el lector.

## La pregunta que hacerle a tu producto

Nada de esto dice que las interfaces mueran o que los copilotos embebidos fueran un desvío. Los tres paradigmas van a coexistir, y muchas experiencias deben seguir siendo visuales y hechas a mano.

Pero hay una pregunta nueva que toda aplicación tiene que responder, y es por la que yo empezaría hoy: **si tu usuario le preguntara a su IA en vez de abrir tu app, ¿podría responderle con tu producto?**

Si la respuesta es no, en esa respuesta estará el producto de otro.

---

*[VitaminD Explorer](https://getvitamind.app) es gratis y open source ([GitHub](https://github.com/JaviMaligno/vitamind)); su servidor MCP está en desarrollo activo. Lecturas relacionadas: [Cuando el chat construye su propia interfaz](/es/blog/ag-ui-third-protocol) y [El software se está disolviendo en el modelo](/es/blog/software-dissolving-into-the-model).*
