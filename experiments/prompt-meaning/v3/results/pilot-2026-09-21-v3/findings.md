# La definición sobrevivió al traspaso

**Completado el 21 de septiembre de 2026.** Este estudio no encontró la pérdida
que buscaba: las siete guías válidas preservaron la regla al resumirse para otro
agente. Todas sus decisiones, incluidas las combinaciones reservadas, coincidieron
con la política original. Cambiar los cuatro nombres que seguían presentes tampoco
cambió decisiones. La evidencia no sostiene el mecanismo propuesto para el artículo.

## Qué se puso a prueba

El [protocolo previo](../../DESIGN.md) fijó cuatro políticas de trabajo de desarrollo:
recuperación de efectos de un cambio, aprobación ligada a revisión y alcance,
corroboración con fuentes compartidas, y permiso de reintento. Son reglas estipuladas
para una simulación, no políticas recomendadas para sistemas reales.

Cada escritor —GPT-5.6 Sol y Claude Opus 5— recibió una política completa y seis
ejemplos. Debía darle un nombre local y preparar una guía independiente. **La
creación del nombre fue solicitada**, no emergió espontáneamente.

Los seis ejemplos se eligieron antes de las llamadas para que una simplificación
concreta de la regla también los resolviese. El banco reservó otras catorce
combinaciones por tarea, incluidas cinco que separaban esa simplificación de la
regla original. No se cambió el significado de los campos ni la política al pasar
a esos casos: cambiaron sus combinaciones.

Ambos ejecutores probaron los ejemplos visibles. Otro llamado al modelo contrario
recibió la guía y esos resultados y redactó un resumen de hasta 80 palabras.
Disponía de la definición transmitida; no se la retiramos deliberadamente. No vio
la política de referencia separada ni los casos reservados. Las guías y todos los
prompts finales quedaron fijados antes de esas evaluaciones.

## Qué ocurrió

Una de las ocho generaciones originales, la de Opus para reintentos, terminó con
un JSON incompleto. El proveedor no la marcó como truncada por el límite de tokens.
Se conservó íntegra, no se reparó ni se volvió a pedir. Sus variantes dependientes
no estuvieron disponibles; los controles canónicos sí se ejecutaron.

Las otras siete guías pasaron los seis ejemplos visibles en los dos ejecutores.
Tras el traspaso, las siete conservaron todas las condiciones dentro del dominio
probado, según la lectura de Codex —no anotación humana independiente— guardada
en [semantic-review.json](semantic-review.json). Esa lectura se registró antes de
inspeccionar las decisiones finales, aunque las llamadas ya estaban en marcha.
Todas las guías resumidas cumplieron el límite solicitado: entre 70 y 77 palabras,
frente a entre 102 y 163 en sus originales.

| Instrucciones ejecutadas | Cadenas disponibles | Decisiones correctas / válidas / previstas |
|---|---:|---:|
| Política canónica completa | 8 controles pareados | 640 / 640 / 640 |
| Guía original del escritor | 7 | 560 / 560 / 560 |
| Guía resumida por el otro modelo | 7 | 560 / 560 / 560 |
| Resumen con el nombre sustituido | 4 | 320 / 320 / 320 |

Cada guía disponible se ejecutó con dos modelos y dos repeticiones, sobre veinte
entradas. Esos productos no crean miles de problemas independientes: seguimos
teniendo cuatro políticas y siete cadenas utilizables. Los controles canónicos
reutilizan las mismas cuatro políticas para mantener el orden de entradas pareado.

Las guías originales y resumidas acertaron **392/392 decisiones reservadas cada
una**, incluidas **140/140** en los casos que separaban la regla de su simplificación.
No hubo pérdidas repetidas, reparaciones necesarias, diferencias entre repeticiones
ni efectos observados del cambio de nombre. Las 104 respuestas de ejecución final
y las catorce de prueba visible cumplieron el formato exigido.

### Tres nombres dejaron de viajar, sus reglas no

En tres resúmenes el nombre permanecía en el campo de metadatos `term`, pero ya
no aparecía en `guide`, el texto que recibía el ejecutor. Son los dos resúmenes de
corroboración y el de aprobación escrito inicialmente por GPT. Las condiciones
de decisión sí estaban en sus guías y las ejecuciones fueron correctas.

Por ejemplo, el resumen de corroboración conservó la prohibición por contradicción,
la ruta de dos resultados favorables sin fuente compartida y la ruta alternativa
de una nueva comprobación ciega con al menos un resultado favorable. La etiqueta
«Corroboration Gate» no era necesaria para expresar esas distinciones.

En esos tres casos no había nombre que sustituir dentro de la guía. El contraste
se marcó como no disponible; no se contó como una intervención sin efecto. En los
otros cuatro se sustituyó exclusivamente el nombre por «velun protocol», manteniendo
la definición y el resto del texto. Esa intervención sí se ejecutó y no cambió
ninguna decisión observada.

## Qué podemos concluir

La hipótesis operativa era que un traspaso que conserva éxitos conocidos podía
perder una distinción y reconstruir otra en situaciones nuevas. **Aquí no ocurrió.**
Los agentes mantuvieron reglas que permitían resolver las situaciones no mostradas;
no se limitaron a copiar lo que los seis ejemplos distinguían.

No es evidencia de ausencia de este problema en desarrollo real. Las políticas son
cortas, completamente especificadas, usan campos booleanos descriptivos y caben en
el presupuesto del resumen. Hubo un solo traspaso, con instrucciones explícitas de
conservar condiciones y excepciones. No se midieron conversaciones largas, cambios
de requisitos, documentación acumulada, ejecución de código ni confianza humana.
El comportamiento correcto tampoco revela una representación conceptual interna
compartida.

El resultado no repara el argumento del borrador anterior. Apoya conservar la
distinción entre nombres y reglas, pero no proporciona un caso real de autoridad
adquirida por terminología accidental. No se ha reescrito el artículo alrededor
de una conclusión negativa exagerada ni se ha lanzado otra tanda buscando un fallo.

## Ejecución y artefactos

- **133 llamadas y 133 intentos:** ocho generaciones, catorce pruebas visibles,
  siete resúmenes y 104 ejecuciones finales. Sin errores de transporte ni reintentos.
- **6 minutos y 22 segundos** entre la primera y la última llamada, sin contar
  diseño, implementación o análisis.
- GPT: 65.856 tokens de entrada y 12.971 de salida; **0,522844 USD** de referencia.
- Claude: 96.921 tokens de entrada y 21.357 de salida; **1,018530 USD** de referencia.
- Total: **1,541374 USD**, usando las tarifas de referencia documentadas en el
  piloto anterior, no una factura. Excluye la asistencia de Codex y los otros pilotos.

Las rutas y parámetros fueron los previamente disponibles: GPT por gateway con
temperatura 1, Claude por Vertex global con razonamiento adaptativo, 8.192 tokens
máximos de salida y concurrencia dos. Las credenciales se conservaron solo en la
memoria del proceso. Los originales privados permanecen excluidos del repositorio.

[Datos públicos completos](data.json), [informe por cadena con las guías literales](report.md),
[recuentos y decisiones](report.json), [revisión textual de Codex](semantic-review.json).
El código está en [v3](../../README.md); los tres tests locales incluyen un recorrido
de 160 respuestas artificiales que verifica detección de pérdida, efecto del nombre,
salida inválida, aislamiento de los casos reservados y ausencia de reintentos ocultos.
