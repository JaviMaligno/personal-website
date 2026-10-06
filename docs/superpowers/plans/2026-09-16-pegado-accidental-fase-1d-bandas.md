# Fase 1d (rediseñada): el eje de similaridad por bandas, un modelo por estímulo

**Goal:** La misma pregunta que la Fase 1d anterior —si el parecido entre el
pegote y la conversación cambia la probabilidad de que el modelo dude de la
intención, sobre el brazo N1, el que se delata solo— con un muestreo que sí
tenga potencia para responderla.

**Architecture:** Runner propio, `src/wrongpaste/run_phase1d.py`. El ranking de
cada prefijo se parte en **4 bandas contiguas por rango** y de cada banda se
sortean **21 artefactos distintos por prefijo, sin reemplazo**. Cada
(prefijo, artefacto) lo ve **un solo modelo**. Salen **1.344 celdas** y 1.344
estímulos distintos.

**Spec de origen:** [`../specs/2026-09-14-pegado-accidental-fase-1-design.md`](../specs/2026-09-14-pegado-accidental-fase-1-design.md)
**Plan que este sustituye:** [`2026-09-16-pegado-accidental-fase-1d.md`](2026-09-16-pegado-accidental-fase-1d.md) — el barrido de doce posiciones. Se conserva porque es el registro del diseño descartado y porque todo lo que no sea el muestreo (puerta, hipótesis, familia de Holm, control de composición por señal) sigue vigente ahí.
**Correcciones vigentes:** [`../specs/2026-09-13-pegado-accidental-correcciones.md`](../specs/2026-09-13-pegado-accidental-correcciones.md) (D1–D18)

---

## Por qué se rediseña el muestreo

La Fase 1b barrió el eje con **doce puestos exactos** del ranking: para cada
prefijo, la posición `p` daba el artefacto del puesto `sweep_index(p, N)`. Con 8
temas x 2 longitudes hay 16 prefijos, luego **16 estímulos distintos por
posición**, y los tres modelos se los repartían viendo cada uno los mismos 16.
Mucha conversación y poca información: la potencia real para la caída de 9 puntos
que el proyecto declara relevante era del **16 %**.

El coste de una tanda no está en los estímulos sino en las conversaciones, y el
rediseño no sube las conversaciones: las reparte mejor.

- **Bandas en vez de puestos.** Doce puntos de una curva sostenidos por 16
  observaciones cada uno son doce estimaciones malas; cuatro tramos sostenidos
  por 288 son cuatro decentes. La resolución que se pierde en el eje no se estaba
  usando: la Fase 1b salió plana y lo que hace falta es poder descartar una
  pendiente, no dibujarla fina.
- **Un modelo por estímulo.** Los tres modelos viendo el mismo pegote no dan tres
  observaciones independientes del eje: dan una, replicada. Repartirlos triplica
  los estímulos con las mismas llamadas.

## El diseño, tal y como está implementado

| | |
|---|---|
| Brazo | Un solo nivel, `N1` (el pegote que se delata solo); banco `data/artifacts-n1/`, **84 artefactos** |
| Prefijos | 16 = 8 temas x 2 longitudes (`LENGTHS = [2, 10]`), los de la Fase 0, ya en disco |
| Bandas | `BANDS = 4`, tramos contiguos **por rango** del ranking, vía `run_phase0.stratum_window` |
| Artefactos por banda y prefijo | `ARTIFACTS_PER_BAND = 18`, sin reemplazo |
| Celdas | 4 x 21 x 16 = **1.344**, todas con un (prefijo, artefacto) distinto |
| Modelos | `gpt-5.6-sol-tst`, `gpt-5.6-luna-tst`, `claude-opus-5` — 384 celdas cada uno |
| Semilla maestra | `MASTER_SEED = 20260916` |
| Presupuesto | 3.456 llamadas al modelo evaluado, 2.304 al usuario simulado, 0 prefijos nuevos |
| Salida | `runs/phase1d/<ts>.jsonl` |

**Por qué 4 y 18.** Con dos bandas el eje solo tiene «cerca» y «lejos»; con más
se vuelve al problema de 1b. Con 4 bandas el banco de 72 da 18 por banda, que es
múltiplo de los 3 modelos: el reparto sale exacto y sin redondeos.
`ARTIFACTS_PER_BAND` se escribe como constante y **no** se deriva del banco,
porque es el tamaño del plan: un presupuesto que encogiera solo porque alguien
quitó un artefacto del banco sería un presupuesto que cambia solo. Si no llegan a
18 por banda, la tirada para antes de escribir en vez de repetir pegotes en
silencio.

**Qué artefacto le toca a cada celda.** `choose_band_artifact(ranking, band,
slot, prefix_id)`: se toma la ventana de la banda y se recorre en el orden de
`band_order(prefix_id, band, size)`, una permutación sembrada con
`blake2b(prefix|band)` —no con `hash()`, que está aleatorizado por proceso, ni
con la semilla de la tirada, para que (prefijo, banda, slot) determine el pegote
sin estado y una reanudación no dependa de recordar el `seed`—. El barajado no
sirve para que cada modelo vea los 21 artefactos de la banda (eso sale del
reparto de modelos): sirve para que el **slot no sea el rango fino** dentro del
tramo, que si no quedaría confundido con el modelo.

