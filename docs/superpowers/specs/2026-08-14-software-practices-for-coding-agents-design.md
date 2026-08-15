# Buenas prácticas de software para coding agents: ¿cómo está escrito, o dónde está?

**Fecha:** 2026-08-14
**Estado:** diseño aprobado, pendiente de pre-flight
**Artículo predecesor:** [Coding Agents and Teamwork: Social Skills, or Structure?](../../../src/content/blog/en/coding-agents-structure.md) (2026-07-12)
**Ejecución:** herramienta desarrollada en Windows (sin Docker), campaña en Mac (con Docker). Corridas secuenciales, copias de repo desechables, limpieza obligatoria (§2).
**Código:** https://github.com/JaviMaligno/agent-code-practices

---

## 1. Motivación y tesis

Las buenas prácticas de software se justificaron para lectores humanos: nombres que se
entienden, formato consistente, módulos con una responsabilidad, documentación que dice dónde
vive cada cosa. Hoy una fracción creciente de las lecturas de un repositorio las hace un agente.
Nadie ha medido cuáles de esas prácticas le sirven **a él**, y cuáles solo nos servían a nosotros.

La pregunta es cara de responder mal: si el formato no importa, hay equipos gastando presupuesto
de revisión en algo inerte; si la modularidad importa mucho más de lo que se cree, hay
codebases que no se pueden agentizar hasta que se reorganicen.

### 1.1 La hipótesis, formulada de forma falsable

La tesis del autor, antes de correr nada:

> Para un coding agent importa **más saber dónde mirar** — organización, distribución en
> ficheros, documentación — **que lo bien escrito que esté el fichero** una vez abierto.
> El tamaño de fichero es la excepción: por debajo de cierto umbral da igual, y por encima
> empieza a hacer daño.

Eso se convierte en un experimento partiendo las prácticas en dos familias y degradando cada una
por separado, con transformaciones **semánticamente equivalentes** — el programa hace exactamente
lo mismo antes y después. Cualquier diferencia en el resultado es atribuible a legibilidad o
navegabilidad, nunca a que la tarea se haya vuelto más difícil.

- **Familia A — cómo está escrito**: lo que cambia dentro de un fichero ya abierto.
- **Familia B — dónde mirar**: lo que cambia entre ficheros, antes de abrir ninguno.

### 1.2 Por qué el resultado no es obvio

Hay un argumento fuerte en cada dirección, y por eso merece medirse.

A favor de la tesis: un modelo grande reconstruye la intención de un fragmento aunque esté mal
escrito — es literalmente lo que hace con el código minificado o generado. Lo que no puede
reconstruir es un fichero que no ha abierto.

En contra: el agente no lee como nosotros. No hojea. Navega por búsquedas, y **las búsquedas son
búsquedas de nombres**. Si eso es así, los nombres — que en la partición de arriba son familia A —
harían el trabajo de la familia B, y la separación entre las dos se rompería justo por su punto
más interesante (§4.4).

### 1.3 Precedente en el blog

El artículo de julio sobre CooperBench estableció el listón metodológico que este hereda:
escalera de condiciones ordenada, dos tiers de capacidad, réplicas solo en las celdas de titular,
y los límites de cobertura declarados por delante en lugar de escondidos al final.

También dejó un resultado que hace de prior: allí la estructura del proceso recuperó rendimiento
que la capacidad conversacional no daba. Este experimento pregunta lo mismo un nivel más abajo —
no la estructura del equipo, sino la estructura del código.

---

## 2. Restricciones de ejecución

La máquina se satura con facilidad y ya se han perdido tandas de trabajo por ello. Reglas
vinculantes para este experimento:

- **Dos máquinas, y la campaña corre en la de contenedores.** El equipo Windows donde se
  desarrolla la herramienta no admite Docker —lo tumba—, así que allí el aislamiento es copia
  desechable del árbol más entorno virtual propio. La campaña se ejecuta en el Mac, con
  contenedores. El motivo del reparto no es solo Docker: el sustrato son repos Python de terceros
  y su hábitat natural es POSIX, así que en Windows varios candidatos caerían por compilación de
  wheels o dependencias del sistema — razones que no dicen nada sobre si el repo sirve. Un
  candidato descartado por no compilar en Windows se pierde por la razón equivocada.
- **Los dos ejecutores se conservan**, seleccionables. El de entorno virtual está verificado y
  sirve de alternativa si el contenedor falla; las decisiones que toma la capa de preparación
  —qué instalar, si la suite llegó a colectarse— son las mismas en los dos (§5.6).
- **Corridas secuenciales.** Como mucho dos condiciones en vuelo a la vez, nunca más.
- **Una copia de repo viva por condición en curso.** Cada condición trabaja sobre una copia
  desechable; al cerrar la condición se borra la copia. Nunca acumular árboles transformados.
- **Un entorno virtual por repo, no por condición.** Las transformaciones no tocan las
  dependencias declaradas, solo el código, así que el entorno se crea una vez por repositorio y
  se reutiliza entre condiciones. Lo que sí cambia por condición es cómo se pone el árbol
  transformado al alcance de pytest (§5.6).
- **Limpieza obligatoria al cerrar cada bloque**: copias de repos, clones de SWE-bench y
  entornos virtuales fuera. Comprobación de disco libre **antes** de arrancar cada bloque, y
  registro de lo que se borró.
- **Las suites de test del experimento no compiten con otras.** Nada de correr una suite del
  usuario mientras hay corridas en vuelo.
