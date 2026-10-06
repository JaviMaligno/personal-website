# Fase 1b del pegado accidental: la curva sale plana, pero la tanda no podía verla

> **CORRECCIÓN, 2026-09-16.** Este documento decía que el eje de similaridad
> quedaba cerrado. **No se sostiene: la tanda estaba infrapotenciada y no se
> calculó la potencia antes de concluir.** Con 288 conversaciones repartidas en
> 12 posiciones y 3 modelos, la prueba primaria —por modelo, 8 observaciones por
> punto— tenía un **11 % de potencia** a alfa 0,05 y un **2 %** con el alfa de
> Holm, y su caída mínima detectable era de **34 a 43 puntos**. Agregando los
> tres modelos: 24 % de potencia y 20 puntos de caída mínima. La caída que el
> propio plan declaraba relevante, 9 puntos, **nunca estuvo al alcance**.
>
> Lo que sigue en pie y lo que no está marcado sección por sección. La frase
> «el eje de similaridad queda cerrado» del §7 se retira.

Fecha: 2026-09-15
Plan: [`../plans/2026-09-15-pegado-accidental-fase-1b.md`](../plans/2026-09-15-pegado-accidental-fase-1b.md)
Fase anterior: [`2026-09-15-pegado-accidental-fase-1a-resultados.md`](2026-09-15-pegado-accidental-fase-1a-resultados.md)
Datos: `runs/phase1b/20260915T114537.jsonl` del repo
[llm-wrong-paste](https://github.com/JaviMaligno/llm-wrong-paste)

> **Auditoría del autor hecha: 9 de 10 confirmadas.** La única corrección va de
> B a C, y no mueve ninguna tasa porque el juez —de quien salen las cifras— ya
> decía C.

## 1. El resultado

**Ninguna de las tres hipótesis preregistradas sobrevive a Holm**, y ninguna
mueve la tasa más que su propio suelo de ruido entre los extremos del barrido.

**Lo que eso NO significa:** que la conducta no dependa del parecido. Con la
potencia que tenía esta tanda (11 % por modelo, 24 % agregada), un efecto de 9
puntos habría salido no significativo casi siempre. Lo único que estos datos
descartan es un efecto **grande**: de unos 20 puntos hacia arriba en la curva
agregada, y de 34 o más por modelo.

| Hipótesis | Tasa global | Mejor `p` crudo | Tras Holm | Extremos (curva agregada) | Suelo |
|---|---|---|---|---|---|
| H1 menciona el salto | 45/275 = 16,4 % | 0,115 (Opus) | 0,92 | 4,3 % → 12,5 % = **8,2 pp** | 9 pp |
| H2 puente confabulado | **1/275 = 0,4 %** | 0,465 | 1,00 | 0 % → 0 % | 7 pp |
| H3 ejecuta en silencio | 175/275 = 63,6 % | 0,082 (Opus) | 0,74 | 91,3 % → 79,2 % = **12,1 pp** | 13 pp |

Y no es que el eje fuera estrecho: el barrido va de un coseno medio de **0,109
en la posición 0 a 0,453 en la 11**, monótono en las doce posiciones. Cuatro
veces más parecido entre un extremo y el otro, y la conducta no se entera.

El único movimiento con alguna forma es H3 en Opus (`z = −1,74`, `p` crudo
0,082): *ejecuta en silencio* **baja** con el parecido. Va en **dirección
contraria** a la hipótesis registrada, no sobrevive a la corrección, y se dice
aquí porque estaba escrito antes de mirar.

## 2. Lo que sí se movió: entre tandas, no a lo largo del eje

Los brazos N0 de las Fases 1a y 1b son la misma condición: mismo banco neutro,
mismos tres modelos, misma rúbrica, mismo juez. Y **el coseno medio es
prácticamente idéntico**: 0,259 y 0,261.

| | n | Menciona el salto |
|---|---|---|
| Fase 1a, brazo N0 | 91 | **25,3 %** |
| Fase 1b | 275 | **16,4 %** |

Nueve puntos de diferencia entre dos tandas de la misma condición. **Tampoco
esta diferencia alcanza significación**: `z = +1,89`, `p = 0,058`. Se reporta
porque es la única estimación que tenemos de cuánto se mueve una medida al
repetirla, y porque fija un listón prudente —no reclamar efectos menores que lo
que mueve volver a tirar— pero no está establecida. Sea por el muestreo de artefactos (1a
forzaba cobertura de géneros y usó 31 artefactos distintos; 1b barre posiciones
y usó 63) o por variación entre ejecuciones, la lectura es la misma y es el
resultado más útil de esta fase: **la varianza de estas medidas no está en el
parecido**. Cualquier efecto que queramos publicar tiene que ser mayor que esto.

## 3. La categoría E se desvanece — y esto SÍ está establecido

*Puente confabulado* pasó de 7 de 91 en el N0 de la Fase 1a a **1 de 275** aquí.
No es deriva del juez: se volvieron a juzgar hoy las 18 filas que en su día
dieron E y **16 siguen dando E**. Tampoco es sesgo de género: las mezclas de los
dos brazos coinciden y 1b usa el doble de artefactos distintos. Los dos jueces
lo ven igual —gpt-5.5 encontró una E, gemini ninguna—.

La diferencia entre tandas es grande y resiste la prueba: `z = +4,14`,
`p < 0,0001`. Es el único contraste de este documento que sobrevive a la
revisión de potencia, y sobrevive con holgura.

H2 no queda refutada: queda **sin nada que medir**. Con una observación en 275,
la hipótesis tal como la escribí no era contrastable en este diseño, y eso es un
fallo del diseño, no un resultado sobre los modelos.

## 4. El instrumento

| Medida | Fase 1a | **Fase 1b** |
|---|---|---|
| Acuerdo entre jueces (kappa) | 0,725 | **0,902** |
| Uso de la categoría Z | 0,2 % | **0 %** |
| Veredictos usables | 558/558 (tras reintentar) | **550/550 a la primera** |
| Acuerdo juez-humano, `gpt-5.5` | 0,819 | **0,896** |
| Acuerdo juez-humano, `gemini` | 0,623 | **0,768** |
| G, agente frente a `gpt-5.5` | 13/13 | **12/12** |
| Auditoría del autor | 19/20 | **9/10** |

`gemini` se comporta mucho mejor aquí que en 1a, y tiene explicación: su defecto
conocido es inflar G, y en el brazo neutro G apenas se disputa. Las tasas siguen
saliendo de `gpt-5.5`, que es el juez validado.

**El desacuerdo que queda es F frente a B, y la auditoría dice que se equivoca
el juez, no el humano.** El agente puso 8 F y el juez llamó B a tres de ellas.
Las tres entraron en la auditoría y el autor **confirmó las tres como F**. En
total, de las cinco discrepancias auditadas dio la razón al agente en cuatro y
al juez en una:

| | Aciertos sobre los 10 auditados |
|---|---|
| Etiquetador humano (agente) | **9/10** |
| Juez `gpt-5.5` | 6/10 |

Esas cifras **no son tasas generalizables**: la muestra se cargó a propósito con
cinco discrepancias, así que mide dónde falla cada uno, no cuánto. Lo que
establece es en qué dirección falla el juez, y es una sola: **infravalora F**,
confundiéndola con B cuando un pegote de tipo instrucción llega sin su texto.
El techo de ese error son **5 filas de 275** —las que el juez llama B y vienen
de un pegote `prompt`— y ninguna de las tres tasas se mueve, porque F y B están
las dos fuera de las tres.

Esto tiene una consecuencia para la tanda siguiente, y no es menor: **el juez no
es fiable para medir F**, que es justo la categoría que el banco arreglado del
§5 está diseñado para provocar. Cualquier análisis de «el pegote secuestra la
sesión» necesitará etiquetas humanas o un desempate de rúbrica más afilado antes
de fiarse de la clasificación automática.

Nota sobre el sentido del fallo: en la auditoría de la Fase 1a el autor había
corregido una F del agente a B, y aquí confirma tres en sentido contrario. No es
una contradicción suya sino la misma frontera mal escrita vista dos veces, que
es lo que el §5 acaba diagnosticando.

## 5. Limitación que esta fase destapó: el género `prompt` medía el sorteo

Al revisar las etiquetas, el autor observó que casi no aparecían casos de B
puros porque los pegotes de tipo instrucción **siempre llegan sin el texto al
que se refieren**. Medido, resulta peor de lo que parecía:

| Artefacto `prompt` | ¿Trae su referente? | Categorías obtenidas |
|---|---|---|
| `corrector-estilo` | no, pero la conversación previa sirve de material | **F ×4** |
| `repaso-examen` | autosuficiente | **F ×2** |
| `nombres-producto` | autosuficiente | **A ×4** |
| `resumen-actas` | no (necesita una transcripción) | **B ×4** |
| `traductor-tecnico` | no (necesita un texto) | **B ×1** |

**Cada artefacto produjo siempre la misma categoría, sin una sola excepción.**
Cero varianza dentro del artefacto. Para ese género, la categoría no estaba
midiendo la conducta del modelo: leía **qué artefacto había tocado en el
sorteo**. Y las 6 F del experimento salen todas de `prompt`; ningún otro género
produce ninguna.

La causa es que los cinco artefactos confundían dos ejes que deberían variar por
separado: **si el pegote trae el material sobre el que trabajar**, y **si asigna
un papel o encarga una tarea suelta**. El contraste entre `corrector-estilo` y
`resumen-actas` lo enseña: a los dos les falta el texto, pero al primero la
conversación anterior le sirve de sustituto —y ahí el pegote acaba secuestrando
la sesión, que es la conducta más llamativa que hemos visto— mientras que un
acta sin transcripción no tiene sobre qué ejecutarse.

**Qué le hace al resultado: nada.** Con F en 6 de 275, ninguna reasignación
posible mueve la curva plana:

| | Tasa de H3 |
|---|---|
| tal cual | 0,636 |
| si las F autosuficientes fueran A | 0,644 |
| si **todas** las F fueran A | 0,658 |

H1 no se mueve en absoluto, porque F y B están las dos fuera de *menciona el
salto*.

**Qué se ha hecho.** El banco N0 pasa de 5 a 8 artefactos `prompt`, que ahora
cubren la rejilla entera de los dos ejes —una casilla cada uno— y **la declaran
en el frontmatter**, con validación al cargar y tests que impiden que el reparto
vuelva a derivar. La casilla que faltaba y más falta hacía es `con_referente`:
en el banco original **ningún** prompt traía su texto, así que nunca se observó
qué hace un modelo con una instrucción completa.

Dos consecuencias que hay que declarar:

- **El banco N0 ya no es el de las Fases 0, 1a y 1b.** Pasa de 64 a 67
  artefactos. Cualquier tanda futura sobre N0 no comparte plantel con estas, y
  la `bank_sha` de la cabecera lo delata.
- **Los tres artefactos nuevos se escribieron conociendo los temas**, y los 64
  originales no. La independencia del §4.1 del spec original es más débil en
  ellos. Se escribieron sobre dominios ajenos a los ocho temas y no se ajustaron
  para caer en ninguna zona del eje, pero la garantía no es la misma.

## 6. Sobre D15: la colinealidad sigue viva

Dentro de los géneros con rango de coseno suficiente, `stacktrace` da una
pendiente aparente (`z = +2,13`, `p = 0,033`). **No sostiene nada**: son 11
pruebas sin corregir, y con cualquier corrección se cae. Los géneros estrechos
—`job_ad` 0,191 y `prompt` 0,141 de rango— quedan fuera del análisis por
declaración previa, no por conveniencia.

## 7. La puerta

El §7 del spec decía: *«si la curva sale plana, se dice tal cual y se decide si
1c aporta»*. La curva sale plana por las dos vías del criterio.

**Se dice tal cual, con la corrección de la cabecera:** con un pegote neutro no
se detectó relación entre el parecido y lo que el modelo hace, **y el diseño no
podía detectar nada menor que 20 puntos**. El eje no queda cerrado; queda sin
resolver por falta de potencia. Cerrarlo costaría del orden de **1.600
conversaciones** (≈225 $) para ver una caída de 9 puntos con un 80 % de
potencia.

**Recomendación para la tanda siguiente, que estaba escrita antes de ver los
datos y se mantiene:** no la Fase 1c —los ocho modelos sobre el mismo eje— sino
**N1 sobre el eje**. La pregunta del artículo es qué hace falta para que
pregunten, esa conducta vive en N1, y 1b acaba de demostrar que en N0 no hay
curva que dibujar. Otras 288 conversaciones, ≈40 $.

Con una condición añadida por el §2: cualquier efecto que esa tanda reporte
tiene que ser **mayor que los nueve puntos** que separan dos tandas de la misma
condición. Ese es ahora el listón.

## 8. Fallos del arnés en esta tanda

- **Una celda perdida por el filtro de contenido de Azure** (400,
  `ContentPolicyViolationError`) sobre un `DELETE` de SQL. El repo la clasifica
  como `refusal` por decisión deliberada y documentada, y no entra en ninguna
  tasa. Queda anotado que ese filtro solo afecta a los dos modelos que van por
  el gateway, no a Opus por Vertex: es una asimetría entre proveedores.
- **Una celda perdida por `ReadTimeout`**, transporte.
- **Once filas con algún turno cortado por el tope de tokens**, todas de Opus.
  El runner las descarta enteras aunque en 6 de las 11 el corte esté en un turno
  posterior y la reacción al pegote esté intacta y sea clasificable. Es
  conservador de más, y en la dirección correcta.
- **`leer-trazas.py` no conocía el esquema de los ficheros de veredictos** y
  declaraba que no guardaban la respuesta completa cuando la guardan las 550.
  Arreglado: es el mismo falso positivo que el propio script decía haber
  corregido ya para los ficheros de conversación.
