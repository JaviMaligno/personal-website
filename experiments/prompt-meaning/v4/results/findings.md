# Un resumen conserva la definición y pierde una condición del programa

La cuarta prueba usa mantenimiento de un proyecto existente, tres traspasos
sucesivos y cambios concretos que deben respetar el comportamiento del código.
El resultado más claro es una discrepancia entre una definición transmitida y
el procedimiento que asigna la marca correspondiente. La sustitución de nombres
no corrige esa discrepancia. No hemos demostrado un lenguaje inventado compartido
por agentes, ni identificado quién acuñó los términos originales.

## El caso concreto

En `code-world-models`, `refine_capped` mantiene una muestra fija de observaciones
que se pueden mostrar al modelo, pero evalúa su código contra un conjunto mayor.
Cuando quedan errores que no pertenecen a la muestra permitida, puede detener
la reparación con `evidence_capped_failure=True`.

El procedimiento actual inicializa esa marca en `False` y la modifica dentro
del bucle de reparación:

```python
evidence_capped_failure = False
while acc < 1.0 and iterations < max_iters:
    # ... tratamiento separado de errores de infraestructura ...
    feed = [f for f in failures if f["source_index"] in allowed_source_indices]
    if not feed:
        evidence_capped_failure = True
        break
    # ... llamada de reparación ...
```

Es un extracto explicativo; la [fuente completa](../sources/evidence_dose.py)
incluye la excepción de los errores de infraestructura. Con `max_iters=0`, el
bucle no se ejecuta y la marca sigue en `False`.

El primer traspaso generado por GPT resume la condición así:

> An `evidence_capped_failure` occurs when gate accuracy is below 1.0 but no remaining attributable failure belongs to the allowed set. It stops refinement immediately.

Tras GPT → Claude → GPT, el tercer traspaso conserva esta formulación:

> Gate accuracy below 1.0 with no attributable allowed failure is `evidence_capped_failure` and stops refinement.

La definición ya no menciona el requisito de entrar en el bucle. Esto estaba
omitido desde el primer resumen: **no es un error nuevo introducido en el tercer
traspaso**, ni una condición que podamos afirmar que otro agente recuperó.

La sonda que separa ambas interpretaciones fija todos los datos: exactitud 0,8;
únicos errores en los índices `{311,512}`; índices permitidos `{7,8,9}`;
`max_iters=0`; ningún error de sintaxis o infraestructura. Se pregunta si devolver
la marca en `True` conserva el comportamiento actual. La respuesta correcta es
rechazar ese cambio. Se comprobó ejecutando la función original con evaluación
y proveedor simulados, sin llamadas a un modelo para decidir el resultado.

| Contexto | GPT, dos repeticiones | Claude, dos repeticiones |
|---|---|---|
| Código, planes y tests originales | Rechaza; una respuesta inválida | Rechaza; rechaza |
| Primer traspaso | Acepta; acepta | Pide contexto; pide contexto |
| Tercer traspaso | Acepta; acepta | Acepta; pide contexto |
| Tercer traspaso con etiquetas opacas | Acepta; acepta | Acepta; acepta |

Una de las justificaciones de GPT con el último traspaso fue:

> With accuracy below 1.0, no failure attributable to an allowed source, and zero permitted iterations, returning evidence_capped_failure with zero repair iterations preserves the specified behavior.

La respuesta sigue la definición recibida y contradice el comportamiento del
programa. Cambiar el identificador por `flag_q7` no lo arregla. La respuesta
malformada del control de GPT se excluye completa: no se rescatan decisiones de
su JSON incompleto. Por eso no satisface el criterio original de dos controles
completos correctos para declarar una diferencia estable frente a ese control.

Con ese mismo tercer traspaso, ambos modelos habían acertado las 16 propuestas
de mantenimiento de la prueba principal en ambas repeticiones: 64/64 decisiones
en el área de evidencia. Ese éxito no detectó la condición perdida. La sonda
específica se añadió después de leer las notas, con su motivación y expectativas
congeladas antes de hacer las llamadas adicionales.

## Qué cambió respecto a los pilotos anteriores

- Ocho archivos preexistentes: un diseño, un plan extenso, módulos y tests de
  regresión de dos áreas del proyecto. Sus copias coinciden byte por byte con
  versiones públicas descargadas de GitHub sin autenticación.
- Los redactores prepararon notas de mantenimiento para otro agente. No se les
  pidió inventar términos ni conservar una etiqueta concreta.
- Tres sesiones sucesivas con objetivos de 650, 450 y 350 palabras. Los límites
  eran orientativos; no se cortó mecánicamente ninguna nota.
- Los receptores revisaron propuestas de cambio con posibilidad de pedir más
  contexto. Se compararon dosier completo, primera nota, tercera nota y tercera
  nota renombrada, con dos modelos y dos repeticiones.

