---
title: "El único software que necesitas es una suscripción"
description: "Los agentes hicieron construir casi gratis, y eso desnudó lo que en realidad comprabas: no el software, sino el mantenimiento, el desriesgo y tu atención. El buy-vs-build reescrito en torno al único recurso que no se paraleliza."
pubDate: 2026-06-30
tags: ["IA", "Agentes", "Software", "Ingeniería", "Automatización"]
lang: es
translationKey: build-vs-buy-attention
heroImage: "/blog/build-vs-buy-attention.png"
publishToDevto: true
---
Hay una pieza de software que uso todos los días y que no existe como producto. Vigila mis calendarios —el personal, el del trabajo, el de la consultoría— y copia los bloques de ocupado entre todos, de modo que quien mire cualquiera de ellos vea cuándo estoy realmente bloqueado, aunque el bloqueo viva en otro sitio. Hay herramientas de pago que hacen justo esto. Las miré, y luego pasé una tarde con Claude Code escribiendo un script y una rutina que corre de forma programada. Lleva meses funcionando en silencio. Casi me olvido de que está ahí.

Esa última frase es todo el artículo, pero déjame llegar despacio.

Porque la conclusión tentadora ahora mismo —la que el momento te empuja a sacar— es la maximalista: con agentes como Claude Code y Codex, construir casi cualquier cosa está de pronto al alcance, así que ¿para qué pagar por nada? Llevado al extremo, el único software que necesitas es una suscripción a Claude o ChatGPT, y lo demás simplemente lo *construyes*. Hay suficiente verdad en eso como para ser peligroso, que es precisamente por lo que vale la pena frenar un momento.

## Lo que el abaratamiento desnuda de verdad

Es fácil leer el momento de los agentes como "construir se abarató" y quedarse ahí. Cierto, pero no es lo interesante. Lo interesante es lo que ese abaratamiento *deja a la vista* —porque el buy vs build nunca fue realmente una pelea por el coste de construir.

Cuando pagabas por software, la etiqueta de precio casi nunca era por el código. El código era lo de menos. Lo que comprabas eran tres cosas que el código cargaba en silencio:

- **Otro absorbe el mantenimiento.** La cosa sigue funcionando cuando una API cambia, cuando aparece un caso límite, cuando la plataforma se mueve bajo sus pies. Esa responsabilidad es del proveedor, no tuya —para siempre, o hasta que canceles.
- **Otro ya pagó el peaje de prueba y error.** Un producto construido ha pasado por el bucle de "esto parecía bien y no lo era" cientos de veces antes de llegarte. Tú te lo saltas. Compras el otro lado de la curva de aprendizaje.
- **No te cuesta tu atención.** Este es el que más importa y el que menos se nombra.

Los agentes colapsaron el primer coste del que todo el mundo habla —la escritura— y al hacerlo descorrieron la cortina sobre los otros tres. La factura que pagabas nunca fue realmente por el software. Era por no tener que ocuparte de él.

## El recurso que no se paraleliza

De los tres, a la atención es a la que vuelvo una y otra vez, porque se comporta distinto del resto.

El tiempo, los agentes te lo devuelven de verdad. Puedes desplegar cinco a la vez y comprimir una semana de trabajo en una tarde —ya he [escrito sobre lo que eso te da y lo que no](/es/blog/human-limits-managing-ai-agents)—. Pero la atención no es tiempo. Puedes correr cinco agentes en paralelo; no puedes *atender* a cinco cosas en paralelo. Cada herramienta que construyes es una pequeña hipoteca permanente sobre tu atención: algo que puede romperse, desviarse, sorprenderte y pedir calladamente que lo mires. Construye suficientes y no te habrás comprado libertad; te habrás nombrado a ti mismo ingeniero de guardia de una maraña de software de una sola persona a la que nadie más puede avisar.

Así que la pregunta real del buy vs build, ahora que el código es casi gratis, no es "¿puedo construir esto?". La respuesta casi siempre es sí. Es: **¿quién acaba cargando el mantenimiento, y quién acaba cargando con mi atención?**

## Cuándo construyo igualmente

Planteado así, dos situaciones convierten construir en la opción evidente.

**Cuando es trivial y luego se calla.** El sincronizador de calendarios es el caso limpio. Lo construí una vez, corre programado, y no me vuelve a reclamar nada. El coste en atención fue una tarde y luego aproximadamente cero. Este es el punto dulce en el que los maximalistas tienen razón de verdad: pequeño, bien acotado, montar-y-olvidar. Cuando algo puede construirse rápido y luego dejarse correr sin vigilar, construir gana de calle —te saltas la suscripción y pagas casi nada en la moneda que de verdad escasea.

