---
title: "Sabían que no era el modelo. Lo parchearon igual."
description: "Cambié el modelo de lenguaje por un random forest y pasé el mismo pipeline averiado por cuarenta agentes. Todos parchearon el síntoma en los dos casos — pero con el modelo en la caja, no encontró la causa nadie. Parchear es genérico; investigar no."
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

Los dos encargos llevan una certificación medida, y es la pieza que hace justa la comparación: *«re-ejecutar la clasificación sobre el mismo contexto reprodujo la salida en X de 20 casos»* — 260/260 el bosque, 240/260 el modelo, los números reales. Sin ella, un agente ante el bosque podría razonar, con toda la razón, que un bosque entrenado es determinista y que por tanto la causa está aguas arriba, y parchearía menos por un buen motivo en vez de por uno revelador.

Cuarenta agentes vieron la tabla sin el código, veinte por brazo.

## Lo que pasó

| | modelo de lenguaje | random forest | p |
|---|---|---|---|
| **Parchea el síntoma** | **20/20** | **20/20** | 1,00 |
| Culpa a la cabeza | 19/20 | 9/20 | **0,0006** |
| Usa el argumento del determinismo | 2/20 | 17/20 | **<0,0001** |
| Sitúa la causa aguas arriba | 7/20 | 15/20 | 0,012 |
| Encuentra la causa real | 0/20 | 5/20 | 0,024 |
| Pide los datos que le faltan | 0/20 | 0/20 | — |

Cuarenta de cuarenta parchearon el síntoma. Intervalo de Wilson [0,91, 1,00].

Ésa es la fila que vi primero, y la que rompe el marco que yo traía. Pero no es la única historia de la tabla, y el resto merece algo más que un encogimiento de hombros — porque las otras cuatro filas no son cuatro medidas sueltas. Son una cadena.

Con el modelo en la caja, la sospecha se queda en la caja: diecinueve de veinte la culpan. Sólo siete de veinte miran aguas arriba siquiera. **Nadie encuentra la causa.**

Con el bosque en la caja, lo exculpan — diecisiete de veinte argumentan explícitamente que un random forest entrenado es una función pura, que la certificación lo demuestra, que el clasificador queda descartado. Quince miran entonces aguas arriba. Cinco encuentran la causa.

Así que cambiar la cabeza no cambia si parchean. Cambia **dónde miran, y si llegan**. Un modelo de lenguaje en el circuito absorbe la sospecha, y la investigación se detiene justo en lo que sospecha.

Y a continuación, habiendo exculpado la caja, la parchean igual.

