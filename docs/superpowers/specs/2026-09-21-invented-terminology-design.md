# Cuando una expresión empieza a parecer un concepto

Fecha: 2026-09-21
Estado: enfoque editorial y experimento aprobados en conversación; banco y ejecutor
implementados en `experiments/prompt-meaning/`. Piloto empírico iniciado el
21 de septiembre de 2026; resultados pendientes de análisis.

Título provisional del artículo: **Ahora parece que significa algo**.

## 1. Origen y argumento

El punto de partida es un post ajeno de LinkedIn, facilitado por Javier en la
conversación. Su autor describe expresiones técnicas introducidas por un LLM que
después pueden acabar en prompts para otros agentes. El autor y el enlace del post
están pendientes de identificar para atribuirlo en el artículo. La clasificación
del vocabulario que relata es una respuesta del propio modelo, no una auditoría
independiente de qué términos existen en la literatura.

La aportación que queremos explorar: **un modelo puede interpretar una instrucción
lo bastante bien como para ocultar lo mal definida que está**. Un resultado útil
puede dar autoridad a una formulación accidental. Después, una explicación
convincente parece justificar retrospectivamente que esa formulación exista.

La pregunta empírica es más estrecha:

> ¿La explicación que da un modelo sobre una instrucción permite predecir qué
> efecto tiene esa instrucción sobre las decisiones de otro agente?

La pregunta editorial más amplia es cómo una expresión adquiere autoridad: se
conserva, se documenta y se construyen otras instrucciones alrededor de ella antes
de comprobar qué distinción permite hacer.

### Límites del enfoque acordado

- Inventar vocabulario puede ser útil. Un término local no es por ello falso,
  innecesario ni una alucinación.
- Resolver la tarea con una expresión presente no identifica su contribución.
- Que eliminarla no cambie decisiones puede significar redundancia.
- Una explicación fluida no demuestra interpretación compartida.
- Este experimento no mide la confianza ni la atribución de autoridad de humanos.
  Ese mecanismo seguirá siendo una hipótesis editorial salvo que se estudie con
  lectores humanos.
- La voz y el nivel del blog sirven como contexto. No convertir esta pieza en una
  recapitulación de los artículos anteriores sobre ontologías, memoria o mensajes.
- Evitar reconducir el argumento a la observación genérica de que escribir prompts
  implica tomar decisiones de diseño: ese enfoque fue descartado en conversación.

## 2. Generación y selección de casos

Preparar un banco fijo de 20 encargos de redacción de prompts, repartidos entre
varias tareas con decisiones verificables. Un ejemplo de dominio es decidir qué
acciones permite una política operativa. No ejecutar acciones externas: las
respuestas son decisiones dentro de un entorno simulado.

Cada encargo tendrá, antes de llamar a modelos:

- requisitos originales y política de referencia;
- entradas y acciones posibles;
- un oráculo determinista que compruebe las decisiones;
- casos ordinarios y casos en las fronteras de las reglas;
- identificador estable y orden de muestreo fijado.

Dos modelos redactarán una vez cada encargo: 40 prompts candidatos. El pedido será
redactar instrucciones utilizables por otro agente. No pedir sofisticación,
terminología propia ni invención de conceptos. Archivar también los prompts donde
no aparezca ningún caso elegible.

Un caso es elegible cuando el autor del prompt introduce una expresión ausente del
encargo, la usa para dirigir decisiones y no proporciona una definición operativa
suficiente. Registrar la expresión literal, su contexto y el requisito original al
que parece referirse, si existe. No llamarla «término inventado» solo porque no
aparece en el encargo: podría ser terminología establecida. Esa procedencia se
revisa por separado antes de usar esa descripción en el artículo.

Seleccionar los primeros diez casos elegibles siguiendo el orden prefijado, como
máximo uno por encargo. Revisar manualmente la selección antes de observar ninguna
ejecución. Registrar todas las exclusiones con su motivo.

Si hay menos de diez, conservar el denominador y trabajar con los disponibles. No
reescribir encargos hasta obtener la clase de jerga que esperamos encontrar. Una
baja frecuencia en este banco limita la premisa del experimento.

## 3. Variantes de cada prompt

| Variante | Intervención |
|---|---|
| Original | Prompt tal como lo escribió el agente. |
| Eliminada | Eliminar la cláusula que contiene la instrucción elegida. |
| Sustituida | Cambiar solo la expresión por otra de apariencia técnica, sin relación deliberada con la tarea. |
| Explícita | Sustituir la cláusula por condiciones concretas procedentes del requisito original. |

