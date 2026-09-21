# Piloto: explicar una instrucción y predecir su efecto

**Ejecutado el 21 de septiembre de 2026. La hipótesis principal queda sin medir.**
La revisión de los 40 prompts no identificó ninguna expresión que cumpliera el
criterio fijado: ausente del encargo, usada para dirigir decisiones y sin una
definición operativa suficiente. Los dos controles funcionaron en ambos modelos.

## Qué se ejecutó

Se usaron GPT-5.6 Sol mediante el gateway existente y Claude Opus 5 mediante
Vertex global, con las credenciales y la sesión de nube ya disponibles. No se
necesitaron claves directas de OpenAI ni Anthropic. Los identificadores públicos
en los datos son `gpt-sol` y `claude-opus`, respectivamente.

Se fijaron 8.192 tokens máximos de salida en ambos; temperatura 1 en GPT y
razonamiento adaptativo sin temperatura en Claude. Cada petición tuvo contexto
nuevo. Los modelos y parámetros se mantuvieron entre fases.

| Fase | Llamadas | Resultado |
|---|---:|---|
| Generación: 20 encargos × 2 escritores | 40 | 40 respuestas completas; 0 candidatos elegibles |
| Predicción: 2 controles × 2 explicadores | 4 | 4 respuestas válidas, sin abstenciones |
| Ejecución: 2 controles × 2 variantes × 2 modelos | 8 | 8 respuestas válidas; ambos controles pasan |
| Total experimental | 52 | Sin errores de transporte, truncamientos ni reintentos |

Hubo además dos llamadas mínimas previas para comprobar conectividad, separadas
de estos datos. La generación tardó 10 min 15 s. Desde la primera generación
hasta la última ejecución transcurrieron 12 min 8 s, incluyendo los pasos de
revisión y congelación; no incluye la preparación del experimento.

La selección la realizó **Codex, mediante lectura de los textos completos**.
No hubo anotación humana independiente. Todos los motivos se conservan en el
[registro de selección](selection.md); este resultado depende también de ese
criterio de revisión y puede ser auditado.

## Qué permiten decir los resultados

En este banco, los modelos tendieron a reproducir reglas ya explícitas. Expresiones
como «All gates cleared» resumían condiciones definidas en el propio prompt.
«Safe-default evaluation» venía acompañada de valores concretos por campo.
Ninguna de esas apariciones se aceptó como instrucción técnica insuficientemente
definida. No se sustituyeron los encargos ni se pidió jerga para obtener casos.

El control positivo eliminaba «Deny if embargoed is true» y dejaba una instrucción
de permitir todos los registros. Ambos ejecutores cambiaron la decisión del
registro embargado de `deny` a `allow`, como habían predicho ambos explicadores.
En el control redundante se eliminaba una repetición de la misma regla: ninguno
cambió sus decisiones, también conforme a las predicciones.

Las 16 comparaciones de pares de acciones previstas y observadas coinciden.
**Son comparaciones sobre dos controles y dos entradas por control, reutilizadas
entre modelos; no son 16 pruebas independientes de la hipótesis.** Una repetición
verifica estos ejemplos sencillos, sin establecer estabilidad ni equivalencia.
Los `1/2` del control positivo eliminado en el informe automático comparan contra
la política original: reflejan el cambio deliberado, no un fallo del control.

El instrumento distingue los dos casos de comprobación. No se llegó a ejecutar
ningún prompt natural seleccionado. Por tanto, no se ha medido si una explicación
plausible de un término poco definido predice su efecto, ni si dos modelos le
atribuyen el mismo significado. Tampoco se midió confianza humana.

## Límite del diseño

El banco facilita una medición precisa entregando campos, reglas y prioridades
casi resueltos. A la vez, esa elección deja poco trabajo conceptual al escritor.
Mi interpretación es que el procedimiento de generación se parece demasiado a
una reescritura de algoritmos para reproducir el fenómeno que motivó la pregunta:
vocabulario que aparece durante discusiones abiertas y acaba en instrucciones.
Este piloto no comparó esas situaciones, por lo que esa explicación del resultado
es una hipótesis sobre el diseño, no un efecto demostrado.

