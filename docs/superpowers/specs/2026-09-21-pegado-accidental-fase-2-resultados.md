# Fase 2: decir «ignóralo» es lo que contamina

Fecha: 2026-09-21
Spec: [`2026-09-17-pegado-accidental-fase-2-design.md`](2026-09-17-pegado-accidental-fase-2-design.md)
Piloto: [`2026-09-18-pegado-accidental-fase-2-piloto.md`](2026-09-18-pegado-accidental-fase-2-piloto.md)
Fases anteriores: [1a](2026-09-15-pegado-accidental-fase-1a-resultados.md) · [1b](2026-09-15-pegado-accidental-fase-1b-resultados.md) · [1d](2026-09-17-pegado-accidental-fase-1d-resultados.md)
Datos: `runs/phase2/main-20260921.jsonl` del repo
[llm-wrong-paste](https://github.com/JaviMaligno/llm-wrong-paste)

## 1. El resultado

**Lo que deja residuo en la conversación no es el pegote: es la orden de
ignorarlo.**

| Brazo | fugan | tasa |
|---|---|---|
| **(a)** el usuario sigue como si nada | 4/120 | **3,3 %** |
| **(b)** «Ignóralo.» | 23/120 | **19,2 %** |
| **(c)** «Ignóralo, era para otro chat. Seguimos con {asunto}.» | 10/120 | **8,3 %** |
| **(d)** «Sí, hablemos de eso.» | 3/120 | **2,5 %** |

«Fuga» es que alguna entidad del artefacto pegado reaparezca en las respuestas
posteriores del modelo. Los cuatro brazos cuelgan de la **misma conversación**
—mismo prefijo, mismo artefacto, mismo pegote y la misma reacción al pegote, ya
pagada en la Fase 1d—, así que la comparación es pareada y lo único que cambia
entre ellos es el texto de reparación.

Sobre las **120 bases con los cuatro brazos completos**, las tres hipótesis
declaradas sobreviven a Holm:

| | contraste | diferencia | IC 95 % | p | Holm |
|---|---|---|---|---|---|
| **H6** | (b) frente a (a) | **+15,8 pp** | [+7,8, +23,8] | 0,00053 | **0,0011** |
| **H7** | (c) frente a (b) | **−10,8 pp** | [−17,3, −4,4] | 0,00361 | **0,0036** |
| **H8** | (b) frente a (d) | **+16,7 pp** | [+9,2, +24,1] | 0,00011 | **0,0003** |

## 2. El control salió al revés de lo que se temía

La variante (d) estaba en el diseño como **control decisivo**, con esta lógica:
«Ignóralo» y «Sí, hablemos de eso» son instrucciones opuestas sobre el mismo
texto, así que si el modelo respondiera igual a las dos, no estaría leyendo la
intención sino reaccionando a la presencia del texto.

No responde igual, y no en la dirección que preocupaba. La instrucción de
**quedarse** con el pegote produce la tasa más baja de las cuatro (2,5 %), y la
de **descartarlo**, la más alta (19,2 %). El modelo lee la intención
perfectamente. El problema es otro, y es más interesante: **para ignorar algo
hay que tenerlo en la cabeza.**

Y (c) lo confirma por el otro lado. La misma orden de ignorar, pero **con un
destino al que ir**, baja del 19,2 % al 8,3 %: −10,8 puntos, significativo tras
Holm. Lo que arregla la reparación no es pedir el olvido, es dar adónde mirar.

## 3. Dónde vive el residuo, y una salvedad que lo limita

**Toda la fuga está en el turno +1**, la respuesta al propio mensaje de
reparación:

| Brazo | +1 (reparación) | +2 (tarea) | +3 (sigue) |
|---|---|---|---|
| (a) | 3,3 % | 0,0 % | 0,8 % |
| **(b)** | **19,2 %** | 0,0 % | 0,0 % |
| (c) | 7,5 % | 0,0 % | 0,8 % |
| (d) | 2,5 % | 0,8 % | 0,8 % |

Eso hace el hallazgo **más pequeño en alcance y más nítido en mecanismo**: no es
contaminación que se arrastra por la conversación, es un eco inmediato. El
modelo repite las entidades del pegote **en el acto mismo de prometer que las
olvida**.

**La salvedad, y es seria.** El turno +2 es una pregunta numérica literal, con
una única respuesta correcta, idéntica en los cinco brazos. Es un turno que
domina lo que el modelo puede decir, así que un 0 % ahí **no se puede atribuir
limpiamente al decaimiento del residuo**: parte de ese cero es una propiedad del
diseño. La afirmación defendible es *«el residuo no sobrevive a una pregunta
concreta»*, no *«el residuo desaparece solo»*.

## 4. La tarea, cerrada como instrumento

**120/120, 120/120, 120/120 y 119/120.** El acierto en la tarea no registra nada,
como ya anunciaron las dos calibraciones del brazo limpio (24/24 con las cuentas
endurecidas, 20/20 con las originales).

Se intentó dos veces: primero cuentas de un solo paso, después cadenas de varios
pasos con una trampa clásica del dominio cada una —sumar el impuesto eléctrico y
el IVA como un 26 %, aplicar la comisión sobre los yenes en vez de sobre los
euros, olvidar el agua que ya lleva el prefermento—. Opus no cae en ninguna, ni
con la conversación contaminada.

**Es un resultado, no un hueco**: en este plantel, la contaminación por pegado
accidental no llega a una tarea aritmética verificable. Lo que queda abierto es
si llegaría a una tarea que dependa del **contexto** en vez del cálculo, y eso
rompería la condición de que el enunciado se baste solo (§5.2 del spec), así que
es rediseño, no ajuste.

## 5. Exploratorio

Sin corregir y fuera de la familia declarada; se reporta como lo que es.

- **(c) frente a (a): +5,0 pp, IC [−1,0, +11,0], p = 0,18.** Dar destino
  **mitiga** —eso sí está probado, es H7— pero no está demostrado que limpie del
  todo. La frase honesta es «lo reduce», no «lo arregla».
- **La banda de similaridad no ordena nada** (10,0 / 26,7 / 20,0 / 20,0 % en (b)
  por banda). Coherente con lo que la Fase 1d cerró para la duda: el parecido
  entre pegote y conversación tampoco modula el residuo.
- **La fuga de (b) casi se dobla cuando el modelo NO había dudado del pegote**:
  25,0 % frente a 13,3 %. El que no se olió nada es el que peor encaja que le
  digan que lo ignore. Es la hipótesis más concreta que deja esta fase.

## 6. Qué se corrió, y qué salió mal

480 celdas = 120 bases × 4 brazos. **464 `ok` y 16 `truncated`**, todas usables;
**cero pérdidas y las 120 bases completas**. Coste de la fase entera —piloto,
dos calibraciones del control y tanda principal— **≈ 145 $**.

**La tirada murió tres veces por falta de memoria**, y ninguna fue culpa suya:

- Las tres paradas las decidió el gestor de tareas del entorno por presión de
  memoria **del sistema**, no del proceso. La primera coincidió con una tanda de
  `jest` de otro repositorio que sostenía 15 workers y 3,8 GB en una máquina de
  16.
- Aun así el diagnóstico destapó un derroche real y se arregló: `main` cargaba
  las 1.339 filas de la tanda base **con sus transcripciones** —357 MB en dicts
  de Python para un fichero de 32 MB— y las mantenía vivas de principio a fin,
  cuando el plan solo referencia 120. Con la carga en dos pasadas son **51 MB**.
- No se perdió una sola celda en ninguna de las tres: todas quedaron escritas y
  la reanudación las reconoció.

## 7. Dos correcciones de método, del mismo tipo

Las dos son el modo de fallo que esta serie lleva pagando: **un número bien
formado que se lee como hallazgo cuando es un artefacto.**

- **La puerta de trivialidad concluía al revés.** Miraba solo la tasa del brazo
  (a), dando por hecho que la reparación *baja* la fuga. Con el efecto oso blanco
  la dirección se invierte, y un suelo en (a) pasa a ser el mejor caso —el fondo
  limpio contra el que el efecto se ve— y no el peor. La puerta medía bien y
  declaraba «no dimensionable» justo el hallazgo que el piloto existía para
  encontrar. Ahora es trivial cuando **ningún** brazo se despega del extremo.
- **«La fórmula no aplica» no es «no se alcanza con ningún tamaño».**
  `paired_power` se niega con `p_base = 0` y hace bien; el informe recogía esa
  negativa como una afirmación sobre el experimento. Se añadió
  `mcnemar_power_exact`, que enumera la binomial, no tiene borde prohibido y
  dimensiona sobre la discordancia.

## 8. Lo que queda

- **El reconocimiento tardío** (§5.3 del spec): el juicio de dos ejes sobre la
  respuesta al turno de reparación está escrito y **sin correr**. Contesta la
  pregunta que dejó abierta el artículo 1 —el modelo que no dudó al recibir el
  pegote, ¿duda cuando se lo dicen?—. Son llamadas al juez, no al modelo
  evaluado: barato.
- **El contraste entre familias**, que el diseño dejaba con puerta. El primario
  ha encontrado efecto, así que ahora sí tiene sentido preguntar si un modelo que
  nunca duda distingue también (b) de (d).
- **La tarea sensible al contexto**, si se quiere reabrir esa variable.
