---
title: "Deja que el loop itere: reiniciar solo compensa si sabes qué tirar"
description: "Karpathy sugirió dejar que un agente atascado reinicie en vez de insistir. Construí un loop con tests visibles y lo medí: iterar sobre el feedback gana a los reinicios limpios a igual cómputo — y darle al agente un botón de reinicio con alcance revela que saber *qué* descartar es lo que separa a los tiers."
pubDate: 2026-07-17
tags: ["IA", "Agentes", "Evaluación"]
lang: es
translationKey: restart-vs-iterate
heroImage: "/blog/restart-vs-iterate.png"
---

> **Un estudio completo: 3 seeds × 3 políticas × 2 tiers de modelo sobre una porción de 29 features, con el harness de evaluación auditado antes de fiarse de un solo número.** El mismo protocolo de rigor que [el artículo de coordinación](https://www.javieraguilar.ai/es/blog/coding-agents-structure) — este experimento es su secuela directa.

Hay una pieza de folclore de agentes, cristalizada por Andrej Karpathy como *"let the loop restart"* (deja que el loop reinicie): cuando el intento de un agente de código va mal, no sigas parcheando el barco que se hunde — tira el intento y deja que empiece de cero. Tiene atractivo intuitivo. Cualquiera que haya visto a un agente cavar más hondo en un enfoque roto lo ha sentido.

¿Pero es verdad? En [mi experimento anterior](https://www.javieraguilar.ai/es/blog/coding-agents-structure) ni siquiera pude probarlo: los agentes de CooperBench hacen una sola pasada y nunca ven los resultados de sus tests, así que la señal de fallo que motivaría un reinicio jamás les llega. Miné las 1.806 trayectorias y encontré exactamente **cero** reinicios voluntarios — un artefacto del montaje, no un hallazgo. Medir reiniciar-vs-iterar de verdad necesitaba otro harness.

Así que lo construí.

## El montaje

Sobre el mismo stack derivado de CooperBench (29 tareas de una-sola-feature en 5 repositorios reales, dos tiers de modelo: un `gpt-5.4-mini` de gama media y un `gpt-5.4` más fuerte), añadí la pieza que faltaba: un **loop con evaluador visible**. El agente intenta la feature; el harness corre la suite de tests de esa feature y le muestra los resultados (conteos de pasa/falla más el output de los tests que fallan); y viene la siguiente ronda — hasta **K = 4 rondas**, parando antes si lo consigue.

Todas las políticas reciben el mismo K, los mismos topes de cómputo por ronda y el *mismo formato de feedback* — así que la única variable es qué pasa **entre** rondas:

- **ITERATE** — el loop clásico: código y contexto se acumulan; el agente parchea su propio trabajo con los resultados de los tests delante.
- **RESTART-FRESH** — la lectura literal de Karpathy: cada ronda arranca de un checkout limpio con contexto fresco. Sin memoria de intentos previos. Esto es deliberadamente muestreo best-of-K — esa *es* la afirmación, probada a igual cómputo, sin pedir disculpas.
- **RESTART-INFORMED** — checkout limpio, pero el contexto lleva un resumen breve de qué falló, construido por el harness a partir de artefactos (nunca escrito por el propio agente que falló). Esto separa el mecanismo: si informed gana a fresh, la *lección* ayuda; si fresh iguala a informed, el problema era el contexto contaminado.
- **AGENT-DECIDES** — el interesante: un loop estilo iterate donde el agente tiene un **botón de reinicio explícito con alcance** — `restart(fichero | directorio | todo-mi-trabajo)` — presentado como una opción legítima y sin coste. Él elige cuándo descartar y *cuánto*.

## Resultados

Tres seeds por celda de cabecera; la tabla muestra media [mín–máx] sobre 29 features.

| política | mini | gpt-5.4 |
|---|---|---|
| iterate (parchear con feedback) | 74% [72–76] | 86% [79–90] |
| restart-fresh (best-of-K limpio) | 63% [62–66] | 69% [69–69] |
| restart-informed (1 seed) | 69% | 79% |
| **agent-decides (reinicio con alcance)** | **75% [69–79]** | **91% [90–93]** |

Cuatro hallazgos, en orden de cuánto aguantan la estadística:

1. **Iterar sobre el feedback gana a reiniciar en limpio — de forma contundente en el modelo fuerte.** McNemar pareado sobre los tres seeds: gpt-5.4 iterate gana 17–2 a restart-fresh (p=0.001); mini apunta igual (15–6, p=0.078). A igual cómputo, K intentos refinando una trayectoria con feedback de tests superan a K intentos limpios independientes. El *let-the-loop-restart* literal — reiniciar como remuestreo ciego — **pierde** en este benchmark.

2. **Lo que duele no es el contexto contaminado — es perder el árbol de trabajo.** Restart-informed (código limpio, lección retenida) queda *entre* fresh e iterate en ambos tiers. La lección construida por el harness recupera parte del hueco, pero nada supera a conservar el código de verdad. A este horizonte (K=4), el "contexto envenenado" que preocupa a la intuición del reinicio simplemente no era la restricción vinculante.

3. **Darle la decisión al agente es la mejor celda de la tabla — y nunca estorba.** Agent-decides corona ambos tiers (91% en gpt-5.4, su máximo; 75% en mini). Contra restart-fresh en el tier fuerte gana **19–0** (p<0.001). Contra iterate puro la ventaja no es significativa (8–4, p=0.39) — así que léelo con prudencia: el grueso del valor está en iterar; la *opción* de reiniciar añade un plus plausible-pero-no-probado y no cuesta nada.

4. **El marcador de capacidad es el *estilo* del reinicio — aunque la historia causal es más sutil que "bisturí vs. bola de demolición".** Este es el hallazgo que me quedaría si solo pudiera quedarme uno, y es el que un lector afilado (`alex_spinov`, en los comentarios) atacó con más fuerza — con razón. El patrón bruto es real: en los tres seeds el modelo fuerte reinició **poco y con bisturí** (7 reinicios, 5 a nivel de fichero, **3 de 4** feature-runs reiniciadas resueltas), mientras que el débil reinició **mucho y a lo bruto** (34 reinicios, 23 de ellos `scope=all`, solo **1 de 14** feature-runs reiniciadas resueltas). Pero un reinicio es *autoseleccionado* — el agente lo usa justo donde ya va perdiendo —, así que las features reiniciadas son un subconjunto difícil por construcción. La prueba honesta es el contrafactual: las *mismas* features y seeds bajo `iterate` puro, que el harness ya corrió. Separa los tiers con nitidez:
   - **Tier débil — la bola de demolición es el síntoma, no la causa.** Esas mismas 14 features se resuelven solo **2/14 con iterate**, muy lejos de la base del 74%. Los reinicios amplios no destruyeron trabajo ganable; el agente arrasó todo *porque* la feature ya estaba perdida. El reinicio es casi neutro aquí (1/14 vs 2/14), no destructivo.
   - **Tier fuerte — el bisturí sí rescata.** Esas mismas 4 features se resuelven **0/4 con iterate**; el reinicio acotado convirtió tres en victorias. Contra el baseline correcto — el subconjunto emparejado, no la tasa global del 91% — eso es una ganancia causal real, aunque con n=4 es direccional (p exacta ≈0.25), no significativa.

   Así que la afirmación afinada: saber *qué* tirar es la metacognición, y es el reinicio acotado del tier fuerte el que de verdad compensa — mientras que el reinicio amplio del tier débil es la *firma* de un agente que ya ha perdido, no el mecanismo de su derrota.

## Bajo el capó

**El piloto se pagó solo.** Antes de gastar en la matriz completa, un piloto de 6 features cazó **tres bugs reales de composición** en mi propio harness — patches que el evaluador aceptaba pero que la siguiente ronda no podía re-aplicar, y (el gordo) rondas de iterate puntuadas contra un árbol al que le faltaba el trabajo de las rondas anteriores. Este último es la misma clase de bug que produjo un 0% falso en el artículo anterior. Los tres se arreglaron con test-primero y los datos contaminados del piloto se descartaron y re-corrieron. Si construyes loops de agentes: **la composición de estado entre rondas es donde están enterrados los cadáveres.**

**Una auditoría adversarial custodió el gasto.** Como en el artículo anterior, un agente revisor independiente auditó el loop antes de la Fase 1 — veredicto FAIL, dos problemas de integridad (un tope de coste que podía hacer desaparecer features de los denominadores en silencio, y rondas con error de harness disfrazadas de "sin progreso"), ambos arreglados y re-auditados a PASS antes de cualquier run de cabecera. Cada ronda persiste su patch, sus resultados de tests y el árbol compuesto exacto que se evaluó, así que todas las curvas son re-analizables offline sin re-gastar.

**Igual cómputo, con honestidad.** Restart-fresh es muestreo best-of-K y se trató como tal — mismas rondas, mismos topes. Su modo de fallo se ve en las curvas por ronda: cuando fresh falla, quema las cuatro rondas sin converger (su coste por feature en los fallos corrió 5–10× el de los éxitos). El modo de fallo de iterate es la meseta — rondas sin ganar un solo test — que ocurrió, pero menos de lo que la intuición del reinicio predice (aproximadamente 1 de cada 5 runs no resueltos en el tier fuerte).

**Coste.** El experimento entero — piloto, tres políticas × dos tiers × tres seeds, la fase de decisión y todo el debugging — salió por unos **\$102** de gasto de API. Las diferencias de coste-por-resolución entre políticas fueron pequeñas comparadas con las diferencias de pass rate; nada en el dinero cambia el ranking.

## Lo que dice y lo que no

**No** dice que Karpathy se equivoque en general. Dice: *en el régimen que medí* — tareas de tamaño feature sobre código existente, cuatro rondas, tests visibles — el reinicio-como-remuestreo pierde contra la iteración, y el reinicio que *sí* compensa es acotado, informado y raro. Regímenes donde esperaría que la balanza se incline hacia reiniciar: tareas greenfield (donde "empezar de cero" significa de verdad una página en blanco y los primeros intentos anclan fuerte), horizontes mucho más largos (donde el contexto sí se pudre), y modelos por debajo de cierto suelo de competencia (donde cada intento es una tirada de dados de todas formas — aunque nota que incluso nuestro tier débil iteró mejor de lo que reinició).

El eco con el [artículo de coordinación](https://www.javieraguilar.ai/es/blog/coding-agents-structure) es difícil de ignorar. Allí, la palanca que funcionaba era estructural (un agente dueño de la integración) y el modelo fuerte era el que sabía explotar una regla. Aquí, la palanca que funciona es *conservar tu trabajo y leer el feedback*, y el modelo fuerte es el que sabe manejar el bisturí. Los dos experimentos aterrizan en la misma forma: **la capacidad no solo sube los pass rates — cambia qué proceso ayuda.** Dale a un agente débil una herramienta potente (un protocolo de coordinación, un botón de reinicio) y manotea con ella; dale un problema más pequeño o un loop más ceñido y mejora. Dale a un agente fuerte la misma herramienta y la usa como esperabas.

Si corres agentes de código en la práctica, la versión accionable son tres líneas:

- Por defecto, **itera con tests visibles** — no reinicies por defecto, y no escondas el feedback.
- Si añades la opción de reiniciar, espera que **solo tus modelos más fuertes la usen bien** — en nuestros datos, los reverts acotados del tier fuerte rescataron features que la iteración pura perdía (3/4 vs 0/4 sobre las mismas features), mientras que los reinicios del tier débil solo marcaban trabajo ya hundido. No cuentes con que *forzar* un alcance estrecho suba el pass rate de un modelo más débil.
- Vigila el *estilo* de los descartes de tu agente. Reinicios frecuentes y amplios no son decisión; en nuestros datos son la firma de un agente ya perdido — la iteración falla también esas mismas features.

## Limitaciones y qué sigue

- **29 features, 5 repos, K=4.** Tres seeds en las celdas de cabecera (informed tiene uno). Aplican los caveats de N pequeño de siempre; el resultado con dientes estadísticos de verdad es iterate-gana-a-fresh (p=0.001), la ventaja de agent-decides sobre iterate es solo direccional.
- **No es greenfield.** Reinicios acotados a una feature sobre código existente limitan cuánto puede significar "empezar de cero". El techo de la herramienta de alcance es bajo aquí por construcción.
- **Un solo framework de agente, una sola familia de modelos** (tiers de GPT-5.4 en Azure) — la replicación cross-familia es el siguiente paso obvio.
- El prompt de decisión presenta reiniciar como legítimo y sin coste; otro encuadre podría mover las tasas de reinicio (aunque no debería mover la *asimetría de payoff* entre tiers, que es el hallazgo central).

Todo es reproducible: el harness del loop, las cuatro políticas, las métricas y los artefactos por ronda son públicos en [github.com/JaviMaligno/CooperBench](https://github.com/JaviMaligno/CooperBench/tree/experiment/restart-loop) (rama `experiment/restart-loop`).

---

*Motivado por la observación "let the loop restart" de Andrej Karpathy. Secuela de [Agentes de código y trabajo en equipo: ¿habilidades sociales o estructura?](https://www.javieraguilar.ai/es/blog/coding-agents-structure)*
