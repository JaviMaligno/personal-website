---
title: "El error que nadie puede alcanzar"
description: "Un modelo del mundo puede estar rotundamente equivocado sobre toda una región, pasar cualquier test que sepas escribir y no costarte absolutamente nada — con demostración. Mueve ese mismo error unos metros, hasta el camino por el que algo pasa de verdad, y te cuesta todo. Lo que decide no es el tamaño ni la forma del error. Es el alcance."
pubDate: 2026-09-05
tags: ["IA", "Machine Learning", "Testing", "Investigación", "Agentes"]
lang: es
translationKey: the-bug-nobody-can-reach
heroImage: "/blog/the-bug-nobody-can-reach.png"
repoUrl: https://github.com/JaviMaligno/code-world-models
linkedinLinks:
  - label: "Preprint"
    url: "https://arxiv.org/abs/XXXX.XXXXX"
---
Supón que al mapa sobre el que planifica tu sistema le falta una habitación. No "está un poco equivocado sobre la habitación" — la habitación no está en el mapa. ¿Cuánto te cuesta eso?

He pasado unos meses haciendo precisa esa pregunta, y la respuesta resultó más estrecha y más rara de lo que esperaba. Depende exactamente de una cosa, y no es el tamaño del error, ni lo seguro que estuviera el modelo, ni siquiera si lo que falta es peligroso. Es si algo que planifique sobre ese mapa puede **llegar** a la habitación.