**Qué modelo le toca.** `(slot + tema + longitud + banda) % 3`, no sorteo. Con 18
slots por (prefijo, banda) cada modelo se lleva 6: 384 por modelo, 96 por
(modelo, banda), 48 por (modelo, banda, longitud). Si un modelo cayera más en las
bandas altas, el contraste entre modelos mediría la banda y el contraste entre
bandas mediría el modelo, que son las dos preguntas de la tanda. Los
desplazamientos hacen además que los modelos roten celda a celda, para que el
modelo no quede correlacionado con la hora de reloj contra un gateway compartido.

**Orden de la tirada.** La banda va en el bucle más interno: con la banda por
fuera, el primer cuarto de la tanda se correría entero en la banda 0 y la
variable independiente quedaría confundida con el momento del día. El prefijo va
por fuera porque el ranking se cachea por prefijo.

## Lo que la fila y la cabecera declaran

- **La banda viaja como `stratum` / `n_strata`**, que es lo que es: un estrato por
  rango del ranking, con su denominador al lado. `sweep_position` se queda en
  `None` — ese campo significa «uno de los doce puestos del barrido de 1b», y
  rellenarlo haría que un análisis conjunto leyera las dos tandas como si
  hubieran muestreado igual.
- **La cabecera (D5) declara `bands` y `artifacts_per_band`**, y no
  `sweep_positions`. Es lo que distingue este fichero del de la Fase 1d anterior
  sin mirar las filas: las dos tandas declaran la misma fase (`1d`) y el mismo
  nivel (`N1`).
- **Identidad de celda**: `p1d-<modelo>-<tema>-<turnos>-b<banda>-a<slot>`. Los
  `-b1-a07` de este diseño no se confunden con los `-s07` del barrido, y la
  reanudación va por identificador.
- **Reanudar un fichero del otro diseño para**: `check_resume_design` mira lo que
  la cabecera declara antes de tocar el fichero. Sin eso, ninguno de los 288
  identificadores viejos estaría en el plan nuevo, no se saltaría ninguna celda,
  se volvería a pagar la tanda entera y quedarían 1.440 filas de dos muestreos
  bajo una sola cabecera, con un resumen diciendo «saltadas: 0».

## Lo que NO cambia respecto del plan sustituido

Se lee allí, no se repite aquí:

- La **puerta de D12**: el ancho del eje se mide antes de gastar y, si alguna
  celda sale estrecha, la tirada no empieza (`check_axis`, importada de 1b).
- Las **hipótesis primarias** H4 (G baja con el parecido) y H5 (G es mayor en las
  conversaciones largas), su familia de Holm y las secundarias descriptivas.
- El **control de composición por señal**: las señales sí se ordenan por coseno,
  y `curve.signal_confound` / `curve.by_signal` dicen cuánto de la curva predice
  la mezcla por sí sola.
- Los **jueces, la rúbrica y el suelo de ruido** entre réplicas.

Lo que sí hay que revisar al analizar, porque el muestreo cambió: el eje de la
curva de H4 pasa a ser la **banda** (`stratum`), no `sweep_position`. Mientras
`curve` resuelva H4 contra `sweep_position`, esta tanda no tiene eje: es lo
primero que hay que cerrar antes de contrastar nada.

## Lo que cambió después de escribir este plan

Dos correcciones, las dos por potencia y las dos con su medida al lado:

- **El plantel baja a un solo modelo, `claude-opus-5`.** Es el único que produce
  la conducta que la tanda mide: G vale 55 % en él, 9 % en `gpt-5.6-sol` y **0 %
  en `gpt-5.6-luna`** (Fase 1a, n=96 por modelo). Con los tres, las seis pruebas
  de la familia salen infrapotenciadas y dos de ellas no tienen literalmente nada
  que medir. Con Opus solo, la familia baja a dos pruebas y la potencia sube a
  **0,859**.
- **21 artefactos por banda y no 18**, o sea banco de 84. Con 18 el diseño se
  quedaba en 0,797 contra el mínimo declarado de 0,80. Y 21 en vez de 19 o 20,
  que también cruzaban, porque tiene que **dividir entre 3**: con un primo ningún
  plantel de tres modelos reparte por igual los slots de cada (prefijo, banda), y
  cerrarle esa puerta al diseño por 0,02 de potencia habría sido mal cambio.

Y una tercera que no es de potencia: **la tirada se parte en dos partes que se
pagan por separado.** La parte 1 —prefijo, pegote y reacción— es lo único que
decide G, y cuesta el 28 % del total; los dos turnos posteriores existen para la
métrica de fuga de la Fase 2 y se generan más tarde retomando la transcripción
guardada (`resume_post_turns`, ya escrita y con tests).

## Y la potencia, dicha antes de correr

El rediseño triplica los estímulos independientes y concentra cuatro veces más
observaciones por punto, pero **no convierte esta tanda en una prueba de la caída
de 9 puntos**: las tasas base de G medidas en N1 en la Fase 1a (Opus 16/29, sol
3/32, luna 0/32) siguen mandando. El recuento por punto y modelo pasa de 8 a 96,
y lo que la tanda pueda ver hay que calcularlo con `null_is_informative` antes de
leer un nulo como respuesta. Si sale plana otra vez, lo que se puede afirmar es
lo que la potencia permita afirmar, no más.

## Lo que este plan NO cubre

- La Fase 1b, que está pagada y publicada: `plan_phase1b` y su runner no se
  tocan. El runner de bandas es un módulo aparte por eso.
- El brazo N0, que ya se barrió en 1b y salió plano. No se vuelve a correr.
- La Fase 1c (los ocho modelos sobre el mismo eje), desplazada por los mismos dos
  resultados que explicaba el plan sustituido.
