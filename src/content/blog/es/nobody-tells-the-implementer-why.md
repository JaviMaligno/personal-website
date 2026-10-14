---
title: "Nadie le cuenta el porqué al que implementa"
description: "Medí cómo se degrada el encargo de un cliente al pasar por un equipo de agentes, del lead al implementador. Los nombres, los números y las prohibiciones sobreviven. Los motivos que los justifican no, y no se desgastan salto a salto: se recortan en el mensaje a quien construye. En prosa, además, un modelo pierde el contrato de datos y su código deja de funcionar."
pubDate: 2026-11-05
tags: ["Agentes", "Multiagente", "Claude", "Comunicación"]
lang: es
translationKey: nobody-tells-the-implementer-why
repoUrl: "https://github.com/JaviMaligno/personal-website/tree/main/experiments/agent-telephone"
heroImage: "/blog/nobody-tells-the-implementer-why.png"
linkedinImage: "/blog/nobody-tells-the-implementer-why-fig-2.png"
---

<style>
.tel-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.tel-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.tel-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
</style>

Mucho de lo que pido a mis agentes lo dicto, y el transcriptor tiene debilidad por los nombres. «Siobhán» sale como otra cosa, y nada en el resto del mensaje permite recuperarlo. Cuando ese encargo pasa después a un agente lead, que se lo pasa a un product manager, que se lo pasa a un arquitecto, que se lo pasa a quien escribe el código, quería saber dos cosas: qué llega al final de la cadena y si los agentes añaden ruido propio por el camino.

Es el juego del teléfono roto, jugado con agentes. Pero no quería la versión artificial, con diez agentes en fila susurrándose. En montajes reales un mensaje rara vez cruza más de tres o cuatro agentes, y cuando lo hace es porque hay una jerarquía: un lead y roles por debajo. Así que eso es lo que medí.

## El montaje

Seis encargos de cliente, tres de software y tres de una agencia de eventos. Los de software piden un módulo pequeño de Python (recordatorios de citas para una óptica, prorrateo de asientos en una factura SaaS, un proceso de purga RGPD). Los de eventos piden un plan: una jornada de empresa, una boda hispano-finlandesa, un congreso científico. Cada encargo está escrito como habla un cliente y contiene hechos de varios tipos, etiquetados de antemano: nombres, números, prohibiciones, condiciones, prioridades, detalles fáciles de pasar por alto y **motivos** («porque el campo antiguo dejó de actualizarse tras la migración del CRM en marzo»).

Dos formas de equipo, las dos realistas:

