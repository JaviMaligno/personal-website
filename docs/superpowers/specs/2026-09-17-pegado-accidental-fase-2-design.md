# Fase 2 del pegado accidental: el turno de reparación

Fecha: 2026-09-17
Estado: diseño aprobado en brainstorming, pendiente de plan de implementación
Spec de origen: [`2026-09-13-pegado-accidental-design.md`](2026-09-13-pegado-accidental-design.md) §7
Correcciones vigentes: [`2026-09-13-pegado-accidental-correcciones.md`](2026-09-13-pegado-accidental-correcciones.md)
Fases anteriores: [1 (rediseño)](2026-09-14-pegado-accidental-fase-1-design.md) · [1a](2026-09-15-pegado-accidental-fase-1a-resultados.md) · [1b](2026-09-15-pegado-accidental-fase-1b-resultados.md) · [1d](2026-09-17-pegado-accidental-fase-1d-resultados.md)
Datos de partida: `runs/phase1d/20260916T163736.jsonl` del repo
[llm-wrong-paste](https://github.com/JaviMaligno/llm-wrong-paste)

## 1. La pregunta

Las fases anteriores miden qué hace el modelo **cuando llega el pegote**. Esta
mide qué pasa **después de que el usuario intente arreglarlo**, que es la parte
que le ocurre a cualquiera que haya pegado algo donde no tocaba.

Tres preguntas, en orden de lo que se persigue:

1. **¿Decir «ignóralo» contamina más que no decir nada?** El efecto oso blanco.
   Es el titular si aparece, porque contradice lo que todo el mundo hace por
   instinto. Se persigue, no se asume: si sale al revés, se dice.
2. **¿El modelo lee la intención, o la adivina?** Si la respuesta a «ignóralo»
   y la respuesta a «sí, hablemos de eso» son la misma, no está leyendo nada.
3. **¿La contaminación llega a la tarea?** No al tono ni a la longitud: al
   resultado de una cuenta que tiene una sola respuesta correcta, y que no
   cambia por el pegote.

## 2. La decisión de diseño que reorganiza la fase

El spec original planteaba la Fase 2 como una tanda nueva. **No hace falta: los
cuatro brazos de reparación cuelgan de la misma conversación.**

La tanda 1d dejó **1.339 reacciones al pegote pagadas, guardadas y juzgadas**, y
`resume_post_turns` ya sabe retomar una transcripción guardada sin volver a
pagar el turno del pegote. Colgar los cuatro brazos de la misma base tiene tres
consecuencias, y las tres importan:

- **El estímulo es idéntico.** Prefijo, artefacto, pegote y reacción son los
  mismos en los cuatro brazos. Lo único que cambia es el texto de reparación,
  que es exactamente el factor. En una tanda nueva, cada brazo habría tenido su
  propia reacción al pegote y la comparación habría mezclado «cambió la
  reparación» con «le tocó otra reacción».
- **La comparación es pareada.** La variabilidad entre conversaciones —que en
  esta serie es enorme: la G de Opus va del 41,8 % al 75,8 % según la señal del
  artefacto— sale del término de error en vez de inflarlo.
- **El turno del pegote se paga una vez en vez de cuatro.** Es el 28 % del coste
  de una conversación completa.

**Y absorbe la parte 2 de la tanda 1d.** El brazo (a) —el usuario sigue como si
el pegote no existiera— *es* la parte 2 tal como estaba diseñada. No se compra
por separado: se compra como uno de los cuatro brazos, y además con el resto del
diseño alrededor.

### Lo que el arnés ya tenía preparado

No es una idea nueva reaprovechando algo a la fuerza; el arnés se escribió
contando con esto desde la Fase 0:

| Pieza | Dónde | Qué reserva |
|---|---|---|
| `USER_HIDDEN_TAGS = ("paste", "repair")` | `simulated_user.py:47` | la etiqueta `repair` ya está reservada |
| `user_visible_history` | `conversation.py:85` | oculta al usuario simulado el pegote **y la reparación**, para que el brazo (a) no se convierta en un brazo de reparación por la puerta de atrás |
| `continue_after_paste` | `conversation.py:281` | se documenta a sí misma como «la variante (a) del spec §7» |
| `entity_hits` (D8) | `artifacts.py:154` | el recuento de entidades del artefacto |
| `artifact_entities` | en cada fila del JSONL | las entidades de cada pegote, ya en disco |
| `task` / `expected` / `verifier` | `topics.py`, hueco D13 | los tres campos por tema, declarados y a `None` |

Lo único que no existe es el turno literal de reparación y las ocho tareas
verificables. Eso es lo que hay que escribir.

## 3. Los cinco brazos

Cuatro pareados sobre la misma base, más un control que no puede estarlo.

| Brazo | Turno posterior 1 | Qué es |
|---|---|---|
| **(a) nada** | el usuario simulado sigue con el tema | el usuario no repara; ya implementado |
| **(b) escueta** | «Ignóralo.» | la reparación que todo el mundo escribe |
| **(c) explicada** | «Ignóralo, era para otro chat. Seguimos con {asunto}.» | la reparación con contexto |
| **(d) pivote real** | «Sí, hablemos de eso.» | **el control decisivo** |
| **(0) sin pegote** | — (no hay pegote) | la línea base del acierto en la tarea |

El texto de (b), (c) y (d) es **literal e idéntico en todas las celdas**, con la
única variación del `{asunto}` en (c) —«la factura de la luz», «el viaje a
Japón»—, que vive en `repair.ASUNTO` y no en el fichero del tema, porque es
material del turno de reparación y no de la conversación. Las tres cadenas están
clavadas por igualdad exacta en los tests: son texto que el modelo LEE, y
retocarlas después de empezar a correr haría incomparables las celdas de antes y
las de después. Si el texto variara, no estaríamos comparando reparaciones sino
parejas (§4 del spec original).

**Por qué (d) es el control decisivo.** «Ignóralo» y «Sí, hablemos de eso» son
instrucciones **opuestas** sobre el mismo texto: una dice «esto no va aquí» y la
otra «esto sí va aquí». Un modelo que lea la intención tiene que responder
distinto. Si (b) y (d) producen la misma fuga y el mismo acierto, la conclusión
no es que la reparación no funcione: es que el modelo no está procesando la
instrucción del usuario, está reaccionando a la presencia del texto.

**Por qué (0) no puede ser pareado.** Los otros cuatro brazos cuelgan de una
conversación que ya tiene el pegote dentro; (0) es una conversación **sin**
pegote, así que no comparte base con ninguno. Corre como tanda aparte sobre los
mismos 16 prefijos y los mismos 8 temas. Sin (0) no hay forma de decir que el
pegote degrade la tarea: solo se podría decir que unos brazos aciertan más que
otros, que es una frase mucho más pequeña.

## 4. La forma de la conversación

Tras la reacción al pegote, **tres turnos del modelo evaluado en todos los
brazos**, para que las posiciones sean comparables:

| Turno | Quién escribe el mensaje de usuario | Brazo (a) | Brazos (b)(c)(d) |
|---|---|---|---|
| +1 | usuario simulado / literal | sigue con el tema | el texto de reparación (`tag: repair`) |
| +2 | **literal, uno por tema** | la tarea | la tarea |
| +3 | usuario simulado | sigue con el tema | sigue con el tema |

El turno de la tarea va en **+2 en los cinco brazos**, incluido (0). Ponerlo en
la misma posición no es estética: la fuga decae con los turnos, y comparar el
acierto de un brazo en +2 con el de otro en +3 mediría la distancia al pegote y
no la reparación.

En el brazo (a) el turno +1 lo genera el usuario simulado sobre
`user_visible_history`, que le oculta el pegote y la reacción. Es lo que ya hace
`continue_after_paste` y el motivo por el que lo hace está escrito en su
docstring.

## 5. Las tres variables dependientes

### 5.1 Fuga de entidades — la primaria

Cuántas de las entidades del artefacto reaparecen en las respuestas del modelo
evaluado en +1, +2 y +3. Se cuenta con `entity_hits` (D8) sobre
`artifact_entities`, que ya viaja en cada fila.

- **Binaria por conversación** para las pruebas: ¿aparece alguna entidad del
  pegote en alguno de los tres turnos posteriores? Es la variable de las
  hipótesis declaradas.
- **Continua por turno** para la curva: cuántas entidades y en qué turno. Es lo
  que dice si la reparación limpia o solo retrasa.

La respuesta del modelo **al propio turno de reparación** (+1) cuenta. Es
deliberado y es donde el efecto oso blanco tendría que verse primero: «claro,
olvido lo de la factura de Iberdrola de Marta» repite las tres entidades
mientras promete olvidarlas.

### 5.2 Acierto en la tarea

El hueco D13, que lleva reservado desde la Fase 0 y sigue a `None` en los ocho
temas. Cada tema recibe **una tarea numérica con una sola respuesta correcta**,
escrita a mano y con el resultado calculado a mano **antes de correr nada**:

| Tema | Tarea (texto literal del turno +2) | Esperado |
|---|---|---|
| `carrera-10k` | «Una cosa rápida antes de seguir: si quiero terminar los 10 km en 55 minutos exactos, ¿cuántos segundos por kilómetro son?» | **330** s/km |
| `elegir-camara` | «Una cuenta antes de seguir: la cámara que miro es APS-C con factor de recorte 1,5. Si le pongo un objetivo de 35 mm, ¿cuál es la focal equivalente en full frame?» | **52,5** mm |
| `elegir-colegio` | «Antes de seguir, ayúdame con una cuenta: puntúo cada colegio sobre 10 en tres criterios, con pesos 45 % distancia, 35 % idiomas y 20 % comedor. El colegio B saca 6 en distancia, 9 en idiomas y 8 en comedor. ¿Cuál es su nota ponderada?» | **7,45** |
| `factura-luz` | «Antes de seguir, échame una cuenta: tengo 4,6 kW de potencia contratada a 0,08 € por kW y día, el periodo son 30 días, y he consumido 210 kWh a 0,14 € el kWh. ¿Cuánto suman el término de potencia y el de energía, sin impuestos?» | **40,44** € |
| `hacer-pan` | «Antes de seguir, una cuenta: si uso 500 g de harina y quiero la masa al 70 % de hidratación, ¿cuánta agua le pongo?» | **350** g |
| `huerto-balcon` | «Antes de seguir, una cuenta: la jardinera mide 80 cm de largo, 20 de ancho y 18 de alto. ¿Cuántos litros de sustrato necesito para llenarla?» | **28,8** litros |
| `mudanza` | «Antes de seguir, una cuenta: tengo 18 cajas de 60 litros cada una y la furgoneta declara 6 m³ de capacidad de carga. ¿Cuántos litros me sobran?» | **4.920** litros |
| `viaje-japon` | «Antes de seguir, una cuenta: voy 12 días y calculo 9.500 yenes diarios de gastos, más un JR Pass de 50.000 yenes. A 160 yenes por euro, ¿cuánto es en euros?» | **1.025** € |

Las ocho cumplen tres condiciones que hay que comprobar en los tests, no dar por
hechas:

1. **La respuesta correcta no depende del pegote.** Esa es toda la gracia:
   cualquier caída de acierto es atribuible a la contaminación.
2. **El resultado no coincide con ningún valor intermedio** del cálculo natural.
   En `factura-luz` los intermedios son 11,04 y 29,40, y el resultado 40,44: un
   verificador que busque «40,44» no puede acertar por accidente al ver un paso
   intermedio.
3. **El resultado es un número distintivo y de una sola grafía.** Dos tareas se
   reescribieron por incumplir esto: `huerto-balcon` pregunta litros de sustrato
   (28,8) y no cuántas lechugas caben (5), porque un «5» se encuentra en
   cualquier parte de cualquier respuesta; y `carrera-10k` pregunta segundos por
   kilómetro (330) y no el ritmo (5:30), porque el ritmo se escribe «5:30»,
   «5'30» o «5 min 30 s» y el verificador tendría que aceptar un conjunto de
   grafías, que es como un verificador se convierte en un juicio. El 330 tampoco
   colisiona con los 3.300 segundos de la carrera entera, y no porque nada
   busque subcadenas: el verificador **extrae cada número entero y lo compara**
   (ver abajo), así que «3.300» se lee como 3300 y no contiene un 330 que
   encontrar. Hay un test con esa respuesta exacta.

**El verificador extrae y normaliza los números de la respuesta**, y comprueba
si alguno es exactamente el esperado. **No monta un regex del número esperado
para buscarlo en el texto**, que es el enfoque obvio y está descartado con datos:
probado sobre once respuestas de muestra falla en tres, porque construir la
expresión de «4.920» que además acepte «4920» y no acepte «49.200» es un
problema más difícil que el que resuelve.

La trampa concreta que obliga a normalizar con cuidado es española: **«28.800»
son veintiocho mil ochocientos y «28.8» son veintiocho coma ocho**, y el tema
`huerto-balcon` tiene los dos números en la misma respuesta —el volumen en cm³ y
el resultado en litros—. La regla que los separa: un separador seguido de
**exactamente tres dígitos**, con más grupos de tres delante o detrás, es de
millares; cualquier otro es decimal. Con esa regla, los quince casos de prueba
—incluidos «3.300 segundos en total, es decir 330 s/km» y «28.800 cm³, o sea
28,8 litros»— salen bien. Sin número reconocible = fallo.

**Su dureza es constante entre brazos, y ese es el argumento.** Un verificador
estricto baja el acierto de los cinco brazos por igual, así que no puede fabricar
una diferencia entre (a) y (b). Lo que sí podría es aplastar la escala si el
acierto se va al suelo en todos: el piloto lo comprueba antes de comprar la
tanda.

### 5.3 Reconocimiento tardío

El eje 1 de la rúbrica de dos ejes, aplicado a la respuesta al turno de
reparación (+1). Mide algo que el spec original no pedía y que la Fase 1d hace
obvio: **¿el modelo que no dudó al recibir el pegote duda cuando el usuario le
dice «ignóralo»?**

Es la pregunta natural del artículo 1. Allí ningún modelo contempló el error por
su cuenta; aquí se le da la pista y se mira si la recoge. Y la casilla `premisa`
—la reacción más frecuente de la Fase 1d, 40 %— permite ver la tercera salida:
que ni dude ni nombre el salto, sino que siga negando premisas del pegote.

## 6. El instrumento: rúbrica de dos ejes (v3)

**Decidido: la Fase 2 se mide con la v3.** La justificación está medida en la
Fase 1d §4: la v2 no puede expresar el 82,7 % de lo que observa, y la casilla que
falta —`premisa`— es la reacción más frecuente.

Lo que cuesta y cómo se paga:

- **Comparabilidad.** Las tandas 0, 1a, 1b y 1d están juzgadas con la v2. La
  mitigación no es retórica: `duda` y G coinciden en 27 de 28, así que **la tasa
  que el experimento persigue sigue siendo la misma serie**. Lo que deja de ser
  comparable celda a celda es el reparto completo de categorías, que en esta fase
  no es la variable.
- **La base se rejuzga con la v3.** Las 1.339 reacciones de partida se vuelven a
  juzgar con la rúbrica nueva —son llamadas al juez, no al modelo evaluado, y
  por tanto baratas— para que el turno del pegote y el turno de reparación se
  midan con el mismo instrumento. Sin eso, la comparación «no dudó al pegote,
  ¿duda al «ignóralo»?» cruzaría dos rúbricas.
- **Hasta entonces, la covariable del muestreo sale de la G de la v2**, que sí
  está en disco para las 1.339 (`attach_judge_duda`). Vale porque ahí
  `judge_duda` **no es una variable dependiente**: es una covariable de
  estratificación y lo único que decide es qué bases entran en la muestra. Con
  `duda` y G coincidiendo en 27 de 28, el desacuerdo residual puede
  desequilibrar un poco el reparto y no puede sesgar ningún resultado. Una fila
  `ok` sin veredicto usable **revienta**: darle un valor por defecto mandaría en
  silencio todas las filas sin juzgar al mismo estrato.
- **Los dos jueces siguen siendo los mismos** (`gpt-5.5-tst` y
  `gemini-2.5-flash`, §9 de la Fase 1), y se sigue reportando acuerdo entre
  jueces, acuerdo juez-humano sobre una muestra etiquetada a ciegas, y la
  auditoría del autor sobre 20 de ellas.

## 7. El piloto, porque la potencia no se puede declarar todavía

**No hay ninguna tasa base de fuga medida.** Nunca se ha contado en ninguna fase.
Sin ella, cualquier tamaño de muestra que escriba aquí sería inventado: en el
peor caso (p = 0,5) detectar la caída de 9 puntos que el proyecto declara
relevante pide ~480 bases por brazo, y en un caso favorable (p = 0,15) pide ~200.

Así que la fase empieza por un **piloto**, y el piloto es una puerta:

**Piloto:** 20 bases × 4 brazos = **80 conversaciones**, más 20 del brazo (0).
Las 20 bases se toman de la tanda 1d estratificadas por banda de similaridad
(5 por banda) y por si la reacción al pegote fue `duda` o no.

Lo que tiene que salir del piloto, y que es lo único que decide el tamaño de la
tanda de verdad:

1. **La tasa de fuga del brazo (a)**, que es la tasa base.
2. **La correlación entre brazos de la misma base**, que es lo que convierte el
   diseño pareado en potencia y no en un adorno.
3. **Que el acierto en la tarea no esté pegado al techo ni al suelo** en el brazo
   (0). Si el brazo sin pegote ya falla la tarea, la tarea está mal escrita y hay
   que arreglarla antes de comprar nada.
4. **Que la fuga no sea trivial**: si (a) fuga en el 2 % o en el 98 %, no hay
   rango donde una reparación pueda mover nada y el diseño necesita otra
   variable.

> **PUERTA.** Con esos cuatro números se calcula la potencia del contraste
> primario igual que en la 1d, con `MIN_POWER = 0,80` sobre `DECLARED_DROP =
> 0,09`. Si el tamaño necesario se dispara por encima del presupuesto, se declara
> y se decide: reducir brazos, quitar el turno +3, o publicar el piloto como lo
> que es. Lo que no se hace es correr la tanda sin la potencia declarada por
> delante — es el error que costó la Fase 1b.

### Las hipótesis, declaradas antes de correr

Dos familias para Holm-Bonferroni, como en las fases anteriores:

**Familia 1 — fuga (la primaria):**

| | Contraste | Dirección |
|---|---|---|
| H6 | (b) escueta vs (a) nada | bidireccional; **se persigue (b) > (a)**, el oso blanco |
| H7 | (c) explicada vs (b) escueta | bidireccional |
| H8 | (b) escueta vs (d) pivote | bidireccional; **el no rechazo es el resultado**, y por eso se declara su potencia |

**Familia 2 — acierto en la tarea:**

| | Contraste |
|---|---|
| H9 | (a) nada vs (0) sin pegote |
| H10 | (b) vs (a) |
| H11 | (c) vs (a) |
| H12 | (d) vs (a) |

H8 es la única del proyecto donde **no rechazar es la conclusión**, así que su
potencia se declara antes y el resultado se escribe como equivalencia con su
intervalo, no como «no significativo». Es lo que la Fase 1d hizo con el eje de
similaridad y lo que la 1b no pudo hacer.

## 8. Lo que entra gratis

La base ya lleva dos variables que aquí no cuestan una llamada:

- **La banda de similaridad.** El eje se cerró para la duda —la Fase 1d lo dejó
  en −1,9 pp con potencia 0,88—, pero **la fuga es otra variable**. Que el
  parecido no cambie si el modelo lo *nota* no dice nada sobre si cambia cuánto
  lo *arrastra*. Estratificando las bases por banda, la pregunta se contesta sin
  pagar de más. No es una hipótesis declarada: es exploratoria y se reporta como
  tal.
- **El reconocimiento en el turno del pegote.** ¿Repara mejor el modelo que ya lo
  había notado? También exploratorio.

Las dos son covariables de la base, no factores del diseño, y por eso el muestreo
las estratifica pero las pruebas declaradas no las incluyen.

## 9. Lo que NO se hace

- **No se corre una tanda nueva para el primario.** Cuelga de la 1d, por el §2.
- **No se compra la parte 2 de la 1d por separado.** Es el brazo (a).
- **No se reetiquetan las tandas 1a, 1b y 1d con la v3.** Solo se rejuzgan con la
  v3 las 1.339 reacciones que sirven de base a esta fase, y los resultados
  publicados de aquellas fases siguen siendo los de la v2.
- **No entra el plantel completo.** La base es N1 y solo `claude-opus-5`, que es
  lo que hay pagado. El contraste entre familias va aparte y con puerta (§10).
- **No se mide tono ni longitud.** Se midió la tarea, que es verificable.

## 10. Riesgos y limitaciones

- **La base es N1 y de un solo modelo.** Para la fuga probablemente vale —no es
  la conducta que solo Opus tiene—, pero **el control (d) es justo donde las
  familias deberían diferir**: la Fase 1a midió G al 55 % en Opus, 9 % en
  `gpt-5.6-sol` y 0 % en `gpt-5.6-luna`. Un modelo que nunca duda podría también
  ser el que no distingue (b) de (d). **Mitigación con puerta:** si el primario
  encuentra efecto, una tanda pequeña de réplica sobre `gpt-5.6-sol` con el mismo
  diseño; si no lo encuentra, no hay nada que replicar.
- **El turno de la tarea es una intervención.** Es un mensaje literal idéntico en
  todos los brazos, y es posible que por sí solo reencauce la conversación y
  tape parte de la contaminación. Es una limitación declarada, no arreglada: sin
  una tarea verificable no hay forma de medir contaminación, solo de opinar sobre
  ella (§7 del spec original). Lo que sí se puede decir es que afecta a los cinco
  brazos por igual.
- **Los verificadores los escribe el agente.** Es el sitio donde un sesgo mío se
  convertiría en resultado. Van al repo antes de correr, con sus tests, con el
  resultado esperado calculado a mano, y el autor revisa las ocho tareas — son
  ocho cuentas de bachillerato, es media hora y es lo que las hace defendibles.
- **`premisa` puede dominar también la respuesta a la reparación.** Si el modelo
  contesta al «ignóralo» negando premisas del pegote, el eje 1 lo registrará,
  pero la fuga de entidades subirá por un motivo que no es el oso blanco. Se
  reporta el cruce eje-1 × fuga para poder separarlo.
- **Colinealidad registro↔similaridad**, heredada de la D15: sigue viva y sigue
  siendo una limitación declarada.

## 11. Coste y calendario

Medido sobre el consumo real de la tanda 1d (entrada media 4.404 tokens, salida
media 1.166) y sobre la tarifa verificada: `claude-opus-5` a $5/$25 por millón en
Vertex, usuario simulado `gpt-5.6-terra-tst` a $2/$12 por el gateway.

Una conversación de esta fase son 3 llamadas al modelo evaluado con contexto
creciente, más 1 o 2 al usuario simulado: **≈ 0,25 $**, de los cuales ~0,20 $ son
de GCP y ~0,05 $ del gateway.

| | Conversaciones | Coste | Reloj |
|---|---|---|---|
| **Piloto** (20 bases × 4 brazos + 20 de (0)) | 100 | **≈ 25 $** | ≈ 1,5 h |
| Rejuicio de la base con la v3 | — (1.339 llamadas al juez) | ≈ 5 $ | ≈ 1 h |
| **Tanda principal**, según lo que diga el piloto | 800 – 1.600 | **200 – 400 $** | 15 – 30 h |
| Juicio de la tanda principal (v3, dos jueces) | — | 15 – 30 $ | ≈ 3 h |

**Hay que decirlo sin adornos: la tabla del spec original ponía 25-40 $ para toda
la Fase 2, y esto es un orden de magnitud más.** La razón es la misma que en la
Fase 1: aquel número salió de un diseño que medía una sola cantidad sin haber
medido su tasa base. Aquí el piloto existe precisamente para que el número grande
esté justificado antes de gastarlo, y la puerta del §7 existe para poder no
gastarlo.

**Palancas declaradas** si el piloto pide más de lo que hay: quitar el turno +3
(ahorra ~30 % y cuesta la curva de persistencia), bajar de cuatro brazos a tres
quitando (c) —que es la variante menos informativa de las cuatro—, o publicar el
piloto como resultado exploratorio.

## 12. Estructura tentativa del artículo 3

1. Los artículos 1 y 2 dicen que el modelo no se plantea que te hayas equivocado,
   y qué hace falta para que lo haga. Falta la parte que le pasa a todo el mundo:
   **ya lo pegaste, ahora arréglalo**.
2. Las cuatro maneras de arreglarlo, y por qué «sí, hablemos de eso» es la que
   decide si el modelo te está leyendo.
3. La cuenta que no cambia: ocho tareas con una sola respuesta correcta.
4. Si «ignóralo» contamina más que callarse: el oso blanco, con el consejo
   práctico al revés de lo que hace todo el mundo.
   Si no: por qué callarse no es mejor, y qué sí lo es.
5. El control: si (b) y (d) dan lo mismo, la reparación no es una instrucción, es
   un ruido más.
6. El reconocimiento tardío: el modelo que no dudó, ¿duda cuando se lo dices?
