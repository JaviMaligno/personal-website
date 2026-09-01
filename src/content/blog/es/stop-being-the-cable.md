---
title: "Deja de hacer de cable"
description: "Casi todos los equipos que prueban un agente y vuelven en silencio a lo de antes no fallaron por falta de habilidad. Estaban haciendo la fontanería a mano — copiar, pegar, devolver la respuesta — y eso cuesta lo mismo todas las veces. Qué implica conectarlo de verdad, y qué parte tendrías que construir tú."
pubDate: 2026-09-01
tags: ["IA", "Agentes", "MCP", "Context Engineering", "Mentoría"]
lang: es
translationKey: stop-being-the-cable
heroImage: "/blog/stop-being-the-cable.png"
---

A alguien que conozco le enseñaron a resolver una consulta de fiscalidad transfronteriza dándole el contexto del cliente a una IA interna, en vez de perder una tarde peleándose con Google. Funcionó. Le pareció genial. A la semana siguiente había vuelto a Google, y allí se quedó.

La lectura habitual de esa historia es resistencia al cambio, y algo de eso hay. Pero conviene mirar la mecánica un segundo, porque en ella está todo: **ese contexto se lo dio una persona, a mano, esa vez.** No quedó cableado en ninguna parte. Para repetir la jugada el martes había que volver a buscar el material, volver a pegarlo y volver a explicar la situación — que es más caro que la búsqueda a la que sustituía.

Eso no es una persona que no adopta una herramienta. Es una persona que se da cuenta, con razón, de que el coste se paga entero cada vez mientras el beneficio no se acumula.

## El humano como cable

Mira cómo se trabaja de verdad en un equipo que "lo probó y no cuajó" y verás esto. Abrir el sistema donde vive el trabajo. Copiar algo de ahí. Pegarlo en una ventana de chat. Leer la respuesta. Copiarla de vuelta al sistema donde vive el trabajo.

La persona es el cable. Es la capa de integración, ejecutada a mano, una vez por tarea.

Es el fallo peor diagnosticado que me encuentro, por dos razones. Primero, porque *funciona* — los resultados son buenos, así que nada parece roto. Segundo, porque se presenta exactamente igual que un problema de habilidad: quien persiste es quien tolera el tedio, así que la constancia se confunde con aptitud y al resto se le archiva como "no le pilló el punto".

Y desde arriba es invisible. Los paneles de licencias miden si se abrió la herramienta. No distinguen entre un agente que lee tu repositorio y un agente que lee lo que alguien tuvo la paciencia de pegarle, que es la diferencia entre una herramienta y una caja de texto muy cara.

## Por qué a los perfiles técnicos les duele más de lo que parece

Si vienes de ingeniería, [tu problema suele ser el contrario](/es/blog/if-you-came-from-engineering): revisas de más, delegas por debajo de tu nivel y compruebas con los ojos lo que debería comprobar un mecanismo.

Lo que añadiría ahora es esto. Cuando el agente no ve tu repositorio, ni el ticket, ni vuestras convenciones, ni las cuatro últimas decisiones, revisarlo todo es *correcto*. Está produciendo código plausible contra un proyecto que no ha leído nunca. Ese exceso de revisión no es solo una costumbre heredada — es una respuesta racional a un montaje mal cableado, y no se va a arreglar confiando más. No puedes dejar de comprobar con los ojos hasta que algo sostenga el contexto de verdad.

Por eso "delega más" es mal consejo si va solo. Delegar más, ¿a qué exactamente?

## Tres capas que se colapsan en una

"Integrar la IA" se dice como si fuera una cosa. Son tres, fallan de forma distinta y cuestan cantidades muy distintas.

**Qué sabe.** ¿De dónde saca todo lo que dais por obvio de vuestra casa — el vocabulario del dominio, las decisiones ya tomadas, por qué ese módulo es raro? Hoy eso vive en la cabeza de un compañero y en una conversación de marzo. Su sitio son ficheros que el agente lee por defecto, documentación a la que llega, el propio repositorio. He escrito el mismo principio desde el lado del entorno: [prepara el entorno, no el agente](/es/blog/bootstrap-the-environment-not-the-agent) — el conocimiento operativo que vive en una conversación en vez de en el repo se vuelve a explicar en cada sesión nueva, para siempre.

