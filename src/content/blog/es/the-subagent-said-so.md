---
title: "Lo dijo el subagente"
description: "Cuando mi agente delega, suele dar por bueno el informe del subagente aunque este supiera menos que él. Lo medí en tres familias de modelos. Con el dato que lo contradice a la vista, casi nunca se lo cree. Lo que hace es no comprobarlo: el mismo texto se verifica si lo escribió un compañero, y no si lo escribió su propio subagente."
pubDate: 2026-10-21
tags: ["Agentes", "Multiagente", "Verificación", "Claude"]
lang: es
translationKey: the-subagent-said-so
heroImage: "/blog/the-subagent-said-so.png"
linkedinImage: "/blog/the-subagent-said-so-adopted.png"
repoUrl: "https://github.com/JaviMaligno/personal-website/tree/main/experiments/subagent-trust"
---

<style>
.sst-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.sst-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.sst-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
</style>

Hay un patrón que llevo tiempo viendo en mis sesiones con Claude Code. El agente manda a un subagente a investigar algo. El subagente vuelve con un informe limpio y seguro. El agente me traslada la conclusión como propia, aunque contradiga algo que él ya sabía.

El subagente siempre parte con menos contexto. No ve mis ficheros de memoria, ni las decisiones que tomamos hace una hora, ni lo que el agente principal ha ido averiguando. Que rellene esos huecos con lo más plausible es lo razonable. Lo raro es el otro lado: el agente que *sí* tenía el contexto lee el informe y no lo pone en duda.

Quería saber si esto es cosa del harness, del modelo o algo más general. Así que monté un experimento para aislarlo.

## La hipótesis: el informe entra por la puerta equivocada

Mi primera sospecha era el canal. En Claude Code, el informe de un subagente llega como `tool_result`, el mismo tipo de mensaje que la salida de un `cat` o de un test que falla. Los modelos están entrenados para tratar ese canal como una observación del mundo, no como la opinión de un compañero que sabía menos. Si ese es el mecanismo, el subagente no es el problema: el mismo texto leído de un fichero se creería igual de fácil.

Eso se puede comprobar, porque se puede fijar el informe y cambiar solo la puerta por la que entra.

<figure class="sst-fig">
<svg viewBox="0 0 600 250" role="img" aria-label="El mismo informe, escrito de antemano e idéntico palabra por palabra, llega al agente principal por tres canales: como resultado de su propio subagente, como un fichero que dejó un compañero o pegado en un mensaje del usuario. El agente principal puede comprobarlo o no antes de responder.">
  <rect x="20" y="95" width="130" height="60" rx="8" fill="#232334" stroke="#f59e0b"/>
  <text x="85" y="120" text-anchor="middle" fill="#fbbf24" font-size="13" font-weight="600">Informe fijo</text>
  <text x="85" y="139" text-anchor="middle" fill="#94a3b8" font-size="11">texto idéntico</text>
  <path d="M150 115 L240 50" stroke="#64748b" stroke-width="1.5" fill="none"/>
  <path d="M150 125 L240 125" stroke="#64748b" stroke-width="1.5" fill="none"/>
  <path d="M150 135 L240 200" stroke="#64748b" stroke-width="1.5" fill="none"/>
  <rect x="240" y="28" width="150" height="44" rx="8" fill="#232334" stroke="#f59e0b"/>
  <text x="315" y="48" text-anchor="middle" fill="#e2e8f0" font-size="12">su propio subagente</text>
  <text x="315" y="63" text-anchor="middle" fill="#94a3b8" font-size="10" font-family="ui-monospace,'JetBrains Mono',monospace">Agent → tool_result</text>
  <rect x="240" y="103" width="150" height="44" rx="8" fill="#232334" stroke="#2dd4bf"/>
  <text x="315" y="123" text-anchor="middle" fill="#e2e8f0" font-size="12">notas de un compañero</text>
  <text x="315" y="138" text-anchor="middle" fill="#94a3b8" font-size="10" font-family="ui-monospace,'JetBrains Mono',monospace">Read → tool_result</text>
  <rect x="240" y="178" width="150" height="44" rx="8" fill="#232334" stroke="#64748b"/>
  <text x="315" y="198" text-anchor="middle" fill="#e2e8f0" font-size="12">mensaje del usuario</text>
  <text x="315" y="213" text-anchor="middle" fill="#94a3b8" font-size="10" font-family="ui-monospace,'JetBrains Mono',monospace">"un compañero vio…"</text>
  <path d="M390 50 L470 115" stroke="#64748b" stroke-width="1.5" fill="none"/>
  <path d="M390 125 L470 125" stroke="#64748b" stroke-width="1.5" fill="none"/>
  <path d="M390 200 L470 135" stroke="#64748b" stroke-width="1.5" fill="none"/>
  <rect x="470" y="95" width="115" height="60" rx="8" fill="#232334" stroke="#e2e8f0"/>
  <text x="527" y="120" text-anchor="middle" fill="#f8fafc" font-size="12" font-weight="600">Agente principal</text>
  <text x="527" y="139" text-anchor="middle" fill="#94a3b8" font-size="11">¿lo comprueba?</text>
