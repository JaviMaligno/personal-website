---
title: "Demos que impresionan vs demos que funcionan"
description: "Dos filosofías de la demo a cliente — espectáculo mockeado vs prueba de concepto funcional — y por qué, con IA, la más vistosa esconde justo lo que importa: latencia y no-determinismo."
pubDate: 2026-06-17
tags: ["IA", "Producto", "Ingeniería", "Demos"]
lang: es
translationKey: demos-that-wow-vs-demos-that-work
heroImage: "/blog/demos-that-wow-vs-demos-that-work.png"
---

He trabajado en dos equipos con filosofías opuestas sobre cómo hacer una demo a un cliente, y todavía dudo sobre cuál tiene razón.

Uno construye demos para **impacto**. Todo está mockeado: las pantallas pulidas, el flujo coreografiado y el resultado que aparece en pantalla es la mejor versión posible de sí mismo. El backend no está haciendo el trabajo de verdad — y, sobre todo, la IA no se está llamando realmente. Es una película preciosa del producto.

El otro construye **pruebas de concepto funcionales**. Lo máximo posible es real y está conectado — servicios reales, llamadas reales al modelo, datos reales — y luego se itera encima. La primera versión es más tosca y menos coreografiada, pero lo que estás viendo está ocurriendo de verdad.

Ambas "funcionan" en el sentido de que ambas pueden ganarse a una sala. Solo que optimizan cosas distintas, y la distancia entre ellas se ensancha mucho en cuanto aparece la IA.

## A favor del mock

Es fácil ser esnob con las demos mockeadas, así que déjame defenderlas primero, porque las razones son buenas.

Un mock es **rápido**. No te bloquea la infraestructura, el acceso al modelo, los pipelines de datos ni las diez cosas poco glamurosas que tienen que existir antes de que un flujo real funcione de principio a fin. Puedes demostrar un producto que aún no existe.

Un mock es **controlado**. Las demos fallan de formas tontas y memorables — un timeout, un rate limit, un modelo teniendo un mal día delante de la única persona a la que necesitabas impresionar. Un mock elimina esa varianza. La historia que ensayaste es la que ven.

Y un mock vende la **visión**, no el estado actual. Al principio, lo que validas en realidad es el deseo: ¿la gente *quiere* esto? Un mock nítido responde a esa pregunta sin tener que construir la cosa antes. Para un stakeholder no técnico que decide si financia la siguiente fase, un mock pulido puede ser exactamente el artefacto correcto.

Nada de eso es deshonesto. Es una estrategia legítima con ventajas reales.

## A favor de la PoC funcional

La PoC funcional renuncia a algo de pulido y a mucho control a cambio de una cosa: **lo que enseñas es verdad**.

Y esa verdad compone. Una PoC funcional no se tira tras la reunión — es el primer commit del producto. Iteras sobre ella en vez de reconstruir desde un slide. El feedback que recibes es feedback real, porque la gente reacciona a un comportamiento real, no a tu storyboard del mejor caso. Y las partes difíciles afloran *ahora*, cuando son baratas, en vez de después de firmar un contrato con el plazo ya fijado.

Lo he vivido de primera mano. En una demo en vivo, alguien le preguntó al asistente por errores que habían ocurrido, y su respuesta mezcló lo que había ido *bien* con lo que había ido mal. Quien lo veía reaccionó al instante: esto tiene que ser más conciso. En la misma sesión, alguien preguntó si era capaz de hacer cierta cosa que —por una restricción interna— simplemente no podía. Dos piezas concretas de feedback y dos tickets nuevos, en lo que dura una demo. Con un mock ni siquiera puedes intentar esas preguntas: el guion responde lo que se le guionizó, y no se está probando nada real.

Tarda más en llegar al primer wow. Pero nunca tiene que desdecirse de nada.

## Dónde ensancha la IA la distancia

Para el software normal, la distancia entre un mock y lo real es sobre todo **pulido**: la versión real será un poco más lenta, algo menos bonita, algún caso borde se portará mal. Manejable.

Con IA, la distancia es de **sustancia** — porque un mock esconde las dos propiedades que definen cómo se va a sentir el producto:

- **Latencia.** En un mock, la respuesta aparece al instante (o tras un spinner guionizado y elegante). En la realidad, la llamada al modelo tarda — a veces un segundo, a veces diez, a veces más si razona o encadena herramientas. "Instantáneo" es lo más fácil de fingir y de lo más difícil de entregar. Ya [conté antes](/es/blog/ag-ui-third-protocol) una demo en la que el arreglo real no era de UI, sino bajar el esfuerzo de razonamiento del modelo para que respondiera en ~1,5s en vez de 10–20s. Eso solo lo descubres cuando el modelo está de verdad en el bucle.
- **No-determinismo.** Un mock siempre devuelve la respuesta perfecta, porque alguien la escribió. El modelo real devuelve *una* respuesta — normalmente buena, a veces incorrecta, de vez en cuando incorrecta con seguridad, y distinta cada vez. El mock demuestra una certeza que el producto no tiene. Todo eso de lo que insisto sobre [evaluar las salidas de un LLM](/es/blog/llm-as-judge-three-decisions) existe precisamente porque los resultados reales varían y hay que medir esa varianza. Un mock la hace desaparecer.

Así que cuando demuestras IA con un mock, no estás solo limando asperezas. Estás vendiendo los dos riesgos que el proyecto realmente tiene. El cliente se enamora de un asistente instantáneo y siempre correcto, y luego el equipo tiene que construir algo que, por defecto, no es ninguna de las dos cosas. Esa brecha no se cierra sola — alguien la paga después, normalmente en confianza erosionada durante el desarrollo.

## Entonces, ¿cuál?

Sinceramente, depende de qué intentes aprender de la demo:

- Si validas **deseo** — "¿querría alguien esto?" — y hablas con gente que piensa en resultados, no en arquitecturas, un mock suele ser la herramienta eficiente y correcta. No montes un backend para responder a una pregunta de marketing.
- Si validas **viabilidad** — "¿podemos construir esto de verdad, y se sentirá bien?" — un mock responde de forma convincente a la pregunta equivocada. Ahí es donde quieres lo real conectado.

Mi sesgo se inclina hacia la PoC funcional, y se ha inclinado más cuanto más trabajo con IA — porque con IA el riesgo vive justo en lo que el mock tapa. Una PoC funcional tampoco tiene por qué ser fea ni cara de montar: la [demo de AG-UI](/es/blog/ag-ui-third-protocol) que armé hace poco es real de principio a fin — modelo real, latencia real, widgets renderizados de verdad — y son unas cien líneas. La suposición de "lo real es demasiado caro para demostrarlo" suele ser menos cierta de lo que parece.

Pero lo sostengo con suavidad. Un mock que vende honestamente una visión, seguido de un equipo que cierra la brecha, es una forma perfectamente válida de construir una empresa. El modo de fallo no es mockear — es mockear las partes arriesgadas y luego confiar en silencio en que la realidad cooperará.

## O monta las dos

No tiene por qué ser binario. He trabajado en proyectos que corrían las dos a la vez: un **camino mockeado** para garantizar un recorrido end-to-end limpio — la historia que siempre puedes contar sin que algo se rompa a mitad de reunión — y el **sistema real al lado**, para probarlo en vivo con distintos casos. El mock quita riesgo a la narrativa; la parte real invita a las preguntas difíciles. Consigues el wow controlado y el feedback honesto en la misma sesión, siempre que todos en la sala sepan qué mitad es cuál.

## La pregunta que dejaría abierta

Quizá la pregunta de verdad no es "mock o funcional". Es **qué momento estás optimizando**: la firma al final de la demo, o la confianza al final del primer sprint. A veces apuntan en la misma dirección. Con IA, más a menudo de lo que me gustaría, no.

¿Cómo hace las demos tu equipo — y te ha mordido alguna vez la brecha entre la demo y lo que acabaste entregando? Me gustaría de verdad leerlo.

---

*Relacionado: [Cuando el chat construye su propia interfaz](/es/blog/ag-ui-third-protocol) (una demo funcional, de principio a fin) y [LLM-as-Judge son tres decisiones](/es/blog/llm-as-judge-three-decisions) (sobre medir la varianza que un mock esconde).*