**Qué respeta.** ¿Cómo sabe qué es aceptable aquí y qué no? Convenciones, definición de hecho, lo que nunca sale a producción. Un aviso salido de mis propios datos: [medí qué compra realmente el andamiaje prescriptivo](/es/blog/the-scaffolding-you-pay-for), y en cuanto el agente tiene herramientas el beneficio se desvanece casi entero y la factura se queda. Así que esta capa conviene tenerla delgada y cargar el peso en mecanismos, no en prosa — una comprobación que falla vale más que un documento que lo pide por favor. [Las skills que sí mantengo](/es/skills) son las que codifican algo que el modelo no puede deducir del repositorio.

**Qué puede tocar.** ¿Sobre qué sistemas actúa sin humano en medio? El repositorio, el gestor de tickets, la documentación, la base de datos, el canal del equipo. Es la capa que termina con el copiar y pegar, y es la que casi nadie monta — porque es la única que obliga a pedirle permiso a alguien.

La mayoría de los equipos tienen algo de la primera, una opinión sobre la segunda, y nada de la tercera.

## Casi todo esto ya existe

Aquí está la parte que conviene decir sin adornos, porque es la que convierte esto de un proyecto en una tarde: **los conectores ya son estándar.** Repositorio, gestor de tickets, documentación, chat, las bases de datos habituales — existen, los mantienen los propios fabricantes, e instalar uno es configuración, no desarrollo. MCP es el estándar de fontanería del momento, y lo que lo hace importante no es la elegancia: es que ya no tienes que construir la tubería.

Lo que sigue exigiendo trabajo de verdad es la cola, y es una cola real:

- **El sistema interno para el que nadie escribió conector.** La herramienta de casa, el servicio heredado, esa cosa con una API que solo usáis vosotros. [Yo construí uno de estos para Bitbucket](/es/blog/mcp-server-bitbucket) porque el oficial no existía y los de la comunidad se quedaban en operaciones básicas de repositorio.
- **El estándar que no cumple vuestros requisitos.** Existe, pero no acota permisos como necesita cumplimiento, o no deja rastro de auditoría, o expondría un campo que legalmente no puede salir.

Esa es la división honesta. Si vuestra respuesta a "¿qué estamos pegando a mano?" es GitHub, Jira, Confluence o Slack, no tenéis un problema de desarrollo — tenéis una solicitud de permisos que nadie ha presentado. El trabajo a medida es real, pero es la excepción, y tratar todo esto como un proyecto de construcción es la forma más fiable de no empezarlo nunca.

### Si eres quien administra la suscripción

Esta parte es para ti en concreto, porque la decisión es tuya y casi nadie te ha dicho que sea una decisión.

Compraste licencias. Lo que no has hecho —porque nadie te lo ha planteado— es decidir hasta dónde llegan esas licencias. Mientras nadie lo decida, cada persona con acceso está trasvasando contexto a mano entre sistemas a los que ya entra por su cuenta, y la herramienta se está evaluando con una fracción de lo que hace. Si la adopción parece decepcionante, esta es una causa más probable que el equipo.

Tres cosas que conviene saber antes de que la solicitud llegue a tu mesa, porque la respuesta por defecto es "no" y nadie la revisa después:

- **Un conector no es un proveedor nuevo.** Conectar el agente a vuestro repositorio no le entrega el código a nadie nuevo: deja que una herramienta que ya pagáis lea un sistema que vuestra gente ya lee. La conversación de riesgo que merece la pena es sobre alcance y retención, no sobre si permitirlo o no. (La pregunta hermana —*qué* herramienta te dejan usar de entrada— [tiene su propia discusión](/es/blog/the-tool-youre-allowed-to-use).)
- **Leer y escribir son dos decisiones, y conviene concederlas por separado.** Casi todo el valor está en leer. Casi todo el riesgo está en escribir. Se piden juntas porque es un solo formulario; puedes decir que sí a la mitad y revisarlo en un mes.
- **"El agente tiene mis accesos" es la frase que hay que interrogar.** ¿Los accesos de quién, acotados a qué, y —la parte que se salta siempre— qué puede hacer por defecto frente a qué se detiene y pide aprobación? Una herramienta que abre una pull request para que la revise una persona y otra que empuja a la rama principal son la misma integración con dos ajustes muy distintos, y esa diferencia es una elección de configuración que alguien tiene que tomar a propósito.

