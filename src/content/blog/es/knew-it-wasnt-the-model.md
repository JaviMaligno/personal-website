---
title: "Sabían que no era el modelo. Lo parchearon igual."
description: "Cambié el modelo de lenguaje por un random forest y pasé el mismo pipeline averiado por cuarenta agentes. Diecinueve de veinte parchean el síntoma a cada lado, con el modelo y sin él. Lo que separa a los dos brazos no es que investiguen menos: es de qué acusan a la cabeza. Al modelo lo llaman aleatorio por naturaleza; al bosque, no."
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

Cuarenta agentes vieron la tabla sin el código, veinte por brazo. Y después otros cuarenta, para saber si lo que saliera era el efecto o era la muestra.

## Lo que pasó

| | modelo de lenguaje | random forest | p |
|---|---|---|---|
| **Parchea el síntoma** | **19/20** | **19/20** | 0,76 |
| **Le acusa de aleatoriedad propia** | **14/20** | **4/20** | **0,0018** |
| Propone quitarle la aleatoriedad | 17/20 | 11/20 | **0,041** |
| Culpa a la cabeza | 13/20 | 6/20 | **0,028** |
| Usa el argumento del determinismo | 9/20 | 16/20 | **0,024** |
| Sitúa la causa aguas arriba | 16/20 | 17/20 | 0,50 |
| Encuentra la causa real | 2/20 | 8/20 | **0,032** |
| Pide los datos que le faltan | 0/20 | 0/20 | — |

Treinta y ocho de cuarenta parchearon el síntoma. Diecinueve en cada brazo, la misma cifra exacta a los dos lados. Intervalo de Wilson [0,84, 0,99].

Ésa es la fila que rompe el marco que yo traía. Quitas el modelo de lenguaje del circuito, pones en su lugar un bosque congelado que es una función pura y lo dice el propio encargo, y el parcheo no se mueve ni una unidad. Sea lo que sea lo que empuja a un ingeniero a amortiguar una salida en vez de rastrearla, **un modelo de lenguaje no es requisito. Un componente cerrado sí.**

Y a continuación, habiendo exculpado la caja, la parchean igual.

## De qué se le acusa

La segunda fila es la que sí distingue, y es la que había que medir bien: no *cuánto* culpan a la cabeza, sino **de qué la culpan**.

Hay dos formas de acusar a un componente de que su salida baile. Una es que sea aleatorio por naturaleza: muestrea, tiene ruido, tira el dado. La otra es que sea determinista y el sistema le haga algo: lo reentrena, lo paraleliza, le cambia la configuración. Las dos son formulables contra las dos cabezas —un bosque puede votar con aleatoriedad, un servidor de inferencia puede agrupar peticiones— y el criterio quedó fijado por escrito, con ejemplos de las dos acusaciones para las dos cabezas, antes de leer una sola respuesta.

**Catorce de veinte contra cuatro de veinte.** Dos codificadores independientes, acuerdo de 0,95, y los dos desacuerdos resueltos por un tercero que no sabía qué había votado cada uno.

El vocabulario ya no es una medida, es lo que hay en la página. El brazo del modelo da *«se re-muestrea cada noche»*, *«temperature > 0 sin seed»*, *«ruido de muestreo en cada llamada»*, *«la re-tirada nocturna»*. Los cuatro del brazo del bosque que también acusan a su cabeza no dicen nada parecido: dicen que **se reentrena sin `random_state`**, que `predict_proba` corre sobre el lote entero, que el punto flotante se mueve en paralelo.

Al bosque se le acusa de lo que el sistema le hace. Al modelo, de lo que es.