- **Los repos de cliente quedan excluidos por completo**, también como copias locales. El
  artículo publica métricas y fragmentos; no merece la pena la conversación.

---

## 3. Sustrato: repos y tareas

### 3.1 Por qué no SWE-bench como sustrato principal

La contaminación no sesga las dos familias por igual, que es justo la comparación que sostiene el
artículo. Con un repo memorizado:

- La familia B sale **subestimada**: el modelo sabe dónde vive cada cosa sin leer el README, así
  que borrarlo duele menos de lo que dolería en código nuevo.
- La familia A sale **sobreestimada**: renombrar un símbolo conocido rompe la recuperación desde
  memoria paramétrica de golpe.

Los dos sesgos empujan en contra de la tesis y en direcciones opuestas. Sobre ese sustrato el
resultado no es interpretable. SWE-bench entra solo como réplica de control (§3.4).

### 3.2 Selección de repos — fase 0, previa a todo lo demás

La selección de repos es una fase de trabajo con entregable propio, no un criterio que se aplica
de pasada durante el pre-flight. Va **antes** que la construcción del harness y antes de fijar
nada más, porque de ella depende qué se puede medir: un repo sin lógica de dominio propia no
admite el estrato de bugs específicos (§3.3), y un repo con módulos ya planos no deja sitio para
degradar la jerarquía. Incluso la decisión de lenguaje queda sujeta a revisión si el examen
revela que los candidatos buenos están en otro sitio.

**Entregable**: una ficha por candidato con las dimensiones de abajo medidas, no estimadas, y una
recomendación de tres finalistas con su razón. **Cerrada**: los resultados y los tres finalistas
—python-stdnum, sqlglot, holidays— están en
[`2026-08-14-fase-0-resultados.md`](2026-08-14-fase-0-resultados.md), incluido el coste declarado de
que los tres sean de jerarquía plana, que deja a B2 con poco recorrido.

**Dimensiones de examen**, más allá de los criterios de admisión:

- **Margen de degradación.** Cuánta estructura hay que destruir. Un repo con jerarquía profunda,
  módulos cohesionados y README útil da recorrido a la familia B; uno que ya es plano y sin
  documentar parte degradado y no puede caer más.
- **Densidad de lógica de dominio.** Si el repo es sobre todo pegamento y utilidades genéricas,
  no se pueden fabricar bugs que exijan entender el negocio. Se necesitan reglas propias —
  precedencias, invariantes, estados, unidades, políticas — que solo se conozcan leyendo.
- **Acoplamiento entre módulos.** Un repo donde cada fallo se arregla en un solo fichero mide
  poco de navegación. Interesan repos donde entender un fallo obligue a leer dos o tres sitios.
- **Coste de entorno.** Tiempo de instalación y de suite, medidos, porque se multiplican por 54.
- **Riesgo de contaminación.** Popularidad y antigüedad como proxy: entre dos candidatos
  equivalentes, gana el menos visto.

### 3.2.1 Criterios de admisión

Por orden de dureza:

1. **Suite verde, rápida y discriminante.** Requisito duro: sin tests que distingan arreglado de
   roto no hay medida. "Rápida" significa que la suite completa cabe en la ejecución de cada
   tarea sin dominar el tiempo de corrida.
2. **Tamaño mediano**, del orden de miles a decenas de miles de líneas. Por debajo, el agente lee
   el repo entero y todas las transformaciones de familia B dan cero por construcción. Por
   encima, el barrido no cabe en el presupuesto.
3. **Dependencias instalables sin pelea en el sustrato de ejecución**: una imagen Linux con
   Python y git (§5.6). El criterio se verifica ejecutando, no leyendo la documentación del repo.
   Con contenedores deja de ser un filtro por la plataforma de desarrollo: un candidato que no
   compilara en Windows se habría perdido por la razón equivocada, porque el hábitat natural de
   estos repos es POSIX.
   Un repo puede además exigir un **paso de preparación propio** —artefactos que genera su build y
   que su suite necesita: holidays compila traducciones, babel descarga el CLDR, dateutil genera su
   base de zonas—. No es una dependencia, así que no lo cubre ninguna estrategia de instalación, y
   sin él la suite se lee como rota cuando no lo está: holidays falla 515 tests. Se declara por
   repositorio, se ejecuta después de instalar lo declarado —el script de holidays importa `polib`,
   que viene en su grupo de tests—, queda registrado en la ficha y forma parte de la receta de cada
   corrida. Que un repo lo necesite no lo excluye; que ese paso sea caro, sí puede excluirlo.
4. **Sin tipado en runtime.** Repos que usan anotaciones para validar en ejecución (pydantic,
   dataclasses con conversión, `typing.get_type_hints`) quedan fuera: ahí A1 no es
   semánticamente equivalente.
5. **Sin código de cliente.**

Objetivo: **tres repos Python** de terceros, más la opción de uno propio si encaja. Los de
terceros evitan que el resultado se lea como dependiente del estilo del autor; uno propio aporta
un sustrato garantizado no visto. Los finalistas salen de la fase 0, no de este documento: los
criterios 1 y 3 solo se verifican ejecutando, y el margen de degradación solo se ve mirando el
árbol.

### 3.3 Las tareas se generan, no se buscan

Sobre un repo con suite verde, cada tarea se fabrica por **inyección de fallo**: se introduce un
bug de forma programática, se comprueba que hace fallar un conjunto concreto de tests y **no
otros**, y eso ya es una instancia con criterio objetivo de resolución. Es la técnica de
SWE-smith, y aporta dos cosas:

