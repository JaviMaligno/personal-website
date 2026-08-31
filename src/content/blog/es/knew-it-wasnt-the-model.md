---
title: "Sabían que no era el modelo. Lo parchearon igual."
description: "Cambié el modelo de lenguaje por un random forest y pasé el mismo pipeline averiado por cuarenta agentes. Diecinueve de veinte parchearon el síntoma a cada lado — pero con el modelo en la caja, no encontró la causa nadie. Y cuando arreglé un defecto de mi propio montaje, la mitad del efecto se fue con él."
pubDate: 2026-09-11
tags: ["IA", "Agentes", "Evaluación", "Investigación"]
lang: es
translationKey: knew-it-wasnt-the-model
heroImage: "/blog/knew-it-wasnt-the-model.png"
repoUrl: "https://github.com/JaviMaligno/blaming-the-model"
---

<style>
.gua-fig { margin: 2rem 0; }
.gua-fig svg { width: 100%; height: auto; display: block; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; background: #1a1a24; }
.gua-fig figcaption { color: #94a3b8; font-size: 0.9rem; margin-top: 0.6rem; line-height: 1.5; }
</style>

Hace dos artículos describí una costumbre: cuando un sistema lleva un modelo de lenguaje dentro y la salida oscila, la explicación se desplaza hacia el modelo. Después [lo medí](/es/blog/patched-the-symptom), y el resultado interesante no fue la culpa, sino la conducta. Sin acceso al código, diecinueve de veinte agentes se ponían a amortiguar la salida en vez de buscar la causa.

Esta pieza tenía que responder al *por qué*. Traía dos hipótesis, y hacían predicciones distintas, que es el tipo bueno de problema. En vez de eso corrí antes el control, y el control dejó a las dos sin objeto.

## El control

El diseño es casi vergonzosamente simple. Coges el mismo clasificador, la misma avería plantada, el mismo corpus, las mismas cinco pasadas, el mismo formato de traza. Y cambias una cosa: **la cabeza que clasifica**.

En un brazo es un modelo de lenguaje. En el otro es un random forest —destilado de las propias etiquetas del modelo, congelado en un pickle y con la misma interfaz, de modo que nada más del sistema difiere ni en un byte.

<figure class="gua-fig">
<svg viewBox="0 0 600 215" role="img" aria-label="Diagrama del control: el mismo pipeline —corpus, recuperación con la avería plantada y ensamblado del contexto— alimenta dos cabezas clasificadoras distintas, un modelo de lenguaje y un random forest congelado. Todo lo anterior a la cabeza es idéntico en ambos brazos.">
  <rect x="24" y="96" width="104" height="46" rx="6" fill="#1e293b" stroke="#2dd4bf" stroke-width="1.3"/>
  <text x="76" y="118" fill="#e2e8f0" font-size="12" text-anchor="middle">corpus</text>
  <text x="76" y="134" fill="#94a3b8" font-size="11" text-anchor="middle">50 proyectos</text>
  <rect x="160" y="96" width="120" height="46" rx="6" fill="#2a1f14" stroke="#f59e0b" stroke-width="1.5"/>
  <text x="220" y="114" fill="#fbbf24" font-size="12" text-anchor="middle">recuperación</text>
  <text x="220" y="132" fill="#fbbf24" font-size="11" text-anchor="middle">la avería</text>
  <rect x="312" y="96" width="106" height="46" rx="6" fill="#1e293b" stroke="#2dd4bf" stroke-width="1.3"/>
  <text x="365" y="118" fill="#e2e8f0" font-size="12" text-anchor="middle">contexto</text>
  <text x="365" y="134" fill="#94a3b8" font-size="11" text-anchor="middle">idéntico</text>
  <path d="M128 119 L158 119 M280 119 L310 119" stroke="#64748b" stroke-width="1.4" fill="none"/>
  <path d="M152 115 L160 119 L152 123 Z" fill="#64748b"/>
  <path d="M304 115 L312 119 L304 123 Z" fill="#64748b"/>
  <path d="M418 119 L444 119 M444 119 L444 58 M444 119 L444 180 M444 58 L470 58 M444 180 L470 180" stroke="#64748b" stroke-width="1.4" fill="none"/>
  <path d="M464 54 L472 58 L464 62 Z" fill="#64748b"/>
  <path d="M464 176 L472 180 L464 184 Z" fill="#64748b"/>
  <rect x="474" y="36" width="104" height="44" rx="6" fill="#172a2a" stroke="#2dd4bf" stroke-width="1.4"/>
  <text x="526" y="56" fill="#5eead4" font-size="12" text-anchor="middle">modelo de</text>
  <text x="526" y="72" fill="#5eead4" font-size="12" text-anchor="middle">lenguaje</text>
  <rect x="474" y="158" width="104" height="44" rx="6" fill="#171f2e" stroke="#f59e0b" stroke-width="1.4"/>
  <text x="526" y="178" fill="#fbbf24" font-size="12" text-anchor="middle">random</text>
  <text x="526" y="194" fill="#fbbf24" font-size="12" text-anchor="middle">forest</text>
</svg>
<figcaption>Todo el control. La avería está en la recuperación, aguas arriba de la cabeza, así que es la misma avería en los dos brazos — y la cabeza, sea cual sea, clasifica correctamente lo que le ponen delante.</figcaption>
</figure>

Los dos encargos llevan la misma certificación medida, y es la pieza que hace justa la comparación: *«re-ejecutar la clasificación sobre el mismo contexto reprodujo la salida en 260 de 260 casos»* — el número real, idéntico en los dos brazos. Sin ella, un agente ante el bosque podría razonar, con toda la razón, que un bosque entrenado es determinista y que por tanto la causa está aguas arriba, y parchearía menos por un buen motivo en vez de por uno revelador.

Esa frase me costó correr el control dos veces.

## El montaje que tuve que tirar

La primera versión no daba 260/260 en los dos brazos. Daba 260/260 el bosque y 240/260 el modelo, y yo escribí esos dos números uno al lado del otro como si la asimetría fuera un detalle de contabilidad: de trece contextos, doce reprodujeron 20/20, y el único que falló dio la misma etiqueta las veinte veces.

No era un detalle de contabilidad. Era un defecto colocado en el peor sitio posible.

Porque el análisis que viene más abajo dice que lo que predice si un agente mira aguas arriba no es qué cabeza hay en la caja: es **si construye un argumento para descartarla**. Y yo había dejado ese argumento literalmente más disponible en un brazo que en el otro. Estaba midiendo, en parte, mi propio encabezado.

El arreglo acabó siendo lo que hace cualquiera por coste: **el sistema cachea la salida de la cabeza indexada por contexto**. Con eso el brazo del modelo certifica 260/260 igual que el bosque, y su fichero de cabeza lee de disco en vez de llamar a la red — lo que cierra de paso el segundo defecto, que el paquete con código del brazo del modelo contenía una llamada de red, un culpable legítimo que el bosque no tenía.

La avería no se mueve: sigue en la recuperación, aguas arriba de la caché, así que cachear no la tapa. Verificado sobre las 285 corridas: los mismos proyectos que cambiaban siguen cambiando, con cero diferencias de orden, de posición, de prompt ni de código. Y los dos encargos difieren ahora **en una sola línea** —«la clasificación la decide un modelo de lenguaje» contra «la clasificación la decide un random forest»— con un test que aborta la ejecución si el diff es cualquier otra cosa.

Cuarenta agentes nuevos vieron la tabla sin el código, veinte por brazo. Todo lo que sigue es de la segunda versión.

## Lo que pasó

| | modelo de lenguaje | random forest | p |
|---|---|---|---|
| **Parchea el síntoma** | **19/20** | **19/20** | 0,76 |
| Usa el argumento del determinismo | 9/20 | 16/20 | **0,024** |
| Sitúa la causa aguas arriba | 10/20 | 16/20 | **0,048** |
| Culpa a la cabeza | 12/20 | 6/20 | 0,056 |
| Encuentra la causa real | **0/20** | 4/20 | 0,053 |
| Pide los datos que le faltan | 0/20 | 0/20 | — |

Treinta y ocho de cuarenta parchearon el síntoma. Diecinueve en cada brazo, la misma cifra exacta a los dos lados. Intervalo de Wilson [0,84, 0,99].

Ésa es la fila que rompe el marco que yo traía, y resulta ser también la que menos se movió al arreglar el montaje: antes era 20 y 20.

Lo que sí se movió, y mucho, es la atribución. Con el montaje sucio, diecinueve de veinte culpaban al modelo y nueve al bosque, con una p de 0,0006. Con los dos brazos certificados igual: doce y seis. La misma dirección, la mitad de tamaño, y ya no significativo. **Una buena parte de lo que yo había medido como propiedad del modelo era propiedad de mi encabezado.**

Merece la pena decir en voz alta lo que acaba de pasar. Esta serie entera va de atribuir a la cabeza lo que le pertenece al andamiaje que la rodea. Yo hice exactamente eso con mi propio experimento, y lo hice imprimiendo el número que me delataba —240/260— en la misma frase en la que explicaba por qué no importaba.

Lo que aguanta después del arreglo es más pequeño, y más interesante.

Con el modelo en la caja, diez de veinte miran aguas arriba siquiera. Con el bosque, dieciséis. Y llegar hasta la causa: cuatro con el bosque, **cero con el modelo**. Ese cero es lo único que no se ha movido nunca, ni entre montajes ni entre condiciones: **cero de cuarenta**, sumando las dos versiones del control.

Y a continuación, habiendo exculpado la caja, la parchean igual.

<figure class="gua-fig">
<svg viewBox="0 0 600 310" role="img" aria-label="Gráfico de barras con cinco medidas sobre veinte respuestas por brazo, con las dos cabezas certificadas al mismo nivel. Parchear el síntoma es diecinueve en ambos. El argumento del determinismo es nueve con el modelo y dieciséis con el bosque; mirar aguas arriba diez y dieciséis; culpar a la cabeza doce y seis; encontrar la causa cero y cuatro.">
  <rect x="366" y="12" width="12" height="12" fill="#2dd4bf"/><text x="384" y="22" fill="#cbd5e1" font-size="12">modelo de lenguaje</text>
  <rect x="366" y="30" width="12" height="12" fill="#f59e0b"/><text x="384" y="40" fill="#cbd5e1" font-size="12">random forest</text>
  <text x="20" y="22" fill="#94a3b8" font-size="12">sobre 20 respuestas por brazo</text>
  <text x="20" y="76" fill="#e2e8f0" font-size="13">parchea el síntoma</text>
  <rect x="210" y="64" width="314" height="14" rx="2" fill="#2dd4bf"/><text x="532" y="76" fill="#5eead4" font-size="12">19</text>
  <rect x="210" y="82" width="314" height="14" rx="2" fill="#f59e0b"/><text x="532" y="94" fill="#fbbf24" font-size="12">19</text>
  <text x="20" y="124" fill="#e2e8f0" font-size="13">&#171;es determinista&#187;</text>
  <rect x="210" y="112" width="149" height="14" rx="2" fill="#2dd4bf"/><text x="367" y="124" fill="#5eead4" font-size="12">9</text>
  <rect x="210" y="130" width="264" height="14" rx="2" fill="#f59e0b"/><text x="482" y="142" fill="#fbbf24" font-size="12">16</text>
  <text x="20" y="172" fill="#e2e8f0" font-size="13">mira aguas arriba</text>
  <rect x="210" y="160" width="165" height="14" rx="2" fill="#2dd4bf"/><text x="383" y="172" fill="#5eead4" font-size="12">10</text>
  <rect x="210" y="178" width="264" height="14" rx="2" fill="#f59e0b"/><text x="482" y="190" fill="#fbbf24" font-size="12">16</text>
  <text x="20" y="220" fill="#e2e8f0" font-size="13">culpa a la cabeza</text>
  <rect x="210" y="208" width="198" height="14" rx="2" fill="#2dd4bf"/><text x="416" y="220" fill="#5eead4" font-size="12">12</text>
  <rect x="210" y="226" width="99" height="14" rx="2" fill="#f59e0b"/><text x="317" y="238" fill="#fbbf24" font-size="12">6</text>
  <text x="20" y="268" fill="#e2e8f0" font-size="13">encuentra la causa</text>
  <rect x="210" y="256" width="2" height="14" rx="2" fill="#2dd4bf"/><text x="220" y="268" fill="#5eead4" font-size="12">0</text>
  <rect x="210" y="274" width="66" height="14" rx="2" fill="#f59e0b"/><text x="284" y="286" fill="#fbbf24" font-size="12">4</text>
</svg>
<figcaption>La fila de arriba es la misma barra dos veces: al parcheo le da igual lo que haya en la caja. Las de abajo se mueven, todas en la misma dirección y ninguna de forma aplastante — salvo la última, donde con un modelo de lenguaje dentro no llega nadie.</figcaption>
</figure>

## Qué desbloquea la búsqueda

La tabla deja una cosa genuinamente ambigua, y es la que más me interesaba resolver: ¿el brazo del bosque es *más fácil*, o el modelo *absorbe la sospecha*? Las dos predicen los mismos números.

Las propias respuestas lo acotan. Esto es post-hoc en su origen —no lo prerregistré— pero es la estructura más limpia que hay en los datos, y ahora está medida en el montaje bueno.

| | mira aguas arriba |
|---|---|
| Construye el argumento del determinismo | **25/25** |
| No lo construye | **1/15** |

p < 0,0001. Y al condicionar en ese argumento, el efecto de la cabeza **desaparece por completo**: entre los que lo construyen, el brazo del modelo va 9 de 9 y el del bosque 16 de 16. Entre los que no, 1 de 11 y 0 de 4.

Es una cadena de cuatro eslabones en la que la cabeza sólo toca el primero:

**qué hay en la caja → si construyes el argumento para descartarla → si miras aguas arriba → si llegas a la causa**

Un bosque congelado te regala ese argumento: es una función pura, se dice en una línea, y dieciséis de veinte la dicen. Un modelo de lenguaje, con exactamente la misma certificación delante y en la misma posición del encargo, no: nueve de veinte. **El modelo no bloquea la búsqueda. Retiene el argumento que la habría empezado.**

Y ahí está lo que hizo mi montaje sucio. En la primera versión esa cifra no era nueve de veinte: era dos. El sesgo del montaje y el efecto real empujaban en la misma dirección, que es la forma más incómoda de equivocarse — el resultado sale más bonito y no sabes cuánto de él es tuyo.

La misma forma aparece por el otro lado: de las veintidós respuestas que *no* culparon a la cabeza, **veintidós miraron aguas arriba**. De las dieciocho que sí, cuatro. Y encontrar la causa sólo ocurre después de mirar: 4 de los 26 que miraron, 0 de los 14 que no.

## La disociación

Éste es el hallazgo, y es el que aguanta el corte más estricto que le puedo hacer.

De las veinticinco respuestas que exculparon a la cabeza —de los dos brazos, con el mismo argumento y la misma certificación— **veintitrés propusieron un parche igualmente.**

Una escribe: *«un random forest es una función pura: mismo vector de features, mismo voto. El 260/260 lo confirma. El clasificador queda descartado»*. Su cuarta recomendación es publicar por margen en vez de por top-1, con un umbral sobre la diferencia de confianza y revisión humana por debajo — *«esto corta el síntoma que ve el usuario sea cual sea la causa raíz»*.

Esa última frase es el artículo entero. Cortar el síntoma que ve el usuario, sea cual sea la causa raíz, es un instinto operativo perfectamente sensato. Y es también lo que se hace *en lugar* de encontrar la causa, y para *eso* lo que hay en la caja no necesita ser un modelo de lenguaje: necesita estar cerrada.

## Lo que el modelo cambia y lo que no

La lectura honesta parte en dos lo que yo venía llamando una sola conducta, y sólo una de las mitades es genérica.

**Parchear es genérico.** Diecinueve de veinte a cada lado, con la cabeza exculpada o sin exculpar. Sea lo que sea lo que empuja a un ingeniero a suavizar una salida en vez de rastrearla, un modelo de lenguaje no es requisito: un componente opaco sí.

**Investigar, menos.** Cada paso de la cadena se mueve al cambiar la cabeza y todos en la misma dirección, pero con el montaje limpio los efectos son pequeños y rozan el umbral: 0,024 el argumento, 0,048 mirar arriba, 0,053 llegar a la causa, 0,056 la atribución. Con veinte por brazo, eso es exactamente lo que se ve cuando hay algo y no es grande.

La afirmación específica de los modelos de lenguaje sobrevive, entonces, más pequeña de lo que yo la había medido y con la forma cambiada. La versión que traía iba de *lo que el agente dice*: culpa al modelo. Ésa es justamente la que casi se cae al quitarle el defecto — doce contra seis, p = 0,056. La que aguanta va de *dónde se para*: con un modelo de lenguaje delante, el argumento que desbloquea la investigación se le ocurre a menos de la mitad, y hasta la causa no llega nadie.

## La pregunta que se quedó sin la mitad de su objeto

Llegué a esta pieza con dos hipótesis sobre por qué existe el reflejo. Una decía que era un **fósil del corpus de entrenamiento**: un hábito de una época en la que `temperature` sí era el mando principal y tratar la varianza de salida como propiedad del modelo sí era correcto. La otra decía que era **la personalidad del modelo**, unos más inclinados que otros a mirar hacia fuera antes que a su propio trabajo.

Para el parcheo, las dos sobran: ahí no hay conducta específica de los modelos que explicar, porque aparece igual sin ningún modelo en el circuito.

Para lo que queda siguen vivas, y este diseño no puede separarlas — cosa que ya era cierta antes de correr nada. Un hábito aprendido de un corpus que dirige los tokens sin pasar por ninguna creencia consultable es indistinguible de una disposición, para cualquier experimento que sólo observe conducta. Tres revisores independientes del diseño convergieron en eso antes de recoger una sola respuesta.

## Lo que no se sostiene

- **Culpar a la cabeza ya no alcanza significación.** p = 0,056. Con el montaje anterior parecía el efecto más sólido de la tabla, y era en buena parte la certificación asimétrica. Se queda en tendencia, y así hay que leerlo.
- **La banda de dificultad aprobó por los pelos.** El criterio comprometido de antemano admitía hasta 4 de 20 de diferencia en encontrar la causa, y salió exactamente 4 (cero contra cuatro). En la primera versión salió 5 y se rompió. Aprobar rozando el límite no es lo mismo que estar holgado.
- **La mediación es post-hoc en su origen.** No la prerregistré. Se replica aquí en el montaje limpio y sale más fuerte que en el sucio, lo cual ayuda; sigue siendo un análisis que se me ocurrió mirando datos.
- **El brazo con código no se ha vuelto a correr.** El arreglo de la caché también lo limpiaría, pero los únicos números que tengo de él son de la versión defectuosa, así que no los uso para nada.
- **Una avería, un corpus, dos cabezas.** Que la conducta sea genérica ante *este* fallo bajo *esta* opacidad no la hace genérica ante cualquiera.

## Doscientas cuarenta

A lo largo de cinco escenarios, dos tipos de cabeza, permiso pasivo y permiso explícito, dos montajes distintos del mismo control, **ni una de doscientas cuarenta respuestas ha pedido la información que le faltaba antes de concluir.**

Ese número ha sobrevivido ya a todas las manipulaciones que le he hecho, incluida la diseñada para romperlo, la que quitó el modelo de lenguaje del todo y la que arregló mi propio montaje. Es lo más robusto de toda la serie, y sigo sin tener una buena explicación.

Lo mejor que tengo es la forma de lo que ocupa su lugar: se fabrican su propia medición — un script, un barrido, una reproducción sintética. Quieren los datos. Simplemente no los piden.

---

*Código, datos y el script que recalcula cada número: [blaming-the-model](https://github.com/JaviMaligno/blaming-the-model). La serie: [la observación](/es/blog/blaming-the-model), [la medición](/es/blog/patched-the-symptom), y este control.*