<figure class="tel-fig">
<svg viewBox="0 0 600 270" role="img" aria-label="Dos topologías de equipo. En la cadena, el encargo del cliente va al lead, después al product manager, al arquitecto y al implementador: cuatro saltos. En el relevo, el lead envía el encargo al product manager, recibe su respuesta y escribe él mismo el cuarto salto al implementador, con el encargo original todavía delante.">
  <defs><marker id="tel-ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="#64748b"/></marker><marker id="tel-ah-amber" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="#f59e0b"/></marker></defs>
  <text x="20" y="24" fill="#94a3b8" font-size="12" font-weight="600">Cadena</text>
  <rect x="20" y="35" width="80" height="34" rx="7" fill="#232334" stroke="#64748b"/><text x="60" y="56" text-anchor="middle" fill="#e2e8f0" font-size="12">cliente</text>
  <rect x="130" y="35" width="80" height="34" rx="7" fill="#232334" stroke="#2dd4bf"/><text x="170" y="56" text-anchor="middle" fill="#e2e8f0" font-size="12">lead</text>
  <rect x="240" y="35" width="80" height="34" rx="7" fill="#232334" stroke="#2dd4bf"/><text x="280" y="56" text-anchor="middle" fill="#e2e8f0" font-size="12">PM</text>
  <rect x="350" y="35" width="80" height="34" rx="7" fill="#232334" stroke="#2dd4bf"/><text x="390" y="56" text-anchor="middle" fill="#e2e8f0" font-size="12">arquitecto</text>
  <rect x="460" y="35" width="110" height="34" rx="7" fill="#232334" stroke="#f59e0b"/><text x="515" y="56" text-anchor="middle" fill="#fbbf24" font-size="12">implementador</text>
  <path d="M100 52 L128 52" stroke="#64748b" stroke-width="1.5" marker-end="url(#tel-ah)"/><path d="M210 52 L238 52" stroke="#64748b" stroke-width="1.5" marker-end="url(#tel-ah)"/>
  <path d="M320 52 L348 52" stroke="#64748b" stroke-width="1.5" marker-end="url(#tel-ah)"/><path d="M430 52 L458 52" stroke="#f59e0b" stroke-width="1.5" marker-end="url(#tel-ah-amber)"/>
  <text x="114" y="86" text-anchor="middle" fill="#94a3b8" font-size="10">1</text><text x="224" y="86" text-anchor="middle" fill="#94a3b8" font-size="10">2</text>
  <text x="334" y="86" text-anchor="middle" fill="#94a3b8" font-size="10">3</text><text x="444" y="86" text-anchor="middle" fill="#fbbf24" font-size="10">4</text>
  <text x="20" y="128" fill="#94a3b8" font-size="12" font-weight="600">Relevo</text>
  <rect x="20" y="175" width="80" height="34" rx="7" fill="#232334" stroke="#64748b"/><text x="60" y="196" text-anchor="middle" fill="#e2e8f0" font-size="12">cliente</text>
  <rect x="130" y="175" width="80" height="34" rx="7" fill="#232334" stroke="#2dd4bf"/><text x="170" y="196" text-anchor="middle" fill="#e2e8f0" font-size="12">lead</text>
  <rect x="270" y="135" width="80" height="34" rx="7" fill="#232334" stroke="#2dd4bf"/><text x="310" y="156" text-anchor="middle" fill="#e2e8f0" font-size="12">PM</text>
  <rect x="270" y="218" width="110" height="34" rx="7" fill="#232334" stroke="#f59e0b"/><text x="325" y="239" text-anchor="middle" fill="#fbbf24" font-size="12">implementador</text>
  <path d="M100 192 L128 192" stroke="#64748b" stroke-width="1.5" marker-end="url(#tel-ah)"/>
  <path d="M210 182 L268 150" stroke="#64748b" stroke-width="1.5" marker-end="url(#tel-ah)"/>
  <path d="M270 163 L212 192" stroke="#64748b" stroke-width="1.5" stroke-dasharray="4 3" marker-end="url(#tel-ah)"/>
  <path d="M210 202 L268 232" stroke="#f59e0b" stroke-width="1.5" marker-end="url(#tel-ah-amber)"/>
  <text x="114" y="226" text-anchor="middle" fill="#94a3b8" font-size="10">1</text>
  <text x="232" y="152" text-anchor="middle" fill="#94a3b8" font-size="10">2</text>
  <text x="254" y="190" text-anchor="middle" fill="#94a3b8" font-size="10">3</text>
  <text x="228" y="232" text-anchor="middle" fill="#fbbf24" font-size="10">4</text>
  <text x="395" y="232" fill="#94a3b8" font-size="11">el lead escribe el salto 4</text>
  <text x="395" y="247" fill="#94a3b8" font-size="11">con el encargo del cliente delante</text>
</svg>
<figcaption>En la cadena, el mensaje al implementador se ha reescrito tres veces. En el relevo también es el salto 4, pero quien lo escribe tiene delante el encargo original. Esa diferencia es la que separa la distancia de la audiencia.</figcaption>
</figure>

Los equipos de eventos tienen tres roles (gestor de cuenta, logística y proveedores) en vez de cuatro, así que su cadena tiene un salto menos.

Cada mensaje entre agentes salía en uno de tres formatos: prosa libre, una lista numerada de requisitos, o una nota breve con el encargo original del cliente adjunto palabra por palabra. El encargo original venía en cuatro versiones: limpio, o con un error de transcripción de un tipo distinto (un nombre destrozado, un homófono, o una puntuación que cambia el sentido: «No, hazlo así» frente a «No hazlo así»).

