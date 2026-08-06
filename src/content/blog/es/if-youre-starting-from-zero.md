---
title: "Si empiezas desde cero"
description: "Describiste lo que querías, un agente lo construyó y funciona. Esto es lo que aprender primero — no la lista entera, el orden. Escrito para quien nunca ha programado y no tiene intención de empezar."
pubDate: 2026-08-10
tags: ["IA", "Vibe Coding", "Software", "Mentoría", "Principiantes"]
lang: es
translationKey: if-youre-starting-from-zero
heroImage: "/blog/if-youre-starting-from-zero-es.png"
---

Hay un momento, la primera vez que esto funciona, que es sinceramente de las mejores sensaciones disponibles en una vida profesional. Describiste algo que no existía y unos minutos después existía, en tu pantalla, haciendo lo que dijiste. Si nunca aprendiste a programar, ese momento pega más fuerte todavía: acabas de hacer una cosa que tenías archivada como *no es para mí*.

No quiero estropearlo. Es tan real como se siente, y quien te diga que no lo es suele estar protegiendo algo.

Pero entre ese momento y tener algo que otras personas puedan usar hay una distancia, y casi nada de lo que hiciste para llegar hasta aquí te ayuda a cruzarla. [Escribí el mapa completo de esa distancia](/es/blog/what-you-still-need-to-know-to-ship) — trece categorías, tres niveles cada una. Este artículo es la otra mitad de la pregunta, la que me hace la gente de verdad: **no qué hay en la lista, sino qué hacer primero.**

## Lo más útil que puedes entender el primer día

No estás teniendo una conversación. Estás ejecutando un bucle.

Especificar → construir → comprobar → corregir, y otra vez. Quien viene de un trabajo técnico lo tiene en los huesos y deja de notarlo. Si no vienes de ahí, es información genuinamente nueva, y su ausencia es la mayor diferencia que he visto entre quien acaba con algo real y quien acaba con un historial de chat muy largo.

Lo que pasa por defecto cuando falta no es dramático. Pides, recibes algo, lo miras dos segundos, pides lo siguiente. Nada comprueba nada nunca. Parece progreso todo el rato, justo hasta que intentas enseñárselo a alguien y descubres qué partes nunca fueron ciertas.

El arreglo es poco lucido y cuesta unos diez segundos por vuelta: después de cada cosa que pidas, **úsala antes de pedir la siguiente.** No la leas: úsala. Esa es toda la disciplina, y vale más que cualquier dato técnico de este artículo.

## La terminal, y por qué es menos muro de lo que era

Casi todos los que he visto empezar desde cero chocan con la misma pared en la primera hora, y no es un concepto. Es una ventana negra con texto dentro.

Conviene ser explícito sobre por qué te la encuentras siquiera: **la terminal es la puerta de entrada.** Los agentes serios — Claude Code, Codex — son programas que arrancas desde ahí. Abres la ventana, escribes su nombre, y a partir de ese momento hablas con el agente en lenguaje normal. La ventana no es el trabajo. Es la puerta al trabajo.

El miedo es racional. Una terminal no se explica, no confirma nada, y históricamente ha castigado las erratas de formas que ninguna otra cosa en tu ordenador hace. Todo el demás software que has usado se pasó veinte años aprendiendo a perdonar. Este no.

Lo que ha cambiado es esto: **pasada esa puerta, no eres tú quien tiene que saberse los comandos.** Los ejecuta el agente. Lo que te queda es mucho más pequeño — de vez en cuando te pasa una línea y te pide que la ejecutes tú, normalmente porque necesita un permiso que no tiene. Tu trabajo es pegarla y darle a enter sin bloquearte.

Ese es el nivel exigido. No memorizar nada: no quedarte paralizado cuando aparece un comando.

**Y puedes saltarte la puerta entera.** Tanto Claude Code como Codex tienen apps de escritorio que parecen una aplicación, y también versiones de navegador. Empezar ahí es una decisión perfectamente razonable y se la sugeriría a cualquiera que ya haya rebotado contra la terminal antes.

Una diferencia que no es obvia y causa confusión de verdad: **las versiones de navegador no corren en tu ordenador.** Corren en el de otro, lo que significa que no ven tus ficheros, no tienen tus claves y no tienen lo que hayas instalado. La app de escritorio y la terminal trabajan sobre tu máquina de verdad; la de navegador trabaja sobre una copia de tu proyecto, en otro sitio. Al principio esto casi nunca importa. En el momento en que tu proyecto dependa de algo que vive en tu portátil, importa mucho — y "funcionaba en mi máquina pero no en la versión de navegador" no es que el agente sea inconsistente: son dos entornos con dos configuraciones distintas.

