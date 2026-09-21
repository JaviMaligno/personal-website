# Prompt meaning pilot

¿La explicación de una instrucción predice su efecto sobre las decisiones de un
agente? Implementación del [diseño acordado](../../docs/superpowers/specs/2026-09-21-invented-terminology-design.md).

**Estado: piloto real completado el 21 de septiembre de 2026.** 52 llamadas,
0 candidatos elegibles entre 40 prompts y ambos controles superados por los dos
modelos. La hipótesis principal queda sin medir. Véase el
[informe de resultados y límites](results/pilot-2026-09-21/findings.md).
Los tests usan respuestas sintéticas declaradas, separadas de los datos empíricos.

**Segundo piloto:** el usuario pidió rediseñar y repetir. La
[versión 2](v2/README.md) incorpora conversaciones de tres rondas, casos sintéticos
controlados, predicciones sin acceso a la definición y dos repeticiones. Sus
[resultados](v2/results/pilot-2026-09-21-v2/findings.md) se mantienen separados de
este primer piloto.

**Tercer estudio:** [transmisión de una definición entre agentes](v3/README.md).
Compara guías originales y resumidas con ejemplos visibles y combinaciones
reservadas que separan la regla de una simplificación. Los nombres se solicitan
deliberadamente; tampoco es una medición de aparición espontánea de jerga.

**Cuarto estudio:** [traspasos sobre mantenimiento de un proyecto real](v4/README.md).
Parte de código, planes y tests ya existentes; evalúa tres traspasos sucesivos,
revisión de cambios y sustitución de etiquetas. Los controles adicionales se
documentan por separado y no se presentan como parte del diseño inicial.

Python 3.10+ y biblioteca estándar. No modifica el blog ni publica nada.

## Qué incluye

- 20 encargos en inglés: cuatro familias (acceso, reembolsos, releases y borrado
  por retención), cinco contextos por familia y 12 entradas por encargo.
- 240 respuestas esperadas especificadas antes de llamar a modelos, contrastadas
  con cuatro oráculos deterministas. Incluyen umbrales, igualdad y conflictos de
  prioridad. `bank.py` contiene el banco legible; cada run guarda una copia JSON.
- Generación natural de instrucciones sin pedir jerga; registro de los 40
  candidatos, incluidos los que no aporten ningún término elegible.
- Revisión explícita de elegibilidad; cuatro variantes por caso cuando proceda.
- Predicciones previas, dos explicadores cruzados con dos ejecutores, y sondas
  adicionales que deben revisarse antes de ejecutar.
- Controles positivo y redundante escritos a mano, separados del corpus natural.
- Reanudación, tope de llamadas, registros por intento, uso de tokens, respuestas
  crudas, latencia, truncamiento y errores de transporte.
- Informe con corrección, cambios pareados, predicciones exactas y frecuencias de
  acciones entre repeticiones. Sin pruebas de significación ni inferencias de
  equivalencia a partir del piloto.

Los veinte encargos **no son veinte dominios independientes**: comparten cuatro
plantillas. La variedad de contexto y umbrales sirve para probar el procedimiento.
El banco usa decisiones sobre registros estructurados; sus resultados no se
pueden generalizar directamente a agentes que programan o usan herramientas.

## Comprobarlo sin red

Desde este directorio:

```bash
python3 run.py validate-bank
python3 -m unittest discover -s tests -v
```

La suite recorre generación, revisión, selección, predicción, revisión de sondas,
ejecución y análisis en directorios temporales con respuestas artificiales. También
comprueba los límites, los controles, los IDs duplicados, el aislamiento de los
prompts y la recuperación tras errores. No necesita credenciales.

## Configurar una corrida

```bash
mkdir -p runs
cp config.gateway-vertex.example.json runs/pilot-config.json
```

Editar `runs/pilot-config.json` para que apunte a la infraestructura existente.
`config.example.json` conserva la alternativa de APIs directas para otros entornos.

- Poner los identificadores exactos de dos modelos/despliegues disponibles. Los
  placeholders permiten preparar un run, pero no realizar llamadas.
- `endpoint` es la URL completa de la operación. Se admite Chat Completions
  compatible con OpenAI, Messages de Anthropic y `vertex_anthropic` (`rawPredict`).
- Elegir exactamente un mecanismo de autenticación: `key_env` (nombre de variable),
  `key_file` (archivo de credencial existente) o `auth: "gcloud"` (sesión existente).
  El ejecutor no carga `.env` automáticamente ni registra tokens ni headers.