Nada de esto es caro. Simplemente no tiene dueño, y las decisiones sin dueño acaban en la opción más restrictiva, que es la que nadie tiene que defender.

Hay una imagen especular de todo esto sobre la que he escrito aparte: en vez de conectar agentes a vuestros sistemas, [meter tu aplicación dentro del agente que tus usuarios ya usan](/es/blog/bring-your-app-to-the-agent). La misma fontanería, en dirección contraria.

## Lo que cuesta conectarlo

Un agente que puede escribir en sistemas reales es un agente que puede escribir en sistemas reales estando equivocado. No es motivo para dejarlo desconectado, pero sí significa que las preguntas cambian en cuanto enchufas algo:

- **Los permisos dejan de ser teóricos.** "El agente tiene mis accesos" es una frase que conviene leer dos veces, sobre todo si tus accesos son amplios. Y es solo la mitad del ajuste: la otra mitad es qué puede hacer *por defecto* frente a qué tiene que detenerse a preguntar. Abrir una pull request, escribir un comentario y mergear a la rama principal son tres respuestas muy distintas al mismo conector, y el valor por defecto sensato es que todo lo irreversible espere a una persona.
- **Todo lo que lee es potencialmente una instrucción.** Un ticket, un documento, un comentario de fuera de la organización: el texto que ingiere puede intentar dirigirlo. Leer mucho y escribir mucho son niveles de riesgo distintos, y es razonable concederlos a velocidades distintas.
- **El contexto interno llega más lejos.** Los agentes son [notablemente malos sabiendo qué parte de su contexto no era para el lector](/es/blog/internal-context-leakage). Cuantas más fuentes conectas, más hay que se pueda escapar.

Ninguna de las tres es un argumento a favor de la caja de texto. Son argumentos para hacerlo a propósito, en el orden que pone primero los conectores de solo lectura. Si quieres el inventario completo de lo que cambia en cuanto lo que has construido es real, ahí está [el mapa](/es/blog/what-you-still-need-to-know-to-ship), donde esto tiene ya una categoría propia, justo detrás del techo.

## Cuatro preguntas para saber dónde estás

Baratas, y todavía no he visto a un equipo responderlas sin que caiga algo:

1. **¿Qué pegáis en el chat todas las veces?** El mismo contexto, un esquema, un ticket, las convenciones. Todo lo que se repite es un cableado que estáis haciendo con las manos.
2. **¿En qué sistemas vive vuestro trabajo de verdad?** Listadlos. Repositorio, tickets, documentación, hojas de cálculo, base de datos.
3. **¿A cuántos de esos llega el agente por su cuenta?** En la mayoría de los equipos, con sinceridad: a ninguno.
4. **¿Quién autoriza el acceso al que más importa, y cuánto tarda?** Si no lo sabéis, esa es la primera tarea — y no es técnica.

La última es la que atasca a los equipos, y es la que no tiene nada que ver con la IA.

## La prueba

Así es como yo comprobaría si un agente forma parte de verdad de cómo trabaja un equipo, o es una demo sobre la que la gente está siendo educada.

**Si mañana dejara de funcionar el portapapeles, ¿cuánto sobreviviría?**

Si la respuesta es "nada", la herramienta nunca estuvo integrada. Lo estaba una persona.

---

*Continuación de los tres artículos sobre lo que exige de verdad construir software con agentes: [el mapa](/es/blog/what-you-still-need-to-know-to-ship), [empezar desde cero](/es/blog/if-youre-starting-from-zero) y [venir de ingeniería](/es/blog/if-you-came-from-engineering). Si prefieres trabajarlo con tu propio equipo — incluido cuál de vuestros sistemas ya tiene conector y cuál no — [eso es lo que hago](/es/mentoring).*
