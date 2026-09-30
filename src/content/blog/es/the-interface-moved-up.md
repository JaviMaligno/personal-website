---
title: "La interfaz subió de nivel"
description: "Los agentes de programación pasaron del editor a la terminal, y de ahí a la nube y a las apps nativas. Cada salto subió lo que mira el humano: del código al diff y del diff al resultado. El siguiente saca al humano incluso del arranque."
pubDate: 2026-10-27
tags: ["Agentes de IA", "Herramientas de desarrollo", "Claude Code", "Futuro del trabajo"]
lang: es
translationKey: the-interface-moved-up
heroImage: "/blog/the-interface-moved-up.png"
---

Empecé a trabajar con IA dentro del editor, como casi todo el mundo. Después me pasé a la terminal, con un editor ligero abierto al lado. Hoy, en mi propia máquina, sigo pasando la mayor parte del tiempo en la terminal: por costumbre, porque pesa menos y porque estoy pegado a la shell. Pero cada mes uso más la app de escritorio, sobre todo cuando no estoy en la mesa. Gestiona mejor varios proyectos y conversaciones, y me deja mezclar en la misma barra lateral un chat normal, una sesión de código que corre en la nube y otra que corre en mi portátil.

Esa deriva no es solo mía. Cursor, OpenAI, Anthropic y GitHub se han pasado 2026 sacando el mismo tipo de producto: una ventana para gestionar agentes, no para editar ficheros. Puestos uno al lado del otro, los movimientos tienen un patrón. **Cada salto subió lo que mira el humano.** Primero el código, después el diff, después el resultado. El siguiente salto ya se ve, y en él el humano ni siquiera arranca el trabajo.

## Cinco años en una imagen

