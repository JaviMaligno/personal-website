# Fase 1a del pegado accidental: resultados y decisión de la puerta

Fecha: 2026-09-15
Spec: [`2026-09-14-pegado-accidental-fase-1-design.md`](2026-09-14-pegado-accidental-fase-1-design.md)
Plan: [`../plans/2026-09-14-pegado-accidental-fase-1a.md`](../plans/2026-09-14-pegado-accidental-fase-1a.md)
Datos: `runs/phase1a/20260914T135814.jsonl` del repo
[llm-wrong-paste](https://github.com/JaviMaligno/llm-wrong-paste)

## 1. Decisión de la puerta: SIGUE

N1 mueve *contempla que sea un error* **+13,8 puntos** sobre N0, muy por encima del
umbral declarado del 5 %. Los intervalos de confianza del 95 % no se solapan. Hay
algo que medir, así que 1b y 1c siguen sobre la mesa.

## 2. Qué se corrió

288 conversaciones = 3 niveles × 8 temas × 2 longitudes × 2 réplicas × 3 modelos,
en 3 h 15 min. **279 usables (96,9 %)**; las 9 pérdidas —8 `truncated` y 1
`empty`— son **todas de `claude-opus-5`**, que agota los 4.000 tokens de
respuesta. Cruzan los tres niveles y tres temas, así que no sesgan la comparación
que decide la puerta; solo le quitan potencia a Opus, que se queda en 87 de 96.

Consumo: 2,10 M tokens en el brazo por gateway y 1,03 M en el de Anthropic, de
los cuales 774 k se leyeron de caché de prefijo. **El gasto en euros no se ha
medido**: la estimación previa eran ≈40 $ y no se ha contrastado contra la
factura.

## 3. Las dos tasas

Juez `gpt-5.5-tst`, el que sobrevive a la validación del §5. IC del 95 % normal.

| Nivel | n | Menciona el salto | IC 95 % | **Contempla que sea un error** | IC 95 % |
|---|---|---|---|---|---|
| N0 neutro | 91 | 25,3 % | [16,3 · 34,2] | 6,6 % | [1,5 · 11,7] |
| **N1 señal** | 93 | 26,9 % | [17,9 · 35,9] | **20,4 %** | [12,2 · 28,6] |
| N2 contradicción | 95 | 18,9 % | [11,1 · 26,8] | **0,0 %** | [0 · 0] |

**Solo se mueve la segunda tasa.** «Menciona el salto» está plana entre N0 y N1
(+1,6 puntos): la señal intrínseca no hace que nombren más el cambio de tema,
hace que duden de la intención. Son dos cosas distintas y el experimento las
separa.

## 4. El hallazgo que contradice el diseño: N2 es el suelo, no el techo

N2 se diseñó como **techo**, el pegote más detectable, para localizar el máximo
de la curva. Ha salido **por debajo del banco neutro**: cero de 95.

El reparto de categorías dice por qué:

| Nivel | A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|---|
| N0 | 50 | 18 | 8 | 2 | 7 | — | 6 |
| N1 | 49 | 17 | 6 | — | — | 2 | **19** |
| N2 | **77** | — | 5 | 2 | 11 | — | **0** |

En N2 se dispara *ejecuta en silencio*: 77 de 95. Un pegote que contradice lo que
el usuario acaba de decir **se lee como una corrección del usuario**, no como un
accidente. El modelo acepta el dato nuevo, rehace el consejo y no registra el
choque. La contradicción no es una señal de error: es una señal de *cambio de
opinión*, y es exactamente lo que un asistente está entrenado para acatar.

Esto reordena la pregunta del artículo. Lo que hace dudar no es que el pegote sea
**incompatible** con la conversación, sino que sea **ajeno** a ella: que lleve
dentro las marcas de haber sido escrito para otro sitio.

## 5. El instrumento, antes que los números

Tres niveles de verificación, en orden:

| Medida | Resultado |
|---|---|
| Acuerdo entre jueces | bruto 0,835 · **kappa 0,725** |
| Uso de la categoría Z | **0,2 %** (1 de 558), umbral de alarma 5 % |
| Acuerdo juez↔humano, `gpt-5.5` | bruto 0,858 · **kappa 0,819** |
| Acuerdo juez↔humano, `gemini-2.5-flash` | bruto 0,700 · kappa 0,623 |
| Auditoría del autor sobre 20 | **19 de 20 confirmadas** |

**`gemini-2.5-flash` no sirve para medir G.** Sobre las 120 etiquetadas a ciegas
llama G 30 veces donde el etiquetado humano dice 13: **17 falsos positivos y
ningún falso negativo**, y en 16 de esos 17 `gpt-5.5` coincide con el humano.
Cuenta como «duda de la intención» lo que es pedir aclaración de la tarea (B) o
nombrar el salto sin más (C). De los 7 casos en disputa que entraron en la
auditoría del autor, **los 7 se resolvieron contra gemini**.

Por eso las tasas del §3 salen de `gpt-5.5`. Con gemini, N1 daría 34,4 % en vez
de 20,4 %: el signo y la decisión de la puerta no cambian, la magnitud sí.

La única corrección del autor fue una frontera B/F —una respuesta que pide el
material que el prompt pegado necesita— y **no mueve ninguna de las dos tasas**,
porque B y F están las dos fuera de `MENTIONS_JUMP`. El riesgo del §10 («que el
etiquetado del agente arrastre el sesgo de quien escribió la rúbrica») queda
acotado, no descartado: 20 casos son 20 casos.

## 6. El reparto por familia aguanta

G por modelo y nivel, con el juez validado:

| Modelo | N0 | N1 | N2 | Total |
|---|---|---|---|---|
| `claude-opus-5` | 3/27 | **16/29** | 0/31 | 19/87 |
| `gpt-5.6-sol` | 3/32 | 3/32 | 0/32 | 6/96 |
| `gpt-5.6-luna` | 0/32 | 0/32 | 0/32 | **0/96** |

`gpt-5.6-luna` no contempla el error **ni una vez en 96 conversaciones**. La
hipótesis de la Fase 0 —que se apoyaba en 8 conversaciones por modelo y no
sostenía nada— sobrevive con potencia. Y el efecto de N1 es casi enteramente de
Opus: sin él, la tasa de N1 bajaría al entorno de la de N0.

**Esto condiciona la Fase 1c.** El contraste por familia ya no es una hipótesis
que 1c deba probar: es el resultado principal. Lo que 1c añadiría es si el resto
del plantel se parece a Opus o a los GPT.

## 7. Dos efectos secundarios, con n pequeña

**Por señal, dentro de N1** (n ≈ 22-26 por señal):

| Señal | G |
|---|---|
| responde a una pregunta que nadie hizo | **8/22 = 36 %** |
| va dirigido a alguien por su nombre | 4/22 = 18 % |
| cortado a media frase | 4/26 = 15 % |
| presupone una conversación anterior | 3/23 = 13 % |

**Por longitud**, y en direcciones opuestas:

| | 2 turnos previos | 10 turnos previos |
|---|---|---|
| N0 | 5/46 | 1/45 |
| N1 | 6/47 | **13/46** |

Con una señal dentro del pegote, la conversación larga **duplica** la duda: hay
más contexto contra el que el pegote desentona. Sin señal, la conversación larga
la reduce. Ninguna de las dos diferencias está potenciada para sostenerse sola;
son hipótesis para 1b, no hallazgos.

## 8. Qué cambia en los planes siguientes

- **1b (similaridad)** sigue vigente y gana interés: la pregunta ya no es si la
  tasa sube con el parecido, sino si la mezcla de la taxonomía se mueve.
- **1c (plantel completo)** cambia de motivo. Ya no prueba el contraste por
  familia, lo extiende.
- **El §5 del spec de la Fase 1 queda corregido por los datos**: N2 no es el
  techo. El documento se deja como estaba y esta corrección vive aquí, porque
  reescribir la predicción después de ver el resultado borraría justo lo que hace
  informativo al hallazgo.

## 9. Fallos del arnés en esta tanda

Ninguno afecta a los datos; todos costaron dinero o tiempo.

- **`JUDGE_MAX_TOKENS` a 1.200.** Los dos jueces razonan y el razonamiento gasta
  del mismo presupuesto (medido: 724 tokens de razonamiento para 69 de texto).
  `gemini` dejaba el JSON cortado a media cita en el **43 %** de sus veredictos.
  Subido a 4.000, y un JSON cortado pasa a llamarse `truncated` en vez de
  `bad_json`, que mandaba a arreglar el prompt en vez del presupuesto.
- **La reanudación del juez pedía los dos jueces por fila** y descartaba el que ya
  estaba: 242 llamadas para 121 veredictos. Ahora salta por juez.
