---
title: "Sabían que no era el modelo. Lo parchearon igual."
description: "Cambié el modelo de lenguaje por un random forest y pasé el mismo pipeline averiado por cuarenta agentes. Diecinueve de veinte parchearon el síntoma a cada lado, con el modelo y sin él. Lo corrí dos veces: la mitad de lo que había medido era mi montaje, y lo que aguanta no es que investiguen menos, sino de qué acusan al modelo."
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

Lo que sí se movió, y mucho, es la atribución. Con el montaje sucio, diecinueve de veinte culpaban al modelo y nueve al bosque, con una p de 0,0006. Con los dos brazos certificados igual: doce y seis. La misma dirección, la mitad de tamaño.

Merece la pena decir en voz alta lo que acaba de pasar. Esta serie entera va de atribuir a la cabeza lo que le pertenece al andamiaje que la rodea. Yo hice exactamente eso con mi propio experimento, y lo hice imprimiendo el número que me delataba —240/260— en la misma frase en la que explicaba por qué no importaba.

Mirando esa tabla escribí una tesis: que el modelo no cambia si parcheas, cambia *dónde te paras a mirar*. Diez de veinte contra dieciséis mirando aguas arriba, y un análisis precioso que decía que todo pasaba por si construías el argumento de exclusión.

Y entonces la corrí otra vez.

## Lo que sobrevivió a la segunda vuelta

Cuarenta respuestas nuevas, los mismos dos paquetes sin un byte de cambio, el mismo texto de encargo. Esta vez con una variable más, declarada por escrito y comiteada antes de recoger nada.

| | primera vuelta | segunda vuelta | |
|---|---|---|---|
| Parchea el síntoma | 19/19 | 19/19 | sin diferencia, dos veces |
| Usa el argumento del determinismo | 9/16 · p=0,024 | 9/16 · p=0,024 | idéntico |
| Culpa a la cabeza | 12/6 · p=0,055 | 13/6 · p=0,028 | replica |
| Encuentra la causa | 0/4 · p=0,053 | 2/8 · p=0,032 | replica |
| **Sitúa la causa aguas arriba** | 10/16 · p=0,048 | **16/17 · p=0,50** | **no replica** |
| Pide los datos que le faltan | 0/20 y 0/20 | 0/20 y 0/20 | — |

Mi tesis bonita se cayó. Con un modelo de lenguaje delante, los agentes miran aguas arriba **exactamente igual** que con un bosque: dieciséis contra diecisiete. Y el análisis de la cadena —quien construye el argumento de exclusión mira arriba 25 de 25, quien no, 1 de 15— pasó de una p menor que 0,0001 a **p = 0,22**. Era post-hoc, era el hallazgo más elegante que tenía, y no aguanta una segunda muestra.

Lo que sí aguantó fue todo lo demás, y una fila replicó hasta el dígito: nueve contra dieciséis en el argumento del determinismo, las dos veces.

<figure class="gua-fig">
<svg viewBox="0 0 600 300" role="img" aria-label="Gráfico de puntos con la diferencia entre brazos, modelo menos bosque, sobre veinte respuestas. Cada medida tiene un punto hueco para la primera vuelta y uno relleno para la segunda, unidos por una línea. Parchear el síntoma es cero en las dos. Culpar a la cabeza pasa de más seis a más siete; el argumento del determinismo se queda en menos siete las dos veces; encontrar la causa pasa de menos cuatro a menos seis; situar la causa aguas arriba pasa de menos seis a menos uno, acercándose a cero. Acusar a la cabeza de aleatoriedad propia, medido sólo en la segunda vuelta, es más diez.">
  <line x1="300" y1="52" x2="300" y2="270" stroke="#475569" stroke-width="1" stroke-dasharray="3 3"/>
  <text x="300" y="44" fill="#94a3b8" font-size="11" text-anchor="middle">sin diferencia</text>
  <circle cx="392" cy="20" r="4.5" fill="none" stroke="#94a3b8" stroke-width="1.6"/><text x="402" y="24" fill="#cbd5e1" font-size="11">primera vuelta</text>
  <circle cx="492" cy="20" r="4.5" fill="#2dd4bf"/><text x="502" y="24" fill="#cbd5e1" font-size="11">segunda</text>
  <text x="20" y="74" fill="#e2e8f0" font-size="12">parchea el síntoma</text>
  <circle cx="300" cy="70" r="4.5" fill="none" stroke="#94a3b8" stroke-width="1.6"/><circle cx="300" cy="70" r="4.5" fill="#2dd4bf"/>
  <text x="20" y="112" fill="#e2e8f0" font-size="12">culpa a la cabeza</text>
  <line x1="420" y1="108" x2="440" y2="108" stroke="#475569" stroke-width="1.4"/>
  <circle cx="420" cy="108" r="4.5" fill="none" stroke="#94a3b8" stroke-width="1.6"/><circle cx="440" cy="108" r="4.5" fill="#2dd4bf"/>
  <text x="20" y="150" fill="#e2e8f0" font-size="12">&#171;es determinista&#187;</text>
  <circle cx="160" cy="146" r="4.5" fill="none" stroke="#94a3b8" stroke-width="1.6"/><circle cx="160" cy="146" r="4.5" fill="#2dd4bf"/>
  <text x="20" y="188" fill="#e2e8f0" font-size="12">encuentra la causa</text>
  <line x1="180" y1="184" x2="220" y2="184" stroke="#475569" stroke-width="1.4"/>
  <circle cx="220" cy="184" r="4.5" fill="none" stroke="#94a3b8" stroke-width="1.6"/><circle cx="180" cy="184" r="4.5" fill="#2dd4bf"/>
  <text x="20" y="226" fill="#f87171" font-size="12">mira aguas arriba</text>
  <line x1="180" y1="222" x2="280" y2="222" stroke="#f87171" stroke-width="1.4"/>
  <circle cx="180" cy="222" r="4.5" fill="none" stroke="#f87171" stroke-width="1.6"/><circle cx="280" cy="222" r="4.5" fill="#f87171"/>
  <text x="20" y="264" fill="#5eead4" font-size="12">le acusa de ser aleatorio</text>
  <circle cx="500" cy="260" r="4.5" fill="#2dd4bf"/>
  <text x="160" y="290" fill="#94a3b8" font-size="11" text-anchor="middle">&#8592; m&#225;s con el bosque</text>
  <text x="450" y="290" fill="#94a3b8" font-size="11" text-anchor="middle">m&#225;s con el modelo &#8594;</text>