<style>
.imu-fig{background:#1a1a24;border:1px solid rgba(255,255,255,.1);border-radius:1rem;padding:1rem;margin:2rem 0}
.imu-fig svg{display:block;width:100%;height:auto;font-family:Inter,-apple-system,system-ui,sans-serif}
.imu-fig figcaption{color:#94a3b8;font-size:.85rem;line-height:1.55;margin:1rem .25rem .25rem;text-align:center}
</style>

<figure class="imu-fig">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 770" role="img" aria-label="Cronología de 2021 a septiembre de 2026 con cinco carriles: editor, terminal, nube, app y agentes disparados por eventos. El editor recorre todo el periodo. Los agentes en terminal aparecen en 2023 y se vuelven la vía principal en 2025. Los agentes en la nube llegan en mayo de 2025, las apps nativas desde noviembre de 2025 y los agentes que arrancan tickets y calendarios desde mayo de 2025. Ningún carril se cierra: las superficies se acumulan.">
  <g font-size="13" font-weight="600" text-anchor="start">
    <text x="60" y="36" fill="#cbd5e1">Editor</text>
    <text x="169" y="36" fill="#5eead4">Terminal</text>
    <text x="278" y="36" fill="#7dd3fc">Nube</text>
    <text x="387" y="36" fill="#fbbf24">App</text>
    <text x="496" y="36" fill="#f8fafc">Por eventos</text>
  </g>
  <path d="M56 50H600" stroke="rgba(255,255,255,.1)"/>
  <g font-size="12" fill="#94a3b8">
    <text x="4" y="116">2022</text>
    <text x="4" y="164">2023</text>
    <text x="4" y="212">2024</text>
    <text x="4" y="284">2025</text>
    <text x="4" y="548">2026</text>
    <text x="4" y="745">sep. '26</text>
  </g>
  <g stroke="rgba(255,255,255,.06)">
    <path d="M40 112H600"/><path d="M40 160H600"/><path d="M40 208H600"/><path d="M40 280H600"/><path d="M40 544H600"/>
  </g>
  <path d="M40 262H600M40 268H600" stroke="#475569" stroke-dasharray="6 4"/>
  <path d="M58 741H600" stroke="#64748b" stroke-dasharray="4 4"/>
  <path d="M64 84V741" stroke="#94a3b8" stroke-width="3"/>
  <path d="M173 182V319" stroke="#2dd4bf" stroke-width="2" stroke-dasharray="3 5"/>
  <path d="M173 319V741" stroke="#2dd4bf" stroke-width="3"/>
  <path d="M282 218V380" stroke="#38bdf8" stroke-width="2" stroke-dasharray="3 5"/>
  <path d="M282 380V741" stroke="#38bdf8" stroke-width="3"/>
  <path d="M391 517V741" stroke="#f59e0b" stroke-width="3"/>
  <path d="M500 380V741" stroke="#f8fafc" stroke-width="3"/>
  <g fill="#1a1a24" stroke-width="2">
    <circle cx="64" cy="84" r="4.5" stroke="#94a3b8"/><circle cx="64" cy="131" r="4.5" stroke="#94a3b8"/><circle cx="64" cy="167" r="4.5" stroke="#94a3b8"/><circle cx="64" cy="204" r="4.5" stroke="#94a3b8"/><circle cx="64" cy="251" r="4.5" stroke="#94a3b8"/><circle cx="64" cy="498" r="4.5" stroke="#94a3b8"/>
    <circle cx="173" cy="182" r="4.5" stroke="#2dd4bf"/><circle cx="173" cy="319" r="4.5" stroke="#2dd4bf"/><circle cx="173" cy="357" r="4.5" stroke="#2dd4bf"/><circle cx="173" cy="584" r="4.5" stroke="#2dd4bf"/>
    <circle cx="282" cy="218" r="4.5" stroke="#38bdf8"/><circle cx="282" cy="380" r="4.5" stroke="#38bdf8"/><circle cx="282" cy="492" r="4.5" stroke="#38bdf8"/>
    <circle cx="391" cy="517" r="4.5" stroke="#f59e0b"/><circle cx="391" cy="567" r="4.5" stroke="#f59e0b"/><circle cx="391" cy="614" r="4.5" stroke="#f59e0b"/><circle cx="391" cy="666" r="4.5" stroke="#f59e0b"/>
    <circle cx="500" cy="380" r="4.5" stroke="#f8fafc"/><circle cx="500" cy="449" r="4.5" stroke="#f8fafc"/><circle cx="500" cy="591" r="4.5" stroke="#f8fafc"/><circle cx="500" cy="620" r="4.5" stroke="#f8fafc"/><circle cx="500" cy="645" r="4.5" stroke="#f8fafc"/><circle cx="500" cy="666" r="4.5" stroke="#f8fafc"/>
  </g>
  <g font-size="11" fill="#e2e8f0">
    <text x="73" y="88">Copilot preview</text>
    <text x="73" y="135">Copilot GA</text>
    <text x="73" y="171">Copilot X: chat</text>
    <text x="73" y="208">Copilot Chat GA</text>
    <text x="73" y="255">Agente Cursor</text>
    <text x="73" y="502">Cursor 2.0:</text>
    <text x="73" y="515">8 en paralelo</text>
    <text x="182" y="186">Aider,</text>
    <text x="182" y="199">gpt-engineer</text>
    <text x="182" y="323">Claude Code</text>
    <text x="182" y="361">Codex CLI</text>
    <text x="182" y="588">Copilot CLI GA</text>
    <text x="291" y="222">Anuncio de Devin</text>
    <text x="291" y="384">Cursor, Codex,</text>
    <text x="291" y="397">Copilot en nube</text>
    <text x="291" y="496">Claude Code</text>
    <text x="291" y="509">en la web</text>
    <text x="400" y="521">Claude Code en</text>
    <text x="400" y="534">escritorio</text>
    <text x="400" y="571">App de Codex</text>
    <text x="400" y="618">Cursor 3,</text>
    <text x="400" y="631">rediseño Claude</text>
    <text x="400" y="670">App Copilot GA</text>
    <text x="509" y="384">Linear for</text>
    <text x="509" y="397">Agents</text>
    <text x="509" y="453">Triage Linear</text>
    <text x="509" y="466">→ Cursor</text>
    <text x="509" y="595">Copilot en Jira</text>
    <text x="509" y="624">Claude Routines</text>
    <text x="509" y="649">Cursor en Jira</text>
    <text x="509" y="670">App Copilot:</text>
    <text x="509" y="683">automatización</text>
  </g>
</svg>
<figcaption>Fechas de lanzamiento de las superficies en las que han vivido los agentes, de junio de 2021 a septiembre de 2026. Desde 2025 (bajo la línea doble) cada mes ocupa cinco veces más altura; si no, los últimos veinte meses no cabrían. Tramos discontinuos: la superficie existía pero era marginal. Ningún carril se cierra.</figcaption>
</figure>

Saltan a la vista dos cosas. La primera es que **ninguna superficie ha desaparecido**. El editor sigue ahí, la terminal sigue ahí, y las nuevas se han sumado encima. Lo que cambia es dónde pasas la mayor parte del día. La segunda es la densidad: casi todo lo que importa ha pasado en los últimos veinte meses.

## El editor: el humano escribe, el modelo sugiere

GitHub Copilot abrió su [technical preview en junio de 2021](https://github.blog/news-insights/product-news/introducing-github-copilot-ai-pair-programmer/) y llegó a [disponibilidad general un año después](https://github.blog/news-insights/product-news/github-copilot-is-generally-available-to-all-developers/). La unidad de trabajo era una línea o una función: tú escribías y el modelo completaba. En 2023 llegó el chat dentro del editor ([Copilot X en marzo](https://github.blog/news-insights/product-news/github-copilot-x-the-ai-powered-developer-experience/), [Copilot Chat en GA en diciembre](https://github.blog/news-insights/product-news/github-copilot-chat-now-generally-available-for-organizations-and-individuals/)), y a finales de 2024 Cursor añadió [un agente a su Composer](https://cursor.com/changelog/0-43-x) que elegía su propio contexto y usaba la terminal.

El agente ya hacía trabajo de varios pasos, pero el marco seguía siendo el fichero. El humano miraba código, porque el trabajo pasaba en el código.

## La terminal: el agente necesita la máquina entera

Los agentes en terminal no nacieron en 2025. [Aider](https://github.com/Aider-AI/aider/releases) y gpt-engineer ya estaban ahí a mediados de 2023. Lo que cambió en 2025 es que la terminal se convirtió en la vía principal: [Claude Code salió en febrero](https://www.anthropic.com/news/claude-3-7-sonnet) como research preview, [Codex CLI en abril](https://community.openai.com/t/this-weeks-launches-o3-o4-mini-gpt-4-1-and-codex-cli/1230312), y Claude Code llegó a [disponibilidad general en mayo](https://www.anthropic.com/news/claude-4).

La terminal ganó por lo que le da al agente, no por lo que le da a la persona. La shell es una interfaz universal a herramientas: tests, git, gestores de paquetes, cualquier CLI que tengas y cualquier script. Darle una terminal al agente es la forma más barata de darle todo. Y eso va de la mano de la autonomía creciente de los modelos: un agente capaz de lanzar cincuenta comandos por su cuenta necesita la máquina entera, no una caja de autocompletado.

Conviene separar la etapa de la terminal en dos formas de trabajar:

- **Terminal más editor.** La terminal da las órdenes y el editor queda abierto para leer el diff y llevar git. Sigues mirando código, pero como revisor, no como autor.
- **Solo terminal.** Gana peso la gestión de agentes, y los comandos de terminal pasan a ser el único punto manual del desarrollo. Puedes seguir abriendo un artefacto, un navegador para ver el resultado final o una extensión, pero el desarrollo en sí ocurre en la conversación. Es menos transparente: ves lo que el agente te cuenta, salvo que le pidas más.

En las dos, el humano mira el **diff**, y la unidad de trabajo es una tarea.

## La nube: el portátil tiene techo

El siguiente paso parece que debería haber sido la app, pero las fechas dicen otra cosa. Primero llegaron los agentes en la nube, tres de ellos en cinco días de mayo de 2025: los [Background Agents de Cursor](https://cursor.com/changelog/0-50), [Codex dentro de ChatGPT](https://openai.com/index/introducing-codex/) y el [coding agent de Copilot](https://github.blog/changelog/2025-05-19-github-copilot-coding-agent-in-public-preview/), que toma una issue de GitHub y abre una pull request. [Claude Code en la web](https://www.anthropic.com/news/claude-code-on-the-web) llegó en octubre.

La comodidad es solo parte de la razón. La otra es la capacidad. Lanzar varios agentes a la vez, cada uno con su rama y su suite de tests, satura un portátil normal mucho antes de saturar tu atención. Los [agentes en paralelo con worktrees](/es/blog/parallel-ai-agent-development) funcionan, hasta que el cuello de botella pasa a ser la máquina.

La nube tiene su propio precio: el entorno tiene que ser reproducible. Si quieres que el agente remoto ejecute exactamente lo que se ejecuta en local, el repositorio tiene que [ser dueño de su bootstrap](/es/blog/bootstrap-the-environment-not-the-agent): paquetes del sistema, bases de datos de test, secretos. No siempre compensa. A veces la tarea no necesita el entorno completo, y a veces es deseable dejar una fase en local, como la que toca datos que prefieres no mover o la comprobación final en tu propia máquina. [Remote Control](https://code.claude.com/docs/en/remote-control), de Anthropic, toma esa posición de forma explícita: la sesión sigue corriendo en tu ordenador y la manejas desde el móvil.

## La app: el mismo trabajo, pero se ve

Aquí es donde pasó 2026. Claude Code llegó a la app de escritorio de Claude [con Opus 4.5 en noviembre de 2025](https://www.anthropic.com/news/claude-opus-4-5), ya con sesiones locales y remotas en paralelo. Luego, seguidos: la [app de Codex en febrero](https://techcrunch.com/2026/02/02/openai-launches-new-macos-app-for-agentic-coding/), [Cursor 3 en abril](https://cursor.com/blog/cursor-3) con una ventana para gestionar agentes en local, worktrees, nube y SSH, el [rediseño del escritorio de Claude Code](https://claude.com/blog/claude-code-desktop-redesign) ese mismo mes, y la [app de Copilot en junio](https://github.blog/changelog/2026-06-17-github-copilot-app-generally-available/).

La última es la que más dice. La empresa que inventó el asistente dentro del editor saca ahora una app independiente para lanzar agentes. Y Cursor 3 no eliminó el IDE: la ventana de agentes vive a su lado y puedes cambiar de una a otro. El editor no fue sustituido, dejó de ser el centro.

Visto desde dentro, lo que ofrece la app es menos espectacular de lo que suena, y ahí está justamente su valor:

- **Un chat normal, pero para código.** La conversación se parece a ChatGPT o a Claude, la interfaz que todo el mundo ya conoce, y debajo corre un agente con acceso a tu repositorio.
- **Todo lo que rodea a la conversación, a mano.** Diff, git, pull requests, artefactos, un panel de vista previa y un [navegador embebido](https://code.claude.com/docs/en/whats-new/2026-w28) para ver el resultado. Sin cambiar de ventana.
- **Lo mismo que haces en la terminal, pero más claro.** Buena parte de la mejora es simplemente que se lee mejor: sesiones en una barra lateral, diffs con un visor de verdad, paneles que colocas a tu gusto.
- **Varios dispositivos.** Empiezas algo en la mesa y lo sigues desde el móvil. Con sesiones en la nube no es un truco: el trabajo nunca estuvo en tu portátil.

Y un cambio fácil de pasar por alto: en la misma barra lateral conviven conversaciones normales, sesiones de código remotas y sesiones locales. **La app deja de ser un sitio para programar y pasa a ser el sitio donde trabajas.**

El coste es el peso. Consume más recursos que una terminal, y es parte de por qué la terminal sigue siendo mi opción por defecto en mi propia máquina.

## Lo que subió

Junta las etapas y aparece la tesis. No es que las interfaces se hayan vuelto más bonitas. Es que lo que el humano necesita ver ha subido un nivel cada vez.

<figure class="imu-fig">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 330" role="img" aria-label="Cuatro escalones ascendentes. En el editor, el humano mira el código y la unidad es una línea o un fichero. En la terminal, el diff, y la unidad es una tarea. En la app con la nube, el resultado, y la unidad es una sesión. Con agentes por detrás, las métricas, y la unidad es un flujo de tickets.">
  <text x="20" y="30" fill="#94a3b8" font-size="15">QUÉ MIRA EL HUMANO</text>
  <rect x="20" y="220" width="135" height="90" rx="8" fill="#283240" stroke="#94a3b8"/>
  <text x="32" y="244" fill="#cbd5e1" font-size="15" font-weight="600">Editor</text>
  <text x="32" y="266" fill="#f8fafc" font-size="13">el código</text>
  <text x="32" y="286" fill="#94a3b8" font-size="12">línea o fichero</text>
  <rect x="165" y="165" width="135" height="145" rx="8" fill="#203237" stroke="#2dd4bf"/>
  <text x="177" y="189" fill="#5eead4" font-size="15" font-weight="600">Terminal</text>
  <text x="177" y="211" fill="#f8fafc" font-size="13">el diff</text>
  <text x="177" y="231" fill="#94a3b8" font-size="12">una tarea</text>
  <rect x="310" y="110" width="135" height="200" rx="8" fill="#362e23" stroke="#f59e0b"/>
  <text x="322" y="134" fill="#fbbf24" font-size="15" font-weight="600">App + nube</text>
  <text x="322" y="156" fill="#f8fafc" font-size="13">el resultado</text>
  <text x="322" y="176" fill="#94a3b8" font-size="12">una sesión</text>
  <text x="322" y="194" fill="#94a3b8" font-size="12">PR · preview</text>
  <text x="322" y="212" fill="#94a3b8" font-size="12">artefacto</text>
  <rect x="455" y="55" width="135" height="255" rx="8" fill="#2a2a33" stroke="#f8fafc"/>
  <text x="467" y="79" fill="#f8fafc" font-size="15" font-weight="600">Por detrás</text>
  <text x="467" y="101" fill="#f8fafc" font-size="13">las métricas</text>
  <text x="467" y="121" fill="#94a3b8" font-size="12">flujo de tickets</text>
  <text x="467" y="139" fill="#94a3b8" font-size="12">evals · feedback</text>
  <text x="467" y="157" fill="#94a3b8" font-size="12">testing</text>
</svg>
<figcaption>Cada escalón sube el nivel al que interviene el humano. Los anteriores no desaparecen: pasan a ser algo que abres cuando hace falta.</figcaption>
</figure>

## La superficie se separa del harness

La consecuencia más importante no está en pantalla. El mismo agente corre ahora en la terminal, en el IDE, en la app de escritorio, en el navegador, desde el móvil, desde un ticket de Linear o Jira, o con un calendario. Lo que lo hace *ese* agente vive por debajo y lo comparten todas esas superficies: el **harness**.

<figure class="imu-fig">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 410" role="img" aria-label="Seis superficies (terminal, IDE, app de escritorio, web y móvil, tickets, calendarios y eventos) se apoyan en un mismo harness compartido: permisos, herramientas, entradas y salidas, contexto y memoria, hooks y skills, sandbox, worktrees y escalado, que corre en local, en la nube o por SSH. Debajo hay un modelo cada vez más intercambiable.">
  <defs><marker id="imu-arrow-es" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10Z" fill="#94a3b8"/></marker></defs>
  <text x="20" y="26" fill="#94a3b8" font-size="14">SUPERFICIES · una elección de vista</text>
  <rect x="20" y="40" width="180" height="40" rx="8" fill="#203237" stroke="#2dd4bf"/><text x="110" y="65" text-anchor="middle" fill="#e2e8f0" font-size="14">Terminal</text>
  <rect x="210" y="40" width="180" height="40" rx="8" fill="#203237" stroke="#2dd4bf"/><text x="300" y="65" text-anchor="middle" fill="#e2e8f0" font-size="14">IDE</text>
  <rect x="400" y="40" width="180" height="40" rx="8" fill="#203237" stroke="#2dd4bf"/><text x="490" y="65" text-anchor="middle" fill="#e2e8f0" font-size="14">App de escritorio</text>
  <rect x="20" y="90" width="180" height="40" rx="8" fill="#203237" stroke="#2dd4bf"/><text x="110" y="115" text-anchor="middle" fill="#e2e8f0" font-size="14">Web · móvil</text>
  <rect x="210" y="90" width="180" height="40" rx="8" fill="#203237" stroke="#2dd4bf"/><text x="300" y="115" text-anchor="middle" fill="#e2e8f0" font-size="14">Tickets (Linear, Jira)</text>
  <rect x="400" y="90" width="180" height="40" rx="8" fill="#203237" stroke="#2dd4bf"/><text x="490" y="115" text-anchor="middle" fill="#e2e8f0" font-size="14">Calendarios · eventos</text>
  <path d="M110 138V172" stroke="#94a3b8" stroke-width="2" marker-end="url(#imu-arrow-es)"/>
  <path d="M300 138V172" stroke="#94a3b8" stroke-width="2" marker-end="url(#imu-arrow-es)"/>
  <path d="M490 138V172" stroke="#94a3b8" stroke-width="2" marker-end="url(#imu-arrow-es)"/>
  <rect x="20" y="180" width="560" height="150" rx="10" fill="#362e23" stroke="#f59e0b"/>
  <text x="300" y="212" text-anchor="middle" fill="#fbbf24" font-size="22" font-weight="600">Harness</text>
  <text x="300" y="242" text-anchor="middle" fill="#e2e8f0" font-size="15">permisos · herramientas · entradas y salidas</text>
  <text x="300" y="266" text-anchor="middle" fill="#e2e8f0" font-size="15">contexto y memoria · hooks y skills</text>
  <text x="300" y="290" text-anchor="middle" fill="#e2e8f0" font-size="15">sandbox · worktrees · escalado a un humano</text>
  <text x="300" y="316" text-anchor="middle" fill="#94a3b8" font-size="13">corre en local, en la nube o por SSH</text>
  <path d="M300 332V346" stroke="#94a3b8" stroke-width="2" marker-end="url(#imu-arrow-es)"/>
  <rect x="20" y="352" width="560" height="46" rx="10" fill="#283240" stroke="#94a3b8"/>
  <text x="300" y="381" text-anchor="middle" fill="#f8fafc" font-size="15">Modelo: frontier u open source, cada vez más intercambiable</text>
</svg>
<figcaption>La superficie es una elección de vista sobre el mismo agente. Qué puede hacer, qué recuerda y cuándo pide ayuda se decide una capa más abajo.</figcaption>
</figure>

Dos tendencias empujan en la misma dirección. Los modelos open source son cada vez más competentes y los frontier cada vez más baratos, así que [elegir modelo](/es/blog/routing-engineering) se está convirtiendo en una decisión de enrutado más que de plataforma. Y el trabajo empieza a hacerse a escala: muchas sesiones, muchos repositorios, tareas largas. Llegados ahí, lo que distingue a los agentes de un equipo de los de otro no es el modelo ni la ventana, sino el harness.

## Gestionar, no teclear

Cuando el humano deja de mirar cada paso, las preguntas cambian. Ya no son «cómo escribo esto», sino «qué puede hacer este agente, qué recibe, qué devuelve y cuándo para a preguntarme». Pesan más en el trabajo de horizonte largo, donde un agente corre durante horas y una mala decisión al principio se multiplica:

- **Permisos.** Qué puede tocar sin preguntar, qué no puede tocar nunca y en qué entorno. Desplegar, escribir en una base de datos compartida o enviar algo hacia fuera es otra categoría que editar un fichero.
- **Entradas.** Con qué contexto arranca: el ticket, la especificación, las instrucciones del repositorio, la memoria de sesiones anteriores. Un agente que arranca sin los hechos que cambian su juicio toma decisiones que no tomaría quien los conoce.
- **Salidas.** Qué cuenta como hecho y en qué forma vuelve: una pull request con evidencias, un informe con fuentes, tests que fallan antes y pasan después. El formato de la salida es lo que permite comprobar sin reabrirlo todo.
- **Escalado.** Cuándo para y pregunta, y a quién. Un agente que nunca escala toma decisiones que no le tocan; uno que escala siempre te devuelve el trabajo.

Para la superficie, eso se traduce en una lista corta. La pantalla para gestionar agentes tiene que enseñar el estado de cada uno, qué espera de ti, qué está bloqueado y por qué, y la evidencia de cada resultado a un clic. Todo lo demás es decoración. Es también la lista que fija cuántos agentes puede supervisar de verdad una persona, que es [un límite humano, no técnico](/es/blog/human-limits-managing-ai-agents).

## Agentes que van por detrás

El último paso es el que el humano no arranca. La cadena es esta: un cliente deja feedback, se crea un ticket, un agente lo desarrolla, y el humano supervisa el *rendimiento* de ese proceso a través de evals (también automatizadas), del feedback externo y del testing final. Nadie abre una sesión.

Suena a especulación, pero las piezas ya existen. [Linear convirtió a los agentes en miembros del workspace](https://linear.app/changelog/2025-05-20-linear-for-agents) en mayo de 2025, y tres meses después su [integración con Cursor](https://linear.app/changelog/2025-08-21-cursor-agent) permitía reglas de triage que asignan issues al agente automáticamente. Copilot [toma issues de Jira](https://github.blog/changelog/2026-03-05-github-copilot-coding-agent-for-jira-is-now-in-public-preview/) y Cursor [también](https://cursor.com/changelog/page/6). Las [Routines](https://claude.com/blog/introducing-routines-in-claude-code) de Anthropic ejecutan un agente guardado en la nube con un calendario, al llamarlo por API o ante un evento de GitHub, sin ningún portátil encendido. La app de Copilot trae sus propias [automatizaciones programadas](https://github.blog/changelog/2026-06-17-github-copilot-app-generally-available/). Casi todo sigue en preview, pero ya está lanzado.

En ese mundo, la interfaz para este tipo de trabajo deja de ser una ventana donde tecleas. Es un panel de métricas y una cola de lo que necesita tu criterio. El resultado llega a donde ya estás, que es el mismo movimiento que conté en [Lleva tu aplicación al agente](/es/blog/bring-your-app-to-the-agent), visto desde el lado del desarrollador.

## ¿Y leer el código?

Hay casos en los que quieres estar cerca del código: un cambio delicado, una pieza de la que no te fías, una exploración en la que aún no sabes qué buscas. Eso no desaparece, pero se está convirtiendo en el caso límite, siempre que la evidencia se pueda extraer. Puedes pedirle al agente el fragmento exacto que cambió, abrirlo en el repositorio, pedir el test que lo demuestra. Lo que cuenta es [verificar el resultado, no releer el camino](/es/blog/results-oriented-programming), y una buena superficie pone esa evidencia a un clic.

## Lo que viene

La terminal no se muere. Se convierte en sustrato: el sitio donde el agente ejecuta, y una superficie más para quien la prefiera. El editor tampoco se muere; es lo que abres cuando necesitas mirar de cerca. Lo que está pasando es que la interfaz se desacopla del agente. Elegirás la superficie según el momento y el dispositivo, mientras el harness de debajo sigue siendo el mismo.

Lo que distinguirá a un equipo, entonces, no es qué ventana usa. Es lo bien que ha definido qué pueden hacer sus agentes, qué reciben, qué devuelven y cuándo llaman a un humano. Eso es un problema de gestión, y es hacia donde va la interfaz: menos teclados y más paneles.

---

*Fuentes de las fechas de la cronología: [Copilot preview](https://github.blog/news-insights/product-news/introducing-github-copilot-ai-pair-programmer/) · [Copilot GA](https://github.blog/news-insights/product-news/github-copilot-is-generally-available-to-all-developers/) · [Copilot X](https://github.blog/news-insights/product-news/github-copilot-x-the-ai-powered-developer-experience/) · [Copilot Chat GA](https://github.blog/news-insights/product-news/github-copilot-chat-now-generally-available-for-organizations-and-individuals/) · [Cursor 0.43](https://cursor.com/changelog/0-43-x) · [Cursor 2.0](https://cursor.com/changelog/2-0) · [Aider releases](https://github.com/Aider-AI/aider/releases) · [Claude Code preview](https://www.anthropic.com/news/claude-3-7-sonnet) · [Codex CLI](https://community.openai.com/t/this-weeks-launches-o3-o4-mini-gpt-4-1-and-codex-cli/1230312) · [Copilot CLI GA](https://github.blog/changelog/2026-02-25-github-copilot-cli-is-now-generally-available/) · [Devin](https://x.com/cognition/status/1767548763134964000) · [Cursor Background Agents](https://cursor.com/changelog/0-50) · [Codex cloud](https://openai.com/index/introducing-codex/) · [Copilot coding agent](https://github.blog/changelog/2025-05-19-github-copilot-coding-agent-in-public-preview/) · [Claude Code en la web](https://www.anthropic.com/news/claude-code-on-the-web) · [Claude Code en la app de escritorio](https://www.anthropic.com/news/claude-opus-4-5) · [App de Codex](https://techcrunch.com/2026/02/02/openai-launches-new-macos-app-for-agentic-coding/) · [Cursor 3](https://cursor.com/blog/cursor-3) · [Rediseño del escritorio de Claude Code](https://claude.com/blog/claude-code-desktop-redesign) · [App de Copilot GA](https://github.blog/changelog/2026-06-17-github-copilot-app-generally-available/) · [Linear for Agents](https://linear.app/changelog/2025-05-20-linear-for-agents) · [Cursor en Linear](https://linear.app/changelog/2025-08-21-cursor-agent) · [Copilot para Jira](https://github.blog/changelog/2026-03-05-github-copilot-coding-agent-for-jira-is-now-in-public-preview/) · [Routines](https://claude.com/blog/introducing-routines-in-claude-code) · [Cursor en Jira](https://cursor.com/changelog/page/6).*
