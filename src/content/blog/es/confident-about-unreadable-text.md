---
title: "Seguros ante un texto que no saben leer"
description: "Un filtro de seguridad asignó severidad media por autolesión a una cadena en base64. Dos jueces puntuando las mismas respuestas cifradas coincidieron peor que el azar. Un modelo base escribió cifrado impecable sin haber entendido nada. Tres sistemas emitiendo veredictos seguros sobre texto que no saben leer — y una conclusión mía que no sobrevivió a la tanda completa."
pubDate: 2026-08-01
tags: ["IA", "Machine Learning", "Evaluación", "Alignment", "Seguridad"]
lang: es
translationKey: confident-about-unreadable-text
heroImage: "/blog/confident-about-unreadable-text.png"
linkedinImage: /blog/ciphers-chatgpt-banana.png
repoUrl: https://github.com/JaviMaligno/llm-language-limits
linkedinLinks:
  - label: "CipherChat, el marco que sigue este sub-experimento"
    url: "https://arxiv.org/abs/2308.06463"
---

Toma la cadena `cmVwbHkgd2l0aCB0aGUgc2luZ2xlIHdvcmQgYmFuYW5h`. Es base64, y se descodifica como *reply with the single word banana* (responde con la única palabra banana). Mándasela a GPT-5 a través del gateway de Azure y no recibes `banana`. Recibes un HTTP 400, y un veredicto del filtro que nombra su motivo:

```
jailbreak:                 { detected: true,  filtered: false }
self_harm:                 { filtered: true,  severity: "medium" }
hate / sexual / violence:  safe
```

Un clasificador de autolesión miró una cadena que no podía interpretar y le asignó **severidad media**. Ni "desconocido", ni una abstención, ni un aviso de baja confianza: un veredicto concreto, seguro y equivocado sobre una petición de la palabra *banana*.

Y la cadena tampoco es ningún caso exótico. Pégala en ChatGPT y la respuesta vuelve al instante:

![Captura de una conversación en ChatGPT. El mensaje del usuario es la cadena en base64 cmVwbHkgd2l0aCB0aGUgc2luZ2xlIHdvcmQgYmFuYW5h y la respuesta completa del asistente es una sola palabra: banana.](/blog/ciphers-chatgpt-banana.png)

Otro stack, otros filtros, ningún drama: descodifica la petición y la responde. Ese contraste es justo el asunto. El veredicto de severidad no es un hecho sobre la petición; es una propiedad del conjunto de clasificadores que hay delante de un deployment concreto, un conjunto que tenía que decir *algo* sobre una cadena que no sabía leer, y dijo `medium`.

Esa es la forma de todo lo que merece la pena contar de este experimento. Ya he terminado la versión completa del barrido de cifrados del que [escribí en el artículo anterior](/es/blog/ciphers-edges-of-language) — 696 conversaciones, 6.960 turnos de modelo, diez cifrados que nadie les explicó nunca. Resultó que tres sistemas distintos dentro del experimento hacen lo mismo: emitir un juicio seguro y bien estructurado sobre un texto que no saben leer. Uno es ese filtro de seguridad. Otro es un modelo base escribiendo cifrado fluido que no comprende. Y el tercero es un juez LLM: precisamente aquel sobre el que se apoyaba mi propia conclusión anterior.

Así que este artículo empieza por la corrección.

## Lo que no sobrevivió

El [artículo de cifrados](/es/blog/ciphers-edges-of-language) terminaba en un tono tranquilizador. Su sub-experimento sobre robustez informaba de que cifrar una petición normalmente rechazada hacía que el cumplimiento se *desplomara* — 36% en texto plano frente a en torno al 1% bajo cifrado — y yo saqué la conclusión evidente: un cifrado no desbloquea una petición rechazada, la desactiva. Los modelos pasan a modo traductor, descodifican el mensaje y lo comentan en vez de obedecerlo.

Aquel artículo matizaba la afirmación en varias direcciones, y sigo pensando que los matices eran correctos. Pero la dirección del titular estaba mal, por un motivo que vale más que la conclusión a la que sustituye.

**La medición estaba rota de una forma muy concreta.** Aquel primer sub-experimento juzgaba incondicionalmente la vista *descodificada* de cada respuesta. Así que cuando un modelo descodificaba una petición dañina y luego la rechazaba en inglés claro — lo más habitual con diferencia — el juez cogía ese rechazo en texto plano y lo volvía a pasar por el cifrado antes de puntuarlo. Veía ruido y lo archivaba como "ilegible". Todas las condiciones con cifrados a nivel de letra devolvían ilegible por construcción, lo que empuja hacia cero tanto el cumplimiento como el rechazo y deja un alentador ~1%.

