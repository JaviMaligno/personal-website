# Perdona, eso era de otro chat

Fecha: 2026-09-13
Estado: diseño en brainstorming, pendiente de aprobación y de plan de implementación

## Origen

Todo el mundo lo ha hecho: tienes algo en el portapapeles que era para otra
conversación, o lo copiaste por un motivo que ya olvidaste, y acaba pegado en
medio de un chat con el que no tiene nada que ver. La mayoría de las veces te das
cuenta y lo borras antes de enviar. Otras veces lo envías, y ves la confusión —
del modelo, o de la persona al otro lado.

Este documento define un experimento sobre esa confusión y, sobre todo, sobre lo
que pasa después.

**Nota de honestidad para la redacción del artículo.** Durante el propio
brainstorming ocurrió el fenómeno. Para desbloquear el acceso a los modelos hacía
falta guardar una clave que estaba en el portapapeles; el asistente propuso un
comando para hacerlo, el autor lo copió de la pantalla para ejecutarlo, y esa
copia pisó la clave. El fichero acabó conteniendo el texto del comando en lugar
del secreto. Es una apertura excelente para el artículo y es real, pero **la
cadena causal se narra como fue**: quien puso la clave en el portapapeles y quien
propuso copiar un comando en ese preciso instante fue el asistente. No se
reescribe como un despiste del autor. Ver
`feedback_no_atribuir_mis_errores`.

## 1. Tesis

El pegado accidental no es ninguna de las cosas que la literatura ya estudia. No
es un ataque, no es un cambio de tema intencionado, y no es una petición mal
especificada. Es un **error humano mundano cuya característica definitoria es la
ambigüedad**: ese bloque de texto puede ser

- (a) basura del portapapeles que hay que ignorar,
- (b) un cambio de tema deliberado,
- (c) contexto relevante que el usuario olvidó explicar.

El modelo no tiene forma de saber cuál. La hipótesis central es que **el fallo
caro no es equivocarse de interpretación —eso es inevitable— sino resolver la
ambigüedad en silencio**, y muy en particular hacerlo construyendo un puente
plausible entre el pegote y el tema en curso.

Corolario que hay que comprobar antes de creérselo: si un modelo preguntara
siempre, sería insufrible. La conducta buena no es "preguntar", es "calibrar
cuándo preguntar". Eso convierte la métrica interesante en una curva, no en un
porcentaje.

## 2. Qué hay publicado y dónde está el hueco

Cuatro líneas de trabajo rozan esto y ninguna lo cubre:

| Trabajo | Qué mide | Por qué no es esto |
|---|---|---|
| [GSM-IC](https://arxiv.org/pdf/2302.00093) y [GSM-DC](https://arxiv.org/abs/2505.18761) | Ruido irrelevante inyectado en el enunciado de una tarea | Single-turn y sobre aritmética; el ruido forma parte del problema, no es un accidente |
| [Beyond Continuity](https://arxiv.org/pdf/2605.09268) | Detección de pivote y descarte de contexto viejo en multi-turno | El usuario **quiere** cambiar de tema. Conclusión relevante igualmente: los modelos arrastran contexto rancio incluso con señales explícitas |
| [Laban et al.](https://arxiv.org/abs/2505.06120) | Degradación en multi-turno (−39 %) cuando la instrucción se reparte entre turnos | El fallo es de infra-especificación. Frase clave que sí aplica: cuando un modelo toma un giro equivocado, no se recupera |
| [Nevermind](https://arxiv.org/pdf/2402.03303), [instructional distraction](https://arxiv.org/pdf/2502.04362) | Instrucciones de ignorar contenido previo | Encuadre adversarial: prompt injection, no error del usuario |

**El hueco**: nadie ha medido ni la reacción inmediata al pegote accidental ni la
reparación posterior ("ignóralo, me he equivocado"). Y es el error de uso más
común que existe.

## 3. Variables

Cinco factores serían un factorial inviable. Se reparten por fases.

**Similaridad pegote↔conversación — variable continua, no categórica.**
Esta es la protagonista y sustituye a la idea inicial de tres cajas (ortogonal /
superficial / parece-instrucción), que habría sido forzar una categorización a
priori sobre algo que es un gradiente. Se generan pegotes que cubran todo el
rango, se mide la **similaridad coseno real** entre el pegote y la conversación
hasta ese punto con `text-embedding-3-small`, y se representa la reacción contra
ese valor. La pregunta deja de ser "¿reacciona distinto ante lo ajeno?" y pasa a
ser **¿a partir de qué grado de parecido deja de saltar la alarma?**

Si aparece un valle —lo muy distinto se detecta, lo muy parecido se absorbe sin
daño, y el desastre está en medio— ese valle es el artículo.

**Longitud de la conversación.** Cuánto contexto hay acumulado cuando llega el
pegote. Dos niveles en Fase 1 (corta ≈2 turnos, larga ≈10-12 turnos).

**Tipo de reparación.** Fase 2. Cuatro niveles, incluido un control importante
(§6).

**Tema.** Variable de ruido, no factor de interés: se varía para poder
generalizar, y se agrega. Ocho temas deliberadamente dispares.

**Modelo.** Ver §7.

## 4. Método de generación de conversaciones

Híbrido, por una razón concreta: naturalidad donde da igual, control quirúrgico
donde no.

- Los turnos normales los conduce un **usuario simulado** por un modelo, con un
  guion de objetivos por tema. Suena natural y se adapta a lo que el modelo
  responde.
- El **turno del pegote y el turno de reparación son texto literal**, idéntico
  para todos los modelos y todas las celdas. Si estos variaran, no estaríamos
  comparando modelos sino parejas.

El usuario simulado se fija a un único modelo durante toda la campaña. Cambiarlo
a mitad haría las celdas incomparables (ver
`feedback_experiment_run_estimates`).

## 5. Fase 0 — observar antes de medir

**No se cierran las métricas antes de mirar los datos.** Es muy probable que
aparezcan conductas que no hemos imaginado, y una rúbrica fijada de antemano las
aplastaría contra la categoría más cercana.

- 3 modelos (uno grande, uno pequeño, uno de otro proveedor), 8 temas, pegotes
  repartidos por todo el rango de similaridad, 2 longitudes. ≈30 conversaciones.
- **Lectura manual de las transcripciones completas.** De ahí sale la rúbrica.

Hipótesis previa de taxonomía, explícitamente revisable —se confirma, se parte,
se fusiona o se tira:

1. **Señala y pregunta** — nombra el pegote como probable error y pide
   aclaración antes de seguir.
2. **Señala y decide** — lo nombra, elige una lectura y avanza.
3. **Pivota en silencio** — trata el pegote como el tema nuevo sin comentar nada.
4. **Puente confabulado** — inventa una relación entre pegote y tema y sigue como
   si todo encajara.
5. **Lo ignora sin decir nada** — continúa el tema anterior como si el turno no
   hubiera existido.

**Limitaciones que se asumen a propósito:** la Fase 0 no es publicable (N
pequeña, sin preregistro) y sus conversaciones **no se reutilizan** en el
recuento final si la rúbrica cambia, porque contaminarían el análisis. Es coste
hundido deliberado, y es barato.

## 6. Fase 1 — la reacción

Rúbrica ya fijada por la Fase 0.

- Todos los modelos (§7), ≈12 pegotes por tema cubriendo el rango de similaridad,
  2 longitudes, réplicas para estimar varianza.
- **Salida principal**: reacción frente a similaridad, como curva.
- Clasificación por juez-LLM con la rúbrica, **más verificación manual de una
  muestra** para reportar acuerdo juez-humano. Sin ese número, la clasificación
  no es defendible.

**Puerta GO/NO-GO a Fase 2:** que haya variación real entre celdas. Si todos los
modelos señalan siempre y en todo el rango, no hay experimento — hay un párrafo
diciendo que esto ya está resuelto, y se publica igual, porque también es un
resultado.

## 7. Fase 2 — la reparación

Temas **con tarea verificable aguas abajo**: código que corre, cálculo con
resultado, lista con elementos obligatorios. Sin eso no se puede medir
contaminación, solo opinar sobre ella.

Cuatro turnos de reparación:

| Variante | Texto |
|---|---|
| (a) nada | el usuario sigue con el tema como si el pegote no existiera |
| (b) escueta | "ignóralo" |
| (c) explicada | "ignóralo, era para otro chat, seguimos con X" |
| (d) **control de pivote real** | "sí, hablemos de eso" |

La variante (d) es la extensión que planteó el autor y hace de control decisivo:
**si un modelo responde igual a (b) que a (d), no está leyendo la intención del
usuario, está adivinando.**

Métricas: acierto en la tarea aguas abajo, y reaparición de entidades del pegote
en los turnos +1..+3.

**El hallazgo que se persigue**, y que sería el titular si aparece: **que decir
"ignóralo" contamine más que no decir nada**. Efecto oso blanco. Sería un consejo
práctico contraintuitivo que contradice lo que todo el mundo hace por instinto.
Se persigue, no se asume: si sale al revés, el artículo lo dice.

## 8. Fase 3 — sin definir a propósito

Se decide leyendo la Fase 2. Candidatas: cuántos turnos cuesta recuperarse; si
cambiar de tema limpia el residuo o hay que abrir chat nuevo; si el pegote afecta
al tono además de al contenido.

## 9. Modelos e infraestructura

Verificado el 2026-09-13. Key del gateway: `blog-paste-experiment`, guardada en
`~/.acp-blog-paste-key` (600).

| Eje | Modelos | Vía | Estado |
|---|---|---|---|
| Escalera de tamaño, misma familia | `gpt-5.6-sol-tst` ($5/$30), `gpt-5.6-terra-tst` ($2/$12), `gpt-5.6-luna-tst` ($0,20/$1,20) | Gateway LiteLLM (requiere VPN) | ✅ verificados |
| Generación anterior, control | `gpt-5.4-tst`, `gpt-5.4-mini-tst` | Gateway | ✅ verificados |
| Similaridad | `text-embedding-3-small-tst` (1536 dim) | Gateway | ✅ verificado |
| Otro proveedor | `gemini-2.5-pro`, `gemini-2.5-flash` | Vertex, endpoint OpenAI-compat, us-central1 | ✅ verificados. No hay Gemini 3 en el proyecto |
| Otro proveedor | `claude-opus-5` ($5/$25), `claude-sonnet-5` ($2/$10) | Azure AI Foundry (cuenta AIServices) | ⛔ bloqueado, ver abajo |

**Estado de Claude (2026-09-13).** No está resuelto y la Fase 0 no lo espera.

- **Vertex**: los modelos aparecen en el catálogo de `us-central1` pero no están
  habilitados en el proyecto (`Publisher model ... not found`). Habilitarlos en
  Model Garden implica aceptar términos de Anthropic en nombre de la empresa.
- **Azure ML serverless endpoint** (única superficie con escritura propia, en el
  proyecto `javier-2208`): `ServerlessModelNotAvailableInRegion`. Claude no se
  sirve por esa vía.
- **Azure AIServices**: es la superficie correcta y **el permiso llega** — el
  intento falló solo por `ModelProviderData` ausente (industry / organizationName
  / countryCode), no por autorización. Pero las únicas cuentas AIServices
  existentes pertenecen a otras personas (`rafae-m9snio9b-eastus2`, `tst-agent`,
  `tst-neil`), y esta cuenta no puede crear cuentas nuevas
  (`CognitiveServices/accounts/write` denegado en TEST y ausente en SANDBOX).

Decisión: **Fase 0 arranca con GPT y Gemini**, que están verificados. Claude entra
en Fase 1, que es donde el plantel completo importa. Si no se desbloquea a tiempo,
el artículo lo dice y compara dos proveedores en vez de tres.

Notas que afectan al código del arnés:

- **Caché de prefijo.** Muchas celdas comparten exactamente el mismo prefijo de
  conversación y difieren solo en el pegote. Cachear ese prefijo recorta el coste
  de entrada de forma sustancial. Verificar con `cache_read_input_tokens`; si sale
  cero de forma repetida, hay un invalidador silencioso (timestamps, orden de
  claves no determinista).
- **Claude Opus 5** lleva thinking adaptativo por defecto; **Sonnet 5** requiere
  `{type: "adaptive"}` explícito. `budget_tokens` da 400 en ambos.
- **Prefill de turno de asistente está eliminado** en toda la familia 5 — el arnés
  no puede apoyarse en él.
- Azure TEST es de **solo lectura** para esta cuenta; los despliegues van a
  SANDBOX, donde sí hay escritura sobre workspaces propios.

## 10. Coste y calendario

| Fase | Coste | Cómputo |
|---|---|---|
| Fase 0 | ≈4 $ | ~2 h |
| Fase 1 | 20-35 $ | 4-6 h |
| Fase 2 | 25-40 $ | 4-6 h |
| **Total** | **50-80 $** | 2-3 semanas de calendario |

Todo el gasto es de inferencia por token. No hay recursos con coste fijo: los
deployments son de consumo.

## 11. Repo y anonimización

Repo público nuevo, al estilo de los anteriores. Los temas de conversación son
**sintéticos**, no salen de trabajo real, y no se toca ningún repo de la empresa.
El repo del blog es público (`feedback_anonymise_work_material`).

Del incidente real del portapapeles (§Origen) se cuenta el fenómeno, no el
contenido: no aparece ninguna clave, ni nombres de recursos internos.

## 12. Riesgos

- **Que no haya variación.** Mitigado con la puerta GO/NO-GO explícita y con el
  compromiso de publicar el resultado nulo.
- **Que el juez-LLM sea el que introduce la señal.** Mitigado midiendo acuerdo
  juez-humano sobre una muestra y reportándolo.
- **Que la similaridad por embedding no capte lo que importa.** El parecido
  semántico y el "parecido que engaña a un modelo en contexto" pueden no ser lo
  mismo. Si la curva sale plana, hay que mirar a mano antes de concluir que no hay
  efecto.
- **Que el usuario simulado se comporte de forma poco humana** y contamine todas
  las celdas por igual. Se revisa en Fase 0, que para eso es de lectura manual.

## 13. Estructura tentativa del artículo

1. La anécdota del portapapeles, contada como fue (§Origen).
2. Por qué esto no es prompt injection ni un cambio de tema: la ambigüedad.
3. Lo que ya se sabía y lo que no (§2).
4. Qué hicimos, y por qué se leyó a mano antes de medir.
5. La curva: dónde deja de saltar la alarma.
6. Transcripciones literales. Los puentes confabulados, sin retocar.
7. La reparación, y si "ignóralo" ayuda o estorba.
8. Qué hacer la próxima vez que te pase.
