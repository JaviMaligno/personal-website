---
title: "Un agente ve lo que ve un lector de pantalla"
description: "Puse a un agente de IA a manejar Fotos, Vista Previa y Telegram en mi Mac sin ninguna API, solo con el árbol de accesibilidad. Después medí qué le enseñan 23 apps. Lo que no puede leer, y lo que puede leer pero no pulsar, es lo mismo con lo que choca un lector de pantalla."
pubDate: 2026-11-05
tags: ["IA", "Agentes", "Accesibilidad", "Automatización"]
lang: es
translationKey: an-agent-sees-what-a-screen-reader-sees
heroImage: "/blog/an-agent-sees-what-a-screen-reader-sees.png"
linkedinImage: "/blog/an-agent-sees-what-a-screen-reader-sees-thumb.png"
linkedinLinks:
  - label: "agent-desktop"
    url: "https://github.com/vercel-labs/agent-desktop"
---

<style>
.a11y-fig { margin: 2rem 0; }
.a11y-fig svg { width: 100%; height: auto; display: block; }
.a11y-fig figcaption { color: #94a3b8; font-size: 0.9rem; margin-top: 0.6rem; }
</style>

Le di a Claude Code una frase en una terminal: hazme un collage con las fotos de la playa y mándalo a mi canal de Telegram, que lo quiero en el móvil. Cuatro minutos después lo tenía en el móvil. Había abierto Fotos, seleccionado el álbum, exportado ocho fotos, montado el collage, comprobado el resultado en Vista Previa, pegado la imagen en Telegram, escrito el pie de foto y enviado.

Ninguna de esas apps tiene una API para eso. Fotos no la tiene, y yo no iba a montar un bot de Telegram para que publicase en mi nombre. El agente manejó las apps con [agent-desktop](https://github.com/vercel-labs/agent-desktop), una CLI de código abierto de Vercel Labs que hace una sola cosa: lee el **árbol de accesibilidad** de cada app y actúa sobre él.

Ese árbol es la misma estructura que macOS le entrega a VoiceOver. Así que la pregunta que me rondaba mientras veía la ejecución no era «¿puede un agente usar mi Mac?». Era: **¿cuánto de mi Mac puede ver de verdad?**

## Un árbol, dos lectores

Cada ventana nativa de macOS publica un árbol de elementos: un rol (`button`, `textfield`, `menuitem`), un nombre, a veces un valor, y las acciones que admite. Un lector de pantalla recorre ese árbol y lo lee en voz alta. agent-desktop recorre el mismo árbol y lo devuelve como JSON con una referencia por elemento, de modo que el agente puede decir «pulsa `@e12`» en lugar de adivinar coordenadas sobre una captura.

<figure class="a11y-fig">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 270" role="img" aria-label="Una ventana publica un único árbol de accesibilidad con roles, nombres, valores y acciones. Un lector de pantalla y el agente leen el mismo árbol; lo que falta en él falta para los dos.">
  <rect x="0" y="0" width="600" height="270" rx="12" fill="#1a1a24"/>
  <rect x="170" y="18" width="260" height="52" rx="10" fill="none" stroke="rgba(255,255,255,0.18)"/>
  <text x="300" y="42" text-anchor="middle" fill="#f8fafc" font-size="15" font-family="Inter,system-ui,sans-serif" font-weight="600">Ventana de la app</text>
  <text x="300" y="60" text-anchor="middle" fill="#94a3b8" font-size="12" font-family="Inter,system-ui,sans-serif">Telegram, Fotos, Vista Previa…</text>
  <path d="M300 70 L300 100" stroke="#64748b" stroke-width="2" marker-end="url(#a11y-arrow-es)"/>
  <rect x="120" y="104" width="360" height="64" rx="10" fill="rgba(45,212,191,0.08)" stroke="#2dd4bf"/>
  <text x="300" y="130" text-anchor="middle" fill="#5eead4" font-size="15" font-family="Inter,system-ui,sans-serif" font-weight="600">Árbol de accesibilidad</text>
  <text x="300" y="152" text-anchor="middle" fill="#e2e8f0" font-size="12.5" font-family="ui-monospace,'JetBrains Mono',monospace">rol · nombre · valor · acciones</text>
  <path d="M240 168 L150 206" stroke="#64748b" stroke-width="2" marker-end="url(#a11y-arrow-es)"/>
  <path d="M360 168 L450 206" stroke="#64748b" stroke-width="2" marker-end="url(#a11y-arrow-es)"/>
  <rect x="40" y="208" width="220" height="46" rx="10" fill="none" stroke="rgba(255,255,255,0.18)"/>
  <text x="150" y="230" text-anchor="middle" fill="#f8fafc" font-size="14" font-family="Inter,system-ui,sans-serif" font-weight="600">VoiceOver</text>
  <text x="150" y="246" text-anchor="middle" fill="#94a3b8" font-size="11.5" font-family="Inter,system-ui,sans-serif">se lo lee a una persona</text>
  <rect x="340" y="208" width="220" height="46" rx="10" fill="none" stroke="#f59e0b"/>
  <text x="450" y="230" text-anchor="middle" fill="#fbbf24" font-size="14" font-family="Inter,system-ui,sans-serif" font-weight="600">agent-desktop</text>
  <text x="450" y="246" text-anchor="middle" fill="#94a3b8" font-size="11.5" font-family="Inter,system-ui,sans-serif">se lo da en JSON a un agente</text>
  <defs><marker id="a11y-arrow-es" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#64748b"/></marker></defs>
</svg>
<figcaption>Una estructura, dos lectores. Lo que una app deja fuera de su árbol es invisible para los dos.</figcaption>
</figure>

Eso cambia lo que significa «computer use». No es visión. El agente no mira píxeles; lee lo que la app ha decidido describir de sí misma. Si la app se describe bien, el agente es rápido y preciso. Si no, no hay nada que leer.

## Qué enseñan 23 apps

Así que lo medí. Abrí las apps que tengo instaladas, una a una, y leí el árbol de la ventana principal con agent-desktop tres veces cada una: cuántos elementos expone, qué parte tiene nombre y cuántos admiten una acción. Solo recuentos, sin contenido.

<img src="https://www.javieraguilar.ai/blog/an-agent-sees-what-a-screen-reader-sees-census.png" alt="Gráfico de barras del tamaño del árbol de accesibilidad por app: Telegram 1.493 elementos con el 100 % con nombre, Spotify 1.221, Slack 616, ChatGPT 406, hasta TextEdit con 13, el emulador de Android con un único elemento y Docker Desktop sin responder en 45 segundos." />

Algunas cosas llaman la atención:

- **Telegram expone 1.493 elementos y todos tienen nombre.** Cada chat, cada mensaje, cada contador. Para un agente es la app más legible del ordenador.
- **Spotify expone casi los mismos, pero la mitad sin nombre.** Un botón sin nombre es un botón que el agente tiene que adivinar. Y quien usa un lector de pantalla, también.
- **El emulador de Android expone un elemento: la ventana.** Todo el teléfono que hay dentro es una imagen. El agente ve que existe una ventana llamada «Android Emulator» y nada más.
- **Docker Desktop no respondió.** Tres lecturas de 45 segundos, ningún árbol.
- **ChatGPT pasó de 12 elementos a 406** entre la primera lectura y la segunda. Recién abierta solo enseñaba el armazón; unos segundos después, toda la interfaz. Si la hubiera medido en frío la habría dado por opaca.
- **La Terminal expone 17 elementos**, porque toda la transcripción es un único campo de texto. El agente la puede leer, pero como un bloque de texto, no como estructura.

Dos matices. Son recuentos de un ordenador en un día, de la ventana con la que abrió cada app, y un árbol más grande no es por fuerza más usable: la proporción de elementos con nombre dice más que el tamaño. Pero los extremos no son sutiles: entre «un elemento» y «1.493 elementos con nombre» no hay error de medida que cambie la conclusión.

## Expuesto no es lo mismo que operable

La segunda mitad me la enseñó el propio collage, y es la parte que un censo no muestra. Telegram, la app más legible del gráfico, fue también donde el agente más sufrió.

Para mandar una imagen la pega en la caja de mensajes y Telegram abre un panel de envío con un campo de pie de foto y dos botones. Todo ese panel está en el árbol, con buenos nombres. Y aun así:

<figure class="a11y-fig">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 300" role="img" aria-label="El panel de envío de Telegram muestra un pie de foto que dice 'Done, 8 beach photos, one collage' y un botón Send. En el árbol de accesibilidad el valor del pie de foto está vacío y los botones Send y Cancel no exponen ninguna acción de pulsar.">
  <rect x="0" y="0" width="600" height="300" rx="12" fill="#1a1a24"/>
  <text x="155" y="30" text-anchor="middle" fill="#94a3b8" font-size="12.5" font-family="Inter,system-ui,sans-serif" letter-spacing="1.5">EN PANTALLA</text>
  <text x="445" y="30" text-anchor="middle" fill="#94a3b8" font-size="12.5" font-family="Inter,system-ui,sans-serif" letter-spacing="1.5">EN EL ÁRBOL</text>
  <rect x="20" y="44" width="270" height="236" rx="12" fill="#232331" stroke="rgba(255,255,255,0.1)"/>
  <text x="38" y="72" fill="#f8fafc" font-size="14" font-family="Inter,system-ui,sans-serif" font-weight="600">Send an image</text>
  <g fill="#2a3b4a"><rect x="38" y="84" width="56" height="34" rx="3"/><rect x="98" y="84" width="56" height="34" rx="3"/><rect x="158" y="84" width="56" height="34" rx="3"/><rect x="218" y="84" width="56" height="34" rx="3"/></g>
  <g fill="#4a3424"><rect x="38" y="122" width="56" height="34" rx="3"/><rect x="98" y="122" width="56" height="34" rx="3"/><rect x="158" y="122" width="56" height="34" rx="3"/><rect x="218" y="122" width="56" height="34" rx="3"/></g>
  <text x="38" y="186" fill="#5eead4" font-size="11.5" font-family="Inter,system-ui,sans-serif">Caption</text>
  <text x="38" y="206" fill="#f8fafc" font-size="13" font-family="Inter,system-ui,sans-serif">Done ✅ — 8 beach photos, one collage.</text>
  <line x1="38" y1="214" x2="272" y2="214" stroke="#2dd4bf" stroke-width="1.5"/>
  <text x="172" y="258" fill="#5eead4" font-size="13.5" font-family="Inter,system-ui,sans-serif">Cancel</text>
  <text x="236" y="258" fill="#5eead4" font-size="13.5" font-family="Inter,system-ui,sans-serif" font-weight="600">Send</text>
  <rect x="310" y="44" width="270" height="236" rx="12" fill="#14141c" stroke="rgba(255,255,255,0.1)"/>
  <g font-family="ui-monospace,'JetBrains Mono',monospace" font-size="13">
    <text x="328" y="82" fill="#5eead4">textfield<tspan fill="#e2e8f0"> "Caption"</tspan></text>
    <text x="344" y="106" fill="#94a3b8">valor: <tspan fill="#fbbf24">""</tspan></text>
    <text x="328" y="150" fill="#5eead4">button<tspan fill="#e2e8f0"> "Send"</tspan></text>
    <text x="344" y="174" fill="#94a3b8">pulsar: <tspan fill="#fbbf24">no disponible</tspan></text>
    <text x="328" y="218" fill="#5eead4">button<tspan fill="#e2e8f0"> "Cancel"</tspan></text>
    <text x="344" y="242" fill="#94a3b8">pulsar: <tspan fill="#fbbf24">no disponible</tspan></text>
  </g>
</svg>
<figcaption>Con nombre, pero no operable. El pie de foto se ve en pantalla y está vacío en el árbol; los botones aparecen y no se pueden pulsar.</figcaption>
</figure>

- **El campo del pie de foto informa de un valor vacío** mientras la pantalla enseña el texto. El agente no podía comprobar leyendo lo que había escrito; tuvo que hacer una captura de esa zona y mirarla.
- **Send y Cancel no admiten la acción de pulsar.** La herramienta se negó a hacer clic sobre ellos por la vía semántica, y un clic físico a través de ella también falló. Lo que funcionó fue el teclado: Enter envía, Escape cancela.
- **Ni siquiera escribir funcionaba ahí.** El campo nunca anunciaba que tenía el foco, así que la herramienta se negaba a teclear en él. El rodeo fue poner el texto en el portapapeles y pegarlo.

Telegram no es la excepción. Otras cosas con las que me encontré por el camino, y que el agente ahora sigue como reglas:

- **Los menús solo funcionan en la app que está delante.** Si le pides a Fotos Archivo › Exportar mientras está en segundo plano, la opción aparece *desactivada*. Traes la app al frente y se activa.
- **El diálogo de guardar es otro proceso.** El panel donde eliges carpeta no pertenece a Fotos, así que los atajos de teclado que le mandas a Fotos nunca le llegan. En uno de los ensayos, un clic semántico sobre una carpeta dentro del panel guardó la exportación directamente en esa carpeta.
- **Las acciones pueden llegar tarde.** Un pegado que parecía no haber funcionado apareció un momento después, y el panel acabó con dos copias de la imagen. Cada paso necesita mirar de nuevo antes del siguiente.
- **El agente solo ve el escritorio actual.** Cambias a otro escritorio de macOS y todas las ventanas de ahí desaparecen del árbol.
- **Hay árboles demasiado grandes para leerlos enteros.** Un chat largo de Telegram pasó del límite de 1 MB de la herramienta; el agente tuvo que leer la ventana por arriba y luego bajar solo a la lista de mensajes.

Nada de esto es exótico. Son las mismas costuras con las que choca quien usa teclado o lector de pantalla: un valor que la app no publica, un control sin acción, un diálogo que vive en otro proceso.

## Qué le llegaría a quien usa un lector de pantalla

No hice estas tareas con VoiceOver, así que aquí voy con cuidado. Pero VoiceOver le hace las mismas preguntas a la misma API. Un pie de foto que informa de un valor vacío es, para él, un campo vacío. Un botón sin acción de pulsar es un botón al que la propia orden de activar de VoiceOver no tiene nada que llamar; tendría que recurrir a simular un clic de ratón, como hizo el agente. Una ventana de emulador con un elemento es, para una persona ciega, una ventana sin etiqueta.

La diferencia es quién paga. Quien usa un lector de pantalla se encuentra estos huecos de uno en uno y los rodea con paciencia. Un agente también se los encuentra, pero luego se convierten en reglas: «pulsa Enter, el botón no admite clics», «pega, no escribas». Los rodeos que necesitó el agente son un mapa de dónde está rota la accesibilidad de una app.

Me recordó a lo que encontré [midiendo agentes sobre código degradado](/es/blog/practices-for-agents-substrate): en repositorios grandes, cómo está escrito el código reduce a la mitad lo que un agente resuelve. Aquí es la misma lección una capa más arriba. El agente es tan bueno como lo que puede leer, y lo que puede leer es lo que alguien se tomó la molestia de describir.

## Si haces apps, o agentes

**Si haces apps:** la accesibilidad iba de las personas que usan tecnologías de apoyo. Sigue yendo de eso, y eso solo ya es razón suficiente. Pero ese mismo árbol es ahora la interfaz de cualquier agente que maneje un ordenador como lo haría una persona. Pon nombre a tus controles, publica sus valores, dales a tus botones una acción de pulsar. Esa es toda la lista, y sirve a los dos lectores a la vez.

**Si haces agentes encima de esto:** trata cada app como si tuviera sus propias reglas y verifica después de cada acción, porque el árbol a veces te dirá que algo funcionó cuando no, o que falló cuando no había fallado. La ejecución que por fin salió limpia, en algo menos de cuatro minutos, no fue un modelo más listo. Fue una lista corta de lo que cada app deja hacer.

Si una app es accesible, es una herramienta. Si no lo es, para un agente casi no existe.

---

*Medido en macOS 15.7 con [agent-desktop](https://github.com/vercel-labs/agent-desktop) 1.0.2: ventana principal de cada app, tres lecturas, solo recuentos. Figma y Cursor no arrancaron desde la línea de comandos en este ordenador y no están en el gráfico.*