Los veinte encargos proceden de cuatro plantillas. El resultado 0/40 no estima
la frecuencia general de jerga en agentes y no refuta el relato del post original.
La ausencia de candidatos tampoco demuestra que los prompts sean correctos.

## Una observación incidental

En `expense-01`, Claude conserva correctamente la regla «review si amount > 100»,
pero añade este ejemplo:

```text
amount=500, currency_matches=true, fraud_confirmed=false, receipt=true → allow
```

La respuesta que corresponde a las reglas es `review`. El ejemplo explica su
`allow` señalando que 500 no supera el límite de denegación de 500, pero omite el
umbral de revisión de 100. El candidato tiene ID
`d2ed76860ea81655cdc3a7a2e32dc0470c6e0bacaacda5c9fcce931be1b0794a`.

Es una contradicción verificable dentro del texto generado. No se probó qué
decisión tomaría otro modelo ante ella, ni se hizo una medición sistemática de
errores en ejemplos. No cuenta como evidencia sobre terminología ni sustituye
la pregunta original.

## Consumo y coste de referencia

| Modelo / ruta | Entrada | Salida | Estimación USD |
|---|---:|---:|---:|
| GPT-5.6 Sol / gateway | 4.831 | 3.438 | 0,0881 |
| Claude Opus 5 / Vertex global | 7.514 | 38.045 | 0,9887 |
| Total | 12.345 | 41.483 | **1,0768** |

Cálculo: tokens de entrada y salida reportados por cada proveedor, multiplicados
por tarifas de referencia de 4/20 USD por millón para
[GPT-5.6 Sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol) y 5/25 USD
para [Opus 5 en Vertex global](https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing),
consultadas al preparar la corrida. Claude no reportó tokens de caché.
No es una factura: el gateway puede tener otra tarifa. Excluye las dos comprobaciones
mínimas previas y la asistencia de Codex. No se utilizó cómputo externo adicional.

## Decisión sobre ampliar

No ampliar este banco con más repeticiones: no hay casos que intervenir.
Antes de otra corrida conviene fijar un corpus de prompts o conversaciones reales
de desarrollo, con una regla de muestreo independiente de que contengan jerga.
Conservar los requisitos originales permitiría construir las pruebas después
de seleccionar expresiones y antes de observar sus ejecuciones. La revisión humana
de elegibilidad sería especialmente útil en ese punto.

Una generación mediante varias rondas de diseño sería otra población distinta y
requeriría un protocolo nuevo; no debe mezclarse retrospectivamente con estos
40 candidatos. Ninguna de esas ampliaciones se ha ejecutado en este piloto.

Para el artículo, estos datos permiten contar lo que esta prueba pudo y no pudo
medir. No permiten afirmar todavía que los modelos racionalicen vocabulario vacío
o que se entiendan mediante conceptos que sus explicaciones no capturan.

## Archivos y comprobaciones

- [Datos exportados](data.json): encargos, 40 respuestas, selección, predicciones,
  ejecuciones, parámetros públicos, tokens y hashes de procedencia.
- [Informe automático](report.md) y [desglose JSON](report.json).
- [Diseño](../../../../docs/superpowers/specs/2026-09-21-invented-terminology-design.md)
  y [ejecutor](../../README.md).

El banco contrasta 240 etiquetas prefijadas con sus oráculos deterministas. La
suite local pasó sus 24 tests antes de la corrida. Los resultados artificiales de
los tests no se incluyen en estos datos. La exportación conserva las respuestas
textuales y elimina endpoints privados, proyectos, rutas de credenciales y
envelopes de los proveedores. Los originales permanecen en `runs/`, excluido de Git.
