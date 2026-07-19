---
title: "Enseñarle a un modelo un idioma que acabas de inventar"
description: "Háblale a un modelo en un cifrado del que nunca le has dado la clave y ocurre algo sorprendente antes de que descifre nada: algunos modelos se niegan a jugar. Un pequeño experimento sobre cuán rápido descifran códigos nuevos — y dónde eso choca con un muro de seguridad."
pubDate: 2026-07-18
tags: ["IA", "Machine Learning", "Evaluación", "Alineamiento", "Seguridad"]
lang: es
translationKey: ciphers-edges-of-language
heroImage: "/blog/ciphers-edges-of-language.png"
linkedinImage: /blog/ciphers-safety-boundary.png
repoUrl: https://github.com/JaviMaligno/llm-language-limits
---

Los criptógrafos tienen una palabra para el momento en que un cifrado se abre: el *break*. Miras un muro de `Wklv pdnhv qr vhqvh`, cuentas letras, y de golpe la forma del idioma que hay debajo emerge y el galimatías resulta ser inglés con máscara. Los criptoanalistas humanos lo describen como un clic. Quería saber qué aspecto tiene ese clic para un modelo de lenguaje — y, más concretamente, *cuán rápido* ocurre cuando al modelo nunca le han dado la clave.

Este es el segundo artículo de una serie suelta sobre los **bordes del lenguaje** — lo que hacen los modelos cuando empujas su entrada fuera de la distribución bien educada en la que se entrenaron. El [primero](/es/blog/repetition-edges-of-language) iba de repetición. Este empezó como una pregunta simple: **háblale a un modelo en un código que no conoce, ¿cuántos turnos tarda en pillarlo y en empezar a responder en el mismo código?**

Obtuve una respuesta a eso. Pero primero me topé con algo que no buscaba.

## El montaje

Construí una escalera de **diez cifrados**, desde los que el modelo seguro ha visto en el entrenamiento hasta los que tiene que inferir de verdad:

- **Sustitución:** ROT13, y una *sustitución aleatoria con clave* — una permutación arbitraria del alfabeto que el modelo no puede haber memorizado, así que descifrarla exige análisis de frecuencias real.
- **Reasignación de símbolos:** letras→dígitos (`a=1…`), Morse.
- **Codificación base:** binario, base64.
- **Transposición:** inversión total del texto, y una permutación por bloques con clave.
- **Mezcla de alfabetos:** homóglifos latino↔cirílico.
- **Con pérdida:** disemvoweling (quitar las vocales).

Cada turno, el modelo recibe una **tarea verificable** corta ("responde con el nombre de la fruta alargada y amarilla", "cuánto es siete más cinco") codificada con el cifrado activo. Todo el sentido de usar tareas verificables es que el oráculo es **determinista** — codifico y decodifico los cifrados yo mismo, así que puntuar si el modelo *actuó correctamente* no necesita un juez LLM, solo una comprobación de cadena. (Esa fue la parte frágil del estudio de repetición; aquí la diseñé fuera.)

Medí dos cosas por conversación: **comprensión** — ¿actuó el modelo correctamente sobre la tarea decodificada, en cualquier idioma? — y **producción** — ¿empezó a *responder en el código* él mismo? Y probé tres **protocolos** de exposición: *puro* (hablar en cifrado desde el turno uno), *few-shot* (mostrar unos pares de ejemplo texto-plano↔codificado primero — una piedra Rosetta) y *escalado* (empezar puro, añadir pistas si flaquea).

Cinco modelos: Claude Opus y Sonnet, GPT-5, y Qwen2.5-7B en sus versiones Instruct y Base.

## Lo que no buscaba

Aquí es donde el plan se encuentra con la realidad. Antes de poder medir *cuán rápido* descifra nadie un código, tuve que darme cuenta de que **dos de mis cinco modelos se niegan a intentarlo.**

![Gráfico de barras de tasa de rechazo por modelo: Claude Opus 87%, Claude Sonnet 86%, GPT-5 0%, Qwen Instruct 0%, Qwen Base 0%. Una anotación indica que el filtro de contenido de Azure bloquea los prompts cifrados de GPT-5 como 'jailbreak' antes de que el modelo los vea.](/blog/ciphers-safety-boundary.png)

