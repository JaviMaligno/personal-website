---
title: "Ya tienes una ontología"
description: "Circula un diagrama de taxonomías, ontologías y knowledge graphs para agentes de IA. Se lee como una arquitectura que adoptar. Es más útil como diagnóstico: audité un proyecto mío y encontré cuatro definiciones incompatibles de su entidad central."
pubDate: 2026-09-07
tags: ["IA", "Agentes", "Knowledge Graphs", "Arquitectura", "RAG"]
lang: es
translationKey: you-already-have-an-ontology
heroImage: "/blog/you-already-have-an-ontology.png"
linkedinImage: /blog/you-already-have-an-ontology-diagram.png
---

Circula un diagrama titulado "Technical Semantic Architecture for AI Agents". Aquí está, redibujado:

<style>
.ont-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.ont-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.ont-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
</style>

<figure class="ont-fig">
<svg viewBox="0 0 600 250" role="img" aria-label="Taxonomy y Semantic Layer alimentan una Ontology (capa de esquema) y un Knowledge Graph (capa de instancias), que juntos derivan un Context Graph para el razonamiento del agente">
  <defs>
    <marker id="ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="#5b7c99"/>
    </marker>
  </defs>
  <g fill="none" stroke="#5b7c99" stroke-width="2.5" marker-end="url(#ar)">
    <path d="M150,52 H205"/>
    <path d="M150,66 C180,66 180,120 205,120"/>
    <path d="M150,186 C180,186 180,132 205,132"/>
    <path d="M150,200 H205"/>
    <path d="M392,126 H432"/>
  </g>
  <g>
    <rect x="8" y="30" width="142" height="52" rx="6" fill="#f1f3f5"/>
    <rect x="8" y="170" width="142" height="52" rx="6" fill="#f1f3f5"/>
    <rect x="212" y="14" width="180" height="222" rx="8" fill="none" stroke="#3f5f7a" stroke-width="3"/>
    <rect x="224" y="26" width="156" height="94" rx="6" fill="#f1f3f5"/>
    <rect x="224" y="130" width="156" height="94" rx="6" fill="#f1f3f5"/>
    <rect x="436" y="82" width="156" height="86" rx="6" fill="#f1f3f5"/>
  </g>
  <g text-anchor="middle" fill="#1a1a24">
    <text x="79" y="52" font-size="15" font-weight="700">Taxonomy</text>
    <text x="79" y="69" font-size="10.5" fill="#5b6b7c">(is-a hierarchy)</text>
    <text x="79" y="192" font-size="15" font-weight="700">Semantic Layer</text>
    <text x="79" y="209" font-size="10.5" fill="#5b6b7c">(analytical definitions)</text>
    <text x="302" y="66" font-size="19" font-weight="700">Ontology</text>
    <text x="302" y="88" font-size="10.5" font-weight="700" letter-spacing="1" fill="#5b6b7c">SCHEMA LAYER</text>
    <text x="302" y="166" font-size="19" font-weight="700">Knowledge</text>
    <text x="302" y="186" font-size="19" font-weight="700">Graph</text>
    <text x="302" y="206" font-size="10.5" font-weight="700" letter-spacing="1" fill="#5b6b7c">INSTANCE LAYER</text>
    <text x="514" y="112" font-size="15" font-weight="700">Context Graph</text>
    <text x="514" y="130" font-size="10.5" fill="#5b6b7c">(decision-specific</text>
    <text x="514" y="144" font-size="10.5" fill="#5b6b7c">information slice)</text>
    <text x="514" y="188" font-size="9.5" font-weight="700" letter-spacing=".8" fill="#94a3b8">DERIVED FOR</text>
    <text x="514" y="201" font-size="9.5" font-weight="700" letter-spacing=".8" fill="#94a3b8">AGENT REASONING</text>
  </g>
  <rect x="146" y="112" width="68" height="30" fill="#1a1a24"/>
  <text x="180" y="126" font-size="8.5" font-weight="700" text-anchor="middle" fill="#94a3b8">INFORMS</text>
  <text x="180" y="137" font-size="8.5" font-weight="700" text-anchor="middle" fill="#94a3b8">STRUCTURE</text>