Guardar los textos completos y sus diferencias exactas. No mejorar el resto de
la redacción al preparar las variantes. La sustitución debe conservar la función
gramatical; fijarla antes de observar las respuestas.

**La eliminación afecta a una cláusula, no solo a un nombre.** Por tanto mide la
contribución de esa instrucción completa. La sustitución se acerca más al efecto
del vocabulario manteniendo el resto del texto. No atribuir automáticamente el
resultado de la primera al término aislado.

La versión explícita solo existe cuando el requisito correspondiente estaba en el
encargo. No obtener su definición preguntando después al modelo qué quiso decir.
Cuando el agente haya añadido una política sin correspondencia, marcar la variante
como no aplicable y conservar el caso en las otras comparaciones.

La versión explícita puede aportar información que el prompt original perdió; no
es un control de longitud ni una paráfrasis garantizada. La versión sustituida
tampoco demuestra que el reemplazo carezca de asociaciones para el modelo. Ambos
límites deben acompañar la interpretación.

## 4. Explicaciones y predicciones antes de ejecutar

En sesiones nuevas, cada uno de los dos modelos leerá el encargo y las variantes
de un caso, sin ver ninguna ejecución. No revelar qué modelo escribió el prompt,
la hipótesis editorial ni que se sospecha del vocabulario.

Pedir:

1. Qué comportamiento exige la expresión y qué parte del texto lo respalda.
2. Si espera diferencias al eliminarla o sustituirla. Permitir explícitamente
   «ninguna diferencia», «es redundante» y «no se puede determinar».
3. Para cada caso de prueba fijo, la decisión prevista bajo cada variante.
4. Hasta tres ejemplos adicionales donde espera una diferencia, con las
   decisiones concretas previstas en ambas condiciones.

Congelar todas las predicciones antes de ejecutar los prompts. La prosa explicativa
se archiva, pero la prueba principal es la predicción de acciones observables.
No forzar al explicador a inventar un contraste cuando no lo encuentra.

Los ejemplos adicionales se validan contra el dominio y sus reglas antes de
ejecutarlos. Mantenerlos separados del banco fijo: fueron propuestos por el
explicador y no constituyen una muestra independiente de tareas.

Cruzar explicador y ejecutor: las predicciones de cada modelo se contrastan con
las ejecuciones de ambos. Así se pueden distinguir interpretaciones compartidas
de predicciones que solo funcionan dentro de una familia.

## 5. Ejecución y controles

Los ejecutores reciben exclusivamente una variante y las entradas de la tarea.
Nunca ven las explicaciones, las otras variantes ni los resultados anteriores.
Cada llamada arranca con contexto limpio. Mantener las mismas herramientas,
presupuesto y parámetros entre variantes de un mismo modelo.

El piloto usa dos modelos, hasta diez prompts y unas doce entradas fijas por
prompt, además de las sondas válidas del explicador. Cada llamada puede devolver
un lote de decisiones independientes para contener el coste. Mantener el orden de
entradas pareado entre variantes y registrar ese orden. La llamada completa será
la unidad de repetición; sus doce respuestas no son doce sesiones independientes.

Añadir controles escritos a mano y declarados como tales:

- **Control positivo:** regla explícita cuya eliminación cambia la decisión
  correcta en casos frontera conocidos. Verificar ese cambio con el oráculo antes
  de llamar al modelo.
- **Control redundante:** instrucción cuya información aparece también en otra
  cláusula. Permite comprobar si el explicador reconoce que puede eliminarse sin
  cambiar el comportamiento esperado.

Los controles se reportan aparte del corpus espontáneo. Si el control positivo no
produce una diferencia detectable, revisar la sensibilidad de la tarea antes de
interpretar como ausencia de efecto los resultados del corpus.

Para cada respuesta guardar salida cruda, decisiones parseadas, errores de
formato, truncamiento, latencia, uso de tokens, modelo y configuración. Los fallos
de API no cuentan como decisiones incorrectas. Una respuesta inválida es un
resultado registrado; no reintentarlo silenciosamente hasta que sea correcto.

## 6. Qué se mide

Separar tres preguntas:

