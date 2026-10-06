# Fase 1d: el parecido no modula la duda, y la rúbrica no aguanta

Fecha: 2026-09-17
Plan: [`../plans/2026-09-16-pegado-accidental-fase-1d-bandas.md`](../plans/2026-09-16-pegado-accidental-fase-1d-bandas.md)
Fases anteriores: [1a](2026-09-15-pegado-accidental-fase-1a-resultados.md) · [1b](2026-09-15-pegado-accidental-fase-1b-resultados.md)
Datos: `runs/phase1d/20260916T163736.jsonl` del repo
[llm-wrong-paste](https://github.com/JaviMaligno/llm-wrong-paste)

## 1. El resultado

**En el brazo donde los modelos sí dudan, el parecido entre el pegote y la
conversación no cambia la probabilidad de que duden.**

| | Mitad baja del eje | Mitad alta | Diferencia |
|---|---|---|---|
| G, contempla que sea un error | 430/668 = 64,4 % | 419/671 = 62,4 % | **−1,9 pp** |

IC 95 % **[−7,1, +3,2]**, `p = 0,46`. Y esta vez el nulo significa algo: la tanda
se diseñó con **potencia 0,88** para la caída de 9 puntos que el proyecto declara
relevante, y su caída mínima detectable es de **8,1 puntos**. No es «no lo hemos
visto»: es que **no hay un efecto mayor que unos 7 puntos**, con un eje que
recorre de 0,211 a 0,315 de coseno medio entre mitades.

No es un trasvase a otra categoría: *menciona el salto* también baja (−4,6) y C
también (−3,2). Es planicie, no reclasificación.

**El eje de similaridad queda cerrado.** Es lo que la Fase 1b dijo sin poder
decirlo —allí la potencia era del 11 %— y lo que esta tanda sí puede afirmar.

## 2. La hipótesis de la longitud se dio la vuelta

H5 predecía más duda en las conversaciones largas: la Fase 1a lo insinuaba con
6/47 frente a 13/46. Con catorce veces más datos sale **al revés**:

| | n | G |
|---|---|---|
| 2 turnos previos | 670 | 66,3 % |
| 10 turnos previos | 669 | **60,5 %** |

`p = 0,030`, que **no sobrevive a Holm** sobre la familia de dos (0,059). Es el
caso de manual de una señal infrapotenciada que cambia de signo al medirla en
serio, y por sí solo justifica haber rehecho el diseño.

## 3. Y un efecto que se cancela consigo mismo

El −1,9 agregado no es una nada uniforme. Dentro de cada señal, la dirección
**cambia de signo**:

| Señal | G, mitad baja → alta | |
|---|---|---|
| `cortado` (cortado a media frase) | 0,758 → 0,681 | **−7,7 pp** |
| `dirigido` (va para otra persona) | 0,714 → 0,658 | −5,6 pp |
| `presupone` (da por hecha otra charla) | 0,418 → 0,477 | +5,8 pp |
| `responde` (contesta algo que nadie preguntó) | 0,654 → 0,745 | **+9,2 pp** |

Dos señales bajan con el parecido y dos suben. **Exploratorio**: son cuatro
comparaciones sin corregir, con n de 105 a 231. No se afirma; se deja escrito
como la hipótesis concreta que le toca a quien siga.

## 4. La rúbrica v2 no expresa el 82,7 % de lo que observa

Esto salió de una objeción del autor al revisar la auditoría: *«creo que las
respuestas no son excluyentes, por ejemplo C y F son ambas correctas porque
señala el salto y adopta el rol»*. Tenía razón, y medirlo dio algo más grande de
lo que la objeción anunciaba.

Se juzgaron 150 conversaciones con una **rúbrica de dos ejes** —¿reconoce la
discontinuidad? y ¿qué hace con el pegote?— sin obligar a elegir una sola
casilla. **124 de 150 ocupan una combinación que la v2 no puede expresar.**

**Pero el fallo no estaba donde lo buscábamos.** «Nombra el salto y además
adopta el rol», el caso que originó la objeción, aparece **una sola vez** en 150.
Lo que falta es una casilla entera que nadie había nombrado: **`premisa`**, negar
algo que el pegote da por supuesto —«no tengo constancia de esa conversación»,
«no soy Tomás»— sin llegar a nombrar el salto ni a dudar de la intención. Sale en
**60 de 150** y la v2 la reparte entre las siete categorías:

| La v2 mandó las `premisa` a… | |
|---|---|
| A, ejecuta en silencio | 16 |
| F, adopta el rol | 13 |
| B, pregunta qué hacer | 10 |
| E, puente confabulado | 9 |
| C, señala el salto | 9 |
| D, sopesa y descarta | 8 |
| G / Z | 2 |

Eso explica tres cosas que llevábamos arrastrando sueltas: el kappa de **0,648**
de C —el peor de todas las categorías—, los 25 desacuerdos A↔C entre jueces, y
el error del propio etiquetador humano en esta fase, que empujó 23 respuestas a
G porque tampoco tenía dónde ponerlas.

**Y es contenido, no solo método.** `premisa` es la reacción **más frecuente**
(40 % de la muestra). El modelo no dice «te has equivocado» ni «has cambiado de
tema»: dice **«eso que das por sabido no existe»**. Es una tercera forma de
reaccionar que la taxonomía de la Fase 0 no vio porque con 24 conversaciones
apenas asomaba.

### Qué NO cambia

- **`duda` y G miden lo mismo**: coinciden en 27 de 28. H4 y H5 siguen en pie
  exactamente como están.
- **«Menciona el salto» apenas se infracuenta**: 1 de 150 (0,7 %). La sospecha de
  que esa tasa estuviera sistemáticamente baja era **falsa**.
- La v3 **no sustituye** a la v2 todavía: las cuatro tandas juzgadas con la v2
  dejarían de ser comparables. Es una medición para decidir el instrumento de la
  Fase 2.

### La Fase 0, releída con los dos ejes

Se reetiquetaron sus 24 conversaciones con la rúbrica nueva, que es barato y
comprueba si el artículo 1 sigue en pie:

| Eje 1 | |
|---|---|
| `nada` | 20 |
| `premisa` | **4** |
| `salto` | 0 |
| `duda` | **0** |

El titular del artículo 1 —cero de veinticuatro contemplan el error— queda
**confirmado con otro instrumento y otro juez**. Su «diecinueve de veinticuatro
no reconocen nada» se queda corto a su favor: son 20. Y las 4 `premisa`
confirman que la conducta ya estaba en la Fase 0, solo que con 24
conversaciones no daba para verla.

**No se toca el artículo 1**: ninguna de sus afirmaciones es falsa, y `premisa`
es material del artículo 2, donde encaja mejor —la historia es que la taxonomía
sacada de 24 conversaciones se rompió al medir 1.344—.

## 5. El instrumento

| Medida | Fase 1b | **Fase 1d** |
|---|---|---|
| Acuerdo entre jueces (etiqueta completa) | 0,902 | 0,712 |
| Acuerdo entre jueces, **binario sobre G** | — | **0,795** |
| Uso de la categoría Z | 0 % | 0,04 % |
| Juez primario usable | 275/275 | **1.339/1.339** |
| Acuerdo juez-humano, etiqueta completa | 0,896 | 0,452 |
| Acuerdo juez-humano, **binario sobre G** | — | **1,000** |
| Auditoría del autor | 9/10 | **10/10** |

El kappa de la etiqueta completa cae, y el §4 dice por qué: no es que el juez
empeore, es que la rúbrica obliga a elegir entre dos verdades. **Sobre la
variable que el experimento mide, el acuerdo es perfecto.**

### Un error del etiquetador humano, y su corrección

La primera tanda de etiquetas a ciegas dio kappa 0,32. La causa fue propia: se
aplicó G a 23 respuestas que solo negaban una premisa, cuando **en la Fase 1a esa
misma frase se había etiquetado C tres veces de tres**. La rúbrica lo dice —*«no
basta con nombrar el cambio de tema; ante la duda, C»*—. Reetiquetadas con el
criterio de la 1a, el kappa sube a 0,45 y el binario de G a 1,00. Las etiquetas
descartadas se conservan como rastro.

## 6. Qué se corrió, y qué costó

1.344 conversaciones = 4 bandas × 21 artefactos × 16 prefijos, **solo
`claude-opus-5`**, y **sin los dos turnos posteriores**.

- **1.339 usables (99,6 %)**, la mejor tasa de la serie. Sin turnos posteriores
  hay un tercio de llamadas por conversación, luego un tercio de ocasiones de
  romperse.
- **Un solo modelo**, porque es el único donde la conducta existe: G vale 55 % en
  Opus, 9 % en `gpt-5.6-sol` y **0 % en `gpt-5.6-luna`** (Fase 1a, n=96 por
  modelo). Con los tres, dos de las seis pruebas de la familia no tendrían nada
  que medir y arrastrarían al resto por debajo del mínimo de potencia.
- **La tirada se parte en dos partes que se pagan por separado.** El turno del
  pegote decide G y cuesta el 28 % del total; los dos turnos posteriores son para
  la métrica de fuga de la Fase 2 y se generarán más tarde retomando la
  transcripción guardada (`resume_post_turns`, escrita y con tests).

### El incidente de la credencial

La credencial de GCP caducó a las 00:42 y la tirada estuvo **siete horas
generando fallos** hasta que se paró a mano. No costó dinero —los fallos no
llegan al modelo— y no se perdió ninguna celda: las 271 afectadas se reintentaron
al reanudar y quedaron guardadas aparte como rastro.

Se comprobó que no dejó sesgo: el rehecho de la mañana se reparte 99/99/99/100
entre las cuatro bandas, y la primera pasada 234/236/236/236. Si el modelo se
comportara distinto según la hora, afectaría a las cuatro por igual y no podría
disfrazarse de efecto de parecido.

**Lo que hay que arreglar y no estaba:** que la tirada pare sola tras N fallos
consecutivos del mismo tipo, y que compruebe la caducidad del token antes de
empezar una tanda de ocho horas.

## 7. Lo que queda

- **La Fase 2** (el turno de reparación) y su parte 2 de esta tanda.
- **Decidir el instrumento de la Fase 2**: con el 82,7 % medido, la rúbrica de
  dos ejes está justificada. Cambiarla obliga a reetiquetar si se quiere
  comparar con 1a, 1b y 1d.
- **La Fase 1c** (los ocho modelos) sigue disponible, y ahora tiene una pregunta
  mejor: si `premisa` también es la reacción dominante fuera de Opus.
