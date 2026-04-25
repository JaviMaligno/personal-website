---
title: "El software se está disolviendo en el modelo"
description: "Lo que escribimos se está convirtiendo en skills en markdown, lo que ven los usuarios se está convirtiendo en píxeles generados, y el medio cada vez es más fino. Una mirada a hacia dónde va el software en 2026."
pubDate: 2026-04-25
tags: ["IA", "Agent Skills", "UI Generativa", "Software", "Tendencias"]
lang: es
translationKey: software-dissolving-into-the-model
---

Dos repositorios me llamaron la atención este mes. El primero es [`google/agents-cli`](https://github.com/google/agents-cli), la herramienta oficial de Google para construir agentes en Google Cloud — un CLI más un paquete de "skills" en markdown que cualquier asistente de código (Claude Code, Codex, Gemini CLI, Cursor) puede cargar. El segundo es [Flipbook](https://flipbook.page/), un "navegador" experimental que un equipo de ex-OpenAI lanzó hace dos días. Flipbook no tiene HTML, ni DOM, ni componentes renderizados. Cada píxel que ves — incluido el texto — lo genera fotograma a fotograma un modelo de difusión de vídeo que streamea por WebSocket.

Parecen pertenecer a conversaciones distintas. No lo son. Si los pones uno al lado del otro aparece un patrón: la capa que llamábamos "software" se está estrujando por los dos extremos. Lo que escribimos se está convirtiendo en markdown. Lo que ven los usuarios se está convirtiendo en una salida del modelo. El medio cada vez es más fino.

## Lo que escribimos se está convirtiendo en markdown

Las skills son repositorios de instrucciones, no servicios desplegados. El runtime es el asistente de código que el usuario tenga instalado. El artefacto es un fichero `SKILL.md` con quizá un par de scripts auxiliares.

Solo las últimas semanas ya cuentan la historia:

- [`OthmanAdi/planning-with-files`](https://github.com/othmanadi/planning-with-files) es una skill para Claude Code que da al agente un workflow de planificación persistente al estilo Manus — unos cuantos ficheros markdown que definen cuándo escribir `task_plan.md`, `findings.md`, `progress.md`. Tiene 9.2k estrellas. Manus, la empresa que llevó ese workflow a producto, fue [adquirida por una cifra del orden de 2.000 millones de dólares](https://aibit.im/blog/post/planning-with-files-manus-style-claude-code-plugin). La propiedad intelectual era el patrón, no la implementación.
- [`VoltAgent/awesome-agent-skills`](https://github.com/VoltAgent/awesome-agent-skills) cura más de 1.000 skills portables compatibles con Claude Code, Codex, Gemini CLI, Cursor y otros 40+ agentes. 18.7k estrellas.
- GitHub lanzó [`gh skill`](https://github.blog/changelog/2026-04-16-manage-agent-skills-with-github-cli/) el 16 de abril — una primitiva nativa del CLI para instalar, fijar y publicar skills directamente desde repositorios de GitHub.
- El CLI oficial de Google Workspace ahora incluye [más de 100 ficheros `SKILL.md`](https://github.com/googleworkspace/cli), uno por cada API soportada, más 50 recetas curadas para Gmail, Drive, Docs, Calendar y Sheets.

Hace un año, "lanzar una herramienta para X" significaba construir un SDK, un servicio o al menos una librería envoltorio. Hoy cada vez más significa escribir una carpeta de markdown que cualquier agente puede cargar bajo demanda. La tendencia no es "la IA te ayuda a escribir software". Es "lo que llamábamos software ahora es un conjunto de instrucciones".

## Lo que ven los usuarios se está convirtiendo en salida del modelo

Ahora mira el otro extremo del pipeline. Está haciendo lo mismo.

Flipbook se lanzó el 23 de abril desde el equipo de Zain Shah (ex-OpenAI, ex-Humane, ex-Apple), parte de South Park Commons. La interfaz se genera píxel a píxel con [LTX Video](https://github.com/Lightricks/LTX-Video), un transformer de difusión open source para vídeo, optimizado para hacer streaming a 1080p/24fps por WebSocket desde GPUs serverless de Modal Labs. No hay DOM. No hay botones en el sentido tradicional. Cuando "haces clic", el modelo genera los siguientes fotogramas.

DeepMind lleva haciendo lo mismo a escala de world-model. [Project Genie](https://blog.google/innovation-and-ai/models-and-research/google-deepmind/project-genie/) salió para suscriptores de AI Ultra en enero de 2026, basado en Genie 3. Escribes un prompt. Te mueves por un mundo generado que se va generando según te mueves, a 24fps, con coherencia mantenida durante unos minutos.

Son demos. Flipbook todavía es apenas útil como producto. Los mundos de Genie duran un minuto o dos antes de que el modelo pierda coherencia. Pero la dirección se ve más clara que los productos: la salida renderizada de una aplicación se está convirtiendo en una inferencia del modelo, no en un árbol de componentes.

## Los que tenemos que adaptarnos somos nosotros

Un compañero me contó esta semana que llevaba tiempo intentando que un LLM escribiera informes internos siguiendo las guías de estilo exactas de su empresa. Tras suficiente iteración se dio cuenta de que el esfuerzo de prompt engineering para mantener al modelo dentro del raíl le estaba llevando más tiempo que escribir los informes él mismo — y su empresa tiene varios tipos de informes así.

Lo que dijo después se me quedó: *"Quizá el problema no es que la IA no se adapte. Quizá los que tenemos que adaptarnos somos nosotros. Estamos haciéndola menos eficiente con tantas restricciones, cuando lo que produce por su cuenta es lo bastante bueno para el propósito".*

Esa intuición no va realmente de informes. Es lo que está pasando en los dos extremos del stack ahora mismo.

Una skill en markdown es lo que sale cuando dejas de intentar forzar al modelo a la forma de un SDK tipado con interfaces versionadas y empiezas a escribir en el medio en el que el modelo realmente funciona bien: lenguaje natural con ejemplos. Flipbook es lo que sale cuando dejas de intentar forzar al modelo a emitir componentes React válidos y le dejas renderizar los píxeles directamente.

La fricción que estábamos añadiendo — APIs tipadas, UIs deterministas, glue code escrito a mano — nos compraba corrección, pero a un coste que no estábamos contabilizando. Cada restricción también cuesta throughput, y muchas de esas restricciones existían porque las necesitábamos *nosotros*, no porque las necesitase el modelo.

Eso no significa que la corrección desaparezca. Significa que la reubicamos. Los evals reemplazan a los tipos. Las instrucciones de la skill reemplazan a la documentación del SDK. Los objetivos a nivel de fotograma reemplazan a las specs Figma de píxel perfecto. Cambiamos un tipo de rigor por otro que encaja mejor con la herramienta.

## Qué sobrevive en el medio

Si lo que escribimos se está volviendo skills y lo que ven los usuarios se está volviendo píxeles, ¿qué queda para los que construimos cosas en el medio?

Llevo dándole vueltas en el contexto de mi propio trabajo.

Los servidores MCP que he construido — [`mcp-server-bitbucket`](https://github.com/JaviMaligno/mcp-server-bitbucket), [`postgres_mcp`](https://github.com/JaviMaligno/postgres_mcp), [`langfuse-mcp-server`](https://github.com/JaviMaligno/langfuse-mcp-server) — ya viven en esta nueva forma. No son productos con UI. Son protocolos que cualquier agente puede recoger. La interfaz es la spec, no la pantalla.

El clasificador de compliance y el parser de documentos médicos dependen de algo que *no* se comprime en un fichero markdown: una taxonomía curada, edge cases extraídos de documentos reales, un suite de evaluación que demuestra que el modelo aguanta la cola larga. La orquestación a su alrededor cada vez se comprime más en instrucciones, pero el contexto de dominio no.

El valor del data-source automator está en una secuencia específica de human-in-the-loop que afinamos a base de iterar — dónde se para el agente, qué pregunta, qué loguea. Hace dos años eso vivía en código. Hoy vive más naturalmente como una skill más un set de evals.

Lo que sobrevive en el medio es lo que en realidad nunca fue código del todo: los datos, la taxonomía, el harness de evals, las *decisiones* de orquestación. Lo que era simplemente "código" — el envoltorio, el formulario, el boilerplate — se va a la capa de skills por un lado o al render generado por el otro.

## Los ingenieros ya no podemos escondernos en el nicho

Hay un corolario para los que escribimos el código que se está estrujando: la distancia entre idea y producto entregado se está acortando lo bastante como para que ya no podamos quedarnos metidos en un nicho de desarrollo y seguir aportando valor.

Cuando la capa intermedia era gruesa, podías ser "el del backend" o "el de LLM ops" y contribuir a través de tu trozo del stack. El product owner tenía la idea, los diseñadores se encargaban de la superficie, los ingenieros del plumbing, y los handoffs eran el trabajo. Cuando el medio es fino, esos handoffs cuestan más de lo que coordinan. El modelo renderiza buena parte de la superficie. El agente carga con buena parte del plumbing.

Lo que queda para los ingenieros se parece más al juicio de producto que a la implementación — qué problema resolver, qué significa "lo bastante bueno" en este dominio, dónde el modelo necesita ir sobre raíles y dónde no, qué pinta tiene un fallo y cómo cazarlo. Incluso cuando no construyes tu propio producto, no puedes esconderte en tu nicho. Tienes que tomar ownership del resultado para que se te confíe — porque la parte por la que solías cobrar, la implementación, es la que se está comprimiendo.

## Conclusiones prácticas

Tres cosas sobre las que estoy actuando:

1. **Lanza la skill, no el envoltorio.** Si construyes algo que vive detrás de un LLM, el código envoltorio es la parte con la vida media más corta. La skill — instrucciones, ejemplos, evals — es lo que realmente posees.
2. **Deja de pelearte con el medio.** Si pasas más tiempo restringiendo al modelo del que el modelo pasa produciendo output útil, estás resolviendo el problema equivocado. O aceptas lo que produce, o eliges otra herramienta.
3. **Invierte donde está el foso.** Lo defendible nuevo no es "lo construimos bien". Es "tenemos los datos, los evals y la orquestación que prueban que esto funciona en nuestro dominio". Ahí es donde estoy poniendo el tiempo en mis propios productos.

El software no está desapareciendo. Se está redistribuyendo por el stack — y el medio, la parte que llamábamos "la aplicación", se está volviendo mucho más fino de lo que esperaba hace seis meses.

---

*Repositorios referenciados: [google/agents-cli](https://github.com/google/agents-cli) · [OthmanAdi/planning-with-files](https://github.com/othmanadi/planning-with-files) · [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills). Demos: [Flipbook](https://flipbook.page/) · [Project Genie](https://blog.google/innovation-and-ai/models-and-research/google-deepmind/project-genie/).*