- Libera de depender de que exista un corpus de issues reales con parche de referencia.
- Produce tareas que **no existen en internet**, así que en el sustrato principal la
  contaminación desaparece del todo.

**Objetivo: 24 tareas** (8 por repo, tres repos). Cada tarea guarda su conjunto de tests
`fail_to_pass` y `pass_to_pass`, y el fichero o ficheros que toca el parche de referencia — esto
último es lo que permite medir localización (§7).

### 3.3.1 Dos estratos de fallo, y por qué no es un detalle

Un fallo genérico —condición invertida, off-by-one, comprobación de nulo que falta, argumento
cambiado de orden— **se reconoce por patrón sin entender el código**. El agente no necesita saber
qué hace el sistema: la forma del bug es la pista. Y esas formas están sobrerrepresentadas en todo
lo que el modelo ha visto, así que en la práctica también son las más memorizadas.

Un fallo de dominio solo es un fallo a la luz de la lógica del sistema. La propiedad que lo define
es que **nadie que lea la función aislada diría que está mal**: es sintácticamente impecable y
localmente coherente, y solo resulta incorrecto respecto a la intención.

Con una precisión que salió de inspeccionar los finalistas (fase 0, §6.1): no basta con que el fallo
exija **conocimiento del mundo**; tiene que exigir **leer varios sitios del repositorio**. Cambiar el
año en que Eslovenia dejó de celebrar el 2 de enero es indetectable sin saber historia eslovena, pero
se juzga en una sola línea: pasaría el filtro de aislamiento de §3.6.2b y aun así no sirve, porque
rompe el puente con la métrica de localización. Los fallos de dominio se inyectan donde la regla
correcta viva repartida —un verificador compartido, una jerarquía de dialectos, una regla de
observancia—, no en tablas de datos. Aplicar el descuento
antes del impuesto en vez de después. Invalidar la caché con la clave del padre en lugar de la del
hijo. Usar la zona horaria del servidor donde el dominio exige la del usuario. Redondear en el
paso intermedio en lugar de al final. Para saber que eso está mal hay que leer **más de un sitio**.

Por eso el estrato no es una variable de control sino un moderador de primer orden, y con toda
probabilidad un resultado por sí mismo:

- Los fallos genéricos deberían ser casi insensibles a la degradación, sobre todo a la de familia
  A: el patrón sobrevive a nombres opacos y a formato destruido.
- Los fallos de dominio deberían ser mucho más sensibles, y **especialmente a la familia B**,
  porque exigen leer varios sitios y por tanto encontrarlos.

Si eso se confirma, explica de paso por qué circula la idea de que a los agentes les da igual el
código feo: porque se mide con benchmarks poblados de fallos reconocibles por patrón.

**Estratificación: 12 tareas genéricas y 12 de dominio**, equilibradas dentro de cada repo. No
añade ni una corrida: el estrato es un corte del análisis dentro de cada ejecución del set. El
coste está en fabricar bien las de dominio, que es trabajo de diseño y no automatizable del todo.

Dentro de cada estrato, los fallos se reparten entre formas distintas para que el set no mida una
sola habilidad. Y cada tarea de dominio lleva anotado **cuántos ficheros hay que leer como mínimo
para poder juzgar que es un fallo** — que es la variable que hace de puente con la métrica de
localización (§7).

Con 12 tareas por estrato el poder es limitado en las celdas de una sola pasada; en las de titular
son 36 observaciones por estrato y tier. El artículo lo declara en lugar de disimularlo.

### 3.4 Réplica de control en SWE-bench Verified

Solo las cuatro condiciones de titular (§6.1), un tier, una pasada, sobre un subconjunto de
instancias. No sirve para el resultado principal: sirve para **cuantificar cuánto de la
tolerancia de los agentes al código feo es memorización y no comprensión**, comparando la caída
en el sustrato limpio con la caída en el contaminado. Es un dato secundario publicable por sí
solo.

### 3.5 Sonda TypeScript

En Python las anotaciones no las comprueba nadie en ejecución, así que A1 mide su valor **como
documentación**. En un lenguaje con comprobación estática, los tipos son además contrato y
herramienta: el agente puede apoyarse en el compilador para saber si su edición rompe algo.

La sonda replica solo el eje tipos sobre **un repo TypeScript con 6 tareas**: T0, A1 en
knock-out, T3 y A1 en add-back. Responde si el hallazgo sobre tipos es un artefacto de que en
Python son opcionales. No se generaliza más allá de eso.

### 3.6 Pre-flight — qué hay que cerrar antes de gastar cómputo

Bloqueante. Ninguna corrida arranca sin esto:

0. **Fase 0 cerrada** (§3.2): tres repos finalistas con su ficha de examen.
1. **Selección de repos verificada**: suite verde, tiempo de suite medido, ausencia de tipado en
   runtime comprobada.
2. **24 tareas generadas y validadas**: cada una falla los tests que debe y pasa los demás, en el
   repo original, con el reparto 12/12 entre estratos.
2b. **Estrato de dominio validado por aislamiento**: a cada tarea de dominio se le pasa al modelo
   **solo la función modificada, fuera de contexto**, preguntando si contiene un fallo. Si lo
   detecta, la tarea no es de dominio y se descarta o se reclasifica. Es el filtro que impide que
   el estrato se llene de bugs genéricos disfrazados, que es el modo de fallo más probable al
   fabricarlos.
3. **Equivalencia de cada transformación verificada por repo**: en el árbol transformado, la
   suite completa da **el mismo resultado** que en el original. Una transformación que rompe el
   repo se lee exactamente igual que un agente que falla, y es el error más caro de descubrir
   tarde.
