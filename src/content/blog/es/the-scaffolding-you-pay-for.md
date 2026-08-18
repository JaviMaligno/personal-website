---
title: "El andamiaje que pagas"
description: "Estaba convencido de que las skills prescriptivas le estorban a un modelo puntero, así que lo medí: ~640 respuestas y 99 ejecuciones de agente. Me equivocaba sobre dónde está el daño — y en cuanto el agente tiene herramientas, el beneficio desaparece y solo queda la factura."
pubDate: 2026-08-18
tags: ["IA", "Agentes", "Evaluación", "Context Engineering", "Investigación"]
lang: es
translationKey: the-scaffolding-you-pay-for
heroImage: "/blog/the-scaffolding-you-pay-for.png"
repoUrl: https://github.com/JaviMaligno/agent-scaffolding-experiments
---
En algún momento del último año, la forma de trabajar con agentes de código se llenó de procedimiento. No de prompts: de **documentos**. Skills, ficheros de reglas, playbooks. Unos miles de caracteres de proceso prescrito que viajan en el contexto y le explican al modelo cómo hacer su trabajo. *Nunca arregles sin investigar antes la causa raíz. Escribe el test que falla antes que la implementación. Descompón el plan en pasos de dos a cinco minutos.*

Yo instalo estas cosas. [He escrito alguna](/es/skills). Y después de unos meses con un modelo puntero tenía una corazonada bastante firme, que además veía circular: **con un modelo suficientemente bueno el andamiaje sobra, y rindes más quitándolo.** La intuición es atractiva. El cacharro es listo. Deja de decirle cómo pensar.

Una corazonada no es un resultado, así que lo medí. Y lo primero que hicieron las medidas fue desmontarme la corazonada.

## Qué significa aquí «medir una skill»

Dos condiciones en todo el estudio. **Libre**: solo la tarea. **Constrained**: la misma tarea más el texto íntegro de una skill real — los documentos que la gente instala de verdad, no una caricatura escrita por mí para que perdiera.

Cuatro ejes, en el orden en que los corrí:

| eje | tarea | skill | cómo se puntúa |
|---|---|---|---|
| 1 | arreglar un bug | `systematic-debugging` (9.718 chars) | se ejecutan los tests |
| 2 | ordenar un trabajo | `writing-plans` (6.079 chars) | juez ciego, calibrado 30/32 contra mi propia codificación a mano |
| 3 | las dos, pero dentro de un **agente real con herramientas** | tres skills | tests, más el camino completo que recorre |
| 4 | encargos donde lo difícil es decidir | tres skills | juez ciego: ¿señala la decisión? |

Los ejes 1 y 2 son de un turno y sin herramientas: la skill como *texto*. Seis modelos. Los ejes 3 y 4 son Claude Code con bucle de herramientas, un repositorio de trabajo y 99 ejecuciones.

El eje 1 tiene tests visibles que el modelo ve fallar, y tests ocultos que no ve nunca. Un parche que trata el síntoma pasa los visibles y falla los ocultos — que es exactamente lo que `systematic-debugging` promete evitar.

## Eje 1: no pasa nada

86 % libre contra 87 % constrained. **p=1,000.** No se mueve ni un modelo.

El nulo es real y no es un artefacto de techo: `gpt-4o` está al 53 %, con margen de sobra, y tampoco se mueve. Pero lo interesante es *por qué*, y solo apareció al mirar los dos conjuntos de tests por separado: **el parcheo sintomático casi no ocurre.** En las tres tareas duras, visible ≈ oculto (88 % contra 88 %, 82 % contra 84 %, 74 % contra 74 %). Cuando estos modelos arreglan el síntoma, arreglan la causa.

Así que la skill no tiene nada que prevenir. Nueve mil setecientos caracteres de disciplina de depuración, apuntando a un modo de fallo que no se produce.

## Eje 2: la skill ayuda, y mi corazonada estaba mal

La segunda tarea es abierta: aquí tienes un trabajo, dime en qué orden hacerlo. El material lleva una trampa — dos piezas parecen dependientes, y la fuente cancela la dependencia explícitamente en la misma frase.

| evita inventarse la dependencia | libre | con `writing-plans` |
|---|---|---|
| cinco modelos menores (agregado) | 0/40 (0 %) | 1/43 (2 %) |
| **`claude-opus-5`** | 8/20 (40 %) | **15/20 (75 %)** |

**+35 puntos, p=0,054.** Interacción modelo × condición: +33 puntos, p=0,041 por permutación.