Los modelos fueron Claude Haiku 5.5 y Sonnet 5.5, como subagentes anidados de verdad en Claude Code, y GPT-6 Luna en un harness propio que pasa los mismos mensajes de rol en rol. Tres repeticiones por celda: 853 corridas válidas de Claude y 432 de Luna. Cada mensaje se puntuó hecho a hecho como conservado, perdido, distorsionado o invertido: nombres y números con comprobaciones deterministas, el resto con un juez de otra familia que los agentes: GPT-6.1 Sol (a través de Codex) para las corridas de Claude, y Claude Opus 5.5 para las de Luna. El artefacto final, el código o el plan, pasó por tests ocultos que comprueban cada requisito.

## Casi todo llega

La mayor parte del encargo sobrevive al viaje. En el salto 4, en las corridas de Claude, las prohibiciones llegan intactas el 98 % de las veces, los detalles fáciles de pasar por alto el 96 %, los números el 92 %, los nombres y las condiciones el 90 %, las prioridades el 85 %. Luna está en el mismo rango: 91-99 % en todo salvo en un tipo.

Ese tipo son los motivos.

## El porqué no se desgasta. Se recorta

En la cadena de Claude, el motivo de una decisión viaja bien durante dos saltos: 88-99 % en el mensaje del lead al PM, 83-97 % del PM al arquitecto. Después el arquitecto escribe al implementador, y cae al 8-31 %.

La lectura obvia sería la distancia: cuatro saltos, cuatro ocasiones de perder algo. El relevo la descarta. Ahí el lead escribe él mismo el salto 4, con el encargo del cliente delante, y solo conserva el motivo en el **24 %** de sus mensajes al implementador, tanto con Haiku como con Sonnet. Tiene la información; decide no pasarla.

<figure class="tel-fig">
<svg viewBox="0 0 600 300" role="img" aria-label="Porcentaje de mensajes que conservan el motivo de una decisión, en los equipos de software, por mensaje y modelo. Lead a PM: Haiku 88 %, Sonnet 99 %, Luna 30 %. PM a arquitecto: 83 %, 97 %, 28 %. Arquitecto a implementador: 31 %, 8 %, 13 %. Lead a implementador en el relevo, con el encargo original delante: 24 %, 24 %, 22 %.">
  <rect x="380" y="10" width="10" height="10" fill="#2dd4bf"/><text x="395" y="19" fill="#e2e8f0" font-size="11">Haiku</text>
  <rect x="445" y="10" width="10" height="10" fill="#f59e0b"/><text x="460" y="19" fill="#e2e8f0" font-size="11">Sonnet</text>
  <rect x="515" y="10" width="10" height="10" fill="#94a3b8"/><text x="530" y="19" fill="#e2e8f0" font-size="11">Luna</text>
  <path d="M70 50 L585 50" stroke="rgba(255,255,255,0.08)"/><path d="M70 145 L585 145" stroke="rgba(255,255,255,0.08)"/><path d="M70 240 L585 240" stroke="#64748b"/>
  <text x="62" y="54" text-anchor="end" fill="#94a3b8" font-size="10">100 %</text><text x="62" y="149" text-anchor="end" fill="#94a3b8" font-size="10">50 %</text><text x="62" y="244" text-anchor="end" fill="#94a3b8" font-size="10">0</text>
  <rect x="462" y="34" width="116" height="210" rx="6" fill="none" stroke="#f59e0b" stroke-dasharray="4 3" opacity="0.6"/>
  <rect x="80" y="73" width="30" height="167" fill="#2dd4bf"/><rect x="114" y="52" width="30" height="188" fill="#f59e0b"/><rect x="148" y="183" width="30" height="57" fill="#94a3b8"/>
  <rect x="210" y="82" width="30" height="158" fill="#2dd4bf"/><rect x="244" y="56" width="30" height="184" fill="#f59e0b"/><rect x="278" y="187" width="30" height="53" fill="#94a3b8"/>
  <rect x="340" y="181" width="30" height="59" fill="#2dd4bf"/><rect x="374" y="225" width="30" height="15" fill="#f59e0b"/><rect x="408" y="215" width="30" height="25" fill="#94a3b8"/>
  <rect x="470" y="194" width="30" height="46" fill="#2dd4bf"/><rect x="504" y="194" width="30" height="46" fill="#f59e0b"/><rect x="538" y="198" width="30" height="42" fill="#94a3b8"/>
  <text x="129" y="260" text-anchor="middle" fill="#e2e8f0" font-size="11">lead → PM</text><text x="129" y="275" text-anchor="middle" fill="#94a3b8" font-size="10">salto 2</text>
  <text x="259" y="260" text-anchor="middle" fill="#e2e8f0" font-size="11">PM → arquitecto</text><text x="259" y="275" text-anchor="middle" fill="#94a3b8" font-size="10">salto 3</text>
  <text x="389" y="260" text-anchor="middle" fill="#e2e8f0" font-size="11">arquitecto → impl.</text><text x="389" y="275" text-anchor="middle" fill="#94a3b8" font-size="10">salto 4, cadena</text>
  <text x="519" y="260" text-anchor="middle" fill="#fbbf24" font-size="11">lead → impl.</text><text x="519" y="275" text-anchor="middle" fill="#94a3b8" font-size="10">salto 4, relevo</text>