4. **Reversibilidad comprobada**: aplicar y deshacer devuelve un árbol funcionalmente idéntico.
5. **Baseline discriminante**: el resolve rate en T0 no puede estar pegado al 0% ni al 100% en
   ninguno de los dos tiers. Si lo está, no hay margen para medir caídas y hay que retocar la
   dificultad de las tareas antes de seguir.
6. **Modelos disponibles confirmados** en el despliegue de Azure (§5.5).
7. **Oráculos de control en verde** (§5.4.6): no-op al 0% y oráculo al 100% en todas las
   condiciones.

---

## 4. Las transformaciones

### 4.1 Familia A — cómo está escrito

| ID | Transformación | Qué hace |
|---|---|---|
| A1 | Tipos | Elimina todas las anotaciones y type hints |
| A2 | Nombres | Renombra identificadores a opacos (`f7`, `v3`, `C2`), repo-wide |
| A3 | Formato | Líneas de hasta 400 caracteres, sin líneas en blanco, sin espaciado alrededor de operadores, expresiones colapsadas |
| A4 | Comentarios y docstrings | Elimina comentarios y docstrings de función |

En Python la sangría es sintaxis, así que A3 no puede destruirla; lo que sí puede es eliminar
todas las demás señales visuales. Es el equivalente operativo a un repo sin formateador.

### 4.2 Familia B — dónde mirar

| ID | Transformación | Qué hace |
|---|---|---|
| B1 | Cohesión | Reparte funciones y clases entre ficheros al azar, con imports corregidos. Mismo número de ficheros y mismo tamaño: solo se rompe la lógica de qué vive con qué |
| B2 | Jerarquía | Aplana todos los directorios y renombra los ficheros a `m1.py`, `m2.py`… |
| B3 | Documentación de repo | Borra README, `docs/`, docstrings de módulo |
| B4 | Tests visibles | Oculta al agente la suite existente del repo |
| B5 | Tamaño | Concatena módulos. Curva de dosis, no celda: original / ~500 / ~2.000 / ~10.000 líneas por fichero |

Tres decisiones de reparto, con su razón:

- **Las docstrings de función son A4; el README es B3.** Las dos son documentación, pero una se
  lee cuando ya has abierto el fichero correcto y la otra te dice cuál abrir. Si la tesis es
  cierta deben comportarse distinto, y ese contraste es de los resultados más limpios que puede
  dar el experimento.
- **Cohesión y tamaño se separan.** Meter todo en un fichero de 10.000 líneas cambia dos cosas a
  la vez. B1 rompe la organización sin tocar el tamaño; B5 varía el tamaño sin tocar nada más. Es
  la única forma de contestar la salvedad del umbral en vez de dejarla como intuición.
- **Los tests entran como B4.** No se mide si el agente escribe tests: se mide si le sirven de
  documentación ejecutable para entender cómo se usa una pieza. Los tests de validación se
  ejecutan fuera del alcance del agente y no se tocan nunca.

### 4.3 Reglas de equivalencia

Vinculantes para toda transformación:

1. **Alcance repo-wide, tests del repo incluidos.** Renombrar solo el código fuente deja los
   tests sin compilar y mide otra cosa.
2. **El enunciado de la tarea se transforma con el mismo diccionario.** Un enunciado que dice
   `get_queryset` sobre un código donde eso se llama `f7` no mide legibilidad: mide si el agente
   sobrevive a un enunciado que no casa con nada. El objetivo es un mundo **internamente
   consistente** donde todo se llama mal pero el enunciado y el código hablan el mismo idioma.
   Lo mismo aplica a trazas, logs y mensajes de error que aparezcan en la tarea.
3. **Renombrado solo de símbolos resolubles estáticamente.** Nada de tocar lo que se alcanza por
   `getattr`, por cadenas, por reflexión o por API pública consumida desde fuera. El pre-flight
   §3.6.3 es el que verifica que la restricción se respetó.
4. **Verificación antes de cada condición**, no una sola vez al principio.

### 4.4 A2 y el punto donde la partición se rompe

Los nombres están en la familia A porque cambian lo que lees dentro del fichero. Pero buscar en un
repositorio es buscar nombres, así que A2 degrada también la navegación. Es el único punto donde
las dos familias se solapan, y está previsto, no es un descuido del diseño.

Esto lo convierte en el resultado más informativo del experimento en lugar de en un problema, por
dos razones. Primero, porque el eje de tooling (§5.2) lo desambigua: si A2 duele sobre todo
cuando **no** hay grep, el daño era de navegación; si duele igual con grep y sin grep, era de
lectura. Segundo, porque si A2 sale como la transformación más dañina de todas — que es
plausible — el artículo deja de ser "la organización gana" y pasa a ser algo más preciso y más
útil: que la frontera real no está entre cómo se escribe y cómo se organiza, sino entre lo que
sirve para **encontrar** y lo que sirve para **entender**.

---

## 5. El harness

### 5.1 Por qué propio

Un agente comercial da validez externa pero es caja negra, cambia entre versiones, no permite
variar modelo con comodidad y no instrumenta lo que hace falta medir. Un harness propio da
control de presupuesto, reproducibilidad y — sobre todo — el registro de **qué ficheros abre y en
qué orden**, que es la hipótesis medida directamente en lugar de inferida del resultado.

El harness se construye en serio: no es un juguete de demostración, es un agente de edición con
las herramientas que usaría cualquiera.

### 5.2 Las dos dotaciones

