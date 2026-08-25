---
title: "El evaluador sabía menos que el sistema evaluado"
description: "Un informe externo dijo que el clasificador acertaba un 54% sobre 500 empresas. El gold set lo había generado un modelo genérico con las 500 de golpe, y sus etiquetas se podían adivinar desde el nombre de la empresa. La cifra defendible estaba veinte puntos más arriba. Sobre cuándo una IA puede evaluar a otra, y cuándo no."
pubDate: 2026-08-25
tags: ["IA", "Evaluación", "Datos", "Métricas", "Investigación"]
lang: es
translationKey: the-grader-knew-less
heroImage: "/blog/the-grader-knew-less.png"
---

Me llegó un informe con una sola cifra grande: **54% de acierto sobre 500 empresas**. Debajo, la conclusión que se sigue de una cifra así: el algoritmo necesita mejorar bastante.

El sistema evaluado era un [clasificador de actividad económica](/es/projects/compliance-classifier): recibe una empresa, busca su presencia web, la identifica, lee a qué se dedica de verdad y mapea esa actividad a un código de industria validado contra la jerarquía oficial de la taxonomía. Tarda del orden de un minuto por entidad. La prueba se hizo por fuera, contra la API, sin que yo interviniera.

Voy a ser honesto con mi primera reacción, porque es la parte que menos me gusta contar: no dudé del informe. Un porcentaje con decimales sobre una muestra de 500 tiene una autoridad que no se cuestiona a la primera. Estuve un buen rato pensando en qué habíamos hecho mal.

## La primera pista

Cuando volví a ejecutar el set por mi lado y me senté a mirar discrepancia por discrepancia, apareció un patrón que no encajaba: **las etiquetas del gold set se podían adivinar sin mirar la empresa**. Bastaba con el nombre. Si en la razón social aparecía una palabra como *logistics*, la etiqueta era transporte. Si aparecía *solar*, energía. Si el nombre era opaco —unas siglas, un apellido, una marca inventada—, la etiqueta caía en alguna categoría genérica de servicios.

Esa correlación es el hallazgo entero. Una etiqueta que se predice desde el nombre no contiene información sobre la empresa: contiene información sobre el nombre. Y resulta que muchas empresas no se dedican a lo que su nombre sugiere. Una consultora llamada *algo Mining Services* que en realidad vende software para mineras se clasifica en minería si solo lees el rótulo, y en software si abres su web. Los casos donde el nombre engaña son precisamente los difíciles, es decir, los únicos que valía la pena medir.

Pregunté. La respuesta fue directa y sin drama: el gold set se había generado pasando la lista por ChatGPT.

## Dos procesos distintos con una sola nota

Ahí está el fondo del asunto, y no es una cuestión de orgullo herido. El sistema evaluado dedica a cada entidad una ronda de enriquecimiento con registros oficiales, búsquedas web y lectura de la actividad real antes de asignar nada. El evaluador leyó una columna de nombres.

No se estaba comparando *sistema contra verdad*. Se comparaba un proceso con investigación contra un proceso sin ella, y quien ponía la nota era el que tenía menos información de los dos. Un evaluador con menos acceso al mundo que el sistema evaluado no mide al sistema: mide la distancia entre dos métodos, y llama error a todo lo que el sistema sabía de más.

Hay una frase que acabamos repitiendo entre compañeros cada vez que salía el tema, y resume el problema mejor que cualquier análisis mío: *si ChatGPT fuera lo bastante bueno como para construir el gold set, no haría falta esta herramienta y no la habríamos desarrollado*. El conjunto de referencia daba por resuelto exactamente el problema que pretendía medir.

## El matiz: no es un problema del modelo

Aquí este artículo se podría convertir en un "los LLM genéricos no sirven para etiquetar", y sería falso.

Un modelo genérico, con una empresa cada vez, con búsqueda habilitada y con tiempo para navegar, es un baseline perfectamente respetable. Lo sé porque fue el punto de partida del proyecto: la pregunta fundacional del proyecto fue literalmente *¿hasta dónde llega esto hecho a mano con un chat, y qué hay que construir para superarlo de forma consistente, auditable y a escala?*. La respuesta a la primera mitad no era mala en absoluto.

