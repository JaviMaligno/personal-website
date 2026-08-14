# Buenas prácticas de software para coding agents: ¿cómo está escrito, o dónde está?

**Fecha:** 2026-08-14
**Estado:** diseño aprobado, pendiente de pre-flight
**Artículo predecesor:** [Coding Agents and Teamwork: Social Skills, or Structure?](../../../src/content/blog/en/coding-agents-structure.md) (2026-07-12)
**Ejecución:** máquina principal. Corridas secuenciales, copias de repo desechables, limpieza obligatoria (§2).

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

- **Corridas secuenciales.** Como mucho dos condiciones en vuelo a la vez, nunca más.
- **Una copia de repo viva por condición en curso.** Cada condición trabaja sobre una copia
  desechable; al cerrar la condición se borra la copia. Nunca acumular árboles transformados.
- **Limpieza obligatoria al cerrar cada bloque**: copias de repos, clones de SWE-bench,
  entornos virtuales y contenedores fuera. Comprobación de disco libre **antes** de arrancar
  cada bloque, y registro de lo que se borró.
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

### 3.2 Criterios de selección de repos

Por orden de dureza:

1. **Suite verde, rápida y discriminante.** Requisito duro: sin tests que distingan arreglado de
   roto no hay medida. "Rápida" significa que la suite completa cabe en la ejecución de cada
   tarea sin dominar el tiempo de corrida.
2. **Tamaño mediano**, del orden de miles a decenas de miles de líneas. Por debajo, el agente lee
   el repo entero y todas las transformaciones de familia B dan cero por construcción. Por
   encima, el barrido no cabe en el presupuesto.
3. **Dependencias instalables sin pelea**, porque el entorno se rehace una vez por condición.
4. **Sin tipado en runtime.** Repos que usan anotaciones para validar en ejecución (pydantic,
   dataclasses con conversión, `typing.get_type_hints`) quedan fuera: ahí A1 no es
   semánticamente equivalente.
5. **Sin código de cliente.**

Selección: **tres repos Python** de terceros que cumplan lo anterior, más la opción de uno propio
si encaja. Los de terceros evitan que el resultado se lea como dependiente del estilo del autor;
uno propio aporta un sustrato garantizado no visto. La lista concreta se cierra en el pre-flight
(§3.5), no aquí, porque el criterio 1 solo se verifica ejecutando.

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

Los bugs inyectados deben repartirse entre tipos (condición invertida, argumento mal pasado,
caso límite eliminado, estado no actualizado) para que el set no mida una sola habilidad.

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

1. **Selección de repos verificada**: suite verde, tiempo de suite medido, ausencia de tipado en
   runtime comprobada.
2. **24 tareas generadas y validadas**: cada una falla los tests que debe y pasa los demás, en el
   repo original.
3. **Equivalencia de cada transformación verificada por repo**: en el árbol transformado, la
   suite completa da **el mismo resultado** que en el original. Una transformación que rompe el
   repo se lee exactamente igual que un agente que falla, y es el error más caro de descubrir
   tarde.
4. **Reversibilidad comprobada**: aplicar y deshacer devuelve un árbol funcionalmente idéntico.
5. **Baseline discriminante**: el resolve rate en T0 no puede estar pegado al 0% ni al 100% en
   ninguno de los dos tiers. Si lo está, no hay margen para medir caídas y hay que retocar la
   dificultad de las tareas antes de seguir.
6. **Modelos disponibles confirmados** en el despliegue de Azure (§5.5).

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

### 5.4 Instrumentación

Por cada ejecución se registra: secuencia completa de herramientas invocadas con sus argumentos,
ficheros abiertos en orden, turno del primer edit, tokens de entrada y salida por turno,
diff final, y resultado de los tests `fail_to_pass` y `pass_to_pass`.

### 5.5 Modelos y control externo

Dos tiers vía Azure, el mismo par que el artículo previo para que las cifras se puedan comparar:
`gpt-5.4-mini` como tier bajo y `gpt-5.4` como tier alto. La disponibilidad en el despliegue se
confirma en el pre-flight; si ese par no está, se toma el par equivalente de la familia disponible
y se declara en el artículo.

**Claude Code** corre las cuatro condiciones de titular, una pasada, con su modelo por defecto.
No es una celda del diseño: es el control que descarta que el efecto sea un artefacto de un
harness pobre.

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

- **Localización.** ¿Llegó a abrir el fichero que toca el parche de referencia, y cuántos ficheros
  abrió antes? Es la hipótesis medida directamente, sin pasar por el resultado final. Se reporta
  como tasa de acierto de localización y como posición mediana del fichero correcto en la
  secuencia de aperturas.
- **Coste de exploración.** Turnos y tokens de entrada consumidos antes del primer edit.
- **Modo de fallo**, en tres categorías excluyentes:
  1. **No localizó** — nunca abrió el fichero correcto.
  2. **Localizó pero editó mal** — lo abrió, editó, y los `fail_to_pass` siguen rojos.
  3. **Rompió otra cosa** — arregló el fallo objetivo pero tumbó `pass_to_pass`.

Esa taxonomía es la que sostiene el argumento: separa "no encuentra" de "no entiende", que es
exactamente la partición entre las dos familias.

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

---

## 9. Qué tumbaría la tesis, y condiciones de abandono

Resultados que refutan la hipótesis del autor, y que se publican igual si salen:

- **T1 ≈ T2.** Las dos familias pesan lo mismo y la partición no era informativa.
- **A2 es la transformación más dañina de todas.** No refuta el experimento pero sí el marco:
  la frontera útil no sería escritura contra organización, sino encontrar contra entender (§4.4).
- **La curva de tamaño sale plana en todo el rango probado.** El umbral no existe dentro de lo
  que un repo mediano puede producir.

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
7. El caso de los nombres, y la frontera entre encontrar y entender.
8. Qué se traduce en práctica, sin ir más lejos de lo que aguanten los datos.

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
| Una transformación rompe el repo y se lee como fallo del agente | Verificación de equivalencia por repo y condición, bloqueante (§3.6.3) |
| El enunciado deja de casar con el código renombrado | Diccionario de renombrado aplicado también al enunciado, trazas y logs (§4.3.2) |
| Baseline pegado al suelo o al techo | Pre-flight con condición de abandono (§9) |
| El presupuesto por tarea esconde el efecto en coste en vez de en éxito | Techo fijo elegido en pre-flight; se reportan las dos dimensiones (§5.3) |
| Renombrado que rompe reflexión o API pública | Solo símbolos resolubles estáticamente, verificado por suite (§4.3.3) |
| Repos con tipado en runtime invalidan A1 | Criterio de exclusión 4 (§3.2) |
| La máquina se satura y se pierde la tanda | Corridas secuenciales, una copia viva por condición, limpieza por bloque (§2) |
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