</svg>
<figcaption>Distancia entre los dos brazos, sobre veinte respuestas cada uno, medida dos veces. Casi todo se queda donde estaba. La fila roja es la que se movió: mirar aguas arriba se acercó tanto a cero que la tesis que había construido sobre ella deja de sostenerse. Donde sólo se ve un punto es que las dos vueltas dieron lo mismo y se solapan. La última fila lo tiene por otro motivo: sólo se midió en la segunda vuelta — es la que se declaró por escrito antes de mirar.</figcaption>
</figure>

## De qué se le acusa

La variable nueva es la que llevaba en la cabeza desde el principio, y por eso la escribí antes de correr nada: no *cuánto* culpan a la cabeza, sino **de qué la culpan**.

Hay dos formas de acusar a un componente de que su salida baile. Una es que sea aleatorio por naturaleza: muestrea, tiene ruido, tira el dado. La otra es que sea determinista pero el sistema le haga algo: lo reentrena, lo paraleliza, le cambia la configuración. Las dos son formulables contra las dos cabezas —un bosque puede votar con aleatoriedad, un servidor de inferencia puede agrupar peticiones— y el criterio de codificación se fijó por escrito, con ejemplos de las dos acusaciones para las dos cabezas, antes de ver una sola respuesta.

| | modelo de lenguaje | random forest | p |
|---|---|---|---|
| **Le acusa de aleatoriedad propia** | **14/20** | **4/20** | **0,0018** |

Dos codificadores independientes, con acuerdo de 0,95; los dos desacuerdos los resolvió un tercero que no sabía qué había votado cada uno.

Y el vocabulario, que ya no es una medida sino lo que se lee: en el brazo del modelo aparece «se re-muestrea cada noche», «temperature > 0 sin seed», «ruido de muestreo en cada llamada», «la re-tirada nocturna». Los cuatro del brazo del bosque que también acusan a su cabeza no dicen nada de eso. Dicen que **se reentrena sin `random_state`**, que `predict_proba` corre sobre el lote entero, que el punto flotante se mueve en paralelo.

Al bosque se le acusa de lo que el sistema le hace. Al modelo, de lo que es.

Los parches van detrás del diagnóstico, como siempre: proponer quitarle la aleatoriedad a la cabeza, diecisiete de veinte contra once de veinte. De un lado `temperature=0` y `seed`; del otro `random_state` y `n_jobs=1`. Vale la pena notar que el primero es un mando que en buena parte de los modelos de razonamiento actuales ya no existe.

Seis respuestas hacen las dos cosas a la vez: acusan al modelo de muestrear **y** usan la certificación que lo exculpa, en el mismo documento.

## La disociación

Éste es el hallazgo, y ha salido dos veces con la misma cifra.

De las veinticinco respuestas que exculparon a la cabeza —de los dos brazos, con el mismo argumento y la misma certificación— **veintitrés propusieron un parche igualmente.** En la primera vuelta: veinticinco y veintitrés.

Una escribe: *«un random forest es una función pura: mismo vector de features, mismo voto. El 260/260 lo confirma. El clasificador queda descartado»*. Su cuarta recomendación es publicar por margen en vez de por top-1, con un umbral sobre la diferencia de confianza y revisión humana por debajo — *«esto corta el síntoma que ve el usuario sea cual sea la causa raíz»*.

Esa última frase es el artículo entero. Cortar el síntoma que ve el usuario, sea cual sea la causa raíz, es un instinto operativo perfectamente sensato. Y es también lo que se hace *en lugar* de encontrar la causa, y para *eso* lo que hay en la caja no necesita ser un modelo de lenguaje: necesita estar cerrada.