| Dotación | Herramientas |
|---|---|
| **Rica** (por defecto) | leer fichero, listar directorio, **grep repo-wide por contenido**, correr tests, editar |
| **Pobre** | las mismas **menos grep** |

La diferencia entre las dos es la variable: sin búsqueda por contenido, encontrar el sitio depende
de que los nombres de fichero y la jerarquía te lo digan, que es exactamente lo que B2 destruye.
Convierte "un buen buscador compensa la mala organización" de objeción en dato.

Corre solo contra T0, T2 y T3 (§6.4): cruzarlo con todo duplicaría el experimento sin responder
nada más.

### 5.3 Presupuesto por tarea

**Límite fijo e idéntico en todas las condiciones**: 40 turnos de agente, y un techo de tokens de
entrada acumulados por tarea.

Esta decisión no es cosmética. Sin techo, la mala organización solo se paga en coste — el agente
acaba encontrando el sitio a base de abrir ficheros — y el resolve rate no se mueve, con lo que el
experimento concluiría erróneamente que la organización da igual. Con un techo realista, el efecto
aparece en las dos dimensiones y ambas se reportan por separado. El techo se elige en el
pre-flight como el que deja el baseline T0 en zona discriminante (§3.6.5).

### 5.4 El sistema de medición

Es la pieza donde se juega la comparabilidad, y merece tanto diseño como el agente. Un harness de
agente mediocre produce resultados pobres, que se ven; un sistema de medición mediocre produce
resultados falsos, que no.

#### 5.4.1 Registro por ejecución

Traza completa de herramientas invocadas con sus argumentos **y con los rangos de líneas que
devolvieron**; turno del primer edit; tokens de entrada y salida por turno; diff final; resultado
de `fail_to_pass` y `pass_to_pass`. Y la procedencia: versión del harness, versión del
transformador, hash del árbol transformado, modelo, parámetros de muestreo y seed.

Sin procedencia registrada, un cambio a mitad de campaña deja el conjunto de datos sin
interpretación posible y no hay forma de saberlo después.

#### 5.4.2 Localización: identidad de símbolo, no de fichero

Medir localización como "¿abrió el fichero correcto?" se rompe en las condiciones que más
importan. Con B2 el fichero se llama distinto. Con B1 el símbolo se ha mudado a otro fichero. Y
con B5, cuando todo está concatenado, **solo hay un fichero, así que la métrica marca acierto
siempre** — justo en la condición donde queremos ver si el agente se pierde.

La definición correcta es por símbolo. El objetivo de una tarea es el conjunto de símbolos que
toca el parche de referencia. El transformador mantiene, por condición, un mapa de identidad de
cada símbolo a su fichero y rango de líneas. Del lado del agente se registran los rangos que
**realmente ha visto** — lecturas parciales y resultados de grep incluidos, no solo ficheros
abiertos enteros — y se proyectan sobre ese mapa.

De ahí salen tres medidas comparables entre todas las condiciones: si llegó a ver la región
objetivo, cuántos símbolos distintos vio antes de verla, y en qué punto de su secuencia de
lecturas apareció.

#### 5.4.3 Normalización del coste

Las transformaciones cambian el tamaño del repositorio. A4 quita comentarios y docstrings, así que
el árbol degradado es **más pequeño**: el agente ve más código por token y llega más lejos con el
mismo presupuesto. Sin normalizar, esa ventaja artificial se leería como "quitar los comentarios
no duele, incluso ayuda".

Se registra el tamaño en tokens de cada repo bajo cada condición, y el coste de exploración se
reporta en dos unidades: tokens absolutos y **fracción del repo vista** antes del primer edit.
Cuando las dos discrepen, manda la fracción y se explica la discrepancia.

#### 5.4.4 Aislamiento y reproducibilidad

Cada ejecución arranca de una copia fresca, sin estado compartido con la anterior y sin reutilizar
caché de proveedor que pueda sesgar entre condiciones. Temperatura fija y seed donde el proveedor
la respete. Orden de tareas fijado, para que ningún corte dependa de él. Versiones congeladas
durante toda la campaña: si algo cambia a mitad, el bloque afectado se vuelve a correr o se
declara en el artículo como corrido con otra versión.

#### 5.4.5 Los fallos de infraestructura no son fallos del agente

Rate limits, timeouts de red, entornos que no llegan a instalarse, cortes del proveedor: se
clasifican aparte, se
reintentan hasta un número fijo de veces, y **se cuentan**. Un experimento donde el 8% de las
ejecuciones murió por rate limit y se contabilizó como fracaso del agente está midiendo otra cosa.
El artículo reporta la tasa de descartes por condición; si es asimétrica entre condiciones, eso es
en sí mismo un problema que hay que explicar antes de leer los resultados.

#### 5.4.6 Oráculos de control

Dos agentes falsos que recorren el pipeline entero en todas las condiciones sin gastar un token de
modelo:

- **No-op**: no edita nada. Debe dar 0% en todas las condiciones. Si da más, hay tareas cuyos
  tests no discriminan.
- **Oráculo**: aplica el parche de referencia traducido a la condición. Debe dar 100% en todas. Si
  da menos, o la transformación rompió el repo, o el mapa de identidad de símbolos está mal.

Es la comprobación más barata del diseño y la que atrapa los errores más caros — los que hacen que
una transformación rota se lea exactamente igual que un agente que fracasa. Se corre **antes de
cada bloque**, no una sola vez al principio.

#### 5.4.7 Ninguna métrica depende de un juez

