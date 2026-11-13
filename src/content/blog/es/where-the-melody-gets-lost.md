---
title: "Un truco de los 90 oye la melodía que un modelo de voz no oye"
description: "Los modelos de voz de OpenAI y Alibaba quedan en el azar al nombrar una canción tarareada entre ocho. Una búsqueda por contorno de tono de los años 90 acierta el 46 %, y como herramienta de un modelo de texto arregla el problema por céntimos. Sondear un codificador de voz capa a capa enseña adónde va la melodía."
pubDate: 2026-12-17
tags: ["IA", "Voz", "Evaluación", "Multimodal", "Machine Learning"]
lang: es
translationKey: where-the-melody-gets-lost
heroImage: "/blog/where-the-melody-gets-lost.png"
---

En [el artículo anterior](/es/blog/chatgpt-cant-hear-a-tune) le tarareé canciones a ChatGPT y a los modelos de voz de OpenAI, y encontré que nombran una canción por su letra y se pierden sin ella. Quedaba la pregunta que de verdad me interesaba: por qué, y qué haría falta para arreglarlo. Mantuve las mismas 120 grabaciones y cambié quién las escucha.

<style>
.mel-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.mel-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.mel-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
</style>

## Oír una melodía no es reconocerla

**Son dos capacidades distintas, y la segunda necesita un catálogo.** Oír una melodía es conservar su forma: esta nota, luego una más aguda, luego una grave y larga. Reconocerla es comparar esa forma con melodías que ya conoces. Una persona que nunca ha oído una canción puede tararearla de vuelta y seguir sin saber cómo se llama.