Cursor también merece una mención. Empezó como editor de código, que suena a la opción menos amable de esta lista, pero sus versiones recientes son más chat que editor y acaba siendo una de las entradas más suaves — sobre todo si ver los ficheros al lado de la conversación te hace sentir más orientado y no menos.

También está Claude Cowork, que merece conocerse precisamente porque se hizo para gente que no programa: le señalas una carpeta, describes lo que quieres, y va haciendo los pasos en tu propia máquina. Su terreno es el trabajo de oficina más que construir una app: ordenar ficheros, sacar números de un montón de documentos, producir un informe. Si lo que quieres es un producto funcionando, la herramienta es Claude Code o Codex. Pero Cowork es la demostración más clara de que "agente" y "terminal" nunca fueron lo mismo, y es una forma suave de cogerle el tacto a dirigir uno.

Si empiezas por algo que no sea la terminal, dos razones para mantenerlo como punto de partida y no como casa permanente. La terminal es donde vive el conjunto completo de capacidades — las apps van por detrás en lo nuevo, así que antes o después querrás algo que la tuya no tiene. Y cuando algo va mal, te enseña el intercambio entero entre el agente y tu máquina, que es justo lo que quieres cuando intentas averiguar qué ha pasado.

Así que: empieza por donde vayas a empezar de verdad. Solo ten claro que estás eligiendo la puerta más amable, no otro edificio.

Un hábito más que conviene coger pronto: **lee por encima lo que imprime.** No para entenderlo — para notar si acabó en algo que parece una queja. "¿Esto ha ido bien o mal?" es una pregunta que puedes responder por la forma de la salida mucho antes de poder leer una palabra.

## Vas a pedir menos de lo que podrías, y no te vas a enterar

El techo de todo lo que construyas no es tu habilidad. Es tu idea de lo que es pedible.

Si crees que estas herramientas escriben fragmentos, pedirás fragmentos. Si crees que no pueden tocar pagos, ni correo, ni una base de datos, no lo pedirás, y nada te va a corregir, porque un agente responde a lo que le preguntas y nunca menciona lo que no. Este es el fallo más silencioso de todo el asunto: no hay mensaje de error para una pregunta que nunca hiciste.

Hay un movimiento que lo arregla y no cuesta nada. **Pregúntale al agente qué puede hacer en tu caso concreto.** No en general: describe tu proyecto real y pregunta qué enfoques existen, qué necesitaría, qué no puede hacer y en qué te estarías metiendo. Responde bien a esto, y casi nadie se lo pregunta.

Hazlo antes de empezar a construir, y otra vez cada vez que te pilles dando por hecho que algo no se puede.

## Qué aprender primero, y por qué en este orden

El mapa tiene trece categorías. No necesitas trece el primer día, y que alguien te las suelte todas de golpe es la razón por la que la mayoría rebota. El orden importa más que la lista, y sale de una sola pregunta: **cuando esto salga mal, ¿quién paga?**

**Primero, lo que no tiene vuelta atrás.** Tus datos no son tu código. Si borras el proyecto y lo reconstruyes, el código vuelve; todo lo que la gente escribió dentro, no. Y hay una forma de recuperar la versión de ayer de tu trabajo que no es Ctrl+Z.

Lo que lleva a la que más veces veo saltarse: **las copias de seguridad**. No porque la idea sea ajena — ya guardas copias de los documentos que te importan, y has sentido el pánico concreto de un fichero que no habías copiado. Simplemente no lo has aplicado aquí, porque una base de datos no parece una carpeta y nadie te lo ha preguntado nunca. Así que hazte la versión llana de la pregunta: *si esta base de datos desapareciera esta noche, ¿dónde está la copia y de cuándo es?* Si la respuesta es encogerse de hombros, ahí tienes el trabajo de la tarde, y vale más que todo lo demás de esta lista junto.

Ese grupo es la diferencia entre un mal día y un mes perdido.

**Segundo, lo que hace daño a otras personas.** En el momento en que tienes usuarios reales, el coste de equivocarte deja de ser tuyo. Las claves no van en el código. Una pantalla de login protege la pantalla, no los datos que hay detrás. Si guardas cualquier cosa sobre otras personas, has asumido obligaciones que no firmaste. Este es el grupo que nunca dejaría saltarse, porque es donde quien paga nunca aceptó tu curva de aprendizaje.