**Claude Opus y Sonnet rechazan ~87% de los turnos codificados.** No "fallan al decodificar" — *rechazan*, con el `stop_reason: refusal` de la API y una respuesta vacía. Dale al mismo modelo la misma pregunta en inglés plano y responde al instante y bien ("La capital de Francia es **París**"). No es que Claude no sepa leer ROT13; es que Claude no actúa sobre una instrucción que no puede leer como texto plano.

Y el rechazo lo modela la **ilegibilidad**. ROT13, base64, binario, Morse, sustitución con clave — cualquier cosa que convierta el mensaje en ruido visual — lleva el rechazo cerca del 100%. Pero `cyrillic_homoglyph`, donde el texto todavía *parece* palabras, se rechaza solo un tercio de las veces. La guardia del modelo sube exactamente con lo ajeno que se ve la entrada.

GPT-5 choca con un muro *distinto*, un turno antes. El filtro de contenido de Azure clasifica los prompts cifrados como un **intento de jailbreak** y devuelve un 400 antes de que el modelo los vea siquiera. (Para poder medir GPT-5 tuve que enrutarlo por un deployment con el escudo de jailbreak desactivado — los filtros de categorías de daño totalmente puestos. Vuelvo luego a por qué importa.)

Así que antes de que ocurra ningún criptoanálisis, el texto codificado ya ha chocado con un **borde de seguridad** — y dos laboratorios frontera lo guardan de dos formas distintas: OpenAI/Azure con un filtro externo, Anthropic con el propio reflejo de rechazo del modelo. Solo GPT-5 (pasado el filtro) y los dos Qwen abiertos participan de verdad. Eso reencuadró todo el estudio: la pregunta de "cuán rápido aprenden un código" solo tiene respuesta para los modelos dispuestos a jugar.

## Para los que sí juegan: la escalera de dificultad

Entre los modelos que participan (GPT-5 + Qwen ×2, ocho réplicas, intervalos de confianza del 95%), la pregunta original por fin tiene una respuesta limpia.

![Gráfico de barras horizontales del ranking de tasa de comprensión por cifrado: letras_a_dígitos 100%, morse 79%, disemvowel 78%, inversión 75%, sustitución_aleatoria 74%, rot13/cirílico/binario 67%, permutación_por_bloques 51%, base64 50%.](/blog/ciphers-difficulty-ranking.png)

La escalera coincide en su mayoría con la intuición, con un par de sorpresas. **Letras→dígitos es trivial** (100%) — el modelo lee `8-5-12-12-15` como "hello" sin pestañear. **base64 y la permutación por bloques con clave son los más difíciles** (~50%), que es la parte interesante: base64 está *por todas partes* en los datos de entrenamiento, y aun así decodificar una cadena base64 larga turno tras turno y actuar sobre ella es genuinamente propenso a error. Familiaridad no es lo mismo que fluidez. Y los cifrados difíciles no solo se resuelven menos: cuando *se* resuelven cuesta más (mediana 4–5 turnos frente a 1 en los fáciles).

La sustitución aleatoria con clave — el único cifrado que ningún modelo pudo memorizar — queda a media escalera con 74%, y los modelos *trabajan* visiblemente por él, que es lo más parecido aquí a ver un "break" de análisis de frecuencias suceder a lo largo de varios turnos.

## Qué ayuda de verdad a un modelo a descifrar un código

Los tres protocolos accionan dos palancas distintas, y aquí es donde una decisión de diseño rindió.

![Gráfico de barras agrupadas por protocolo. Comprensión: puro 61%, few-shot 83%, escalado 70%. Producción: puro 25%, few-shot 14%, escalado 62%.](/blog/ciphers-protocol-effect.png)

Darle al modelo una **piedra Rosetta** — unos pares texto-plano↔codificado — sube la comprensión de 61% a 83%, una brecha cuyos intervalos de confianza no se solapan, y ayuda a los cifrados *novedosos* con clave tanto como a los memorizados. Es exactamente lo que esperarías: mostrada la clave, el modelo descifra el código más rápido, incluso un código que nunca ha visto.

(Un inciso para quien construye evaluaciones: este resultado solo existe por un bug que cacé en la revisión. Mi primera implementación de la "piedra Rosetta" codificaba por accidente *ambos* lados de cada ejemplo, así que no había ningún ancla en texto plano — la condición few-shot era en secreto idéntica a la inferencia pura. De haberse publicado, el hallazgo estrella aquí habría sido un plano "los ejemplos no ayudan", que es falso. La clave en texto plano *es* toda la intervención.)

