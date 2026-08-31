---
title: "Culpa al modelo de lo que no se culparía a sí mismo"
description: "Los agentes que construyen sistemas con un LLM dentro recurren siempre a la misma explicación: el modelo no es determinista. Cinco veces no lo era, y lo interesante es adónde fue la sospecha en vez de adónde estaba la causa."
pubDate: 2026-08-31
tags: ["IA", "Agentes", "Ingeniería", "Depuración"]
lang: es
translationKey: blaming-the-model
heroImage: "/blog/blaming-the-model.png"
---

<style>
.btm-fig { margin: 2rem 0; }
.btm-fig svg { width: 100%; height: auto; display: block; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; background: #1a1a24; }
.btm-fig figcaption { color: #94a3b8; font-size: 0.9rem; margin-top: 0.6rem; line-height: 1.5; }
</style>

Paso la mayor parte del tiempo construyendo sistemas que llevan un modelo de lenguaje dentro, y la mayor parte de ese tiempo no escribo yo el código: lo escribe un agente. Lo que significa que dedico buena parte del día a leer la explicación de un agente sobre por qué algo no ha funcionado.

En esas explicaciones hay un patrón que tardé en saber nombrar. Cuando el sistema del que se habla es software normal, el agente razona bien: busca el fallo y encuentra el fallo. Cuando el sistema del que se habla tiene un modelo dentro, el razonamiento cambia. La sospecha se desplaza, y aterriza en el modelo.

Lo que lo vuelve raro, más que simplemente equivocado, es que el agente que razona es él mismo un modelo — a menudo el mismo que corre dentro de aquello que está diagnosticando.

Cinco veces me ha pasado. Ninguna es una catástrofe; todas son pequeñas, y precisamente por eso las cuento.

## La traza que nadie pidió

Teníamos un clasificador: lee documentos sobre algo y le asigna una categoría, con una confianza y una justificación. Los resultados eran irregulares, y pedí a los agentes que trabajaban en él que averiguaran por qué.

Lo que volvió fueron hipótesis. Buenas, en el sentido de que eran plausibles y estaban bien escritas. Las fronteras entre categorías podían ser ambiguas. Los documentos podían ser demasiado cortos. El modelo podía estar dando demasiado peso a ciertas palabras. Cualquiera de ellas podía ser cierta. Ninguna se podía comprobar con lo que teníamos, porque lo que teníamos era la entrada y la respuesta final, y nada en medio.

Ni una sola vez propuso nadie lo evidente: *registremos lo que pasó de verdad*.

Así que lo decidí yo, y costó tres pasadas dejarlo bien: primero qué se buscó y qué volvió, después qué documentos llegaron realmente al modelo y no sólo qué devolvió la búsqueda, y por último todas las llamadas a herramientas y no sólo las búsquedas. En cada pasada creí que ya teníamos bastante y en cada pasada no lo teníamos.

Y entonces pasó algo que no esperaba. Con la traza completa, el análisis mejoró solo. Yo había escrito además una regla —mira el razonamiento, mira las confianzas, mira todos los pasos intermedios— y había dado por hecho que la regla era la que hacía el trabajo. No lo era, o no en su mayor parte. **Dar la información resultó más efectivo que dar la instrucción sobre cómo analizarla.**

Merece la pena pararse ahí, porque el reflejo actual para corregir el comportamiento de un agente es escribirle una regla mejor: una skill, una sección en `CLAUDE.md`, una lista de comprobación. A veces lo que le hace falta no es una instrucción mejor, sino una ventana más ancha.

## «Es que es estocástico»

La segunda es la más frecuente, y es la que le puso nombre a todo esto.

Los resultados varían entre ejecuciones, y la explicación que se ofrece es el muestreo del modelo. A veces se dice tal cual; más a menudo llega en forma de encogimiento de hombros — *estos sistemas no son deterministas, no puedes esperar estabilidad*.

En mi experiencia casi nunca ha sido esa la causa real. Cambiaban los inputs. La recuperación devolvía los documentos en otro orden. Una herramienta omitía un campo opcional. Dos reglas del prompt aplicaban a la vez y nadie había declarado cuál gana. El contexto se truncaba y el documento decisivo se quedaba fuera de la ventana. Son problemas de diseño, y tienen la útil propiedad de ser arreglables.

<figure class="btm-fig">
<svg viewBox="0 0 600 300" role="img" aria-label="Diagrama con las cinco capas de un sistema que lleva un modelo dentro: datos de entrada, prompt y reglas, herramientas y recuperación, código del harness, y muestreo del modelo. Las causas de la variabilidad suelen estar en las cuatro primeras capas, mientras que la sospecha aterriza en la quinta.">
  <rect x="30" y="40" width="300" height="34" rx="5" fill="#1e293b" stroke="#2dd4bf" stroke-width="1.2"/>
  <text x="46" y="62" fill="#e2e8f0" font-size="14" font-family="ui-monospace,'JetBrains Mono',monospace">datos de entrada</text>
  <rect x="30" y="86" width="300" height="34" rx="5" fill="#1e293b" stroke="#2dd4bf" stroke-width="1.2"/>
  <text x="46" y="108" fill="#e2e8f0" font-size="14" font-family="ui-monospace,'JetBrains Mono',monospace">prompt y reglas</text>
  <rect x="30" y="132" width="300" height="34" rx="5" fill="#1e293b" stroke="#2dd4bf" stroke-width="1.2"/>
  <text x="46" y="154" fill="#e2e8f0" font-size="14" font-family="ui-monospace,'JetBrains Mono',monospace">herramientas</text>
  <rect x="30" y="178" width="300" height="34" rx="5" fill="#1e293b" stroke="#2dd4bf" stroke-width="1.2"/>
  <text x="46" y="200" fill="#e2e8f0" font-size="14" font-family="ui-monospace,'JetBrains Mono',monospace">código del harness</text>
  <rect x="30" y="230" width="300" height="34" rx="5" fill="#2a1f14" stroke="#f59e0b" stroke-width="1.6"/>
  <text x="46" y="252" fill="#fbbf24" font-size="14" font-family="ui-monospace,'JetBrains Mono',monospace">muestreo del modelo</text>

  <path d="M338 57 L400 57 M338 103 L400 103 M338 149 L400 149 M338 195 L400 195" stroke="#2dd4bf" stroke-width="1.2" fill="none" opacity="0.7"/>
  <path d="M400 50 L400 202" stroke="#2dd4bf" stroke-width="1.5" fill="none"/>
  <text x="412" y="120" fill="#5eead4" font-size="13">donde suele</text>
  <text x="412" y="138" fill="#5eead4" font-size="13">estar la causa</text>

  <path d="M338 247 L400 247" stroke="#f59e0b" stroke-width="1.6" fill="none"/>
  <text x="412" y="243" fill="#fbbf24" font-size="13">donde aterriza</text>
  <text x="412" y="261" fill="#fbbf24" font-size="13">la sospecha</text>
</svg>
<figcaption>La variabilidad viene casi siempre de una de las cuatro capas de arriba, y todas ellas son decisiones de diseño que alguien tomó. La explicación se va a la quinta, que es la única de la que no se puede culpar a nadie.</figcaption>
</figure>

Fíjate en lo que tiene la capa de abajo y no tienen las demás: nadie la escribió. Atribuir un problema al muestreo del modelo es el único diagnóstico que cierra la investigación sin señalar ninguna decisión que alguien tomara. Y eso no es una parte pequeña de su atractivo.

## El interruptor

La segunda historia lleva un reflejo pegado, y el reflejo es una pequeña historia por su cuenta.

Una vez que «es estocástico» está sobre la mesa, el remedio que viene detrás es bajar la temperatura. Es lo primero que se propone, muchas veces antes de haber medido nada.

Falla en dos planos a la vez. No es la causa, así que no arregla nada — como mucho congela la respuesta equivocada en lugar de dejar que varíe. Y en un buen número de modelos actuales ni siquiera está disponible: varios despliegues de razonamiento rechazan el parámetro. Lo comprobé mientras montaba el experimento que sigue a este artículo, porque quería ser preciso y no retórico, y ni siquiera es uniforme dentro de una misma familia: algunos despliegues de gpt-5.x rechazan cualquier valor de `temperature` y otros lo aceptan sin queja. Así que el reflejo es siempre un error de diagnóstico, y en algunos modelos es además un error de API que se descubre al chocar con él.

Lo que me parece revelador no es la equivocación. Es que buscar un mando cuesta menos que buscar el diseño, y siempre hay un mando.

Hay una segunda explicación que me parece plausible y que no puedo zanjar desde aquí. Estos modelos se entrenaron sobre un corpus donde el software normal supera con mucho al software que lleva un modelo dentro, y la parte que sí habla de modelos de lenguaje está sesgada hacia lo antiguo: artículos y cuadernos de una época en la que `temperature` era el mando principal que había, y en la que tratar la varianza de salida como una propiedad del modelo era sencillamente correcto. Leído así, el reflejo no es descuido sino un fósil: buena práctica para los modelos de hace unos años, aplicada a sistemas que ya no funcionan de esa manera. Explicaría la forma concreta del error, que el mando al que se recurre sea siempre el que solía ser el mando bueno. No puedo establecerlo sin ver los datos de entrenamiento, pero una versión más estrecha sí es comprobable —si lo que un agente cree sobre las APIs de los modelos sigue a la época en que se entrenó y no a los modelos que está llamando— y eso probablemente da para un artículo propio.

## Nadie auditó el ground truth

Estábamos migrando de una versión de Claude a la siguiente, y el feedback era que la nueva iba peor.

No me lo creí, y no por lealtad al modelo nuevo: simplemente sabía cómo se había montado la comparación. Resultó que el prompt que se usaba con el modelo nuevo no era equivalente al del viejo. Y por debajo de eso, el gold set tenía errores propios, y esos errores premiaban justo las respuestas que daba el modelo viejo.

La medición estaba mal en la dirección que hacía obvia la conclusión. Y hizo falta que alguien preguntara *¿este ground truth es correcto de verdad?* para que alguien lo mirara — que es una pregunta sobre el método de uno, no sobre el modelo.

Esa asimetría es la versión más nítida de todo el patrón. La sospecha sobre el modelo vino primero. La sospecha sobre el montaje que producía el número llegó sólo cuando se pidió.

Volvió a pasar más tarde, a lo grande, y aquello lo conté aparte: [el evaluador sabía menos que el sistema evaluado](/es/blog/the-grader-knew-less). Un informe externo situaba a un clasificador en un 54% de acierto sobre 500 empresas; el gold set que producía ese número lo había generado un modelo genérico de una sentada, y sus etiquetas se podían adivinar desde el nombre de la empresa. La cifra defendible estaba veinte puntos más arriba. La misma forma, otra vez: del número sólo se dudó cuando alguien dudó en voz alta.

## Un regex donde hacía falta juicio

La quinta es lo que ocurre cuando el agente por fin acepta que el problema es de diseño.

El remedio que propone es un regex. O una lista de palabras clave, o un umbral duro sobre una puntuación. Algo que funciona perfectamente sobre los tres ejemplos que tiene delante y se cae con el cuarto. En la práctica tengo que pararle los pies a casi toda propuesta de determinismo que me llega, porque suelo ver por dónde se rompe antes de que esté escrita.

Y el motivo que hay detrás es la otra mitad del mismo problema. El agente busca reglas frágiles porque no se fía de que el modelo discierna — que es precisamente para lo que sirve un modelo. Cuando la tarea no tiene una regla enumerable, cuando el conjunto de casos no está acotado y las formulaciones son abiertas, la respuesta correcta es dar al modelo mejor andamiaje y dejarle juzgar. Recurrir ahí a una lista de palabras no es prudencia: es sustituir el único componente que podría haber resuelto el caso.

Así que las dos mitades apuntan en direcciones opuestas y comparten causa. Sospecha del modelo donde el fallo es del diseño, y desconfía del modelo donde el modelo *es* el diseño. Las dos son fallos de calibración sobre qué es en realidad un sistema con un modelo de lenguaje dentro — y diría que la segunda sale más cara, porque la regla frágil tiende a sobrevivir en el código mucho después de que quien la añadió se haya ido a otra cosa.

## El mismo modelo a los dos lados

Ninguno de estos fallos es exótico. Son la textura corriente de construir este tipo de software con agentes, y quiero tener cuidado de no hacerlos sonar peores de lo que son: en casi todos estos casos el trabajo del agente fue bueno y el arreglo, una vez señalado, fue competente.

Pero el patrón se sostiene, y lo que lo vuelve extraño es la simetría que rompe. Un agente depurando un servidor web no concluye que la CPU es poco fiable. Busca el error, y lo busca en el código, porque el código es donde viven los errores. Mete un modelo de lenguaje en el sistema y ese mismo agente empieza a tratar una capa como si fuera el tiempo atmosférico: algo que te pasa, en vez de algo que alguien construyó.

La capa que excusa es la que está ejecutando al agente que la excusa. Y eso es lo bastante raro como para que dejara de escribir sobre ello y me pusiera a medirlo: si la sospecha se mueve de verdad según lo que le enseñas al agente, y si se mueve por el motivo que parece. De eso va la siguiente pieza.

---

*Relacionado: [agentes de código y trabajo en equipo](/es/blog/coding-agents-structure), donde una pregunta parecida —¿esto es un problema de capacidad o de estructura?— resultó tener la misma respuesta; y [qué prácticas ayudan de verdad a un agente](/es/blog/practices-for-agents-substrate), medido sobre 750 corridas.*
