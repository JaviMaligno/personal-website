---
title: "Frontend, backend y motor agéntico"
description: "Cuándo conviene dar a la lógica de IA un bloque propio junto al frontend y al backend de aplicación. Casos reales, antecedentes y una alternativa más sencilla."
pubDate: 2026-09-18
tags: ["Agentes IA", "Arquitectura", "Desarrollo"]
lang: es
translationKey: frontend-backend-agentic-core
heroImage: "/blog/frontend-backend-agentic-core.png"
---

En varios proyectos en los que trabajo se está repitiendo una separación. Por un lado está el frontend. Por otro, el backend que mantiene la aplicación funcionando. Y después está el motor agéntico: los workflows, los prompts, las herramientas, la gestión del contexto, los modelos y las evaluaciones que permiten saber si todo eso hace bien su trabajo.

Podría llamar «backend» a las dos últimas piezas y seguiría siendo técnicamente correcto. Pero, para trabajar sobre ellas, la distinción resulta cada vez más útil. Cambiar cómo un agente investiga una fuente de datos es un trabajo diferente de cambiar cómo un usuario revisa y acepta sus resultados. Ambos necesitan código de servidor; tienen responsabilidades y motivos para cambiar distintos.

Hablo de tres bloques de responsabilidad. Pueden vivir en un monorepo, repartirse entre repositorios o compartir proceso. Dar entidad propia al motor no obliga a convertirlo en un microservicio.

## La aplicación que rodea al agente

Un ejemplo es un [pipeline de automatización de fuentes de datos](/es/projects/data-source-automator). Su trabajo incluye investigar fuentes, proponer métodos de extracción, generar especificaciones y producir servicios. Hay varias etapas, herramientas, decisiones y puntos de revisión. También un conjunto de evaluaciones que compara los resultados de las etapas con referencias corregidas.

La aplicación desde la que se gestiona ese trabajo tiene frontend y backend propios. El backend envía trabajos al motor, consulta su estado y recupera resultados. La lógica que presenta esos resultados como parte de una aplicación tiene suficiente entidad para mantenerse separada de la lógica que los produce.

Esta es la distribución de responsabilidades que me interesa:

<style>
.fab-fig{background:#1a1a24;border:1px solid rgba(255,255,255,.1);border-radius:1rem;padding:1rem;margin:2rem 0}
.fab-fig svg{display:block;width:100%;height:auto;font-family:Inter,-apple-system,system-ui,sans-serif}
.fab-fig figcaption{color:#94a3b8;font-size:.85rem;line-height:1.55;margin:1rem .25rem .25rem;text-align:center}
</style>

<figure class="fab-fig">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 620" role="img" aria-label="Una aplicación puede separar frontend, backend de aplicación y motor agéntico. Una interfaz de acceso directo puede conectar con el motor sin un backend de aplicación separado.">
  <defs><marker id="fab-arrow-es" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="#94a3b8"/></marker></defs>
  <text x="300" y="28" text-anchor="middle" fill="#94a3b8" font-size="17">CUANDO HAY LÓGICA DE APLICACIÓN PROPIA</text>
  <rect x="35" y="49" width="530" height="76" rx="10" fill="#203237" stroke="#2dd4bf"/>
  <text x="300" y="80" text-anchor="middle" fill="#5eead4" font-size="23" font-weight="600">Frontend</text>
  <text x="300" y="107" text-anchor="middle" fill="#e2e8f0" font-size="17">Interacción · supervisión · resultados</text>
  <path d="M300 135V181" stroke="#94a3b8" stroke-width="2" marker-start="url(#fab-arrow-es)" marker-end="url(#fab-arrow-es)"/>
  <text x="320" y="164" fill="#94a3b8" font-size="16">Acciones y estado del producto</text>
  <rect x="35" y="191" width="530" height="76" rx="10" fill="#283240" stroke="#94a3b8"/>
  <text x="300" y="222" text-anchor="middle" fill="#f8fafc" font-size="23" font-weight="600">Backend de aplicación</text>
  <text x="300" y="249" text-anchor="middle" fill="#e2e8f0" font-size="17">Permisos · reglas · ciclo de vida del trabajo</text>
  <path d="M300 277V323" stroke="#94a3b8" stroke-width="2" marker-start="url(#fab-arrow-es)" marker-end="url(#fab-arrow-es)"/>
  <text x="320" y="306" fill="#94a3b8" font-size="16">Trabajos, eventos y resultados</text>
  <rect x="35" y="333" width="530" height="76" rx="10" fill="#362e23" stroke="#f59e0b"/>
  <text x="300" y="364" text-anchor="middle" fill="#fbbf24" font-size="23" font-weight="600">Motor agéntico</text>
  <text x="300" y="391" text-anchor="middle" fill="#e2e8f0" font-size="17">Workflows · contexto · herramientas · evals</text>
  <path d="M35 442H565" stroke="#475569" stroke-dasharray="5 5"/>
  <text x="300" y="478" text-anchor="middle" fill="#94a3b8" font-size="17">CUANDO LA INTERFAZ ES UNA PUERTA DE ENTRADA</text>
  <rect x="35" y="503" width="210" height="76" rx="10" fill="#203237" stroke="#2dd4bf"/>
  <text x="140" y="549" text-anchor="middle" fill="#5eead4" font-size="23">Frontend</text>
  <path d="M255 541H345" stroke="#94a3b8" stroke-width="2" marker-start="url(#fab-arrow-es)" marker-end="url(#fab-arrow-es)"/>
  <rect x="355" y="503" width="210" height="76" rx="10" fill="#362e23" stroke="#f59e0b"/>
  <text x="460" y="549" text-anchor="middle" fill="#fbbf24" font-size="23">Motor agéntico</text>
  <text x="300" y="610" text-anchor="middle" fill="#94a3b8" font-size="16">La autenticación sigue siendo necesaria en ambos casos.</text>
</svg>
<figcaption>Dos distribuciones posibles. Las cajas expresan responsabilidades; las flechas, intercambios. No fijan cuántos repositorios o procesos hacen falta ni todos los caminos de comunicación.</figcaption>
</figure>

El backend de aplicación puede tener bastante que hacer. En una aplicación documental, por ejemplo, determina quién puede abrir un expediente, qué revisión necesita y cuándo un resultado pasa a estar aceptado. El motor extrae información y aporta evidencias. Que la ejecución haya terminado no significa que el expediente esté resuelto.

En otro proyecto de lectura documental con el que trabajo, la extracción se ejecuta en un worker y el backend de la aplicación gestiona los casos y sus artefactos. Para las preguntas sobre documentos ya procesados, ese mismo backend importa el servicio de IA como librería. La separación de responsabilidades admite ambas formas de integración dentro del mismo producto.

## Un chat puede esconder un sistema entero

En los [proyectos de IA conversacional de los que escribí al hablar de interfaces que se construyen dentro del chat](/es/blog/ag-ui-third-protocol), la superficie visible es una conversación. Detrás hay captura de documentos, herramientas, verificaciones, estado persistente y procesos que necesitan intervención humana.

Parte de esos motores comparte una librería con capacidades comunes: persistencia durante la ejecución, eventos de actividad, gestión de contexto, conexión con modelos y protecciones contra bucles o fallos repetidos. Cada motor conserva las herramientas, instrucciones y estructuras propias de su dominio.

Ahí aparece otra razón para dar entidad al bloque agéntico: varias experiencias pueden reutilizar las mismas capacidades de ejecución. El núcleo compartido es una librería; cada consumidor lo incorpora a su servicio. Tener una frontera reconocible en el código ya aporta valor.

Esto también obliga a afinar qué queremos decir con «un chatbot sencillo». El chat describe cómo interactúa el usuario. Dice muy poco sobre el sistema que está usando. En [Había construido un formulario caro](/es/blog/expensive-form) conté cómo una conversación podía apoyarse en un grafo de fases, validaciones y decisiones, y aun así ofrecer una experiencia peor que un formulario. La complejidad del motor y la utilidad de la interfaz son cuestiones distintas.

## El agente también puede operar sobre la aplicación

Un [asistente integrado en una plataforma de revisión de casos](/es/projects/compliance-assistant) introduce otra relación. El analista ya está trabajando sobre un caso y abre el asistente dentro de la aplicación. Puede pedirle que consulte información, actualice datos o proponga un cambio de estado. El agente utiliza capacidades del backend para trabajar sobre ese mismo caso.

En la implementación integrada, las herramientas son adaptadores sobre operaciones del producto. Por ejemplo, la herramienta que actualiza un caso valida los datos y llama al servicio de actualización existente. La herramienta que cambia el estado comprueba que la transición esté permitida desde el estado actual. Las escrituras pasan por una tarjeta de confirmación y dejan registro de auditoría.

<figure class="fab-fig">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 380" role="img" aria-label="Las pantallas de la aplicación y las herramientas del asistente utilizan capacidades del mismo backend. El asistente propone operaciones; las escrituras requieren confirmación humana.">
  <defs><marker id="fab-assistant-es" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="#94a3b8"/></marker></defs>
  <rect x="25" y="35" width="235" height="100" rx="10" fill="#203237" stroke="#2dd4bf"/>
  <text x="142" y="74" text-anchor="middle" fill="#5eead4" font-size="23" font-weight="600">Frontend</text>
  <text x="142" y="105" text-anchor="middle" fill="#e2e8f0" font-size="17">Pantallas y panel de chat</text>
  <rect x="340" y="35" width="235" height="100" rx="10" fill="#362e23" stroke="#f59e0b"/>
  <text x="458" y="74" text-anchor="middle" fill="#fbbf24" font-size="23" font-weight="600">Asistente IA</text>
  <text x="458" y="105" text-anchor="middle" fill="#e2e8f0" font-size="17">Contexto y propuestas</text>
  <path d="M270 85H330" stroke="#94a3b8" stroke-width="2" marker-start="url(#fab-assistant-es)" marker-end="url(#fab-assistant-es)"/>
  <text x="300" y="67" text-anchor="middle" fill="#94a3b8" font-size="16">chat</text>
  <path d="M142 145V245" stroke="#94a3b8" stroke-width="2" marker-start="url(#fab-assistant-es)" marker-end="url(#fab-assistant-es)"/>
  <path d="M458 145V245" stroke="#94a3b8" stroke-width="2" marker-start="url(#fab-assistant-es)" marker-end="url(#fab-assistant-es)"/>
  <text x="162" y="190" fill="#94a3b8" font-size="16">acciones</text>
  <text x="162" y="212" fill="#94a3b8" font-size="16">habituales</text>
  <text x="438" y="190" text-anchor="end" fill="#94a3b8" font-size="16">herramientas</text>
  <text x="438" y="212" text-anchor="end" fill="#94a3b8" font-size="16">del asistente</text>
  <rect x="25" y="255" width="550" height="100" rx="10" fill="#283240" stroke="#94a3b8"/>
  <text x="300" y="295" text-anchor="middle" fill="#f8fafc" font-size="23" font-weight="600">Capacidades del backend de aplicación</text>
  <text x="300" y="328" text-anchor="middle" fill="#e2e8f0" font-size="17">Casos · validaciones · transiciones · auditoría</text>
</svg>
<figcaption>El asistente abre otra vía para operar sobre el producto. Es un esquema de responsabilidades: la conversación y las herramientas pasan por código del servidor, y las escrituras requieren confirmación en la interfaz.</figcaption>
</figure>

Aquí el backend ofrece capacidades que consumen tanto las pantallas como las herramientas del asistente. La frontera útil separa la interpretación de la petición de la ejecución de la operación de negocio. En este caso, el módulo del asistente vive dentro del propio backend de la aplicación: esa distinción existe sin un servicio agéntico separado.

Esto amplía el dibujo inicial. Una aplicación puede encargar trabajo al motor, y un agente puede usar operaciones de la aplicación como herramientas. Ambas relaciones pueden convivir. Los tres bloques ayudan a repartir responsabilidades, pero no imponen una cadena de llamadas única.

## El caso en el que bastaban dos bloques

El antiguo frontend de un [clasificador de actividad empresarial](/es/projects/compliance-classifier) era una puerta de entrada al agente: enviar una consulta y ver la clasificación. Apenas había lógica intermedia más allá de autenticar el acceso.

Ese caso encajaba bien como frontend más servicio del agente. Añadir un backend de aplicación separado habría necesitado una responsabilidad concreta que justificara mantenerlo.

«Acceso directo» significa aquí que el frontend se comunica con el servicio que ejecuta el agente. Las credenciales del proveedor y la ejecución de las herramientas siguen en el servidor. El cliente de interfaz presenta resultados y eventos; el motor prepara contexto y ejecuta el trabajo.

Este ejemplo me parece tan útil como los anteriores, porque evita convertir una observación práctica en una receta universal. Incluso un motor complejo puede tener una interfaz de acceso muy ligera.

## Qué tiene de nuevo

La separación entre una aplicación y un motor de procesamiento tiene antecedentes claros. El patrón [Web–Queue–Worker](https://learn.microsoft.com/en-us/azure/architecture/guide/architecture-styles/web-queue-worker) ya distingue la atención de peticiones del trabajo largo o intensivo. Las aplicaciones con servicios de inferencia también conocen esa frontera.

En el ecosistema de agentes hay referencias explícitas. [LangGraph Cloud se presentó en junio de 2024](https://www.langchain.com/blog/langgraph-cloud) con persistencia, trabajos en segundo plano, streaming y colaboración humana. La [arquitectura de CopilotKit](https://docs.copilotkit.ai/concepts/architecture) describe frontend, runtime dentro del servidor de aplicación y backend del agente. Ese runtime cubre la integración con la interfaz; el backend de negocio puede tener responsabilidades más amplias.

Lo que estoy viendo en mis proyectos es que la lógica de IA adquiere suficiente entidad para necesitar un ciclo de ingeniería propio. Cambiar un modelo o un prompt exige evaluar la calidad de los resultados, además de comprobar que las llamadas funcionan. Un flujo puede terminar sin errores y haber elegido mal una herramienta, omitido un dato o consumido demasiado presupuesto.

Ese ciclo combina tests de software, evaluaciones sobre casos representativos e inspección de ejecuciones. Es una razón para reconocer el motor como bloque, aunque comparta infraestructura con la aplicación. La separación sigue necesitando trazabilidad de extremo a extremo: una ejecución debe poder relacionarse con el trabajo del usuario que la originó.

No he encontrado un nombre único consolidado para esta distribución exacta. «Frontend, backend de aplicación y motor agéntico» describe lo que quiero señalar. Además, parte de ese motor puede ser un workflow cuyo recorrido fija el código. La [distinción de Anthropic entre workflows y agentes](https://www.anthropic.com/engineering/building-effective-agents) es útil aquí: esta frontera puede tener sentido en ambos casos.

## Qué frontera merece la pena dibujar

La centralidad de la IA en el producto y su complejidad ayudan a decidir, pero ninguna basta por sí sola. Una aplicación puede vivir de una única operación de IA sencilla. Otra puede incluir la investigación automatizada como función secundaria y necesitar varios workflows complejos para ofrecerla.

Me fijaría en señales concretas:

- La lógica de IA tiene herramientas, contexto y evaluaciones que cambian con independencia del resto del producto.
- Las ejecuciones necesitan durar, reanudarse o esperar intervención humana más allá de una petición web.
- Varios procesos o experiencias reutilizan el mismo motor o sus capacidades comunes.
- La aplicación tiene permisos, revisiones y estados de negocio que conservan su sentido aunque cambie cómo trabaja el agente.

Las tres primeras dan peso al motor. La última da peso al backend de aplicación. El caso del clasificador ilustra por qué conviene hacerse ambas preguntas.

La frontera tampoco se dibuja por tecnologías. El motor puede tener APIs, colas y mucho código determinista. El backend puede administrar configuraciones y documentos que consumen los agentes. Una herramienta puede invocar una operación de negocio cuyos permisos y reglas valida el servicio responsable de esa operación.

Lo que necesita quedar claro es quién decide qué, qué estado mantiene cada parte y qué contrato permite que colaboren. Ese contrato incluye entradas y resultados, pero también progreso, errores, cancelación y revisión cuando el producto los necesita.

Separar procesos añade costes: fallos de comunicación, versiones compatibles y sincronización. Si un reintento crea dos trabajos, tener tres cajas bien dibujadas no resuelve el problema. Por eso empezaría por una frontera entre módulos y separaría despliegues cuando hubiera una razón operativa.

Para una función pequeña puede bastar un módulo de IA dentro del backend. Para una interfaz cuya única tarea es dar acceso al agente, puede bastar su servicio. Cuando tanto el producto como el motor acumulan responsabilidades propias, reconocer los tres bloques ayuda a trabajar sobre cada uno sin arrastrar innecesariamente a los demás.

La pregunta que me resulta útil al revisar estos proyectos es: **si mañana cambiamos cómo trabaja el agente, ¿qué tendría que cambiar en la aplicación, y por qué?** La respuesta dice bastante más sobre la arquitectura que contar repositorios.