<figure class="gua-fig">
<svg viewBox="0 0 600 310" role="img" aria-label="Gráfico de barras con cinco medidas sobre veinte respuestas por brazo. Parchear el síntoma es veinte en ambos. Culpar a la cabeza es diecinueve con el modelo y nueve con el bosque; el argumento del determinismo dos y diecisiete; mirar aguas arriba siete y quince; encontrar la causa cero y cinco.">
  <rect x="366" y="12" width="12" height="12" fill="#2dd4bf"/><text x="384" y="22" fill="#cbd5e1" font-size="12">modelo de lenguaje</text>
  <rect x="366" y="30" width="12" height="12" fill="#f59e0b"/><text x="384" y="40" fill="#cbd5e1" font-size="12">random forest</text>
  <text x="20" y="22" fill="#94a3b8" font-size="12">sobre 20 respuestas por brazo</text>
  <text x="20" y="76" fill="#e2e8f0" font-size="13">parchea el síntoma</text>
  <rect x="210" y="64" width="330" height="14" rx="2" fill="#2dd4bf"/><text x="548" y="76" fill="#5eead4" font-size="12">20</text>
  <rect x="210" y="82" width="330" height="14" rx="2" fill="#f59e0b"/><text x="548" y="94" fill="#fbbf24" font-size="12">20</text>
  <text x="20" y="124" fill="#e2e8f0" font-size="13">culpa a la cabeza</text>
  <rect x="210" y="112" width="314" height="14" rx="2" fill="#2dd4bf"/><text x="532" y="124" fill="#5eead4" font-size="12">19</text>
  <rect x="210" y="130" width="148" height="14" rx="2" fill="#f59e0b"/><text x="366" y="142" fill="#fbbf24" font-size="12">9</text>
  <text x="20" y="172" fill="#e2e8f0" font-size="13">&#171;es determinista&#187;</text>
  <rect x="210" y="160" width="33" height="14" rx="2" fill="#2dd4bf"/><text x="251" y="172" fill="#5eead4" font-size="12">2</text>
  <rect x="210" y="178" width="280" height="14" rx="2" fill="#f59e0b"/><text x="498" y="190" fill="#fbbf24" font-size="12">17</text>
  <text x="20" y="220" fill="#e2e8f0" font-size="13">mira aguas arriba</text>
  <rect x="210" y="208" width="115" height="14" rx="2" fill="#2dd4bf"/><text x="333" y="220" fill="#5eead4" font-size="12">7</text>
  <rect x="210" y="226" width="248" height="14" rx="2" fill="#f59e0b"/><text x="466" y="238" fill="#fbbf24" font-size="12">15</text>
  <text x="20" y="268" fill="#e2e8f0" font-size="13">encuentra la causa</text>
  <rect x="210" y="256" width="2" height="14" rx="2" fill="#2dd4bf"/><text x="220" y="268" fill="#5eead4" font-size="12">0</text>
  <rect x="210" y="274" width="82" height="14" rx="2" fill="#f59e0b"/><text x="300" y="286" fill="#fbbf24" font-size="12">5</text>
</svg>
<figcaption>La fila de arriba es la misma barra dos veces: al parcheo le da igual lo que haya en la caja. Todas las de abajo se mueven, y en la misma dirección — con un modelo de lenguaje dentro, la sospecha se queda en la cabeza, menos gente mira más allá, y nadie llega.</figcaption>
</figure>

## La disociación

Éste es el hallazgo, y aguanta el corte más estricto que le puedo hacer.

De las veinte respuestas frente al bosque, **diecisiete usaron el argumento del determinismo. Las diecisiete propusieron un parche igualmente.** Once exculparon a la cabeza sin reservas. Las once parchearon también.

Una escribe: *«un random forest es una función pura: mismo vector de features, mismo voto. El 260/260 lo confirma. El clasificador queda descartado»*. Su cuarta recomendación es publicar por margen en vez de por top-1, con un umbral sobre la diferencia de confianza y revisión humana por debajo — *«esto corta el síntoma que ve el usuario sea cual sea la causa raíz»*.

Esa última frase es el artículo entero. Cortar el síntoma que ve el usuario, sea cual sea la causa raíz, es un instinto operativo perfectamente sensato. Y es también lo que se hace *en lugar* de encontrar la causa, y para *eso* lo que hay en la caja no necesita ser un modelo de lenguaje: necesita estar cerrada.

Lo que añade el modelo de lenguaje es la otra mitad: un sitio plausible donde la sospecha se puede quedar a descansar. El bosque no ofrece ese descanso, así que nueve de veinte lo culpan igual pero quince se van a mirar aguas arriba. El modelo ofrece uno excelente, y miran siete.

## Lo que el modelo cambia y lo que no

La lectura honesta de esta tabla es que parte en dos lo que yo venía llamando una sola conducta, y sólo una de las mitades es genérica.

**Parchear es genérico.** Le da igual lo que haya en la caja. Sea lo que sea lo que empuja a un ingeniero a suavizar una salida en vez de rastrearla, un modelo de lenguaje no es requisito: un componente opaco sí.

**Investigar no lo es.** Cada paso de la cadena diagnóstica se mueve al cambiar la cabeza, y todos en la misma dirección: atribución a la cabeza (19/20 → 9/20), mirar aguas arriba (7/20 → 15/20), llegar a la causa (0/20 → 5/20). El modelo no hace que la gente parchee. Hace que se detenga en el modelo.