**Tercero, lo que te sorprende.** Tu factura no tiene techo salvo que se lo pongas. Tu app funciona contigo y puede no funcionar con trescientas personas. Algo de lo que dependes puede desaparecer.

**Por último, lo que lo hace agradable.** Tests, documentación, tu propio gusto en cómo se ve. Reales, y ninguno es el motivo por el que el proyecto de alguien acaba mal en el primer mes.

Cuatro grupos. Dos tardes para los dos primeros. Eso es una propuesta completamente distinta de "aprende a programar", y es la versión honesta de lo que esto exige.

## El error del que va todo este artículo

Todo el que empieza desde cero comete el mismo, y no es el que teme.

El miedo es a romper algo por ignorancia. El error de verdad es **entregar decisiones que no tienes forma de comprobar** — y, peor, no saber que eran decisiones. El agente eligió cómo guardar tus datos. Eligió qué es público y qué no. Eligió qué pasa cuando algo falla. Cada una de esas cosas, desde tu lado, pareció que no pasaba nada.

Eso es lo que lo hace difícil de notar: delegar bien y delegar a ciegas son idénticos desde fuera. Las dos cosas son tú describiendo lo que quieres y recibiendo algo que funciona. La diferencia solo aparece después, y solo si tienes mala suerte.

No se arregla delegando menos — irías más lento y no más seguro, porque no puedes comprobar aquello de lo que no sabes nada. Se arregla sabiendo qué casillas existen, para poder ver cuáles están vacías. **Una casilla vacía que conoces es un riesgo gestionado. Una casilla vacía cuya existencia ignoras es lo que acaba en las noticias.**

Esa es toda la razón de ser del mapa, y por qué lo primero que aprender no es una habilidad.

## Si vienes de WordPress, no-code o automatizaciones

Entonces no empiezas desde cero, por mucho que te lo hayas estado diciendo.

Ya sabes que un sitio puede estar publicado o no. Te has topado con un plugin que lo rompió todo y has tenido que volver atrás. Has tenido una suscripción que se te olvidó. Sabes que algunas cosas viven en la herramienta y otras en tu cuenta. Son las mismas categorías, aprendidas con otra forma.

Lo que suele faltar es más estrecho: el bucle como disciplina, y el hecho de que esta vez no hay nadie protegiéndote. Aquellas plataformas tenían muros — no podías borrar la base de datos porque no llegabas a la base de datos. Ahora llegas a todo, que es exactamente por lo que es más potente y exactamente por lo que el mapa importa.

En mi experiencia este perfil es el que más rápido se adapta. No porque sepa más, sino porque ya se cree que el software es algo que uno puede ir a cambiar, y esa creencia es la mayor parte de la batalla.

## Por dónde empezar hoy

Si quieres saber qué casillas tienes vacías, hay una [versión de trece preguntas](/es/assessment) del mapa — unos dos minutos, y el resultado útil es encontrar una categoría que nunca te habías planteado.

Y el resumen honesto de todo lo anterior:

1. **Usa la cosa después de cada cambio.** No la leas, úsala. Este único hábito vale más que cualquier dato de aquí.
2. **Pregunta qué es posible antes de dar por hecho que no lo es.** El techo es tu idea de lo que es pedible, y el agente te lo sube encantado si se lo pides.
3. **Dedica una tarde a lo que no tiene vuelta atrás — copias de seguridad incluidas — y otra a lo que hace daño a otras personas.** El resto, sáltatelo por ahora.
4. **Da por hecho que has entregado decisiones sin darte cuenta.** Lo has hecho. La pregunta es solo cuáles.

Nada de esto es aprender a programar. Es aprender qué vigilar mientras otra cosa programa — que es un trabajo más pequeño, y que no enseña nadie porque cae entre dos sillas: demasiado obvio para ingenieros, invisible para el resto.

---

*Segundo de tres artículos sobre lo que construir software con agentes exige de verdad. El primero es [el mapa en sí](/es/blog/what-you-still-need-to-know-to-ship); el último va en dirección contraria, para quien viene de la ingeniería y delega demasiado poco en vez de demasiado. Si prefieres recorrer tu propio proyecto con alguien, [eso es lo que hago](/es/mentoring).*
