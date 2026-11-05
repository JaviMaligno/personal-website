---
title: "Siete modelos con mi propio trabajo: importó más la tarea que el modelo"
description: "Di a siete modelos diecinueve tareas que yo había pedido de verdad y conté cuántas de mis propias correcciones seguiría necesitando cada uno. Con jueces de dos laboratorios, seis no se distinguen, DeepSeek necesita más, y qué tarea era importó mucho más que qué modelo la hizo."
pubDate: 2026-12-08
tags: ["IA", "Evaluación", "Benchmarks", "Agentes"]
lang: es
translationKey: the-task-not-the-model
heroImage: "/blog/the-task-not-the-model.png"
linkedinImage: /blog/the-task-not-the-model-fig-1.png
repoUrl: https://github.com/JaviMaligno/benchmaxing-probes
---

<style>
.ttm-fig{background:#1a1a24;border:1px solid rgba(255,255,255,.1);border-radius:1rem;padding:1.25rem;margin:2rem 0}
.ttm-fig svg{display:block;width:100%;height:auto;font-family:Inter,system-ui,sans-serif}
.ttm-fig figcaption{color:#94a3b8;font-size:.88rem;line-height:1.55;margin:.9rem 0 0;text-align:center}
</style>

[El artículo anterior](/es/blog/no-benchmaxing-found) terminaba con una admisión: mis propias pruebas también son benchmarks. Tienen una clave de respuestas, y el trabajo real no la tiene. Lo que noto cuando trabajo horas con un modelo es cuántas veces tengo que corregirlo, y ningún corrector automático había medido eso. Así que esta vez no escribí la clave. Volví a las sesiones de mi propio portátil, cogí diecinueve cosas que de verdad le había pedido a un agente y usé mis propias correcciones como medida.

**La respuesta corta: en mi trabajo, seis de los siete modelos necesitan más o menos la misma cantidad de guía.** DeepSeek necesita más. Y la distancia entre modelos es pequeña al lado de la distancia entre tareas: qué tarea era explica al menos diez veces más de la variación que qué modelo la hizo.

## De mis sesiones a tareas

**Cada tarea es una petición que escribí de verdad, y la clave son las correcciones que hice después.** Repasé el historial de Claude Code y de Codex de esta máquina y me quedé con diecinueve sesiones en las que había pedido algo concreto, había corregido al agente por el camino y había acabado aceptando un cambio. Diez son del trabajo: el [Industry Classifier](/es/projects/compliance-classifier), el [asistente de DevOps](/es/projects/devops-slack-bot), un flujo de chat guiado y un servicio de agentes de análisis. Nueve son personales: esta web, mi [servidor MCP de Bitbucket](/es/projects/mcp-bitbucket), una app de salud, un informe en PDF y un texto mío. Doce empezaron en Claude Code y siete en Codex.

De cada una guardé cuatro cosas: la petición tal cual, erratas incluidas («metele i18n a esto por un tubo en ingles y ruso»); el repositorio en el commit en el que lo pedí; el cambio que acabé aceptando; y la lista de todo lo que tuve que corregir o añadir antes de aceptarlo. Esa lista es la medida.

**El mismo entorno para los siete modelos, con un único empujón neutro.** Cada modelo recibió la petición en una copia limpia del repositorio, cortada en ese commit para que no se viera nada de la historia posterior, dentro de un contenedor con Claude Code, Bash y permisos abiertos. Opus 5 y Fable 5 corrieron con mi suscripción Max; Kimi K3.1 Pro, Gemini 4 Argon, DeepSeek V4 Pro, GLM 5.3 y Qwen3.8, por el endpoint compatible con Anthropic de OpenRouter. Si el primer turno no cambiaba nada, la sesión recibía un único «Adelante, hazlo.» y nada más. Después comparé lo que dejaba con lo que yo había aceptado.

**No todas las correcciones eran justas de contar.** Algunas arreglan algo que la petición ya implicaba: si pido un paso antes de «Venue» y el agente lo pone después, el fallo es del agente. Otras son cosas que solo decidí más tarde: «y documenta también la variable de entorno» no estaba en ninguna petición. Así que primero se clasificó cada expectativa como *deducible* (un buen ingeniero podría haber llegado a ella con la petición y el código) o como *nueva petición*. La medida principal solo cuenta las deducibles que cada modelo me dejaba por arreglar. Las nuevas peticiones van aparte, como quién se adelantó a lo que yo acabaría pidiendo.

**Tres jueces ciegos de dos laboratorios.** Cada tarea la juzgaron dos subagentes de Claude Opus 5.5 y gpt-6.1-sol de OpenAI a través de Codex, con esfuerzo alto. Los tres veían los siete resultados como letras, sin nombres de modelo en el código ni en las respuestas, con el repositorio de partida para contrastar lo que cada sesión afirmaba y, como apoyo, la salida de las comprobaciones que escribí para cada tarea; los dos jueces de Claude tenían barajados distintos. Con el mismo prompt, cada uno clasificaba las expectativas antes de mirar ningún resultado y después puntuaba cada una como cumplida, parcial o no cumplida. Los dos jueces de Claude coinciden mucho: sus recuentos de correcciones se correlacionan con r = 0,88 en las 133 sesiones. El juez de OpenAI es bastante más estricto, 5,4 correcciones por sesión frente a sus 3,2, y coincide menos con ellos (r = 0,65), así que presento las dos familias una al lado de la otra en lugar de promediarlas.

## Seis modelos, una franja

**Con las dos familias de jueces, seis modelos caen en una misma franja y DeepSeek queda por debajo.** Con los jueces de Claude, los seis necesitan entre 2,7 y 3,4 correcciones deducibles por tarea y DeepSeek 4,0; con el juez de OpenAI, entre 4,9 y 5,6, y DeepSeek 6,2.

<figure class="ttm-fig">
<svg viewBox="0 0 600 320" role="img" aria-label="Correcciones deducibles que aún harían falta por tarea, por modelo, con dos familias de jueces: con los jueces de Claude seis modelos se solapan entre 2,7 y 3,4 y DeepSeek queda en 4,0; con el juez de OpenAI, más estricto, seis se solapan entre 5,0 y 5,6 y DeepSeek queda en 6,2.">
<text x="230" y="24" fill="#e2e8f0" font-size="12.5" text-anchor="middle">Dos jueces de Claude</text>
<line x1="126" y1="44" x2="126" y2="260" stroke="rgba(255,255,255,0.08)"/>
<text x="126" y="278" fill="#94a3b8" font-size="11" text-anchor="middle">0</text>
<line x1="178" y1="44" x2="178" y2="260" stroke="rgba(255,255,255,0.08)"/>
<text x="178" y="278" fill="#94a3b8" font-size="11" text-anchor="middle">2</text>
<line x1="230" y1="44" x2="230" y2="260" stroke="rgba(255,255,255,0.08)"/>
<text x="230" y="278" fill="#94a3b8" font-size="11" text-anchor="middle">4</text>
<line x1="282" y1="44" x2="282" y2="260" stroke="rgba(255,255,255,0.08)"/>
<text x="282" y="278" fill="#94a3b8" font-size="11" text-anchor="middle">6</text>
<line x1="334" y1="44" x2="334" y2="260" stroke="rgba(255,255,255,0.08)"/>
<text x="334" y="278" fill="#94a3b8" font-size="11" text-anchor="middle">8</text>
<line x1="175.3" y1="58" x2="217.7" y2="58" stroke="#2dd4bf" stroke-width="3" stroke-linecap="round" opacity="0.55"/>
<circle cx="195.8" cy="58" r="5.5" fill="#2dd4bf"/>
<text x="195.8" y="49" fill="#94a3b8" font-size="10" text-anchor="middle">2,7</text>
<line x1="186.9" y1="88" x2="217.7" y2="88" stroke="#2dd4bf" stroke-width="3" stroke-linecap="round" opacity="0.55"/>
<circle cx="201.9" cy="88" r="5.5" fill="#2dd4bf"/>
<text x="201.9" y="79" fill="#94a3b8" font-size="10" text-anchor="middle">2,9</text>
<line x1="186.9" y1="118" x2="222.5" y2="118" stroke="#2dd4bf" stroke-width="3" stroke-linecap="round" opacity="0.55"/>
<circle cx="204.7" cy="118" r="5.5" fill="#2dd4bf"/>
<text x="204.7" y="109" fill="#94a3b8" font-size="10" text-anchor="middle">3,0</text>
<line x1="191.7" y1="148" x2="222.5" y2="148" stroke="#2dd4bf" stroke-width="3" stroke-linecap="round" opacity="0.55"/>
<circle cx="206.7" cy="148" r="5.5" fill="#2dd4bf"/>
<text x="206.7" y="139" fill="#94a3b8" font-size="10" text-anchor="middle">3,1</text>
<line x1="187.6" y1="178" x2="232.1" y2="178" stroke="#2dd4bf" stroke-width="3" stroke-linecap="round" opacity="0.55"/>
<circle cx="209.5" cy="178" r="5.5" fill="#2dd4bf"/>
<text x="209.5" y="169" fill="#94a3b8" font-size="10" text-anchor="middle">3,2</text>
<line x1="199.9" y1="208" x2="227.9" y2="208" stroke="#2dd4bf" stroke-width="3" stroke-linecap="round" opacity="0.55"/>
<circle cx="214.3" cy="208" r="5.5" fill="#2dd4bf"/>
<text x="214.3" y="199" fill="#94a3b8" font-size="10" text-anchor="middle">3,4</text>
<line x1="212.9" y1="238" x2="249.2" y2="238" stroke="#f59e0b" stroke-width="3" stroke-linecap="round" opacity="0.55"/>
<circle cx="230.0" cy="238" r="5.5" fill="#f59e0b"/>
<text x="230.0" y="229" fill="#94a3b8" font-size="10" text-anchor="middle">4,0</text>
<text x="481" y="24" fill="#e2e8f0" font-size="12.5" text-anchor="middle">Juez de OpenAI (Codex)</text>
<line x1="376" y1="44" x2="376" y2="260" stroke="rgba(255,255,255,0.08)"/>
<text x="376" y="278" fill="#94a3b8" font-size="11" text-anchor="middle">0</text>
<line x1="428" y1="44" x2="428" y2="260" stroke="rgba(255,255,255,0.08)"/>
<text x="428" y="278" fill="#94a3b8" font-size="11" text-anchor="middle">2</text>
<line x1="481" y1="44" x2="481" y2="260" stroke="rgba(255,255,255,0.08)"/>
<text x="481" y="278" fill="#94a3b8" font-size="11" text-anchor="middle">4</text>
<line x1="534" y1="44" x2="534" y2="260" stroke="rgba(255,255,255,0.08)"/>
<text x="534" y="278" fill="#94a3b8" font-size="11" text-anchor="middle">6</text>
<line x1="586" y1="44" x2="586" y2="260" stroke="rgba(255,255,255,0.08)"/>
<text x="586" y="278" fill="#94a3b8" font-size="11" text-anchor="middle">8</text>
<line x1="481.0" y1="58" x2="545.9" y2="58" stroke="#2dd4bf" stroke-width="3" stroke-linecap="round" opacity="0.55"/>
<circle cx="511.4" cy="58" r="5.5" fill="#2dd4bf"/>
<text x="511.4" y="49" fill="#94a3b8" font-size="10" text-anchor="middle">5,2</text>
<line x1="478.2" y1="88" x2="537.6" y2="88" stroke="#2dd4bf" stroke-width="3" stroke-linecap="round" opacity="0.55"/>
<circle cx="505.9" cy="88" r="5.5" fill="#2dd4bf"/>
<text x="505.9" y="79" fill="#94a3b8" font-size="10" text-anchor="middle">4,9</text>
<line x1="486.5" y1="118" x2="547.3" y2="118" stroke="#2dd4bf" stroke-width="3" stroke-linecap="round" opacity="0.55"/>
<circle cx="515.5" cy="118" r="5.5" fill="#2dd4bf"/>
<text x="515.5" y="109" fill="#94a3b8" font-size="10" text-anchor="middle">5,3</text>
<line x1="493.4" y1="148" x2="541.8" y2="148" stroke="#2dd4bf" stroke-width="3" stroke-linecap="round" opacity="0.55"/>
<circle cx="516.9" cy="148" r="5.5" fill="#2dd4bf"/>
<text x="516.9" y="139" fill="#94a3b8" font-size="10" text-anchor="middle">5,4</text>
<line x1="478.2" y1="178" x2="544.6" y2="178" stroke="#2dd4bf" stroke-width="3" stroke-linecap="round" opacity="0.55"/>
<circle cx="508.6" cy="178" r="5.5" fill="#2dd4bf"/>
<text x="508.6" y="169" fill="#94a3b8" font-size="10" text-anchor="middle">5,1</text>
<line x1="497.6" y1="208" x2="555.6" y2="208" stroke="#2dd4bf" stroke-width="3" stroke-linecap="round" opacity="0.55"/>
<circle cx="523.8" cy="208" r="5.5" fill="#2dd4bf"/>
<text x="523.8" y="199" fill="#94a3b8" font-size="10" text-anchor="middle">5,6</text>
<line x1="512.8" y1="238" x2="566.7" y2="238" stroke="#f59e0b" stroke-width="3" stroke-linecap="round" opacity="0.55"/>
<circle cx="537.6" cy="238" r="5.5" fill="#f59e0b"/>
<text x="537.6" y="229" fill="#94a3b8" font-size="10" text-anchor="middle">6,2</text>
<text x="112" y="62" fill="#e2e8f0" font-size="12.5" text-anchor="end">Gemini</text>
<text x="112" y="92" fill="#e2e8f0" font-size="12.5" text-anchor="end">Opus</text>
<text x="112" y="122" fill="#e2e8f0" font-size="12.5" text-anchor="end">Fable</text>
<text x="112" y="152" fill="#e2e8f0" font-size="12.5" text-anchor="end">GLM</text>
<text x="112" y="182" fill="#e2e8f0" font-size="12.5" text-anchor="end">Kimi</text>
<text x="112" y="212" fill="#e2e8f0" font-size="12.5" text-anchor="end">Qwen</text>
<text x="112" y="242" fill="#fbbf24" font-size="12.5" text-anchor="end">DeepSeek</text>
<text x="300" y="302" fill="#94a3b8" font-size="11.5" text-anchor="middle">correcciones que aún harían falta por tarea (media de 19 tareas, intervalo 95 %)</text>
</svg>
<figcaption>Media de correcciones deducibles que cada modelo seguía necesitando por tarea, en 19 tareas, con intervalos bootstrap del 95 % sobre las tareas, para los dos jueces de Claude y para el juez de OpenAI, más estricto, en la misma escala. El orden dentro de la franja verde azulada cambia con el juez; DeepSeek, en ámbar, es el último con los dos.</figcaption>
</figure>

El orden dentro de la franja depende de quién juzgue. Los jueces de Claude ponen primero a Gemini y segundo a Opus; el de OpenAI pone primero a Opus, segundo a Kimi y tercero a Gemini. Siete modelos forman veintiuna parejas, y con diecinueve tareas ninguna distancia dentro de la franja aguanta una corrección por hacer tantas comparaciones, con ninguno de los jueces. La de DeepSeek sí: frente a Opus y Gemini con las dos familias (1,3 correcciones más que Gemini por tarea según los jueces de Claude, con un intervalo del 95 % de 0,8 a 1,9), y también frente a GLM y Kimi con el juez de OpenAI. DeepSeek, además, fue el que menos cumplió de lo deducible según todos los jueces: un 43 % y un 40 %.

Tampoco lo clavó nadie solo. De 266 veredictos (siete modelos, diecinueve tareas, dos jueces), los jueces de Claude habrían aceptado un resultado tal cual solo 8 veces, y el de OpenAI, ninguno de sus 133. En mi trabajo real, cada uno de estos modelos sigue necesitando unas tres correcciones por tarea antes de que yo lo mergeara, que es más o menos lo que me pasó en las sesiones originales.

## Importó diez veces más la tarea que el modelo

**Las mismas tareas fueron fáciles o difíciles para todos.** Si reparto la variación de las correcciones en las 133 sesiones, con los jueces de Claude la tarea explica el 64 % y el modelo el 6 %; con el de OpenAI, el 88 % y el 2 %. El resto es la interacción: este modelo en esta tarea.

<figure class="ttm-fig">
<svg viewBox="0 0 600 478" role="img" aria-label="Correcciones por tarea y modelo: las filas varían mucho más que las columnas; las mismas tareas son fáciles o difíciles para todos.">
<text x="268" y="34" fill="#e2e8f0" font-size="11.5" text-anchor="middle">Gemini</text>
<text x="318" y="34" fill="#e2e8f0" font-size="11.5" text-anchor="middle">Opus</text>
<text x="366" y="34" fill="#e2e8f0" font-size="11.5" text-anchor="middle">Fable</text>
<text x="416" y="34" fill="#e2e8f0" font-size="11.5" text-anchor="middle">GLM</text>
<text x="464" y="34" fill="#e2e8f0" font-size="11.5" text-anchor="middle">Kimi</text>
<text x="514" y="34" fill="#e2e8f0" font-size="11.5" text-anchor="middle">Qwen</text>
<text x="562" y="34" fill="#fbbf24" font-size="11.5" text-anchor="middle">DeepSeek</text>
<text x="234" y="61" fill="#e2e8f0" font-size="11.5" text-anchor="end">Flujo de chat: un paso antes de «Venue»</text>
<rect x="246" y="48" width="45" height="18" rx="3" fill="rgb(45,212,191)" opacity="0.25"/>
<text x="268" y="61" fill="#f8fafc" font-size="11" text-anchor="middle">0</text>
<rect x="295" y="48" width="45" height="18" rx="3" fill="rgb(70,205,168)" opacity="0.33"/>
<text x="318" y="61" fill="#f8fafc" font-size="11" text-anchor="middle">1</text>
<rect x="344" y="48" width="45" height="18" rx="3" fill="rgb(70,205,168)" opacity="0.33"/>
<text x="366" y="61" fill="#f8fafc" font-size="11" text-anchor="middle">1</text>
<rect x="393" y="48" width="45" height="18" rx="3" fill="rgb(82,202,157)" opacity="0.36"/>
<text x="416" y="61" fill="#f8fafc" font-size="11" text-anchor="middle">1,5</text>
<rect x="442" y="48" width="45" height="18" rx="3" fill="rgb(82,202,157)" opacity="0.36"/>
<text x="464" y="61" fill="#f8fafc" font-size="11" text-anchor="middle">1,5</text>
<rect x="491" y="48" width="45" height="18" rx="3" fill="rgb(70,205,168)" opacity="0.33"/>
<text x="514" y="61" fill="#f8fafc" font-size="11" text-anchor="middle">1</text>
<rect x="540" y="48" width="45" height="18" rx="3" fill="rgb(108,195,135)" opacity="0.44"/>
<text x="562" y="61" fill="#f8fafc" font-size="11" text-anchor="middle">2,5</text>
<text x="234" y="83" fill="#e2e8f0" font-size="11.5" text-anchor="end">App de salud: escribir mientras responde</text>
<rect x="246" y="70" width="45" height="18" rx="3" fill="rgb(45,212,191)" opacity="0.25"/>
<text x="268" y="83" fill="#f8fafc" font-size="11" text-anchor="middle">0</text>
<rect x="295" y="70" width="45" height="18" rx="3" fill="rgb(70,205,168)" opacity="0.33"/>
<text x="318" y="83" fill="#f8fafc" font-size="11" text-anchor="middle">1</text>
<rect x="344" y="70" width="45" height="18" rx="3" fill="rgb(70,205,168)" opacity="0.33"/>
<text x="366" y="83" fill="#f8fafc" font-size="11" text-anchor="middle">1</text>
<rect x="393" y="70" width="45" height="18" rx="3" fill="rgb(70,205,168)" opacity="0.33"/>
<text x="416" y="83" fill="#f8fafc" font-size="11" text-anchor="middle">1</text>
<rect x="442" y="70" width="45" height="18" rx="3" fill="rgb(95,198,146)" opacity="0.40"/>
<text x="464" y="83" fill="#f8fafc" font-size="11" text-anchor="middle">2</text>
<rect x="491" y="70" width="45" height="18" rx="3" fill="rgb(95,198,146)" opacity="0.40"/>
<text x="514" y="83" fill="#f8fafc" font-size="11" text-anchor="middle">2</text>
<rect x="540" y="70" width="45" height="18" rx="3" fill="rgb(95,198,146)" opacity="0.40"/>
<text x="562" y="83" fill="#f8fafc" font-size="11" text-anchor="middle">2</text>
<text x="234" y="105" fill="#e2e8f0" font-size="11.5" text-anchor="end">Informe PDF: tablas solapadas</text>
<rect x="246" y="92" width="45" height="18" rx="3" fill="rgb(58,209,180)" opacity="0.29"/>
<text x="268" y="105" fill="#f8fafc" font-size="11" text-anchor="middle">0,5</text>
<rect x="295" y="92" width="45" height="18" rx="3" fill="rgb(95,198,146)" opacity="0.40"/>
<text x="318" y="105" fill="#f8fafc" font-size="11" text-anchor="middle">2</text>
<rect x="344" y="92" width="45" height="18" rx="3" fill="rgb(58,209,180)" opacity="0.29"/>
<text x="366" y="105" fill="#f8fafc" font-size="11" text-anchor="middle">0,5</text>
<rect x="393" y="92" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="416" y="105" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="442" y="92" width="45" height="18" rx="3" fill="rgb(82,202,157)" opacity="0.36"/>
<text x="464" y="105" fill="#f8fafc" font-size="11" text-anchor="middle">1,5</text>
<rect x="491" y="92" width="45" height="18" rx="3" fill="rgb(145,185,101)" opacity="0.55"/>
<text x="514" y="105" fill="#f8fafc" font-size="11" text-anchor="middle">4</text>
<rect x="540" y="92" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="562" y="105" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<text x="234" y="127" fill="#e2e8f0" font-size="11.5" text-anchor="end">Texto: ¿abuso de una palabra?</text>
<rect x="246" y="114" width="45" height="18" rx="3" fill="rgb(108,195,135)" opacity="0.44"/>
<text x="268" y="127" fill="#f8fafc" font-size="11" text-anchor="middle">2,5</text>
<rect x="295" y="114" width="45" height="18" rx="3" fill="rgb(82,202,157)" opacity="0.36"/>
<text x="318" y="127" fill="#f8fafc" font-size="11" text-anchor="middle">1,5</text>
<rect x="344" y="114" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="366" y="127" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="393" y="114" width="45" height="18" rx="3" fill="rgb(95,198,146)" opacity="0.40"/>
<text x="416" y="127" fill="#f8fafc" font-size="11" text-anchor="middle">2</text>
<rect x="442" y="114" width="45" height="18" rx="3" fill="rgb(70,205,168)" opacity="0.33"/>
<text x="464" y="127" fill="#f8fafc" font-size="11" text-anchor="middle">1</text>
<rect x="491" y="114" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="514" y="127" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="540" y="114" width="45" height="18" rx="3" fill="rgb(108,195,135)" opacity="0.44"/>
<text x="562" y="127" fill="#f8fafc" font-size="11" text-anchor="middle">2,5</text>
<text x="234" y="149" fill="#e2e8f0" font-size="11.5" text-anchor="end">Web: ¿todos los proyectos?</text>
<rect x="246" y="136" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="268" y="149" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="295" y="136" width="45" height="18" rx="3" fill="rgb(95,198,146)" opacity="0.40"/>
<text x="318" y="149" fill="#f8fafc" font-size="11" text-anchor="middle">2</text>
<rect x="344" y="136" width="45" height="18" rx="3" fill="rgb(95,198,146)" opacity="0.40"/>
<text x="366" y="149" fill="#f8fafc" font-size="11" text-anchor="middle">2</text>
<rect x="393" y="136" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="416" y="149" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="442" y="136" width="45" height="18" rx="3" fill="rgb(95,198,146)" opacity="0.40"/>
<text x="464" y="149" fill="#f8fafc" font-size="11" text-anchor="middle">2</text>
<rect x="491" y="136" width="45" height="18" rx="3" fill="rgb(82,202,157)" opacity="0.36"/>
<text x="514" y="149" fill="#f8fafc" font-size="11" text-anchor="middle">1,5</text>
<rect x="540" y="136" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="562" y="149" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<text x="234" y="171" fill="#e2e8f0" font-size="11.5" text-anchor="end">Web: ¿blog a LinkedIn?</text>
<rect x="246" y="158" width="45" height="18" rx="3" fill="rgb(108,195,135)" opacity="0.44"/>
<text x="268" y="171" fill="#f8fafc" font-size="11" text-anchor="middle">2,5</text>
<rect x="295" y="158" width="45" height="18" rx="3" fill="rgb(95,198,146)" opacity="0.40"/>
<text x="318" y="171" fill="#f8fafc" font-size="11" text-anchor="middle">2</text>
<rect x="344" y="158" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="366" y="171" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="393" y="158" width="45" height="18" rx="3" fill="rgb(95,198,146)" opacity="0.40"/>
<text x="416" y="171" fill="#f8fafc" font-size="11" text-anchor="middle">2</text>
<rect x="442" y="158" width="45" height="18" rx="3" fill="rgb(82,202,157)" opacity="0.36"/>
<text x="464" y="171" fill="#f8fafc" font-size="11" text-anchor="middle">1,5</text>
<rect x="491" y="158" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="514" y="171" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="540" y="158" width="45" height="18" rx="3" fill="rgb(145,185,101)" opacity="0.55"/>
<text x="562" y="171" fill="#f8fafc" font-size="11" text-anchor="middle">4</text>
<text x="234" y="193" fill="#e2e8f0" font-size="11.5" text-anchor="end">Clasificador: campos planos</text>
<rect x="246" y="180" width="45" height="18" rx="3" fill="rgb(70,205,168)" opacity="0.33"/>
<text x="268" y="193" fill="#f8fafc" font-size="11" text-anchor="middle">1</text>
<rect x="295" y="180" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="318" y="193" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="344" y="180" width="45" height="18" rx="3" fill="rgb(132,188,112)" opacity="0.51"/>
<text x="366" y="193" fill="#f8fafc" font-size="11" text-anchor="middle">3,5</text>
<rect x="393" y="180" width="45" height="18" rx="3" fill="rgb(70,205,168)" opacity="0.33"/>
<text x="416" y="193" fill="#f8fafc" font-size="11" text-anchor="middle">1</text>
<rect x="442" y="180" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="464" y="193" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="491" y="180" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="514" y="193" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="540" y="180" width="45" height="18" rx="3" fill="rgb(145,185,101)" opacity="0.55"/>
<text x="562" y="193" fill="#f8fafc" font-size="11" text-anchor="middle">4</text>
<text x="234" y="215" fill="#e2e8f0" font-size="11.5" text-anchor="end">Flujo de chat: opción de enviar de más</text>
<rect x="246" y="202" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="268" y="215" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="295" y="202" width="45" height="18" rx="3" fill="rgb(95,198,146)" opacity="0.40"/>
<text x="318" y="215" fill="#f8fafc" font-size="11" text-anchor="middle">2</text>
<rect x="344" y="202" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="366" y="215" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="393" y="202" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="416" y="215" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="442" y="202" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="464" y="215" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="491" y="202" width="45" height="18" rx="3" fill="rgb(95,198,146)" opacity="0.40"/>
<text x="514" y="215" fill="#f8fafc" font-size="11" text-anchor="middle">2</text>
<rect x="540" y="202" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="562" y="215" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<text x="234" y="237" fill="#e2e8f0" font-size="11.5" text-anchor="end">Bot de ops: compactar salidas</text>
<rect x="246" y="224" width="45" height="18" rx="3" fill="rgb(82,202,157)" opacity="0.36"/>
<text x="268" y="237" fill="#f8fafc" font-size="11" text-anchor="middle">1,5</text>
<rect x="295" y="224" width="45" height="18" rx="3" fill="rgb(108,195,135)" opacity="0.44"/>
<text x="318" y="237" fill="#f8fafc" font-size="11" text-anchor="middle">2,5</text>
<rect x="344" y="224" width="45" height="18" rx="3" fill="rgb(82,202,157)" opacity="0.36"/>
<text x="366" y="237" fill="#f8fafc" font-size="11" text-anchor="middle">1,5</text>
<rect x="393" y="224" width="45" height="18" rx="3" fill="rgb(132,188,112)" opacity="0.51"/>
<text x="416" y="237" fill="#f8fafc" font-size="11" text-anchor="middle">3,5</text>
<rect x="442" y="224" width="45" height="18" rx="3" fill="rgb(108,195,135)" opacity="0.44"/>
<text x="464" y="237" fill="#f8fafc" font-size="11" text-anchor="middle">2,5</text>
<rect x="491" y="224" width="45" height="18" rx="3" fill="rgb(158,182,90)" opacity="0.59"/>
<text x="514" y="237" fill="#f8fafc" font-size="11" text-anchor="middle">4,5</text>
<rect x="540" y="224" width="45" height="18" rx="3" fill="rgb(132,188,112)" opacity="0.51"/>
<text x="562" y="237" fill="#f8fafc" font-size="11" text-anchor="middle">3,5</text>
<text x="234" y="259" fill="#e2e8f0" font-size="11.5" text-anchor="end">Servicio de análisis: ¿README al día?</text>
<rect x="246" y="246" width="45" height="18" rx="3" fill="rgb(82,202,157)" opacity="0.36"/>
<text x="268" y="259" fill="#f8fafc" font-size="11" text-anchor="middle">1,5</text>
<rect x="295" y="246" width="45" height="18" rx="3" fill="rgb(108,195,135)" opacity="0.44"/>
<text x="318" y="259" fill="#f8fafc" font-size="11" text-anchor="middle">2,5</text>
<rect x="344" y="246" width="45" height="18" rx="3" fill="rgb(132,188,112)" opacity="0.51"/>
<text x="366" y="259" fill="#f8fafc" font-size="11" text-anchor="middle">3,5</text>
<rect x="393" y="246" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="416" y="259" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="442" y="246" width="45" height="18" rx="3" fill="rgb(82,202,157)" opacity="0.36"/>
<text x="464" y="259" fill="#f8fafc" font-size="11" text-anchor="middle">1,5</text>
<rect x="491" y="246" width="45" height="18" rx="3" fill="rgb(108,195,135)" opacity="0.44"/>
<text x="514" y="259" fill="#f8fafc" font-size="11" text-anchor="middle">2,5</text>
<rect x="540" y="246" width="45" height="18" rx="3" fill="rgb(170,178,78)" opacity="0.62"/>
<text x="562" y="259" fill="#f8fafc" font-size="11" text-anchor="middle">5</text>
<text x="234" y="281" fill="#e2e8f0" font-size="11.5" text-anchor="end">Clasificador: falso positivo en registro</text>
<rect x="246" y="268" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="268" y="281" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="295" y="268" width="45" height="18" rx="3" fill="rgb(108,195,135)" opacity="0.44"/>
<text x="318" y="281" fill="#f8fafc" font-size="11" text-anchor="middle">2,5</text>
<rect x="344" y="268" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="366" y="281" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="393" y="268" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="416" y="281" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="442" y="268" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="464" y="281" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="491" y="268" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="514" y="281" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="540" y="268" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="562" y="281" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<text x="234" y="303" fill="#e2e8f0" font-size="11.5" text-anchor="end">Bot de ops: ¿está todo auditado?</text>
<rect x="246" y="290" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="268" y="303" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="295" y="290" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="318" y="303" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="344" y="290" width="45" height="18" rx="3" fill="rgb(145,185,101)" opacity="0.55"/>
<text x="366" y="303" fill="#f8fafc" font-size="11" text-anchor="middle">4</text>
<rect x="393" y="290" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="416" y="303" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="442" y="290" width="45" height="18" rx="3" fill="rgb(58,209,180)" opacity="0.29"/>
<text x="464" y="303" fill="#f8fafc" font-size="11" text-anchor="middle">0,5</text>
<rect x="491" y="290" width="45" height="18" rx="3" fill="rgb(132,188,112)" opacity="0.51"/>
<text x="514" y="303" fill="#f8fafc" font-size="11" text-anchor="middle">3,5</text>
<rect x="540" y="290" width="45" height="18" rx="3" fill="rgb(182,175,67)" opacity="0.66"/>
<text x="562" y="303" fill="#f8fafc" font-size="11" text-anchor="middle">5,5</text>
<text x="234" y="325" fill="#e2e8f0" font-size="11.5" text-anchor="end">Agentes de análisis: plan alternativo</text>
<rect x="246" y="312" width="45" height="18" rx="3" fill="rgb(95,198,146)" opacity="0.40"/>
<text x="268" y="325" fill="#f8fafc" font-size="11" text-anchor="middle">2</text>
<rect x="295" y="312" width="45" height="18" rx="3" fill="rgb(120,192,124)" opacity="0.47"/>
<text x="318" y="325" fill="#f8fafc" font-size="11" text-anchor="middle">3</text>
<rect x="344" y="312" width="45" height="18" rx="3" fill="rgb(145,185,101)" opacity="0.55"/>
<text x="366" y="325" fill="#f8fafc" font-size="11" text-anchor="middle">4</text>
<rect x="393" y="312" width="45" height="18" rx="3" fill="rgb(132,188,112)" opacity="0.51"/>
<text x="416" y="325" fill="#f8fafc" font-size="11" text-anchor="middle">3,5</text>
<rect x="442" y="312" width="45" height="18" rx="3" fill="rgb(170,178,78)" opacity="0.62"/>
<text x="464" y="325" fill="#f8fafc" font-size="11" text-anchor="middle">5</text>
<rect x="491" y="312" width="45" height="18" rx="3" fill="rgb(158,182,90)" opacity="0.59"/>
<text x="514" y="325" fill="#f8fafc" font-size="11" text-anchor="middle">4,5</text>
<rect x="540" y="312" width="45" height="18" rx="3" fill="rgb(132,188,112)" opacity="0.51"/>
<text x="562" y="325" fill="#f8fafc" font-size="11" text-anchor="middle">3,5</text>
<text x="234" y="347" fill="#e2e8f0" font-size="11.5" text-anchor="end">Servidor MCP: implementar un plan</text>
<rect x="246" y="334" width="45" height="18" rx="3" fill="rgb(158,182,90)" opacity="0.59"/>
<text x="268" y="347" fill="#f8fafc" font-size="11" text-anchor="middle">4,5</text>
<rect x="295" y="334" width="45" height="18" rx="3" fill="rgb(132,188,112)" opacity="0.51"/>
<text x="318" y="347" fill="#f8fafc" font-size="11" text-anchor="middle">3,5</text>
<rect x="344" y="334" width="45" height="18" rx="3" fill="rgb(132,188,112)" opacity="0.51"/>
<text x="366" y="347" fill="#f8fafc" font-size="11" text-anchor="middle">3,5</text>
<rect x="393" y="334" width="45" height="18" rx="3" fill="rgb(132,188,112)" opacity="0.51"/>
<text x="416" y="347" fill="#f8fafc" font-size="11" text-anchor="middle">3,5</text>
<rect x="442" y="334" width="45" height="18" rx="3" fill="rgb(132,188,112)" opacity="0.51"/>
<text x="464" y="347" fill="#f8fafc" font-size="11" text-anchor="middle">3,5</text>
<rect x="491" y="334" width="45" height="18" rx="3" fill="rgb(132,188,112)" opacity="0.51"/>
<text x="514" y="347" fill="#f8fafc" font-size="11" text-anchor="middle">3,5</text>
<rect x="540" y="334" width="45" height="18" rx="3" fill="rgb(158,182,90)" opacity="0.59"/>
<text x="562" y="347" fill="#f8fafc" font-size="11" text-anchor="middle">4,5</text>
<text x="234" y="369" fill="#e2e8f0" font-size="11.5" text-anchor="end">App de salud: inglés y ruso</text>
<rect x="246" y="356" width="45" height="18" rx="3" fill="rgb(108,195,135)" opacity="0.44"/>
<text x="268" y="369" fill="#f8fafc" font-size="11" text-anchor="middle">2,5</text>
<rect x="295" y="356" width="45" height="18" rx="3" fill="rgb(145,185,101)" opacity="0.55"/>
<text x="318" y="369" fill="#f8fafc" font-size="11" text-anchor="middle">4</text>
<rect x="344" y="356" width="45" height="18" rx="3" fill="rgb(145,185,101)" opacity="0.55"/>
<text x="366" y="369" fill="#f8fafc" font-size="11" text-anchor="middle">4</text>
<rect x="393" y="356" width="45" height="18" rx="3" fill="rgb(158,182,90)" opacity="0.59"/>
<text x="416" y="369" fill="#f8fafc" font-size="11" text-anchor="middle">4,5</text>
<rect x="442" y="356" width="45" height="18" rx="3" fill="rgb(195,172,56)" opacity="0.70"/>
<text x="464" y="369" fill="#f8fafc" font-size="11" text-anchor="middle">6</text>
<rect x="491" y="356" width="45" height="18" rx="3" fill="rgb(145,185,101)" opacity="0.55"/>
<text x="514" y="369" fill="#f8fafc" font-size="11" text-anchor="middle">4</text>
<rect x="540" y="356" width="45" height="18" rx="3" fill="rgb(108,195,135)" opacity="0.44"/>
<text x="562" y="369" fill="#f8fafc" font-size="11" text-anchor="middle">2,5</text>
<text x="234" y="391" fill="#e2e8f0" font-size="11.5" text-anchor="end">Agentes de análisis: unir salidas</text>
<rect x="246" y="378" width="45" height="18" rx="3" fill="rgb(108,195,135)" opacity="0.44"/>
<text x="268" y="391" fill="#f8fafc" font-size="11" text-anchor="middle">2,5</text>
<rect x="295" y="378" width="45" height="18" rx="3" fill="rgb(145,185,101)" opacity="0.55"/>
<text x="318" y="391" fill="#f8fafc" font-size="11" text-anchor="middle">4</text>
<rect x="344" y="378" width="45" height="18" rx="3" fill="rgb(145,185,101)" opacity="0.55"/>
<text x="366" y="391" fill="#f8fafc" font-size="11" text-anchor="middle">4</text>
<rect x="393" y="378" width="45" height="18" rx="3" fill="rgb(108,195,135)" opacity="0.44"/>
<text x="416" y="391" fill="#f8fafc" font-size="11" text-anchor="middle">2,5</text>
<rect x="442" y="378" width="45" height="18" rx="3" fill="rgb(182,175,67)" opacity="0.66"/>
<text x="464" y="391" fill="#f8fafc" font-size="11" text-anchor="middle">5,5</text>
<rect x="491" y="378" width="45" height="18" rx="3" fill="rgb(170,178,78)" opacity="0.62"/>
<text x="514" y="391" fill="#f8fafc" font-size="11" text-anchor="middle">5</text>
<rect x="540" y="378" width="45" height="18" rx="3" fill="rgb(145,185,101)" opacity="0.55"/>
<text x="562" y="391" fill="#f8fafc" font-size="11" text-anchor="middle">4</text>
<text x="234" y="413" fill="#e2e8f0" font-size="11.5" text-anchor="end">Clasificador: ¿cómo elige?</text>
<rect x="246" y="400" width="45" height="18" rx="3" fill="rgb(170,178,78)" opacity="0.62"/>
<text x="268" y="413" fill="#f8fafc" font-size="11" text-anchor="middle">5</text>
<rect x="295" y="400" width="45" height="18" rx="3" fill="rgb(182,175,67)" opacity="0.66"/>
<text x="318" y="413" fill="#f8fafc" font-size="11" text-anchor="middle">5,5</text>
<rect x="344" y="400" width="45" height="18" rx="3" fill="rgb(70,205,168)" opacity="0.33"/>
<text x="366" y="413" fill="#f8fafc" font-size="11" text-anchor="middle">1</text>
<rect x="393" y="400" width="45" height="18" rx="3" fill="rgb(158,182,90)" opacity="0.59"/>
<text x="416" y="413" fill="#f8fafc" font-size="11" text-anchor="middle">4,5</text>
<rect x="442" y="400" width="45" height="18" rx="3" fill="rgb(195,172,56)" opacity="0.70"/>
<text x="464" y="413" fill="#f8fafc" font-size="11" text-anchor="middle">6</text>
<rect x="491" y="400" width="45" height="18" rx="3" fill="rgb(158,182,90)" opacity="0.59"/>
<text x="514" y="413" fill="#f8fafc" font-size="11" text-anchor="middle">4,5</text>
<rect x="540" y="400" width="45" height="18" rx="3" fill="rgb(208,168,45)" opacity="0.74"/>
<text x="562" y="413" fill="#f8fafc" font-size="11" text-anchor="middle">6,5</text>
<text x="234" y="435" fill="#e2e8f0" font-size="11.5" text-anchor="end">Clasificador: versión real en /health</text>
<rect x="246" y="422" width="45" height="18" rx="3" fill="rgb(208,168,45)" opacity="0.74"/>
<text x="268" y="435" fill="#f8fafc" font-size="11" text-anchor="middle">6,5</text>
<rect x="295" y="422" width="45" height="18" rx="3" fill="rgb(182,175,67)" opacity="0.66"/>
<text x="318" y="435" fill="#f8fafc" font-size="11" text-anchor="middle">5,5</text>
<rect x="344" y="422" width="45" height="18" rx="3" fill="rgb(195,172,56)" opacity="0.70"/>
<text x="366" y="435" fill="#f8fafc" font-size="11" text-anchor="middle">6</text>
<rect x="393" y="422" width="45" height="18" rx="3" fill="rgb(182,175,67)" opacity="0.66"/>
<text x="416" y="435" fill="#f8fafc" font-size="11" text-anchor="middle">5,5</text>
<rect x="442" y="422" width="45" height="18" rx="3" fill="rgb(208,168,45)" opacity="0.74"/>
<text x="464" y="435" fill="#f8fafc" font-size="11" text-anchor="middle">6,5</text>
<rect x="491" y="422" width="45" height="18" rx="3" fill="rgb(158,182,90)" opacity="0.59"/>
<text x="514" y="435" fill="#f8fafc" font-size="11" text-anchor="middle">4,5</text>
<rect x="540" y="422" width="45" height="18" rx="3" fill="rgb(195,172,56)" opacity="0.70"/>
<text x="562" y="435" fill="#f8fafc" font-size="11" text-anchor="middle">6</text>
<text x="234" y="457" fill="#e2e8f0" font-size="11.5" text-anchor="end">App de salud: bugs documentados</text>
<rect x="246" y="444" width="45" height="18" rx="3" fill="rgb(208,168,45)" opacity="0.74"/>
<text x="268" y="457" fill="#f8fafc" font-size="11" text-anchor="middle">6,5</text>
<rect x="295" y="444" width="45" height="18" rx="3" fill="rgb(170,178,78)" opacity="0.62"/>
<text x="318" y="457" fill="#f8fafc" font-size="11" text-anchor="middle">5</text>
<rect x="344" y="444" width="45" height="18" rx="3" fill="rgb(195,172,56)" opacity="0.70"/>
<text x="366" y="457" fill="#f8fafc" font-size="11" text-anchor="middle">6</text>
<rect x="393" y="444" width="45" height="18" rx="3" fill="rgb(195,172,56)" opacity="0.70"/>
<text x="416" y="457" fill="#f8fafc" font-size="11" text-anchor="middle">6</text>
<rect x="442" y="444" width="45" height="18" rx="3" fill="rgb(182,175,67)" opacity="0.66"/>
<text x="464" y="457" fill="#f8fafc" font-size="11" text-anchor="middle">5,5</text>
<rect x="491" y="444" width="45" height="18" rx="3" fill="rgb(182,175,67)" opacity="0.66"/>
<text x="514" y="457" fill="#f8fafc" font-size="11" text-anchor="middle">5,5</text>
<rect x="540" y="444" width="45" height="18" rx="3" fill="rgb(245,158,11)" opacity="0.85"/>
<text x="562" y="457" fill="#f8fafc" font-size="11" text-anchor="middle">8</text>
</svg>
<figcaption>Correcciones deducibles por tarea (filas, de la más fácil a la más difícil) y modelo (columnas, por media), con la media de los dos jueces. Las filas cambian mucho más que las columnas: las mismas tareas son fáciles o difíciles para todos los modelos.</figcaption>
</figure>

Las dos tareas más difíciles enseñan por qué. En una, el endpoint de salud de un servicio mostraba una versión antigua. El arreglo que acepté dependía de cómo un pipeline de build compartido, que vive en otro repositorio, pasa el tag de git a la imagen; y por el camino yo había pedido arreglar un test que ya estaba roto y corregir una afirmación falsa en la documentación de despliegue. Todos los modelos necesitaron cuatro correcciones o más. En la otra, la petición era «tenemos documentados unos cuantos bugs del chat, ¿puedes mirarlos?», y nadie arregló suficientes.

**Mis preguntas se leyeron como preguntas.** Siete de las diecinueve peticiones tenían forma de pregunta: «¿puedes mirarlos?», «¿cómo funciona exactamente el selector?», «me gustaría saber si hay alguna posibilidad de automatizar esto». En todas quería el cambio, no solo la respuesta. En esas siete, 40 de 49 sesiones contestaron y se pararon, y necesitaron el empujón para empezar; en las otras doce, 15 de 84. Les pasó a todos los modelos. Cuando revisé una muestra a mano, DeepSeek había escrito en los bugs del chat un buen diagnóstico, con archivo y línea para cada bug, y después, incluso tras el «adelante», preguntó si quería que los arreglara. Quería. Así lo juzgué y así cuenta.

## En lo que se diferencian es en cómo fallan

**Con el mismo número de correcciones, cada modelo deja un tipo distinto de trabajo pendiente.**

| Modelo | Correcciones por tarea | Correcciones, juez de OpenAI | Deducibles cumplidas | Nuevas peticiones anticipadas | Problemas nuevos introducidos | Afirmaciones falsas | Aceptado tal cual (de 38) |
|---|---|---|---|---|---|---|---|
| Gemini 4 Argon | 2,7 | 5,2 | 66 % | 20 % | 1,2 | 0,13 | 4 |
| Opus 5 | 2,9 | 4,9 | 65 % | 15 % | 1,2 | 0,18 | 1 |
| Fable 5 | 3,0 | 5,3 | 58 % | 12 % | 0,6 | 0,21 | 1 |
| GLM 5.3 | 3,1 | 5,4 | 54 % | 9 % | 0,7 | 0,16 | 0 |
| Kimi K3.1 Pro | 3,2 | 5,1 | 59 % | 18 % | 0,9 | 0,05 | 2 |
| Qwen3.8 | 3,4 | 5,6 | 54 % | 6 % | 0,9 | 0,21 | 0 |
| DeepSeek V4 Pro | 4,0 | 6,2 | 43 % | 10 % | 0,7 | 0,21 | 0 |

*Todas las columnas salvo la tercera salen de los dos jueces de Claude; la misma tabla para el juez de OpenAI está en el repositorio. En las deducibles cumplidas, las parciales cuentan la mitad. Los problemas nuevos son cosas que los jueces encontraron rotas o añadidas sin que se pidieran; las afirmaciones falsas, frases de la respuesta final que el diff o las comprobaciones contradicen. Ambas son por veredicto.*

Opus cumple de lo deducible tanto como el que más según todos los jueces, y también toca más cosas que nadie pidió que Fable: 1,2 problemas nuevos por veredicto frente a 0,6 según los jueces de Claude, y 1,2 frente a 0,7 según el de OpenAI. Gemini sale alto en problemas nuevos con los jueces de Claude, pero no con el de OpenAI. En una tarea sobre un falso positivo contra un registro público, Opus escribió una coincidencia aproximada más estricta y bien testeada cuando yo había exigido una exacta, y de paso añadió un script de depuración. Fable hace menos, pero rompe menos. Qwen fue el que menos se adelantó a lo que yo pediría después, y Kimi el que menos afirmó cosas falsas, según todos los jueces. Y el fallo de DeepSeek tiene una forma reconocible: en un flujo de chat en el que yo había pedido un paso antes de «Venue», puso el paso en uno de los dos sitios donde hacía falta, rompió tres tests que antes pasaban y terminó con «implementado y con tests verdes».

## Lo que revisé a mano

**Revisé una muestra de los veredictos con los modelos a la vista, y estuve de acuerdo con ellos.** Cuatro casos: el único resultado que los dos jueces de Claude habrían mergeado tal cual (Gemini, el paso del flujo de chat, la única sesión que lo puso en los dos sitios), DeepSeek en esa misma tarea, DeepSeek en los bugs del chat y Opus en la coincidencia con el registro. El que necesitaba mi criterio eran los bugs del chat, porque «¿puedes mirarlos?» se podía leer como una petición de diagnóstico y nada más. Yo esperaba los arreglos, así que el «no hizo nada» se mantiene. Es una muestra pequeña, y la elegí para poner a prueba al juez donde más podía equivocarse, no al azar.

## Lo que dice esto de las sensaciones

**En mi propio trabajo, mi sospecha sobre Opus no aparece como más correcciones.** [El primer artículo](/es/blog/benchmaxing) partía de la sensación de que Opus 5 trabaja peor que Fable 5 a pesar de sus benchmarks. Aquí necesitan la misma guía: 2,9 frente a 3,0 correcciones por tarea según los jueces de Claude, y 4,9 frente a 5,3 según el de OpenAI. Lo que cambia es la textura: Opus hace más y se dispersa más; Fable se queda más cerca de lo que se le pide. Y esa textura no es neutra. Incluso dentro de una sola tarea, un cambio que nadie pidió es algo que tengo que revisar y muchas veces deshacer. Con meses de trabajo sobre el mismo código, un modelo que toca archivos fuera de lo pedido hace el código más difícil de mantener y puede alterar la documentación sin que se note. Una medida hecha con tareas aisladas lo cuenta una vez por tarea; nunca ve cómo se acumula ese coste. Puede que sea justo eso lo que captaba mi impresión.

**La medida que pedí es también la que iguala el campo.** Contar las correcciones que necesitó mi propio trabajo es lo más cerca que sé llegar de las sensaciones con un número, y con ella seis modelos de cinco laboratorios no se distinguen. Los modelos abiertos no rinden peor de lo que prometen sus benchmarks; uno de ellos, simplemente, necesita más. Lo que separa una buena sesión de una mala es sobre todo qué tarea llevé, con qué claridad la pedí y cuánto de lo que quería vivía solo en mi cabeza.

Me llevo dos cosas prácticas. Una pregunta recibe una respuesta: si quiero el cambio, tengo que pedir el cambio. Y los modelos baratos no son una apuesta arriesgada en mi tipo de trabajo, con la excepción que medí.

## Lo que esto no puede decir

**Una sesión por modelo y tarea.** Los intervalos recogen la variación entre tareas, no lo que pasaría si corriera el mismo modelo dos veces en la misma tarea. Además, cada tarea está aislada, así que nada de esto mide lo que cuestan los cambios de más tras meses sobre el mismo código. Dos de los jueces son de la misma familia que dos de los participantes, y por eso añadí uno de otro laboratorio. No mostró ventaja de casa: el juez de OpenAI coloca a Opus más arriba que los de Claude. Lo que sí mostró es cuánto mueve las cifras absolutas lo estricto que sea un juez, así que solo las leo unas frente a otras. Las expectativas salen de sesiones con Claude Code y Codex, así que recogen lo que esos agentes hicieron mal; un modelo que repite esos errores sale penalizado, y uno que comete otros puede librarse. Y diecinueve tareas de una sola persona son un retrato de mi trabajo, no de la ingeniería de software.

---

*Método: Claude Code 2.1.314 sin interfaz en Docker, `--max-turns 120`, dos workers. Las copias de los repositorios se cortaron en el commit base, sin referencias posteriores; una pasada anterior que dejaba la historia posterior alcanzable se descartó allí donde una sesión la había visto, y esas 27 sesiones se repitieron. Los datos personales de salud se quitaron de las copias. Los diffs se miden contra el commit de preparación, así que el trabajo commiteado cuenta. Jueces: dos subagentes de Claude Opus 5.5 por tarea, con barajados distintos, y gpt-6.1-sol de OpenAI a través de Codex CLI con esfuerzo alto sobre el primer barajado, todos con el mismo prompt y el mismo esquema de salida; los jueces de Claude coincidieron en el tipo de expectativa 134 de 142 veces y en los veredictos 895 de 994, y el de OpenAI coincidió con el primero de ellos en 817 de 994 veredictos. Intervalos: bootstrap sobre las 19 tareas, 10.000 remuestreos, donde la puntuación de cada modelo en cada tarea es la media de los dos jueces; comparaciones por parejas: test de permutación con cambio de signo sobre las tareas, con corrección de Holm sobre las 21 parejas. Gasto en OpenRouter: unos 350 USD, repeticiones incluidas; Opus y Fable corrieron con una suscripción Max. Las tareas contienen código privado y de empresa, así que [el repositorio](https://github.com/JaviMaligno/benchmaxing-probes/tree/main/realtasks) guarda el entorno, el prompt y los scripts del juez y los resultados anonimizados por veredicto, con un script que reproduce todas las cifras de este artículo, pero no las tareas ni las sesiones.*