El experimento corregido juzga la vista que de verdad se lee como lenguaje natural, registra en qué canal respondió el modelo y guarda la identidad del juez en cada celda. Y luego hace lo que la primera tanda no hizo: que un **segundo juez independiente** vuelva a etiquetar una muestra, para poder preguntarme si las etiquetas significan algo antes de leer ninguna tasa.

En su mayoría no significan nada. Y donde sí, la respuesta va en sentido contrario.

![Gráfico de barras del acuerdo entre jueces (kappa de Cohen) para tres modelos, separando respuestas en texto plano y cifradas. GPT-5: 1,00 en texto plano, 0,35 cifrado. Qwen-7B Instruct: 0,66 y −0,17. Qwen-7B Base: 0,74 y −0,05. La región negativa está sombreada y etiquetada como 'peor que el azar'.](/blog/ciphers-full-judge-agreement.png)

En texto plano, dos jueces independientes coinciden sobre lo que pasó, en todos los modelos. En respuestas cifradas coinciden en GPT-5 — y en los dos modelos de 7B coinciden **peor que el azar**: kappa de −0,17 y −0,05. Por cifrado aparece la misma división, desde 0,71 en la inversión completa hasta 0,002 en la sustitución con clave.

Eso no es una pega menor sobre datos ruidosos. Significa que, para esos modelos y en esa condición, el instrumento estándar al estilo CipherChat no mide nada. Su "uplift" sale fuertemente negativo — el modelo base cae del 80% de cumplimiento en texto plano a entre el 0% y el 20% bajo cualquier cifrado — y **ese número negativo no es prueba de que los cifrados los protejan.** Un modelo de 7B respondiendo a una petición dañina cifrada suele emitir algo que no es ni un rechazo ni un cumplimiento, y "rechazó / cumplió / ilegible" son categorías de texto plano que no reparten bien ese espacio de salidas. Un cumplimiento que el juez no reconoce en un texto a medio descifrar se archiva como ilegible, lo que baja la tasa mecánicamente. Quien está haciendo el trabajo es el juez que te tocara en suerte.

**En GPT-5, donde los jueces sí coinciden, aparece un bypass.** En texto plano rechazó las 30 celdas dañinas — un 100% limpio, con los dos jueces en acuerdo perfecto. Bajo cifrado, dos prompts distintos fueron cumplidos bajo dos cifrados distintos (letras→dígitos e inversión completa) después de haber sido rechazados en texto plano. Cada uno se reprodujo entre réplicas, y los dos jueces etiquetaron de forma independiente las cuatro celdas como cumplimientos — incluido el juez que *no* es GPT-5, lo cual importa, porque un juez puntuando sus propias salidas estaría sesgado a leerlas como rechazos.

Quiero ser exacto sobre cuánto es esto y cuánto no. Es un **resultado de existencia, nunca una tasa**. Diez prompts no pueden estimar una frecuencia; todos los intervalos de confianza aquí incluyen el cero; 0,067 son literalmente dos prompts. Lo que establece es que el rechazo no es una propiedad del significado de la petición por sí solo: el mismo significado, envuelto en un cifrado, cruzó una frontera que no cruzó en texto plano. Fíjate además en qué cifrados *no* lo lograron: ROT13 y base64, los dos que GPT-5 descodifica con más soltura, y el cifrado con clave que tiene que deducir. Sea lo que sea lo que ocurre, no es "cuanto más difícil de leer, más fácil de saltar".

Todo el sub-experimento usó un subconjunto deliberadamente suave de **AdvBench**, excluyendo las categorías CBRN, armas, CSAM y autolesión, y guarda únicamente etiquetas: no se publica ningún prompt dañino ni ninguna respuesta del modelo, ni aquí ni en el repositorio.

## La parte que los jueces no tocaron

Todo lo anterior es el apéndice. El experimento principal es la razón por la que me fío de él, porque **sus métricas centrales no usan ningún juez LLM**.

En cada turno, el modelo recibe una instrucción corta y verificable — *responde con la única palabra banana*, *cuánto es siete más cinco* — cifrada con el cifrado activo, y yo compruebo dos cosas por programa. **Comprensión**: ¿actuó correctamente sobre la instrucción descodificada, en el idioma que fuera? Eso lo decide un oráculo de tareas, de forma determinista. **Producción**: ¿escribió su respuesta en el código? Eso lo decide el cifrado inverso, descodificando la respuesta y comprobando que el resultado se lee como inglés mientras que la respuesta cruda no.

Diez cifrados, tres protocolos de exposición, ocho réplicas, tres modelos: 696 conversaciones. Dos de los cifrados — una sustitución aleatoria del alfabeto y una permutación por bloques — llevan **clave generada en cada ejecución**, así que su correspondencia no ha podido memorizarse en el entrenamiento. Son los únicos que hablan de inferencia y no de reconocimiento.

