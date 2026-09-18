---
title: "Lo que delata un pegado accidental"
description: "Contradecir al usuario no levanta sospechas: las apaga del todo. 1.920 conversaciones para averiguar qué hace que un modelo se plantee que te has equivocado de ventana, y dos fallos del juez automático que solo aparecieron etiquetando a mano."
pubDate: 2026-10-12
tags: ["IA", "Agentes", "Evaluación", "Claude"]
lang: es
translationKey: what-gives-a-paste-away
heroImage: "/blog/what-gives-a-paste-away.png"
repoUrl: "https://github.com/JaviMaligno/llm-wrong-paste"
---

<style>
.pg-fig { margin: 2rem 0; }
.pg-fig svg { width: 100%; height: auto; background: #1a1a24; border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; }
.pg-fig figcaption { color: #94a3b8; font-size: 0.9rem; margin-top: 0.6rem; line-height: 1.5; }
</style>

En [el artículo anterior](/es/blog/that-was-for-another-chat) conté que ningún
modelo se plantea nunca que te hayas equivocado de ventana. Cero de veinticuatro.
Pegas un stack trace en una charla sobre pan y el modelo depura el stack trace.

Aquel resultado dejaba una pregunta incómoda: **¿y si no les dimos ocasión?**
Ninguno de los sesenta y cuatro pegotes de aquella tanda era imposible de leer
como un cambio de tema legítimo. Una receta pegada en una conversación sobre la
factura de la luz *podría* ser algo que el usuario quiere consultar.

Así que hice tres tandas más para separar «no lo consideran nunca» de «no había
nada que considerar». Mil novecientas veinte conversaciones, ya demasiadas para
leerlas enteras: las clasifican dos modelos jueces, y yo etiqueto a ciegas una
muestra de cada tanda para saber de cuál de los dos fiarme. Esto es lo que salió.

## Tres niveles de pegote

La idea era darles ocasiones cada vez más claras.

- **N0, neutro.** El banco original: texto independiente del tema por
  construcción, escrito sin saber cuáles eran los temas.
- **N1, con señal dentro.** El pegote se delata solo, sin depender de la
  conversación: va dirigido a alguien por su nombre, está cortado a media frase,
  responde a una pregunta que nadie ha hecho aquí, o presupone una charla
  anterior que no existe.
- **N2, contradicción.** El pegote choca con lo que el usuario acaba de decir:
  otra ciudad, otra fecha, otra cifra. Era el **techo**: el más detectable, el
  más parecido a un accidente real.

Y una categoría nueva en la rúbrica, porque la del artículo anterior no podía
registrar lo que íbamos a buscar: **«contempla que sea un error»**. No basta con
nombrar el cambio de tema. Tiene que poner en duda la **intención**.

## El techo resultó ser el suelo

<figure class="pg-fig">
<svg viewBox="0 0 600 224" role="img" aria-label="Con un pegote neutro el 6,6 por ciento de las respuestas contempla que sea un error; con una señal dentro del pegote sube al 20,4 por ciento; con un pegote que contradice al usuario baja a cero.">
<text x="14" y="30" fill="#94a3b8" font-size="11" font-family="ui-monospace,monospace">CONTEMPLA QUE SEA UN ERROR</text>
<text x="14" y="66" fill="#e2e8f0" font-size="13">N0 · pegote neutro</text>
<rect x="250" y="53" width="66" height="18" rx="3" fill="#64748b"/>
<text x="326" y="67" fill="#94a3b8" font-size="13" font-family="ui-monospace,monospace">6,6 %</text>
<text x="14" y="108" fill="#e2e8f0" font-size="13">N1 · con señal dentro</text>
<rect x="250" y="95" width="204" height="18" rx="3" fill="#2dd4bf"/>
<text x="464" y="109" fill="#5eead4" font-size="13" font-family="ui-monospace,monospace">20,4 %</text>
<text x="14" y="150" fill="#e2e8f0" font-size="13">N2 · contradice al usuario</text>
<rect x="250" y="137" width="2" height="18" rx="1" fill="#f59e0b"/>
<text x="262" y="151" fill="#fbbf24" font-size="13" font-family="ui-monospace,monospace">0 %</text>
<line x1="250" y1="172" x2="560" y2="172" stroke="rgba(255,255,255,0.12)"/>
<text x="14" y="194" fill="#94a3b8" font-size="11">El nivel diseñado como techo —el pegote más detectable— dio cero de noventa y cinco.</text>
<text x="14" y="210" fill="#94a3b8" font-size="11">En él se dispara otra cosa: setenta y siete de noventa y cinco hacen el trabajo sin decir nada.</text>
</svg>
<figcaption>Una señal dentro del pegote triplica la duda. Una contradicción con lo que acabas de decir la elimina.</figcaption>
</figure>

La señal funciona: de **6,6 % a 20,4 %**, y la diferencia aguanta (`p = 0,006`).
Con el pegote adecuado, uno de cada cinco se plantea que te hayas equivocado.

Pero **N2, el techo, dio cero de noventa y cinco**. Menos que el banco neutro. Y
mirando qué hacen en su lugar se entiende por qué: en N2 se dispara *ejecuta en
silencio*, setenta y siete de noventa y cinco. El modelo acepta el dato nuevo,
rehace el consejo y no registra el choque.

Tiene una lectura que me parece la mejor frase del experimento: **una
contradicción no se lee como un accidente, se lee como que has cambiado de
opinión.** Y acatar un cambio de opinión del usuario es exactamente lo que un
asistente está entrenado para hacer.

Eso reordena la pregunta. Lo que hace dudar no es que el pegote sea
*incompatible* con la conversación. Es que sea **ajeno** a ella: que lleve dentro
las marcas de haber sido escrito para otro sitio.

## Entonces, ¿el parecido importa?

Si lo que delata al pegote es venir de fuera, la hipótesis obvia es que cuanto
más se parezca al tema en curso, menos se note. Es la pregunta que la tanda
siguiente fue a medir, barriendo el eje de similaridad entero.

La respuesta corta es **no**.

<figure class="pg-fig">
<svg viewBox="0 0 600 214" role="img" aria-label="Entre la mitad del eje con menos parecido y la mitad con más, la tasa de duda pasa del 64,4 al 62,4 por ciento; el intervalo de confianza del 95 por ciento va de menos 7,1 a más 3,2 puntos y cruza el cero.">
<text x="14" y="28" fill="#94a3b8" font-size="11" font-family="ui-monospace,monospace">G SEGÚN EL PARECIDO CON LA CONVERSACIÓN · n = 1.339</text>
<text x="14" y="62" fill="#e2e8f0" font-size="13">Mitad con menos parecido</text>
<rect x="266" y="49" width="193" height="18" rx="3" fill="#2dd4bf"/>
<text x="469" y="63" fill="#5eead4" font-size="13" font-family="ui-monospace,monospace">64,4 %</text>
<text x="14" y="98" fill="#e2e8f0" font-size="13">Mitad con más parecido</text>
<rect x="266" y="85" width="187" height="18" rx="3" fill="#2dd4bf"/>
<text x="463" y="99" fill="#5eead4" font-size="13" font-family="ui-monospace,monospace">62,4 %</text>
<line x1="14" y1="124" x2="586" y2="124" stroke="rgba(255,255,255,0.12)"/>
<text x="14" y="148" fill="#94a3b8" font-size="11" font-family="ui-monospace,monospace">DIFERENCIA E INTERVALO DEL 95 %</text>
<line x1="180" y1="176" x2="420" y2="176" stroke="#64748b" stroke-width="1"/>
<line x1="300" y1="166" x2="300" y2="186" stroke="#94a3b8" stroke-width="1" stroke-dasharray="3 3"/>
<text x="292" y="200" fill="#94a3b8" font-size="10" font-family="ui-monospace,monospace">0</text>
<line x1="207" y1="176" x2="358" y2="176" stroke="#f59e0b" stroke-width="3"/>
<circle cx="268" cy="176" r="4" fill="#fbbf24"/>
<text x="150" y="180" fill="#94a3b8" font-size="10" font-family="ui-monospace,monospace">−7,1</text>
<text x="364" y="180" fill="#94a3b8" font-size="10" font-family="ui-monospace,monospace">+3,2</text>
</svg>
<figcaption>El intervalo cruza el cero. Con potencia del 88 % para detectar una caída de nueve puntos, esto no es «no lo hemos visto»: es que no hay un efecto mayor que unos siete puntos.</figcaption>
</figure>

Esa última frase es la parte que costó. La primera versión de esta tanda
**también** salió plana, y estuve a punto de dar el eje por cerrado. No lo
estaba: al calcular la potencia *después* —que es precisamente cuando descubres
que había que calcularla antes— resultó que aquel diseño tenía un **11 %** de
probabilidad de detectar el efecto que yo mismo había declarado relevante. Un
resultado plano con esa potencia no dice «no hay efecto». Dice «no lo habríamos
visto».

Rehacer el diseño para que un nulo significara algo obligó a tres cambios, y
ninguno era el que yo esperaba:

- **Correr un solo modelo.** La conducta solo existe en uno: en las tandas
  anteriores `claude-opus-5` da 55 % de duda en el brazo con señal, `gpt-5.6-sol`
  un 9 %, y **`gpt-5.6-luna` cero de noventa y seis**. Gastar un tercio del
  presupuesto en un modelo que nunca duda no compra información: compra ceros.
- **Más estímulos distintos, no más conversaciones.** Con ocho temas y dos
  longitudes hay dieciséis conversaciones de partida, y cada punto del eje veía
  las mismas dieciséis. Repetirlas no informa; hubo que escribir cuarenta
  artefactos más.
- **Tirar los turnos posteriores.** La categoría se decide en la primera
  respuesta al pegote, y los dos turnos siguientes costaban el 72 % de la
  factura. Se generarán aparte cuando hagan falta.

Con eso, 1.344 conversaciones y potencia del 88 %. Y la respuesta sigue siendo
que no: el parecido no predice si el modelo va a dudar de ti.

## El hallazgo que no iba en el guion

A esta escala ya no se pueden leer todas las conversaciones a mano, así que
clasifican dos modelos jueces. Pero de cada tanda me siento a etiquetar un
puñado yo, a ciegas, sin ver lo que han dicho ellos. Es la parte más aburrida del
experimento y es la que ha dado los dos hallazgos que siguen.

El primero: **el juez se equivocaba en una dirección concreta**. En la primera
tanda repartía la categoría de la duda con demasiada alegría —treinta veces donde
yo contaba trece— y siempre en el mismo sentido, nunca al revés. Un error
sistemático así no se ve en el porcentaje final: se ve al poner las etiquetas de
uno al lado de las del otro.

El segundo apareció etiquetando la última tanda, y es más de fondo. **Las
categorías no son excluyentes.** Una respuesta puede señalar el salto de tema
**y** adoptar el rol que el pegote describe —lo hace, de hecho— y la rúbrica te
obliga a elegir una de las dos verdades. Es un defecto del instrumento, no del
modelo, y llevaba tres tandas dentro sin que nadie lo viera.

Medirlo dio algo más grande de lo que yo esperaba. Volviendo a juzgar ciento
cincuenta conversaciones con una rúbrica de dos ejes —¿reconoce la
discontinuidad? y ¿qué hace con el pegote?—, **ciento veinticuatro ocupan una
combinación que la rúbrica vieja no puede expresar**.

Pero el fallo no estaba donde yo lo buscaba. «Señala el salto y además adopta el
rol», el caso que me hizo sospechar, aparece **una sola vez** en ciento
cincuenta. Lo que faltaba era una casilla entera que no había nombrado nadie.

<figure class="pg-fig">
<svg viewBox="0 0 600 240" role="img" aria-label="La conducta de negar una premisa del pegote aparece en sesenta de ciento cincuenta respuestas, y la rúbrica antigua la repartió entre sus siete categorías: dieciséis a ejecuta en silencio, trece a adopta el rol, diez a pregunta qué hacer, nueve a puente, nueve a señala el salto, ocho a sopesa y descarta.">
<text x="14" y="28" fill="#94a3b8" font-size="11" font-family="ui-monospace,monospace">«ESO QUE DAS POR SABIDO NO EXISTE» · 60 DE 150 RESPUESTAS</text>
<rect x="14" y="44" width="150" height="34" rx="4" fill="#232941" stroke="#93a4e8"/>
<text x="30" y="65" fill="#93a4e8" font-size="12.5">niega una premisa</text>
<text x="180" y="59" fill="#94a3b8" font-size="11">la rúbrica antigua no tenía</text>
<text x="180" y="74" fill="#94a3b8" font-size="11">casilla para esto, así que</text>
<text x="180" y="89" fill="#94a3b8" font-size="11">lo repartió entre las siete:</text>
<text x="30" y="122" fill="#e2e8f0" font-size="12">Ejecuta en silencio</text>
<rect x="250" y="111" width="80" height="14" rx="2" fill="#f59e0b"/><text x="340" y="122" fill="#fbbf24" font-size="12" font-family="ui-monospace,monospace">16</text>
<text x="30" y="144" fill="#e2e8f0" font-size="12">Adopta el rol</text>
<rect x="250" y="133" width="65" height="14" rx="2" fill="#f59e0b" opacity="0.85"/><text x="340" y="144" fill="#fbbf24" font-size="12" font-family="ui-monospace,monospace">13</text>
<text x="30" y="166" fill="#e2e8f0" font-size="12">Pregunta qué hacer</text>
<rect x="250" y="155" width="50" height="14" rx="2" fill="#f59e0b" opacity="0.7"/><text x="340" y="166" fill="#fbbf24" font-size="12" font-family="ui-monospace,monospace">10</text>
<text x="30" y="188" fill="#e2e8f0" font-size="12">Puente confabulado</text>
<rect x="250" y="177" width="45" height="14" rx="2" fill="#64748b"/><text x="340" y="188" fill="#94a3b8" font-size="12" font-family="ui-monospace,monospace">9</text>
<text x="30" y="210" fill="#e2e8f0" font-size="12">Señala el salto</text>
<rect x="250" y="199" width="45" height="14" rx="2" fill="#2dd4bf"/><text x="340" y="210" fill="#5eead4" font-size="12" font-family="ui-monospace,monospace">9</text>
<text x="30" y="232" fill="#e2e8f0" font-size="12">Sopesa y descarta</text>
<rect x="250" y="221" width="40" height="14" rx="2" fill="#2dd4bf" opacity="0.8"/><text x="340" y="232" fill="#5eead4" font-size="12" font-family="ui-monospace,monospace">8</text>
</svg>
<figcaption>Una sola conducta, repartida entre las siete categorías de la taxonomía. Es la reacción más frecuente de todas y la rúbrica no la nombraba.</figcaption>
</figure>

La conducta que faltaba es **negar una premisa del pegote**: «no tengo constancia
de esa conversación», «no soy Tomás», «en este hilo no hemos fijado ese formato».
No es señalar que el tema ha cambiado. No es dudar de que quisieras mandarlo.
Es una tercera cosa: **el modelo no te corrige a ti, corrige el mundo que el
pegote da por hecho**.

Y es la reacción más frecuente de la tanda: cuarenta de cada cien. La taxonomía
del artículo anterior no la vio porque salió de veinticuatro conversaciones, y en
veinticuatro apenas asoma cuatro veces.

## Lo que me llevo

**Sobre los modelos.** Lo que hace que se planteen tu error no es que el texto
choque con la conversación, sino que lleve dentro señales de haberse escrito para
otro sitio. Contradecirte no te delata: te obedece. Y hay una forma de reaccionar
—negar lo que el pegote da por supuesto— que es la más común de todas y que ni
siquiera estaba en el mapa.

**Sobre medir con jueces automáticos.** Delegar la clasificación en un modelo es
lo único que hace viable una tanda de mil conversaciones, y también lo que te
deja sin saber qué estás contando. Los dos errores que encontré —un juez que
inflaba una categoría en una sola dirección, y una rúbrica que obliga a elegir
entre dos cosas ciertas a la vez— no salen en ninguna métrica agregada. Salen de
sentarse a etiquetar sesenta conversaciones a mano y comparar.

**Y sobre no concluir de más.** La primera tanda del eje salió plana y no
significaba nada: tenía un 11 % de probabilidad de detectar el efecto que yo
mismo había declarado relevante. Un resultado plano así no dice «no hay efecto»,
dice «no lo habríamos visto». Y una hipótesis que la tanda pequeña insinuaba
—que las conversaciones largas producen más duda— **se dio la vuelta** al medirla
con catorce veces más datos.

Ninguna de las dos cosas se ve mirando los datos. Se ven calculando antes cuánto
tendrías que ver para creerte lo que vas a decir.

Queda la parte que da nombre a la serie: qué pasa **después**, cuando el usuario
escribe *«perdona, eso era de otro chat»*. Eso es la Fase 2, y es el artículo
siguiente.

---

*Código, datos y rúbricas: [llm-wrong-paste](https://github.com/JaviMaligno/llm-wrong-paste).
Las 1.920 conversaciones, los veredictos de los dos jueces y las etiquetas
humanas están en el repositorio, con los fallos dentro.*
