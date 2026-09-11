---
title: "La memoria que fue cierta"
description: "Audité las 35 memorias que mi agente guarda de este proyecto. Tres estaban obsoletas, y ninguna se había equivocado al escribirse: describían un estado que caducó solo. El 80% restante no admite comprobación, y eso no es un defecto."
pubDate: 2026-09-20
tags: ["Agentes", "Memoria", "Contexto", "Verificación"]
lang: es
translationKey: the-memory-that-was-true
heroImage: "/blog/the-memory-that-was-true.png"
repoUrl: "https://github.com/JaviMaligno/personal-website/tree/main/scripts/memory-audit"
---

El artículo anterior terminaba con una pregunta abierta: dónde vive cada tipo de contexto. Mientras lo preparaba, mi agente me sirvió una memoria obsoleta y estuve a punto de hacerle caso.

La memoria decía que, para programar la publicación de un artículo en esta web, hay que crear un workflow de un solo uso con el nombre del artículo. Es lo que hacía en julio. Desde entonces el mecanismo se sustituyó por un manifiesto: un único fichero JSON con la cola de publicaciones. En la rama principal no queda **ni uno** de aquellos workflows.

La memoria no se equivocó. **Fue cierta y dejó de serlo mientras nadie miraba.** No hubo error, ni descuido al escribirla: el mundo se movió y ella se quedó donde estaba.

Eso me llevó a una pregunta más incómoda: si esa estaba caducada y nadie lo sabía, ¿cuántas más?

## Dos memorias con reglas opuestas

Mantengo dos sistemas de memoria a la vez, y están construidos con criterios contrarios a propósito.

Uno es **personal**: los archivos que Claude Code guarda por proyecto. Los escribe el agente al cerrar sesión, yo los reviso, y salen de conversaciones en las que estuve delante.

El otro es **de producción**: el sistema de conocimiento de un bot interno de DevOps que atiende peticiones por chat. Ahí la memoria la escribe un modelo pequeño después de cada respuesta, sin que nadie la supervise, a partir de interacciones con terceros que yo no he leído.

Ese segundo sistema tiene una maquinaria que el personal no necesita, y cada pieza responde a un problema concreto de escribir sin supervisión. Un hecho nuevo no entra como cierto: entra como candidato, y solo asciende cuando el bot vuelve a deducirlo por su cuenta en otra investigación. Lo que nadie confirma en un mes se borra. Lo que lleva noventa días sin que ninguna consulta lo recupere pasa a obsoleto y deja de inyectarse, aunque no se destruye: si alguien lo vuelve a confirmar, revive. Y cada noche un proceso agrupa lo que se parece demasiado y decide si fusionarlo.

| | Personal | Producción |
|---|---|---|
| **Quién escribe** | el agente al cerrar sesión | un modelo pequeño, solo |
| **Con qué revisión** | la mía, antes de guardar | ninguna |
| **A partir de qué** | conversaciones en las que estuve | interacciones con terceros |
| **Confianza** | entra directa | dos confirmaciones |
| **Obsolescencia** | nadie la detecta | caducidad por desuso |
| **Contradicción** | conviven en silencio | se resuelve |
| **Utilidad** | no se mide | se cuenta el uso |

Visto así, la diferencia no es de sofisticación. **Es quién escribe y con cuánta supervisión.** Cuando escribo yo, o reviso lo que se escribe, la confianza sale gratis: por eso el sistema personal puede permitirse ser ligero, y por eso trabajar con él es agradable. Cuando escribe un modelo solo, sobre material que nadie ha leído, hay que construir la confianza entera, y sin esa maquinaria el sistema se degrada solo.

Son problemas distintos y no tiene sentido que se parezcan. Llevar la promoción por evidencia y el olvido nocturno a una carpeta que reviso yo cada día añadiría ceremonia donde ya hay una persona haciendo ese trabajo.

## Lo que caduca solo

Hay una distinción que tardé en ver y que ordena todo lo demás.

**Una preferencia no se vuelve falsa sola.** Si mi criterio es que un artículo debe evitar afirmaciones tajantes, eso no deja de ser cierto por sí mismo: cambia el día que yo cambie de opinión, y ese día lo digo. No hace falta verificar nada.

**Un hecho sobre el sistema sí caduca solo**, en silencio, porque el mundo se mueve sin avisar a nadie. El mecanismo de publicación cambió sin que la memoria que lo describía se enterara.

Así que la verificación automática solo tiene sentido sobre la segunda mitad. Eso deja de ser una limitación para convertirse en el criterio de diseño: **solo se puede comprobar lo que puede caducar sin que nadie lo toque.**