Lo que rompe no es el modelo, es **el modo**. Quinientas filas en una sola petición reparten un presupuesto de razonamiento minúsculo por fila y, sobre todo, no dejan hueco para ir a buscar nada fuera. El modelo hace entonces lo único que puede hacer con lo que tiene delante: inferir a partir del texto disponible, que es el nombre. No es una alucinación ni un fallo de capacidad; es la respuesta correcta a la pregunta que se le hizo, que no era la que se creía estar haciendo.

Y esta frontera se mueve. Un agente con navegador y presupuesto por caso ya hace hoy una parte real de esa investigación, y dentro de un año hará más. Por eso el criterio útil no es *¿lo hizo una IA?* sino **¿hubo investigación por caso, y de qué profundidad?**. Esa segunda pregunta seguirá siendo válida cuando los modelos hayan cambiado tres veces.

## La regla que me llevo

De aquí sale una línea bastante limpia entre dos usos que solemos meter en el mismo saco: la IA como **juez** y la IA como **investigadora**.

Un modelo evaluando a otro funciona bien cuando el juicio se cierra con lo que ya está en la pantalla: ¿esta respuesta es coherente con el contexto?, ¿respeta el formato?, ¿cuál de estas dos es mejor?, ¿sigue las instrucciones que se le dieron? Ahí un evaluador externo aporta incluso algo que nosotros no tenemos: una perspectiva sin cariño por el sistema. Es un uso legítimo y razonablemente bien estudiado: es el terreno donde [se asentó la idea de usar modelos como jueces](https://arxiv.org/abs/2306.05685), comparando respuestas y midiendo su acuerdo con preferencias humanas.

Deja de funcionar cuando la respuesta correcta no está en la pantalla sino en el mundo: en un registro mercantil, en la web de la empresa, en una noticia de hace tres meses. Entonces el evaluador tiene que hacer al menos el mismo trabajo que el sistema evaluado. No un trabajo parecido: el mismo o más. Si no lo hace, la métrica que produce es una medida de él, no del sistema. No es casualidad: [los repasos de la literatura sobre LLM como juez](https://arxiv.org/abs/2412.05579) colocan entre sus límites centrales justamente los de conocimiento — información desactualizada, lagunas de dominio y afirmaciones inventadas con aplomo.

El test de una línea que aplico ahora antes de aceptar cualquier evaluación:

> ¿El evaluador tuvo acceso a más información que el sistema evaluado, o a menos?

Con más, la evaluación puede ser dura y sigue siendo útil. Con lo mismo, es discutible pero informativa. Con menos, no es una evaluación.

## Los errores aburridos que también estaban ahí

El gold set fue el problema grande, pero no el único. La comparación tampoco estaba bien montada:

- **Sensible al orden.** Una entidad puede recibir varios códigos, y la respuesta se contaba como fallo si venían en distinto orden que el esperado.
- **Ciega a la compatibilidad.** En estas taxonomías hay códigos legítimamente compatibles entre sí: una empresa puede caer en dos y ambos ser correctos. Se contaba uno como acierto y el otro como error.
- **Binaria.** Sin distancia en la jerarquía. Fallar de rama y fallar de subcategoría dentro de la rama correcta valían exactamente lo mismo.

Merece la pena señalar algo sobre estos tres: empujan en la misma dirección que el gold set malo. Un conjunto de referencia inferido del nombre y una comparación estricta solo pueden restar puntos, nunca sumarlos. Cuando todos los sesgos de una medición apuntan hacia abajo, el número que sale no es simplemente "ruidoso": está sesgado, y encima en la dirección que sale más cara.

## Lo que costó tener un número honesto

Rehacerlo bien fue trabajo manual, y no encontré atajo. Caso por caso, empezando por los desacuerdos. Apoyarse en un buen modelo, uno a uno y despacio, ayuda mucho —bastante más que en batch, que es justamente el punto—, pero ni así sale limpio: hubo entradas que hubo que abrir a mano porque la clasificación automática no me cuadraba, y quedan casos que siguen siendo defendibles en dos códigos distintos.

El resultado fue **un 75% con criterio conservador, y hasta un 85% si resuelves las zonas grises a favor**. Unos veinte puntos por encima del informe.

Y la parte que también hay que decir: el sistema no salió perfecto de esa revisión. Había fallos reales, y esos fueron el material útil de todo el episodio. Lo que no existía era el diagnóstico. Un 54% dice *esto está roto, replantea el enfoque*. Un 75% con una lista de casos concretos dice *esto funciona y aquí están las diez cosas que hay que afinar*. Son dos decisiones de producto completamente distintas, y una de las dos habría sido muy cara.

Tampoco conviene leer ese 75% como una propiedad fija del sistema. Este lote era particularmente difícil, y la exactitud alcanzable depende mucho de la composición: qué fracción de las empresas tiene presencia web propia, de qué tipo y con cuánto detalle. Un conjunto de negocios con web activa y actividad descrita se clasifica muy por encima de uno cargado de sociedades patrimoniales sin apenas rastro público. Comparar el porcentaje de dos lotes distintos como si midieran lo mismo es otra versión del mismo error de fondo.

Y de la revisión, junto con el feedback del cliente, salió la conclusión que más me cambió la forma de mirar la métrica: **un resultado equivocado que el propio sistema marca como de baja confianza no es el mismo tipo de fallo que uno equivocado con confianza alta**. El primero se enruta a revisión humana y el flujo hace justo lo que tiene que hacer; el segundo es el que hace daño de verdad. Una exactitud plana los cuenta igual, y esa es probablemente la limitación más seria de medir esto con un único porcentaje.

## Por qué el etiquetado se ha vuelto caro

Este incidente es una versión doméstica de algo que está pasando a escala industrial. En 2026, Meta reasignó a miles de ingenieros —del orden de [6.500 personas en su organización de datos para agentes](https://thenextweb.com/news/meta-applied-ai-unit-revolt-data-labeling-draftees), según los reportes— a producir y etiquetar datos de entrenamiento, con [una revuelta interna considerable](https://newsletter.pragmaticengineer.com/p/why-is-meta-destroying-its-engineering) y una marcha atrás parcial después. Se puede discutir la gestión; la señal de fondo es difícil de discutir: alguien decidió que pagar sueldos de ingeniería de frontera por etiquetar datos salía a cuenta.

La lectura coincide con la de este episodio. Correr una evaluación es barato. Construir la verdad contra la que comparas, no. Es la parte que sigue siendo lenta, humana y aburrida, y por eso se está pagando cada vez mejor. Pasar el dataset por un chat en batch no es una versión rápida de ese trabajo: es la operación de saltárselo entero conservando la apariencia del resultado. Y esa apariencia es peor que no tener nada, porque un número falso sí toma decisiones — nadie replantea un roadmap por una carpeta vacía.

## Antes de creerte una métrica

Las cinco preguntas que hago ahora a cualquier evaluación antes de discutir su resultado:

1. **¿Quién construyó el gold set y con qué acceso a información?** Si la respuesta es "un modelo, en batch", ya sabes qué mide.
2. **¿Puedo predecir las etiquetas con una heurística tonta?** Coge el atributo más superficial de cada caso —el nombre, la primera palabra— e intenta reproducir el gold set. Si lo consigues, el gold set *es* esa heurística.
3. **¿Qué cuenta exactamente como acierto?** Orden, multiplicidad, sinónimos, distancia en la jerarquía. Muchas discusiones de calidad son en realidad discusiones de comparador.
4. **¿Se revisaron a mano los desacuerdos, o solo se contaron?** Un desacuerdo no revisado no es un error: es un desacuerdo.
5. **En los desacuerdos revisados, ¿quién gana?** Si el sistema gana una fracción alta de ellos, el problema no está en el sistema.

Durante todo este episodio, el sistema estuvo bajo sospecha desde el primer minuto y el gold set no lo estuvo ni un segundo. Esa asimetría es lo que me parece interesante: damos por auditado lo que hace de referencia precisamente porque hace de referencia. Cuando una evaluación te dice que tu sistema es malo, la primera hipótesis barata no es rehacer el sistema. Es abrir el gold set y comprobar si alguien fue a mirar.