</svg>
<figcaption>El diagrama que circula, redibujado. La taxonomía y la semantic layer informan la ontología; la ontología y el knowledge graph derivan juntos un context graph, que es sobre lo que el agente razona de verdad.</figcaption>
</figure>

Mi primera reacción fue la que sospecho que tiene casi todo el que construye agentes. He montado agentes que investigan, que rellenan formularios en navegadores reales, que revisan código, que clasifican riesgo de cumplimiento — y ninguno necesitó un knowledge graph. Un agente de código es un modelo más un sistema de ficheros, grep, una terminal y git. Un agente de soporte es un modelo más un almacén vectorial y dos APIs. El diagrama parecía sofisticación buscando un problema.

Lo sigo pensando en buena medida, pero lo estaba leyendo mal. El diagrama se presenta como una arquitectura que adoptas. Es mucho más útil como **diagnóstico de algo que ya tienes** — y para comprobarlo, hice la auditoría sobre mi propio código. El resultado fue peor de lo que esperaba, que es justo lo que lo hace digno de un artículo.

## Las cuatro cajas, rápido

La distinción que sostiene todo el diagrama es **ontología frente a knowledge graph**: qué tipos de cosas pueden existir, frente a qué existe ahora mismo.

<figure class="ont-fig">
<svg viewBox="0 0 600 250" role="img" aria-label="Izquierda: la ontología define que una Persona puede trabajar en un Proyecto, que contiene Tareas que dependen de otras Tareas. Derecha: el knowledge graph contiene las instancias concretas Javier, Falcon, Task 381 y Task 204.">
  <defs>
    <marker id="ar2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="#64748b"/>
    </marker>
  </defs>
  <text x="20" y="20" font-size="11" font-weight="700" letter-spacing="1" fill="#2dd4bf">ONTOLOGÍA</text>
  <text x="132" y="20" font-size="11" fill="#64748b">lo que PUEDE existir</text>
  <text x="330" y="20" font-size="11" font-weight="700" letter-spacing="1" fill="#f59e0b">KNOWLEDGE GRAPH</text>
  <text x="472" y="20" font-size="11" fill="#64748b">lo que existe</text>
  <line x1="300" y1="8" x2="300" y2="240" stroke="rgba(255,255,255,0.12)" stroke-dasharray="4 5"/>
  <g font-family="ui-monospace,'JetBrains Mono',monospace" font-size="12.5">
    <g>
      <rect x="20" y="36" width="120" height="30" rx="5" fill="none" stroke="#2dd4bf" stroke-width="1.5" stroke-dasharray="5 4"/>
      <text x="80" y="56" text-anchor="middle" fill="#5eead4">Person</text>
      <rect x="20" y="100" width="120" height="30" rx="5" fill="none" stroke="#2dd4bf" stroke-width="1.5" stroke-dasharray="5 4"/>
      <text x="80" y="120" text-anchor="middle" fill="#5eead4">Project</text>
      <rect x="20" y="164" width="120" height="30" rx="5" fill="none" stroke="#2dd4bf" stroke-width="1.5" stroke-dasharray="5 4"/>
      <text x="80" y="184" text-anchor="middle" fill="#5eead4">Task</text>
    </g>
    <g>
      <rect x="330" y="36" width="120" height="30" rx="5" fill="rgba(245,158,11,0.14)" stroke="#f59e0b" stroke-width="1.5"/>
      <text x="390" y="56" text-anchor="middle" fill="#fbbf24">Javier</text>
      <rect x="330" y="100" width="120" height="30" rx="5" fill="rgba(245,158,11,0.14)" stroke="#f59e0b" stroke-width="1.5"/>
      <text x="390" y="120" text-anchor="middle" fill="#fbbf24">Falcon</text>
      <rect x="330" y="164" width="120" height="30" rx="5" fill="rgba(245,158,11,0.14)" stroke="#f59e0b" stroke-width="1.5"/>
      <text x="390" y="184" text-anchor="middle" fill="#fbbf24">Task 381</text>
    </g>
  </g>
  <g fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#ar2)">
    <path d="M80,66 V96"/><path d="M80,130 V160"/><path d="M140,179 C186,179 186,205 140,205 C110,205 92,196 82,196"/>
    <path d="M390,66 V96"/><path d="M390,130 V160"/><path d="M450,179 H486"/>
  </g>
  <rect x="492" y="164" width="100" height="30" rx="5" fill="rgba(245,158,11,0.14)" stroke="#f59e0b" stroke-width="1.5"/>
  <text x="542" y="184" text-anchor="middle" fill="#fbbf24" font-family="ui-monospace,'JetBrains Mono',monospace" font-size="12.5">Task 204</text>
  <g font-size="10.5" fill="#94a3b8" font-family="ui-monospace,'JetBrains Mono',monospace">
    <text x="88" y="86">works_on</text>
    <text x="88" y="150">contains</text>
    <text x="150" y="228">depends_on</text>
    <text x="398" y="86">works_on</text>
    <text x="398" y="150">contains</text>
    <text x="469" y="212" text-anchor="middle">depends_on</text>
  </g>