**Cuando nada en el mercado encaja lo suficiente.** [VitaminD Explorer](/es/blog/from-artifact-to-pwa-vitamind) —mi calculadora de síntesis de vitamina D solar— empezó como un artifact de Claude y creció hasta ser una PWA de verdad precisamente porque lo que yo quería no existía en una forma por la que hubiera pagado. Cuando la respuesta del mercado es "se acerca, pero no es la cosa", la cuenta de build/buy deja de ir de coste. No estás abaratando un producto; estás rellenando un hueco que ningún producto rellenó.

Fíjate en que ninguna de las dos es "construir porque construir es gratis". Lo gratis es la *precondición* que pone construir sobre la mesa. No es la razón.

## La trampa, y los límites

El reverso es donde la postura maximalista se rompe en silencio.

La trampa es todo lo que *no* se calla. Una herramienta que hay que vigilar, que se rompe de formas que no puedes prever, que exige una decisión cada vez que algo aguas arriba se mueve —eso no es un ahorro, es un segundo trabajo que te asignaste a ti mismo. Aquí la oferta del proveedor es honesta y vale la pena aceptarla: págame y el mantenimiento, la deriva, el fallo de las 3 de la mañana pasan a ser problema *nuestro*. Para cualquier cosa que de otro modo se quedaría sobre tu atención indefinidamente, ese suele ser el mejor trato incluso cuando podrías construirlo en un fin de semana. El *podría* y el *debería* se separan exactamente aquí.

Y luego están los límites llanos que el marco del "solo una suscripción" despacha con la mano. Los topes de uso son reales. Hay cosas que de verdad no deberían correr sin supervisión, por capaz que sea el agente —cualquier cosa con dinero, identidad o consecuencias irreversibles al otro lado quiere un humano en el bucle, lo que significa que nunca abandona del todo tu atención—. El *reductio* —el único software que necesitas es una suscripción— es una provocación útil y un mal plan operativo. La suscripción es el taller, no el almacén.

## La misma lógica, a escala empresa

Esto no es solo un cálculo personal, y la versión empresarial es la parte de la que se ha hablado hasta el agotamiento: "la muerte del SaaS", cada empresa convirtiéndose en una empresa de software, el gran desempaquetado. No tengo mucho que añadir a ese discurso salvo señalar que el eje sobre el que suele discutir es el equivocado. El debate se fija en coste y capacidad: ahora que *podemos* construir herramientas internas baratas, ¿deberíamos dejar de comprar SaaS? Pero la variable que decide es la misma que en el caso personal —la atención, solo que repartida entre un equipo en lugar de una persona.

He construido sistemas de monitorización internos que corren solos, vigilando logs y haciendo revisiones automáticas de performance y de calidad de código. Herramientas así existen perfectamente en el mercado. La razón para construir no fue un hueco —fue una capa fina de personalización que la opción de catálogo no igualaba de forma barata, encima de algo que, una vez construido, prácticamente se mantiene solo. Coste de atención permanente bajo, esfuerzo modesto, un encaje que no podías comprar: el punto dulce *personal*, a mayor escala.

La misma trampa también escala. Una empresa puede construir algo que luego tiene que mantener con personal para siempre, sacando a un equipo de la línea de negocio real para hacer de niñera de software interno —que no es más que el problema de la guardia desperdigada, pero con una nómina detrás—. La pregunta que una empresa debería hacerse no es "¿podemos construir esto en lugar de comprarlo?". Son las mismas dos preguntas: **¿quién carga el mantenimiento, y a quién le gasta la atención?** Un equipo dedicado de herramientas internas es a veces exactamente la respuesta correcta a eso —y a veces es la forma más cara en que una empresa aprendió que debió, simplemente, haberlo comprado.

## Dónde aterrizo

Ahora construyo por defecto, más que antes, y no me da vergüenza. El código se abarató; eso cambió la cuenta de verdad. Pero la versión de "construye todo" que merece la pena sostener es más estrecha que el eslogan: construye lo trivial como para dejarlo corriendo, o lo que el mercado nunca construyó para ti —y *especialmente* lo que, una vez construido, se calla y deja de reclamarte.

Para todo lo demás, lo más útil que vende una herramienta de pago no es el software. Es el derecho a dejar de prestar atención. Eso es un producto real, y hay días en que es el único que vale la pena comprar.

---

*Complemento de [Los límites humanos al gestionar agentes de IA](/es/blog/human-limits-managing-ai-agents) y [Programación orientada a resultados](/es/blog/results-oriented-programming). VitaminD Explorer vive en [getvitamind.app](https://getvitamind.app).*