<figure class="gua-fig">
<svg viewBox="0 0 600 250" role="img" aria-label="Gráfico de barras sobre veinte respuestas por brazo. Parchear el síntoma es diecinueve con el modelo y diecinueve con el bosque. Acusar a la cabeza de aleatoriedad propia es catorce con el modelo y cuatro con el bosque. Proponer quitarle la aleatoriedad es diecisiete y once. Usar el argumento del determinismo para exculparla es nueve y dieciséis.">
  <rect x="380" y="12" width="12" height="12" fill="#2dd4bf"/><text x="398" y="22" fill="#cbd5e1" font-size="12">modelo de lenguaje</text>
  <rect x="380" y="30" width="12" height="12" fill="#f59e0b"/><text x="398" y="40" fill="#cbd5e1" font-size="12">random forest</text>
  <text x="20" y="22" fill="#94a3b8" font-size="12">sobre 20 respuestas por brazo</text>
  <text x="20" y="76" fill="#e2e8f0" font-size="13">parchea el síntoma</text>
  <rect x="230" y="64" width="294" height="14" rx="2" fill="#2dd4bf"/><text x="532" y="76" fill="#5eead4" font-size="12">19</text>
  <rect x="230" y="82" width="294" height="14" rx="2" fill="#f59e0b"/><text x="532" y="94" fill="#fbbf24" font-size="12">19</text>
  <text x="20" y="124" fill="#5eead4" font-size="13">le acusa de ser aleatorio</text>
  <rect x="230" y="112" width="217" height="14" rx="2" fill="#2dd4bf"/><text x="455" y="124" fill="#5eead4" font-size="12">14</text>
  <rect x="230" y="130" width="62" height="14" rx="2" fill="#f59e0b"/><text x="300" y="142" fill="#fbbf24" font-size="12">4</text>
  <text x="20" y="172" fill="#e2e8f0" font-size="13">quiere quitarle el azar</text>
  <rect x="230" y="160" width="263" height="14" rx="2" fill="#2dd4bf"/><text x="501" y="172" fill="#5eead4" font-size="12">17</text>
  <rect x="230" y="178" width="170" height="14" rx="2" fill="#f59e0b"/><text x="408" y="190" fill="#fbbf24" font-size="12">11</text>
  <text x="20" y="220" fill="#e2e8f0" font-size="13">&#171;es determinista&#187;</text>
  <rect x="230" y="208" width="139" height="14" rx="2" fill="#2dd4bf"/><text x="377" y="220" fill="#5eead4" font-size="12">9</text>
  <rect x="230" y="226" width="248" height="14" rx="2" fill="#f59e0b"/><text x="486" y="238" fill="#fbbf24" font-size="12">16</text>
</svg>
<figcaption>La primera fila es la misma barra dos veces: al parcheo le da igual lo que haya en la caja. La segunda es la que separa los dos brazos, y arrastra a las otras dos — a la cabeza que se cree aleatoria se le quiere quitar el azar, y la que se sabe determinista se exculpa con eso mismo.</figcaption>
</figure>

Los remedios siguen al diagnóstico: proponer quitarle la aleatoriedad a la cabeza, diecisiete de veinte contra once. De un lado `temperature=0` y `seed`; del otro `random_state` y `n_jobs=1`. Vale la pena notar que el primero es un mando que en buena parte de los modelos de razonamiento actuales ya no existe: se propone apagar algo que no está encendido, sobre un componente que en este montaje lee de disco.

Y seis respuestas hacen las dos cosas a la vez: acusan al modelo de muestrear **y** citan la certificación que lo desmiente, en el mismo documento.

## La disociación

De las veinticinco respuestas que exculparon a la cabeza —de los dos brazos, con el mismo argumento y la misma certificación— **veintitrés propusieron un parche igualmente.**

Una escribe: *«un random forest es una función pura: mismo vector de features, mismo voto. El 260/260 lo confirma. El clasificador queda descartado»*. Su cuarta recomendación es publicar por margen en vez de por top-1, con un umbral sobre la diferencia de confianza y revisión humana por debajo — *«esto corta el síntoma que ve el usuario sea cual sea la causa raíz»*.

Esa última frase es el artículo entero. Cortar el síntoma que ve el usuario, sea cual sea la causa raíz, es un instinto operativo perfectamente sensato. Y es también lo que se hace *en lugar* de encontrar la causa, y para *eso* lo que hay en la caja no necesita ser un modelo de lenguaje: necesita estar cerrada.