</svg>
<figcaption>La misma forma en dos niveles. Izquierda: tipos y relaciones permitidas — un esquema. Derecha: las filas. Los bordes discontinuos son lo que <em>puede</em> existir; los sólidos, lo que existe.</figcaption>
</figure>

Si vienes de bases de datos, la correspondencia es casi exacta: la ontología es el esquema, los tipos de entidad son tablas, las propiedades son columnas, las relaciones son claves foráneas y el knowledge graph son las filas. En filosofía, la ontología pregunta qué categorías de cosas hay y cómo pueden relacionarse — la versión de software es la misma pregunta con las ambiciones rebajadas de *la realidad* a *nuestro sistema*.

Las dos cajas laterales son entradas. Una **taxonomía** no es más que una jerarquía is-a: `BackendEngineer` es un `Engineer` es un `Employee`. Clasificación, nada más. Una **semantic layer** es la idea que viene de analytics: la definición canónica y única de ARR, churn o cliente activo, para que el agente no se invente su propia aritmética.

**Context graph** es la caja que más me gusta, y la de pedigrí más débil — no es terminología estándar y no la vas a encontrar en un manual. Sigue siendo el nombre correcto para algo que todos hacemos sin nombrarlo. Tu knowledge graph puede tener diez millones de entidades; tu ventana de contexto tiene unos cientos de miles de tokens. Así que para cada decisión ensamblas una rebanada pequeña y específica de esa decisión — este cliente, su proyecto bloqueado, la revisión que lo frena, quién es dueño de esa revisión, el hecho de que está de vacaciones hasta el día 7. Ese subgrafo es lo que el modelo ve de verdad. Ponerle nombre lo convierte en algo que diseñas deliberadamente en lugar de en lo que salga de lo que tu recuperador haya devuelto esta vez.

Un dato de contexto que el diagrama no da: esta forma tiene procedencia. Es el discurso de ontología de Palantir cruzado con la semantic layer de analytics (dbt, Cube, AtScale). No es una crítica — es una pista sobre el cliente al que va dirigido. Esta es una arquitectura para organizaciones con muchos sistemas, muchos equipos y definiciones genuinamente en disputa. Leerla como "la arquitectura para agentes de IA" es un error de categoría que el título fomenta activamente.

## La ontología que ya escribiste

Esta es la afirmación que quiero poner a prueba: **no puedes decidir si tienes una ontología. Solo puedes decidir si vive en un sitio.** En la mayoría de los sistemas ya está ahí, embadurnada por el esquema de la base de datos, los tipos de la API, los enums, los modelos del ORM, la documentación y los prompts. La propuesta real del diagrama no es "añade una capa". Es "ya tienes una; consolídala".

Para ver si eso aguanta fuera de una diapositiva, audité un proyecto mío: una herramienta de automatización de candidaturas, API en Python más un dashboard en Next.js. Es un proyecto personal, de un solo autor, sin comités y sin sistemas heredados — lo cual lo convierte en el *caso más débil posible* para el argumento, y por eso mismo es interesante.