</svg>
<figcaption>Porcentaje de mensajes que conservan el motivo de una decisión (equipos de software, formatos de prosa y lista). La caída está en el mensaje al implementador, y ocurre igual cuando quien escribe tiene el encargo completo delante.</figcaption>
</figure>

Así que no es un efecto de teléfono roto en el sentido de algo que se desgasta de boca en boca. Es una decisión sobre la audiencia: quien escribe a quien construye escribe instrucciones, y las instrucciones no llevan motivos. Luna hace lo mismo, solo que antes: quita el motivo desde el primer mensaje (lo conserva en el 30 % de sus mensajes al PM) y se queda bajo hasta el final.

En los equipos de eventos el recorte es más suave. El responsable de proveedores, que reserva el catering y escribe el plan, sigue recibiendo el motivo el 75-84 % de las veces en la cadena de Claude, y el 40-64 % cuando el lead le escribe directamente en el relevo. El ejecutor que escribe código es el que menos lo oye.

### ¿Importa perderlo?

Esa fue mi siguiente pregunta, y la respuesta es menos limpia de lo que esperaba. Dentro de cada regla, formato y modelo, comparé las corridas en las que el motivo llegó al implementador con las que no, y miré si el artefacto final cumplía la regla. Con Claude, conservar el motivo no ayudó: las reglas se cumplían algo *menos* cuando su motivo llegaba (10 puntos menos, intervalo del 95 % de −15 a −5). Con Luna la diferencia va al revés, +9 puntos, pero el intervalo cruza el cero.

El efecto negativo en Claude se concentra en Haiku y en reglas cuyo motivo nombra lo antiguo. «La inactividad se mide con `last_seen_at`, no con `last_login`, porque la app móvil dejó de actualizar `last_login`»: con ese motivo en el mensaje, Haiku usó el campo correcto el 59 % de las veces; sin él, el 97 %. Mi hipótesis es que el motivo vuelve a meter el nombre equivocado en el mensaje y hace de distractor. Este análisis no estaba planeado antes de las corridas, así que lo tomo como hipótesis, no como conclusión. Pero basta para no afirmar que siempre merece la pena llevar el porqué.

Lo que sí importa, y claramente, es perder el requisito en sí. En las corridas de Claude, un hecho que llegó intacto al implementador se cumplía en el artefacto final el 95 % de las veces; uno que se perdió por el camino, el 40 %. Las pérdidas son raras, pero cada una se nota en el resultado.

## Los nombres se congelan; la puntuación se repara

Los errores de transcripción se comportan de forma muy distinta según el tipo.

Un nombre destrozado no se puede reparar a partir del texto: nada en el encargo dice cómo se escribe «Siobhán». Pero sí se puede cuestionar, como haría una persona: «¿seguro que el nombre es este?». Casi nadie lo hizo. En los traspasos de Claude, menos del 2 % de los mensajes que llevaban un nombre destrozado lo marcaron como dudoso; Luna, nunca. El nombre se congeló y llegó al artefacto tal como se transcribió: todos los planes y módulos finales que lo usaban usaban la versión equivocada.

