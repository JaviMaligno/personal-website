---
title: "Cuando el chat construye su propia interfaz"
description: "La UI generativa permite que un agente renderice widgets interactivos — formularios, gráficos, firmas — dentro del chat en vez de texto plano. AG-UI es el protocolo que lo estandariza, y yo ya llevo meses construyéndolo a mano."
pubDate: 2026-06-15
tags: ["Agentes IA", "UI Generativa", "AG-UI", "IA Conversacional"]
lang: es
translationKey: ag-ui-third-protocol
heroImage: "/blog/ag-ui-third-protocol.png"
---

En el [AI Signals x LangChain Community London #32](https://lu.ma/hn9dhq7e), [Sofía Sánchez-Zárate](https://www.linkedin.com/in/sof%C3%ADa-s%C3%A1nchez-z%C3%A1rate-91493381/), de CopilotKit, dio una charla titulada *"AG-UI & The Generative UI Spectrum"*. La demo que se me quedó grabada: le pides ayuda para calcular la cuota de un préstamo y, en vez de responderte con un único número —uno que tendrías que pedirle recalcular cada vez que cambias el tipo o el plazo—, renderiza una calculadora funcional de verdad *dentro del propio chat*. Campos que editas, un total que se actualiza en vivo. No un pantallazo de una; un widget real que el agente montó para esa pregunta, sobre la marcha.

Eso es la UI generativa: el chat deja de ser una caja de texto y se convierte en una superficie que el agente puede componer.

## Yo ya llevo construyendo esto — a mano

La razón por la que la charla me caló es que llevo colaborando en un proyecto de KYC conversacional que hace exactamente esto. El agente no responde a las preguntas de onboarding con párrafos. Cuando necesita una estructura de titularidad real, renderiza un formulario para añadir personas y su relación con la empresa. Cuando ha extraído datos de un documento subido, muestra un panel de confirmación editable, no un muro de texto. Renderiza cargas de archivos, un pad de firma, un gráfico de accionariado — todo *dentro de la conversación*.

Por debajo, el patrón es sencillo. El agente (sobre LangGraph) se pausa con un `interrupt` tipado — un payload cuyo `type` es `person_form`, `confirm_summary`, `signature_pad`, `shareholder_chart`, etc. El front end de React mantiene un registro que mapea cada `type` a un componente, lo renderiza, deja que el usuario interactúe, y devuelve el resultado para que el grafo se reanude exactamente donde se pausó.

Funciona muy bien. También es completamente casero y está soldado a nuestro stack: nuestro formato de interrupt, nuestro registro de widgets, nuestro front end. Y por eso la charla de Sofía me dio en la diana: **lo que nosotros construimos en vertical a mano es justo lo que AG-UI estandariza.**

## Qué es AG-UI en realidad

AG-UI (Agent-User Interaction) es un protocolo ligero y basado en eventos para el canal entre un backend agéntico y el front end que mira un humano. En vez de devolver un único bloque final de texto, el agente emite un *stream de eventos tipados* que la UI renderiza según llegan:

- **Ciclo de vida** — `RunStarted`, `RunFinished`, `RunError`, con pares opcionales `StepStarted`/`StepFinished`.
- **Mensajes de texto** — en streaming token a token.
- **Llamadas a herramientas** — para que la UI pueda mostrar qué está haciendo el agente.
- **Estado** — snapshots más deltas para mantener sincronizados front end y agente.

Nuestro mecanismo de `interrupt` + registro es un dialecto privado de esto. AG-UI es el intento de convertirlo en un lenguaje compartido — para que un backend conversacional no quede casado para siempre con un único front end a medida, y para que el human-in-the-loop (pausar, dejar que el usuario confirme, edite o firme, reanudar) sea un primitivo nativo en lugar de algo que cableas tú.

## El espectro de la UI generativa

El encuadre que me pareció más útil fue el *espectro* — cuánto de la interfaz dicta el modelo, de menos a más:

- **Componentes tipados.** El agente elige de un catálogo fijo de componentes de front end y los rellena con datos. Es exactamente lo que son nuestros widgets de KYC: el modelo no inventa el formulario, elige `person_form` y lo rellena.
- **UI declarativa.** El agente emite una descripción de la interfaz y el cliente la renderiza. **A2UI** (la spec de Google) hace streaming de un árbol de UI como JSONL — un layout serializado de componentes y bindings que el cliente construye, en vez de un catálogo fijo que el cliente ya tiene. **Open-JSON-UI** (OpenAI) es la misma idea desde el otro bando; es el linaje detrás de **los gráficos interactivos que ChatGPT ha empezado a renderizar en el chat** — un protocolo equivalente, aunque no estrictamente el que propone CopilotKit. (Conviene deshacer una confusión común: A2UI *no* es AG-UI. A2UI es una representación de UI; AG-UI es el transporte que puede llevarla.)
- **Embebida en iframe.** **MCP-UI** envía UI autocontenida dentro de un frame aislado.
- **Píxeles generados.** En el extremo, el modelo renderiza la interfaz él mismo — el territorio que exploré en [Software Is Dissolving Into the Model](/es/blog/software-dissolving-into-the-model), donde Flipbook y Project Genie generan cada frame sin DOM alguno.

La apuesta de AG-UI es ser la tubería neutral que recorre todo ese rango: estandarizas el canal y dejas que la representación se deslice de tipado → declarativo → generado sin reescribir el backend cada vez. El extremo de los píxeles generados es hacia donde yo había argumentado que se dirige el software; la UI generativa es el punto medio pragmático de esa misma línea — lo bastante estructurada para ser fiable, lo bastante generada para ser flexible.

## Por qué los formularios son el caso matador

Sofía señaló que la IA conversacional sobre **formularios** es donde esto brilla — y que DocuSign, cuyo negocio entero son documentos, acuerdos y firmas, tiene un partnership con CopilotKit. Me encajó al instante, porque los formularios son justo donde el texto plano se rompe.

Una conversación es una forma estupenda de *recoger* información y una forma pésima de *estructurarla*. "Lista cada accionista con más del 25%, su nacionalidad y su relación con los administradores" es doloroso como un ida y vuelta de mensajes y trivial como una pequeña tabla renderizada que rellenas. Confirmar campos extraídos de un pasaporte, dibujar una firma, revisar un árbol de titularidad — nada de eso quiere párrafos; quiere widgets. Esa es toda la premisa del proyecto de KYC: sustituir el wizard rígido paso a paso por una conversación que aun así produce datos estructurados, validados y firmables. La UI generativa es lo que hace que la conversación y la estructura sean la misma superficie.

## Qué te daría estandarizar

Nuestro protocolo casero funciona, pero está acoplado. Un estándar como AG-UI permitiría que el mismo backend conversacional hablara con cualquier front end que lo entienda, mezclar specs de UI declarativa donde un catálogo fijo de widgets se queda corto, y obtener las pausas de human-in-the-loop como parte de primera clase del protocolo en lugar de una convención que mantenemos nosotros. El coste es el de siempre al adoptar un estándar joven: apostar por su modelo de eventos y su trayectoria.

Dado que LangGraph — sobre el que nuestro proyecto ya corre — está entre los frameworks con integración de AG-UI, el camino de migración de "nuestro dialecto" al "estándar" es inusualmente corto. Eso lo convierte en una opción real, no en una reescritura.

## Probándolo: del patrón hecho a mano al SDK

Para palpar la diferencia entre mi versión a medida y el estándar, monté una demo mínima con el SDK de AG-UI — un agente [Pydantic AI](https://ai.pydantic.dev/) sobre Azure OpenAI, un frontend de CopilotKit en React, y los dos widgets declarados como *frontend tools*. Le pides estimar la cuota de un préstamo y renderiza una calculadora interactiva en el chat; dices que quieres solicitarlo y renderiza un formulario. La parte de Python es esencialmente "conectar un modelo a AG-UI" — la UI generativa vive en el cliente, en unas cien líneas en total.

![La demo de AG-UI: el agente renderiza una calculadora de préstamo interactiva, y luego un formulario de solicitud, dentro del propio chat](/blog/ag-ui-generative-ui-demo.gif)

Ahí está la idea entera en una pantalla: el mismo bucle que el proyecto de KYC —el modelo elige un widget, el cliente lo renderiza, el usuario interactúa, el resultado vuelve— pero el cableado es un protocolo en vez de un registry que mantengo a mano. [Código en GitHub](https://github.com/JaviMaligno/agui-generative-ui-demo).

## El punto medio del espectro

La conclusión honesta es que la UI generativa responde a una pregunta que dejé abierta en *Software Is Dissolving Into the Model*: si la superficie renderizada se está desplazando de componentes codificados a mano hacia píxeles generados por el modelo, ¿dónde te plantas *hoy*, en un producto que tiene que funcionar de verdad? La respuesta es el punto medio del espectro — deja que el modelo elija y componga UI estructurada, mantén el render fiable — y un protocolo como AG-UI es lo que te permite escoger tu sitio en esa línea y moverte luego. Yo llevo meses ahí plantado a mano. Da gusto verlo recibir un nombre.

---

*Inspirado por la charla "AG-UI & The Generative UI Spectrum" de [Sofía Sánchez-Zárate](https://www.linkedin.com/in/sof%C3%ADa-s%C3%A1nchez-z%C3%A1rate-91493381/) en [AI Signals x LangChain Community London #32](https://lu.ma/hn9dhq7e). Detalles del protocolo: la [documentación de AG-UI](https://docs.ag-ui.com/introduction) y el [AG-UI Dojo](https://dojo.ag-ui.com/). Lectura relacionada: [Software Is Dissolving Into the Model](/es/blog/software-dissolving-into-the-model).*