- En Vertex, `billing_project` permite enviar la cabecera de proyecto de cuota.
  El endpoint y ese identificador se guardan solo en la configuración local privada.
- Para Claude con razonamiento adaptativo se configura `thinking: {"type":
  "adaptive"}` sin parámetros de temperatura. No se presupone equivalencia entre
  el razonamiento de familias diferentes; se conservan los parámetros efectivos.
- `max_tokens` limita salida en cada llamada; para OpenAI se envía como
  `max_completion_tokens`. Elegir margen para todas las predicciones del lote.
- `temperature` es opcional y se omite por defecto. Si un proveedor rechaza un
  parámetro se registra el error; no se cambia silenciosamente la configuración.
- `repetitions: 1` prepara el piloto de viabilidad. `selection_limit` puede ser
  de 1 a 10. Para una medición posterior hay que fijar repeticiones y precisión
  antes de crear otro run.

Los adaptadores siguen los contratos de [Chat Completions](https://developers.openai.com/api/reference/resources/chat)
y [Anthropic Messages](https://platform.claude.com/docs/en/api/messages); las rutas y
los modelos concretos deben verificarse en el entorno donde se vaya a lanzar.
Se han comprobado ambas rutas de la campaña actual con inferencia mínima real.

### Rutas utilizadas en esta campaña

Se reutilizan las del experimento `llm-wrong-paste`: GPT-5.6 Sol por el gateway
existente, con credencial local, y Claude Opus 5 por Vertex con `gcloud`. No hacen
falta claves directas de OpenAI o Anthropic. Se fijan 8.192 tokens de salida por
llamada en ambos; GPT usa temperatura 1 y Claude razonamiento adaptativo sin
temperatura, como en el cliente precedente. Los nombres de despliegue, endpoints
privados e identificadores de proyecto permanecen en `runs/`, fuera de Git.

```bash
python3 run.py init --run runs/pilot-01 --config runs/pilot-config.json
python3 run.py generate --run runs/pilot-01
```

El segundo comando solo muestra el plan: 40 llamadas pendientes. **Ninguna fase
llama a la red sin `--live` y un `--max-calls` positivo.** El tope se aplica a esa
invocación, no al total de toda la corrida. No constituye un presupuesto monetario.

Cada run fija código, banco y configuración con hashes. Si cambia el instrumento,
crear otro run. Los snapshots son controles de integridad accidental y procedencia,
no una firma que impida manipular archivos deliberadamente.

## Fases del piloto

### 1. Generar y revisar candidatos

Con la autenticación existente ya disponible:

```bash
python3 run.py generate --run runs/pilot-01 --live --max-calls 40
python3 run.py prepare-review --run runs/pilot-01
```

Editar `runs/pilot-01/review.json`. Anotar `reviewer` y, para **cada** candidato:

- `decision`: `eligible` o `excluded`, siempre con `reason`.
- Para un elegible: `term`, `clause` literal que lo contiene, `replacement` y
  `rule_ids` correspondientes al encargo original (por ejemplo `['r2']`, en JSON
  con comillas dobles).
- Si no existe un requisito correspondiente, dejar `rule_ids: []` y explicar
  por qué en `explicit_na_reason`. Ese caso tendrá tres variantes.
- `terminology_provenance` empieza en `unverified`. Estar ausente del encargo no
  prueba que una expresión sea nueva; investigar su procedencia antes de llamarla
  «inventada» en el artículo.

No editar `prompt_text`, orden, IDs o hashes. Los términos deben estar ausentes
del encargo y aparecer una sola vez en una cláusula única para permitir una edición
local inequívoca. Registrar los casos con múltiples apariciones como exclusiones
del piloto, sin ocultarlos del denominador.

```bash
python3 run.py freeze-selection --run runs/pilot-01
```

Selecciona los primeros elegibles del orden fijado, como máximo uno por encargo
y hasta el límite. El orden alterna qué escritor se considera primero en cada
encargo. No existe una fase de ejecución para escoger los términos que «funcionen».
Se añaden dos controles etiquetados aparte, incluso si no aparece ningún elegible.

### 2. Explicar y congelar predicciones

```bash
python3 run.py explain --run runs/pilot-01
python3 run.py explain --run runs/pilot-01 --live --max-calls 24
python3 run.py freeze-predictions --run runs/pilot-01
python3 run.py prepare-probes --run runs/pilot-01
```

Hasta 24 llamadas: diez casos más dos controles, por dos explicadores. Los
explicadores ven el encargo, las variantes bajo letras contrabalanceadas y las
entradas, sin salidas de ejecución ni etiquetas de referencia. Pueden predecir
igualdad y abstenerse con `undetermined`.

Las explicaciones inválidas, vacías o truncadas quedan registradas como tales.
No se reintentan hasta obtener una historia convincente. El informe conserva su
denominador y no las convierte en predicciones válidas.

Editar `probe-review.json`: `reviewer` y `accept`/`reject` con motivo para cada
sonda propuesta. Las sondas ya deben cumplir el esquema; la revisión juzga que
el caso tenga sentido para el dominio. No modificar sus entradas o predicciones.
Si no se propuso ninguna, registrar igualmente quién revisó ese estado.

```bash
python3 run.py freeze-execution --run runs/pilot-01
```

Las variantes y predicciones están ahora fijadas. Sondas repetidas reutilizan el
mismo input; conservan separadas las predicciones de sus autores. Los ejecutores
reciben una sola variante y los registros, sin encargo original, explicaciones,
acciones esperadas ni identidad del escritor. Las sondas aceptadas se añaden al
lote de ese caso; el orden es el mismo entre variantes de una repetición. Compartir
lote puede producir efectos entre entradas: no tratar sus decisiones como sesiones
independientes.

### 3. Ejecutar y analizar

```bash
python3 run.py execute --run runs/pilot-01
python3 run.py execute --run runs/pilot-01 --live --max-calls 88
python3 analyze.py --run runs/pilot-01
```

Con diez elegibles, cuatro variantes, dos modelos y una repetición: hasta **88
llamadas** (80 naturales más 8 de controles). Las sondas van dentro de los mismos
lotes, aumentando tokens pero no llamadas. El plan real puede ser menor por
selección o variantes no aplicables. Generación + explicación + ejecución suman
hasta **152 llamadas**, sin reintentos de transporte.

`report.md` es legible y `report.json` conserva los desgloses completos. Revisar:

1. Estado de llamadas y fallos de formato; nunca son decisiones válidas.
2. Controles y sensibilidad antes de interpretar el corpus natural.
3. Acierto contra las reglas originales separado de diferencias entre variantes.
4. Coincidencia de **ambas acciones** previstas frente a observadas.
5. Predicciones de cambio comparadas con la referencia trivial de «nada cambia».
6. Resultados por encargo y familia; los controles y las sondas van separados.

Una repetición solo comprueba viabilidad. No permite distinguir con fiabilidad
variación aleatoria de un efecto, ni demostrar equivalencia entre condiciones.
El texto explicativo no se puntúa automáticamente por elocuencia. Atribución de
autoridad por humanos requeriría otro estudio.

## Reanudar y diagnosticar

Repetir una fase reutiliza todos los resultados ya guardados. No se reejecutan
salidas vacías, inválidas o truncadas. Para errores de transporte o una llamada
interrumpida, usar deliberadamente:

```bash
python3 run.py generate --run runs/pilot-01 --live --max-calls 2 --retry-errors
python3 run.py status --run runs/pilot-01
```

Cada intento queda en el historial; un timeout puede haber sido cobrado por el
proveedor aunque no haya respuesta. La fase de generación no se puede repetir
después de congelar la selección, ni la explicación tras congelar predicciones.
Una ejecución interrumpida deja una marca explícita. `.lock` impide dos escritores:
si el proceso muere, comprobar que terminó antes de retirar ese archivo.

Un HTTP 401 o 403 detiene la fase inmediatamente. Si caduca la sesión de `gcloud`,
se recupera la autenticación existente antes de reanudar: no se agota el banco de
casos contra una credencial que ha dejado de funcionar.

`runs/` está excluido de Git para evitar añadir accidentalmente salidas o
configuraciones locales. Los datos reales que se decida publicar necesitarán una
exportación revisada, conservando los denominadores, las exclusiones y los errores.

```bash
python3 export.py --run runs/pilot-01 --out results/pilot-01
```

La exportación elimina endpoints, proyectos, rutas de credenciales y los envelopes
privados del proveedor. Conserva prompts, respuestas textuales exactas, uso de
tokens, decisiones de selección, predicciones e informe. Sus hashes de procedencia
identifican los originales privados, no la representación redactada. Revisar esa
exportación antes de subirla a un repositorio público.