Esta es la versión corta de un preprint ([arXiv:XXXX.XXXXX](https://arxiv.org/abs/XXXX.XXXXX)); el [post largo](/es/blog/being-wrong-can-be-free) cuenta lo mismo con los números, las demostraciones y las partes que salieron mal. Aquí quiero solo la idea, porque es la que yo usaría.

<style>
.cwm-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.cwm-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.cwm-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
</style>


## El montaje, en un párrafo

Un robot pequeño sobre un plano. En algún sitio de ese plano hay una banda que no debe cruzar — una valla alrededor de un punto de alto valor al que, si no, iría directo. A un modelo de lenguaje se le da la física y se le pide que escriba el simulador que usará el planificador, y la descripción que recibe simplemente **omite la valla**. Después se pone a prueba su simulador: ejecutar el sistema real unas decenas de veces y comprobar que el código escrito predice cada paso exactamente. Si lo hace, se acepta. Eso es todo lo que es aquí un "conjunto de tests", y es exactamente lo que es en la práctica.

Vallas, recintos de contención, zonas de exclusión geovalladas: esa es la forma que tienen de verdad las omisiones críticas para la seguridad, y por eso dejé de usar muros y empecé a usar anillos.

<figure class="cwm-fig">
<!-- fig:plain-setup -->
<svg viewBox="0 0 600 252" role="img" aria-label="The setup: a robot outside a fenced band, the high-value spot inside it, and the straight route the robot wants to take">
<defs><marker id="mk-setup" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,1 L9,5 L0,9 z" fill="#f8fafc"/></marker></defs>
<circle cx="300.0" cy="128.0" r="72.25" fill="none" stroke="#f43f5e" stroke-width="25.50" stroke-opacity="0.85"/>
<polygon points="300.0,110.2 295.4,121.6 283.0,122.5 292.5,130.4 289.5,142.4 300.0,135.9 310.5,142.4 307.5,130.4 317.0,122.5 304.6,121.6" fill="#fbbf24"/>
<circle cx="158.9" cy="128.0" r="4.2" fill="#f8fafc"/>
<line x1="164.9" y1="128.0" x2="202.2" y2="128.0" stroke="#f8fafc" stroke-width="2.0" stroke-dasharray="5 3" marker-end="url(#mk-setup)"/>
<path d="M207.8,122.5 L218.8,133.5 M218.8,122.5 L207.8,133.5" stroke="#f8fafc" stroke-width="2.4" stroke-linecap="round"/>
<text x="158.9" y="112.0" font-size="11" fill="#f8fafc" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">the robot</text>
<text x="396.0" y="133.0" font-size="11" fill="#fbbf24" text-anchor="start" font-family="ui-monospace,'JetBrains Mono',monospace">what it wants</text>
<text x="300.0" y="32.0" font-size="11" fill="#fb7185" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">the fence — not in the description it was given</text>
<text x="30.0" y="226.0" font-size="10" fill="#64748b" text-anchor="start" font-family="ui-monospace,'JetBrains Mono',monospace">it stops here — and the model never mentioned it</text>
</svg>
<!-- /fig:plain-setup -->
<figcaption>El montaje. El robot quiere el punto de alto valor; la valla que lo rodea es real pero no está en la descripción que recibió el modelo, así que el código que escribe dice que el camino está libre.</figcaption>
</figure>


## Cuando equivocarse es gratis

Cierra la banda del todo — un anillo completo alrededor del punto — y esto es lo que escribe el modelo: no un anillo, sino un **disco relleno**. Todo el interior marcado como prohibido, cuando en realidad solo lo está el borde. Equivocado sobre la forma del mundo, y no por un milímetro sino categóricamente.

De ese modelo equivocado son ciertas dos cosas, y son la razón de que escribiera el paper.

**Ningún test puede pillarlo.** No es "tuvimos mala suerte" ni "harían falta más muestras". Hay demostración. La valla detiene al robot al contacto, así que ninguna ejecución que empiece fuera puede acabar dentro; por tanto ninguna observación que ningún test pueda hacer jamás distingue el disco relleno de la verdad. Puedes lanzar un millón de muestras con la tolerancia que quieras. Coinciden, siempre, porque el sitio donde discrepan es un sitio al que nada llega.

**No cuesta nada.** El planificador que se fía del disco relleno elige la misma acción en cada paso que uno que tuviera el mapa verdadero: mismo recorrido, mismo resultado, mismos contactos, ejecución por ejecución, semilla por semilla. No aproximadamente: idénticamente.

O sea: certificado, incorrecto y gratis. En nuestra cabeza esas tres cosas suelen ir juntas; aquí se separan limpiamente.

Una palabra sobre cómo mido el coste, porque hace legible el resto. Comparo lo que gana el planificador contra dos referencias: lo que ganaría con la verdad y lo que ganaría actuando al azar. **Cero significa que el modelo equivocado no cuesta nada. Uno significa que podrías haber actuado al azar. Por encima de uno significa que el modelo te llevó activamente a algo peor que el azar.**

## La misma ceguera, otro mundo

Ese era un tipo de modelo equivocado: uno que **inventa** una región prohibida donde nada puede ir. Aquí está el otro, y el que duele de verdad — un modelo que simplemente no sabe que la valla existe. Es el caso común: la descripción omitió la valla, las ejecuciones de prueba no la tocaron por casualidad, y el código volvió sin ella.

Ahora la valla **sí** está en la ruta. El planificador conduce confiado hacia el punto de alto valor, la valla real lo detiene en seco, y replanifica la misma ruta condenada en cada paso. Coste: **1.116** — peor que actuar al azar, porque el modelo no es solo poco informativo: promete activamente una ruta que no existe.

Ahora cambia una cosa, y es una cosa del mundo, no del modelo: abre en la valla un hueco lo bastante ancho para pasar, y pon ese hueco **delante** del robot, por donde ya quería ir. Mismo modelo. Misma ceguera. La misma cláusula que falta en el código. Coste: **0.029**. Casi nada — porque la ruta equivocada y confiada va ahora a un sitio que la verdad sí permite.

Y para asegurarnos de que no fue el hueco en sí, pon ese mismo hueco — anchura idéntica, y en los dos casos la valla es igual de "no un anillo cerrado" — por detrás, por donde no pasa ninguna ruta. Coste: **1.116** otra vez, con cuatro decimales lo mismo que la valla completamente cerrada.

Mismo modelo, mismo error, misma forma de agujero. Un número es 0.029 y el otro es 1.116, y lo único que los separa es si el camino del propio robot cruza el hueco.

<figure class="cwm-fig">
<!-- fig:plain-free-vs-costly -->
<svg viewBox="0 0 600 244" role="img" aria-label="The same gap in the fence, in front of the robot and behind the goal, with the cost of the blind model in each case">
<defs><marker id="mk-plain" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,1 L9,5 L0,9 z" fill="#f8fafc"/></marker></defs>
<rect x="10" y="22" width="285" height="170" rx="8" fill="none" stroke="rgba(255,255,255,0.10)"/>
<text x="152.0" y="15.0" font-size="11.5" fill="#94a3b8" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace" font-weight="bold">gap in front of the robot</text>
<circle cx="152.0" cy="104.0" r="59.50" fill="none" stroke="#6366f1" stroke-width="21.00" stroke-opacity="0.9" stroke-dasharray="338.54 35.31" stroke-dashoffset="169.27"/>
<polygon points="152.0,90.7 148.6,99.3 139.4,99.9 146.4,105.8 144.2,114.8 152.0,109.9 159.8,114.8 157.6,105.8 164.6,99.9 155.4,99.3" fill="#fbbf24"/>
<circle cx="42.8" cy="104.0" r="3.6" fill="#f8fafc"/>
<line x1="47.8" y1="104.0" x2="132.4" y2="104.0" stroke="#f8fafc" stroke-width="2.0" stroke-dasharray="5 3" marker-end="url(#mk-plain)"/>
<text x="152.0" y="180.0" font-size="15" fill="#6366f1" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace" font-weight="bold">costs you  0.029</text>
<text x="152.0" y="210.0" font-size="9.5" fill="#64748b" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">the route goes through</text>
<rect x="305" y="22" width="285" height="170" rx="8" fill="none" stroke="rgba(255,255,255,0.10)"/>
<text x="447.0" y="15.0" font-size="11.5" fill="#94a3b8" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace" font-weight="bold">the same gap, round the back</text>
<circle cx="447.0" cy="104.0" r="59.50" fill="none" stroke="#f43f5e" stroke-width="21.00" stroke-opacity="0.9" stroke-dasharray="338.54 35.31" stroke-dashoffset="356.20"/>
<polygon points="447.0,90.7 443.6,99.3 434.4,99.9 441.4,105.8 439.2,114.8 447.0,109.9 454.8,114.8 452.6,105.8 459.6,99.9 450.4,99.3" fill="#fbbf24"/>
<circle cx="337.8" cy="104.0" r="3.6" fill="#f8fafc"/>
<line x1="342.8" y1="104.0" x2="367.2" y2="104.0" stroke="#f8fafc" stroke-width="2.0" stroke-dasharray="5 3" marker-end="url(#mk-plain)"/>
<path d="M371.3,99.0 L381.3,109.0 M381.3,99.0 L371.3,109.0" stroke="#f8fafc" stroke-width="2.4" stroke-linecap="round"/>
<text x="447.0" y="180.0" font-size="15" fill="#f43f5e" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace" font-weight="bold">costs you  1.116</text>
<text x="447.0" y="210.0" font-size="9.5" fill="#64748b" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">the fence still blocks it</text>
<text x="300.0" y="232.0" font-size="11.5" fill="#f8fafc" text-anchor="middle" font-style="italic">same model, same fence, same size of gap</text>
</svg>
<!-- /fig:plain-free-vs-costly -->
<figcaption>El mismo modelo ciego en dos mundos que se diferencian en una rotación. A la izquierda el hueco cae por donde el robot ya iba, así que su ruta equivocada y confiada resulta estar permitida. A la derecha el hueco idéntico está detrás del objetivo, la valla sigue cortando la ruta, y el modelo cuesta más que actuar al azar.</figcaption>
</figure>


Ese es el hallazgo entero, y la razón de que el eslogan sea *alcance* y no forma: no puedes mirar en qué se equivocó tu modelo — ni su tamaño, ni su geometría, ni siquiera una propiedad estructural tan robusta como "¿tiene un agujero?" — y concluir nada en absoluto sobre lo que te va a costar. Tienes que preguntar por dónde puede ir lo que planifica contra él.

## "Pero en el mundo real yo podría rodearlo"

Esa fue la primera objeción que me hicieron, y es la correcta. En dos dimensiones un anillo es un muro: claro que no entra nada. A lo mejor todo el resultado es un artefacto de un juguete donde el error está casualmente sellado.

Así que el paper corre el caso en el que rodear **sí** es posible: una región con forma de donut flotando en el espacio tridimensional, entre el robot y su objetivo. Nada está sellado — existe una ruta explícita que la rodea sin tocarla en absoluto.

<figure class="cwm-fig">
<!-- fig:torus-3d -->
<svg viewBox="0 0 600 250" role="img" aria-label="The same solid torus in three dimensions: with the route through its hole it costs 0.019, and moved so the route runs into the tube it costs 0.898 — while a contact-free path around it still exists">
<defs><marker id="t3-mk" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,1 L9,5 L0,9 z" fill="#f8fafc"/></marker></defs>
<defs><marker id="t3b-mk" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,1 L9,5 L0,9 z" fill="#f8fafc"/></marker></defs>
<defs><marker id="t3b-mk2" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,1 L9,5 L0,9 z" fill="#22d3ee"/></marker></defs>
<rect x="10" y="22" width="285" height="176" rx="8" fill="none" stroke="rgba(255,255,255,0.10)"/>
<text x="152.0" y="15.0" font-size="11.5" fill="#94a3b8" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace" font-weight="bold">the route threads the hole</text>
<ellipse cx="152.0" cy="172.0" rx="46" ry="7" fill="#000" fill-opacity="0.30"/>
<defs><clipPath id="t3-far"><rect x="152.0" y="2.0" width="72.0" height="204.0"/></clipPath><clipPath id="t3-near"><rect x="80.0" y="2.0" width="72.0" height="204.0"/></clipPath></defs>
<path d="M120.0,104.0 A32.0,62.0 0 1,0 184.0,104.0 A32.0,62.0 0 1,0 120.0,104.0 Z" fill="none" stroke="#6366f1" stroke-width="20" stroke-opacity="0.55" clip-path="url(#t3-far)"/>
<circle cx="34.0" cy="104.0" r="3.4" fill="#f8fafc"/>
<line x1="40.0" y1="104.0" x2="254.0" y2="104.0" stroke="#f8fafc" stroke-width="2.0" stroke-dasharray="5 3" marker-end="url(#t3-mk)"/>
<path d="M120.0,104.0 A32.0,62.0 0 1,0 184.0,104.0 A32.0,62.0 0 1,0 120.0,104.0 Z" fill="none" stroke="#6366f1" stroke-width="20" clip-path="url(#t3-near)"/>
<polygon points="268.0,91.0 264.6,99.4 255.6,100.0 262.6,105.8 260.4,114.5 268.0,109.7 275.6,114.5 273.4,105.8 280.4,100.0 271.4,99.4" fill="#fbbf24"/>
<text x="152.0" y="186.0" font-size="15" fill="#6366f1" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace" font-weight="bold">costs you  0.019</text>
<text x="152.0" y="214.0" font-size="9.5" fill="#64748b" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">it never touches the object</text>
<rect x="305" y="22" width="285" height="176" rx="8" fill="none" stroke="rgba(255,255,255,0.10)"/>
<text x="447.0" y="15.0" font-size="11.5" fill="#94a3b8" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace" font-weight="bold">the same torus, moved</text>
<ellipse cx="447.0" cy="172.0" rx="86" ry="7" fill="#000" fill-opacity="0.30"/>
<defs><clipPath id="t3b-far"><rect x="323.0" y="34.0" width="248.0" height="70.0"/></clipPath><clipPath id="t3b-near"><rect x="323.0" y="104.0" width="248.0" height="70.0"/></clipPath></defs>
<path d="M363.0,104.0 A84.0,30.0 0 1,0 531.0,104.0 A84.0,30.0 0 1,0 363.0,104.0 Z" fill="none" stroke="#f43f5e" stroke-width="21" stroke-opacity="0.55" clip-path="url(#t3b-far)"/>
<circle cx="329.0" cy="104.0" r="3.4" fill="#f8fafc"/>
<line x1="335.0" y1="104.0" x2="365.0" y2="104.0" stroke="#f8fafc" stroke-width="2.0" stroke-dasharray="5 3" marker-end="url(#t3b-mk)"/>
<path d="M350.0,99.0 L360.0,109.0 M360.0,99.0 L350.0,109.0" stroke="#f8fafc" stroke-width="2.4" stroke-linecap="round"/>
<path d="M337.0,104.0 Q447.0,16.0 549.0,104.0" fill="none" stroke="#22d3ee" stroke-width="2" stroke-dasharray="6 4" marker-end="url(#t3b-mk2)"/>
<text x="447.0" y="36.0" font-size="9.5" fill="#22d3ee" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">a way around, contact-free</text>
<path d="M363.0,104.0 A84.0,30.0 0 1,0 531.0,104.0 A84.0,30.0 0 1,0 363.0,104.0 Z" fill="none" stroke="#f43f5e" stroke-width="21" clip-path="url(#t3b-near)"/>
<polygon points="563.0,91.0 559.6,99.4 550.6,100.0 557.6,105.8 555.4,114.5 563.0,109.7 570.6,114.5 568.4,105.8 575.4,100.0 566.4,99.4" fill="#fbbf24"/>
<text x="447.0" y="186.0" font-size="15" fill="#f43f5e" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace" font-weight="bold">costs you  0.898</text>
<text x="447.0" y="214.0" font-size="9.5" fill="#64748b" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">the route runs into the tube</text>
<text x="300.0" y="238.0" font-size="11" fill="#f8fafc" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">nothing here is sealed off  ·  same object, same contact rarity 0.0033</text>
</svg>
<!-- /fig:torus-3d -->
<figcaption>El donut en tres dimensiones. A la izquierda la ruta pasa por su agujero y el modelo equivocado no cuesta casi nada; a la derecha el mismo objeto se ha movido para que la ruta se meta en él, y cuesta casi tanto como actuar al azar. El camino de puntos que pasa por encima es el que importa para la segunda mitad de la historia: llega al objetivo sin tocar nada, y eso es lo que vuelve a hacer el error detectable en principio.</figcaption>
</figure>


El resultado se parte en dos, y esta es la versión que yo me llevaría a un sistema real.

**El peligro sobrevive.** Pon el donut de forma que la ruta planificada se meta en su parte sólida y el coste es **0.898**. Muévelo para que la ruta enhebre el agujero y el coste es **0.019** — mismo objeto, misma rareza de contacto, misma forma trivial. Lo que te cuesta es estar en el camino, encierre la cosa algo o no.

**La garantía no.** En cuanto puedes rodear, ya no hay ninguna región que un planificador competente no pueda consultar por demostración, así que ya no hay ninguna prueba de que un test no habría podido pillar el error. Pasa a ser meramente improbable de pillar, que es una situación mucho más débil y mucho más familiar.

Dos preguntas distintas, entonces, y hasta este experimento las tenía fundidas en una:

- **¿Cruza algún plan el sitio donde mi modelo se equivoca?** Esto decide lo que cuesta el error.
- **¿Está ese sitio amurallado frente a todo lo que puedo ejecutar?** Esto decide si algún test habría podido encontrarlo.

## Qué le preguntaría a mi propio sistema

Tres preguntas, y ninguna necesita las matemáticas:

1. **¿Dónde se equivoca mi modelo de una forma que nada de lo que ejecuto visita nunca?** Esa parte hoy es gratis — y también es invisible para todos mis tests, así que nadie me va a avisar cuando deje de serlo.
2. **¿Qué metería un plan por ahí?** Una funcionalidad nueva, un objetivo nuevo, un atajo que alguien añade el trimestre que viene. El alcance no es una propiedad del modelo; es una propiedad del modelo **más** lo que planifica con él, y la segunda mitad cambia mucho más a menudo que la primera.
3. **¿Mis tests muestrean donde mi sistema actúa, o donde es cómodo muestrear?** Una suite en verde certifica la parte alcanzable y no dice absolutamente nada del resto.

La versión incómoda de todo esto: un modelo puede ser exactamente correcto en todo lo que puedes comprobar y arbitrariamente incorrecto más allá, y la diferencia entre "gratis" y "catastrófico" no es una propiedad del error. Es una propiedad de los planes que hoy resulta que ejecutas.

---

*La versión larga, con las curvas de peligro, los experimentos de reparación y un test pre-registrado que salió nulo: [Estar equivocado puede ser gratis](/es/blog/being-wrong-can-be-free). La versión formal: [arXiv:XXXX.XXXXX](https://arxiv.org/abs/XXXX.XXXXX), con el [código y todos los artefactos de resultados abiertos](https://github.com/JaviMaligno/code-world-models).*
