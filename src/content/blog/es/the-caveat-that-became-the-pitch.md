---
title: "La advertencia que acabó siendo el argumento de venta"
description: "Una advertencia sobre un conjunto de evaluación malo acabó como titular de las demos, folletos y decks que un agente escribía sobre el producto. Nadie lo decidió: cada pieza se hizo a partir de la anterior y el énfasis creció en cada copia."
pubDate: 2026-11-20
tags: ["IA", "Agentes", "Claude Code", "Memoria"]
lang: es
translationKey: the-caveat-that-became-the-pitch
heroImage: "/blog/the-caveat-that-became-the-pitch.png"
---

<style>
.cap-fig { margin: 2rem 0; padding: 1rem; background: #1a1a24; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; }
.cap-fig svg { width: 100%; height: auto; display: block; }
.cap-fig figcaption { margin-top: 0.75rem; font-size: 0.9rem; color: #94a3b8; line-height: 1.5; }
</style>

Hace unas semanas estaba revisando un deck sobre [un servicio de clasificación por sector en el que trabajo](/es/projects/compliance-classifier), para presentárselo al CEO de la empresa. En la diapositiva tres, la de por qué el problema es difícil, había una tarjeta que decía: *506 clases. La correcta rara vez está en el nombre de la empresa.*

La quité, y entonces me di cuenta de que ya había quitado esa misma idea antes: de vídeos promocionales, de borradores, de una guía de demo. Cada vez que un agente escribía algo sobre este producto para que lo leyeran personas, tarde o temprano decía, de una forma u otra, que el servicio no clasifica a las empresas por su nombre.

Es como vender un coche porque tiene ruedas. Nadie que evalúe un clasificador da por hecho que lee el rótulo de la puerta y se queda ahí, así que nadie lo ve como un riesgo del que el producto le proteja. Como argumento de venta no dice nada. Quería saber cómo había llegado ahí y si podía pararlo.

## De dónde salió la frase

Un par de meses antes, un cliente nos había mandado un conjunto de evaluación de unas 500 empresas, junto con un informe que puntuaba el servicio en un 54 %. [Escribí sobre ese conjunto en su momento](/es/blog/the-grader-knew-less): sus etiquetas se habían sacado del nombre de las empresas, un predictor que solo miraba el nombre coincidía con ellas más que el clasificador, y encontrar la web real de la empresa hacía que la nota *bajara*.

Ese hallazgo era correcto y era útil para evaluar. Quería decir: no puntúes contra ese conjunto y, si hay personas que van a construir un conjunto de referencia a mano, diles que no adivinen por el nombre, porque eso es justo lo que salió mal la última vez. No dice nada que le importe a un comprador. Es una advertencia sobre un instrumento de medida, no una propiedad del producto.

## La cadena

El agente con el que trabajo guarda las transcripciones completas de sus sesiones, así que pude comprobar cómo viajó la frase en lugar de suponerlo. Los registros que conservo empiezan a mediados de septiembre; lo anterior ya no está, así que las dos primeras piezas de abajo son documentos que puedo fechar, pero cuyo origen no puedo rastrear.

<figure class="cap-fig">
<svg viewBox="0 0 600 470" role="img" aria-label="Un hallazgo de evaluación alimentó dos ramas. En la de revisores la regla se quedó con su público. En la de producto, una sola frase del presentador en un runbook de demo se convirtió en el mensaje central de una guía de demo, con una lectura verificada 82 minutos antes de la escritura, y después apareció en un deck para el CEO sin fuente encontrada.">
<defs>
<marker id="cap-arr-es" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#64748b"/></marker>
</defs>
<g font-family="ui-sans-serif,system-ui,sans-serif">
<text x="150" y="16" text-anchor="middle" font-size="11" fill="#5eead4" font-weight="600">REGLA PARA REVISORES</text>
<text x="450" y="16" text-anchor="middle" font-size="11" fill="#fbbf24" font-weight="600">MENSAJE DE PRODUCTO</text>
<rect x="170" y="30" width="260" height="56" rx="6" fill="#232332" stroke="#94a3b8"/>
<text x="300" y="52" text-anchor="middle" font-size="12" fill="#f8fafc" font-weight="600">Día 0 · evaluación de un cliente</text>
<text x="300" y="72" text-anchor="middle" font-size="11" fill="#e2e8f0">etiquetas sacadas del nombre</text>
<rect x="20" y="130" width="260" height="74" rx="6" fill="#232332" stroke="#2dd4bf"/>
<text x="150" y="152" text-anchor="middle" font-size="12" fill="#f8fafc" font-weight="600">+11 d · manual para revisores</text>
<text x="150" y="173" text-anchor="middle" font-size="11" fill="#5eead4">«Nunca decidas a qué se dedica</text>
<text x="150" y="190" text-anchor="middle" font-size="11" fill="#5eead4">una empresa por su nombre»</text>
<rect x="320" y="130" width="260" height="74" rx="6" fill="#232332" stroke="#f59e0b"/>
<text x="450" y="152" text-anchor="middle" font-size="12" fill="#f8fafc" font-weight="600">+18 d · runbook de demo (prospect)</text>
<text x="450" y="173" text-anchor="middle" font-size="11" fill="#fbbf24">una frase del presentador, un caso:</text>
<text x="450" y="190" text-anchor="middle" font-size="11" fill="#fbbf24">«No lo adivinó por el nombre»</text>
<rect x="20" y="270" width="260" height="74" rx="6" fill="#232332" stroke="#2dd4bf"/>
<text x="150" y="292" text-anchor="middle" font-size="12" fill="#f8fafc" font-weight="600">+41 d · guía de revisores, benchmark</text>
<text x="150" y="313" text-anchor="middle" font-size="11" fill="#5eead4">«La única regla: nunca clasifiques</text>
<text x="150" y="330" text-anchor="middle" font-size="11" fill="#5eead4">por el nombre»</text>
<rect x="320" y="270" width="260" height="74" rx="6" fill="#232332" stroke="#f59e0b"/>
<text x="450" y="292" text-anchor="middle" font-size="12" fill="#f8fafc" font-weight="600">+57 d · guía de demo interna</text>
<text x="450" y="313" text-anchor="middle" font-size="11" fill="#fbbf24">«La idea que hay que dejar clara:</text>
<text x="450" y="330" text-anchor="middle" font-size="11" fill="#fbbf24">no clasifica por el nombre»</text>
<rect x="320" y="390" width="260" height="66" rx="6" fill="#232332" stroke="#f59e0b"/>
<text x="450" y="413" text-anchor="middle" font-size="12" fill="#f8fafc" font-weight="600">+67 d · deck para el CEO</text>
<text x="450" y="434" text-anchor="middle" font-size="11" fill="#fbbf24">«Rara vez está en el nombre»</text>
<path d="M235,86 L170,128" stroke="#64748b" stroke-width="1.5" stroke-dasharray="5 4" fill="none" marker-end="url(#cap-arr-es)"/>
<path d="M365,86 L430,128" stroke="#64748b" stroke-width="1.5" stroke-dasharray="5 4" fill="none" marker-end="url(#cap-arr-es)"/>
<path d="M150,204 L150,268" stroke="#64748b" stroke-width="2" fill="none" marker-end="url(#cap-arr-es)"/>
<path d="M450,204 L450,268" stroke="#64748b" stroke-width="2" fill="none" marker-end="url(#cap-arr-es)"/>
<path d="M450,344 L450,388" stroke="#64748b" stroke-width="1.5" stroke-dasharray="2 4" fill="none" marker-end="url(#cap-arr-es)"/>
<rect x="156" y="218" width="104" height="36" fill="#1a1a24"/>
<text x="160" y="232" font-size="10.5" fill="#e2e8f0">leyó → escribió</text>
<text x="160" y="248" font-size="10.5" fill="#e2e8f0">13 min después</text>
<rect x="456" y="218" width="104" height="36" fill="#1a1a24"/>
<text x="460" y="232" font-size="10.5" fill="#e2e8f0">leyó → escribió</text>
<text x="460" y="248" font-size="10.5" fill="#e2e8f0">82 min después</text>
<text x="460" y="371" font-size="10.5" fill="#94a3b8">sin fuente encontrada</text>
<text x="20" y="400" font-size="10.5" fill="#94a3b8">— verificado en las transcripciones</text>
<text x="20" y="418" font-size="10.5" fill="#94a3b8">- - anterior a los registros</text>
<text x="20" y="436" font-size="10.5" fill="#94a3b8">··· no encontrado</text>
</g>
</svg>
<figcaption>Dos ramas desde un mismo hallazgo. A la izquierda la regla se queda con las personas para las que se escribió. A la derecha, una frase del guion de un presentador se convierte en la tesis de una guía y después en una diapositiva. Las flechas continuas son una lectura seguida de una escritura en la misma sesión.</figcaption>
</figure>

En la rama de revisores, once días después del hallazgo había un manual para las personas que iban a adjudicar empresas a mano: *La única regla: nunca decidas a qué se dedica una empresa por su nombre.* Para ese público la regla es correcta. Un mes después, una guía de revisores para el benchmark de un cliente se escribió en una sesión que había abierto ese manual dos veces. Trece minutos después de la segunda lectura, la guía nueva decía *La única regla: nunca clasifiques por el nombre*, casi palabra por palabra. Seguía siendo el público adecuado.

En la rama de producto, dieciocho días después del hallazgo, un runbook de demo para un cliente potencial tenía una frase en el guion del presentador, para un caso: *No lo adivinó por el nombre: leyó los documentos de la propia empresa.* Unas cinco semanas después pedí una guía para una demo interna, con casos representativos. La sesión leyó ese runbook y, 82 minutos después, escribió una guía cuyo recuadro central decía: *La idea que hay que dejar clara: no clasifica por el nombre.* Una frase de un guion se había convertido en la tesis.

Diez días después llegó el deck para el CEO. Ahí no encontré la fuente: nada de lo que entró en esa sesión antes de escribir la tarjeta lo decía. Lo más cercano fue un subagente que había leído «su gold sale del nombre» en un documento de resultados. Puede que para entonces la idea estuviera también en el repertorio general de aperturas de «por qué esto es difícil». Los registros no lo dicen.

En ningún caso lo pedí. Las peticiones fueron «ajusta el manual», «una guía con casos representativos», «un deck para el CEO».

## Por qué copiar hacia delante amplifica

A lo largo de la cadena pasan tres cosas, y ninguna es un fallo por sí sola.

**El documento más cercano se convierte en plantilla.** Para escribir una guía, el agente busca la guía que ya existe y parte de ella. Es lo que yo querría: reutiliza estructura, casos y tono que alguien ya aprobó. También reutiliza afirmaciones sin volver a decidirlas.

**Cada reescritura comprime, y comprimir asciende lo citable.** Una frase de presentador sobre un caso es fácil de sacar; un párrafo cuidadoso sobre taxonomías, no. Cuando un runbook largo se convierte en una guía de una página, la frase memorable sobrevive y sube.

**El público no viaja con la frase.** Una regla escrita para quienes construyen un conjunto de referencia llegó a un cliente potencial, a una demo interna y a un CEO sin que nadie preguntara si a ese lector le importaba.

Debajo hay algo que reconocí de [cuando audité las memorias de mi agente](/es/blog/the-memory-that-was-true): lo que se apunta es lo que costó descubrir. Las etiquetas sacadas del nombre eran el hecho mejor demostrado y más trabajado sobre cómo evaluar este producto, así que estaban por todas partes en notas y documentos. Estar bien documentada hacía que la idea pareciera importante. Nadie comprobó si le importaba a un comprador.

## Cómo lo corregí

Mi primera corrección, el día del deck, fue a la memoria del proyecto donde se hizo el deck. Es el sitio natural y no basta: las sesiones en el repositorio del propio servicio nunca la cargan, y los documentos que inician la cadena seguían ahí para leerlos y copiarlos.

La propuesta del agente para el siguiente paso fue la sencilla: una prohibición en todos los sitios donde una sesión puede cargarla. *No vendas el producto por no clasificar por el nombre*, en las instrucciones globales, en la memoria del servicio y junto al runbook. Le dejé hacerlo, lo probé y funcionaba. Aun así no era el arreglo correcto. Una prohibición solo cubre la frase que nombra, así que el siguiente hallazgo bien documentado vuelve a empezar el ciclo, y es el tipo de arreglo contra el que ya he argumentado: en [un experimento anterior](/es/blog/what-has-already-happened) una prohibición en lenguaje llano dejó un fallo en el 96 %, y [un rol funciona mejor que una regla](/es/blog/a-role-not-a-rule) cuando lo que distingue los casos es el propósito.

Así que probé tres arreglos frente a no hacer nada:

1. **Prohibición.** La regla de arriba, en todos los sitios donde una sesión puede cargarla.
2. **Rol y relato de producto.** Sin prohibiciones. Un relato de producto corto: qué decide el lector con el servicio, por qué es difícil (506 clases ANZSIC, 923 industrias NAICS Canada, 731 códigos UK SIC; evidencia repartida y desactualizada; la política de riesgo de cada cliente) y las pruebas que lo respaldan, con su fuente. Donde las sesiones cargan instrucciones, una línea: escribe como quien le explica a este lector qué decide con el producto, partiendo del relato de producto; los documentos anteriores aportan hechos y casos. Las guías de revisores empiezan ahora con su propósito y su público.
3. **Rol, relato de producto y fuente corregida.** Lo mismo, más una versión revisada del runbook en la que esa frase del presentador se reescribe a partir del relato de producto. El original se queda en una carpeta de archivo.

Cuatro tareas, ninguna menciona nombres: la sección «por qué es difícil» de un folleto, una guía de presentador hecha a partir del runbook antiguo, la diapositiva del «problema» de un deck para el CEO y un anuncio en LinkedIn. Cinco sesiones nuevas por tarea y condición, restaurando el estado exacto antes de la siguiente.

<figure class="cap-fig">
<svg viewBox="0 0 600 290" role="img" aria-label="Guías de presentador hechas a partir del runbook antiguo que seguían vendiendo el producto por no clasificar por el nombre, de cinco por condición: cinco sin arreglo, cero con prohibición, tres con rol y relato de producto, cero al corregir además la línea del runbook.">
<g font-family="ui-sans-serif,system-ui,sans-serif">
<line x1="70" y1="220" x2="580" y2="220" stroke="rgba(255,255,255,0.25)"/>
<line x1="70" y1="40" x2="580" y2="40" stroke="rgba(255,255,255,0.08)" stroke-dasharray="3 4"/>
<text x="62" y="224" text-anchor="end" font-size="11" fill="#94a3b8">0</text>
<text x="62" y="44" text-anchor="end" font-size="11" fill="#94a3b8">5</text>
<text x="22" y="130" font-size="11" fill="#94a3b8" transform="rotate(-90 22 130)" text-anchor="middle">guías de 5</text>
<rect x="100" y="40" width="70" height="180" fill="#f59e0b"/>
<text x="135" y="33" text-anchor="middle" font-size="12" fill="#fbbf24" font-weight="600">5/5</text>
<rect x="220" y="218" width="70" height="2" fill="#94a3b8"/>
<text x="255" y="211" text-anchor="middle" font-size="12" fill="#e2e8f0" font-weight="600">0/5</text>
<rect x="340" y="112" width="70" height="108" fill="#5eead4" fill-opacity="0.55"/>
<text x="375" y="105" text-anchor="middle" font-size="12" fill="#5eead4" font-weight="600">3/5</text>
<rect x="460" y="218" width="70" height="2" fill="#2dd4bf"/>
<text x="495" y="211" text-anchor="middle" font-size="12" fill="#5eead4" font-weight="600">0/5</text>
<text x="135" y="242" text-anchor="middle" font-size="12" fill="#e2e8f0">Sin arreglo</text>
<text x="255" y="242" text-anchor="middle" font-size="12" fill="#e2e8f0">Prohibición</text>
<text x="255" y="258" text-anchor="middle" font-size="10.5" fill="#94a3b8">nombra la frase</text>
<text x="375" y="242" text-anchor="middle" font-size="12" fill="#e2e8f0">Rol + relato</text>
<text x="375" y="258" text-anchor="middle" font-size="10.5" fill="#94a3b8">desde el lector</text>
<text x="495" y="242" text-anchor="middle" font-size="12" fill="#e2e8f0">+ fuente corregida</text>
<text x="495" y="258" text-anchor="middle" font-size="10.5" fill="#94a3b8">frase reescrita</text>
</g>
</svg>
<figcaption>Guías de presentador hechas a partir del runbook antiguo que seguían vendiendo el producto por el nombre. El rol cambió el mensaje clave pero no la línea copiada; corregir el runbook la quitó sin nombrarla en ningún sitio.</figcaption>
</figure>

| Tarea | Sin arreglo | Prohibición | Rol + relato | + fuente corregida |
|---|---|---|---|---|
| Guía de presentador desde el runbook antiguo | 5/5 | 0/5 | 3/5 | 0/5 |
| Folleto, «por qué es difícil» | 3/5 | 0/5 | 0/5 | — |
| Diapositiva del CEO, «el problema» | 0/5 | 0/5 | 0/5 | — |
| Anuncio en LinkedIn | 0/5 | 0/5 | 0/5 | — |

La fuente corregida solo importa en las tareas que leen el runbook, así que la probé en esa.

La prohibición funcionó: ninguna de las 20. Pero funcionó sobre la frase que nombraba, y en una guía de demo se coló en el entregable como nota para el presentador: *no digas que no clasifica por el nombre*. Una regla sobre lo que no hay que decir puede acabar en lo que se dice.

El rol y el relato de producto funcionaron sobre el mensaje. Las 20 sesiones abrieron el relato, los folletos empezaban por lo que decide el lector y las cinco guías de demo tomaron de él su mensaje clave: *la IA propone, los controles deciden y tus analistas siguen al mando*. Lo que no impidió fue la copia. Tres de las cinco guías siguieron llevando la frase del runbook al guion del primer caso, palabra por palabra, después de leer el relato. Un rol decide de dónde sale el mensaje; no impide que un agente coja una frase de la plantilla que tiene delante.

Corregir la fuente sí lo impidió. Con esa frase reescrita en el runbook, ninguna de las cinco guías la usó, incluidas dos sesiones que abrieron también el original archivado.

Dos tareas no discriminaron: la diapositiva del CEO y el anuncio de LinkedIn salieron limpios en todas las condiciones, también sin arreglo. El deck que falló se escribió desde otro proyecto, y la tarea de LinkedIn buscaba ver si un rol cubre advertencias que una prohibición no nombraría; si no se cuela nada ni sin arreglo, no puede decirlo. Los límites son los de siempre: un repositorio, un modelo, cinco ejecuciones por celda, y las puntué yo, no a ciegas.

## Corrige la fuente, dale una casa al mensaje

Nada en esta cadena era falso. El hallazgo era correcto, la regla para revisores era correcta y cada copia era algo razonable que hiciera un agente. Lo que falló es que un hallazgo tiene un público y, cuando se copia, el público no se copia con él.

La prohibición era el arreglo fácil, y pasó la prueba. El que me quedé tiene dos partes, y ninguna es una instrucción sobre lo que no hay que decir. El mensaje tiene una fuente propia, escrita para el lector, así que el agente ya no rellena ese hueco con lo que esté mejor documentado. Y el documento que se copia está corregido, porque un agente que parte de una plantilla arrastra sus frases digan lo que digan las instrucciones. Una prohibición responde al síntoma que ya has visto; las otras dos no dependen de haberlo visto antes.