Las tres categorías de modo de fallo se derivan mecánicamente de los tests y de la traza: no
localizó (nunca vio la región objetivo), localizó pero editó mal (la vio y los `fail_to_pass`
siguen rojos), rompió otra cosa (`pass_to_pass` en rojo). No hay LLM evaluador en ninguna parte
del circuito, lo que elimina de raíz una familia entera de sesgos.

#### 5.4.8 Agregación

Las celdas con réplicas se reportan como media con rango observado entre seeds, igual que en el
artículo previo. Las de una sola pasada se reportan como una sola pasada, sin intervalo. Las
comparaciones que sostienen las predicciones de §8 se hacen sobre las celdas con réplicas; el
desglose de una pasada se presenta como indicativo y se dice así.

### 5.5 Modelos y control externo

Dos tiers vía Azure, el mismo par que el artículo previo para que las cifras se puedan comparar:
`gpt-5.4-mini` como tier bajo y `gpt-5.4` como tier alto. La disponibilidad en el despliegue se
confirma en el pre-flight; si ese par no está, se toma el par equivalente de la familia disponible
y se declara en el artículo.

**Claude Code** corre las cuatro condiciones de titular, una pasada, con su modelo por defecto.
No es una celda del diseño: es el control que descarta que el efecto sea un artefacto de un
harness pobre.

### 5.6 Aislamiento y preparación del entorno

La campaña corre con contenedores en el Mac; el ejecutor de entorno virtual se conserva como
alternativa verificada para la máquina que no los admite (§2). Con contenedor el aislamiento es de
sistema; con entorno virtual es solo de dependencias, y entonces instalar y ejecutar la suite de un
repo de terceros ocurre directamente sobre la máquina — razón por la que solo entran repositorios
públicos y conocidos.

Lo que **no** cambia entre los dos es la capa de preparación, y ahí hay dos trampas verificadas
empíricamente. La primera: `pip install -e '.[test]'` sobre un repo que no declara ese extra
imprime un aviso y **sale con código 0**, así que una cadena de fallbacks encadenada con `||` nunca
dispara y la suite acaba corriendo sin sus dependencias, con errores de colección que se leen como
suite en rojo. Por eso solo se intenta lo que el repo declara de verdad —extras, grupos de
dependencias, ficheros de requisitos, `deps` de `[testenv]` en `tox.ini`— y el éxito se comprueba
**funcionalmente, colectando los tests**, no leyendo códigos de salida. La segunda: los `addopts`
de un proyecto pueden exigir plugins que no declara en ninguna parte; se deducen de los argumentos
que pytest rechaza y se instalan en un reintento. Neutralizar los `addopts` no es opción, porque a
veces incluyen `--doctest-modules` y los doctests son media suite.

El aislamiento obliga además a resolver un problema que con contenedores no aparecía, y que hay
que respetar igual en los dos ejecutores. Un repo se instala en modo
editable a partir de la estructura que declara su `pyproject.toml`, y B2 —aplanar directorios y
renombrar ficheros— destruye precisamente esa estructura. Con la instalación editable rota, los
tests de validación no encontrarían nada que importar, y la condición se leería como un fracaso
total del agente cuando en realidad es fontanería rota.

Las dos decisiones que lo resuelven:

1. **En el entorno se instalan las dependencias del repo, no el repo.** El árbol transformado se
   pone al alcance de pytest por ruta, no por instalación, así que ninguna transformación puede
   invalidar el entorno. Con el ejecutor de entorno virtual, ese entorno se crea una vez por
   repositorio y sobrevive a las 54 corridas. Con contenedores no: el contenedor se destruye al
   cerrar la corrida, y la instalación se repite (44 s medidos en python-stdnum). Conservar la
   propiedad exige congelar una imagen por repositorio con las dependencias ya dentro, y se
   decide al planificar la campaña — en la fase 0, con un perfilado por candidato, no compensa.
2. **El nombre del paquete raíz no se transforma nunca.** Todo lo de dentro sí: subpaquetes,
   módulos, jerarquía, símbolos. Pero el punto de entrada se conserva, porque es lo único que
   mantiene válidos a la vez la instalación de dependencias, los imports desde fuera y el
   comando de test. No afecta a la hipótesis: lo que se mide es la organización interna del
   repositorio, no cómo se llama el paquete visto desde fuera.

Coste declarado, solo del ejecutor sin contenedor: al no haber aislamiento de sistema, un repo que
ensucie el entorno global o que dependa de bibliotecas del sistema puede contaminar corridas
posteriores. La mitigación es el criterio de admisión —solo entran repos que instalen limpio— y la
verificación de equivalencia antes de cada bloque (§3.6.3), que detectaría el desvío. Con
contenedor el coste desaparece, pero aparece otro: la imagen `slim` no trae git, y varios
candidatos derivan su versión del repositorio en tiempo de instalación, así que la imagen tiene que
traerlo o `pip install -e .` aborta.

**El repo se copia dentro del contenedor, no se monta.** Medido sobre python-stdnum en el mismo
contenedor y con el mismo entorno instalado: 113 s de suite sobre el volumen montado frente a 43 s
con el repo dentro. Multiplicado por 54 corridas eso son horas, y el coste de entorno es además una
de las dimensiones de examen de la fase 0 (§3.2), así que medirlo inflado por el sistema de
ficheros del anfitrión distorsionaría también la selección de repos. La copia tiene un segundo
efecto útil: el clon del anfitrión queda intacto, sin `.egg-info` ni artefactos de la suite, que es
lo que permite reutilizarlo entre condiciones sin arrastrar estado.

---