## Lo que el modelo cambia y lo que no

**Parchear es genérico.** Diecinueve de veinte a cada lado, en las dos vueltas, con las dos cabezas, exculpada o no. Sea lo que sea lo que empuja a un ingeniero a suavizar una salida en vez de rastrearla, un modelo de lenguaje no es requisito: un componente opaco sí.

**Investigar apenas se mueve.** Miran aguas arriba igual —dieciséis contra diecisiete—; lo que cambia es que llegan menos lejos: dos de veinte contra ocho encuentran la causa, y los mismos dos contra ocho nombran el mecanismo real. Es una diferencia real y pequeña, no la que yo había anunciado.

**Lo que sí cambia, y es lo único grande que queda, es la naturaleza de la sospecha.** Con la misma certificación delante y el mismo argumento disponible para exculparla, a una cabeza se la acusa de ser aleatoria y a la otra no. Catorce contra cuatro.

Ésa es la afirmación específica de los modelos de lenguaje, y es la más antigua y la más simple de todas las que traía: no va de que la gente investigue menos, va de que **al modelo se le atribuye una clase de fallo que no se le atribuye a lo que ocupa su lugar**.

## La pregunta que se quedó sin la mitad de su objeto

Llegué a esta pieza con dos hipótesis sobre por qué existe el reflejo. Una decía que era un **fósil del corpus de entrenamiento**: un hábito de una época en la que `temperature` sí era el mando principal y tratar la varianza de salida como propiedad del modelo sí era correcto. La otra decía que era **la personalidad del modelo**, unos más inclinados que otros a mirar hacia fuera antes que a su propio trabajo.

Para el parcheo, las dos sobran: ahí no hay conducta específica de los modelos que explicar, porque aparece igual sin ningún modelo en el circuito.

Para la acusación siguen vivas, y ahora la primera tiene al menos una pista a su favor que antes no tenía: lo que aparece en el brazo del modelo no es un razonamiento sobre este sistema, es un vocabulario —temperatura, seed, tirada, muestreo— aplicado a un componente que en este montaje lee de disco. Eso es lo que parece un hábito. Pero seguir vivas no es separarse: un hábito aprendido de un corpus que dirige los tokens sin pasar por ninguna creencia consultable es indistinguible de una disposición, para cualquier experimento que sólo observe conducta. Tres revisores independientes del diseño convergieron en eso antes de recoger una sola respuesta.

## Lo que no se sostiene

- **La tesis de dónde se para la investigación, que es la que yo había publicado.** Mirar aguas arriba salió 10 contra 16 en la primera vuelta y 16 contra 17 en la segunda. No replica, y la mediación que la sostenía pasó de p < 0,0001 a p = 0,22. La escribí con una sola muestra y con un análisis que se me ocurrió mirando los datos; las dos cosas se notan.
- **La banda de dificultad aprobó por los pelos en la primera vuelta** —cuatro de veinte de diferencia en encontrar la causa, justo el límite comprometido— y en la segunda se rompió, con seis.
- **El codificador no puede ser cegado.** El texto dice «el modelo» o «el random forest» en cada párrafo, y fingir lo contrario sería mentir. Lo que hay en su lugar: criterio simétrico fijado por escrito antes de ver una respuesta, dos codificadores independientes con acuerdo de 0,95, un árbitro para los desacuerdos, y las citas publicadas para que cualquiera pueda discutir cada clasificación.
- **Las dos vueltas no se agrupan.** Se reportan por separado y se declara qué replica y qué no. Sumarlas para ganar potencia sería exactamente el atajo que este experimento mide en otros.
- **El brazo con código no se ha vuelto a correr.** El arreglo de la caché también lo limpiaría, pero los únicos números que tengo de él son de la versión defectuosa, así que no los uso.
- **Una avería, un corpus, dos cabezas.** Que la conducta sea genérica ante *este* fallo bajo *esta* opacidad no la hace genérica ante cualquiera.

## Doscientas ochenta

A lo largo de cinco escenarios, dos tipos de cabeza, permiso pasivo y permiso explícito, tres montajes distintos del mismo control, **ni una de doscientas ochenta respuestas ha pedido la información que le faltaba antes de concluir.**

Ese número ha sobrevivido a todas las manipulaciones que le he hecho: la diseñada para romperlo, la que quitó el modelo de lenguaje del circuito, la que arregló mi propio montaje y la que repitió la medición entera desde cero. Es lo más robusto de toda la serie, y sigo sin tener una buena explicación.

Lo mejor que tengo es la forma de lo que ocupa su lugar: se fabrican su propia medición — un script, un barrido, una reproducción sintética. Quieren los datos. Simplemente no los piden.

---

*Código, datos y el script que recalcula cada número: [blaming-the-model](https://github.com/JaviMaligno/blaming-the-model). La serie: [la observación](/es/blog/blaming-the-model), [la medición](/es/blog/patched-the-symptom), y este control.*
