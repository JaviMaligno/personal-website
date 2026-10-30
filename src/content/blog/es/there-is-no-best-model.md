---
title: "No hay mejor modelo, solo una frontera"
description: "Ningún modelo gana a la vez en coste, calidad y velocidad: hay una frontera de modelos que no pierden en todo frente a otro. Cómo leerla, por qué medirla por tarea y no por token, cómo tratar la calidad como umbral y por qué me llevó a no cambiar a un modelo más rápido."
pubDate: 2026-11-29
tags: ["IA", "LLM", "Economía", "Evaluación", "Ingeniería"]
lang: es
translationKey: there-is-no-best-model
heroImage: "/blog/there-is-no-best-model.png"
---

<style>
.ptf-fig { margin: 2rem 0; }
.ptf-fig svg { width: 100%; height: auto; display: block; background: #1a1a24; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; }
.ptf-fig figcaption { color: #94a3b8; font-size: 0.9rem; margin-top: 0.6rem; line-height: 1.5; }
</style>

Hace unas semanas probé un modelo más nuevo en el [Industry Classifier](/es/projects/compliance-classifier), el agente que busca una empresa en la web, comprueba que es la correcta y le asigna un código de actividad. El servicio funciona con `gpt-6-luna`. El candidato era `gpt-6.1-terra`, publicado pocos días antes.

El resultado, en una línea: **terra era claramente más rápido, más caro, y no vi ninguna diferencia de calidad.** ¿Es mejor modelo? La respuesta honesta es que la pregunta está mal planteada. Depende de qué paga mi servicio, y la forma útil de pensarlo tiene nombre: la frontera de Pareto.

## La idea en un dibujo

Elegir un modelo es repartir al menos tres cosas: lo buenas que son las respuestas, lo que cuestan y lo que tardan. Rara vez un modelo gana en las tres.

Un modelo **domina** a otro cuando es al menos igual de bueno en todos los ejes y estrictamente mejor en alguno: misma calidad y más barato, o mejor y no más lento. Un modelo dominado se descarta sin discusión, porque para cualquier prioridad que tengas hay una opción mejor. Los modelos a los que nadie domina forman la **frontera de Pareto**.

<figure class="ptf-fig">
<svg viewBox="0 0 600 340" role="img" aria-label="Calidad frente a coste por tarea. Cuatro modelos forman la frontera, dibujada como una escalera que sube rápido al principio y se aplana arriba. Todo lo que queda por debajo y a la derecha de la escalera es la zona dominada; dentro hay dos modelos dominados, a cada uno le gana en coste y en calidad un modelo de la frontera.">
  <g font-family="system-ui,-apple-system,sans-serif">
    <path d="M110,290 L110,250 L220,250 L220,150 L330,150 L330,108 L500,108 L500,92 L570,92 L570,290 Z" fill="rgba(148,163,184,0.09)"/>
    <line x1="70" y1="290" x2="570" y2="290" stroke="#64748b" stroke-width="1.4"/>
    <line x1="70" y1="290" x2="70" y2="30" stroke="#64748b" stroke-width="1.4"/>
    <text x="320" y="322" text-anchor="middle" fill="#94a3b8" font-size="12">coste por tarea →</text>
    <text x="30" y="160" text-anchor="middle" fill="#94a3b8" font-size="12" transform="rotate(-90 30 160)">calidad →</text>
    <path d="M110,290 L110,250 L220,250 L220,150 L330,150 L330,108 L500,108 L500,92 L570,92" stroke="#2dd4bf" stroke-width="2" fill="none"/>
    <circle cx="110" cy="250" r="7" fill="#2dd4bf"/>
    <circle cx="220" cy="150" r="7" fill="#2dd4bf"/>
    <circle cx="330" cy="108" r="7" fill="#2dd4bf"/>
    <circle cx="500" cy="92" r="7" fill="#2dd4bf"/>
    <text x="98" y="244" text-anchor="end" fill="#5eead4" font-size="12">pequeño</text>
    <text x="208" y="146" text-anchor="end" fill="#5eead4" font-size="12">mediano</text>
    <text x="318" y="104" text-anchor="end" fill="#5eead4" font-size="12">grande</text>
    <text x="488" y="86" text-anchor="end" fill="#5eead4" font-size="12">insignia</text>
    <circle cx="300" cy="215" r="7" fill="none" stroke="#94a3b8" stroke-width="2"/>
    <circle cx="460" cy="165" r="7" fill="none" stroke="#94a3b8" stroke-width="2"/>
    <text x="300" y="240" text-anchor="middle" fill="#94a3b8" font-size="11.5">dominado</text>
    <text x="460" y="190" text-anchor="middle" fill="#94a3b8" font-size="11.5">dominado</text>
    <text x="470" y="275" text-anchor="middle" fill="#64748b" font-size="12" font-style="italic">zona dominada</text>
    <text x="268" y="140" text-anchor="middle" fill="#94a3b8" font-size="11">codo</text>
    <circle cx="96" cy="44" r="5" fill="#2dd4bf"/>
    <text x="108" y="48" fill="#e2e8f0" font-size="11.5">frontera: nada es más barato y mejor a la vez</text>
    <circle cx="96" cy="64" r="5" fill="none" stroke="#94a3b8" stroke-width="1.6"/>
    <text x="108" y="68" fill="#94a3b8" font-size="11.5">dominado: algo es más barato y mejor</text>
  </g>
</svg>
<figcaption>La frontera es la escalera: para cada modelo que está en ella, nada es a la vez más barato y mejor. Todo lo que cae en la zona sombreada está dominado y sale de la discusión. A lo largo de la frontera no hay ganador técnico, solo un intercambio, y pasado el codo cada unidad extra de calidad cuesta mucho más que la anterior.</figcaption>
</figure>

Del dibujo salen dos cosas.

La primera es que la frontera resuelve muchas discusiones gratis. Si en tus mediciones un modelo está dominado, no hay nada que hablar.

La segunda es la contraria: **entre dos puntos de la frontera, ninguna medición decide.** Moverse por ella es comprar una cosa con otra, y cuánto estás dispuesto a pagar es una preferencia de negocio, no un hecho técnico. El trabajo de ingeniería es dibujar la frontera con honestidad. La elección del punto le corresponde a quien sabe cuánto cuesta un segundo de espera, un céntimo por tarea o una respuesta equivocada.

Hay además una forma que conviene buscar: el **codo**. Las fronteras suelen subir rápido y luego aplanarse. Pasado el codo, pagar el doble compra un poco más de calidad, y para muchos usos ese poco no compensa.

## Coste por tarea, no por token

El eje que todo el mundo mira primero es la tarifa: dólares por millón de tokens de entrada y de salida. En la tarifa, terra costaba **diez veces** más que luna. Si hubiera dibujado la frontera con ella, la conversación habría terminado ahí.

Pero no es lo que pago. Lo que paga el servicio es el coste de **una clasificación**: unas diez llamadas al modelo, varias búsquedas web, verificación de páginas. Hice una prueba corta y pareada: tres empresas reales de un cliente, dos rondas cada una, los dos modelos intercalados y compartiendo la misma caché de búsquedas, así que la evidencia era la misma para ambos. Medido por clasificación:

| | gpt-6-luna | gpt-6.1-terra |
|---|---:|---:|
| Precio por token (relativo) | 1× | 10× |
| Coste del modelo por clasificación | 0,0039 \$ | 0,0250 \$ |
| Búsquedas web de pago por clasificación | 5,67 | 5,67 |
| **Coste total por clasificación** | **0,096 \$** | **0,118 \$** |
| Mediana de tiempo por clasificación | 82 s | 55 s |
| Código principal correcto | 6 / 6 | 6 / 6 |

<figure class="ptf-fig">
<svg viewBox="0 0 600 320" role="img" aria-label="Terra frente a luna, en tres pasos. Precio por token: diez veces. Coste de modelo por clasificación: 6,4 veces, 0,025 frente a 0,0039 dólares, porque terra gasta menos tokens. Coste total por clasificación: 1,23 veces, 0,118 frente a 0,096 dólares, porque el modelo es una parte pequeña de lo que cuesta una clasificación.">
  <g font-family="system-ui,-apple-system,sans-serif">
    <text x="100" y="34" text-anchor="middle" fill="#f8fafc" font-size="13.5" font-weight="600">Precio por token</text>
    <line x1="20" y1="250" x2="180" y2="250" stroke="#64748b" stroke-width="1.2"/>
    <rect x="45" y="232" width="45" height="18" fill="#2dd4bf"/>
    <rect x="110" y="70" width="45" height="180" fill="#f59e0b"/>
    <text x="67.5" y="224" text-anchor="middle" fill="#5eead4" font-size="12">1×</text>
    <text x="132.5" y="62" text-anchor="middle" fill="#fbbf24" font-size="13" font-weight="600">10×</text>
    <text x="67.5" y="268" text-anchor="middle" fill="#94a3b8" font-size="12">luna</text>
    <text x="132.5" y="268" text-anchor="middle" fill="#94a3b8" font-size="12">terra</text>
    <text x="67.5" y="286" text-anchor="middle" fill="#94a3b8" font-size="11">0,50 $/M</text>
    <text x="132.5" y="286" text-anchor="middle" fill="#94a3b8" font-size="11">5 $/M</text>
    <text x="100" y="302" text-anchor="middle" fill="#64748b" font-size="10.5">precio de salida</text>
    <text x="200" y="160" text-anchor="middle" fill="#64748b" font-size="20">→</text>
    <text x="300" y="34" text-anchor="middle" fill="#f8fafc" font-size="13.5" font-weight="600">Coste modelo / tarea</text>
    <line x1="220" y1="250" x2="380" y2="250" stroke="#64748b" stroke-width="1.2"/>
    <rect x="245" y="232" width="45" height="18" fill="#2dd4bf"/>
    <rect x="310" y="134.8" width="45" height="115.2" fill="#f59e0b"/>
    <text x="267.5" y="224" text-anchor="middle" fill="#5eead4" font-size="12">1×</text>
    <text x="332.5" y="126.8" text-anchor="middle" fill="#fbbf24" font-size="13" font-weight="600">6,4×</text>
    <text x="267.5" y="268" text-anchor="middle" fill="#94a3b8" font-size="12">luna</text>
    <text x="332.5" y="268" text-anchor="middle" fill="#94a3b8" font-size="12">terra</text>
    <text x="267.5" y="286" text-anchor="middle" fill="#94a3b8" font-size="11">0,0039 $</text>
    <text x="332.5" y="286" text-anchor="middle" fill="#94a3b8" font-size="11">0,025 $</text>
    <text x="400" y="160" text-anchor="middle" fill="#64748b" font-size="20">→</text>
    <text x="500" y="34" text-anchor="middle" fill="#f8fafc" font-size="13.5" font-weight="600">Coste total / tarea</text>
    <line x1="420" y1="250" x2="580" y2="250" stroke="#64748b" stroke-width="1.2"/>
    <rect x="445" y="232" width="45" height="18" fill="#2dd4bf"/>
    <rect x="510" y="227.9" width="45" height="22.1" fill="#f59e0b"/>
    <text x="467.5" y="224" text-anchor="middle" fill="#5eead4" font-size="12">1×</text>
    <text x="532.5" y="219.9" text-anchor="middle" fill="#fbbf24" font-size="13" font-weight="600">1,23×</text>
    <text x="467.5" y="268" text-anchor="middle" fill="#94a3b8" font-size="12">luna</text>
    <text x="532.5" y="268" text-anchor="middle" fill="#94a3b8" font-size="12">terra</text>
    <text x="467.5" y="286" text-anchor="middle" fill="#94a3b8" font-size="11">0,096 $</text>
    <text x="532.5" y="286" text-anchor="middle" fill="#94a3b8" font-size="11">0,118 $</text>
  </g>
</svg>
<figcaption>El mismo cambio medido de tres formas. El multiplicador baja de 10× a 6,4× al contar los tokens que gasta de verdad cada modelo, y a 1,23× al contar todo lo demás que paga una clasificación.</figcaption>
</figure>

Diez veces por token se quedaron en **un 23 % más por tarea**, en dos pasos.

**De 10× a 6,4×: los tokens.** Terra llega en menos vueltas (4,8 iteraciones del agente por clasificación frente a 5,5) y piensa mucho menos por el camino: una quinta parte de su salida es razonamiento, frente a la mitad en luna. Genera 1.362 tokens de salida por clasificación frente a los 2.540 de luna. Así que su factura de modelo creció 6,4×, no 10×.

**De 6,4× a 1,23×: todo lo demás.** Con luna, el modelo es apenas un 4 % de lo que cuesta una clasificación. El grueso es la búsqueda web: los dos modelos hicieron exactamente las mismas búsquedas de pago, 5,67 por clasificación a 0,016 \$ cada una, unos nueve céntimos. Multiplicar por seis el cuatro por ciento de la factura es una subida moderada de la factura entera.

### Lo que cuesta una búsqueda en tokens

La tarifa de la búsqueda no es todo lo que cuesta una búsqueda. Lo que devuelve, el modelo tiene que leerlo, y el modelo cobra por leer. Unos dos tercios de lo que lee el agente en una clasificación es material de búsquedas y páginas: las búsquedas de apertura van en el primer mensaje y se reenvían enteras en cada llamada (casi todo sale de la caché), y cada resultado de una búsqueda que lanza el propio agente viaja entero en todas las llamadas siguientes hasta la próxima.

Poniéndole precio a una búsqueda más, aparte de su tarifa: si le cuesta al agente una vuelta más, esa vuelta son unos 0,0003-0,0005 \$ de tokens con luna y **0,003-0,004 \$ con terra**. Con luna, la tarifa de la búsqueda pesa de 30 a 50 veces más que leer el resultado. Con terra, solo cuatro o cinco veces más. El precio del modelo multiplica el coste de todo lo que lee, así que un modelo más caro también encarece sus búsquedas.

Aquí los dos buscaron lo mismo. No está garantizado: cuando [probé el cambio de modelo anterior en este servicio](/es/blog/the-new-model-is-cheaper), el modelo nuevo buscaba un 12 % más que el viejo. El comportamiento de un modelo mueve costes que no factura él, y eso la tarifa no lo puede enseñar.

La regla general es la que pondría al principio de cualquier comparación de modelos: **dibuja la frontera con el coste y la latencia de la tarea completa en tu sistema, no con la tarifa.** Un modelo barato por token y verboso puede salir caro por tarea. Uno caro por token y conciso puede salir más barato de lo que parece. Y si el modelo es una parte pequeña de tu coste, su precio importa menos que su efecto sobre todo lo demás.

## Tres ejes, y la calidad como umbral

El primer dibujo tiene dos ejes, y el problema tiene tres. Se pueden dibujar los tres, y hacerlo enseña algo: con tres ejes casi nadie está dominado. A un modelo le basta con ser el mejor en una cosa, o en una combinación, para sobrevivir. Cuantos más ejes, más grande la frontera y menos descarta la dominancia por sí sola.

En la práctica, la calidad suele jugar un papel distinto de los otros dos. Antes que una cantidad que intercambiar, es una condición: el modelo tiene que poder hacer la tarea. Un clasificador que falla la mitad de los códigos no es una opción barata, no es una opción. Así que la forma útil de manejar los tres ejes suele ser un **umbral**: fijas un suelo de calidad, descartas lo que no llega y dibujas la frontera entre coste y latencia con lo que pasa.

Mi servicio tiene ese umbral por escrito. Antes de cualquier cambio en el modelo o en su arnés hay unos límites aprobados: entre otros, ninguna regresión estable (casos que el cambio falla en todas las rondas y que la versión actual acertaba en todas) más allá de las que muestra el propio control. En octubre medí el propio `gpt-6-luna` a tres niveles de razonamiento, sobre 38 casos de un banco elegidos a propósito por difíciles: casos en los que el modelo había encontrado la empresa correcta pero había fallado el código o discrepado del modelo anterior. Cuatro rondas cada uno. En esos casos el acierto absoluto es bajo por construcción; lo que importa es la diferencia entre niveles:

<figure class="ptf-fig">
<svg viewBox="0 0 600 330" role="img" aria-label="El mismo modelo a tres niveles de razonamiento, coste relativo al nivel por defecto frente a tiempo mediano. Low es un 29 por ciento más barato y 16 segundos más rápido, pero acierta 9 puntos menos, con dos regresiones estables, así que no pasa el umbral de calidad. High es un 16 por ciento más caro y 11 segundos más lento con el mismo acierto dentro del ruido, así que el nivel por defecto lo domina. Solo queda el nivel por defecto.">
  <g font-family="system-ui,-apple-system,sans-serif">
    <line x1="80" y1="290" x2="570" y2="290" stroke="#64748b" stroke-width="1.4"/>
    <line x1="80" y1="290" x2="80" y2="40" stroke="#64748b" stroke-width="1.4"/>
    <text x="325" y="322" text-anchor="middle" fill="#94a3b8" font-size="12">coste por clasificación, relativo al defecto →</text>
    <text x="30" y="165" text-anchor="middle" fill="#94a3b8" font-size="12" transform="rotate(-90 30 165)">tiempo mediano (s) →</text>
    <g fill="#94a3b8" font-size="11" text-anchor="middle">
      <text x="150" y="306">−30 %</text><text x="360" y="306">defecto</text><text x="500" y="306">+20 %</text>
    </g>
    <g fill="#94a3b8" font-size="11" text-anchor="end">
      <text x="72" y="234">40</text><text x="72" y="174">50</text><text x="72" y="114">60</text>
    </g>
    <g stroke="rgba(255,255,255,0.07)" stroke-width="1">
      <line x1="80" y1="230" x2="570" y2="230"/><line x1="80" y1="170" x2="570" y2="170"/><line x1="80" y1="110" x2="570" y2="110"/>
    </g>
    <circle cx="157" cy="242" r="12" fill="none" stroke="#f87171" stroke-width="2"/>
    <path d="M149,234 L165,250 M165,234 L149,250" stroke="#f87171" stroke-width="2"/>
    <text x="178" y="238" fill="#f87171" font-size="12.5" font-weight="600">low</text>
    <text x="178" y="254" fill="#94a3b8" font-size="11">−9 puntos de acierto · 2 regresiones estables</text>
    <text x="178" y="269" fill="#f87171" font-size="11">no pasa el umbral de calidad</text>
    <circle cx="360" cy="146" r="9" fill="#2dd4bf"/>
    <text x="376" y="150" fill="#5eead4" font-size="12.5" font-weight="600">defecto</text>
    <text x="376" y="166" fill="#94a3b8" font-size="11">acierto de referencia</text>
    <circle cx="472" cy="80" r="8" fill="none" stroke="#94a3b8" stroke-width="2"/>
    <text x="488" y="76" fill="#94a3b8" font-size="12.5" font-weight="600">high</text>
    <text x="488" y="92" fill="#94a3b8" font-size="11">−1 punto (ruido)</text>
    <text x="488" y="107" fill="#94a3b8" font-size="11">dominado</text>
  </g>
</svg>
<figcaption>El mismo modelo, tres ajustes, tres destinos distintos. Low es más barato y más rápido pero no pasa el umbral. High lo pasa, pero el nivel por defecto es más barato, más rápido y no peor. Solo queda el defecto. El acierto se muestra relativo al nivel por defecto: estos 38 casos se eligieron porque el modelo ya había fallado o discrepado en ellos, así que la tasa absoluta no dice nada del servicio.</figcaption>
</figure>

Con `low` el agente deja de investigar: lanza 1,2 búsquedas propias por clasificación en vez de 3,2, y muchas de sus respuestas son abstenciones sin haber comprobado ni una página. Es un 29 % más barato y 16 segundos más rápido, y no pasa el umbral. `high` lo pasa pero no compra nada: +16 % de coste y +20 % de latencia para el mismo acierto dentro del ruido. El nivel por defecto lo domina. Dos niveles descartados, uno por el umbral y otro por dominancia, y ninguno necesitó debate.

También muestra que un modelo no es un único punto del mapa. Cada nivel de razonamiento es un punto distinto, y también lo es cada prompt o arnés con el que lo combines. Lo que colocas en la frontera son configuraciones, no nombres de modelo. Eso multiplica los candidatos, y es una razón más para que el umbral y la medición por tarea sean baratos de repetir.

## Dónde se decide de verdad

Volvamos a terra. En calidad no vi diferencia: los dos modelos acertaron el código principal en los seis pares. Eso no demuestra que sean iguales. Seis pares en un banco donde cualquier modelo reciente pasa del 90 % no pueden separarlos. Pero los dos pasan el umbral, y por encima de él la decisión es entre coste y latencia: luna, más barato y más lento, y terra, más rápido y más caro. Los dos en la frontera.

La pregunta pasa a ser: ¿valen 27 segundos por clasificación 2,2 céntimos? Divide uno entre otro y sale el precio del intercambio: unos **0,0008 \$ por segundo ahorrado, unos 3 \$ por hora de espera**. Es la pendiente de la línea de la figura siguiente. Terra gana si para alguien un segundo de espera vale más que eso. Si no, gana luna.

<figure class="ptf-fig">
<svg viewBox="0 0 600 340" role="img" aria-label="Coste por clasificación frente a tiempo mediano. Luna queda más abajo y a la derecha, terra más arriba y a la izquierda. Tres líneas que pasan por luna representan distintos valores del segundo de espera: a un dólar la hora terra queda por encima y pierde, a unos tres dólares la hora empatan, a veinte dólares la hora terra queda por debajo y gana.">
  <g font-family="system-ui,-apple-system,sans-serif">
    <line x1="70" y1="300" x2="570" y2="300" stroke="#64748b" stroke-width="1.4"/>
    <line x1="70" y1="300" x2="70" y2="40" stroke="#64748b" stroke-width="1.4"/>
    <text x="320" y="330" text-anchor="middle" fill="#94a3b8" font-size="12">tiempo mediano por clasificación (s) →</text>
    <text x="24" y="170" text-anchor="middle" fill="#94a3b8" font-size="12" transform="rotate(-90 24 170)">coste por clasificación →</text>
    <g fill="#94a3b8" font-size="11" text-anchor="middle">
      <text x="140" y="316">40</text><text x="280" y="316">60</text><text x="420" y="316">80</text><text x="560" y="316">100</text>
    </g>
    <g fill="#94a3b8" font-size="11" text-anchor="end">
      <text x="64" y="267">0,08 $</text><text x="64" y="193">0,10 $</text><text x="64" y="118">0,12 $</text><text x="64" y="44">0,14 $</text>
    </g>
    <line x1="70" y1="149.4" x2="560" y2="222" stroke="#64748b" stroke-width="1.4" stroke-dasharray="5 4"/>
    <line x1="70" y1="46" x2="560" y2="258" stroke="#94a3b8" stroke-width="1.4" stroke-dasharray="5 4"/>
    <line x1="378.6" y1="40" x2="466.8" y2="300" stroke="#64748b" stroke-width="1.4" stroke-dasharray="5 4"/>
    <rect x="76" y="128" width="62" height="16" fill="#1a1a24"/>
    <text x="80" y="140" fill="#94a3b8" font-size="11">1 $ / h</text>
    <rect x="84" y="52" width="62" height="16" fill="#1a1a24"/>
    <text x="88" y="64" fill="#e2e8f0" font-size="11">3 $ / h</text>
    <rect x="384" y="28" width="66" height="16" fill="#1a1a24"/>
    <text x="388" y="40" fill="#94a3b8" font-size="11">20 $ / h</text>
    <circle cx="434" cy="203.4" r="8" fill="#2dd4bf"/>
    <circle cx="245" cy="121.7" r="8" fill="#f59e0b"/>
    <text x="420" y="234" text-anchor="end" fill="#5eead4" font-size="12.5" font-weight="600">luna</text>
    <text x="420" y="250" text-anchor="end" fill="#94a3b8" font-size="11">82 s · 0,096 $</text>
    <text x="196" y="104" fill="#fbbf24" font-size="12.5" font-weight="600">terra</text>
    <text x="196" y="88" fill="#94a3b8" font-size="11">55 s · 0,118 $</text>
  </g>
</svg>
<figcaption>Cada línea discontinua une los puntos que cuestan lo mismo que luna cuando el segundo de espera tiene precio. Por debajo de la línea se gana a luna; por encima, se pierde. Terra cae justo sobre la línea de 3 $/hora: que sea mejor modelo depende por completo de ese número.</figcaption>
</figure>

Planteado así, la decisión deja de ser sobre modelos y pasa a ser una pregunta que puedo hacer a quien usa el servicio: ¿hay alguien esperando esos 27 segundos, y cuánto cuesta esa espera? En este caso decidí parar: un 23 % más por clasificación sin mejora visible de calidad, con la latencia como único argumento a favor. Si algún día la clasificación entra en un flujo interactivo con alguien esperando delante de la pantalla, los mismos números darán otra respuesta, y solo tendré que volver a medir.

## Tres formas de equilibrar los ejes

Lo que hice arriba mezcla las tres formas prácticas de decidir dentro de una frontera. No son excluyentes.

- **Restricciones duras y luego optimizar un eje.** Escribe primero los límites: calidad no peor que la del modelo actual en tu banco, latencia p95 por debajo de X segundos, datos que no salen de cierta región. Entre lo que sobrevive, elige el más barato. Es lo más robusto porque no te obliga a ponerle precio a todo, y elimina muchos puntos antes de comparar nada. El umbral de calidad de la sección anterior es una de ellas.
- **Ponerle precio a lo que no es dinero.** Convierte latencia y errores en dólares: cuánto cuesta un segundo de espera, cuánto cuesta una respuesta equivocada que llega a una persona. Luego minimiza un solo número. Es lo que hice con los segundos. Te obliga a hacer explícitas las preferencias, lo que es incómodo y útil.
- **No elegir un único punto.** Enruta: el modelo barato por defecto y el caro solo para los casos que lo necesitan (confianza baja, entradas difíciles, un cliente con requisitos más estrictos). Tu punto efectivo queda entre los dos, en un sitio al que ninguno de los dos llega solo. El precio es complejidad, y el propio enrutador hay que evaluarlo.

## Benchmarks públicos: para preseleccionar, no para decidir

Hay fronteras públicas que vale la pena mirar. [Artificial Analysis](https://artificialanalysis.ai/models/comparisons) publica, para cada modelo, un índice agregado de inteligencia junto al precio por millón de tokens, la velocidad de salida, el tiempo hasta el primer token, el tiempo de respuesta completo y, lo importante, el **coste por tarea del índice** y el coste de correr el índice entero. Esa última métrica es la idea correcta: ya tiene en cuenta que un modelo escriba el doble que otro para resolver lo mismo. [Arena](https://arena.ai) ofrece también una vista de Pareto de precio frente a puntuación, y para agentes cruza la puntuación con el coste por tarea.

Sirven para dibujar un primer mapa y descartar lo claramente dominado. No pueden hacer tu elección, por la misma razón que la tarifa no podía hacer la mía. Sus tareas no son las tuyas. Su coste por tarea no incluye tus búsquedas, tus reintentos ni tu caché. En mi servicio el modelo es menos del 5 % del coste; en un benchmark es el 100 %. Usa la frontera pública para decidir qué tres o cuatro candidatos merece la pena medir, y dibuja la tuya con tus tareas.

## Self-hosted: otra frontera, con costes fijos

La pregunta de modelos abiertos frente a API es otro intercambio en los mismos ejes, con dos particularidades.

En calidad, la brecha sigue existiendo, aunque es menor que antes. [Epoch AI](https://epoch.ai/data-insights/open-closed-eci-gap) midió en mayo de 2026 que, desde enero, los mejores modelos de pesos abiertos van unos **cuatro meses** por detrás de los mejores cerrados en su índice agregado de capacidades, unos ocho puntos. Es más o menos la distancia entre GPT-5 y GPT-5.5. El propio Epoch avisa de que la cifra probablemente se queda corta, porque los laboratorios cerrados no siempre publican su mejor modelo. Cuatro meses no parece mucho, pero en una tarea saturada como la mía puede ser irrelevante, y en una difícil puede decidir si pasas el umbral.

En coste cambia la estructura. Una API cobra por uso: cero tareas, cero dólares. Una GPU propia cobra por hora, la uses o no. Tu coste por tarea es el coste por hora (la máquina, más quien la opera, la actualiza y se levanta cuando falla) dividido entre las tareas que de verdad haces por hora. Con volumen alto y constante, esa división puede ganar a cualquier API. Con volumen bajo es pésima. Como ilustración con números redondos: una GPU a un dólar la hora son más de 700 \$ al mes, y este servicio entero, con unas 500 clasificaciones al mes, cuesta unos 50 \$ al mes con luna. A este volumen el punto self-hosted ni aparece en el mapa.

Y servir un modelo tiene su propia frontera. Meter más peticiones por GPU baja el coste por token pero hace más lento a cada usuario: [InferenceX, de SemiAnalysis](https://inferencex.semianalysis.com/glossary/pareto-frontier), mapea exactamente ese intercambio entre throughput por GPU e interactividad. El self-hosting no te libra de elegir, te añade otra elección.

A veces el self-hosting no es un punto de la frontera sino una restricción: datos que no pueden salir de tu infraestructura. Entonces es otro umbral, uno que elimina el resto del mapa, y eliges en la frontera que queda.

## La frontera se mueve

Lo que menos me gusta de este ejercicio es también lo que lo hace necesario: la frontera cambia con cada lanzamiento. Terra salió días antes de que lo probara. Luna salió semanas antes. El próximo modelo moverá los dos puntos o añadirá un tercero, y la respuesta de este mes habrá que rehacerla.

Por eso merece la pena mantener barata y repetible la medición, no fija la conclusión: un banco pareado con tus tareas, un umbral de calidad escrito antes de la primera llamada, coste y latencia medidos por tarea, y el intercambio explícito: cuánto vale un segundo, cuánto vale un error. Con eso, un modelo nuevo es una tarde de medición y una línea en un gráfico. Sin eso, es un debate sobre la tarifa.

---

*El Industry Classifier está descrito en [su página de proyecto](/es/projects/compliance-classifier). Cómo pruebo en él un cambio de modelo, y lo que cuesta esa prueba, está en [El modelo nuevo es más barato. Probarlo, no](/es/blog/the-new-model-is-cheaper).*
