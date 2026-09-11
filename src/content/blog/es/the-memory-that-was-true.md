---
title: "La memoria que fue cierta"
description: "Audité las 35 memorias que mi agente guarda de este proyecto. Tres estaban obsoletas, y ninguna se había equivocado al escribirse: describían un estado que caducó solo. El 80% restante no admite comprobación, y eso no es un defecto."
pubDate: 2026-09-20
tags: ["Agentes", "Memoria", "Contexto", "Verificación"]
lang: es
translationKey: the-memory-that-was-true
heroImage: "/blog/the-memory-that-was-true.png"
---

El artículo anterior terminaba con una pregunta abierta: dónde vive cada tipo de contexto. Mientras lo preparaba, mi agente me sirvió una memoria obsoleta y estuve a punto de hacerle caso.

La memoria decía que, para programar la publicación de un artículo en esta web, hay que crear un workflow de un solo uso con el nombre del artículo. Es lo que hacía en julio. Desde entonces el mecanismo se sustituyó por un manifiesto: un único fichero JSON con la cola de publicaciones. En la rama principal no queda **ni uno** de aquellos workflows.

La memoria no se equivocó. **Fue cierta y dejó de serlo mientras nadie miraba.** No hubo error, ni descuido al escribirla: el mundo se movió y ella se quedó donde estaba.

Eso me llevó a una pregunta más incómoda: si esa estaba caducada y nadie lo sabía, ¿cuántas más?

## La memoria que escribes tú y la que escribe un modelo

Resulta que tengo dos sistemas de memoria funcionando a la vez, con decisiones de diseño opuestas.

Uno es **personal**: los archivos que Claude Code mantiene por proyecto. Los escribe el agente al cerrar sesión, yo los reviso, y salen de conversaciones en las que estuve delante.

El otro es **de producción**: el sistema de conocimiento de un bot interno de DevOps que atiende peticiones por chat. Ahí la memoria la escribe un modelo pequeño después de cada respuesta, sin que nadie la supervise, a partir de interacciones con terceros que yo no he leído.

Puestos uno al lado del otro, la diferencia no está donde esperaba:

| | Personal | Producción |
|---|---|---|
| **Quién escribe** | el agente al cerrar sesión, supervisado | un modelo pequeño tras cada respuesta, solo |
| **A partir de qué** | conversaciones en las que estuve | interacciones con terceros |
| **Confianza** | entra directa | `candidato` → `confirmado` tras redescubrirlo dos veces |
| **Obsolescencia** | nadie la detecta | estado `obsoleto` + mantenimiento nocturno |
| **Contradicción** | conviven en silencio | se registra y se resuelve |
| **Utilidad** | no se mide | se cuenta cuántas veces se ha usado |
| **Recuperación** | índice y relevancia | búsqueda semántica |

La tentación era clara: el de producción es más sofisticado, así que llevémoslo al personal. Estuve a punto de proponerlo y era un error de bulto.

**La diferencia no es sofisticación, es quién escribe y con cuánta supervisión.** Cuando escribo yo, o reviso lo que se escribe, la confianza sale gratis: por eso el sistema personal puede permitirse ser ligero, y por eso trabajar con él es agradable. Cuando escribe un modelo solo, sobre material que nadie ha leído, hay que construir la confianza entera —promoción por evidencia repetida, detección de contradicciones, olvido de lo que nadie usa— y sin esa maquinaria el sistema se degrada solo.

Portar una cosa a la otra no habría mejorado nada. Habría añadido ceremonia a un sitio donde la revisión humana ya hace ese trabajo.

## Lo que caduca solo

Hay una distinción que tardé en ver y que ordena todo lo demás.

**Una preferencia no se vuelve falsa sola.** Si mi criterio es que un artículo debe evitar afirmaciones tajantes, eso no deja de ser cierto por sí mismo: cambia el día que yo cambie de opinión, y ese día lo digo. No hace falta verificar nada.

**Un hecho sobre el sistema sí caduca solo**, en silencio, porque el mundo se mueve sin avisar a nadie. El mecanismo de publicación cambió sin que la memoria que lo describía se enterara.

Así que la verificación automática solo tiene sentido sobre la segunda mitad. Eso deja de ser una limitación para convertirse en el criterio de diseño: **solo se puede comprobar lo que puede caducar sin que nadie lo toque.**

## Poner un número

Escribí un verificador pequeño para dejar de especular. La idea es tonta a propósito: cada memoria puede llevar asociada una comprobación que se ejecuta contra el repositorio.

```json
{
  "project_blog_publishing_mechanism": {
    "checks": [
      { "file_matches": ".github/workflows/scheduled-publish-*.yml" }
    ]
  }
}
```

Esa comprobación dice: *la memoria afirma que existen workflows de un solo uso, así que debería haber al menos uno*. Hoy no hay ninguno, la comprobación falla y la memoria sale **roja**.

Cada memoria cae en uno de cuatro montones: **verde** (la comprobación pasa), **rojo** (afirma algo que ya no es cierto), **gris** (no admite comprobación) y **error** (no se puede saber). El cuarto importa más de lo que parece: una comprobación mal escrita no puede contarse como memoria obsoleta, porque inflaría el resultado justo en la dirección que me conviene.

