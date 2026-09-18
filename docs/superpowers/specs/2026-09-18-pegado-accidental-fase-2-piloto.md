# Piloto de la Fase 2: decir «ignóralo» es lo que contamina

Fecha: 2026-09-18
Spec: [`2026-09-17-pegado-accidental-fase-2-design.md`](2026-09-17-pegado-accidental-fase-2-design.md)
Plan: [`../plans/2026-09-17-pegado-accidental-fase-2.md`](../plans/2026-09-17-pegado-accidental-fase-2.md)
Fases anteriores: [1a](2026-09-15-pegado-accidental-fase-1a-resultados.md) · [1b](2026-09-15-pegado-accidental-fase-1b-resultados.md) · [1d](2026-09-17-pegado-accidental-fase-1d-resultados.md)
Datos: `runs/phase2/20260918T073151.jsonl` y `runs/phase2/control-20260918T123221.jsonl` del repo
[llm-wrong-paste](https://github.com/JaviMaligno/llm-wrong-paste)

## 1. El resultado

**Lo que contamina la conversación no es el pegote: es la orden de ignorarlo.**

| Brazo | n | fugan | tasa |
|---|---|---|---|
| **(a)** el usuario sigue como si nada | 20 | 1 | **5 %** |
| **(b)** «Ignóralo.» | 20 | 6 | **30 %** |
| **(c)** «Ignóralo, era para otro chat. Seguimos con {asunto}.» | 20 | 1 | **5 %** |
| **(d)** «Sí, hablemos de eso.» | 18 | 0 | **0 %** |

«Fuga» es que alguna entidad del artefacto pegado reaparezca en alguna de las
tres respuestas posteriores del modelo. Los cuatro brazos cuelgan de la **misma
conversación**: mismo prefijo, mismo artefacto, mismo pegote y **la misma
reacción al pegote**, ya pagada en la tanda 1d. Lo único que cambia entre ellos
es el texto de reparación.

Sobre las 18 bases con los cuatro brazos completos, **todas las discordancias
van en la misma dirección**:

| | contraste | diferencia | IC 95 % | p |
|---|---|---|---|---|
| H6 | (b) frente a (a) | **+33,3 pp** | [+11,6, +55,1] | 0,041 |
| H7 | (c) frente a (b) | −27,8 pp | [−48,5, −7,1] | 0,074 |
| H8 | (b) frente a (d) | **+33,3 pp** | [+11,6, +55,1] | 0,041 |

**Nada sobrevive a Holm** (los tres quedan en 0,124). Eso no es una decepción: la
potencia declarada del piloto era **0,107** y su caída mínima detectable, 34,8
puntos. Un piloto no tiene potencia; si la tuviera sería la tanda. Lo que el
piloto sí da son los números con los que se dimensiona la de verdad.

## 2. El control salió al revés de lo que temía

La variante (d) —«Sí, hablemos de eso»— estaba en el diseño como **control
decisivo**, con esta lógica: «Ignóralo» y «Sí, hablemos de eso» son
instrucciones opuestas sobre el mismo texto, así que si el modelo responde igual
a las dos, no está leyendo la intención, está reaccionando a la presencia del
texto.

No responde igual. Responde **al revés de lo que contaminaría más**: la
instrucción de *quedarse* con el pegote produce **cero** fuga, y la de
*descartarlo*, un 30 %. El modelo lee la intención perfectamente. El problema no
es que no entienda «ignóralo»; es que para ignorar algo hay que tenerlo en la
cabeza.

Y (c) lo confirma por el otro lado: la misma orden de ignorar, pero **con un
destino al que ir** —«seguimos con la factura de la luz»—, vuelve a bajar al 5 %
de la línea base. La diferencia entre (b) y (c) es exactamente el contexto, y son
27,8 puntos.

## 3. La tarea está muerta como instrumento

**100 % de acierto en los cuatro brazos, y 20/20 en el control sin pegote**, con
los ocho temas representados. Las ocho cuentas numéricas del hueco D13 son
demasiado fáciles para Opus, así que no pueden registrar degradación: un
instrumento que da el máximo en la condición contaminada y en la limpia no está
midiendo, está saturado.

Es un resultado del piloto, no un accidente, y es justo para lo que estaba la
puerta del §7 («que el acierto no esté pegado al techo ni al suelo en el brazo
(0)»). La decisión que abre: endurecer las tareas hasta que el brazo limpio falle
alguna, o quitar el acierto como variable y quedarse con la fuga —que es la
primaria y la que ha dado señal—.

## 4. Dos fallos de método que el piloto destapó

Los dos del mismo tipo, que es el que este proyecto lleva toda la serie pagando:
**un número bien formado que se lee como hallazgo cuando es un artefacto.**

### 4.1 La puerta de trivialidad concluía al revés

Estaba escrita mirando solo la tasa del brazo (a), con este razonamiento: «si (a)
fuga en el 2 %, no hay rango donde una reparación pueda mover nada». Da por hecho
que **la reparación baja la fuga**.

El piloto midió la dirección contraria: (a) fuga cero veces sobre las bases
completas y (b) un tercio. Con esa dirección, **un suelo en (a) no es el peor
caso sino el mejor**: es el fondo limpio contra el que el efecto se ve enorme. La
puerta medía bien y concluía al revés, y declaró no dimensionable exactamente el
hallazgo que el piloto existe para encontrar.

La condición honesta es la que la frase original quería decir: no hay rango
cuando **ningún** brazo se despega del extremo.

### 4.2 «La fórmula no aplica» no es «no se alcanza con ningún tamaño»

`paired_power` —la forma de Wald sobre la diferencia pareada— valida `0 < p_base`
y se niega cuando la tasa está pegada al suelo. Se niega **con razón**: una
potencia normal sobre una tasa de cero no describe ninguna tirada.

Pero el informe recogía esa negativa como *«no se alcanza la potencia declarada
con ningún tamaño»*, que es una frase distinta y mucho más fuerte: la primera
habla de la fórmula y la segunda del experimento. Publicada tal cual, habría
cerrado la fase con una conclusión que los datos no sostienen.

Para ese régimen se añadió `mcnemar_power_exact`, que enumera la binomial, no
tiene borde prohibido y dimensiona sobre la **discordancia** —los pares que
discrepan, que es lo que McNemar mira de verdad— en vez de sobre una diferencia
de tasas marginales. Con la discordancia observada recomienda 29 bases.

## 5. Cuánto costaría la tanda principal

El efecto medido es de ~33 puntos, no de los 9 que el proyecto declara
relevantes, así que la tanda sale **mucho más barata de lo proyectado**. Potencia
exacta de McNemar con el α de Holm sobre la familia de tres:

| escenario (discordancia a favor de (b) / de (a)) | n=40 | n=60 | n=80 | n=120 |
|---|---|---|---|---|
| **observado** (0,33 / 0,00) | 0,98 | 1,00 | 1,00 | 1,00 |
| prudente (0,20 / 0,02) | 0,37 | 0,71 | 0,88 | 0,98 |
| pesimista (0,12 / 0,03) | 0,04 | 0,15 | 0,27 | 0,49 |

El punto estimado dice 29 bases, pero sale de 6 discordantes sobre 18 y su
intervalo es ancho. **La recomendación es 120 bases** —480 conversaciones,
≈ 120 $—: cubre el escenario prudente con 0,98 y deja margen. Compárese con los
305 bases / 305 $ que proyectaba el supuesto de partida, y con los 200-400 $ que
el §11 del spec reservaba.

## 6. Qué se corrió, y qué salió mal

80 celdas = 20 bases × 4 brazos, más 20 de control. 240 llamadas al modelo
evaluado y 100 al usuario simulado; el prefijo, el pegote y la reacción **no se
volvieron a pagar**.

- **78 de 80 celdas usables** en los brazos pareados (1 `harness_error`, 1
  `timeout`); 5 `truncated`, que cuentan como conducta. **2 de 20 bases quedaron
  incompletas** y salen del análisis pareado, que es el motivo de que los
  contrastes vayan sobre 18.
- El control: 20/20, 17 `ok` y 3 `truncated`.
- **El aviso de credencial dijo que el token caducaba antes del final** —«se
  quedará sin credencial hacia la llamada 156 de 340»— y la tirada aguantó
  igual. Es la primera vez que ese aviso corre en una tanda de verdad, y funcionó
  como tenía que funcionar: informó sin parar nada.

### Una nota sobre el dato que faltaba

`sample_bases` equilibra la covariable `judge_duda`, y **ninguna tanda de este
repositorio escribe esa clave en sus filas**: los veredictos viven en su propio
fichero desde la Fase 0, para que rejuzgar no obligue a reescribir una tanda ya
pagada. Sobre el fichero real, la tirada habría reventado en la primera fila. Se
cerró con `attach_judge_duda`, que la toma de la G de la v2 —vale porque aquí
`judge_duda` es covariable de estratificación y no variable dependiente, y `duda`
y G coinciden en 27 de 28—. Cruzadas las 1.339 filas: **63,4 % dudaron**, y el
piloto salió con 20 bases clavadas 5/5/5/5 por banda y 10/10 en la covariable.

## 7. Lo que queda

- **Decidir qué se hace con la tarea**: endurecerla hasta que el control falle
  alguna, o quitarla y quedarse con la fuga.
- **La tanda principal**: 120 bases ≈ 120 $, con la potencia declarada por
  delante como en la 1d.
- **El reconocimiento tardío** (§5.3 del spec): el juicio de dos ejes sobre la
  respuesta al turno de reparación está escrito y sin correr. Contesta la
  pregunta que dejó abierta el artículo 1 —el modelo que no dudó al recibir el
  pegote, ¿duda cuando se lo dicen?—.
- **El contraste entre familias**, con puerta: el primario ha encontrado efecto,
  así que ahora sí tiene sentido preguntarse si un modelo que nunca duda
  distingue también (b) de (d).