Su entidad central es el **blocker**: aquello que impide que una candidatura se envíe automáticamente. Un CAPTCHA, un muro de login, un formulario de varios pasos. El producto entero existe para detectar blockers y pasárselos a un humano. Si algo está bien definido en ese código, debería ser esto.

Está definido en tres sitios — un enum de SQLAlchemy en el backend, un enum de TypeScript en el frontend y un `Record` de etiquetas dentro de un componente de React — y no coinciden:

<figure class="ont-fig">
<svg viewBox="0 0 600 350" role="img" aria-label="Matriz de once valores de blocker frente a tres capas. Solo captcha y login_required están presentes en las tres; los otros nueve aparecen en una o dos capas.">
  <g font-size="10.5" font-weight="700" letter-spacing=".5" fill="#94a3b8" text-anchor="middle">
    <text x="392" y="20">backend</text>
    <text x="462" y="20">frontend</text>
    <text x="536" y="20">componente</text>
  </g>
  <line x1="16" y1="30" x2="584" y2="30" stroke="rgba(255,255,255,0.14)"/>
  <g font-family="ui-monospace,'JetBrains Mono',monospace" font-size="12.5" fill="#e2e8f0">
    <text x="16" y="52">captcha</text>
    <text x="16" y="80">login_required</text>
    <text x="16" y="108">file_upload</text>
    <text x="16" y="136">multi_step_form</text>
    <text x="16" y="164">location_mismatch</text>
    <text x="16" y="192">none</text>
    <text x="16" y="220">form_too_complex</text>
    <text x="16" y="248">unsupported_ats</text>
    <text x="16" y="276">other</text>
    <text x="16" y="304">custom_question</text>
    <text x="16" y="332">review_before_submit</text>
  </g>
  <g>
    <rect x="330" y="34" width="254" height="26" rx="4" fill="rgba(45,212,191,0.12)"/>
    <rect x="330" y="62" width="254" height="26" rx="4" fill="rgba(45,212,191,0.12)"/>
  </g>
  <g fill="#2dd4bf">
    <circle cx="392" cy="47" r="6"/><circle cx="462" cy="47" r="6"/><circle cx="536" cy="47" r="6"/>
    <circle cx="392" cy="75" r="6"/><circle cx="462" cy="75" r="6"/><circle cx="536" cy="75" r="6"/>
  </g>
  <g fill="#f59e0b">
    <circle cx="392" cy="103" r="6"/><circle cx="536" cy="103" r="6"/>
    <circle cx="392" cy="131" r="6"/><circle cx="536" cy="131" r="6"/>
    <circle cx="392" cy="159" r="6"/>
    <circle cx="392" cy="187" r="6"/>
    <circle cx="462" cy="215" r="6"/>
    <circle cx="462" cy="243" r="6"/>
    <circle cx="462" cy="271" r="6"/>
    <circle cx="536" cy="299" r="6"/>
    <circle cx="536" cy="327" r="6"/>
  </g>
  <g fill="none" stroke="rgba(255,255,255,0.13)" stroke-width="1" stroke-dasharray="2 4">
    <circle cx="462" cy="103" r="6"/><circle cx="462" cy="131" r="6"/>
    <circle cx="462" cy="159" r="6"/><circle cx="536" cy="159" r="6"/>
    <circle cx="462" cy="187" r="6"/><circle cx="536" cy="187" r="6"/>
    <circle cx="392" cy="215" r="6"/><circle cx="536" cy="215" r="6"/>
    <circle cx="392" cy="243" r="6"/><circle cx="536" cy="243" r="6"/>
    <circle cx="392" cy="271" r="6"/><circle cx="536" cy="271" r="6"/>
    <circle cx="392" cy="299" r="6"/><circle cx="462" cy="299" r="6"/>
    <circle cx="392" cy="327" r="6"/><circle cx="462" cy="327" r="6"/>
  </g>
</svg>
<figcaption>Once valores en circulación entre tres capas de un mismo producto. Las tres definiciones coinciden en dos filas.</figcaption>
</figure>

El frontend cree en `form_too_complex` y `unsupported_ats`, que el backend no puede producir. El componente pinta `custom_question` y `review_before_submit`, que no existen en ningún enum de ninguna capa. Y `file_upload` sigue en el modelo de datos, debidamente migrado, mientras el detector que debería emitirlo no lo emite nunca.