Antes de ejecutarlo dejé escrita una predicción, para que el resultado significara algo: el gris sería el montón mayor, y el rojo pequeño pero no cero.

Sobre las 35 memorias de este proyecto:

| estado | nº |
|---|---|
| verde | 7 |
| **rojo** | **3** |
| gris | 25 |
| error | 0 |

## Las tres rojas dicen lo mismo

Verifiqué a mano cada roja, porque una roja es una acusación. Las tres eran ciertas. Y las tres comparten forma:

- Una decía que el mecanismo de programación son workflows de un solo uso.
- Otra, que su artículo seguía pendiente en una rama. Se publicó el 30 de agosto.
- Otra, que dos artículos estaban pendientes de revisión y de merge. Se publicaron el 15 y el 30 de julio.

**Ninguna se equivocó al escribirse. Las tres describían un estado transitorio.** «Esto está pendiente», «ahora mismo se hace así». Y un estado transitorio empieza a caducar desde el momento en que se escribe, porque su razón de ser es que va a cambiar.

Ahí hay una regla práctica que no esperaba encontrar: **la memoria que registra un hecho estable envejece bien; la que registra una situación en curso nace con fecha de caducidad.** Y nada obliga a volver sobre ella, porque el día que el trabajo avanza uno está ocupado avanzando.

## Lo que no se puede comprobar, que es casi todo

De las 31 memorias que no tenían comprobación, recorrí todas y solo 7 admitían una. Un revisor adversarial rechazó una más por forzada: era una preferencia mía, y la comprobación la sustituía por la presencia de un texto literal en un fichero, que es otra cosa.

Es decir: **alrededor del 80% de mi memoria no admite comprobación mecánica.**

Podría contarlo como el límite de la herramienta. Creo que es más honesto contarlo al revés: ese 80% son criterios, preferencias y formas de trabajar, y **es la parte que hace que trabajar con un agente sea llevadero**. No necesita verificación porque no caduca sola. Ya está bien atendida sin ninguna maquinaria encima.

El instinto al medir algo es querer que el número suba. Aquí subir el número habría significado forzar comprobaciones sobre memorias que no las admiten, y eso no habría medido vigencia: habría fabricado verdes.

## El verde que no significa lo que parece

El resultado más útil del ejercicio es una de las verdes.

Una memoria sobre la automatización de publicaciones sale **verde**: sus siete ficheros existen, todos comprobados. Y dentro, esa misma memoria dice que una credencial caduca en una fecha que ya pasó.

El verde es correcto y la memoria está caducada a la vez. **Un verde certifica lo que se codificó, no la memoria entera.** No hay contradicción: hay una herramienta que responde exactamente la pregunta que se le hizo, y una lectura mía que quería que respondiera otra más grande.

Lo dejé anotado como pregunta para una persona, contando como gris. Una pregunta pendiente no es una comprobación.

## La verificación también puede estar rota

Esto es lo que más me hizo pensar, y me deja en peor lugar.

El verificador necesitó cinco rondas de revisión adversarial. Los fallos graves que aparecieron compartían forma con lo que este artículo denuncia: **eran silenciosos y todos sesgaban hacia «todo correcto»**. Una memoria salía verde cuando el directorio que miraba no existía. Otra se clasificaba como «no comprobable» si cierta palabra aparecía antes en el texto, y desaparecía del informe sin ruido.

Y el mejor de todos fue mío. Escribí las primeras comprobaciones describiendo **cómo funciona el mecanismo hoy**, en vez de lo que la memoria afirma. Pasaban todas, claro. Una comprobación que describe el presente no puede fallar nunca, y **una comprobación que siempre pasa es peor que ninguna, porque da confianza falsa.**

La herramienta que mide si la memoria sigue siendo cierta puede estar equivocada exactamente de la misma manera que la memoria que vigila, y con la misma consecuencia: nadie lo nota, porque el informe dice que todo está bien.

La prueba que uso ahora antes de escribir una comprobación son dos preguntas: qué hecho concreto la pondría en rojo, y si ese hecho podría ocurrir sin que la memoria dejase de ser cierta. Si la respuesta a la segunda es que sí, la comprobación no sirve.

## Lo que solo aparece cuando hay más de uno

Todo esto es de una persona y un proyecto. Tres rojas sobre treinta y cinco no es una tasa de obsolescencia de nada: es lo que salió de mi carpeta.

Lo interesante empieza donde se acaba mi caso. En el sistema de producción la memoria la escriben interacciones de otros, y ahí aparecen problemas que en solitario no existen: quién mantiene lo vigente cuando el archivo no tiene dueño, cómo se corrige algo que ya se ha citado en otras decisiones, y qué información corresponde compartir con cada persona.

Es en lo que estoy trabajando ahora, y no está resuelto. Pero el ejercicio pequeño ya dejó dos cosas que me llevo:

- **Lo que registra una situación en curso hay que marcarlo como tal**, porque va a caducar y conviene saber por dónde va a romper.
- **Una comprobación que nunca puede fallar es ruido con aspecto de garantía.**

El código del verificador está en el [repositorio de esta web](https://github.com/JaviMaligno/personal-website/tree/main/scripts/memory-audit), con sus límites documentados. Es pequeño a propósito: lo interesante no era la herramienta, era el número que salió al usarla.