## Contarlas

Dejé que un agente montara un verificador, por ver si de la automatización salía algo que a mano no se viera. La idea es simple: asociar a cada memoria una comprobación que se ejecute contra el repositorio, del tipo *esta memoria afirma que existen esos workflows, así que debería haber al menos uno*. Si no lo hay, la memoria queda marcada.

```json
{ "file_matches": ".github/workflows/scheduled-publish-*.yml" }
```

Sobre las 35 memorias que este proyecto tenía el 11 de septiembre:

| estado | nº | |
|---|---|---|
| verde | 7 | la comprobación pasa |
| **rojo** | **3** | afirma algo que ya no es cierto |
| gris | 25 | no admite comprobación |

Adelanto el juicio sobre la herramienta, porque no es lo interesante: **es torpe**. Cada comprobación hay que escribirla a mano, y escribirla obliga a leerse la memoria entera y decidir qué afirma. Hecho eso, ya sabes si sigue viva: el programa solo lo confirma. Revisar las 35 a mano habría costado parecido y habría dado el mismo número.

Lo que sí justifica el rodeo es lo que apareció por el camino, y no es el número. ([El código está aquí](https://github.com/JaviMaligno/personal-website/tree/main/scripts/memory-audit), con sus límites documentados.)

## Las tres rojas dicen lo mismo

Verifiqué a mano cada roja, porque una roja es una acusación. Las tres eran ciertas. Y las tres comparten forma:

- Una decía que el mecanismo de programación son workflows de un solo uso.
- Otra, que su artículo seguía pendiente en una rama. Se publicó el 30 de agosto.
- Otra, que dos artículos estaban pendientes de revisión y de merge. Se publicaron el 15 y el 30 de julio.

**Ninguna se equivocó al escribirse. Las tres describían un estado transitorio.** «Esto está pendiente», «ahora mismo se hace así». Y un estado transitorio empieza a caducar desde el momento en que se escribe, porque su razón de ser es que va a cambiar.

Ahí hay una regla práctica que no esperaba encontrar: **la memoria que registra un hecho estable envejece bien; la que registra una situación en curso nace con fecha de caducidad.** Y nada obliga a volver sobre ella, porque el día que el trabajo avanza uno está ocupado avanzando.

## Lo que no se puede comprobar, que es casi todo

Recorrí las 31 memorias que no tenían comprobación y solo 7 admitían una. De esas 7 descarté otra por forzada: era una preferencia mía sobre cómo ordenar un documento, y la comprobación la sustituía por la presencia de un texto literal en un fichero. Reescribir ese encabezado la habría puesto roja sin que yo cambiara de criterio, y saltarme el criterio dejando el texto donde estaba la habría dejado verde. No medía lo que decía medir.

Es decir: **alrededor del 80% de mi memoria no admite comprobación mecánica.**

Podría contarlo como el límite de la herramienta. Creo que es más honesto contarlo al revés: ese 80% son criterios, preferencias y formas de trabajar, y **es la parte que hace que trabajar con un agente sea llevadero**. No necesita verificación porque no caduca sola. Ya está bien atendida sin ninguna maquinaria encima.

El instinto al medir algo es querer que el número suba. Aquí subir el número habría significado forzar comprobaciones sobre memorias que no las admiten, y eso no habría medido vigencia: habría fabricado verdes.

## El verde que no significa lo que parece

El resultado más útil del ejercicio fue una de las verdes.

Una memoria sobre la automatización de publicaciones salió **verde**: sus siete ficheros existen, todos comprobados. Y dentro, esa misma memoria decía que una credencial caducaba en una fecha que para entonces había pasado hacía un mes.

El verde era correcto y la memoria estaba caducada a la vez. **Un verde certifica lo que se codificó, no la memoria entera.** No hay contradicción: hay una herramienta respondiendo exactamente la pregunta que se le hizo, y una lectura mía que quería que respondiera otra más grande.

Al ir a arreglarla, la credencial resultó estar perfectamente viva: se había renovado en agosto y nadie lo escribió en ningún sitio. Así que el arreglo no era corregir la fecha, porque una fecha nueva vuelve a caducar en sesenta días y el problema se repite. Era **quitarla y dejar dicho dónde se consulta el estado**, que resultó ser un workflow diario que ya lo comprobaba y lo dejaba escrito en su propio registro.

La memoria pasó de afirmar un hecho con fecha de caducidad a decir dónde mirar. Lo segundo no envejece.

## Una comprobación que no puede fallar

Hay un último resultado, y es sobre el propio intento de automatizar: es la razón por la que no me fío del número más de lo que vale.

Las primeras comprobaciones que entraron describían **cómo funciona el mecanismo hoy**: que existe el manifiesto, que ya no quedan workflows de un solo uso. Son afirmaciones ciertas, así que pasaban todas. Pero una comprobación así no vigila nada: describe el presente, y el presente siempre se describe a sí mismo. Para que la realidad pueda contradecir a una memoria, hay que codificar **lo que la memoria afirma**, no lo que pasa ahora.

**Una comprobación que siempre pasa es peor que no tener ninguna**, porque una memoria sin comprobar se sabe sin comprobar, y una con una comprobación vacua parece vigilada.

Y ahí está el límite del enfoque entero: la herramienta que mide si una memoria sigue siendo cierta puede estar equivocada igual que la memoria que vigila, y con la misma consecuencia. Nadie lo nota, porque el informe dice que todo está bien. Un verificador de verdad necesitaría que alguien verificara al verificador, y eso ya no se sostiene solo.

## Lo que de verdad lo arregla

Después de todo el rodeo, lo que mantiene la memoria viva no es comprobarla: es **cerrar la sesión actualizándola**.

Cuando un trabajo termina —el artículo se publica, el mecanismo cambia, la decisión se toma— ese es el momento en que la memoria que lo describía deja de ser cierta, y es también el único momento en que alguien tiene el contexto entero en la cabeza para corregirla. Media hora después ya cuesta, y una semana después hace falta reconstruirlo.

La buena noticia es que el agente lo hace a menudo por su cuenta, sin que se lo pidan. La mala es que "a menudo" no es "siempre", y las tres rojas de arriba son exactamente los casos en los que no ocurrió. Así que conviene asegurarse: que cerrar sesión incluya preguntarse qué de lo que estaba escrito ha dejado de valer hoy.

Es menos vistoso que un verificador y funciona mejor, porque ataca el problema donde se origina en vez de detectarlo meses después.

## Lo que solo aparece cuando hay más de uno

Todo lo anterior es de una persona y un proyecto. Tres rojas sobre treinta y cinco no es una tasa de obsolescencia de nada: es lo que salió de mi carpeta.

Lo interesante empieza donde se acaba mi caso, y es donde estoy ahora. Cuando la memoria la alimentan varias personas aparecen tres preguntas que en solitario no existen.

**Quién mantiene lo vigente cuando el archivo no tiene dueño.** Hay más opciones de las que parece y ninguna es obviamente la buena: nombrar a alguien responsable; que cada uno actualice lo que toca su contribución, que es quien está en posición de saberlo; que las actualizaciones se propongan y luego se mantengan de forma automatizada; o dejar que lo que nadie usa se marchite solo, como hace el sistema de producción caducando por desuso. Probablemente convivan varias según el tipo de memoria.

**Cómo se corrige lo que ya se ha citado.** Aquí me llevo una idea del sistema de producción que me parece la más transferible de todo él: si las correcciones manuales se vuelven frecuentes, lo que hay que arreglar es cómo se guarda, no construir una herramienta de borrado más cómoda. Corregir mucho a mano no es mantenimiento sano, es un síntoma.

**Y qué ve cada uno**, que planteado como «qué persona ve qué» está mal planteado. Lo que es común al proyecto tiene que llegar a cada agente, y por tanto a cada persona: para eso es común. El matiz fino son los roles. Un PM y un dev del mismo proyecto pueden tener accesos distintos, o el mismo acceso organizado de otra forma, de modo que lo que para uno es conocimiento para el otro sea contexto general.

Lo que no es común es la otra mitad: **las prácticas y la metodología de cada uno**, que difieren en parte porque cada uno trabaja con agentes distintos. Eso no hay que unificarlo, y forzarlo sería repetir el error de querer que dos sistemas con problemas distintos se parezcan.

Pero hay un caso bonito en medio. Cuando varias de esas prácticas propias **convergen solas** —la misma costumbre aparece en gente que no se ha puesto de acuerdo— eso es exactamente la señal que el sistema de producción usa para ascender un hecho de candidato a confirmado: que alguien vuelva a llegar a él por su cuenta. Aplicada a la forma de trabajar en vez de a los hechos, da una vía para estandarizar sin imponer: lo que converge se propone, y lo demás se decide en conjunto o se queda donde está.

No está resuelto. Pero el ejercicio pequeño deja dos cosas que sí me llevo:

- **Lo que registra una situación en curso hay que marcarlo como tal**, porque va a caducar y conviene saber por dónde va a romper.
- **El momento de arreglar una memoria es cuando termina el trabajo que la deja obsoleta**, no meses después con una herramienta.
