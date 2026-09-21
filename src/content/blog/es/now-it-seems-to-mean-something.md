---
title: "La definición parecía completa"
description: "Un agente resumió código real para otro. La nota permitió acertar 16 revisiones de cambios, pero había convertido una condición del programa en una regla más amplia."
pubDate: 2026-12-14
tags: ["IA", "Agentes", "Evaluación"]
lang: es
translationKey: now-it-seems-to-mean-something
heroImage: "/blog/now-it-seems-to-mean-something-v4.png"
linkedinImage: "/blog/now-it-seems-to-mean-something-fig-2.png"
repoUrl: "https://github.com/JaviMaligno/code-world-models"
linkedinLinks:
  - label: "Post de Mathias Strasser"
    url: "https://www.linkedin.com/posts/mathias-strasser-6990594_today-i-have-something-interesting-to-share-share-7505892928104570880-nI6R/"
---
<style>
.meaning-fig { margin: 2rem 0; }
.meaning-fig img, .meaning-fig svg { display: block; width: 100%; height: auto; border-radius: 6px; margin: 0; }
.meaning-fig figcaption { color: #94a3b8; font-size: .9rem; line-height: 1.55; margin-top: .7rem; }
</style>

Un agente recibió código, documentación y tests de un proyecto mío. Su encargo era preparar una nota para otro agente que iba a revisar cambios de mantenimiento. En esa nota explicó qué significaba una de las marcas que devuelve el programa.

La definición era clara. Pasó por otros dos traspasos y seguía siendo clara. Con la última nota, dos modelos acertaron las 16 propuestas de cambio de la prueba inicial, en ambas repeticiones.

Sin embargo, la definición había perdido una condición. Al construir un caso que separaba lo escrito en la nota de lo que hacía el código, GPT aceptó un comportamiento incorrecto y lo justificó recurriendo a esa misma definición.

Eso es lo que me interesa del caso: **un agente puede trabajar bien con una explicación que ya ha cambiado el significado operativo de lo que explica.**

## Una palabra con una definición razonable

La pregunta venía de [un post de Mathias Strasser](https://www.linkedin.com/posts/mathias-strasser-6990594_today-i-have-something-interesting-to-share-share-7505892928104570880-nI6R/) sobre la terminología que inventan los LLM. Su preocupación era qué ocurre cuando esas expresiones terminan en prompts escritos por un agente para otro. El siguiente modelo puede parecer que las entiende mientras la persona que mantiene el sistema pierde la capacidad de seguir la conversación.

Quise examinar qué conserva realmente un agente cuando transmite una explicación técnica. Para eso utilicé código, planes y tests de [mi proyecto Code World Models](https://github.com/JaviMaligno/code-world-models). Una de las tareas consistía en preparar instrucciones para revisar cambios de rendimiento en un proceso de generación y reparación de código.

Ese proceso enseña al modelo una muestra de observaciones y evalúa el código generado contra un conjunto mayor. Durante la reparación solo puede mostrarle errores pertenecientes a la muestra permitida. Así se puede estudiar qué consigue corregir con una cantidad acotada de evidencia.

Hay una marca llamada `evidence_capped_failure`. El primer agente la explicó así:

> An `evidence_capped_failure` occurs when gate accuracy is below 1.0 but no remaining attributable failure belongs to the allowed set. It stops refinement immediately.

En castellano: quedan errores, pero ninguno pertenece al conjunto que se permite enseñar al modelo; por tanto, se detiene la reparación y se marca el fallo como limitado por la evidencia disponible.

Es una explicación útil. Distingue esa situación de un error de sintaxis o de ejecución, que se trata por otra vía. Conserva la diferencia entre lo que se evalúa y lo que se puede mostrar. También encaja con el nombre de la marca.

El detalle que falta está en el lugar del programa donde se comprueba todo eso.

## La condición estaba fuera de la definición

La [función original](https://github.com/JaviMaligno/code-world-models/blob/e2e061a8112d1576728e00912b92df455049b4d5/src/cwm/continuous/evidence_dose.py) inicializa la marca en `False` y la cambia dentro del bucle de reparación. Este extracto omite el tratamiento separado de los errores de infraestructura y el cuerpo de la llamada al modelo:

```python
evidence_capped_failure = False

while acc < 1.0 and iterations < max_iters:
    # ... tratamiento de errores de infraestructura ...
    feed = [f for f in failures
            if f["source_index"] in allowed_source_indices]
    if not feed:
        evidence_capped_failure = True
        break
    # ... reparación e incremento de iterations ...
```

Con cero iteraciones permitidas, el bucle no se ejecuta. La marca sigue en `False`, aunque los errores conocidos estén fuera de la muestra permitida.

La nota había convertido una descripción de lo que ocurre **dentro de un procedimiento** en una definición aplicable directamente a los datos. El código exige haber entrado en el bucle; la definición abreviada solo exige que queden errores fuera del conjunto permitido.

Esa diferencia puede desaparecer a la vista si uno se pregunta qué significa el nombre. Las palabras *evidence-capped failure* encajan bastante bien con un código imperfecto al que no se le van a mostrar más ejemplos. Pero el campo del resultado tiene el comportamiento concreto que implementa la función, incluido cuándo puede establecerse.

Se podría decidir que el programa debería calcular esa marca antes del bucle. Sería una modificación del comportamiento. En esta prueba el encargo era conservarlo durante un refactor de rendimiento, así que esa decisión no estaba autorizada por la tarea.

## El traspaso conservó la frase

El primer resumen lo escribió GPT-5.6 Sol. Una sesión nueva de Claude Opus 5 lo convirtió en una nota de revisión, y otra sesión nueva de GPT preparó la nota de arranque para el siguiente agente. Cada receptor veía solo el texto recibido; no podía recuperar los archivos originales. Los objetivos de extensión eran progresivamente menores, sin cortar mecánicamente las respuestas.

<figure class="meaning-fig">
<picture>
<source srcset="/blog/now-it-seems-to-mean-something-fig-1-es.png" type="image/png">
<img src="https://www.javieraguilar.ai/blog/now-it-seems-to-mean-something-fig-1-es.png" alt="La condición de entrada al bucle faltaba ya en la primera nota. Los siguientes traspasos conservaron la definición abreviada." aria-label="La condición de entrada al bucle faltaba ya en la primera nota. Los siguientes traspasos conservaron la definición abreviada." loading="lazy">
</picture>
<figcaption>La condición de entrada al bucle faltaba ya en la primera nota. Los siguientes traspasos conservaron la definición abreviada.</figcaption>
</figure>

La última nota decía:

> Gate accuracy below 1.0 with no attributable allowed failure is `evidence_capped_failure` and stops refinement.

La condición de entrada al bucle faltaba ya en la primera nota. Los siguientes traspasos conservaron esa definición abreviada. Esto importa para localizar el fallo: aquí no observé una regla correcta que se fuese deformando un poco en cada relevo. La primera explicación ya abarcaba más casos que el procedimiento del que procedía.

Y, aun así, la última nota permitió acertar las 16 propuestas iniciales del área de evidencia con ambos modelos y dos repeticiones. Eran cambios sobre cuestiones como conservar los índices originales, evaluar contra el conjunto completo, evitar que se filtraran ejemplos positivos en el fondo o distinguir un fallo de infraestructura. La nota retenía suficiente información para resolverlos.

## El caso que separa los dos significados

La comprobación adicional fijó una situación concreta: quedaban dos errores, ambos fuera del conjunto permitido, no había ningún problema de infraestructura y el número máximo de iteraciones era cero. La propuesta era devolver `evidence_capped_failure=True` sin hacer llamadas de reparación.

Según el código vigente, esa propuesta debe rechazarse. La expectativa se comprobó ejecutando la función original con una evaluación simulada. No dependía del juicio de otro LLM.

Se compararon el dosier completo, la primera nota, la última y una copia de esta con etiquetas opacas. Entre otras sustituciones, `evidence_capped_failure` pasaba a llamarse `flag_q7`, tanto en las instrucciones como en la propuesta.

<figure class="meaning-fig">
<picture>
<source srcset="/blog/now-it-seems-to-mean-something-fig-2-es.png" type="image/png">
<img src="https://www.javieraguilar.ai/blog/now-it-seems-to-mean-something-fig-2-es.png" alt="La propuesta devuelve True donde el código devuelve False. Las etiquetas opacas no corrigen la aceptación incorrecta. Son dos repeticiones del mismo caso por condición y modelo." aria-label="La propuesta devuelve True donde el código devuelve False. Las etiquetas opacas no corrigen la aceptación incorrecta. Son dos repeticiones del mismo caso por condición y modelo." loading="lazy">
</picture>
<figcaption>La propuesta devuelve True donde el código devuelve False. Las etiquetas opacas no corrigen la aceptación incorrecta. Son dos repeticiones del mismo caso por condición y modelo.</figcaption>
</figure>

Con los resúmenes, GPT aceptó el cambio en ambas repeticiones de las tres condiciones. Una de sus razones fue, traducida:

> Con una exactitud inferior a 1,0, ningún fallo atribuible a un índice permitido y cero iteraciones disponibles, devolver `evidence_capped_failure` con cero iteraciones de reparación conserva el comportamiento especificado.

Con el dosier completo, su única respuesta válida rechazó el cambio; la otra tenía JSON incompleto y se excluyó entera. Claude rechazó el cambio en las dos respuestas con el dosier. Con la primera nota pidió contexto dos veces; con la última, una vez lo pidió y otra aceptó; con las etiquetas opacas aceptó las dos veces.

Son repeticiones de **un mismo caso**, no descubrimientos independientes ni una estimación de cuántos traspasos fallan así. La comprobación se diseñó después de examinar los resúmenes: es una sonda exploratoria de una omisión observada. Las expectativas quedaron fijadas antes de sus llamadas.

## Lo que el acierto había dejado sin comprobar

Los agentes podían usar el término, explicar la condición y coincidir en muchas decisiones. Ninguna de esas cosas obligaba a distinguir entre dos lecturas: «los datos cumplen esta condición» y «el procedimiento ha llegado al punto en que comprueba esta condición».

En el caso de cero iteraciones, esa distinción decide el resultado. Una definición que parecía describir el programa se había convertido en una pequeña especificación alternativa. El siguiente agente podía seguirla con bastante fidelidad y proponer un cambio que rompía el comportamiento que debía conservar.

El nombre sobrevivió. Lo que dejó de viajar con él fue una condición de uso que estaba expresada en la estructura del código.

Esto acota también lo que puedo decir sobre la preocupación que motivó la prueba. No he establecido quién acuñó estos términos ni medido cómo los entienden las personas. Cambiar los nombres no corrigió el error de este caso. En otra parte de la prueba apareció una posible confusión al renombrar una categoría; su explicación léxica no se reprodujo en las 19 respuestas válidas del seguimiento. No tengo base para atribuir este resultado a que dos modelos compartan una jerga privada.

Sí tengo un ejemplo de cómo una explicación suficientemente útil puede pasar a ocupar el lugar de la especificación. Volver a explicar la palabra puede dejar intacta esa diferencia. Aquí se hizo visible con una situación en la que las dos lecturas dejaban de coincidir.

Para una marca como esta, preguntaría qué permite al programa establecerla y qué devuelve cuando ese paso no ocurre. Esa información forma parte de su significado operativo. Si el próximo agente solo recibe la definición, tiene motivos para tratarla como una regla general.

La frase que faltaba era corta: «Esta marca solo puede establecerse dentro del bucle de reparación». Todo lo demás podía estar bien escrito, ser comprensible y ayudar a resolver la tarea. Esa frase seguía haciendo falta.

---

*Prueba con dos áreas de mantenimiento de un único proyecto y traspasos simulados sin acceso a los archivos. Completaron la cadena dos de los cuatro inicios previstos; los otros dos devolvieron respuestas vacías marcadas como rechazo por el proveedor. La prueba principal y los dos seguimientos sumaron 76 llamadas, con dos revisiones de formato inválido excluidas completas. Coste de referencia: 4,97 USD. El [archivo de código y datos (ZIP)](/downloads/prompt-meaning-pilots.zip) contiene las fuentes, prompts, respuestas, exclusiones y los pilotos anteriores. El informe de esta prueba está en `v4/results/findings.md` dentro del archivo; los seguimientos se documentan por separado.*