Los errores de puntuación que cambian el sentido, en cambio, se repararon en torno a dos tercios de las veces en los traspasos (Claude 66 %, Luna 73 %), probablemente porque el resto del encargo deja clara la lectura buena. Claude repitió la lectura errónea tal cual en uno de cada siete mensajes, más o menos; Luna, en uno de cada veinte.

## El formato importa, según el modelo

Para Claude, el formato del traspaso apenas cambia nada: una lista numerada conserva algo más en el salto 4 que la prosa (88 % frente a 85 % de los hechos), y el código final puntúa más o menos igual en los tres formatos.

Para Luna lo cambia todo.

<figure class="tel-fig">
<svg viewBox="0 0 600 270" role="img" aria-label="Porcentaje medio de tests ocultos superados por el módulo final de software, por formato de traspaso y modelo. Prosa libre: Haiku 72 %, Sonnet 89 %, Luna 23 %. Lista numerada: Haiku 72 %, Sonnet 89 %, Luna 76 %. Nota con el original adjunto: Haiku 71 %, Sonnet 91 %, Luna 86 %.">
  <rect x="380" y="10" width="10" height="10" fill="#2dd4bf"/><text x="395" y="19" fill="#e2e8f0" font-size="11">Haiku</text>
  <rect x="445" y="10" width="10" height="10" fill="#f59e0b"/><text x="460" y="19" fill="#e2e8f0" font-size="11">Sonnet</text>
  <rect x="515" y="10" width="10" height="10" fill="#94a3b8"/><text x="530" y="19" fill="#e2e8f0" font-size="11">Luna</text>
  <path d="M70 50 L585 50" stroke="rgba(255,255,255,0.08)"/><path d="M70 135 L585 135" stroke="rgba(255,255,255,0.08)"/><path d="M70 220 L585 220" stroke="#64748b"/>
  <text x="62" y="54" text-anchor="end" fill="#94a3b8" font-size="10">100 %</text><text x="62" y="139" text-anchor="end" fill="#94a3b8" font-size="10">50 %</text><text x="62" y="224" text-anchor="end" fill="#94a3b8" font-size="10">0</text>
  <rect x="110" y="98" width="34" height="122" fill="#2dd4bf"/><rect x="150" y="69" width="34" height="151" fill="#f59e0b"/><rect x="190" y="181" width="34" height="39" fill="#94a3b8"/>
  <rect x="270" y="98" width="34" height="122" fill="#2dd4bf"/><rect x="310" y="69" width="34" height="151" fill="#f59e0b"/><rect x="350" y="91" width="34" height="129" fill="#94a3b8"/>
  <rect x="430" y="99" width="34" height="121" fill="#2dd4bf"/><rect x="470" y="65" width="34" height="155" fill="#f59e0b"/><rect x="510" y="74" width="34" height="146" fill="#94a3b8"/>
  <text x="207" y="175" text-anchor="middle" fill="#e2e8f0" font-size="10">23 %</text>
  <text x="167" y="240" text-anchor="middle" fill="#e2e8f0" font-size="11">prosa</text>
  <text x="327" y="240" text-anchor="middle" fill="#e2e8f0" font-size="11">lista numerada</text>
  <text x="487" y="240" text-anchor="middle" fill="#e2e8f0" font-size="11">nota + original adjunto</text>
</svg>
<figcaption>Módulo final de software, porcentaje medio de tests ocultos superados. El código de Luna no es peor en sí: con lista o con el original adjunto queda junto a Claude. En prosa, su resumen pierde los campos de entrada y el implementador se los inventa.</figcaption>
</figure>

Cuando vi por primera vez las cifras de Luna di por hecho que su código era peor sin más. No lo es. El cliente enumera los campos de los datos de entrada («cada cita tiene `id`, `customer_name`, `email`…»), y Luna, al resumir en prosa, quitó esa lista del mensaje al implementador en **54 de 72** corridas. El implementador se inventó entonces los nombres (`appointment["appointment_id"]` en lugar de `appointment["id"]`) y el módulo reventaba en el primer test. Con una lista numerada el contrato llegó el 89 % de las veces; con el original adjunto, siempre. Su código puntuó entonces 0,76 y 0,86, junto a Sonnet.