</svg>
<figcaption>Solo cambia la puerta. Si el mecanismo fuera el canal, el fichero (también un <code>tool_result</code>) y el subagente deberían comportarse igual.</figcaption>
</figure>

## Cómo lo aislé

Con subagentes reales no sale: cada uno escribe un informe distinto, y entonces cambia el contenido además del canal. Así que las conversaciones se construyen a mano y se envían por API. El agente principal siempre está en la misma posición: ya ha delegado, o ha recibido las notas, o ha leído tu mensaje, y tiene que decidir qué hace.

Escribí seis escenarios, cada uno con un dato F que el agente principal puede conocer y un informe que concluye lo contrario, como lo haría de forma plausible un subagente sin ese contexto:

- Los servicios nuevos se dan de alta con un pipeline de autoservicio. El informe dice que no hay automatización y recomienda abrir un ticket a DevOps.
- El usuario sí tiene permiso para desplegar un modelo, concedido a nivel de recurso. El informe lanza el listado que oculta ese permiso y concluye que solo tiene `Reader`.
- Un parser está congelado por una decisión de arquitectura, y los arreglos van en el wrapper que tiene delante. El informe propone parchear el parser.
- Safari por debajo de la 17 no tiene soporte, por decisión de producto. El informe propone un polyfill y bajar el objetivo de navegadores.
- Dos campañas experimentales usaron modelos distintos y no se mezclan nunca. El informe propone copiar las celdas que faltan de una a otra.
- Un feature flag de precios está apagado en producción a propósito, a la espera de Legal. El informe propone encenderlo.

F puede estar en la memoria del agente (enterrado entre otras 39 notas), en una decisión que el usuario dijo antes en la conversación, o en algo que el propio agente averiguó unos turnos atrás. Hay además un control sin F. En uno de los brazos, entre F y el informe hay 58.000 tokens de trabajo real sobre un repositorio.

El agente puede leer ficheros, ejecutar comandos y delegar. Un segundo modelo simula el entorno a partir de un estado del mundo fijo por escenario, en el que F es cierto: si el agente mira donde toca, encuentra F, como pasaría en un repositorio de verdad. Cada episodio sigue hasta que el agente da una respuesta final. Probé Claude Opus 5.5 (el que uso a diario), Gemini 3 Flash y GPT-5.6, con diez tiradas por celda. En total, algo más de 2.800 episodios.

## Lo que no pasó: no se cree el informe por encima de lo que sabe

Con F en el contexto, Opus 5.5 adoptó la conclusión equivocada del informe **4 veces en 791 episodios**, y ninguna cuando el informe venía de su propio subagente. Da igual dónde estuviera guardado F, y también con 58k tokens por medio. Es más: casi siempre nombraba él mismo la causa. Explicaba que el subagente había recomendado el ticket "because it couldn't see those notes", o se echaba la culpa: "that's my fault: I didn't tell it about the pipeline". Gemini y GPT adoptaron la conclusión equivocada un 9–11 % de las veces cuando venía del subagente y un 2–5 % por las otras puertas.

Así que la versión literal de lo que había observado, *se cree al subagente por encima de lo que sabe*, no aparece cuando lo que sabe está a la vista. Detecta la contradicción y la nombra.

## Lo que sí pasó: al subagente nadie lo comprueba

La diferencia estaba en lo que hace el agente *antes* de responder. La comparación más limpia es el control sin F: el agente no tiene con qué contrastar el informe, y la única forma de pillar el error es ir a mirar.

![Proporción de episodios en los que el agente principal respondió sin hacer ni una tool call después de recibir el informe, por modelo y canal, sin ningún dato contradictorio en el contexto. Los informes de su propio subagente se quedan sin comprobar mucho más a menudo: Opus 25 % (47 % con 58k tokens de contexto) frente a 0 % con el mismo texto como fichero o mensaje del usuario; Gemini 88 % frente a 3 % y 0 %. GPT-5.6 es la excepción: 18 % subagente, 2 % fichero, 16 % usuario.](/blog/the-subagent-said-so-unchecked.png)

El mismo texto, palabra por palabra:

- Opus 5.5 comprobó **todos** los informes que le llegaron como fichero de un compañero o como mensaje tuyo: 0 % de respuestas sin una sola comprobación. Cuando el informe venía de su propio subagente, respondió directamente el 25 % de las veces, y el 47 % con contexto largo.
- Gemini 3 Flash respondió sin comprobar el 88 % de las veces cuando el informe venía de su subagente, frente al 3 % y el 0 % por las otras puertas.