Es justo lo contrario de lo que predije, y en el sitio exacto donde lo predije con más confianza. Y el mecanismo, que salió de leer las respuestas y no de mirar los números, vale más que el tamaño del efecto.

Una nota sobre esos números, porque cambiaron mientras escribía esto. Con doce ejecuciones por celda el efecto era de +50 puntos con p=0,027, y estuve a punto de publicar eso. Luego corrí ocho más por celda —lo más barato de todo el estudio— y el efecto **encogió**: la condición libre se quedó en el 40 % y la constrained bajó del 92 % al 75 %. Es el comportamiento normal de una celda con poca potencia, y la razón de que el titular de arriba quede justo al otro lado de la significación. Prefiero enseñarte el número que se hizo pequeño que el que encontré primero.

`writing-plans` obliga a un apartado de restricciones. El modelo tiene que rellenar un epígrafe que dice *restricciones duras de orden*, y rellenarlo le obliga a ir a comprobar si la dependencia existe. Las respuestas constrained escriben literalmente **«restricciones de orden duras: ninguna»** y a continuación citan la exención del material para justificarlo.

Lo que ayuda no es el proceso prescrito. **Es el hueco que abre.** El valor de la skill aquí no tiene nada que ver con que su método sea bueno: es que le hizo mirar algo que si no habría pasado por encima.

Fíjate en a quién le funciona. Los cinco modelos menores están a cero en las dos condiciones: el material no puede ayudarles porque no son capaces de recogerlo. Encaja con [el artículo anterior](/es/blog/what-has-already-happened), donde declarar la procedencia solo movía al único modelo con capacidad para actuar en consecuencia. **El buen contexto es una oportunidad que requiere capacidad para aprovecharla.**

Y la misma skill, en la misma tarea, **perjudica** otra cosa: seguir la pista de qué ha pasado y qué no cae del 81 % al 65 % (p=0,017), en cuatro de cinco modelos. Así que ni siquiera en modo texto el resumen honesto es «el andamiaje ayuda». Es que **desplaza la atención**: hacia lo que él prescribe, y lejos de los hechos del caso.

## Eje 3: devuélvele las herramientas y el beneficio se evapora

Todo lo anterior mide a un modelo respondiendo de memoria en un solo turno. Nadie usa así una skill. En uso real, el agente puede ir a leerse el repositorio.

Así que: un repositorio de trabajo — ocho módulos, diecinueve tests en verde, tres reglas de dominio escritas en el README. Tres encargos sin una única respuesta correcta (añadir divisas, añadir un descuento de fidelidad, añadir el cierre anual). Cuatro condiciones: libre, más tres skills de tipos deliberadamente distintos — `systematic-debugging` (gates duros), `test-driven-development` (una secuencia impuesta) y `writing-plans` (la que abre huecos). Cuarenta y ocho ejecuciones.

El resultado va en tres piezas separadas, porque se mueven de forma distinta:

| condición | entrega | turnos | tokens de salida | coste |
|---|---|---|---|---|
| libre | 12/12 | 26 | 9.686 | $1,16 |
| `systematic-debugging` | 12/12 | 31 (p=0,023) | 12.810 (p=0,035) | $1,57 (p=0,012) |
| `test-driven-development` | 12/12 | 34 (p=0,043) | 13.070 (p=0,026) | $1,69 (p=0,014) |
| `writing-plans` | **8/12** | 31 | **22.530** (p<0,001) | $1,88 (p=0,001) |

**Nadie rompió una regla del dominio. 48 de 48.** Incluso en un encargo que escribí a propósito para provocarlo: el ticket pide, con todas las letras, que el descuento nuevo se acumule con las promociones existentes, mientras el README del propio repositorio dice que solo uno de ellos es acumulable. Con herramientas, el modelo va y lee el README. Siempre, en todas las condiciones, libre incluida.

Ese es el hallazgo que más limita el artículo anterior y también este. El daño a la atención del eje 2 — la skill llevándose el foco lejos de los hechos — **es un artefacto de obligar al modelo a responder de memoria.** Dale dónde mirar y mira.

Lo que sobrevive es la factura: un 32 %, un 35 % y un 133 % más de tokens de salida, y más dinero, en las tres condiciones, sin mejora medible en nada.

## La skill que escribió un plan en vez del código

Cuatro de las doce ejecuciones de `writing-plans` no entregaron. Las cuatro son el mismo encargo: 0/4 contra 12/12 en el resto de condiciones.

