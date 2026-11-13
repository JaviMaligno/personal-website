---
title: "ChatGPT lee la letra, no oye la melodía"
description: "Le tarareé Cumpleaños feliz a ChatGPT y no supo decir qué era; con la letra contestó al instante. Después pasé 150 grabaciones sin palabras por los modelos de voz de OpenAI: nombran una canción por su letra y sin ella quedan en el azar, mientras un modelo diminuto de contorno acertó mis tres tarareos."
pubDate: 2026-12-17
tags: ["IA", "Voz", "Evaluación", "Multimodal", "Machine Learning"]
lang: es
translationKey: chatgpt-cant-hear-a-tune
heroImage: "/blog/chatgpt-cant-hear-a-tune.png"
---

Cuando le hablas a ChatGPT da la sensación de que está escuchando. Yo quería saber qué llega de verdad al otro lado, así que elegí lo más sencillo que lleva una voz además de las palabras: una melodía. Le tarareé Cumpleaños feliz a ChatGPT de todas las formas en que la aplicación me deja hablarle, y después hice la misma pregunta a escala a los modelos de voz que OpenAI vende a los desarrolladores.

<style>
.hum-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.hum-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.hum-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
</style>

## Dos botones, dos cosas distintas

**El micrófono y el botón de voz no hacen lo mismo.** El micrófono pequeño es el dictado: la [página de ayuda de OpenAI](https://help.openai.com/en/articles/20001274-chatgpt-voice) lo describe como convertir una grabación en texto editable, que luego envías como cualquier cosa que hubieras tecleado. El otro botón abre el modo voz, una conversación hablada que hoy funciona con un modelo llamado GPT-Live-1.1.

<figure class="hum-fig">
<svg viewBox="0 0 600 230" role="img" aria-label="El dictado convierte la voz en texto antes de que el modelo la vea, así que un tarareo llega como mensaje vacío; el modo voz envía el propio sonido a un modelo de voz">
  <defs>
    <marker id="hum-ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#64748b"/></marker>
  </defs>
  <text x="20" y="28" fill="#94a3b8" font-size="13">Dictado (botón del micrófono)</text>
  <rect x="20" y="42" width="110" height="46" rx="8" fill="none" stroke="#64748b"/>
  <text x="75" y="70" fill="#e2e8f0" font-size="13" text-anchor="middle">mi tarareo</text>
  <rect x="175" y="42" width="120" height="46" rx="8" fill="none" stroke="#f59e0b"/>
  <text x="235" y="70" fill="#fbbf24" font-size="13" text-anchor="middle">transcriptor</text>
  <rect x="340" y="42" width="100" height="46" rx="8" fill="none" stroke="#64748b"/>
  <text x="390" y="70" fill="#e2e8f0" font-size="13" text-anchor="middle">texto: «»</text>
  <rect x="485" y="42" width="95" height="46" rx="8" fill="none" stroke="#64748b"/>
  <text x="532" y="70" fill="#e2e8f0" font-size="13" text-anchor="middle">modelo de texto</text>
  <g stroke="#64748b" stroke-width="2" fill="none" marker-end="url(#hum-ar)"><path d="M130,65 H170"/><path d="M295,65 H335"/><path d="M440,65 H480"/></g>
  <text x="20" y="140" fill="#94a3b8" font-size="13">Modo voz (el botón que te contesta)</text>
  <rect x="20" y="154" width="110" height="46" rx="8" fill="none" stroke="#64748b"/>
  <text x="75" y="182" fill="#e2e8f0" font-size="13" text-anchor="middle">mi tarareo</text>
  <rect x="340" y="154" width="240" height="46" rx="8" fill="none" stroke="#2dd4bf"/>
  <text x="460" y="182" fill="#5eead4" font-size="13" text-anchor="middle">modelo de voz (recibe el sonido)</text>
  <g stroke="#64748b" stroke-width="2" fill="none" marker-end="url(#hum-ar)"><path d="M130,177 H335"/></g>
  <text x="232" y="170" fill="#94a3b8" font-size="12" text-anchor="middle">audio</text>
</svg>
<figcaption>Con el dictado el modelo solo ve texto, y un tarareo no tiene texto. Con el modo voz el sonido llega a un modelo, así que la pregunta pasa a ser qué hace ese modelo con él.</figcaption>
</figure>

**El dictado no escribió nada.** Tarareé Cumpleaños feliz dos veces, una con «hmmm» y otra con «na na na», y las dos veces la caja de texto se quedó vacía. Es lo esperable de un transcriptor: no había palabras que apuntar.

**El modo voz me dijo que no podía.** Le dije que iba a tararear una canción y le pregunté cuál era. Antes de que tararease una sola nota contestó:

> Me encantaría poder hacerlo, pero ahora mismo no puedo identificar canciones por tarareos o melodías. Estamos trabajando en eso y pronto podré hacerlo. Si quieres, puedes decirme alguna frase de la letra y veo si podemos localizarla juntos.

Lo intenté otra vez en un chat nuevo, tarareando sin avisar y preguntando después qué canción era, y la respuesta fue la misma. Entonces canté «Cumpleaños feliz» con su letra y contestó al instante que era Happy Birthday.

El producto, por tanto, es honesto con el límite. Lo que no podía saber desde la aplicación es si el modelo de detrás oye la melodía y lo frenan, o si no la oye lo bastante bien como para intentarlo. Para eso fui a los modelos directamente.

## La misma pregunta, por la API

**Probé tres formas de hacer llegar una voz a un modelo de OpenAI**, todas desplegadas en Azure OpenAI:

- **Transcribir y preguntar**: `gpt-4o-mini-transcribe` pone el audio por escrito y `gpt-6-luna`, un modelo de texto, responde a partir de la transcripción. Es lo que hace el dictado, y sirve además de referencia: es la vía que no oye nada salvo las palabras.
- **`gpt-audio-1.5`**: un modelo de chat que recibe el archivo de audio como entrada.
- **`gpt-realtime-2.1`**: el modelo de voz a voz con el que los desarrolladores montan agentes de voz.

Ninguno de ellos es GPT-Live, el modelo del modo voz de ChatGPT, que solo pude probar desde la aplicación. Son los modelos de voz de OpenAI tal como los recibe un desarrollador.

Como grabaciones usé [MTG-QBH](https://zenodo.org/records/1290712), un conjunto de investigación con 118 audios de gente cantando o tarareando canciones pop sin acompañamiento. Tomé los primeros 20 segundos de cada uno y pregunté a cada vía qué canción era. Un modelo de texto calificó las respuestas, y contrasté sus veredictos con la coincidencia literal del título. A partir de dos transcripciones por audio los separé en 76 cantados con letra, 30 sin ninguna palabra y 12 intermedios.

<figure class="hum-fig">
<svg viewBox="0 0 600 270" role="img" aria-label="Con letra las tres vías nombran entre 71 y 74 de 76 canciones; sin palabras nombran 0, 1 y 1 de 30">
  <line x1="50" y1="210" x2="570" y2="210" stroke="#64748b"/>
  <g font-size="12" fill="#e2e8f0" text-anchor="middle">
    <rect x="80" y="70" width="50" height="140" fill="#64748b"/><text x="105" y="62">71/76</text>
    <rect x="150" y="70" width="50" height="140" fill="#f59e0b"/><text x="175" y="62">71/76</text>
    <rect x="220" y="64" width="50" height="146" fill="#2dd4bf"/><text x="245" y="56">74/76</text>
    <rect x="350" y="209" width="50" height="1" fill="#64748b"/><text x="375" y="200">0/30</text>
    <rect x="420" y="205" width="50" height="5" fill="#f59e0b"/><text x="445" y="196">1/30</text>
    <rect x="490" y="205" width="50" height="5" fill="#2dd4bf"/><text x="515" y="196">1/30</text>
  </g>
  <g font-size="13" fill="#e2e8f0" text-anchor="middle">
    <text x="175" y="232">Cantadas con letra</text>
    <text x="445" y="232">Sin palabras</text>
  </g>
  <g font-size="12" fill="#94a3b8">
    <rect x="70" y="248" width="10" height="10" fill="#64748b"/><text x="86" y="257">transcribir y preguntar</text>
    <rect x="250" y="248" width="10" height="10" fill="#f59e0b"/><text x="266" y="257">gpt-audio-1.5</text>
    <rect x="400" y="248" width="10" height="10" fill="#2dd4bf"/><text x="416" y="257">gpt-realtime-2.1</text>
  </g>
</svg>
<figcaption>Canciones nombradas correctamente en MTG-QBH. La vía que solo lee una transcripción acierta tanto como las dos que reciben el audio, y las tres se hunden cuando desaparecen las palabras.</figcaption>
</figure>

**Con letra, la vía que solo lee una transcripción nombró 71 de 76 canciones, las mismas que `gpt-audio-1.5`.** `gpt-realtime-2.1` nombró 74. El audio no añadió nada medible a las palabras. Sin palabras, las tres vías nombraron 0, 1 y 1 de 30, y el único acierto fue «Ob-La-Di, Ob-La-Da», cuyas sílabas son el título.

**Cuando `gpt-realtime-2.1` se arriesgó, dijo «Hey Jude».** Pasé cada audio sin palabras tres veces: 64 de sus 90 respuestas fueron «unknown» y 19 fueron «Hey Jude», para tarareos de «Bohemian Rhapsody», «Smells Like Teen Spirit» o «Sweet Home Alabama». Le bastó un «na na na» para decidirlo.

## Quizá la oyen y no saben nombrarla

**La objeción evidente es que nombrar una canción es difícil aunque oigas la melodía.** Así que puse la tarea fácil. [MLEnd Hums and Whistles](https://www.kaggle.com/datasets/jesusrequena/mlend-hums-and-whistles) es un conjunto de gente tarareando y silbando ocho canciones de cine. Tomé 120 tarareos, 15 por canción, de 95 personas distintas, y le di al modelo la lista de las ocho para que eligiera. Respondiendo a ciegas se acierta el 12,5 %.

`gpt-realtime-2.1` eligió la correcta en 11 de 120, un 9 %. La vía de solo transcripción, que en la mayoría de estos audios recibió una transcripción vacía, acertó 16 de 120. Oír el tarareo no fue mejor que no oírlo.

<figure class="hum-fig">
<svg viewBox="0 0 600 300" role="img" aria-label="Cada una de las ocho canciones se tarareó 15 veces, pero gpt-realtime-2.1 eligió Harry Potter 50 veces, La Pantera Rosa 37 y Star Wars 32, y casi nunca las otras cinco">
  <g font-size="12.5" fill="#e2e8f0" text-anchor="end">
    <text x="165" y="39">Tema de Harry Potter</text><text x="165" y="69">Tema de La Pantera Rosa</text><text x="165" y="99">Tema de Star Wars</text><text x="165" y="129">Singin' in the Rain</text><text x="165" y="159">Hakuna Matata</text><text x="165" y="189">Mamma Mia</text><text x="165" y="219">The Greatest Showman</text><text x="165" y="249">Let It Go</text>
  </g>
  <g fill="#2dd4bf">
    <rect x="175" y="26" width="300" height="18"/><rect x="175" y="56" width="222" height="18"/><rect x="175" y="86" width="192" height="18"/><rect x="175" y="116" width="6" height="18"/>
    <rect x="175" y="146" width="1" height="18"/><rect x="175" y="176" width="1" height="18"/><rect x="175" y="206" width="1" height="18"/><rect x="175" y="236" width="1" height="18"/>
  </g>
  <g font-size="12" fill="#5eead4">
    <text x="481" y="40">50</text><text x="403" y="70">37</text><text x="373" y="100">32</text><text x="187" y="130">1</text><text x="182" y="160">0</text><text x="182" y="190">0</text><text x="182" y="220">0</text><text x="182" y="250">0</text>
  </g>
  <line x1="265" y1="18" x2="265" y2="262" stroke="#f59e0b" stroke-dasharray="5 4" stroke-width="2"/>
  <text x="271" y="282" fill="#fbbf24" font-size="12">cada canción se tarareó 15 veces</text>
</svg>
<figcaption>Lo que eligió gpt-realtime-2.1 para 120 tarareos con los ocho títulos delante. Repartió sus respuestas entre tres de ellos, se tararease lo que se tararease: así se elige cuando no se oye la melodía.</figcaption>
</figure>

**Sus elecciones no seguían al audio.** Cada canción se tarareó 15 veces, y aun así el modelo respondió Harry Potter 50 veces, La Pantera Rosa 37 y Star Wars 32, y las otras cinco canciones una sola vez entre todas. Con la pregunta abierta, sin lista, nombró 1 tarareo de 119.

## Mi propia voz, y un modelo que sí la oye

**Me grabé a mí mismo para dejar fija la canción y cambiar una sola cosa cada vez.** Cuatro tarareos (Cumpleaños feliz, el Himno de la alegría, Jingle Bells y «Dear Prudence» de los Beatles), Cumpleaños feliz cantada con su letra, y una grabación con trampa: la letra de Cumpleaños feliz cantada con la melodía de Jingle Bells.

<figure class="hum-fig">
<svg viewBox="0 0 600 300" role="img" aria-label="Ninguna vía de OpenAI nombró ninguno de mis cuatro tarareos, todas nombraron la canción en cuanto tuvo letra y todas dijeron que la melodía de la grabación cruzada era Cumpleaños feliz; hum2song puso primera la melodía correcta en los tres tarareos de su catálogo">
  <g font-size="12" fill="#94a3b8" text-anchor="middle">
    <text x="262" y="24">transcribir</text><text x="262" y="38">y preguntar</text><text x="352" y="31">gpt-audio-1.5</text><text x="447" y="31">gpt-realtime-2.1</text><text x="540" y="31">hum2song</text>
  </g>
  <g font-size="12.5" fill="#e2e8f0">
    <text x="14" y="72">Tarareada: Cumpleaños feliz</text><text x="14" y="108">Tarareada: Himno de la alegría</text><text x="14" y="144">Tarareada: Jingle Bells</text><text x="14" y="180">Tarareada: Dear Prudence</text><text x="14" y="216">Cantada con su letra</text><text x="14" y="246">Letra de Cumpleaños feliz,</text><text x="14" y="261">melodía de Jingle Bells</text>
  </g>
  <g font-size="13" text-anchor="middle">
    <g fill="#94a3b8"><text x="262" y="72">no</text><text x="352" y="72">0 de 3</text><text x="447" y="72">0 de 3</text><text x="262" y="108">no</text><text x="352" y="108">0 de 3</text><text x="447" y="108">0 de 3</text><text x="262" y="144">no</text><text x="352" y="144">0 de 3</text><text x="447" y="144">0 de 3</text><text x="262" y="180">no</text><text x="352" y="180">0 de 3</text><text x="447" y="180">0 de 3</text><text x="540" y="180">no está en su lista</text><text x="540" y="216">–</text><text x="540" y="254">–</text></g>
    <g fill="#5eead4"><text x="540" y="72">1.ª de 15</text><text x="540" y="108">1.ª de 15</text><text x="540" y="144">1.ª de 15</text><text x="262" y="216">sí</text><text x="352" y="216">3 de 3</text><text x="447" y="216">3 de 3</text></g>
    <g fill="#fbbf24"><text x="352" y="254">melodía: Cumpleaños feliz (las 7 respuestas)</text></g>
  </g>
  <g stroke="rgba(255,255,255,0.1)"><line x1="10" y1="48" x2="590" y2="48"/><line x1="10" y1="194" x2="590" y2="194"/><line x1="10" y1="228" x2="590" y2="228"/></g>
</svg>
<figcaption>Mis grabaciones. Las tres vías de OpenAI fallan en todos los tarareos y aciertan en cuanto hay letra; un modelo pequeño que solo ve el contorno de la melodía encuentra los tres tarareos que tiene en su catálogo.</figcaption>
</figure>

**Ninguna vía nombró ninguno de los cuatro tarareos; todas nombraron la canción en cuanto tuvo letra.** La grabación con trampa es el resultado más claro. Pregunté por separado a qué canción pertenece la letra y a cuál la melodía, y las siete respuestas dijeron que la melodía era Cumpleaños feliz. Preguntados directamente por la melodía, los modelos respondieron con la letra.

**Un modelo pequeño que solo mira la melodía no tuvo problema.** [hum2song](https://github.com/luiginotmario/hum2song) es un modelo abierto que convierte en un vector el contorno de tono de una grabación, es decir, cómo sube y baja la nota a lo largo del tiempo, y lo compara con los contornos de melodías conocidas. Funciona en mi portátil. Le di un catálogo de 15 melodías muy conocidas y mis tres tarareos que están en él, y puso la melodía correcta en primer lugar en los tres. Con la misma lista de 15 para elegir, `gpt-realtime-2.1` acertó en 0 de 9 intentos y `gpt-audio-1.5` en 2 de 9; la vía de solo transcripción, sin nada en que apoyarse, acertó 1 de 3. Tres tarareos de una sola persona son un ejemplo y no una medida, pero enseñan que la información está en la grabación.

## Lo que sí llega

**Los modelos de voz no son sordos a todo lo que no sean palabras.** En [RAVDESS](https://zenodo.org/records/1188976), donde actores dicen la misma frase con distintas emociones, usé 48 audios de cuatro emociones: `gpt-audio-1.5` acertó la emoción en 37 y `gpt-realtime-2.1` en 28 de 47, frente a 12 esperables por azar. Y cuando canté dos notas separadas por más de una octava, `gpt-realtime-2.1` dijo cuál era más aguda las seis veces que se lo pregunté.

Así que parte del sonido llega: lo suficiente para una emoción gruesa o un salto amplio de tono, no lo suficiente para seguir una melodía. Esa es la versión precisa del título. El tono de voz solo lo sondeé, y no le atribuyo más de lo que dicen esas cifras.

## Con qué me quedo

**Si las palabras son las mismas, da por hecho que al modelo le llegó el mismo mensaje.** Es la lectura práctica para quien construya sobre estos modelos, un agente telefónico de atención al cliente por ejemplo: una cadena que transcribe primero le entrega al modelo texto y nada más, y un modelo de voz a voz oye más que eso, pero menos de lo que aparenta la conversación.

Es la misma forma que encontré con imágenes en [Un nivel de gris sobre 255](/es/blog/perception-edges-of-language): lo que un modelo percibe no es lo que yo percibiría en su lugar, en ninguno de los dos sentidos, y la única manera de saberlo es medir.

Los límites conviene decirlos. A ChatGPT lo probé a mano, unas pocas veces y en español, y declinó en lugar de intentarlo. Las mediciones son sobre tres modelos de OpenAI por la API, con los primeros 15 a 20 segundos de cada grabación, y los audios de MTG-QBH proceden de solo 17 cantantes. No probé modelos de otras empresas.

ChatGPT dice que está trabajando en ello, y puede que esté resuelto cuando leas esto. Lo interesante es la pregunta de fondo: qué haría falta para que un modelo así oiga una melodía, y si darle una herramienta que sí la oye es el camino más corto. Esa es la siguiente entrega.
