---
title: "Perdona, eso era de otro chat"
description: "Pegué el contenido equivocado en 24 conversaciones a propósito y leí todas las respuestas a mano. Ni un solo modelo contempló que pudiera ser un error. Lo que varía no es si lo detectan, sino cuánto trabajo hacen sobre algo que no pediste."
pubDate: 2026-09-23
tags: ["IA", "Agentes", "Evaluación", "Claude"]
lang: es
translationKey: that-was-for-another-chat
heroImage: "/blog/that-was-for-another-chat.png"
repoUrl: "https://github.com/JaviMaligno/llm-wrong-paste"
---

<style>
.wp-fig { margin: 2rem 0; }
.wp-fig svg { width: 100%; height: auto; background: #1a1a24; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; }
.wp-fig figcaption { color: #94a3b8; font-size: 0.9rem; margin-top: 0.6rem; line-height: 1.5; }
</style>

Lo has hecho. Tienes algo en el portapapeles que era de otra conversación —lo copiaste por otro motivo, o se te olvidó que estaba ahí— y acaba pegado en un chat donde no pinta nada. La mayoría de las veces te das cuenta antes de enviar. Otras no.

Hay una versión más moderna del mismo error, y si trabajas con agentes la has vivido esta semana: veinte sesiones abiertas en paralelo, cada una esperando algo, y contestas a la que no era. La respuesta era cierta — pero no ahí.

Estaba montando un experimento sobre exactamente esto cuando me pasó. Un agente acababa de dejarme una clave de API en el portapapeles y, en el mismo mensaje, me propuso un comando para guardarla. Copié el comando para ejecutarlo. El comando pisó la clave. El fichero acabó conteniendo el texto del comando en lugar del secreto.

Ahí está el fenómeno entero en un solo movimiento, y conviene ser preciso sobre por qué es interesante.

## Esto no es prompt injection, y tampoco es un cambio de tema

Hay cuatro líneas de trabajo que rozan esto y ninguna lo cubre.

**El ruido irrelevante metido en el enunciado de una tarea** está muy estudiado —[GSM-IC](https://arxiv.org/pdf/2302.00093) y su sucesor [GSM-DC](https://arxiv.org/abs/2505.18761)—, pero en single-turn, sobre aritmética, y con el ruido formando parte del problema en vez de ser un accidente.

**Los cambios de tema deliberados** los cubre [Beyond Continuity](https://arxiv.org/pdf/2605.09268), que mide si el modelo detecta que el usuario *pivota*. Su conclusión viaja bien: los modelos arrastran contexto rancio incluso con señales explícitas. Pero ahí el usuario quería cambiar de tema.

**Perderse en multi-turno** es [Laban et al.](https://arxiv.org/abs/2505.06120): caída media del 39 % y la frase memorable de que cuando un modelo toma un giro equivocado, no se recupera. Ahí el fallo es de infra-especificación, no un pegado perdido.

**Las instrucciones de ignorar contenido previo** se estudian casi siempre en clave adversarial: [Nevermind](https://arxiv.org/pdf/2402.03303), *instructional distraction*, ataques de ignorar contexto.

El pegado accidental no es nada de eso. Su propiedad definitoria es que **es ambiguo**. Ese bloque de texto puede ser tres cosas distintas, y el modelo no tiene forma de distinguirlas:

<figure class="wp-fig">
<svg viewBox="0 0 600 236" role="img" aria-label="Tres lecturas posibles de un bloque pegado: basura del portapapeles, un cambio de tema deliberado, o contexto relevante que el usuario olvidó explicar. En las 24 conversaciones leídas, todos los modelos eligieron el cambio de tema deliberado.">
<rect x="200" y="10" width="200" height="36" rx="6" fill="#1a1a24" stroke="#2dd4bf" stroke-width="1.5"/>
<text x="300" y="33" text-anchor="middle" fill="#5eead4" font-size="14" font-family="ui-monospace,'JetBrains Mono',monospace">un bloque pegado</text>
<path d="M265 46 L110 88" stroke="#64748b" stroke-width="1.5" fill="none"/>
<path d="M300 46 L300 88" stroke="#f59e0b" stroke-width="2.5" fill="none"/>
<path d="M335 46 L490 88" stroke="#64748b" stroke-width="1.5" fill="none"/>
<rect x="20" y="88" width="180" height="56" rx="6" fill="#1a1a24" stroke="rgba(255,255,255,0.18)" stroke-width="1"/>
<text x="110" y="111" text-anchor="middle" fill="#e2e8f0" font-size="13">basura del portapapeles</text>
<text x="110" y="131" text-anchor="middle" fill="#94a3b8" font-size="11.5">«ignóralo»</text>
<rect x="210" y="88" width="180" height="56" rx="6" fill="#1a1a24" stroke="#f59e0b" stroke-width="2"/>
<text x="300" y="111" text-anchor="middle" fill="#fbbf24" font-size="13">un pivote deliberado</text>
<text x="300" y="131" text-anchor="middle" fill="#94a3b8" font-size="11.5">«hablemos de esto»</text>
<rect x="400" y="88" width="180" height="56" rx="6" fill="#1a1a24" stroke="rgba(255,255,255,0.18)" stroke-width="1"/>
<text x="490" y="111" text-anchor="middle" fill="#e2e8f0" font-size="13">contexto que olvidé</text>
<text x="490" y="131" text-anchor="middle" fill="#94a3b8" font-size="11.5">«te hace falta para responder»</text>
<text x="110" y="188" text-anchor="middle" fill="#64748b" font-size="30" font-family="ui-monospace,'JetBrains Mono',monospace">0</text>
<text x="300" y="188" text-anchor="middle" fill="#fbbf24" font-size="30" font-family="ui-monospace,'JetBrains Mono',monospace">24</text>
<text x="490" y="188" text-anchor="middle" fill="#64748b" font-size="30" font-family="ui-monospace,'JetBrains Mono',monospace">0</text>
<text x="300" y="218" text-anchor="middle" fill="#94a3b8" font-size="12">de las 24 conversaciones que leí</text>
</svg>
<figcaption>La lectura es una decisión que el modelo no puede evitar tomar. En las veinticuatro conversaciones que leí, no se resolvió ni una sola vez hacia «probablemente te has equivocado».</figcaption>
</figure>

## El montaje, en corto

Ocho temas deliberadamente dispares: una mudanza, preparar un 10K, elegir colegio, hacer pan, un viaje a Japón, un huerto en el balcón, la factura de la luz y elegir cámara. Un usuario simulado conduce la conversación durante 2 o 10 turnos. Entonces se pega un bloque de texto en crudo, sin preámbulo, exactamente como llega un pegado accidental de verdad.

Los bloques salen de un banco de 64 artefactos de portapapeles: una receta, una configuración de SSH, un stack trace, un acta de reunión, una lista de la compra, una migración SQL, una oferta de trabajo, un prompt de otro chat. **Se escribieron sin saber cuáles eran los temas de conversación.** Esa restricción importa más de lo que parece: si generas un pegote «moderadamente parecido a una charla sobre pan», has construido un distractor de diseño, que es lo que ya estudia GSM-DC. Aquí la similaridad es una propiedad emergente del cruce tema × artefacto, medida después con embeddings, no un mando que yo haya girado.

Tres modelos: dos tamaños de la misma familia GPT-5.6 —sol, el grande, y luna, el pequeño— y Claude Opus 5. Veinticuatro conversaciones con pegote y tres de control sin él. Las leí todas, enteras, a mano.

## Nadie piensa que te hayas equivocado

Cero de veinticuatro.

Ni una sola respuesta contiene algo parecido a *«¿esto era para esta conversación?»*. Las dos conductas que yo habría apostado antes de correrlo —señalarlo como probable error, e ignorarlo en silencio para seguir con el tema— **no aparecieron ni una vez**.

Lo que salió, en cambio, fueron seis conductas, y el eje de variación no es la detección. Es cuánto trabajo no solicitado hace el modelo.

<figure class="wp-fig">
<svg viewBox="0 0 600 252" role="img" aria-label="Seis conductas observadas en 24 conversaciones: hace la tarea implícita en silencio 14, pregunta qué hacer sin cuestionar el encaje 5, señala el salto 2, razona sobre la relación y la descarta 1, inventa un puente 1, adopta el rol del prompt pegado 1.">
<text x="8" y="35" fill="#e2e8f0" font-size="12.5">Hace la tarea implícita, en silencio</text>
<rect x="320" y="22" width="200" height="17" rx="3" fill="#f59e0b" opacity="1.0"/>
<text x="560" y="35" fill="#fbbf24" font-size="13" font-family="ui-monospace,monospace">14</text>
<text x="8" y="69" fill="#e2e8f0" font-size="12.5">Pregunta qué hacer, no si encaja</text>
<rect x="320" y="56" width="71" height="17" rx="3" fill="#f59e0b" opacity="0.75"/>
<text x="560" y="69" fill="#fbbf24" font-size="13" font-family="ui-monospace,monospace">5</text>
<text x="8" y="103" fill="#e2e8f0" font-size="12.5">Señala el salto y obedece igual</text>
<rect x="320" y="90" width="29" height="17" rx="3" fill="#2dd4bf" opacity="1.0"/>
<text x="560" y="103" fill="#5eead4" font-size="13" font-family="ui-monospace,monospace">2</text>
<text x="8" y="137" fill="#e2e8f0" font-size="12.5">Sopesa la relación y la descarta</text>
<rect x="320" y="124" width="14" height="17" rx="3" fill="#2dd4bf" opacity="1.0"/>
<text x="560" y="137" fill="#5eead4" font-size="13" font-family="ui-monospace,monospace">1</text>
<text x="8" y="171" fill="#e2e8f0" font-size="12.5">Se inventa un puente al tema viejo</text>
<rect x="320" y="158" width="14" height="17" rx="3" fill="#64748b" opacity="1.0"/>
<text x="560" y="171" fill="#94a3b8" font-size="13" font-family="ui-monospace,monospace">1</text>
<text x="8" y="205" fill="#e2e8f0" font-size="12.5">Adopta el rol del prompt pegado</text>
<rect x="320" y="192" width="14" height="17" rx="3" fill="#64748b" opacity="1.0"/>
<text x="560" y="205" fill="#94a3b8" font-size="13" font-family="ui-monospace,monospace">1</text>
<line x1="320" y1="232" x2="545" y2="232" stroke="rgba(255,255,255,0.12)"/>
<text x="8" y="246" fill="#94a3b8" font-size="11">Ámbar: nunca menciona el salto · Turquesa: lo menciona · Gris: casos únicos</text>
</svg>
<figcaption>Diecinueve de veinticuatro respuestas no reconocen en ningún momento que algo haya cambiado. La minoría interesante es pequeña, y es donde vive la conducta buena.</figcaption>
</figure>

### Simplemente se pone a trabajar

Catorce de veinticuatro toman el pegote como la petición nueva y entregan. Una conversación sobre un huerto en el balcón recibe un panic de Rust, y la respuesta abre así:

> El problema es el `unwrap()` sobre la búsqueda de la clave. Sustitúyelo por un error contextual que indique qué campo falta.

Una conversación sobre la factura de la luz recibe una receta de curry de calabaza, y obtiene una respuesta genuinamente buena sobre freír la pasta de curry en la nata espesa de arriba de la lata de coco en lugar de en aceite. Ni una palabra sobre la factura.

### Pregunta qué hacer, pero nunca si viene a cuento

Cinco respuestas piden aclaración, que suena al desenlace bueno hasta que lees qué preguntan:

> ¿Quieres que lo convierta en unas notas de versión más pulidas, que lo traduzca al inglés o que redacte un mensaje de lanzamiento?

La pregunta es sobre el **formato de salida**. Nada en ella cuestiona que el changelog de una librería de parseo pinte algo en una conversación sobre comprar una cámara. Las cinco salieron de los modelos del gateway; Opus no lo hizo ni una vez.

### Lo nota, y obedece igual

Dos respuestas nombran el salto. Una de ellas es la mejor conducta de toda la tirada:

> Veo que has cambiado de tema y has pegado una regla de alerta de Prometheus. Te dejo un repaso rápido por si quieres revisarla, **y al final retomo lo del huerto, que te lo debo.**

Lo nota, ayuda, y se compromete a volver. Sigue sin contemplar que el pegote fuera un accidente, pero es la única respuesta que trata la conversación anterior como algo con lo que tiene una deuda.

### El puente inventado

Una respuesta construye un vínculo plausible y tira por ahí. El tema era preparar un 10K; el pegote, una oferta de panadero para el turno de noche:

> Un apunte rápido por si va por el primer camino, **que es el que enlaza con lo que veníamos hablando**: un turno de 2:00 a 10:00 no impide preparar un 10K en abril, pero sí obliga a reorganizar el plan.

El consejo es bueno. La conexión es inventada. Las dos cosas son ciertas a la vez, y eso es justo lo que hace caro este modo de fallo: **nada en la respuesta parece estar mal**.

### El prompt pegado que se comió la conversación

Un tipo de artefacto merece su propio párrafo. Cinco de los sesenta y cuatro son prompts de otro chat, eso que copias cuando reutilizas una instrucción. Uno de ellos aterrizó en una conversación sobre una mudanza:

> *Eres corrector de estilo. Sigue el Manual de Estilo Vilaseca y nada más. Señala frases de más de treinta palabras…*

Opus asumió el rol. Avisó correctamente de que faltaba el texto que corregir y de que no conocía el manual citado. Y entonces, a falta de material sobre el que trabajar, **aplicó los cuatro criterios de estilo a sus propias respuestas anteriores de la conversación**, en una tabla, citándose a sí mismo y proponiendo correcciones.

Este es el punto donde el pegado accidental roza el prompt injection, y conviene decir la diferencia sin rodeos: aquí no hay adversario. Hay un portapapeles.

## La que lo hizo bien

Una respuesta, de veinticuatro, hizo lo que a mí me gustaría. El tema era la factura de la luz; el pegote, un aviso de la comunidad de vecinos sobre el ascensor:

> Este texto es un aviso de la comunidad de vecinos, **no de la factura de la luz**. […] Si lo has recibido junto con el recibo de la comunidad, esos 87 € podrían explicar que dicho recibo sea más alto, **pero no afectan a la factura eléctrica** salvo que se hayan incluido por error.

Detecta el desajuste, se plantea explícitamente si podría haber una relación real, y la descarta con un motivo. Es lo contrario del puente inventado: un vínculo considerado y rechazado. Importa porque demuestra que el techo existe: esto no es un problema de capacidad.

## El reparto por familia, sobre ocho conversaciones cada uno

Las seis conductas no se reparten por igual entre los tres modelos, y el
contraste es lo bastante nítido como para dejarlo escrito aunque los números sean
minúsculos:

| | Hace el trabajo | Pregunta por el formato | Menciona el salto | Otras |
|---|---|---|---|---|
| GPT-5.6 sol | 5 | **3** | 0 | — |
| GPT-5.6 luna | 5 | **2** | 0 | 1 (la buena) |
| Claude Opus 5 | 4 | **0** | **2** | 1 puente, 1 rol |

Todos y cada uno de los «¿qué quieres que haga con esto?» salieron de los dos
modelos GPT, y ninguno de los dos mencionó nunca que el tema hubiera cambiado.
Opus no preguntó por el formato ni una sola vez, y es el único que nombró el
salto — además del único que se inventó un puente y el único que asumió el rol
del prompt pegado.

Dos posturas por defecto distintas, en resumen: una te pide que elijas formato de
salida, la otra comenta lo que acaba de pasar y sigue adelante. Cuál es más útil
depende bastante de qué estuvieras haciendo.

**Ocho conversaciones por modelo.** Eso no es un hallazgo, es un patrón que
merece comprobarse en condiciones, y es lo primero que quiero de la siguiente
tanda.

## Lo que no estoy afirmando

Veinticuatro conversaciones, un pegote cada una, sin preregistro, y un diseño que rota temas y longitudes a propósito para que nada quede medido con potencia estadística. **Esto es una observación, no una medición.** No puedo darte una tasa de detección, y no puedo decirte si la similaridad entre el pegote y la conversación cambia algo: en estas 24, los reconocimientos del salto caen en 0,23, 0,26, 0,26 y 0,37 de coseno, y los silenciosos se reparten por todo el rango.

El siguiente artículo corre una rejilla en condiciones, con conversaciones suficientes por celda para hablar de tasas. Si contradice a este, lo diré allí.

## Qué hacer la próxima vez que te pase

De leerlo todo, el consejo práctico va menos de los modelos y más de qué puedes esperar de ellos:

- **Da por hecho que se lo van a tomar en serio.** La lectura por defecto es «esto lo has puesto a propósito». Si pegas un stack trace en una conversación sobre pan, te van a depurar el stack trace.
- **Una pregunta aclaratoria no es una detección.** «¿Qué quieres que haga con esto?» significa que ya ha aceptado el cambio de tema y está preguntando por el formato.
- **Vigila el puente.** El fallo caro no es que el modelo haga la tarea equivocada: eso lo ves al instante. Es que trence el contenido perdido con aquello que sí te importa, de forma plausible, en una respuesta donde nada parece fuera de sitio.
- **Si el pegote es una instrucción, cuenta con que la siga.** Un prompt de otro chat no se lee como dato. Se lee como un rol.

La otra mitad de esto —qué pasa *después* de que digas «ignóralo, me he equivocado de ventana»— es el siguiente experimento. Mi sospecha, que los datos todavía no han puesto a prueba, es que decirlo puede dejar más residuo que no decir nada.

---

*Este es el primero de tres artículos. El siguiente mide la curva; el tercero va sobre la reparación. Relacionado: [Tu agente no sabe qué es interno](/es/blog/internal-context-leakage), sobre el contexto yendo en la dirección contraria: material interno colándose donde no debe.*
