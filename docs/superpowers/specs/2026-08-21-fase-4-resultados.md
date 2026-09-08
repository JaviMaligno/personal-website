# Fase 4 — Resultados: tareas, oráculos y la campaña reanudable

**Fecha:** 2026-08-21
**Plan:** [`../plans/2026-08-20-fase-4-tareas-y-oraculos.md`](../plans/2026-08-20-fase-4-tareas-y-oraculos.md)
**Spec:** [`2026-08-14-software-practices-for-coding-agents-design.md`](2026-08-14-software-practices-for-coding-agents-design.md), §3.2, §3.3, §3.6.2b, §6.1
**Fase 3:** [`2026-08-20-fase-3-resultados.md`](2026-08-20-fase-3-resultados.md)
**Código:** https://github.com/JaviMaligno/agent-code-practices — `545 passed`

---

## 1. Seis tareas validadas y un agente que puede resolverlas

`tasks/python-stdnum/` tiene cuatro tareas genéricas por inyección de fallo (invert_condition,
off_by_one, drop_none_check, swap_args) y dos de dominio escritas a mano (el `get_gender` del CURP
mexicano y la rotación de `iso11649`). `tasks/pint/` tiene cuatro genéricas. Cada una declara sus
`fail_to_pass` y sus `pass_to_pass`, y ninguna se acepta sin que la suite del repo confirme que el
parche pone en rojo exactamente esos tests.

El agente tiene cinco herramientas (buscar, listar, leer, editar, correr los tests) y la dotación
pobre le quita la búsqueda. Su traza registra turnos, primer turno con edición, y qué rangos de
líneas llegó a ver, que es lo que después permite separar «no lo encontró» de «lo encontró y lo
editó mal».

---

## 2. El filtro de aislamiento no discriminaba nada hasta que tuvo control

§3.6.2b pide enseñar al modelo solo la función mutada, fuera de contexto, y preguntar si tiene un
fallo: si lo ve, el fallo no era de dominio.

Medido: preguntado directamente —«¿tiene esta función un fallo?»— los dos tiers dicen **sí al 100%**
de las funciones, incluidas las correctas. Preguntado en tono conservador dicen **no a todas**,
incluidas las rotas. Con un prompt neutro discrimina 4 de 6 en un conjunto de control pequeño, y los
dos errores son el hallazgo:

- Los modelos marcan como defectuosa la versión **correcta** de `stdnum.mx.curp.get_gender`. En un
  CURP la entrada está en español (`H` de Hombre) y la salida en convención inglesa (`M` de Male),
  así que el mapeo correcto `H → 'M'` se lee como un error obvio e invertirlo se lee como el
  arreglo. Un filtro sin control habría tirado la mejor tarea de dominio del conjunto.
- En un off-by-one sobre `len(number) != 11` no ven nada, porque eso no se puede juzgar sin conocer
  el formato.

De ahí el **control emparejado**: se pregunta por la original *y* por la mutada, y solo cuenta como
detección que señale la segunda y no la primera. Si señala las dos, no está detectando la mutación:
está diciendo que no entiende la función.

Consecuencia para el diseño: la frontera genérico/dominio **no coincide con la forma sintáctica del
fallo**, y §3.3 asume que sí.

---

## 3. El runner de la campaña reprodujo el riesgo número uno del spec

La primera tanda dio 12 registros y ninguno medía al agente:

- **T1 y T3: cero mediciones.** El parche de una tarea es un diff unificado contra el árbol
  original, con hunks anclados a números de línea. A1 y A3 desplazan todas las líneas, así que un
  hunk anclado a `@@ -118` no encajaba en ningún sitio.
- **T2: las seis tareas como «rompió otra cosa».** B4 saca la suite del árbol, y no se le devolvía al
  contenedor, así que los tests que la validación necesita no existían.

Es literalmente el modo de fallo que §11 pone como riesgo número uno: *una transformación que rompe
el repo se lee exactamente igual que un agente que fracasa*. Y ocurrió después de haber arreglado
seis veces esa misma clase de error dentro de las transformaciones.

### 3.1. Aplicar el parche por contenido no arregla el caso general

Fue el primer arreglo intentado y no basta: A2 renombra los identificadores del cuerpo y A3 le
cambia el formato, así que **el texto del hunk tampoco existe** en el árbol degradado. Reinyectar la
mutación desde el catálogo tampoco alcanza: las tareas de dominio se escriben a mano y no tienen una
forma del catálogo que repetir.

### 3.2. Lo que sí vale para todas: invertir el orden

El fallo entra donde el parche encaja —el árbol original— y **la degradación va encima**. Las
transformaciones son semánticamente equivalentes, luego preservan el fallo inyectado.