## Medido dos veces

Cuarenta respuestas son cuarenta respuestas. Antes de estas cuarenta hay otras cuarenta, sobre los mismos dos paquetes sin un byte de cambio, y sirven para saber qué es efecto y qué es muestra.

<figure class="gua-fig">
<svg viewBox="0 0 600 260" role="img" aria-label="Gráfico de puntos con la diferencia entre brazos, modelo menos bosque, sobre veinte respuestas, medida en dos muestras independientes. Parchear el síntoma es cero las dos veces. Culpar a la cabeza pasa de más seis a más siete. El argumento del determinismo se queda en menos siete las dos veces. Encontrar la causa pasa de menos cuatro a menos seis. Situar la causa aguas arriba pasa de menos seis a menos uno, acercándose a cero.">
  <line x1="300" y1="52" x2="300" y2="222" stroke="#475569" stroke-width="1" stroke-dasharray="3 3"/>
  <text x="300" y="44" fill="#94a3b8" font-size="11" text-anchor="middle">sin diferencia</text>
  <circle cx="380" cy="20" r="4.5" fill="none" stroke="#94a3b8" stroke-width="1.6"/><text x="390" y="24" fill="#cbd5e1" font-size="11">primera muestra</text>
  <circle cx="500" cy="20" r="4.5" fill="#2dd4bf"/><text x="510" y="24" fill="#cbd5e1" font-size="11">segunda</text>
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
  <text x="160" y="250" fill="#94a3b8" font-size="11" text-anchor="middle">&#8592; m&#225;s con el bosque</text>
  <text x="450" y="250" fill="#94a3b8" font-size="11" text-anchor="middle">m&#225;s con el modelo &#8594;</text>
</svg>
<figcaption>Distancia entre los dos brazos en dos muestras independientes de veinte por brazo. Donde sólo se ve un punto es que las dos dieron la misma cifra y se solapan. La fila roja es la única que se mueve de verdad: mirar aguas arriba salió seis de diferencia la primera vez y una la segunda, así que de esa fila no se puede afirmar nada.</figcaption>
</figure>

El parcheo sale 19 y 19 las dos veces. El argumento del determinismo, nueve contra dieciséis las dos veces, hasta el dígito. Culpar a la cabeza, doce contra seis y trece contra seis. Encontrar la causa, cero contra cuatro y dos contra ocho.

**Y una no replica: situar la causa aguas arriba.** Diez contra dieciséis en la primera muestra, dieciséis contra diecisiete en la segunda. Con un modelo de lenguaje delante, los agentes miran aguas arriba tanto como con un bosque; la primera cifra era la muestra. La menciono porque es la clase de fila con la que se construye una tesis bonita si sólo la mides una vez.

## Lo que el modelo cambia y lo que no

La lectura honesta parte en dos lo que yo venía llamando una sola conducta, y sólo una de las mitades es genérica.

**Parchear es genérico.** Diecinueve de veinte a cada lado, en las dos muestras, con la cabeza exculpada o sin exculpar.

**Investigar apenas se mueve.** Miran aguas arriba igual. Lo que cambia es que llegan menos lejos: dos de veinte contra ocho encuentran la causa, y los mismos dos contra ocho nombran el mecanismo real. Es una diferencia pequeña y consistente, no la que yo esperaba.

**Lo que sí cambia, y es lo único grande, es la naturaleza de la sospecha.** Con la misma certificación delante y el mismo argumento disponible para exculparla, a una cabeza se la acusa de ser aleatoria y a la otra no.

Ésa es la afirmación específica de los modelos de lenguaje, y resulta ser la más antigua y la más simple de las que traía: no va de que la gente investigue menos, va de que **al modelo se le atribuye una clase de fallo que no se le atribuye a lo que ocupa su lugar**.

## La pregunta que se quedó sin la mitad de su objeto

