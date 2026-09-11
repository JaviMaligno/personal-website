---
title: "Conseguir que no dependan de ti"
description: "La capacidad de conseguir que otro pueda hacerse cargo de tu trabajo sin necesitarte para cada decisión. Cómo preparar un relevo cuando trabajas con agentes: separar el estado actual de su historial y conservar los motivos."
pubDate: 2026-09-11
tags: ["Agentes", "Contexto", "Equipos", "Memoria"]
lang: es
translationKey: make-yourself-replaceable
heroImage: "/blog/make-yourself-replaceable.png"
---

Hay una capacidad que me parece especialmente valiosa en una empresa: **conseguir que otra persona pueda hacerse cargo de tu trabajo sin necesitarte para cada decisión.**

Cuanto mejor haces eso, más valor aportas. Y, sin embargo, el resultado es que dejas de ser imprescindible para que ese trabajo continúe.

La paradoja me interesa porque solemos hablar de ser irremplazable como algo a lo que aspirar. Ser quien más sabe, quien resuelve los problemas difíciles, quien tiene todas las respuestas. Pero **si todo ese conocimiento necesita pasar por ti para servirle a alguien más, también has puesto un límite a lo que el equipo puede hacer cuando tú no estás disponible.**

Yo valoraría especialmente a quien sabe hacer bien su trabajo y, además, consigue dar a otros las herramientas, el conocimiento y el contexto para hacerlo con autonomía. Esa capacidad sigue siendo valiosa después del relevo: puede volver a aplicarse en otro proyecto, con otro equipo o ante un problema más difícil.

He llegado a esta reflexión desde algo bastante concreto: preparar un handover cuando trabajas con agentes.

## Lo que no está en el repositorio

Entregar el código y explicar cómo ejecutarlo cubre una parte del trabajo. Pero hay mucho más que has ido acumulando mientras trabajabas: cómo se revisan los cambios, qué se comprueba antes de dar una tarea por terminada, qué restricción pidió el cliente, qué alternativa se descartó y por qué una solución aparentemente mejor todavía no se puede usar.

Si intento ordenar dónde acaba cada cosa, salen tres sitios distintos:

- **La documentación**, que es la parte que solemos considerar el entregable.
- **Las conversaciones con Codex o Claude Code**, donde se discutió el enfoque, se probó algo que no funcionó y se acordó el criterio con el que se revisa.
- **Lo que viene de fuera** y nunca llegó a entrar en el proyecto: un correo, un hilo de Slack, una reunión en la que se cambió una prioridad.

**La tercera categoría es la que peor se conserva, y suele ser la que más pesa.** Una restricción del cliente rara vez se documenta como restricción; llega en un correo, se tiene en cuenta al escribir el código y desaparece. El código queda. El motivo, no.

Cuando llega alguien a ayudarte, necesita orientarse entre todas esas cosas. El repositorio le dice qué existe. Para continuar también necesita entender qué está acordado, qué sigue pendiente y qué motivos hay detrás. **Sin eso puede leer el código entero y aun así proponer la alternativa que ya se descartó hace un mes**, por una razón que sigue siendo válida y que nadie escribió.

## Archivo y memoria

En mi caso la práctica es bastante sencilla: mantengo registros de las comunicaciones relevantes para los proyectos con los que trabajan mis agentes. Correos, conversaciones de Slack y notas de reuniones, en archivos que viven en el propio repositorio del proyecto.

El material entra por dos vías, y la diferencia importa más de lo que parece. Para el correo y para Slack uso conectores, así que **el agente puede consultarlos él mismo** cuando los necesita. Para las reuniones uso las notas que generan Gemini y Granola, y esas las incorporo yo. Algunas conversaciones no tienen conector ninguno y simplemente las pego.

Esa asimetría es la razón de que los archivos locales no sobren teniendo conectores. **El conector resuelve lo que está conectado; el archivo es el único sitio donde puede aterrizar todo lo demás.** Y es también lo que hace que el contexto sobreviva a la herramienta: si mañana cambio de sistema de notas, lo que ya está recogido sigue estando.