Que lo preserven no se supone: `tests/test_campaign.py` lo comprueba **ejecutando el código** del
árbol degradado, no buscando una cadena en un fichero. Con A3 el formato ya no se parece al
original y cualquier aserción sobre el texto mediría la transformación en vez de la tarea. Y con un
control: la misma degradación sin fallo tiene que seguir dando el resultado correcto, porque si no un
árbol roto por la transformación daría el mismo resultado y pasaría por medida.

---

## 4. El oráculo se deriva del árbol donde se mide

No de los nodeids que la tarea trae del original. B1 mueve la definición a otro fichero, así que el
doctest de la función pasa a ejecutarse con **otro nodeid**; B4 saca la suite del árbol. Traducir
nodeids a mano sería adivinar.

Así que cada celda monta **dos** árboles degradados —uno sano y uno con el fallo— y el oráculo es la
diferencia entre lo que la suite responde en cada uno. Ya está confirmado en datos: la primera celda
de T2 salió con **1** test en el oráculo donde la tarea declaraba 2, porque el nodeid del doctest
cambió al moverse la definición.

**Una celda cuyo fallo no pone en rojo ningún test se declara no medible y no llega al modelo.**
Gastar inferencia ahí no compra nada y deja escrito un resultado que se lee como un agente que
fracasó. Por lo mismo, `summarise()` calcula la tasa **solo sobre celdas medibles** y cuenta las no
medibles aparte: es el error que hundió T2 entera en la primera tanda, y el resumen que va al
artículo tiene que ser incapaz de cometerlo.

---

## 5. Dos decisiones que no pueden ser flags

- **Si el repo se instala lo decide la condición.** B1, B2 y B5 dejan el árbol sin correspondencia
  con lo que declara su `pyproject` (§5.6): instalarlo ahí mide el paquete que pip baja de PyPI en
  vez del árbol transformado, y la celda sigue leyéndose como un resultado.
- **Si hay que devolver la suite, también.** B4 la esconde del agente, que es lo que la condición
  mide, pero el oráculo la necesita.

Derivarlas de la condición y no de la línea de comandos es lo que impide que una celda se mida mal
por un flag que alguien olvidó.

---

## 6. La campaña tiene que sobrevivir a la máquina

Tres corridas se perdieron: dos por falta de memoria del portátil y una porque los contenedores se
borraron a mano estando en vuelo. Con el registro escrito al final, cada una habría costado horas de
agente ya pagadas.

Ahora **cada celda se apunta en disco en cuanto termina**, y al arrancar se salta lo que el registro
ya da por medido. Una celda que salió **no medible** no cuenta como hecha: eso fue fontanería, y
darla por hecha congelaría el hueco justo donde el diseño avisa del riesgo.

Dos detalles que costaron un bug cada uno:

- `copy_tree` usa `shutil.copytree` sin `dirs_exist_ok`, así que **la primera reanudación habría
  muerto** con `FileExistsError` sobre el árbol que dejó la corrida caída. El árbol a medias se
  rehace en vez de reutilizarse: puede llevar media transformación aplicada, y medir sobre eso es
  peor que perder los minutos. El borrado lleva guarda para no alcanzar nunca al clon de referencia.
- Cada condición escribe **su propio registro**: dos procesos sobre el mismo `jsonl` se entrelazan,
  y la reanudación lo lee para saber qué falta.

---

## 7. Coste medido

| Concepto | Medido |
|---|---|
| Transformación de un árbol (368 ficheros, familia A completa) | ~11 min |
| Celda de T0 (sin transformar): suites + agente | ~15–20 min |
| Celda transformada: + su transformación | ~25–30 min |
| Turnos por celda | 8–29 |
| Tokens de prompt por celda | 37k–108k |

El 2×2 completo sobre un repositorio son 24 celdas. Secuencial, es una noche de reloj.

La primera vez se lanzaron las cuatro condiciones en paralelo con 35–88 MB de RSS por proceso y la
memoria libre subiendo al 58%, lo que descartó la hipótesis de que la campaña fuera lo que ahogaba
la máquina —era el harness de agentes de las sesiones anteriores—. Aun así corre de una en una por
decisión explícita: menos carga simultánea y un solo contenedor vivo en cada momento.

---

## 8. Estado

Nueve transformaciones verificadas equivalentes, seis tareas validadas, el filtro de aislamiento con
control emparejado, y una campaña reanubable con oráculo por celda. **La baseline discrimina**, que
es la condición de §9 para que el experimento se corra.

El 2×2 está en marcha. Lo que ya está medido con el circuito corregido confirma lo que la primera
tanda no pudo: **T1 y T2 producen celdas medibles**, con su oráculo derivado del árbol degradado.