Los sistemas que hacen esto bien están construidos sobre esa separación. Shazam no oye melodías en absoluto: [su método publicado](https://www.ee.columbia.edu/~dpwe/papers/Wang03-shazam.pdf) saca una huella de una grabación concreta a partir de los picos de su espectrograma, así que encuentra la pista de estudio que suena en un bar y no tiene con qué comparar cuando tarareas. La búsqueda por tarareo de Google va en la dirección contraria. [Google describe](https://research.google/blog/the-machine-learning-behind-hum-to-search/) una red que convierte el audio en un embedding solo de la melodía, entrenada para que un tarareo caiga cerca de la grabación de la misma canción, y que busca entre más de medio millón de canciones. Lo probé desde el móvil: tarareé Cumpleaños feliz y La Marsellesa, y encontró las dos.

Un modelo de voz no tiene ninguna de las dos piezas por diseño. Se entrenó para entender el habla, y lo que sepa de melodías lo aprendió de paso.

## El método más viejo del manual

**La búsqueda por tarareo es un campo de investigación de los años 90, y su primera receta cabe en tres pasos.** Seguir el tono de la voz. Tirar la tonalidad, para que dé igual lo agudo que cante cada persona. Comparar el contorno que queda con los contornos que tienes, estirando el tiempo para que tampoco importe la velocidad.

Escribí esa receta en un script corto, con un extractor de tono estándar y alineamiento temporal dinámico, la forma clásica de comparar dos curvas que avanzan a distinta velocidad. Las grabaciones son los 120 tarareos de [MLEnd Hums and Whistles](https://www.kaggle.com/datasets/jesusrequena/mlend-hums-and-whistles) que ya había usado: ocho canciones de cine, 15 tarareos de cada una, 95 personas. Para cada tarareo, la búsqueda localiza el tarareo más parecido de otra persona y responde con la canción de esa persona. No hay ninguna red neuronal.

<figure class="mel-fig">
<svg viewBox="0 0 600 210" role="img" aria-label="Eligiendo entre ocho canciones para 120 tarareos, los dos modelos de voz que oyen el audio nombran 11 y 12, por debajo de los 15 esperables por azar, mientras una búsqueda por contorno nombra 55 y un modelo de texto que usa esa búsqueda como herramienta nombra 56">
  <text x="260" y="36" fill="#e2e8f0" font-size="12.5" text-anchor="end">Respondiendo a ciegas</text>
  <rect x="270" y="22" width="34" height="20" fill="#64748b"/>
  <text x="311" y="37" fill="#e2e8f0" font-size="12.5">15</text>
  <text x="260" y="70" fill="#e2e8f0" font-size="12.5" text-anchor="end">gpt-realtime-2.1, oye el audio</text>
  <rect x="270" y="56" width="25" height="20" fill="#f59e0b"/>
  <text x="302" y="71" fill="#e2e8f0" font-size="12.5">11</text>
  <text x="260" y="104" fill="#e2e8f0" font-size="12.5" text-anchor="end">Qwen2.5-Omni-3B, oye el audio</text>
  <rect x="270" y="90" width="27" height="20" fill="#f59e0b"/>
  <text x="304" y="105" fill="#e2e8f0" font-size="12.5">12</text>
  <text x="260" y="138" fill="#e2e8f0" font-size="12.5" text-anchor="end">Búsqueda por contorno (método de los 90)</text>
  <rect x="270" y="124" width="124" height="20" fill="#2dd4bf"/>
  <text x="401" y="139" fill="#e2e8f0" font-size="12.5">55</text>
  <text x="260" y="172" fill="#e2e8f0" font-size="12.5" text-anchor="end">Modelo de texto + búsqueda como herramienta</text>
  <rect x="270" y="158" width="126" height="20" fill="#2dd4bf"/>
  <text x="403" y="173" fill="#e2e8f0" font-size="12.5">56</text>
</svg>
<figcaption>Tarareos nombrados de 120, eligiendo entre ocho canciones de cine. Los modelos que reciben el sonido no lo hacen mejor que el azar; una búsqueda sobre la forma de la melodía acierta casi la mitad, con o sin un modelo de lenguaje que lea su resultado.</figcaption>
</figure>

**Nombró 55 de 120, un 46 %, donde el azar da un 12,5 %.** Con las mismas grabaciones y las mismas ocho opciones, `gpt-realtime-2.1`, el modelo de voz a voz de OpenAI, nombró 11. Así que la melodía está en la grabación y una técnica muy antigua la saca. El problema no es difícil de la manera que disculparía a un modelo grande.

Dos cautelas sobre ese 46 %. Es una elección entre ocho canciones, con tarareos de otras personas de esas mismas canciones como referencia, no un reconocimiento contra un catálogo real. Y es la versión más simple del método: la gente tararea pasajes distintos de cada tema, y eso explica parte de los fallos.

## No es solo OpenAI

**Un modelo abierto de otra empresa falla igual.** Pasé Qwen2.5-Omni-3B, el modelo de audio abierto de Alibaba, por los mismos tarareos y las mismas preguntas. Con la pregunta abierta respondió «unknown» las 120 veces. Con las ocho opciones acertó 12, y contestó «1» en 80 de las 120, el primer elemento de la lista se tararease lo que se tararease.

Encaja con lo que dicen los benchmarks sobre el tono en general. En [PitchBench](https://arxiv.org/abs/2605.26176), un conjunto de tareas de tono con sonidos sintetizados, el mejor modelo de lenguaje con audio saca un 53,9 % de media mientras una referencia clásica de procesado de señal saca un 73,2 %. El modelo que pude ejecutar es el pequeño de su familia; sus hermanos mayores encabezan esos benchmarks y no caben en una GPU gratuita.

## El arreglo es una herramienta

**Si el modelo no oye la melodía, dale algo que sí la oiga.** Convertí la búsqueda por contorno en una herramienta: devuelve sus cinco coincidencias más cercanas con sus títulos, y un modelo de texto, `gpt-6-luna`, responde a partir de esa lista sin recibir nunca el audio.

Nombró 56 de 120 eligiendo entre las ocho, y 40 de 120 con la pregunta abierta, frente a 11 y 1 del modelo de voz que sí oye la grabación. Toda la corrida costó dos céntimos de dólar. La canción correcta estaba entre las cinco coincidencias de la herramienta en 97 de los 120 tarareos, así que la mayor parte del error que queda es de mi búsqueda mínima, y una mejor subiría el resultado.

En el primer artículo un modelo pequeño entrenado, [hum2song](https://github.com/luiginotmario/hum2song), puso mis tres tarareos en primer lugar entre quince melodías. Es la versión aprendida de la misma idea: reducir la grabación a su contorno y comparar contornos.

**Lo que no pude hacer es saltarme el catálogo.** También probé a darle al modelo de texto las notas directamente. Con tonos sintetizados limpios de cuatro melodías clásicas, nombró las cuatro a partir de la lista de notas. Con cantantes reales y 118 canciones pop, la misma vía no nombró ninguna. Un modelo de lenguaje tiene una memoria escasa de las melodías como notas: le alcanza para Cumpleaños feliz, no para el pop. Reconocer exige la lista de canciones con la que comparar, que es justo lo que lleva una herramienta de búsqueda.

## Adónde va la melodía

**Quería ver la pérdida mientras ocurre, así que miré dentro de un codificador.** OpenAI no publica cómo reciben el audio sus modelos de voz, pero sí publica [Whisper](https://arxiv.org/abs/2212.04356), su modelo de reconocimiento de voz, cuyo codificador es la entrada abierta estándar para el habla. Pasé por él los 120 tarareos y, en cada una de sus doce capas, intenté leer de vuelta el tono con la sonda más simple posible: un ajuste lineal, comprobado con cantantes que no había visto.

<figure class="mel-fig">
<svg viewBox="0 0 600 280" role="img" aria-label="Una lectura lineal del tono en el codificador de Whisper correlaciona 0,69 con el tono real en la entrada, 0,90 en las capas 2 y 3, y cae de forma sostenida hasta 0,63 en la última capa">
  <line x1="70" y1="210" x2="570" y2="210" stroke="rgba(255,255,255,0.08)"/>
  <text x="62" y="214" fill="#94a3b8" font-size="11" text-anchor="end">0.5</text>
  <line x1="70" y1="174" x2="570" y2="174" stroke="rgba(255,255,255,0.08)"/>
  <text x="62" y="178" fill="#94a3b8" font-size="11" text-anchor="end">0.6</text>
  <line x1="70" y1="138" x2="570" y2="138" stroke="rgba(255,255,255,0.08)"/>
  <text x="62" y="142" fill="#94a3b8" font-size="11" text-anchor="end">0.7</text>
  <line x1="70" y1="102" x2="570" y2="102" stroke="rgba(255,255,255,0.08)"/>
  <text x="62" y="106" fill="#94a3b8" font-size="11" text-anchor="end">0.8</text>
  <line x1="70" y1="66" x2="570" y2="66" stroke="rgba(255,255,255,0.08)"/>
  <text x="62" y="70" fill="#94a3b8" font-size="11" text-anchor="end">0.9</text>
  <line x1="70" y1="30" x2="570" y2="30" stroke="rgba(255,255,255,0.08)"/>
  <text x="62" y="34" fill="#94a3b8" font-size="11" text-anchor="end">1.0</text>
  <polyline points="70,142 108,93 147,69 185,66 224,66 262,69 301,74 339,80 378,95 416,103 455,119 493,131 532,141 570,164" fill="none" stroke="#2dd4bf" stroke-width="2.5"/>
  <circle cx="70" cy="142" r="3.5" fill="#2dd4bf"/>
  <circle cx="108" cy="93" r="3.5" fill="#2dd4bf"/>
  <circle cx="147" cy="69" r="3.5" fill="#2dd4bf"/>
  <circle cx="185" cy="66" r="3.5" fill="#2dd4bf"/>
  <circle cx="224" cy="66" r="3.5" fill="#2dd4bf"/>
  <circle cx="262" cy="69" r="3.5" fill="#2dd4bf"/>
  <circle cx="301" cy="74" r="3.5" fill="#2dd4bf"/>
  <circle cx="339" cy="80" r="3.5" fill="#2dd4bf"/>
  <circle cx="378" cy="95" r="3.5" fill="#2dd4bf"/>
  <circle cx="416" cy="103" r="3.5" fill="#2dd4bf"/>
  <circle cx="455" cy="119" r="3.5" fill="#2dd4bf"/>
  <circle cx="493" cy="131" r="3.5" fill="#2dd4bf"/>
  <circle cx="532" cy="141" r="3.5" fill="#2dd4bf"/>
  <circle cx="570" cy="164" r="3.5" fill="#2dd4bf"/>
  <text x="70" y="228" fill="#94a3b8" font-size="11" text-anchor="middle">entrada</text>
  <text x="108" y="228" fill="#94a3b8" font-size="11" text-anchor="middle">emb.</text>
  <text x="147" y="228" fill="#94a3b8" font-size="11" text-anchor="middle">1</text>
  <text x="185" y="228" fill="#94a3b8" font-size="11" text-anchor="middle">2</text>
  <text x="224" y="228" fill="#94a3b8" font-size="11" text-anchor="middle">3</text>
  <text x="262" y="228" fill="#94a3b8" font-size="11" text-anchor="middle">4</text>
  <text x="301" y="228" fill="#94a3b8" font-size="11" text-anchor="middle">5</text>
  <text x="339" y="228" fill="#94a3b8" font-size="11" text-anchor="middle">6</text>
  <text x="378" y="228" fill="#94a3b8" font-size="11" text-anchor="middle">7</text>
  <text x="416" y="228" fill="#94a3b8" font-size="11" text-anchor="middle">8</text>
  <text x="455" y="228" fill="#94a3b8" font-size="11" text-anchor="middle">9</text>
  <text x="493" y="228" fill="#94a3b8" font-size="11" text-anchor="middle">10</text>
  <text x="532" y="228" fill="#94a3b8" font-size="11" text-anchor="middle">11</text>
  <text x="570" y="228" fill="#94a3b8" font-size="11" text-anchor="middle">12</text>
  <text x="199" y="54" fill="#5eead4" font-size="12.5">capas 2–3: 0,90</text>
  <text x="570" y="186" fill="#fbbf24" font-size="12.5" text-anchor="end">salida: 0,63</text>
  <text x="320" y="252" fill="#94a3b8" font-size="12" text-anchor="middle">Codificador de Whisper: entrada, embedding y capas 1 a 12</text>
  <text x="16" y="120" fill="#94a3b8" font-size="12" text-anchor="middle" transform="rotate(-90 16 120)">cuánto tono se puede leer (correlación)</text>
</svg>
<figcaption>Tono leído con una sonda lineal en cada capa del codificador de Whisper, con cantantes que la sonda no había visto. La melodía es más nítida justo después de la entrada y se desdibuja hacia la capa que recibiría un modelo de lenguaje.</figcaption>
</figure>

**La melodía es más nítida justo después de la entrada y se desdibuja a partir de ahí.** La lectura correlaciona 0,90 con el tono real en las capas 2 y 3, y 0,63 en la última, la que se le entregaría a un modelo de lenguaje. Un codificador entrenado para poner palabras por escrito tiene todos los motivos para hacerlo: el tono es lo que debe ignorar para reconocer la misma palabra en dos hablantes distintos.

Una correlación no dice si lo que queda sigue siendo una melodía utilizable, así que repetí la búsqueda de canciones tres veces, cambiando solo de dónde sale el contorno.

<figure class="mel-fig">
<svg viewBox="0 0 600 200" role="img" aria-label="La misma búsqueda de canciones nombra 56 de 120 tarareos con el tono real, 62 con el tono leído en la capa 3 del codificador, 34 con el leído en su salida, y el modelo de voz completo nombra 11; el azar son 15">
  <text x="260" y="36" fill="#e2e8f0" font-size="12.5" text-anchor="end">Tono real de la grabación</text>
  <rect x="270" y="22" width="126" height="20" fill="#2dd4bf"/>
  <text x="403" y="37" fill="#e2e8f0" font-size="12.5">56</text>
  <text x="260" y="70" fill="#e2e8f0" font-size="12.5" text-anchor="end">Tono leído en la capa 3</text>
  <rect x="270" y="56" width="140" height="20" fill="#2dd4bf"/>
  <text x="417" y="71" fill="#e2e8f0" font-size="12.5">62</text>
  <text x="260" y="104" fill="#e2e8f0" font-size="12.5" text-anchor="end">Tono leído en la salida del codificador</text>
  <rect x="270" y="90" width="76" height="20" fill="#f59e0b"/>
  <text x="353" y="105" fill="#e2e8f0" font-size="12.5">34</text>
  <text x="260" y="138" fill="#e2e8f0" font-size="12.5" text-anchor="end">Modelo de voz completo (gpt-realtime-2.1)</text>
  <rect x="270" y="124" width="25" height="20" fill="#64748b"/>
  <text x="313" y="139" fill="#e2e8f0" font-size="12.5">11</text>
  <line x1="304" y1="14" x2="304" y2="158" stroke="#f59e0b" stroke-dasharray="5 4" stroke-width="2"/>
  <text x="310" y="174" fill="#fbbf24" font-size="12">azar: 15</text>
</svg>
<figcaption>Canciones encontradas por la misma búsqueda, cambiando solo de dónde se lee la melodía. A la salida del codificador ya falta la mitad; un modelo de voz completo no usa nada de lo que queda.</figcaption>
</figure>

**La mitad de la melodía sobrevive al codificador, y el modelo completo no usa nada de ella.** Leído en la capa 3, el contorno encuentra 62 de 120 canciones, algo mejor que las 56 del propio extractor de tono. Leído en la salida encuentra 34, muy por encima de las 15 del azar. El modelo de voz completo encuentra 11.

Hay, por tanto, dos pérdidas. Parte de la melodía se desgasta dentro del codificador, y lo que queda no se recoge después. Un benchmark reciente, [SonicBench](https://arxiv.org/abs/2601.11039), describe la segunda mitad de esto para propiedades básicas del sonido: los codificadores congelados las conservan mientras los modelos completos responden cerca del azar, y sus autores sitúan el cuello de botella en las etapas posteriores al codificador. Con tarareos, yo veo las dos.

Los límites aquí importan. Whisper es el codificador abierto de OpenAI, no necesariamente el que llevan `gpt-realtime-2.1` o el modo voz de ChatGPT. Sondeé su versión pequeña, con 120 tarareos, y una sonda lineal da un suelo: una lectura más rica podría recuperar más de la última capa.

## Con qué me quedo

**Un modelo que oye no es un modelo que lo escucha todo.** Un modelo de habla conserva lo que le entrenaron a conservar. Para la melodía, la respuesta que funciona hoy es la de hace treinta años, envuelta como herramienta: extraer el contorno, buscar en un catálogo y dejar que el modelo de lenguaje ponga las palabras.

Aplicaría el mismo patrón antes de dar por hecho que un modelo de voz oye cualquier otra cosa que no sean palabras: lo rápido que habla alguien, si duda, si se cortó la línea. Primero medirlo y, si no está, un pequeño oyente especializado junto al modelo sale barato.

Quedan abiertas dos cosas, y cada una merece su propia entrega. La primera es qué significa ese 46 %. No sé cuánto acertaría una persona con estos mismos tarareos, y sospecho que la respuesta depende más de la familiaridad que del oído: de si conoces la canción, de si la conoces pero no sabes cómo se llama, de qué pasaje se tarareó. Una melodía de los Beatles seguramente la reconocería; una que he oído unas pocas veces, quizá no. La segunda es la propia herramienta de búsqueda. Ocho canciones son un juguete. Encontrar un contorno entre millones de pistas, deprisa y con una noción de similitud que aguante a alguien que canta mal, es un campo entero.

Todo esto es sobre un solo corpus de ocho canciones, con un modelo de voz por empresa y mi búsqueda mínima. Enseña dónde mirar, no cómo de grande es la distancia en general.