## 6. Condiciones

### 6.1 Titular — el 2×2 de familias

| | Organización intacta | Organización degradada |
|---|---|---|
| **Escritura intacta** | **T0** baseline | **T2** (B1–B4) |
| **Escritura degradada** | **T1** (A1–A4) | **T3** todo |

Tres seeds, dos tiers. Es la única parte con réplicas, y es la que responde la pregunta del
artículo. La interacción importa tanto como los efectos principales: si T3 es mucho peor que la
suma de T1 y T2, las prácticas se apoyan unas en otras y el mensaje práctico cambia.

### 6.2 Knock-out y add-back

Ocho celdas de **knock-out** desde T0 (quitar A1, A2, A3, A4, B1, B2, B3, B4 de una en una) y
ocho de **add-back** desde T3 (devolver cada una de las ocho por separado). Una pasada, un tier.

Las dos direcciones no coinciden, y **donde no coinciden está el artículo**. El knock-out contesta
"qué pierdo si dejo de hacer esto"; el add-back contesta "qué recupero si solo hago esto". Una
práctica cuyo knock-out no duele pero cuyo add-back salva es una práctica que solo importa cuando
todo lo demás ya está mal — y ese es un consejo distinto del que se da hoy.

Se descarta la escalera acumulativa por confundir el orden de aplicación con el efecto: quitar la
documentación en el quinto peldaño, cuando el código ya es ilegible, la haría parecer inocua.
El knock-out y el add-back dan la misma lectura de escalera — dos, enfrentadas — sin depender de
un orden arbitrario.

**Regla declarada antes de correr**: el desglose se ejecuta en el tier donde el 2×2 muestre mayor
separación entre T1 y T2. Se fija así por adelantado para que la elección no sea post-hoc.

### 6.3 Curva de tamaño

Tres puntos nuevos sobre B5 (~500, ~2.000, ~10.000 líneas por fichero), con el original como
cuarto punto. Es la única parte del diseño que busca un umbral en lugar de una diferencia, y por
eso necesita más de dos puntos.

### 6.4 Eje de tooling

T0, T2 y T3 con la dotación pobre, un tier, una pasada. Tres celdas.

### 6.5 Sonda TypeScript

Cuatro celdas sobre el repo TS con sus 6 tareas: T0, A1 knock-out, T3, A1 add-back.

### 6.6 Recuento

| Bloque | Corridas |
|---|---|
| Titular (4 × 3 seeds × 2 tiers) | 24 |
| Claude Code (4 × 1) | 4 |
| Knock-out | 8 |
| Add-back | 8 |
| Curva de tamaño | 3 |
| Tooling pobre | 3 |
| Sonda TS | 4 |
| **Total** | **54** |

A 24 tareas por corrida (6 en la sonda), del orden de **1.250 ejecuciones de agente**, la mayoría
en el tier mini. Es el techo del presupuesto: cualquier ampliación sale de recortar otra cosa.

La réplica de control en SWE-bench (§3.4) son 4 corridas adicionales sobre su propio subconjunto,
contabilizadas aparte porque su coste por tarea es distinto.

---

## 7. Métricas y taxonomía de resultado

**Primaria**: resolve rate — pasan los `fail_to_pass` y siguen pasando los `pass_to_pass`.

Si el artículo se queda en la tabla de porcentajes, describe pero no explica. Lo que lo convierte
en explicación son tres medidas de proceso que el harness registra sin coste extra:

- **Localización**, definida por símbolo y no por fichero (§5.4.2). ¿Llegó a ver la región que
  toca el parche de referencia, y cuánto vio antes de verla? Es la hipótesis medida directamente,
  sin pasar por el resultado final.
- **Coste de exploración.** Turnos, tokens de entrada y fracción del repo vista antes del primer
  edit (§5.4.3).
- **Modo de fallo**, en tres categorías excluyentes:
  1. **No localizó** — nunca vio la región objetivo.
  2. **Localizó pero editó mal** — lo abrió, editó, y los `fail_to_pass` siguen rojos.
  3. **Rompió otra cosa** — arregló el fallo objetivo pero tumbó `pass_to_pass`.

Esa taxonomía es la que sostiene el argumento: separa "no encuentra" de "no entiende", que es
exactamente la partición entre las dos familias.

**Todas las métricas se reportan además partidas por estrato de fallo** (§3.3.1), genérico contra
dominio. Es el corte que más probablemente cambie la lectura de la tabla principal.

---

## 8. Predicciones registradas

Escritas antes de correr nada. Su función es que el análisis no degenere en pesca de
correlaciones.

- **P1.** T2 reduce el resolve rate más que T1.
- **P2.** El daño de T1 se concentra en el modo de fallo 2 ("editó mal"); el de T2 en el modo 1
  ("no localizó").
- **P3.** En add-back, devolver B3 (documentación) o B2 (jerarquía) recupera más que devolver A3
  (formato).
- **P4.** El tamaño de fichero tiene umbral: plano hasta cierto punto, caída a partir de ahí. No
  se predice dónde.
- **P5.** El tier fuerte tolera la degradación de escritura mejor que el mini; en organización la
  brecha entre tiers es menor, porque navegar depende del tooling y no de la capacidad.
- **P6.** El daño de B2 (jerarquía) es sustancialmente mayor con dotación pobre que con dotación
  rica. Si no lo es, el grep no compensa la mala organización tanto como se supone.
- **P7.** El efecto de toda la degradación se concentra en el estrato de fallos de dominio. Los
  fallos genéricos son casi insensibles, y muy en particular a la familia A.