La parte que más me importa es **separar el estado actual de su historial, conservando los motivos y las decisiones.** Son dos artefactos distintos y conviene no mezclarlos:

| | Archivo | Memoria mantenida |
|---|---|---|
| **Qué contiene** | todas las comunicaciones, enteras | solo lo que sigue en vigor |
| **Cómo se ordena** | por fecha | por tema |
| **A qué pregunta responde** | ¿qué pasó y cuándo? | ¿qué sabemos hoy? |
| **Cuando algo cambia** | se añade una entrada más | se reescribe y se marca lo superado |
| **Para qué sirve** | investigar, comprobar, citar | ponerse a trabajar |

Ese mantenimiento lo hago en dos momentos. **Cuando entra material nuevo**, se archiva tal cual y se actualiza lo que cambie del estado vigente. **Y al cerrar una sesión de trabajo**, lo que se haya decidido durante esa sesión baja también a la memoria.

Hacen falta los dos. El primero recoge lo que pasa fuera; el segundo, lo que pasa mientras trabajas. Si solo haces el primero, la memoria no registra las decisiones que tomaste tú. Si solo haces el segundo, **la memoria ignora que el cliente cambió de idea el martes.**

Ahora mismo los dos destilados los superviso yo. Automatizarlos es el paso siguiente, no algo que ya tenga resuelto.

Imaginemos que en la reunión del 17 se acuerda entregar una integración el viernes 18. La nota de esa reunión se archiva con su fecha, y la memoria pasa a decir que la entrega es el viernes. Dos días después llega un correo: hay una dependencia del cliente y la entrega se mueve al martes siguiente. El correo se archiva con su fecha, igual que la nota. Y la entrada anterior de la memoria no se borra:

```markdown
## Entrega de la integración

Fecha: martes 22                      [decisión · 19 sep]
Bloqueada por: dependencia del cliente
Pendiente: confirmación del endpoint de staging
Fuente: correo 19 sep — cliente

~~Fecha: viernes 18~~                 [superado · 19 sep]
Fuente: acta de la reunión del 17 sep
```

Son seis líneas y hacen tres cosas a la vez: **dicen qué está vigente, dejan ver qué había antes y apuntan a la fuente de las dos.** Quien retoma el proyecto encuentra primero la fecha buena y lo que falta para cumplirla, que es lo que necesita para ponerse a trabajar. Si necesita entender el cambio, el acuerdo anterior está a un paso. Mezclar las dos cosas obliga a leerlo todo para averiguar qué sigue en pie.

Por eso **la fecha de una nota, su procedencia y si recoge una propuesta o una decisión importan mucho.** No es lo mismo que alguien plantease una fecha a que el equipo la acordase, y en un resumen las dos cosas se parecen demasiado. **Un resumen puede ser útil y estar equivocado.** Poder volver al correo o al acta evita que una interpretación del agente termine convertida en un acuerdo que nadie tomó.

Hay una última decisión que parece administrativa y no lo es: **si esos archivos se commitean o no.** Yo no siempre lo hago. Mientras viven sin commitear son memoria mía y funcionan igual de bien para mi trabajo. En el momento en que entran al repositorio dejan de serlo y pasan a ser contexto del equipo, disponible para cualquiera que abra el proyecto. **Es el mismo gesto técnico y cambia por completo para qué sirve.**

Lo que frena ese gesto no es la pereza, es que obliga a decidir qué puede entrar. Un hilo de Slack lleva nombres, un correo puede llevar datos del cliente, un acta recoge cosas que se dijeron sin pensar que quedarían escritas. Preparar ese material para compartirlo es trabajo real, y es justo el trabajo que hace posible el relevo. Mientras no se hace, **lo que tengo es una práctica personal muy cómoda que no le sirve a nadie más.**

## Esto también me sirve a mí

Nada de esto exige que vaya a incorporarse alguien. Yo también olvido. Yo también vuelvo a un proyecto después de varias semanas y necesito recuperar por qué habíamos decidido algo. Tener ese registro reduce el trabajo de volver a situarme.