Sigue siendo una simulación de traspasos sin recuperación de archivos. Las
propuestas de cambio son sondas construidas a partir del proyecto, no PRs
históricas ni modificaciones que se aplicaran y probaran después. Esas
limitaciones impiden llamarlo un estudio de agentes desplegados en producción.

## Resultado principal y límites de ejecución

Se planearon cuatro cadenas. Las dos iniciadas por Claude produjeron respuestas
vacías con `finish_reason=refusal`; se conservaron y no se repitieron. Completaron
las tres etapas las dos cadenas iniciadas por GPT, con Claude en el segundo
traspaso. El control con dosier completo sí produjo revisiones válidas en ambos
modelos. El proveedor no explicó los dos rechazos iniciales.

| Contexto | Aciertos | Errores | Peticiones de contexto |
|---|---:|---:|---:|
| Dosier completo | 128 | 0 | 0 |
| Primera nota | 126 | 0 | 2 |
| Tercera nota | 126 | 0 | 2 |
| Tercera nota renombrada | 125 | 2 | 1 |

Las 32 revisiones principales fueron válidas. No hubo un error estable nuevo
entre primera y tercera nota bajo los criterios fijados. Hubo un cambio estable
de petición de contexto a respuesta correcta al renombrar el contexto de
geometría; no era una regresión. Las dos decisiones equivocadas de la condición
renombrada proceden de **una misma interpretación en una misma respuesta**,
no de dos hallazgos independientes.

La propuesta inicial sobre cero iteraciones no aislaba bien la condición del
bucle: también podía rechazarse por otro motivo. Esa insuficiencia se documentó
antes de leer los resultados principales. El [suplemento](../SUPPLEMENT.md) fija
explícitamente que todos los fallos quedan fuera de los índices permitidos y
conserva aparte sus cuatro casos y dieciséis llamadas.

## La explicación léxica que no se reprodujo

En una respuesta de geometría con todos los nombres sustituidos, GPT interpretó
`on failure` como un error al calcular IoU, en lugar del fallo de la comprobación
de invariancia descrita en la frase anterior. La otra repetición fue correcta.

Se hizo un [seguimiento factorial separado](../FACTOR-CHECK.md): conservar o
renombrar únicamente `non_positional`, y conservar `on failure` o sustituirlo por
`when preimage_invariant returns False`. Cinco llamadas por combinación, solo
al modelo que había cometido ese error, con las demás instrucciones intactas.

| Referencia | Nombre | Pares de decisiones objetivo correctos / respuestas válidas |
|---|---|---:|
| Implícita | Original | 5/5 |
| Implícita | Opaco | 4/4; una respuesta inválida |
| Explícita | Original | 5/5 |
| Explícita | Opaco | 5/5 |

La confusión no volvió a aparecer en las 19 respuestas válidas. El seguimiento
no permite atribuir el error original a esa etiqueta ni demostrar que aclarar
el referente lo corrige. Tampoco repite la sustitución global original: comprueba
una explicación concreta de ella. No se añadieron más variantes al obtener este
resultado.

## Qué sostiene la evidencia

En este caso, una nota redactada por un agente convirtió una condición evaluada
dentro de un procedimiento en una definición que parecía aplicable fuera de él.
Otro agente pudo usar esa nota con éxito en los cambios examinados y, ante el
caso que separaba ambos significados, justificar una modificación incorrecta.
La repetición del nombre no aseguraba que se hubiera preservado la condición de
uso del programa.

La evidencia apoya ese caso de pérdida de una condición al resumir y su
consecuencia en la revisión. No mide la frecuencia del fenómeno, comprensión
humana, aparición espontánea de jerga ni un lenguaje privado entre modelos.
Tampoco prueba que las etiquetas fueran su causa. Los dos seguimientos son
exploratorios y su selección posterior está documentada.

## Registro y coste

76 llamadas y 76 intentos: 40 principales, 16 del suplemento y 20 del seguimiento
factorial. Dos generaciones vacías por rechazo; dos revisiones con JSON inválido
(una en cada seguimiento), excluidas completas. No hubo reintentos de llamadas
a modelos. Los fallos de arranque de autenticación ocurrieron antes de las
llamadas y se registran aparte.

Coste de referencia total: **4,968829 USD**, calculado con las tarifas utilizadas
en los pilotos anteriores; no es una factura ni aplica descuentos de caché.
Transcurrieron 29 min 7 s entre la primera y la última llamada, incluyendo el
análisis intermedio y la preparación de los seguimientos; ese tiempo no incluye
el diseño y validación anteriores a la primera llamada.

Archivos: [protocolo inicial](../DESIGN.md), [datos principales](data.json),
[informe principal](report.md), [datos del suplemento](supplement-data.json),
[verificación del caso contra el código](supplement-oracle-check.json),
[seguimiento factorial](factor-report.json), [recuentos y costes](summary.json).
La anotación semántica la realizó Codex y está identificada como tal; no es una
revisión humana independiente. Se conservan las tres tandas anteriores.