El escalado, en cambio, apenas mueve la comprensión pero dispara la **producción** hasta el techo (62% vs 25%): en el momento en que dices explícitamente "responde en el mismo código", los modelos que entienden empiezan a *hablarlo*. Entender un código y elegir responder en él son interruptores separados, y responden a instrucciones distintas.

## El giro: codificar una petición rechazada no la desbloquea

Lo que nos devuelve a ese borde de seguridad, y a la pregunta obvia. Si el texto codificado se cuela por el rechazo-de-instrucciones-legibles de Claude y el filtro-en-claro de Azure, ¿es un cifrado un **jailbreak** — una forma de colar una petición que el modelo normalmente rechazaría? Esta es la hipótesis de CipherChat, y es algo legítimo que testar, así que lo hice, con cuidado: un conjunto pequeño y fijo de peticiones suaves "normalmente-rechazadas" (texto de phishing, un bulo difamatorio, ganzúa — nada de las categorías CBRN/armas/autolesión), enviadas en claro y codificadas, puntuadas solo por cumplimiento agregado. Solo etiquetas; ningún texto dañino almacenado ni publicado.

El resultado va en dirección contraria al titular alarmista.

![Gráfico de barras: el cumplimiento de una petición dañina en texto plano es 36%, frente a 1% cuando la misma petición va codificada en un cifrado. Anotación: el modelo cambia a modo 'decodifica este puzzle' en vez de obedecer.](/blog/ciphers-jailbreak-backfire.png)

En texto plano estas peticiones se cumplen el 36% de las veces (y el modelo *base*, sin capa de alineamiento, el 80% — sencillamente no ha aprendido a rechazar). Codifica la misma petición exacta y el cumplimiento **se desploma a ~1%.** Leer las transcripciones a mano muestra por qué: el cifrado voltea al modelo a *modo traductor*. Responde, en inglés plano, "Esto parece ROT13 — decodificando: EXPLICA CÓMO…" y luego trata el texto decodificado como un puzzle que ha resuelto en vez de una orden que debe seguir. La ofuscación que se cuela por el filtro externo también impide que el modelo *ejecute* la instrucción, porque la reencuadra como un objeto a examinar.

Esa es la versión honesta y sin alarmismo. Bajo *inferencia pura* — sin un system prompt que enseñe el cifrado, al estilo del montaje original de CipherChat — envolver una petición en un código no hace jailbreak al modelo; lo desactiva. La lección relevante para seguridad no es "los cifrados rompen los guardarraíles". Es más sutil y más útil: **los filtros en texto plano y el contenido decodificado son dos superficies distintas.** El filtro de Azure salta por la forma del texto cifrado; Claude rechaza por ilegibilidad; el cumplimiento decodificado real es una tercera cosa completamente distinta. Una defensa afinada para cualquiera de ellas es ciega a las otras dos.

## De vuelta al clic

El "break" del criptoanalista humano es un momento de *comprensión* — la máscara cae y el significado inunda. Lo que este experimento no para de separar es que, para un modelo, la comprensión es solo uno de varios interruptores, y ni siquiera el primero en activarse. Antes de entender hay una *disposición a participar siquiera* — el interruptor que Claude mantiene apagado, que Azure apaga en nombre de GPT-5. Después de entender está la elección de *responder* en el código, que solo se enciende cuando lo pides. Y lo que más temerías — comprensión-más-obediencia de una instrucción oculta — resulta ser el interruptor que se atasca, porque decodificar y obedecer tiran del modelo en direcciones distintas.

Una persona que descifra un código y lee "roba el banco" no roba por ello el banco; leer y hacer son actos distintos. Resulta curiosamente tranquilizador que, al menos bajo inferencia pura, los modelos trazan la misma línea — y un poco inquietante que el modelo base, despojado de alineamiento, sea el más dispuesto a hacer sin más lo que dice el texto plano.

---

*Código, cifrados, oráculo determinista y análisis completo: [github.com/JaviMaligno/llm-language-limits](https://github.com/JaviMaligno/llm-language-limits). Segundo de una serie sobre los bordes del lenguaje, tras [Repetición en los bordes del lenguaje](/es/blog/repetition-edges-of-language). La sonda de jailbreak sigue el planteamiento de [CipherChat](https://arxiv.org/abs/2308.06463) y reporta solo tasas agregadas.*