Esa es la parte que no esperaba: **cuando el estado vigente está escrito en algún sitio, los cambios se notan.** Si la memoria dice que la entrega es el viernes y aparece un correo que da por hecho otra fecha, la contradicción salta. Cuando todo vive en la cabeza, esa misma contradicción se resuelve sola y sin enterarte, normalmente a favor de lo último que leíste.

Para alguien nuevo, la diferencia puede ser mayor. Le estamos pidiendo que continúe conversaciones en las que nunca estuvo. Si además tiene que descubrir dónde ocurrieron, quién recuerda qué y cuáles siguen siendo relevantes, **buena parte de su incorporación consiste en perseguir contexto.**

Tener acceso a ese material no pone a nadie a tu nivel de inmediato. Siguen haciendo falta experiencia, práctica y acompañamiento. Pero permite que **ese acompañamiento se concentre en desarrollar criterio, en vez de dedicarlo a reconstruir lo que ya pasó.**

Ahí es donde preparar el relevo empieza a parecerse a una práctica diaria más que a una tarea de despedida. Cada decisión importante que queda localizada y actualizada es algo que después no tendrás que explicar desde cero. Sirve para unas vacaciones, para incorporar apoyo o simplemente para que un compañero avance mientras tú estás ocupado.

## La empresa también tiene que dejar sitio

Si compartir conocimiento siempre se hace después de terminar «lo importante», **será lo primero que se abandone cuando haya presión.** Y siempre hay presión.

Si además solo se reconoce a quien desbloquea personalmente cada problema, preparar a otros para resolverlo tendrá poco reconocimiento, porque **su efecto se ve justo donde nadie está mirando: en los problemas que ya no llegan a escalar.**

Debería contar como una contribución que un compañero pueda asumir una responsabilidad que antes dependía de ti. También que una decisión se pueda recuperar sin convocarte, o que el equipo continúe durante tu ausencia. Son resultados que conviene mirar cuando se evalúa el trabajo de alguien, y son difíciles de ver si solo se miran los problemas resueltos y no los que dejaron de aparecer.

## Dónde vive cada cosa

El siguiente paso técnico sería llevar esta memoria a un entorno compartido: que varios agentes puedan consultar el mismo contexto y que las actualizaciones lleguen al proyecto aunque quien lo lleva no haya asistido a una reunión o no haya escrito ese código.

Antes que eso hay una pregunta más básica, y es la que tengo abierta: **dónde vive cada cosa.**

Para lo que pertenece al proyecto —fechas, acuerdos, restricciones del cliente, lo que se descartó— el propio repositorio es un sitio razonable. Está donde está el trabajo, se versiona con él y llega solo a quien tiene acceso.

Pero hay otra mitad que **no pertenece a ningún proyecto**: cómo se revisa un cambio, qué se comprueba antes de dar algo por terminado, qué tecnologías hemos probado y cuáles descartamos, las skills y las herramientas que he ido afinando. Eso se aplica a todos los proyectos a la vez. **Copiarlo en cada repositorio es garantizar que las copias se desincronicen**, y que la versión buena acabe siendo la que está en la cabeza de quien la escribió, que es exactamente el punto de partida del que quería salir.

Ese material necesita un sitio propio y compartible, y ahí las preguntas cambian:

- Cómo se mantiene lo vigente cuando nadie es dueño del archivo.
- Cómo se corrige un error cuando una práctica se queda obsoleta.
- Qué información corresponde compartir con cada persona.

Hay bastante ingeniería detrás, suficiente para otro artículo. Pero **se puede empezar mucho antes de resolver nada de eso**: recogiendo lo relevante, distinguiendo los acuerdos de las propuestas y dejando claro qué sigue en vigor y dónde comprobarlo. Con archivos en un repositorio se llega bastante lejos.

Me interesa que mi contribución se note también en lo que otros pueden hacer después. Si alguien puede continuar mi trabajo con criterio porque he preparado el contexto y le he ayudado a aprender, esa autonomía forma parte de mi trabajo bien hecho.

**Conseguir que no dependan de ti es una capacidad que merece la pena querer conservar en el equipo.**
