---
title: "El modelo nuevo es más barato. Probarlo, no."
description: "Cambiar el modelo de un agente en producción casi nunca es enchufar y listo, porque el harness está ajustado al anterior. El método que uso para probar un cambio, lo que costó uno, y el volumen por debajo del cual la evaluación le deja al proveedor más que la producción."
pubDate: 2026-11-02
tags: ["IA", "Evaluación", "LLM", "Ingeniería", "Economía"]
lang: es
translationKey: the-new-model-is-cheaper
heroImage: "/blog/the-new-model-is-cheaper.png"
---

<style>
.csw-fig { margin: 2rem 0; }
.csw-fig svg { width: 100%; height: auto; display: block; background: #1a1a24; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; }
.csw-fig figcaption { color: #94a3b8; font-size: 0.9rem; margin-top: 0.6rem; line-height: 1.5; }
</style>

En septiembre salió una nueva generación del modelo que usa uno de los servicios que mantengo. Sobre los mismos casos, su gama pequeña costaba por clasificación casi la mitad que la que estaba en producción. Sobre el papel, la decisión se toma sola.

Probar el cambio como es debido llevó varios días y **entre 47 y 65 dólares en tokens del modelo**. El servicio hace unas **500 clasificaciones al mes**, y en producción su factura de modelo rondaba los **cinco dólares al mes**. A ese volumen, el ahorro recupera solo los tokens de la prueba en unos **dos años**. El modelo al que iba a sustituir llevaba **75 días** en el mercado.

Merece la pena mirar las dos mitades: por qué un cambio de modelo necesita tanta prueba, y qué se sigue cuando la prueba cuesta más de lo que el cambio ahorra.

## Por qué un modelo mejor puede salir peor

Un ranking mide un modelo. Lo que tú pones en producción es un sistema: el modelo y todo lo que lo rodea — prompts, definiciones de herramientas y sus descripciones, cómo se leen las respuestas, el control del razonamiento, presupuestos y tiempos límite. Llamemos a eso el **harness**. Cada pieza se fue ajustando, prueba tras prueba, al comportamiento del modelo con el que se construyó.

Otro modelo se comporta de otra manera, y ninguna de estas diferencias es un defecto de ninguno de los dos:

- **Adherencia al prompt.** Uno sigue una instrucción al pie de la letra, otro la toma como sugerencia. Una regla escrita para el lector flexible la sobreaplica el literal.
- **Ambigüedad.** Ante un caso que las instrucciones no resuelven, uno pregunta, otro se abstiene y otro elige la lectura más plausible y sigue.
- **Cómo interpreta las instrucciones.** Las palabras absolutas («nunca», «siempre») y las excepciones escritas al lado pesan distinto, así que la misma frase produce casuísticas distintas.
- **Conocimiento previo.** Lo que el modelo ya cree sobre el mundo compite con lo que le da el harness. Un modelo más nuevo [no sabe necesariamente cuáles de sus datos han caducado](/es/blog/when-the-fact-stops-being-true): simplemente tiene otros.
- **Uso de herramientas y razonamiento.** Con qué facilidad llama a una herramienta, cómo lee su descripción, cuánto razona antes de responder. En este servicio, el modelo nuevo, en la configuración adoptada, hacía alrededor de un 12 % más de búsquedas web por clasificación que el anterior sobre los mismos casos. Estas diferencias mueven el coste y la latencia, no solo la calidad, y lo hacen en etapas que el modelo no factura: a un modelo más lento lo pueden cortar tiempos límite pensados para uno más rápido, y eso parece una pérdida de calidad.

La consecuencia es una asimetría que conviene nombrar. Si metes al candidato tal cual en el harness del modelo actual, lo que mides es **lo bien que el modelo nuevo imita al viejo** dentro de un harness hecho para el viejo. Esa prueba favorece sistemáticamente a lo que ya está en producción. Puede descubrir bloqueos. No puede justificar rechazar al candidato por calidad. La llamo prueba de sustitución, y la separo de la comparación real, donde cada modelo corre con un harness adaptado a él.

## Un método para probar un cambio

El procedimiento que sigue es el que escribí para un [servicio de clasificación sectorial](/es/projects/compliance-classifier): un agente que busca una empresa, comprueba que es la correcta y asigna a lo que hace un código de actividad. Nada en él es específico de ese servicio.

<figure class="csw-fig">
<svg viewBox="0 0 600 400" role="img" aria-label="El procedimiento de cambio de modelo como una cadena: precondiciones, un sondeo del gateway con las llamadas exactas, adaptación del harness, después tres etapas medidas y una puerta de release frente a la versión desplegada. Las etapas uno y dos vuelven a la adaptación del harness, así que adaptar y medir son un ciclo, no un paso.">
  <defs>
    <marker id="csw-arr-es" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#64748b"/></marker>
    <marker id="csw-arr-a-es" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#f59e0b"/></marker>
  </defs>
  <g font-family="system-ui,-apple-system,sans-serif">
    <rect x="20" y="20" width="170" height="78" rx="8" fill="#22222e" stroke="rgba(255,255,255,0.12)"/>
    <text x="105" y="44" text-anchor="middle" fill="#f8fafc" font-size="14" font-weight="600">Precondiciones</text>
    <text x="105" y="64" text-anchor="middle" fill="#94a3b8" font-size="11.5">versión fijada, con precio</text>
    <text x="105" y="80" text-anchor="middle" fill="#94a3b8" font-size="11.5">sin fallback silencioso</text>

    <rect x="215" y="20" width="170" height="78" rx="8" fill="#22222e" stroke="rgba(255,255,255,0.12)"/>
    <text x="300" y="44" text-anchor="middle" fill="#f8fafc" font-size="14" font-weight="600">Sondeo del gateway</text>
    <text x="300" y="64" text-anchor="middle" fill="#94a3b8" font-size="11.5">las llamadas exactas</text>
    <text x="300" y="80" text-anchor="middle" fill="#94a3b8" font-size="11.5">¿respeta cada parámetro?</text>

    <rect x="410" y="20" width="170" height="78" rx="8" fill="#14302c" stroke="#2dd4bf"/>
    <text x="495" y="44" text-anchor="middle" fill="#5eead4" font-size="14" font-weight="600">Adaptar el harness</text>
    <text x="495" y="64" text-anchor="middle" fill="#94a3b8" font-size="11.5">prompts, herramientas,</text>
    <text x="495" y="80" text-anchor="middle" fill="#94a3b8" font-size="11.5">lectura, razonamiento</text>

    <path d="M190,59 L211,59" stroke="#64748b" stroke-width="1.6" fill="none" marker-end="url(#csw-arr-es)"/>
    <path d="M385,59 L406,59" stroke="#64748b" stroke-width="1.6" fill="none" marker-end="url(#csw-arr-es)"/>

    <rect x="410" y="150" width="170" height="78" rx="8" fill="#22222e" stroke="rgba(255,255,255,0.12)"/>
    <text x="495" y="174" text-anchor="middle" fill="#f8fafc" font-size="14" font-weight="600">1 · Cohorte dirigida</text>
    <text x="495" y="194" text-anchor="middle" fill="#94a3b8" font-size="11.5">seguridad y casos difíciles</text>
    <text x="495" y="210" text-anchor="middle" fill="#94a3b8" font-size="11.5">≥ 4 rondas por caso</text>

    <rect x="215" y="150" width="170" height="78" rx="8" fill="#22222e" stroke="rgba(255,255,255,0.12)"/>
    <text x="300" y="174" text-anchor="middle" fill="#f8fafc" font-size="14" font-weight="600">2 · Banco completo</text>
    <text x="300" y="194" text-anchor="middle" fill="#94a3b8" font-size="11.5">pareado, intercalado</text>
    <text x="300" y="210" text-anchor="middle" fill="#94a3b8" font-size="11.5">≥ 2 rondas, prerregistrado</text>

    <rect x="20" y="150" width="170" height="78" rx="8" fill="#22222e" stroke="rgba(255,255,255,0.12)"/>
    <text x="105" y="174" text-anchor="middle" fill="#f8fafc" font-size="14" font-weight="600">3 · Atribución</text>
    <text x="105" y="194" text-anchor="middle" fill="#94a3b8" font-size="11.5">solo casos discordantes</text>
    <text x="105" y="210" text-anchor="middle" fill="#94a3b8" font-size="11.5">leídos en las trazas</text>

    <path d="M495,98 L495,146" stroke="#64748b" stroke-width="1.6" fill="none" marker-end="url(#csw-arr-es)"/>
    <path d="M410,189 L389,189" stroke="#64748b" stroke-width="1.6" fill="none" marker-end="url(#csw-arr-es)"/>
    <path d="M215,189 L194,189" stroke="#64748b" stroke-width="1.6" fill="none" marker-end="url(#csw-arr-es)"/>

    <path d="M330,150 C330,120 440,128 462,102" stroke="#f59e0b" stroke-width="1.6" fill="none" stroke-dasharray="5 4" marker-end="url(#csw-arr-a-es)"/>
    <path d="M555,150 C575,130 575,118 560,102" stroke="#f59e0b" stroke-width="1.6" fill="none" stroke-dasharray="5 4" marker-end="url(#csw-arr-a-es)"/>
    <rect x="352" y="112" width="74" height="16" fill="#1a1a24"/>
    <text x="389" y="124" text-anchor="middle" fill="#fbbf24" font-size="11">readaptar</text>

    <rect x="20" y="290" width="560" height="84" rx="8" fill="#2a2216" stroke="#f59e0b"/>
    <text x="300" y="316" text-anchor="middle" fill="#fbbf24" font-size="14" font-weight="600">Puerta de release frente a la versión ya desplegada</text>
    <text x="300" y="338" text-anchor="middle" fill="#94a3b8" font-size="11.5">misma ventana para las dos versiones · casos que cambian, ≥ 2 rondas cada una</text>
    <text x="300" y="356" text-anchor="middle" fill="#94a3b8" font-size="11.5">una ronda guardada de otro día no es un control</text>

    <path d="M105,228 L105,286" stroke="#64748b" stroke-width="1.6" fill="none" marker-end="url(#csw-arr-es)"/>
  </g>
</svg>
<figcaption>Adaptar el harness y medirlo son un ciclo. Lo que llega a la puerta de release es el modelo candidato con su harness adaptado, comparado con lo que está realmente desplegado.</figcaption>
</figure>

El orden de las etapas es deliberado: va de lo específico a lo exhaustivo. La primera etapa corre solo los casos que un cambio debería afectar — casos de seguridad, casos difíciles, el caso objetivo de cada salvaguarda —, componente a componente y con muchas rondas, para que una regresión aparezca cuando todavía es barata de encontrar. Solo un candidato que la supera pasa al banco completo. La atribución vuelve después a los casos en los que los dos brazos discreparon, y solo a esos. Las tandas caras van al final y las apuntan las baratas.

Las reglas que sostienen casi todo el peso:

- **Medir el servicio, no el modelo.** Un candidato se juzga por lo que el sistema devuelve de punta a punta — respuesta, evidencia, confianza, coste, latencia —, nunca por lo que diga el proveedor ni por un prompt en el playground.
- **Fijarlo, y verlo.** La versión del modelo se fija para que el proveedor no la cambie en mitad de una medición. Antes de tocar el servicio, un sondeo corto por el gateway usa exactamente las llamadas que envía el servicio. Un gateway puede descartar un parámetro que no admite y responder 200 igualmente, y un parámetro que se respeta en una API puede ignorarse en otra. Cada respuesta registra qué modelo la sirvió de verdad: un fallback silencioso sirve otro modelo con el nombre del candidato.
- **Pareado, intercalado y repetido.** Cada caso corre todos los brazos en la misma sesión, rotando el orden. El sistema no es determinista, así que una ronda por caso no decide nada, y puede que dos tampoco: en este servicio, entre los casos cuyas dos primeras rondas coincidían, las rondas tres y cuatro devolvieron otro código **en el 24 % de las ocasiones**. Antes de leer cualquier diferencia, se mide cuánto discrepa el control consigo mismo en los mismos casos. Un efecto menor que ese suelo no es un efecto.
- **Separar una caída de una respuesta.** Una llamada que no llegó (timeout, error del gateway) se excluye. Una que llegó con algo inservible (ilegible, vacío, fuera de escala) cuenta contra el candidato: es parte de lo que se mide. La traza tiene que distinguir las dos antes de empezar.
- **Llevar un registro de mecanismos.** Muchas salvaguardas son instrucciones que se adoptaron porque cambiaron de forma medida el comportamiento del modelo actual. Un modelo nuevo puede leerlas de otra manera, así que un mecanismo puede dejar de funcionar mientras el agregado sigue plano. Cada uno se apunta con su caso objetivo y se comprueba en el candidato.
- **Distinto no es mejor.** Las reglas de decisión se escriben antes de la primera llamada: cero fallos graves de seguridad, ningún caso que pase de acierto a fallo por encima de la variación del propio control, ninguna subida de respuestas equivocadas con confianza alta, estabilidad no peor, coste y latencia dentro de los límites acordados. Un candidato que arregla un caso y rompe otro no es una mejora.
- **Comparar con lo desplegado, en la misma ventana.** Pasar frente al modelo anterior en la misma build no basta para promocionar. La release se compara con la versión que corre en el siguiente entorno, en la misma ventana de tiempo, porque [los jueces LLM](/es/blog/three-judges-three-rankings) y los datos externos cambian de un día a otro.

## En qué se diferencia del testing que ya conoces

| | Software tradicional | ML tradicional | Cambiar el modelo de un sistema con LLM |
|---|---|---|---|
| Quién cambia el componente | Tú | Tú (reentrenas) | El proveedor, cuando decide |
| ¿Misma entrada, misma salida? | Sí | Sí, una vez entrenado | No: muestreo, resultados de búsqueda, jueces |
| Qué ajustas | Código | Pesos, features, hiperparámetros | Prompts, descripciones de herramientas, forma de las llamadas — en lenguaje natural |
| Una prueba es | Pasa o falla | Un agregado sobre un conjunto reservado | Pareada, repetida, por caso, por encima de un suelo de ruido |
| Qué decide | La aserción | La métrica | La métrica, y después una persona leyendo en las trazas cada discrepancia |

Los modelos de pesos abiertos en tu propia infraestructura se acercan al ML tradicional en un eje: tú decides cuándo cambias, nadie te retira el modelo y la evaluación corre en tus GPU. En el otro eje no se mueven. Salvo que hagas fine-tuning, sigues cambiando unos pesos por otros y adaptando prompts y herramientas, exactamente igual que con un proveedor.

## Lo que costó un cambio

Esta es la factura del cambio del principio, contando **solo lo que cuesta el modelo de lenguaje**. El servicio también paga búsqueda web, pero ese gasto tiene su propia dinámica y queda fuera de este cálculo.

Los doce días de pruebas alrededor del cambio no fueron todos del cambio. Más o menos la mitad habría ocurrido igual: la puerta de release de una versión de antes del cambio, los arreglos que salieron de esa puerta, trabajo de integración, una ronda de arreglos que pidió un cliente. Esa mitad también queda fuera. Lo que cuenta es la comparación pareada de los dos modelos con la adaptación del harness, las puertas de release de las primeras versiones con el modelo nuevo y los arreglos que salieron de esas puertas. Algunos de esos arreglos corregían defectos anteriores al modelo nuevo, pero fue la comparación la que los volvió a sacar, así que cuentan para ella.

| | Valor |
|---|---:|
| Tokens del modelo gastados en el cambio, en las tandas guardadas | 47 $ |
| … escalado por el 27 % de llamadas que no se guardaron (pruebas de humo, tandas cortadas) | ≈ 65 $ |
| Coste de modelo por clasificación, pareado sobre la misma build: modelo en producción → candidato | 0,0098 $ → 0,0053 $ |
| **Ahorro por clasificación** | **≈ 0,0045 $** |
| Volumen de producción | ≈ 500 al mes |

A los tokens se suma el tiempo de ingeniería. La sesión que hizo el cambio registró unas **20 horas activas de trabajo del agente**. Las mías, dentro de ella, fueron unas **cuatro horas**. Valorando esas cuatro horas a 50 $/h y dejando aparte lo que cuestan las del agente, el cambio sale por unos **250 a 265 dólares**.

| Coste del cambio | Clasificaciones para amortizarlo | A 500 al mes |
|---|---:|---:|
| Tokens, tandas guardadas (47 $) | ≈ 10.500 | ≈ 21 meses |
| Tokens, escalado (65 $) | ≈ 14.400 | ≈ 29 meses |
| Tokens + mis 4 horas (≈ 265 $) | ≈ 59.000 | ≈ 10 años |

Solo con los tokens, a este volumen, recuperar la inversión queda ya a dos años. El tiempo de ingeniería lo lleva a una década. Y el horizonte que importa no se mide en años: es lo que tarda el siguiente modelo.

<figure class="csw-fig">
<svg viewBox="0 0 600 360" role="img" aria-label="Meses necesarios para recuperar el coste de un cambio de modelo, frente al volumen mensual, en escalas logarítmicas. A 500 clasificaciones al mes hacen falta entre 21 y 29 meses contando solo tokens, y unos 118 contando cuatro horas de ingeniería. Recuperarlo antes del siguiente lanzamiento, a 2,5 meses, exige entre unas 4.200 y 23.500 clasificaciones al mes.">
  <g font-family="system-ui,-apple-system,sans-serif">
    <g stroke="rgba(255,255,255,0.08)" stroke-width="1">
      <line x1="70" y1="30" x2="570" y2="30"/><line x1="70" y1="95" x2="570" y2="95"/><line x1="70" y1="160" x2="570" y2="160"/><line x1="70" y1="225" x2="570" y2="225"/><line x1="70" y1="290" x2="570" y2="290"/>
      <line x1="70" y1="30" x2="70" y2="290"/><line x1="236.7" y1="30" x2="236.7" y2="290"/><line x1="403.3" y1="30" x2="403.3" y2="290"/><line x1="570" y1="30" x2="570" y2="290"/>
    </g>
    <g fill="#94a3b8" font-size="11" text-anchor="end">
      <text x="62" y="34">1.000</text><text x="62" y="99">100</text><text x="62" y="164">10</text><text x="62" y="229">1</text><text x="62" y="294">0,1</text>
    </g>
    <g fill="#94a3b8" font-size="11" text-anchor="middle">
      <text x="70" y="308">100</text><text x="236.7" y="308">1k</text><text x="403.3" y="308">10k</text><text x="570" y="308">100k</text>
    </g>
    <text x="320" y="334" text-anchor="middle" fill="#94a3b8" font-size="12">clasificaciones al mes</text>
    <text x="20" y="160" text-anchor="middle" fill="#94a3b8" font-size="12" transform="rotate(-90 20 160)">meses para amortizar</text>

    <line x1="70" y1="199.1" x2="570" y2="199.1" stroke="#f59e0b" stroke-width="1.5" stroke-dasharray="6 4"/>

    <line x1="186.5" y1="30" x2="186.5" y2="290" stroke="#5eead4" stroke-width="1" stroke-dasharray="3 3"/>
    <rect x="191" y="270" width="62" height="16" fill="#1a1a24"/>
    <text x="194" y="282" fill="#5eead4" font-size="11.5">500 al mes</text>
    <rect x="76" y="203" width="212" height="16" fill="#1a1a24"/>
    <text x="80" y="215" fill="#fbbf24" font-size="11.5">siguiente modelo de esa gama: 2,5 meses</text>

    <line x1="70" y1="44.9" x2="570" y2="240.0" stroke="#e2e8f0" stroke-width="2"/>
    <line x1="70" y1="84.7" x2="570" y2="279.7" stroke="#2dd4bf" stroke-width="2"/>
    <line x1="70" y1="93.6" x2="570" y2="288.6" stroke="#64748b" stroke-width="2"/>

    <circle cx="186.5" cy="90.4" r="4" fill="#e2e8f0"/>
    <circle cx="186.5" cy="130.1" r="4" fill="#2dd4bf"/>
    <circle cx="186.5" cy="139.0" r="4" fill="#64748b"/>

    <circle cx="465.3" cy="199.1" r="3.5" fill="#f59e0b"/>
    <circle cx="363.5" cy="199.1" r="3.5" fill="#f59e0b"/>
    <circle cx="340.7" cy="199.1" r="3.5" fill="#f59e0b"/>

    <rect x="340" y="40" width="224" height="66" rx="6" fill="#1a1a24" stroke="rgba(255,255,255,0.1)"/>
    <line x1="352" y1="56" x2="372" y2="56" stroke="#e2e8f0" stroke-width="2"/><text x="378" y="60" fill="#e2e8f0" font-size="11.5">tokens + mis 4 horas (265 $)</text>
    <line x1="352" y1="74" x2="372" y2="74" stroke="#2dd4bf" stroke-width="2"/><text x="378" y="78" fill="#e2e8f0" font-size="11.5">tokens, escalado (65 $)</text>
    <line x1="352" y1="92" x2="372" y2="92" stroke="#64748b" stroke-width="2"/><text x="378" y="96" fill="#e2e8f0" font-size="11.5">tokens, tandas guardadas (47 $)</text>
  </g>
</svg>
<figcaption>Meses para recuperar el cambio con un ahorro de 0,0045 $ por clasificación. A 500 al mes, entre 21 y 29 meses solo con los tokens, unos diez años con el tiempo de ingeniería. Para recuperarlo antes de que llegue el siguiente modelo, el servicio necesitaría entre unas 4.200 y 23.500 clasificaciones al mes.</figcaption>
</figure>

## Quién cobra

Las horas de ingeniería se quedan con quien paga al ingeniero. Los tokens no: van al proveedor del modelo, y eso cambia cómo se ve el cambio desde el otro lado.

A 500 clasificaciones al mes, este servicio le pagaba al proveedor unos cinco dólares al mes en producción, y con el modelo nuevo le paga menos de tres. La comparación le pagó entre 47 y 65: **lo equivalente a entre 10 y 13 meses de producción al precio anterior, o entre 18 y 25 al nuevo**. Un lanzamiento que un equipo tiene que probar puede dejarle al proveedor más por la prueba que por uno o dos años de uso real.

La proporción se invierte con el volumen. La evaluación cuesta más o menos lo mismo se hagan las clasificaciones que se hagan en producción: lo que la mueve es el número de rondas, no el tráfico. Lo que factura la producción sí crece con el tráfico. En los 75 días que duró un modelo de esa gama, la producción con el modelo nuevo igualaría el coste de la comparación con **entre unas 3.500 y 4.900 clasificaciones al mes**. Por debajo de esa línea, cada cambio que un equipo prueba le deja al proveedor más en evaluación de lo que el modelo nuevo factura en producción antes de que llegue el siguiente.

No digo que los proveedores saquen modelos para cobrar evaluaciones. La competencia explica los lanzamientos sin ayuda. Pero el efecto secundario existe y se acumula con la cadencia. Desde GPT-5, en agosto de 2025, OpenAI ha sacado una generación nueva [más o menos cada dos meses](https://en.wikipedia.org/wiki/GPT-6). En Anthropic, el intervalo entre [lanzamientos de Sonnet](https://en.wikipedia.org/wiki/Claude_(language_model)) pasó de casi cinco meses a unos tres. Lo que pesa para un sistema concreto es la cadencia de la gama que usa, no la del catálogo: aquí, 75 días.

## Cuándo compensa cambiar

Solo por coste, un cambio compensa cuando

**ahorro por ejecución × volumen mensual × meses que vas a quedarte con el modelo nuevo > coste del cambio**

De ahí salen tres cosas.

**No hace falta subirse a cada lanzamiento.** El horizonte es cuánto vas a quedarte con el modelo nuevo, no cuánto falta para el siguiente. Un equipo con poco volumen que se salta generaciones paga el coste de un cambio una vez por cada migración obligada — cuando retiran el modelo anterior —, no una vez por lanzamiento.

**Con poco volumen, el coste no puede justificar un cambio; solo la calidad.** La regla pasa a ser *errores evitados por ejecución × coste de un error × volumen × meses > coste del cambio*. En un clasificador de cumplimiento normativo, una respuesta equivocada con confianza alta puede costar más que todos los tokens juntos. Pero ese coste por error hay que fijarlo, no suponerlo, o la fórmula justifica cualquier cosa.

**El coste de un cambio no es el mismo de un cambio a otro.** Buena parte de lo que necesita este método es infraestructura que se construye una vez: elegir el modelo por petición, que cada respuesta registre qué la sirvió, bancos de casos con referencias revisadas, el registro de mecanismos. El primer cambio la paga. Los siguientes la reutilizan. Si eso deja el próximo cambio por debajo de la línea lo medirá el próximo cambio.

Todo esto es un servicio, un cambio y un proveedor, con el tiempo de ingeniería reconstruido a partir de los registros de las sesiones y sin contar lo que no pasó por ellas. Basta para enseñar la forma del problema, no para fijar la cifra de nadie más. Lo que viaja es la fórmula: pon tu volumen, tu ahorro y lo que te cuesta probar, y mira en qué lado de la línea caes.