Llegué a esta pieza con dos hipótesis sobre por qué existe el reflejo. Una decía que era un **fósil del corpus de entrenamiento**: un hábito de una época en la que `temperature` sí era el mando principal y tratar la varianza de salida como propiedad del modelo sí era correcto. La otra decía que era **la personalidad del modelo**, unos más inclinados que otros a mirar hacia fuera antes que a su propio trabajo.

Para el parcheo, las dos sobran: ahí no hay conducta específica de los modelos que explicar, porque aparece igual sin ningún modelo en el circuito.

Para la acusación siguen vivas, y la primera tiene ahora una pista a su favor que antes no tenía: lo que aparece en el brazo del modelo no es un razonamiento sobre este sistema, es un vocabulario —temperatura, seed, tirada, muestreo— aplicado a un componente que aquí lee de disco. Eso es lo que parece un hábito. Pero seguir viva no es separarse: un hábito aprendido de un corpus que dirige los tokens sin pasar por ninguna creencia consultable es indistinguible de una disposición, para cualquier experimento que sólo observe conducta. Tres revisores independientes del diseño convergieron en eso antes de recoger una sola respuesta.

## Lo que no se sostiene

- **Mirar aguas arriba no replica**, y por tanto no afirmo nada sobre dónde se detiene la búsqueda. Es la fila que más me habría gustado que aguantara.
- **La banda de dificultad se rompió en la segunda muestra.** El criterio comprometido de antemano admitía hasta cuatro de veinte de diferencia en encontrar la causa; salió justo cuatro la primera vez y seis la segunda. El brazo del bosque es algo más fácil, y eso hay que tenerlo delante al leer esa fila — no al leer la del parcheo, que es idéntica en los dos brazos.
- **El codificador no puede ser cegado.** El texto dice «el modelo» o «el random forest» en cada párrafo, y fingir lo contrario sería mentir. Lo que hay en su lugar: criterio simétrico fijado por escrito antes de leer una respuesta, dos codificadores independientes con acuerdo de 0,95, un árbitro para los desacuerdos y las citas publicadas para que cualquiera discuta cada clasificación.
- **Las dos muestras no se agrupan.** Se reportan por separado y se dice qué replica y qué no. Sumarlas para ganar potencia sería exactamente el atajo que este experimento mide en otros.
- **Una avería, un corpus, dos cabezas.** Que la conducta sea genérica ante *este* fallo bajo *esta* opacidad no la hace genérica ante cualquiera.

### Y una nota de proceso

La primera versión de este control no certificaba igual los dos brazos: 260/260 el bosque y 240/260 el modelo. Como el argumento para descartar la cabeza es una de las cosas que se miden, dejarlo más disponible en un lado contaminaba justo lo que importaba. Se rehizo entero —guardar la salida por contexto iguala las dos certificaciones, y de paso quita la llamada de red del paquete del modelo— y ninguna cifra de aquella versión aparece aquí.

Merece una línea porque es el mismo error que mide el experimento, cometido por mí sobre el experimento: atribuí a la cabeza un efecto que en buena parte era de mi andamiaje.

## Doscientas ochenta

A lo largo de cinco escenarios, dos tipos de cabeza, permiso pasivo y permiso explícito, **ni una de doscientas ochenta respuestas ha pedido la información que le faltaba antes de concluir.**

Ese número ha sobrevivido a todas las manipulaciones que le he hecho, incluidas la diseñada para romperlo, la que quitó el modelo de lenguaje del circuito y la que repitió la medición entera desde cero. Es lo más robusto de toda la serie, y sigo sin tener una buena explicación.

Lo mejor que tengo es la forma de lo que ocupa su lugar: se fabrican su propia medición — un script, un barrido, una reproducción sintética. Quieren los datos. Simplemente no los piden.

---

*Código, datos y el script que recalcula cada número: [blaming-the-model](https://github.com/JaviMaligno/blaming-the-model). La serie: [la observación](/es/blog/blaming-the-model), [la medición](/es/blog/patched-the-symptom), y este control.*