| Pregunta | Medida |
|---|---|
| ¿Resuelve la tarea? | Acierto contra la política original por variante. |
| ¿La intervención cambia algo? | Distribución de acciones y cambios pareados sobre las mismas entradas. |
| ¿La explicación predice el efecto? | Correspondencia entre decisiones/contrastes previstos y observados. |

Una diferencia entre variantes puede ser correcta o incorrecta. No confundir
cambio de comportamiento con mejora. Informar también de contradicciones entre
las predicciones de los dos explicadores.

En una fase con repeticiones, comparar para cada entrada las frecuencias de las
acciones previstas bajo cada variante. Una predicción del tipo «al quitarla,
permitir pasa a escalar» requiere que los datos respalden ambas partes del cambio,
no simplemente que alguna respuesta sea distinta.

Distinguir diferencias entre variantes de la variabilidad dentro de una misma
variante. Una sola ejecución por condición no permite hacerlo de forma fiable.

Presentar resultados por prompt, tarea y modelo antes del agregado. Para cualquier
inferencia posterior, agrupar por encargo de origen; las repeticiones y las entradas
de un mismo prompt no multiplican el número de conceptos independientes estudiados.

## 7. Tamaño y decisiones después del piloto

Primera pasada de viabilidad: una ejecución por modelo y variante. Con diez casos
y cuatro variantes son hasta 80 llamadas de ejecución del banco fijo, más 40 de
generación y 20 de explicación. Los controles, las sondas adicionales y los
reintentos de transporte se presupuestan aparte. Registrar los costes reales; no
elegir modelos ni publicar una estimación monetaria sin comprobar la configuración
y los precios disponibles al implementar.

Esta primera pasada sirve para revisar el instrumento, no para sostener un nulo.
Antes de ampliar:

1. Revisar a mano selección, variantes, oráculos y predicciones.
2. Comprobar que los controles miden lo que deben y que los casos admiten cambios.
3. Distinguir términos dudosos de instrucciones simplemente redundantes.
4. Usar repeticiones para estimar variabilidad y fijar qué magnitud de discrepancia
   merece una afirmación en el artículo.
5. Dimensionar la siguiente tanda a partir de esa precisión y del presupuesto.

Si se modifican criterios o tareas después de mirar los resultados, conservar la
primera tanda como exploratoria y validar el diseño revisado con casos nuevos.
No concluir equivalencia porque una diferencia no salga significativa: demostrar
equivalencia exige un margen fijado de antemano y precisión suficiente.

## 8. Resultados posibles y alcance

- **Las explicaciones predicen diferencias repetibles:** el vocabulario puede
  tener contenido operativo identificable. Esto limita la sospecha inicial.
- **Se anuncian contrastes que no aparecen con precisión suficiente:** evidencia
  de que esas explicaciones exageran o describen mal el efecto de la instrucción,
  compatible también con redundancia cuando corresponda.
- **El reemplazo recibe otra justificación elaborada sin el cambio anunciado:**
  caso especialmente relevante para la hipótesis editorial, siempre que sobreviva
  a los controles y las repeticiones.
- **El efecto varía por modelo:** interpretación poco transportable, aunque el
  término sí influya en las decisiones.
- **Pocos términos elegibles, controles fallidos o intervalos amplios:** el banco
  no sostiene la conclusión. Publicar ese límite o rediseñar; no fabricar una
  historia a partir de explicaciones llamativas.

## 9. Entregables siguientes

1. Banco de encargos, casos y oráculos comprobables.
2. Registro de selección y variantes, separado de resultados.
3. Runner con llamadas independientes, reanudación y registros completos.
4. Predicciones congeladas antes de ejecutar y análisis reproducible.
5. Informe del piloto con revisión manual y decisión sobre ampliar la muestra.
6. Artículo bilingüe construido sobre lo observado, con atribución al post de
   origen y figuras cuando existan resultados que representar.

La implementación y sus concreciones se registran a continuación. Este archivo
documenta el diseño; no programa ninguna publicación ni presupone resultados.

## 10. Implementación del piloto

Implementado en [experiments/prompt-meaning](../../../experiments/prompt-meaning/README.md)
dentro de este repositorio, siguiendo el precedente de `experiments/judge-bias`.
Python y biblioteca estándar, sin dependencias nuevas para el sitio.

Concreciones fijadas antes de obtener resultados:

- Banco de 20 encargos en inglés, cuatro familias de reglas y 240 decisiones con
  gold especificado. La unidad de diversidad es limitada: cinco contextos de una
  misma familia no son cinco dominios independientes.
- Orden de generación por encargo, alternando el escritor que se considera
  primero. Se retienen todos los candidatos y sus motivos de exclusión.
- Para el piloto, intervenciones sobre una única aparición inequívoca del término;
  otras formas se excluyen con motivo, sin eliminarse del registro.
- Dos controles adicionales (positivo y redundante), con dos variantes cada uno.
- Hasta 152 llamadas en la primera pasada completa: 40 para generación, 24 para
  explicaciones incluidos los controles, 88 para ejecuciones. Las sondas aceptadas
  se añaden al lote correspondiente y no requieren otra llamada. Se reportan por
  separado y se reconoce que compartir lote puede introducir dependencia.
- Fases congeladas mediante snapshots, sin reintentos invisibles de salidas
  inválidas ni acceso del ejecutor a explicaciones o gold.
- En esta fase solo se habían realizado comprobaciones locales con fixtures sintéticas. No usar
  esas respuestas como datos ni atribuirles conclusiones empíricas.

## 11. Conexión a la infraestructura existente (antes de la tanda real)

La primera implementación asumía APIs directas sin consultar el cliente de los
experimentos recientes. Se corrige para reutilizar las rutas de `llm-wrong-paste`:
GPT-5.6 Sol por el gateway existente y Claude Opus 5 por Vertex AI mediante la sesión
de `gcloud`. Los endpoints y datos del proyecto se mantienen privados.

Se han comprobado con una llamada mínima cada uno. Configuración fijada antes de
generar candidatos: 8.192 tokens máximos de salida en ambos, temperatura 1 en GPT y
razonamiento adaptativo sin temperatura en Claude. No se cambia de modelo entre
fases. El límite aumenta respecto al ejemplo de configuración para dejar margen a
razonamiento y predicciones completas.

La estimación inicial de generación es 5–15 minutos, 0,50–1,50 USD por el gateway
y 0,50–1,50 USD por Vertex, sin cómputo externo. Se recalcula con el uso registrado
antes de avanzar. Son estimaciones con tarifas de referencia, no facturas.

La selección inicial que haga Codex se identificará expresamente como revisión
por un modelo. No se presentará como anotación humana independiente. Los candidatos
y sus motivos permanecerán disponibles para la revisión humana del artículo.

## 12. Resultado del piloto real

Completado el 21 de septiembre de 2026: 40 generaciones, cuatro predicciones de
controles y ocho ejecuciones, sin reintentos ni errores. Codex revisó los 40 textos
y no identificó expresiones elegibles; esta selección no es anotación humana
independiente. Los controles positivo y redundante pasaron en ambos modelos.

La hipótesis principal queda sin medir. No se amplía el banco ni se fuerza la
aparición de vocabulario. El [informe completo](../../../experiments/prompt-meaning/results/pilot-2026-09-21/findings.md)
documenta el límite de la generación mediante reglas casi resueltas, los datos,
el consumo y una contradicción incidental que no se cuenta como evidencia sobre
terminología. Coste de referencia de las 52 llamadas: aproximadamente 1,08 USD;
no es facturación verificada. No se ha redactado ni publicado un artículo de
conclusiones empíricas sobre la hipótesis.

## 13. Segundo piloto solicitado por el usuario

El rediseño y la repetición se documentan aparte en
[v2/DESIGN.md](../../../experiments/prompt-meaning/v2/DESIGN.md), fijado antes de
las llamadas. Incorpora conversaciones de diseño en tres rondas y casos con
etiquetas sintéticas sin definición, sin presentar estos últimos como vocabulario
espontáneo. Los explicadores no ven la política completa y cada ejecución se
repite dos veces.

Se completaron 220 llamadas. Los ocho traspasos naturales no aportaron candidatos
terminológicos y acertaron las 384 decisiones examinadas. En los casos sintéticos
hubo una discrepancia estable entre predicción y ejecución para una etiqueta de
aprobación, además de otros efectos sobre decisiones. El
[informe completo](../../../experiments/prompt-meaning/v2/results/pilot-2026-09-21-v2/findings.md)
conserva denominadores, abstenciones, 17 salidas inválidas por formato y el incidente
de autenticación resuelto durante la corrida. No se mezclan sus datos con los del
primer piloto ni se ha publicado un artículo.