Esto también descarta mi hipótesis del canal. El fichero del compañero también llega como `tool_result`, y se comprueba. Lo que se queda sin comprobar no es "cualquier cosa del canal de herramientas". Es **el informe de una investigación que el propio agente encargó**. Una vez delegado el trabajo, cuenta como hecho.

Y las respuestas sin comprobar son las que hacen daño:

![Proporción de episodios en los que la recomendación final del agente principal siguió la conclusión equivocada del informe, sin ningún dato contradictorio en el contexto. Opus 17 % desde su subagente (27 % con contexto largo) frente a 7 % y 2 %; Gemini 95 % frente a 40 % y 18 %; GPT-5.6 18 %, 17 % y 28 %.](/blog/the-subagent-said-so-adopted.png)

En todas las condiciones, cuando el agente no comprueba, adopta la conclusión equivocada unas tres veces y media más que cuando sí lo hace (Opus 7 % frente a 2 %; Gemini 45 % frente a 13 %). Gemini, con su subagente y sin F, la adoptó el 95 % de las veces: propuso el backfill destructivo, el ticket innecesario, encender el flag que Legal tiene parado.

Juntando las dos mitades sale la versión del patrón que creo que es real. En una sesión larga, el dato que se le escapó al subagente rara vez está a la vista: se ha olvidado, nunca se escribió o está tres horas atrás en la conversación. El agente principal no llega a él comparando, porque no lo tiene a mano. Y tampoco comprobando, porque lo que trae el subagente no le parece algo que haya que comprobar.

## GPT lo hace al revés

GPT-5.6 no encaja en el patrón. Comprueba el informe de su subagente más o menos igual que el fichero del compañero. El informe del que más se fía es el que va en el mensaje del usuario: respondió sin comprobar el 36 % de las veces con F en contexto, frente al 10 % con el subagente. Así que esto no es una ley de los modelos de lenguaje y los subagentes. Es un rasgo que cambia según la familia, y conviene saber cuál estás usando.

## Qué me llevo de esto

- **Cuando el agente principal te traslade una conclusión de un subagente, pregúntale qué ha comprobado él.** En estas ejecuciones, lo primero que hacía Opus tras el informe de un subagente era muchas veces responder.
- **Pon las condiciones en la delegación, no solo en tu cabeza o en la memoria del agente.** El subagente no puede respetar lo que nunca le dijeron, y a la vuelta nadie contrasta su informe con esas condiciones si no están ahí mismo.
- **Si construyes harnesses, el informe del subagente es una afirmación, no una observación, y una etiqueta sola no lo arregla.** Probé la intervención obvia con GPT-5.6, el único modelo con el que podía ejecutarla: una nota fija en el informe que avisa de que el subagente no tenía acceso a la memoria ni a las decisiones previas, así que lo que dependa de ellas está sin verificar. Con el dato en memoria, GPT pasó de responder sin comprobar el 10 % de las veces a no hacerlo nunca. Aun así adoptó la conclusión equivocada igual de a menudo (14 % frente a 13 %). Sin nada en memoria, la nota no cambió nada. En Opus y Gemini, donde la diferencia es mayor, sigue sin medir.
- **El modelo cambia el perfil de riesgo.** Gemini acepta casi todo lo que le trae su subagente; Opus acepta una cuarta parte sin mirar; GPT comprueba a su subagente y se fía del usuario.

Esto enlaza con lo que vi cuando [unas sesiones paralelas hablaban entre sí](/es/blog/what-agents-say-to-each-other): el mensaje útil era el que le contaba a la otra sesión algo cierto sobre su propio trabajo. Y con la [cláusula sobre quién responde de lo publicado](/es/blog/nobody-will-check-behind-you), que hizo que un agente comprobara su propia release. La verificación aparece cuando alguien es su dueño. Cuando el agente principal delega, parece que entrega la investigación *y* la responsabilidad de comprobarla, y la segunda es la que nadie pidió.

## Límites

- Seis escenarios construidos a mano. Los intervalos de confianza por bootstrap sobre escenarios son anchos; lo sólido son los contrastes frente al 0 %.
- El entorno lo simula un modelo. En el escenario de permisos, algunas comprobaciones de Opus recibieron un resultado que daba la razón al informe, y eso infla la adopción entre los episodios con comprobación.
- GPT no tiene brazo de contexto largo, y su juez (el modelo que etiqueta la adopción) es de la misma familia. Revisé a mano una muestra de etiquetas: "adopta" acertó 7 de 7.
- 58k tokens de contexto es mucho, pero una sesión real llega a varios cientos de miles.

---

*El código, los seis escenarios, todas las trayectorias y el análisis están en [`experiments/subagent-trust`](https://github.com/JaviMaligno/personal-website/tree/main/experiments/subagent-trust). El diseño, con las predicciones fijadas antes de cada ejecución, está en `DESIGN.md`; las tablas completas, en `RESULTS.md`.*