Claude conservó ese contrato prácticamente en todas las corridas, en los tres formatos. Sus fallos venían de otro sitio: en 29 de sus 216 corridas de software, el implementador de Haiku no entregó código, sino una especificación, porque esa era la forma del mensaje que le había enviado el arquitecto. El tipo de entregable también se había desviado por la cadena.

## Con qué me quedo

- **Si el motivo le importa a quien ejecuta, tiene que estar en su mensaje, y nadie lo va a poner por ti.** Los roles intermedios lo llevan; el que escribe al ejecutor lo quita. Si quieres que el implementador sepa *por qué*, dilo en la delegación o adjunta el original.
- **Adjunta el encargo original al último salto.** Fue el formato más robusto en los tres modelos y el único en el que Luna no perdió el contrato de datos. Cuesta tokens, pero la alternativa es que el implementador adivine nombres de campos.
- **Los contratos viajan literales, no resumidos.** Nombres de campos, firmas y formas de salida son justo lo que un resumen en prosa elimina porque parece detalle.
- **Pide a tus agentes que señalen los nombres que no pueden verificar.** Un nombre destrozado no se arregla aguas abajo, pero sí se puede cuestionar, y en estas corridas nadie lo hizo.

Encaja con lo que encontré al [comparar formas de hacer colaborar a agentes de código](/es/blog/coding-agents-structure): lo que ayudaba era la forma del equipo y de sus traspasos, no un protocolo de conversación mejor. Aquí también, el efecto más grande no estaba en la inteligencia de los modelos, sino en lo que se le pide llevar a cada mensaje.

## Límites

- Seis encargos escritos a mano, tres por dominio. Los errores de transcripción son sintéticos: escritos para parecerse a lo que hace un transcriptor, no producidos ejecutando uno.
- Claude corrió en Claude Code con subagentes de verdad; Luna, en un harness propio. Las comparaciones entre ellos mezclan modelo y harness.
- El juez se validó en una muestra piloto de 150 etiquetas contra un segundo modelo como anotador (Claude Opus 5.5) y un tercero como árbitro (Claude Fable 5.1), no contra etiquetas humanas. Los dos son de la misma familia que los agentes de Claude. En el piloto, su acuerdo fue bueno en las pérdidas y más flojo en las distorsiones (κ 0,79 en conjunto), así que las tasas de distorsión probablemente están infraestimadas. Su acuerdo consigo mismo en una segunda pasada fue de 0,93 (GPT) y 0,97 (Claude).
- Dos comprobaciones de los planes de eventos se corrigieron después de ver los datos: contaban «no Coachline» como una reserva de Coachline. Con la corrección, solo 3 planes en las dos rejillas reservan al proveedor que el cliente había excluido.
- Sonnet delegó dos veces en el mismo paso en el 7 % de sus primeros intentos, sobre todo en corridas de eventos (25 de 30). Esas corridas se repitieron; excluirlas no mueve ninguna cifra más de unos dos puntos.
- El análisis de si el motivo ayuda a cumplir la regla no estaba planeado de antemano.
- Claude Code añade el nombre y el email de la cuenta al contexto de la sesión principal aunque se sustituya el system prompt. En 17 de las 853 corridas de Claude el lead los usó: trató mi email como el del cliente o me nombró como intermediario. Ningún hecho puntuado depende de ello; en los datos publicados están sustituidos.

---

*El código, los seis encargos, todos los mensajes entre agentes, los artefactos finales y las puntuaciones están en [`experiments/agent-telephone`](https://github.com/JaviMaligno/personal-website/tree/main/experiments/agent-telephone). El diseño, con las hipótesis fijadas antes de las corridas y cada cambio posterior fechado, está en `DESIGN.md`; `scripts/article_numbers.py` recalcula desde los datos publicados todas las cifras de este artículo.*