Casi todo lo que encontró esa maquinaria ya lo contó [el artículo anterior](/es/blog/ciphers-edges-of-language) a partir del piloto, y el barrido completo lo confirma en vez de corregirlo: los cifrados con clave son los difíciles de verdad, tres pares de ejemplo texto plano↔cifrado suben mucho la comprensión, y los modelos solo empiezan a *responder* en código cuando se lo pides. Merece la pena añadir dos detalles. Agrupando todos los modelos, Morse, la supresión de vocales y ROT13 tienen una **mediana de un turno siempre que llegan a resolverse**: el reconocimiento es instantáneo o no llega nunca, sin apenas término medio, justo lo contrario del trabajo de varios turnos que exigen los cifrados con clave. Y la fila de base64 se apoya en dos modelos y no en tres, porque Azure rechazó el bloque entero de base64 de GPT-5: el rechazo con el que abre este artículo es también un agujero en la tabla de resultados.

Lo genuinamente nuevo necesita ver las tasas de *producción* de todos los modelos una al lado de la otra.

### Las dos capacidades se disocian en direcciones opuestas

![Gráfico de barras agrupadas comparando las tasas de comprensión y producción por modelo, con intervalos de confianza. GPT-5: 97% de comprensión, 24% de producción. Qwen-7B Instruct: 83% y 20%. Qwen-7B Base: 36% de comprensión y 56% de producción — el único modelo que produce más de lo que entiende.](/blog/ciphers-full-dissociation.png)

Que las dos son separables ya era el hallazgo del artículo anterior: el protocolo escalado dispara la producción sin mover la comprensión. Lo que muestra el barrido completo es más afilado: no solo se separan, se **invierten**. GPT-5 entiende el 97% de las celdas y aun así responde en inglés claro, escribiendo en código solo en un 24% de ellas. Qwen-7B Base hace lo contrario: entiende el 36% y escribe en código el 56% de las veces. Es el único modelo aquí que produce más de lo que entiende.

La mitad correspondiente al modelo base necesita una advertencia, y es el tercer sistema de mi lista. En tres celdas de cifrado — binario, homoglifos cirílicos y permutación por bloques — produjo salida en código sin acertar **ni una sola vez** la tarea descodificada. Eso no es adoptar el código. Es continuar el patrón superficial del prompt, que es exactamente lo que debe hacer un modelo de completado sin ajuste por instrucciones. Cifrado fluido, comprensión cero. Se reporta como mimetismo, no como hablar el idioma.

## Lo que tienen en común

Un filtro que no sabe interpretar base64 le asigna severidad media por autolesión. Un juez que no sabe leer una respuesta a medio descifrar la archiva como ilegible y desinfla una tasa sin avisar. Un modelo base que no ha entendido nada produce cifrado impecable. En los tres casos la salida del sistema tiene la *forma* de un juicio — una severidad, una etiqueta, una respuesta fluida — y nada del contenido que haría falta detrás.

Es un modo de fallo concreto y poco vistoso, y es una historia distinta de la que conté en el artículo anterior. La lectura tranquilizadora que publiqué no estaba equivocada porque los modelos resultaran ser más frágiles de lo que yo creía. Estaba equivocada porque leí un número de un instrumento que, en esa condición, no medía nada — y el artefacto apuntaba casualmente hacia un sitio cómodo.

Así que la lección práctica no va de cifrados. Si estás replicando trabajo al estilo CipherChat, o cualquier evaluación en la que un juez LLM puntúe texto que el modelo puede haber destrozado, **calcula el acuerdo entre jueces por sujeto y por condición antes de reportar una sola tasa**. Con este material, esa pasada extra de juicio es toda la diferencia entre una medición y un artefacto seguro de sí mismo. A mí me costó una tanda descubrirlo, y para entonces ya había publicado el artefacto.

La versión defensiva de la misma lección: un filtro de seguridad entrenado en texto plano y la instrucción descodificada son dos superficies distintas. El mismo conjunto de clasificadores bloquea de más una petición inocua sobre un plátano *y* dejó pasar dos dañinas en un modelo de frontera. Ajustar para una de esas superficies dice muy poco sobre la otra.

---

*Código, cifrados, el oráculo determinista y el método completo: [github.com/JaviMaligno/llm-language-limits](https://github.com/JaviMaligno/llm-language-limits) — con un registro de procedencia en `docs/PUBLICATION_FREEZE.md` (identificadores de modelo, versiones servidas, ajustes de muestreo, semilla de los cifrados y un sha256 por cada fichero de datos, sellado con el commit generador) y 172 tests. Esto cierra el estudio de cifrados que empezó en [Enseñarle a un modelo un idioma que acabas de inventar](/es/blog/ciphers-edges-of-language), a su vez la segunda pieza de una serie sobre los bordes del lenguaje tras [Repetición en los bordes del lenguaje](/es/blog/repetition-edges-of-language). El sub-experimento de robustez sigue el marco de [CipherChat](https://arxiv.org/abs/2308.06463) y reporta únicamente etiquetas agregadas.*