Con el vocabulario de estados pasa lo mismo. `ApplicationStatus` tiene siete valores en Python y cinco en TypeScript. Los dos que faltan son `cancelled` y — este es el que escuece — **`needs_intervention`**, el estado cuyo propósito entero es decir *aquí hace falta un humano*. El backend lo emite en tres sitios distintos. El dashboard lo maneja como una cadena suelta dentro de un `switch`, porque su propio enum no lo tiene.

Nadie decidió no modelar el dominio. Se modeló cuatro veces, en cuatro días distintos, y derivó. Ese es el punto. Si un único desarrollador trabajando solo sobre un código pequeño produce cuatro definiciones incompatibles del concepto que da nombre al producto, entonces la ontología repartida no es un problema de escala organizativa que evitas siendo pequeño y disciplinado. Es estructural.

## Por qué deriva, y por qué ningún compilador lo impide

El mecanismo es aburrido y conviene decirlo claro. Un concepto del dominio tiene que cruzar dos fronteras que ninguna herramienta vigila.

Cruza una **frontera de lenguaje**: Python a JSON a TypeScript. Los tipos se comprueban a cada lado de ese cable y en ningún punto a través de él. Un `blocker_type` con valor `"location_mismatch"` se deserializa en una variable tipada como `JobBlockerType` sin la menor queja, porque en tiempo de ejecución un enum de TypeScript no es más que una cadena. El valor es inválido; el sistema de tipos está mirando a otro lado.

Y cruza una **frontera temporal**. El enum del backend se amplió cuando el detector aprendió un modo de fallo nuevo. El enum del frontend se escribió antes y no tuvo motivo para cambiar — no se rompió nada. La deriva no se anuncia: la interfaz pinta calladamente una etiqueta gris de reserva y todo el mundo sigue con lo suyo.

