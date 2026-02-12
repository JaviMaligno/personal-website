---
title: "Más allá de RAG: Construyendo un Recursive Language Model para procesar 1M de tokens"
description: "Cómo construí un prototipo RLM que procesa 71 papers de arXiv (~1M tokens) sin inyectarlos en el prompt, usando análisis de documentos out-of-core con Azure OpenAI tool calling."
pubDate: 2026-02-11
tags: ["IA", "LLM", "Azure OpenAI", "Tool Calling", "Python"]
lang: es
translationKey: recursive-language-models-prototype
heroImage: "/blog/rlm-prototype-hero.png"
---

Tienes un millón de tokens de texto. La ventana de contexto de tu modelo es de 128K. ¿Qué haces?

Las respuestas habituales son **RAG** (trocear, generar embeddings, recuperar los fragmentos relevantes) o **modelos de contexto largo** (esperar que la ventana sea suficiente). Pero ambos tienen trade-offs fundamentales: RAG pierde contexto global porque solo recupera fragmentos, y los modelos de contexto largo degradan su calidad a medida que crece la entrada -- el famoso problema "lost in the middle".

Un [paper reciente de arXiv](https://arxiv.org/abs/2512.24601) propone un tercer enfoque: **Recursive Language Models (RLM)**. La idea es engañosamente simple -- dejar que el LLM *programe su propio acceso* al documento.

Construí un prototipo funcional. Así es como lo hice.

<!-- IMAGE: Captura de terminal mostrando la tabla "Document Loaded" con 71 archivos, 4,044,992 chars, ~1,011,248 tokens -->

## ¿Qué es un Recursive Language Model?

El [paper RLM](https://arxiv.org/abs/2512.24601) introduce un paradigma de inferencia donde el modelo trata un documento largo como un **entorno externo** en lugar de como entrada. En vez de meter el texto en el prompt, el sistema:

1. **Carga el documento en memoria** (un entorno Python) donde el modelo no puede verlo directamente
2. **Le da herramientas al modelo** para examinar, hacer slicing y buscar en el documento mediante ejecución de código
3. **Permite sub-llamadas recursivas** -- el modelo puede invocarse *a sí mismo* sobre fragmentos para resumirlos o analizarlos

Esto es fundamentalmente diferente de RAG. En RAG, un sistema de recuperación decide qué es relevante *antes* de que el modelo vea nada. En RLM, el propio modelo decide qué leer, cuándo y con qué profundidad -- escribe código Python para navegar el texto.

La clave: **los LLMs son sorprendentemente buenos escribiendo código para explorar datos que no pueden ver.** Buscan patrones, hacen slicing alrededor de regiones interesantes, y usan sub-llamadas para resumir secciones -- todo de forma autónoma.

El paper muestra que los RLM procesan entradas **hasta dos órdenes de magnitud más allá de la ventana de contexto**, con mejoras de ~28% sobre los modelos base.

## Arquitectura del prototipo

El prototipo tiene tres componentes:

<!-- IMAGE: Diagrama de arquitectura mostrando: Pregunta del usuario → Orquestador → [Entorno Python (context, get_slice, search, llm_query)] ↔ [Azure OpenAI API (tool calling)] → Respuesta final -->

### 1. El Orquestador

Un bucle por turnos que gestiona la conversación entre el LLM y el entorno Python:

```python
for turn in range(1, max_turns + 1):
    response = client.chat(
        messages=messages,
        tools=[python_exec, final],
        tool_choice="auto",
    )
    # Procesar tool calls, recoger observaciones
    # Parar cuando el modelo llame a "final"
```

El LLM tiene acceso a dos herramientas:
- **`python_exec(code)`**: Ejecutar código Python en un entorno persistente
- **`final(answer)`**: Devolver la respuesta sintetizada

### 2. El Entorno Python Persistente

El documento completo se carga como un string en la variable `context` en un entorno Python que persiste entre turnos. Helpers integrados:

```python
context       # El texto completo del documento (~4M chars)
context_len   # Longitud
get_slice(start, end)  # Extraer un substring
search(pattern, max_results=5)  # Búsqueda regex con snippets de contexto
llm_query(prompt_text)  # Sub-llamada al LLM para análisis de fragmentos
```

El crítico es `llm_query()`. Cuando el modelo encuentra un fragmento relevante, puede invocar una *llamada separada al LLM* para resumir o analizar solo ese fragmento -- esta es la parte **recursiva**.

### 3. La API LLM

Azure OpenAI con GPT-5 vía tool calling. El system prompt le dice al modelo que es un RLM y que el documento NO está en su contexto:

```
Eres un RLM (Recursive Language Model). El documento completo NO está en tu contexto.
El texto está cargado en un entorno Python como variable `context`.
Usa python_exec para explorarlo con slicing y búsqueda.
Usa llm_query() para sub-consultas sobre fragmentos.
Llama a `final` con tu respuesta cuando estés listo.
```

## Construyendo la demo: Paso a paso

### 1. Setup

```bash
git clone https://github.com/YOUR_USER/rlm-prototipo
cd rlm-prototipo
uv venv && source .venv/bin/activate
uv pip install -e .
cp .env.example .env
# Rellena tus credenciales de Azure OpenAI
```

### 2. Recopilar datos (~1M tokens)

Escribí un script que descarga papers de arXiv y extrae texto limpio de las fuentes LaTeX:

```bash
python scripts/fetch_arxiv.py --target-chars 4000000 --output-dir data
```

Busca papers sobre agentes LLM, RAG e IA -- priorizando la extracción de fuentes LaTeX (texto más limpio), con fallback a PDF-a-texto, y usando abstracts como último recurso. Se detiene cuando alcanza el objetivo de caracteres.

En unos 2 minutos, descargó **71 papers** totalizando **4,033,636 caracteres (~1M tokens)**.

### 3. Ejecutar el RLM

```bash
rlm run \
  --input "data/*.txt" \
  --question "¿Cuál es la contribución principal de estos papers? \
              Resume las 5 temáticas más frecuentes."
# Defaults: --max-turns 15 --max-subcalls 90
```

<!-- VIDEO: Grabación de pantalla del RLM ejecutándose, mostrando turnos, paneles de código python_exec, subcalls llm_query, y la respuesta final -->

## Qué ocurre durante la ejecución

Observar el RLM trabajar es fascinante. Este es el comportamiento real sobre nuestro corpus de 71 papers:

**Turno 1**: El modelo comprueba el tamaño del documento, identifica la estructura, y muestrea fragmentos representativos:
```python
L = len(context)  # → 4,044,992
starts = [0, L//3, 2*L//3]  # Muestrear 3 posiciones
for st in starts:
    frag = context[st:st+6000]
    topics = llm_query(f"Extrae 4-6 temas clave:\n{frag}")
```

**Turno 2**: Con los temas iniciales recopilados, sintetiza la respuesta final:
```python
synth = llm_query(f"De estas listas parciales, identifica los 3 temas principales:\n{joined}")
```

Con un budget pequeño (15 subcalls), el modelo completa en **2 turnos, menos de 1 minuto** -- muestreando estratégicamente y produciendo una síntesis coherente sin ver nunca el millón completo de tokens.

Con budget completo (90 subcalls), el modelo analiza **los 71 papers individualmente** en ~23 minutos, produciendo una síntesis detallada que cita títulos específicos de papers, métodos y métricas. Usó 80 subcalls para análisis y el resto para síntesis -- todo con un 100% de tasa de éxito.

<!-- IMAGE: Terminal mostrando el panel Final Answer con las 3 temáticas identificadas -->

## Gestión de presupuesto: La decisión de diseño clave

El reto de ingeniería más interesante no fue la arquitectura -- fue la **gestión de recursos**. Cuando el modelo tiene subcalls limitadas repartidas entre múltiples turnos, ¿cómo debe distribuirlas?

### El problema

Con 71 papers pero solo 15 subcalls, el enfoque naíf falla:

```python
# MAL: El modelo intenta iterar sobre todo
for section in sections:  # 71 secciones
    llm_query(section[:8000])  # Quema todas las subcalls en el turno 1
# ¡No quedan subcalls para la síntesis!
```

### Visibilidad del budget: Enseñando al modelo a autoplanificarse

La solución fue inyectar la info de budget restante en cada resultado de herramienta:

```
[budget] subcalls restantes: 11/15 | turnos restantes: 4/5
```

Esta simple adición transforma el comportamiento del modelo. En lugar de iterar exhaustivamente, aprende a **muestrear** fragmentos representativos y reservar subcalls para la síntesis.

### Benchmark: Budget global vs Relleno por turno

Probé dos estrategias con parámetros idénticos (5 turnos, 15 subcalls):

| | Budget global + Info visible | Relleno por turno |
|---|---|---|
| **Tiempo** | 3:56 | 1:31 (sin respuesta) |
| **Subcalls usadas** | 9 | 2 |
| **Resultado** | 3 temas con explicaciones | "Max turns reached" |
| **Comportamiento** | Muestreó, hizo fallback a búsqueda por keywords cuando fallaron subcalls, sintetizó | Gastó 3 turnos explorando sin usar subcalls, luego falló |

**El budget global gana claramente.** El enfoque de relleno por turno elimina la urgencia -- el modelo "vagabundea" explorando sin comprometerse con subcalls. Con budget global y un contador de recursos restantes visible, el modelo planifica su estrategia alrededor de los recursos disponibles.

El modelo con budget global también mostró mejor adaptabilidad: cuando las llamadas a `llm_query()` devolvieron respuestas vacías (un problema de GPT-5), hizo fallback autónomo a conteo de keywords con `search()` -- sin necesidad de subcalls.

## Resultados y lecciones aprendidas

### Lo que funcionó

El RLM analizó exitosamente 71 papers e identificó temáticas coherentes en múltiples ejecuciones:
- **Seguridad, ética y robustez** -- alineamiento, mitigación de sesgos, resistencia adversarial
- **LLMs y NLP a escala** -- mejoras en Transformers, prompting, razonamiento de contexto largo
- **Aplicaciones transversales de IA** -- salud, robótica, generación de código, sistemas multimodales

### Problemas de compatibilidad con GPT-5

Construir contra GPT-5 requirió varios fixes:
- **`max_completion_tokens`** en vez de `max_tokens` (renombrado del parámetro de la API)
- **Sin `temperature` personalizada** -- GPT-5 solo soporta el valor por defecto (1)
- **Serialización de tool calls** -- los objetos del SDK necesitaban conversión explícita a dicts para el historial de mensajes
- **Rechazo de `tools=null`** -- GPT-5 devuelve contenido vacío cuando `tools` y `tool_choice` se establecen explícitamente a null; estos params deben omitirse

### La trampa de los reasoning tokens

Este fue el bug más difícil de diagnosticar. Las sub-llamadas devolvían `content: null` el 100% de las veces. La API no estaba caída -- respondía con `finish_reason: "length"` y consumía todos los tokens internamente.

GPT-5 es un modelo de razonamiento (como o1/o3). El parámetro `max_completion_tokens` incluye **tanto** los tokens de razonamiento interno como la respuesta visible. Con `max_completion_tokens=800`, el modelo gastaba los 800 tokens "pensando" y le quedaban cero para la respuesta real:

```
finish_reason: length
content: ""
reasoning_tokens: 800    ← todo el budget consumido aquí
completion_tokens: 800   ← nada para la respuesta visible
```

La solución fue subir `max_completion_tokens` de 800 a 8000 para las sub-llamadas. Esto da al modelo ~2000-3000 tokens para razonar y deja de sobra para la respuesta visible (~500-1000 chars).

El resultado fue drástico: la tasa de éxito de sub-llamadas pasó de **~6% a 100%** (80/80 en nuestro test). Lo que habíamos atribuido a "problemas intermitentes de la API" era en realidad un problema sistemático de starvation de recursos.

### Guardrails que importan

Tres guardrails previnieron los modos de fallo más comunes:

1. **Límite de longitud de código (50 líneas máx)**: Sin esto, el modelo escribe parsers regex enormes en vez de usar `llm_query()`. Al rechazar el código, hace fallback a código simple y correcto.

2. **Hints de error específicos**: En vez de un genérico "ocurrió un error", el sistema da guía concreta:
   - `SyntaxError` → "Simplifica tu código. Usa llm_query() en vez de parsing complejo."
   - `Max subcalls reached` → "Sintetiza con los datos que ya tienes y llama a final."

3. **Inyección de budget**: Las subcalls/turnos restantes mostrados tras cada resultado de `python_exec` cambiaron el comportamiento del modelo de "iterar todo" a "muestrear estratégicamente".

### Auto-corrección en acción

Uno de los comportamientos emergentes más interesantes: el modelo escribe código con bugs, recibe el error, y lo corrige autónomamente. Un ejemplo real:

```
# Turno 3: El modelo intenta hacer slicing sobre un dict como si fuera lista
KeyError: slice(None, 120, None)

# Turno 4: El modelo ve el traceback, se da cuenta de su error,
# y reescribe el código usando indexación de listas
```

El modelo también se auto-corrige a un nivel más alto. En una ejecución, encontró solo 5 separadores de archivo en vez de 71 porque buscó el patrón incorrecto. Al ver el conteo inesperado en el output, probó un enfoque diferente y encontró todos los archivos.

Esto no es un bug -- es el sistema funcionando como fue diseñado. El loop agentic devuelve cada error al modelo como una observación, y el modelo aprende de ello dentro de la misma ejecución. Los guardrails (límite de código, hints de error, visibilidad de budget) mantienen estos ciclos de auto-corrección cortos y productivos.

### Streaming de output en tiempo real

Un fix sutil pero crítico: el entorno Python usa `redirect_stdout` durante la ejecución de código, lo que captura todo el output -- incluyendo los logs de progreso de subcalls del orquestador. La solución fue anclar Rich Console al `sys.stdout` real en tiempo de construcción:

```python
# Console(file=sys.stdout) guarda una referencia directa al stdout real.
# Cuando redirect_stdout luego cambia sys.stdout a StringIO, la Console
# sigue escribiendo al terminal original.
self.console = Console(file=sys.stdout)
```

Sin esto, los usuarios observando el terminal durante bloques largos de `python_exec` no verían nada hasta que la ejecución completa termine -- mala UX para ejecuciones de 5+ minutos.

### Trade-offs

| Aspecto | RLM | RAG | Contexto largo |
|---------|-----|-----|---------------|
| **Complejidad de setup** | Baja (sin embeddings, sin vector DB) | Media-Alta | Baja |
| **Contexto global** | Alto (el modelo explora libremente) | Bajo (el retrieval decide) | Alto |
| **Coste** | Alto (múltiples llamadas API por consulta) | Bajo por consulta | Medio |
| **Latencia** | Alta (turnos secuenciales + subcalls) | Baja | Media |
| **Tamaño máx. documento** | Ilimitado (out-of-core) | Ilimitado | Limitado por ventana |

RLM brilla cuando necesitas **análisis profundo y exploratorio** de documentos masivos donde no sabes de antemano qué es relevante. RAG es mejor para recuperación de patrones conocidos a escala. El contexto largo funciona cuando el documento cabe.

## Cuándo usar RLM

Usa RLM cuando:
- Tu documento **excede la ventana de contexto** y necesitas comprensión global
- Necesitas que el modelo **decida qué leer** (preguntas exploratorias)
- Quieres **transparencia** -- puedes ver exactamente qué código escribe el modelo

No uses RLM cuando:
- Tienes un **patrón de recuperación simple** (usa RAG)
- La **latencia importa** más que la profundidad (RLM es secuencial)
- El documento **cabe en contexto** (usa contexto largo directamente)

## Próximos pasos

El prototipo es intencionalmente mínimo. Mejoras concretas que hemos identificado:
- **Helpers de estructura** (`list_files()`, `get_file(i)`) para eliminar los 2-3 turnos que el modelo gasta parseando separadores de documentos
- **Tabla de contenidos inyectada** en el system prompt para que el modelo sepa qué hay disponible sin explorar a ciegas
- **Sub-llamadas en paralelo** para reducir latencia (actualmente secuenciales a ~10s cada una; 71 papers × 10s = ~12 min que podrían ser ~2-3 min)
- **Caché de resultados** entre ejecuciones para consultas repetidas sobre el mismo corpus
- **Tracking de costes** por consulta para presupuestos de producción

El código fuente completo está disponible en el [repositorio de GitHub](https://github.com/YOUR_USER/rlm-prototipo).

---

*Basado en el paper ["Recursive Language Models"](https://arxiv.org/abs/2512.24601). Construido con Azure OpenAI GPT-5 y Python.*
