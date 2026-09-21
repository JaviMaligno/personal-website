# Segundo piloto: contexto de diseño, instrucciones sin definición y predicciones

Fijado antes de las llamadas del segundo piloto, 21 de septiembre de 2026.
Los datos del primer piloto se conservan íntegros y no se mezclan con estos.

## Preguntas y alcance

1. En una conversación de diseño de tres rondas, ¿aparecen expresiones operativas
   cuya definición se pierde al transmitir las instrucciones a otro agente?
2. Ante una instrucción sin definición, ¿los modelos pueden predecir qué decisiones
   cambiarán al eliminarla o cambiar su nombre? ¿Se abstienen cuando falta información?

La primera pregunta es observacional y puede volver a producir cero candidatos.
La segunda se mide también con intervenciones sintéticas fijadas de antemano.
Un resultado sintético no demuestra frecuencia ni emergencia espontánea de jerga.
No se mide confianza humana, comprensión interna ni el efecto de usar herramientas.

## Generación natural: ocho conversaciones

Cuatro tareas diferentes: compartir datos, reembolsos, despliegues y retención.
Cada uno de los dos modelos desarrolla cada tarea en tres llamadas:

1. Propone un enfoque a partir de una necesidad descrita en prosa y tensiones entre criterios.
2. Revisa el enfoque cuando el responsable aclara las interacciones y excepciones.
3. Redacta un prompt independiente para un agente que no verá la conversación.

Las dos primeras respuestas tienen un límite solicitado de 350 palabras; el
traspaso, 180. Es una condición de compresión explícita, no una muestra de todos
los prompts reales. Los límites de palabras son instrucciones, no truncamientos
del programa; se conservan las respuestas aunque los incumplan. No se pide jerga,
nombres nuevos ni sofisticación. Se transmiten los turnos previos como texto
etiquetado dentro de una petición nueva, no como un chat persistente del proveedor.

Las reglas y 48 casos de referencia están fijados antes de generar. No se entregan
como una tabla de prioridades al escritor. Las cuatro familias proceden del primer
piloto; aquí cambia el procedimiento de generación, sin que exista una comparación
causal aleatorizada con aquel. Dos escritores por tarea no son ocho dominios.

Todos los ocho prompts finales utilizables se ejecutarán íntegros, incluso si no
contienen vocabulario elegible, contra los casos fijos. Eso mide fidelidad de los
traspasos a los requisitos y evita descartar silenciosamente errores sin jerga.

La revisión de elegibilidad la hará Codex, sin presentarla como anotación humana.
Se acepta una expresión ausente de las solicitudes del usuario, operativa y sin
definición suficiente en el prompt final. Puede estar definida en la conversación
previa: se anotará esa diferencia. Se elegirá el primer caso elegible por tarea,
hasta cuatro, antes de observar ejecuciones. Se conservarán todas las exclusiones.
No se supone que un término ausente de la solicitud sea nuevo en la literatura.

## Ocho casos sintéticos fijados sin depender de la generación

Por cada tarea se retira una regla de revisión de la política de referencia.
La política restante sigue determinando decisiones mediante su opción final de
permitir. Se añade una instrucción sin definición: «Before issuing the final
label, apply the [term]». Hay dos términos por tarea:

| Tarea | Regla retirada | Etiqueta sugerente | Etiqueta opaca | Reemplazo |
|---|---|---|---|---|
| Acceso | Falta aprobación del propietario | owner clearance closure | velun index | tavrel balance |
| Reembolsos | Importe >100 o moneda no coincide | amount currency alignment | navic alignment | lomar concordance |
| Despliegues | Irreversibilidad sin restauración probada | recovery readiness gate | tavrel balance | velun index |
| Retención | Aprobación requerida y ausente | conditional approval closure | lomar concordance | navic alignment |

Estos nombres son estímulos experimentales, no citas de agentes ni afirmaciones
de novedad terminológica. Las etiquetas sugerentes tienen pistas semánticas;
«opaco» tampoco garantiza ausencia de asociaciones aprendidas. Ningún nombre
recibe secretamente una definición que el modelo deba adivinar.