Este es exactamente el problema que el mundo de analytics resolvió primero, y por eso la semantic layer llegó a ser una categoría de producto. El propio argumento de venta de dbt es que [cinco personas pueden lanzar lo que creen que es el mismo informe y obtener cinco números distintos](https://www.getdbt.com/blog/build-centralize-and-deliver-consistent-metrics-with-the-dbt-semantic-layer), porque cada equipo escribió un SQL diferente para "revenue". El mismo fallo, un nivel de abstracción más arriba. Mis once valores de blocker son ese problema en miniatura — y yo tenía la ventaja de ser la única persona en la sala.

## Con agentes, esto sube de precio

Aquí está el motivo por el que un problema viejo merece revisarse ahora.

Cuando una interfaz se encuentra un valor que no conoce, se degrada de forma visible. Una etiqueta gris, un icono que falta, una columna vacía. Un humano ve el hueco y da un rodeo.

Cuando un **agente** se encuentra un valor que no conoce, no se degrada: interpreta. Tiene que producir una decisión, así que echa mano del único modelo del mundo que tiene, la ontología implícita y probabilística que lleva en los pesos. Ha leído suficiente software como para tener opiniones sobre qué significa probablemente `location_mismatch` y cómo de grave es probablemente. Esas opiniones son plausibles, no quedan registradas, y no son las de tu empresa.

Ese es el argumento real para hacer explícita la ontología, y es más estrecho de lo que el diagrama sugiere. No es que un knowledge graph haga al modelo más listo. Es que **mueve conocimiento desde "estadísticamente probable" hacia "definido por este sistema"**, de modo que cuando el agente duda consulta algo con autoridad en vez de confabular algo razonable.

## Las cuatro cajas se separan

Antes de preguntarte si necesitas la arquitectura, conviene notar que casi nunca la necesitas entera. El diagrama dibuja cuatro cajas como una sola pila, pero se adoptan de forma independiente, y la mayoría de los sistemas necesitan exactamente una. Coge los agentes que he construido:

- **Un agente de código** que pregunta *¿dónde se define esta función y quién la llama?* Eso es un grafo — aristas de llamada, imports, definiciones. Pero `grep`, un servidor LSP y un runner de tests ya lo recorren, y el índice lo mantiene un tooling que nadie llama knowledge graph. Las relaciones son reales y la caja sobra, porque el recorrido ya viene con el lenguaje.
- **Un agente de soporte** que pregunta *¿cuál es la política de reembolso de este plan?* La similitud de texto es exactamente la primitiva de recuperación correcta. Aquí no encadena nada. Este es el caso del almacén vectorial, y añadir un grafo sería estrictamente peor.
- **Un clasificador de cumplimiento** que pregunta *¿en qué categoría de riesgo cae este sistema?* Aquí una caja sí se gana su sitio, y es la más pequeña: una **taxonomía**. El trabajo entero consiste en colocar una instancia dentro de una jerarquía de categorías con fronteras defendibles. No hace falta grafo de instancias — el valor está en que la clasificación sea explícita, versionada y la misma que lee el auditor.
- **Un agente de informes** que pregunta *¿cuánto ARR renovó este trimestre?* La caja que importa es la **semantic layer**, y solo esa. El modo de fallo no es una relación que falta, son cuatro equipos con cuatro definiciones de ARR.

Así que "¿necesito esta arquitectura?" es la pregunta equivocada. La buena es *cuál de estos cuatro modos de fallo tengo de verdad*: clasificación inestable, definiciones en disputa, relaciones ilimitadas, o una ventana de contexto que no puede sostener la respuesta. Tienen arreglos distintos y precios distintos.

## El criterio: la forma de la pregunta, no el tamaño de los datos

Para el knowledge graph en concreto, el test equivocado es el volumen. Hay muchos equipos con conjuntos de datos enormes que no necesitan más que Postgres y buenos tipos.

El test que yo usaría es la **forma de tus consultas**:

<figure class="ont-fig">
<svg viewBox="0 0 600 240" role="img" aria-label="Izquierda: una consulta acotada filtra una tabla con joins conocidos de antemano. Derecha: una consulta no acotada recorre cliente, proyecto, hito, tarea, equipo y proveedor hasta una profundidad desconocida.">
  <defs>
    <marker id="ar3" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" fill="#64748b"/>
    </marker>
  </defs>
  <text x="16" y="18" font-size="11" font-weight="700" letter-spacing=".8" fill="#2dd4bf">ACOTADA</text>
  <text x="100" y="18" font-size="11" fill="#64748b">búsqueda + filtro</text>
  <text x="250" y="18" font-size="11" font-weight="700" letter-spacing=".8" fill="#f59e0b">NO ACOTADA</text>
  <text x="356" y="18" font-size="11" fill="#64748b">recorrido de profundidad desconocida</text>
  <line x1="228" y1="6" x2="228" y2="232" stroke="rgba(255,255,255,0.12)" stroke-dasharray="4 5"/>
  <g font-family="ui-monospace,'JetBrains Mono',monospace" font-size="11.5">
    <rect x="16" y="40" width="180" height="34" rx="5" fill="rgba(45,212,191,0.10)" stroke="#2dd4bf" stroke-width="1.4"/>
    <text x="106" y="62" text-anchor="middle" fill="#5eead4">applications</text>
    <rect x="16" y="104" width="180" height="34" rx="5" fill="rgba(45,212,191,0.10)" stroke="#2dd4bf" stroke-width="1.4"/>
    <text x="106" y="126" text-anchor="middle" fill="#5eead4">status = failed</text>
    <rect x="16" y="168" width="180" height="34" rx="5" fill="rgba(45,212,191,0.10)" stroke="#2dd4bf" stroke-width="1.4"/>
    <text x="106" y="190" text-anchor="middle" fill="#5eead4">respuesta</text>
  </g>
  <g fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#ar3)">
    <path d="M106,74 V100"/><path d="M106,138 V164"/>
  </g>
  <text x="106" y="224" font-size="10.5" text-anchor="middle" fill="#94a3b8">joins conocidos de antemano</text>
  <g font-family="ui-monospace,'JetBrains Mono',monospace" font-size="11" fill="#fbbf24">
    <g fill="none" stroke="#f59e0b" stroke-width="1.4">
      <rect x="252" y="34" width="96" height="26" rx="5" fill="rgba(245,158,11,0.12)"/>
      <rect x="252" y="76" width="96" height="26" rx="5" fill="rgba(245,158,11,0.12)"/>
      <rect x="252" y="118" width="96" height="26" rx="5" fill="rgba(245,158,11,0.12)"/>
      <rect x="252" y="160" width="96" height="26" rx="5" fill="rgba(245,158,11,0.12)"/>
      <rect x="432" y="118" width="96" height="26" rx="5" fill="rgba(245,158,11,0.12)"/>
      <rect x="432" y="160" width="96" height="26" rx="5" fill="rgba(245,158,11,0.12)"/>
    </g>
    <text x="300" y="52" text-anchor="middle">Cliente</text>
    <text x="300" y="94" text-anchor="middle">Proyecto</text>
    <text x="300" y="136" text-anchor="middle">Hito</text>
    <text x="300" y="178" text-anchor="middle">Tarea</text>
    <text x="480" y="136" text-anchor="middle">Proveedor</text>
    <text x="480" y="178" text-anchor="middle">Equipo</text>
  </g>
  <g fill="none" stroke="#64748b" stroke-width="1.5" marker-end="url(#ar3)">
    <path d="M300,60 V72"/><path d="M300,102 V114"/><path d="M300,144 V156"/>
    <path d="M348,173 H428"/><path d="M480,160 V148"/>
  </g>
  <g font-size="9.5" fill="#94a3b8" font-family="ui-monospace,'JetBrains Mono',monospace">
    <text x="306" y="70">owns</text><text x="306" y="112">has</text><text x="306" y="154">blocked_by</text>
    <text x="352" y="166">owned_by</text><text x="486" y="156">waiting_for</text>
  </g>
  <text x="480" y="212" font-size="22" text-anchor="middle" fill="#f59e0b">⋯ ?</text>
  <text x="404" y="232" font-size="10.5" text-anchor="middle" fill="#94a3b8">profundidad desconocida al consultar</text>
</svg>
<figcaption>Dos formas de consulta. A la izquierda, cada join se conoce al escribir la consulta. A la derecha no puedes decir de antemano a cuántos saltos está la respuesta — ese es el caso para el que se construye un grafo.</figcaption>
</figure>

*¿Qué facturas vencen esta semana? ¿Cuántos tickets abrió este cliente el mes pasado? ¿Qué cuentas del plan Pro llevan treinta días sin entrar?* Cada una de esas es una tabla, un filtro y un par de joins que ya conoces cuando te sientas a escribir la consulta. Esa es la forma de la izquierda, y ahí una API tipada sobre una base de datos relacional gana en todos los ejes.

*¿Por qué está bloqueado este cliente? ¿Qué se rompe si retiramos este endpoint? ¿Quién aprobó la versión que está ahora mismo en producción?* Nadie puede decir de antemano cuántos saltos hacen falta: depende de la respuesta. Esa es la forma de la derecha: recorridos de profundidad desconocida sobre dependencias, propiedad, procedencia, causalidad o permisos. Es la única cosa que SQL hace genuinamente mal, porque cada join hay que escribirlo antes de saber cuántos vas a necesitar.

La señal práctica es justo esa: **si no puedes escribir la consulta sin saber ya la respuesta, tu pregunta tiene forma de grafo.** Cuenta cuántas de las preguntas que recibe tu agente de verdad fallan ese test. Si son un puñado entre cientos, tienes una herramienta de informes con un caso raro interesante, no un problema de grafos.

La evidencia respalda la lectura conservadora. [GraphRAG-Bench](https://arxiv.org/abs/2506.05690), un benchmark de ICLR 2026 construido para responder exactamente a esta pregunta, arranca señalando que "GraphRAG frecuentemente rinde peor que el RAG convencional en muchas tareas del mundo real", y se propone identificar las condiciones en las que el grafo gana de verdad — separando recuperación de hechos de razonamiento complejo y de resumen, porque se comportan distinto. El coste cuenta la misma historia: [LazyGraphRAG](https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/), de la propia Microsoft, existe porque la indexación inicial de GraphRAG completo resultaba prohibitiva, y su resultado de titular es igualar la calidad al 0,1% del coste de indexación. Cuando el producto siguiente del fabricante es sobre todo una forma de no pagar el anterior, conviene captar la indirecta.

Aquí hay una escalera, y el diagrama salta directamente al último peldaño:

1. **Una definición compartida del vocabulario de tu dominio**, generada desde una única fuente en lugar de copiada a mano por lenguaje. Barato. Arregla lo que encontró mi auditoría.
2. **Una API tipada sobre los datos relacionales**, expuesta al agente como herramientas en vez de como SQL en crudo. Aquí es donde deberían parar la mayoría de los agentes.
3. **Un grafo**, cuando los recorridos son genuinamente ilimitados.

Casi todo el valor de ese diagrama está disponible en el primer peldaño. Saber cuándo *no* seguir subiendo es parte de la disciplina, igual que lo es [saber cuándo no enrutar](/es/blog/routing-engineering).

## Lo que el diagrama esconde

Mira otra vez la primera figura: es todo cajas y flechas, y ninguna de esas flechas está etiquetada como *y quién mantiene esto verdadero*.

Modelar es la parte divertida. La parte que mata estos proyectos es **poblar y mantener fresco**: la ingesta, la resolución de entidades (¿es `Acme Corp` del CRM el mismo nodo que `ACME S.L.` del sistema de facturación?) y la pregunta de quién garantiza que `Task 381 blocked_by SecurityReview` siga siendo un hecho mañana. Un knowledge graph es una vista materializada y desnormalizada de media docena de sistemas, y las vistas materializadas se quedan rancias.

Rancio es peor que ausente, y peor de forma específica para los agentes. Cuando [medí cómo manejan los agentes lo que ya ha ocurrido](/es/blog/what-has-already-happened) — 572 respuestas, seis modelos — el hallazgo fue que planifican alrededor de eventos que nunca sucedieron e inventan dependencias entre cosas que no dependen entre sí, y que **darles la fecha no cambia nada**. Un calendario le dice al modelo dónde está el *ahora*; no le dice nada sobre cuáles de sus hechos ya están fijados y qué relaciones siguen valiendo. Un knowledge graph le entrega al agente exactamente ese tipo de información: relaciones afirmadas en plano, en presente, sin indicación de cuándo fue verdad cada una por última vez. Cada arista está bien formada, cada tipo cuadra, el esquema valida, y el contenido lleva tres semanas por detrás de la realidad — y, a diferencia de un documento en crudo, el grafo es la fuente autorizada, así que el agente no tiene motivo para matizar.

La única intervención que sí ayudó en aquel experimento fue hacer la procedencia inseparable del valor, de modo que un hecho no pueda viajar sin su salvedad. Traducido a un grafo, eso es un requisito de diseño que el diagrama no menciona nunca: la frescura y el origen pertenecen a la arista, no a los logs de un trabajo de sincronización.

## Por dónde empezaría de verdad

No por una base de datos de grafos. Por la auditoría.

Elige la entidad que da nombre a tu producto. Busca con grep todos los sitios donde se define su vocabulario: el enum, el tipo, el mapa de constantes, la cadena suelta dentro de un switch, la frase del prompt que le explica el dominio al modelo. Cuenta las definiciones. Cuenta los valores en los que coinciden.

Si sale una definición, tienes una ontología y está centralizada; el diagrama no tiene nada que venderte hasta que tus consultas adopten forma de grafo. Si salen cuatro, como me salieron a mí, entonces ya tienes una ontología — solo que repartida por el código en una forma que ninguna herramienta puede comprobar, y a punto de entregársela a algo que interpretará con total seguridad lo que no reconozca.

Esa es la lectura útil del diagrama. No una arquitectura que adoptar. Una pregunta que lanzar contra el código que ya tienes.

---

*Relacionados: [Lleva tu aplicación al agente](/es/blog/bring-your-app-to-the-agent), sobre exponer tu sistema a los agentes como herramientas, y [Tu agente no sabe qué ha pasado ya](/es/blog/what-has-already-happened), sobre por qué la fecha no arregla los hechos rancios.*
