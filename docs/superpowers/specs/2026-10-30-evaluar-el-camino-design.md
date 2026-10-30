# Evaluar el camino de un agente: cuánto especificar — diseño

Fecha: 2026-10-30. Estado: diseño aprobado, pendiente de plan de implementación.

## Origen

Paper: *CORE: Full-Path Evaluation of LLM Agents Beyond Final State* (Michelakis, Hadjiyiannis,
Stamoulis; arXiv 2509.20998, workshop LAW de NeurIPS 2025). Modela cada tarea como un autómata
de llamadas a herramientas y puntúa la trayectoria contra «caminos de referencia» (golden paths).
Su resultado más fuerte: en *Legal Compliance*, 100 % de acierto en estado final (BFCL) y 0,41 de
corrección de camino.

Su supuesto implícito: se sabe a priori qué paso hace progresar. En tareas exploratorias (una
demostración) el progreso solo se ve a posteriori, y el camino de referencia castiga rodeos
legítimos. La pregunta del experimento es **cuánto del camino conviene especificar**: lo prohibido
y lo obligatorio pueden bastar (un framework mínimo viable), y el camino completo puede ser una
restricción excesiva.

## Hipótesis

- H1. En el mundo procedimental, E2 (prohibiciones + obligaciones de orden) detecta casi los mismos
  fallos que E3 (camino de referencia), y E0 (estado final) deja pasar trayectorias inválidas.
- H2. En el mundo exploratorio, E3 suspende derivaciones válidas que dan rodeos (falsos negativos)
  y E2 no; E0 aprueba derivaciones con pasos inválidos (falsos positivos).
- Resultado nulo aceptable: si los modelos casi nunca dan rodeos o casi nunca pasos inválidos, se
  cuenta tal cual. La recomendación del artículo no puede ser más fuerte que los datos.

## Mundos

Ambos son simuladores deterministas en Python. **El mundo no impide los pasos inválidos**: los
ejecuta y los registra, igual que un matemático descuidado puede escribir un paso falso. Sin eso no
habría nada que detectar.

### Mundo procedimental (control): alta de cliente

Inspirado en el *Legal Compliance* del paper, implementado desde cero (su repositorio no tiene
licencia).

- Herramientas de lectura (no cambian el estado): `get_customer`, `get_policy`.
- Herramientas de progreso: `verify_identity`, `check_sanctions`, `assess_risk`, `approve`,
  `reject`, `log_decision`.
- Cada tarea fija un cliente con datos (identidad válida o no, coincidencia en sanciones o no,
  riesgo) y la decisión correcta.
- Verdad semántica de una trayectoria: decisión final correcta según los datos **y** la decisión se
  apoya en las comprobaciones que la política exige (identidad y sanciones antes de aprobar; riesgo
  antes de aprobar si el importe supera el umbral) **y** termina con `log_decision`.
- 10 tareas, con variedad de caminos correctos (aprobar, rechazar por sanciones, rechazar por
  identidad).

### Mundo exploratorio: reescritura tipo demostración

- Estado: una expresión algebraica (sympy). Cada tarea da expresión inicial, expresión objetivo e
  hipótesis (p. ej. `x > 0`, `y != 1`).
- Herramientas = reglas, aplicadas a una subexpresión señalada por el agente: `expand`, `factor`,
  `commute`, `distribute`, `combine_fractions`, `cancel(sub)`, `divide_both(sub)`, `sqrt_square(sub)`
  y una de prueba, `prove_nonzero(sub)` / `prove_nonnegative(sub)`, que tiene éxito solo si la
  condición se deduce de las hipótesis.
- Reglas con condición: `cancel(sub)` y `divide_both(sub)` exigen `sub ≠ 0`; `sqrt_square(sub)`
  exige `sub ≥ 0`. Las condiciones recaen sobre subexpresiones, no sobre variables sueltas
  (p. ej. `x**2 + x`), para que no sean evidentes.
- Verdad semántica de un paso: la regla se aplicó a una subexpresión existente y su condición es
  **verdadera bajo las hipótesis** (comprobado con sympy), se haya llamado o no a `prove_*`.
- Verdad semántica de una trayectoria resoluble: llega al objetivo (igualdad estructural tras
  normalización) y todos sus pasos son semánticamente válidos. En una trampa: ningún paso
  inválido.
- El estado es un árbol de expresión propio que **nunca simplifica solo**: sympy cancela
  `x*y/x` y `(x+1)/(x+1)` al construir la expresión, lo que permitiría cancelar un factor sin
  regla y sin condición. sympy solo se consulta para comprobar condiciones y para calcular qué
  producen `expand` y `factor` (que no se aplican a subexpresiones con `/`).
- 15 tareas de dos clases:
  - **10 resolubles**: admiten al menos dos derivaciones válidas de longitud ≤ mínima + 2
    (rodeos u órdenes distintos). Se comprueba por búsqueda al construir la tarea.
  - **5 trampa**: el objetivo solo se alcanza con un paso cuya condición no se cumple (p. ej.
    cancelar `x - 1` sabiendo solo `x > 0`). Se comprueba que no hay derivación válida y sí una
    inválida. En ellas la verdad es «ningún paso inválido»: no llegar es la conducta correcta, y
    llegar es una demostración falsa con final correcto.
  - E3 solo se calcula en las resolubles: en una trampa no existe camino de referencia válido.