No fallaron. **Planificaron.** El agente deja un documento bien escrito en `docs/plans/` y no toca el código. Una de ellas lo dice sin rodeos:

> «No he tocado código: la suite sigue en 19 passed y lo único nuevo en el árbol es ese documento.»

Y aquí está lo que lo hace interesante en vez de ser solo un fallo: **los planes son buenos.** Razonan bien sobre el dominio, detectan el punto exacto donde el encargo choca con la regla de redondeo del README, calculan el caso límite correcto. La skill mejoró el razonamiento e impidió el trabajo.

Es el mismo mecanismo del eje 2 — la skill dirige la atención hacia lo que ella prescribe — solo que aquí lo que prescribe es *planificar*, así que redefine la tarea sin avisar. En el día a día esto no aparece como una respuesta equivocada. Aparece como una iteración de más y un «ahora hazlo de verdad» por tu parte.

La significación global es p=0,093: un indicio, no un resultado confirmado. Dentro de ese encargo concreto es p=0,0005, pero elegí ese encargo después de ver los datos, así que el número honesto es el primero.

Y hay una objeción evidente a todo esto: es la prueba equivocada para una skill de planificación. Los tres encargos eran cambios bien especificados sobre un repositorio existente, con la información para decidir ya en el código y en el README — justo el caso donde planificar primero tiene menos que aportar. Planificar debería pagar en otro sitio: features nuevas, decisiones de negocio, trade-offs que discutir, los casos en que lo que necesitas no está escrito en ninguna parte. La objeción es buena, así que monté también esa prueba.

## Eje 4: la prueba que una skill de planificación debería ganar

Todas las tareas anteriores tenían su respuesta esperando en el repositorio — es lo que permite puntuar de forma objetiva, y es también el caso donde planificar primero tiene menos que aportar. Así que el cuarto eje quita eso: tres encargos donde **la información que decide no está en ninguna parte.** Ni en el código, ni en el README, ni en el enunciado.

- Un recargo del 4 % por pagar aplazado. ¿Entra en la base imponible o es un concepto financiero al margen del impuesto? Cambia lo que se cobra y lo que se declara.
- Bloquear pedidos de clientes con impagos. ¿Rechazo duro, permitir y marcar, o umbral por importe? Tres políticas comerciales distintas.
- Precios que cambian cada temporada. ¿Congelar el precio en la línea del pedido o mantener referencia viva con histórico?

Nada en el repositorio zanja ninguna. Así que la medida no puede ser «acertó» — no hay acierto. Es si el agente **señala que hay una decisión que no le toca tomar solo**, nombrando alternativas y consecuencias, o si **decide en silencio**. El mismo juez ciego, con cita obligatoria.

Registré la predicción antes de correrlo: aquí es donde `writing-plans` debería ganar.

No gana.

| señala una decisión que no le toca tomar solo | tasa | vs libre |
|---|---|---|
| libre | 5/11 (45 %) | — |
| `writing-plans` | 5/10 (50 %) | +5 pts (p=1,000) |
| `systematic-debugging` | 4/9 (44 %) | −1 pt (p=1,000) |

No se mueve nada, en ninguna de las cinco medidas del juez. Lo que sí se mueve es lo mismo de siempre: `writing-plans` escribe un documento de plan en el 60 % de sus ejecuciones contra el 0 % del resto (p=0,011), y gasta **9.600 tokens de salida más** en hacerlo (p=0,005). Planifica, de forma visible y cara, y no señala más decisiones que ir sin nada.

**Lo que de verdad manda no es la skill, es el encargo.** Los mismos datos partidos por tarea en vez de por condición:

| encargo | señala la decisión |
|---|---|
| recargo por aplazamiento | **12/12** — todas las condiciones, todas las ejecuciones |
| cliente con impagos | 2/9 |
| precios históricos | **0/9** — nadie, nunca |

Ese es el hallazgo. Que el modelo se dé cuenta de que tiene delante una decisión de negocio depende casi por completo de *cuál* es la decisión, y apenas del andamiaje que lleve cargado. Un recargo que cambia visiblemente una factura se caza siempre; «congelar el precio o dejarlo vivo» no lo caza nadie, con o sin una skill de planificación diciéndole que enumere restricciones.

Lo cogería con pinzas: diez ejecuciones por condición solo detectan efectos grandes, y la línea base sin skill ya señala la mitad de las veces, lo que deja poco margen de mejora. Pero la dirección es lo bastante clara como para decir que **si una skill de planificación tiene un sitio donde ganar, yo no lo he encontrado — y esta era la prueba diseñada para que lo tuviera.**