Cuatro condiciones por caso:

- Original: política parcial más instrucción sin definición.
- Eliminada: misma política parcial sin la instrucción.
- Sustituida: solo cambia el nombre de la instrucción.
- Explícita: política completa, con la regla retirada restaurada en su posición.

La condición explícita es una referencia de suficiencia de información y ejecución,
no un sinónimo demostrado del término ni una intervención de igual longitud.
Puede cambiar varias palabras y la ubicación de la regla. No atribuir a vocabulario
por sí solo una diferencia entre esa condición y las otras.

## Predicciones, aislamiento y repeticiones

Los dos explicadores reciben solo las tres primeras variantes, bajo letras
contrabalanceadas, el esquema y los inputs. **No ven la política original completa,
la variante explícita, la conversación de diseño ni resultados.** Así la explicación
no recibe por adelantado la definición que luego pretenderíamos que descubriera.
Pueden predecir igualdad o `undetermined`. Se piden acciones concretas para los
12 casos fijos. No se piden nuevos casos después de leer las respuestas.

Se congelan todas las predicciones antes de ejecutar. Cada ejecutor recibe una sola
variante y los inputs, sin las explicaciones ni otras variantes. Dos repeticiones
por combinación, con orden de casos y llamadas fijado mediante una semilla derivada
de sus IDs. Se cruzan los dos explicadores con los dos ejecutores.

Se repiten los controles positivo y redundante del primer piloto, también dos veces.
Las llamadas independientes pueden ejecutarse con concurrencia máxima de dos.
No hay reintentos automáticos ni selección de respuestas según el resultado.

## Análisis fijado

- Natural: número de términos elegibles sobre ocho traspasos; procedencia respecto
  de la discusión; corrección de los ocho prompts sin editar, por tarea y escritor.
- Sintético: decisiones exactas antes/después de eliminar y sustituir; concordancia
  de predicciones, abstenciones y referencia trivial de predecir «sin cambio».
- Separar términos sugerentes/opacos y los dos ejecutores. Comparar acciones, no
  puntuar la elocuencia de la explicación. El informe conserva también la prosa.
- Informar cambios entre repeticiones. Las comparaciones con ambas condiciones
  estables en las dos repeticiones se desglosan aparte. Dos repeticiones no prueban
  estabilidad general; inputs de un mismo lote no son observaciones independientes.
- La política completa debe producir las etiquetas de referencia. La parcial debe
  producir las de su oráculo sin la regla retirada. Se comprobarán ambos; el segundo
  es un control adicional de sensibilidad de los casos elegidos.
- Un modelo que reconozca la indefinición o prediga correctamente «sin cambio» no
  apoya la tesis de racionalización fallida. Una discrepancia tampoco demuestra por
  sí sola que no entienda: puede reflejar variación de ejecución o una predicción mala.

No habrá pruebas de significación ni una conclusión general basada en promediar
muchas decisiones de solo cuatro políticas. Los casos sintéticos, naturales y los
controles se reportarán por separado. No se generarán nuevos términos tras los
resultados para buscar discrepancias.

## Modelos, límite y coste

Mismos GPT-5.6 Sol por gateway y Claude Opus 5 por Vertex global y autenticación
existente. Máximo de 8.192 tokens de salida por llamada; GPT temperatura 1;
Claude razonamiento adaptativo sin temperatura. Endpoints y proyecto permanecen
en configuración local excluida de Git.

Sin candidatos naturales: 24 llamadas de generación, 20 de explicación y 176 de
ejecución, total 220. Con cuatro candidatos naturales y cuatro variantes: hasta
292 llamadas. La cifra real depende de si la variante explícita corresponde a
un requisito original. Se conserva el coste y tiempo de cada fase. Estimación
previa: 15–25 minutos de llamadas, 2–5 USD por gateway y 3–8 USD por Vertex,
sin cómputo externo. Son márgenes de referencia, no presupuestos de facturación.