Esa segunda mitad es la afirmación específica de los LLM, y sobrevive — en una forma más afilada que la que yo traía. La tesis original iba de *lo que el agente dice*: culpa al modelo. Lo que los datos sostienen va de *dónde se para el agente*: el modelo de lenguaje actúa como sumidero de la sospecha, y la búsqueda termina en lo sospechado. En el brazo del modelo no encontró la causa nadie. Ni uno.

## La pregunta que se quedó sin la mitad de su objeto

Llegué a esta pieza con dos hipótesis sobre por qué existe el reflejo. Una decía que era un **fósil del corpus de entrenamiento**: un hábito de una época en la que `temperature` sí era el mando principal y tratar la varianza de salida como propiedad del modelo sí era correcto. La otra decía que era **la personalidad del modelo**, unos más inclinados que otros a mirar hacia fuera antes que a su propio trabajo.

Para el parcheo, las dos sobran: ahí no hay conducta específica de los modelos que explicar, porque aparece igual sin ningún modelo en el circuito.

Para la atribución siguen vivas, y este diseño no puede separarlas — cosa que ya era cierta antes de correr nada. Un hábito aprendido de un corpus que dirige los tokens sin pasar por ninguna creencia consultable es indistinguible de una disposición, para cualquier experimento que sólo observe conducta. Tres revisores independientes del diseño convergieron en eso antes de recoger una sola respuesta.

## Lo que no se sostiene

- **La banda de dificultad se rompió por una unidad, y es ambiguo cómo leerlo.** El criterio comprometido de antemano admitía hasta 4/20 de diferencia en encontrar la causa; salió 5/20. Una lectura es que el brazo del bosque es sencillamente *más fácil*, y entonces es un defecto de pareado — nótese que la dirección sigue jugando en contra del resultado del parcheo, porque una tarea más fácil debería producir menos parcheo, no el mismo. La otra lectura es que no es un defecto sino el hallazgo mismo: el 0/20 es lo que pasa cuando la sospecha tiene dónde pararse cómodamente. Las otras tres filas de la cadena son coherentes con la segunda, pero este diseño no puede separarlas, y no voy a elegir la que me conviene.
- **La certificación neutralizó menos de lo previsto.** 260/260 contra 240/260 se sigue leyendo como «perfecto» frente a «no del todo», y diecisiete de veinte razonaron justamente desde ahí. De cerca, el fallo del modelo es un único contexto de trece: doce reprodujeron 20/20, y el que no dio la misma etiqueta las veinte veces.
- **El brazo con código no es limpio del lado del modelo**: su fichero de cabeza contiene la llamada de red, un culpable legítimo que el bosque no tiene. Falsearlo sería mentir sobre el sistema. La comparación que porta es la de sin código.
- **Una avería, un corpus, dos cabezas.** Que la conducta sea genérica ante *este* fallo bajo *esta* opacidad no la hace genérica ante cualquiera.

## Doscientas

A lo largo de cinco escenarios, dos tipos de cabeza, permiso pasivo y permiso explícito, **ni una de doscientas respuestas ha pedido la información que le faltaba antes de concluir.**

Ese número ha sobrevivido ya a todas las manipulaciones que le he hecho, incluida la diseñada para romperlo y la que quitó el modelo de lenguaje del todo. Es lo más robusto de toda la serie, y sigo sin tener una buena explicación.

Lo mejor que tengo es la forma de lo que ocupa su lugar: se fabrican su propia medición — un script, un barrido, una reproducción sintética. Quieren los datos. Simplemente no los piden.

---

*Código, datos y el script que recalcula cada número: [blaming-the-model](https://github.com/JaviMaligno/blaming-the-model). La serie: [la observación](/es/blog/blaming-the-model), [la medición](/es/blog/patched-the-symptom), y este control.*