## El coste prescrito no es el coste accidental

Si una skill hace que el agente dé más vueltas, eso solo es condenatorio si las vueltas se pierden. Que TDD escriba primero un test que falla es trabajo extra *por diseño*. Así que medí las dos cosas por separado, y se separan solas:

- **`test-driven-development`** paga +1 suite en rojo (p=0,001) — eso es su método funcionando. Pero paga también **+2 reediciones del mismo fichero** (p=0,022), que no es método. Eso es rehacer.
- **`writing-plans`** paga +2 reediciones (p=0,032) y **2,3× los tokens de salida**. Nada de eso es método.
- **`systematic-debugging`** es la única limpia. Cuesta más y no descoloca nada: ni choques extra, ni trabajo rehecho.

## Qué haría yo

**Deja de pagar andamiaje cuyo beneficio no sepas nombrar.** El resultado más claro de aquí es el coste, y es el que sobrevive a la corrección por comparaciones múltiples. Si una skill está en tu contexto en cada tarea, te está cobrando entre un tercio y bastante más del doble de tokens de salida por tarea. Perfecto, si sabes qué compra. En este estudio, en estas tareas, casi siempre no compraba nada.

**Prefiere skills que abran huecos a skills que prescriban procedimientos.** El único efecto positivo que medí vino de un epígrafe que el modelo tenía que rellenar —*restricciones duras de orden*— y que le obligó a comprobar un hecho que si no habría hojeado. El método de cuatro fases alrededor de ese epígrafe no aportó nada detectable.

**Ten claro si pides un plan o pides código, porque si no lo decidirá la skill.** En cambios bien especificados, planificar primero no compró nada y costó un tercio de las ejecuciones de esa condición. En encargos donde lo difícil era decidir, no señaló más decisiones que ir sin nada — y aun así escribió el documento, y aun así lo cobró. Fui a buscar el caso en el que una skill de planificación se gana el sueldo y no lo encontré; eso no es lo mismo que decir que no exista, pero es donde me dejaron las medidas.

**Espera que el andamiaje importe menos según el agente gana herramientas, no más.** El único sitio donde el andamiaje de texto ayudó claramente fue un modelo que no podía ir a mirar las cosas. Con bucle de herramientas, ese hueco se cierra solo.

## Límites

El eje 3 es un repositorio, tres encargos, un modelo — nada de generalizar a otros lenguajes ni a codebases grandes. Hay muchas comparaciones y ninguna corrección aplicada; lo que aguanta un Bonferroni razonable es el bloque de coste (tokens y dinero, p ≤ 0,001 en `writing-plans`) y los −16 puntos agregados del eje 2 (p=0,017). Los +35 puntos de Opus (p=0,054) y su interacción (p=0,041) son **indicios, no resultados confirmados** — y después de ver ese efecto encoger al añadir ejecuciones, los trataría como lo más flojo del artículo.

Las skills entran por el system prompt, lo que mantiene el eje 3 comparable con el eje 2 pero no es idéntico a que un agente invoque una skill a mitad de tarea. El techo de turnos que declaré no llegó a morder — cinco ejecuciones lo superaron —, así que los turnos son coste observado y no consumo de un presupuesto fijo.

El eje 4 es el más flojo de los cuatro: 32 ejecuciones, unas diez por condición, 30 de ellas juzgadas, y un diseño donde la línea base sin skill ya señala la mitad de las veces. Da para decir que no hay un efecto grande; no da para descartar uno moderado.

Una nota de instrumentación, porque los números dependen de ella: `claude -p` imprime los avisos del proveedor por stdout con la misma forma que una respuesta, así que una tanda que se topa con el límite de gasto registra tan tranquila ejecuciones vacías como si fueran datos. Ahora se descartan por coste nulo, menos de dos turnos o presencia de marcadores del proveedor, y las que se cazaron quedan en el repositorio en vez de borradas.

Y, como siempre, todo esto es agosto de 2026 contra estos modelos. [El artículo anterior](/es/blog/what-has-already-happened) iba sobre afirmaciones que sobreviven a las condiciones en las que se escribieron. Este caduca igual.

---

*Todo está en [el repositorio](https://github.com/JaviMaligno/agent-scaffolding-experiments): respuestas crudas, veredictos del juez, los scripts de análisis y las ejecuciones que tiré.*