- **P8.** Dentro del estrato de dominio, la familia B pesa más que en el conjunto global, porque
  esos fallos exigen leer varios sitios para poder juzgarlos.

---

## 9. Qué tumbaría la tesis, y condiciones de abandono

Resultados que refutan la hipótesis del autor, y que se publican igual si salen:

- **T1 ≈ T2.** Las dos familias pesan lo mismo y la partición no era informativa.
- **A2 es la transformación más dañina de todas.** No refuta el experimento pero sí el marco:
  la frontera útil no sería escritura contra organización, sino encontrar contra entender (§4.4).
- **La curva de tamaño sale plana en todo el rango probado.** El umbral no existe dentro de lo
  que un repo mediano puede producir.
- **Los dos estratos de fallo se comportan igual.** Refutaría P7 y P8, y dejaría sin base la
  explicación de por qué los benchmarks actuales no ven este efecto.

**Condición de abandono**: si tras el pre-flight el baseline T0 no es discriminante en ninguno de
los dos tiers después de ajustar la dificultad, el experimento no se corre. Un suelo o un techo
no dejan sitio donde medir una caída.

---

## 10. Estructura del artículo

1. La pregunta: las buenas prácticas se justificaron para lectores humanos, y ahora una parte de
   las lecturas las hace un agente.
2. El método: degradación semánticamente equivalente, las dos familias, por qué el sustrato no
   puede ser SWE-bench.
3. El 2×2 y su interacción.
4. Knock-out contra add-back: la tabla de qué se pierde y qué se recupera.
5. La curva de tamaño.
6. Localización y modos de fallo: por qué pasa lo que pasa.
7. Los dos estratos de fallo, y qué dice de cómo se miden hoy estas cosas.
8. El caso de los nombres, y la frontera entre encontrar y entender.
9. Qué se traduce en práctica, sin ir más lejos de lo que aguanten los datos.

### 10.1 Reglas de honestidad heredadas

- Los límites de cobertura van **por delante**, en el bloque de apertura, como en el artículo de
  CooperBench: cuántos repos, cuántas tareas, qué tiene réplicas y qué no.
- Las celdas de una sola pasada se presentan como una sola pasada, sin barras de error fabricadas.
- Ninguna recomendación más fuerte que el dato que la sostiene. Si una práctica sale plana en un
  set de 24 tareas sobre tres repos Python, eso es lo que se dice — no "el formato no importa".
- Las predicciones de §8 se publican con su acierto y su fallo, incluidas las que fallen.
- El eje de tooling se reporta como lo que es: dos puntos, no una curva.

---

## 11. Riesgos

| Riesgo | Mitigación |
|---|---|
| Una transformación rompe el repo y se lee como fallo del agente | Verificación de equivalencia por repo y condición, más oráculos de control antes de cada bloque (§3.6.3, §5.4.6) |
| A4 encoge el repo y regala presupuesto de lectura, leyéndose como "los comentarios no ayudan" | Coste reportado también como fracción del repo vista (§5.4.3) |
| La localización se satura en B5, donde solo hay un fichero | Localización definida por símbolo y rango, no por fichero (§5.4.2) |
| Los fallos de dominio fabricados resultan reconocibles por patrón | Filtro de aislamiento en el pre-flight: si el modelo lo detecta viendo la función sola, no es de dominio (§3.6.2b) |
| Fallos de infraestructura contados como fracasos del agente | Clasificación aparte, reintentos y tasa de descarte reportada por condición (§5.4.5) |
| El enunciado deja de casar con el código renombrado | Diccionario de renombrado aplicado también al enunciado, trazas y logs (§4.3.2) |
| Baseline pegado al suelo o al techo | Pre-flight con condición de abandono (§9) |
| El presupuesto por tarea esconde el efecto en coste en vez de en éxito | Techo fijo elegido en pre-flight; se reportan las dos dimensiones (§5.3) |
| Renombrado que rompe reflexión o API pública | Solo símbolos resolubles estáticamente, verificado por suite (§4.3.3) |
| Repos con tipado en runtime invalidan A1 | Criterio de exclusión 4 (§3.2) |
| La máquina se satura y se pierde la tanda | Corridas secuenciales, una copia viva por condición, limpieza por bloque (§2) |
| Sin contenedores no hay aislamiento de sistema: un repo puede contaminar corridas posteriores | Solo entran repos que instalen limpio aquí; verificación de equivalencia antes de cada bloque (§5.6, §3.6.3) |
| Una transformación rompe la instalación editable y se lee como fracaso del agente | Se instalan las dependencias, no el repo; el nombre del paquete raíz nunca se transforma (§5.6) |
| Disco lleno por acumulación de copias y clones | Comprobación de disco antes de cada bloque, borrado registrado (§2) |

---

## 12. Alcance excluido

Fuera de este experimento, por decisión explícita:

- **Prácticas de proceso**: revisión de código, CI, convenciones de commit, gestión de ramas.
  Este experimento mide propiedades del código en reposo.
- **Generación de código nuevo desde cero.** Todas las tareas son de modificación sobre un
  codebase existente, que es donde las prácticas de legibilidad tienen sentido.
- **Más de un eje de tooling.** Se mide grep contra no-grep. Índices semánticos, LSP y navegación
  por símbolos quedan fuera.
- **Generalización más allá de Python**, salvo lo que autorice la sonda TS sobre el eje tipos.
- **Recomendaciones de estilo concretas** (qué formateador, qué convención de nombres). El
  experimento mide presencia contra ausencia, no variantes.