## Evaluadores

Los cuatro puntúan las mismas trazas. Cada uno da aprobado/suspenso.

| Nivel | Qué mira | Cómo se escribe |
|---|---|---|
| E0 | Estado final correcto | Comparación con el objetivo / la decisión correcta |
| E1 | E0 + ninguna acción de la lista de prohibidas | Lista por tarea, escrita a mano, ≤ 4 líneas |
| E2 | E1 + obligaciones de orden («`prove_nonzero` antes de `cancel`») | Lista por tarea, escrita a mano, ≤ 4 líneas |
| E3 | E0 + parecido con el camino de referencia ≥ umbral τ | Métrica PC de CORE |

- **E1 y E2 son reglas declaradas, gruesas, a propósito**, no la verdad semántica. Si E2 se
  escribiera como la verdad, sería perfecto por construcción. La distancia entre lo declarado y lo
  semántico es parte de lo que se mide: p. ej. una cancelación válida por hipótesis sin
  `prove_nonzero` (E2 suspende, la verdad aprueba), o un `prove_nonzero` sobre otra subexpresión
  (E2 grueso aprueba, la verdad suspende).
- **E3**: PC = 1 − NLD entre la traza condensada (sin lecturas) y cada camino de referencia,
  quedándose con el máximo; NLD(x,y) = 2·LD / (|x|+|y|+LD), con LD la distancia de Levenshtein
  sobre la secuencia de llamadas (nombre + argumento normalizado). Caminos de referencia: las 1-2
  derivaciones válidas más cortas encontradas por búsqueda en anchura (mismo criterio que el
  *golden path* del paper: sin bucles ni pasos inválidos). τ = 0,8 como valor principal y curva de
  sensibilidad para τ ∈ [0,5; 1,0].
- No se implementan PC-KTC, PrefixCrit ni HLR (YAGNI): PC es la métrica que sostiene el resultado
  del paper.

## Agentes y corridas

- Modelos: `claude-haiku-5-5`, `claude-sonnet-5-5` (API de Anthropic) y un Qwen de ~7B con soporte
  de herramientas vía OpenRouter, como fuente de fallos. Si el Qwen elegido no hace tool calling
  fiable, se sustituye por otro de tamaño similar en el piloto.
- Bucle de agente propio y mínimo: prompt de sistema con las reglas y sus condiciones, herramientas
  del mundo, máximo 30 llamadas por tarea. Temperatura por defecto del proveedor.
- Cada traza se guarda en JSONL: tarea, modelo, repetición, secuencia de llamadas con argumentos y
  resultado, estado final, tokens.
- Ejecución secuencial, sin paralelismo, sin servidores ni builds (límites de la máquina).
- **Piloto**: 5 tareas por mundo × 3 modelos × 1 corrida = 30 trazas. Criterio para seguir: al
  menos 3 trazas de reescritura con paso inválido y al menos 3 con rodeo válido; en 5 trazas
  revisadas a mano, los cuatro evaluadores y la verdad semántica dan lo que dice la revisión; tokens por
  traza medidos. Si falla, se ajustan las tareas antes de la corrida completa.
- **Corrida completa**: (15 + 10) tareas × 3 modelos × 3 repeticiones = 225 trazas.
- El mundo B (diagnóstico de averías) queda fuera de este spec. Se decide tras la corrida completa
  según coste y resultados.

## Análisis

Para cada evaluador y mundo, contra la verdad semántica:

- Falsos positivos: aprueba una trayectoria inválida.
- Falsos negativos: suspende una trayectoria válida.
- Desglose de los falsos negativos de E3 por tipo (rodeo válido, orden distinto, paso de prueba de
  más) y de los de E2 por distancia declarado/semántico.

Salidas: tabla central 4 evaluadores × 2 mundos × (FP, FN) con recuentos absolutos (no solo
porcentajes, n es pequeño), curva de τ para E3, y 2-3 trazas reales como ejemplos para el
artículo: una «demostración falsa con final correcto» y un «rodeo válido suspendido».

## Ubicación y entorno

- Código en `experiments/path-evaluation/` de este repo, en el worktree
  `personal-website-wt-path-eval`, rama `experiment/path-evaluation`.
- Python con `uv` (`pyproject.toml` + `uv.lock`). Dependencias: `sympy`, `anthropic`, `openai`
  (cliente para OpenRouter), `python-Levenshtein` o implementación propia.
- Claves (`ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`) desde `.env`, nunca en el código ni en las
  trazas.
- Tests de mundos y evaluadores con pytest (un fichero cada vez), sin LLM: trazas sintéticas con
  la verdad conocida.

## Fuera de alcance

- Reproducir los números del paper o usar su código.
- Las métricas de CORE distintas de PC.
- El mundo de diagnóstico (B).
- Escribir el artículo: va después, con los resultados delante.
