---
title: "Tu agente no sabe qué ha pasado ya"
description: "Los agentes planifican alrededor de cosas que nunca ocurrieron e inventan dependencias entre piezas que no dependen entre sí. Parece falta de reloj, así que lo medí: 572 respuestas, seis modelos, dos dominios. La fecha no cambia nada, y uno de los fallos empeora en los modelos más potentes."
pubDate: 2026-08-13
tags: ["IA", "Agentes", "Evaluación", "Contexto", "Investigación"]
lang: es
translationKey: what-has-already-happened
heroImage: "/blog/what-has-already-happened.png"
---
Llevo unos meses trabajando a diario con agentes de código en un proyecto con mucho *estado*: un curso universitario que tengo que grabar en un estudio cuatro días seguidos, con guiones, tiempos y una fecha de entrega antes. Y había un tipo de sugerencia que volvía una y otra vez: **consejos de orden que no se sostenían.**

Deja esta pieza para el final, porque depende de las demás. Graba estas dos seguidas, porque la segunda retoma la primera. Suena razonable, y es falso: aquello de lo que supuestamente dependía estaba terminado y congelado desde meses antes. El agente razonaba sobre mi proyecto sin una línea firme entre lo que ya estaba resuelto y lo que no.

El diagnóstico obvio es que no sabe cuándo es *ahora*. Volveré a eso, porque se puede medir y es falso.

## La anécdota que tuve que tirar

Me puse a buscar el ejemplo más flagrante para abrir. Encontré uno precioso: un fichero de estado que el agente venía manteniendo decía

```
| Rodadas y buenas   | 2  |
| Rodadas, a repetir | 3  |
| Pendientes         | 63 |
```

No se había grabado nada. Ni un fotograma: la reserva del estudio estaba a semanas vista. Lo que existía eran lecturas de práctica cronometradas en mi salón, yo leyendo un guion en voz alta con un cronómetro para ver si cabía en diez minutos.

Párrafo de apertura perfecto. Solo que, al escarbar en cómo había llegado el fichero a ese estado, dejó de ser prueba de nada.

El vocabulario venía contaminado por los dos lados. Una sesión estaba preparando material para el rodaje de verdad y mezcló los dos estados. Y yo, más de una vez, había llamado «grabación» a mis propias prácticas, en conversaciones sobre medir tiempos donde la distinción daba igual. Dejó de dar igual en el momento en que un documento quedó escrito en ese tiempo verbal: todas las sesiones posteriores heredaron un fichero de estado que hablaba de tomas. Lo corregí de viva voz más de una vez y volvía, porque el documento seguía ahí.

O sea que no es un modelo inventándose un estado de la nada. Son meses de deriva en un vocabulario compartido, con autoría por ambas partes, la mía incluida.

**Ese es el problema de cualquier anécdota sacada de tu propio proyecto: yo estoy dentro del bucle.** Mis palabras entran en el contexto, mis correcciones lo modifican, no hay condición de control, y el ejemplo que eligiera lo habría elegido *porque* era llamativo, para luego explicarlo a posteriori con la explicación que ya me creía.

Una corazonada no es un caso. Así que, en lugar de publicar la corazonada, construí algo en lo que sí pudiera equivocarme.

## El experimento

Sacar la *forma* de lo que venía notando de mi proyecto y llevarla a un sitio donde no tengo historia. Material fijo, una pregunta, una variable cada vez, y suficientes repeticiones como para no poder elegir a dedo.

Le das a un modelo ~1,7 KB de hechos del proyecto y le preguntas: *¿en qué orden conviene hacer esto, y hay restricciones de orden que respetar?* El material es mi proyecto real, ambigüedades incluidas:

- Sesenta y ocho píldoras de vídeo que grabar, una ventana de estudio reservada para cuatro días seguidos y una fecha de entrega antes.
- Guiones **cerrados y congelados desde julio**: el texto no va a cambiar.
- Una tabla de tiempos medidos y un recuento de estado: *2 buenas / 3 a repetir / 63 pendientes*.
- Y una trampa. Dos piezas parecen dependientes —la cuarta retoma un cálculo que se escribe durante la tercera— pero el guion de la cuarta dice, con todas las letras, **«te las reescribo»**. Es autocontenida. No hay ninguna restricción de orden.

Después varías el contexto en una o dos líneas:

| | añadido al material |
|---|---|
| **A** | nada |
| **B** | «hoy es 11 de agosto de 2026» |
| **C** | «los tiempos medidos son lecturas de práctica, no tomas de estudio; del estudio no ha salido nada todavía» |
| **D** | ambas |
| **E** | ambas, más «no inventes restricciones de orden» |

Seis modelos —`gpt-4o`, `gpt-4.1-mini`, `gpt-5.4-mini`, `claude-haiku-4.5`, `claude-sonnet-4.6` y `claude-opus-5`— y luego todo otra vez en un dominio sin relación: una release de doce servicios, con la ventana de despliegue en producción por delante y ensayos en staging por detrás. Misma estructura lógica, ninguna de las mismas palabras. Su trampa es un servicio que lee una tabla que migra otro servicio, donde el runbook dice que la migración es idempotente y que el servicio «arranca contra el esquema viejo o el nuevo, sin tocar nada».

**572 respuestas puntuadas.** La puntuación la hace un juez LLM, ciego a la condición y obligado a citar literalmente la frase que justifica cada marca. Antes de fiarme codifiqué a mano una muestra y contrasté los dos jueces candidatos contra mi codificación: uno coincidió en 30/32 y el otro en 23/32, y ocho de los nueve errores del perdedor eran falsos positivos, marcando fallo en respuestas que decían lo contrario. Así que hay un solo juez, y es el validado.

## Fallo 1: una precedencia que el documento niega explícitamente

| afirma la dependencia igualmente | dominio curso | dominio despliegue |
|---|---|---|
| `gpt-4.1-mini` | 100 % | 100 % |
| `gpt-4o` | 100 % | 100 % |
| `claude-haiku-4.5` | 100 % | 96 % |
| `gpt-5.4-mini` | 100 % | 86 % |
| `claude-sonnet-4.6` | 100 % | 100 % |
| **`claude-opus-5`** | **52 %** | **10 %** |

Cinco de seis modelos dicen que B tiene que ir después de A. En el dominio del curso son **92 de 92 respuestas**: no una tendencia, un techo.

Y la exención no está enterrada en un anexo. Está en la *misma frase* que la dependencia. Aquí va `gpt-4o`, sin editar, con tres líneas de diferencia:

> `auth-db-migrator` — Prepárate el esquema que utiliza `auth-api`. **Es idempotente y compatible hacia atrás.**
>
> […]
>
> **Desplegar siempre el `auth-db-migrator` antes de `auth-api`**, ya que ajusta el esquema.

Leyó la exención, la escribió y razonó como si no existiera. No faltaba nada en el contexto: el modelo **reprodujo** la información y luego la ignoró. Lo que se pierde no es el hecho, es su *alcance*. La relación («B retoma algo de A») sobrevive; la cláusula que anula la relación, no.

La forma del resultado importa tanto como el tamaño. **Esto no es un gradiente, es un umbral.** `gpt-5.4-mini` y `claude-sonnet-4.6` son modelos potentes y recientes, y fallan exactamente igual de a menudo que el más pequeño del conjunto. Un modelo de seis está en otro régimen; los otros cinco son indistinguibles entre sí.

## Fallo 2: una premisa que caducó en julio

Los dos materiales contienen algo que *invita* a una convención del corpus de entrenamiento. En el curso, una apertura que describe el curso entero, y en producción audiovisual la intro se graba al final, porque tiene que cuadrar con lo que acabaste haciendo. En la release, un gateway que publica el manifiesto de todo, y en despliegues el gateway va el último, para que no anuncie servicios que no están arriba.

Las dos son prácticas reales y sensatas. Y las dos se apoyan en una condición que este material elimina explícitamente: **los guiones se congelaron en julio y los artefactos se firmaron en julio.** Nada hecho después puede cambiar lo que dicen. La razón para dejarlos al final caducó antes de que la ventana llegara a abrirse.

| lo deja al final *porque depende del resto* | curso | despliegue |
|---|---|---|
| cinco modelos menores | 36 % | 69 % |
| **`claude-opus-5`** | **60 %** | **98 %** |

Este es el fallo que me parece más interesante, porque es temporal en el sentido más puro: el modelo recupera una regla sobre *cuándo* hacer algo y no comprueba si la precondición de la regla sigue en pie. Es el mismo movimiento que recomendarle a alguien reservar con antelación para un viaje que ya hizo.

El modelo que lee la exención está entre los *peores* en esto: 25 de 25 en el dominio de despliegue, el número más alto del estudio.

Quiero ir con cuidado, porque hay una historia redonda disponible y los datos no la sostienen del todo. La historia redonda es «el fallo crece con la capacidad». No de forma monótona: en despliegue, `gpt-4.1-mini` pica entre el 79 % y el 90 % de las veces mientras `gpt-4o` pica entre el 20 % y el 40 %. Lo que los datos sí sostienen es más estrecho y sigue siendo útil: **ser un modelo mejor no ayuda aquí.** Los tres modelos más potentes del conjunto fallan esto entre el 92 % y el 100 % en el dominio de despliegue. Si tu plan es «esperar a un modelo mejor», esta es la parte que seguirá esperando.

Mi lectura, ofrecida como interpretación y no como medición: los dos fallos tiran en direcciones opuestas porque uno es de leer y el otro de producir. Ignorar la exención es leer de menos. Aplazar la apertura es producir de más: el modelo no se limita a responder, aporta una *razón*, y una razón fluida y plausible es exactamente la forma que tiene una restricción de orden inventada.

## Fallo 3: qué ha ocurrido y qué no

El recuento de estado —*2 buenas / 3 a repetir*— es genuinamente ambiguo en la condición A. Leerlo como producción terminada no es ninguna locura: el material no lo zanja. Así que la condición C lo zanja: *son ensayos, del estudio no ha salido nada todavía.*

Lo que compra esa línea depende por completo de qué modelo la lea.

**`claude-opus-5` actúa en consecuencia.** El error de estado baja del 92 % al 20 % en el dominio del curso (p=3,7·10⁻⁷) y del 20 % al 0 % en despliegue. Además lo *dice*: pasa del 12 % al 100 % y del 16 % al 96 %.

**Los modelos menores, en su mayoría, solo lo repiten.** `gpt-5.4-mini` pasa de no mencionar nunca la procedencia a mencionarla entre el 40 % y el 48 % de las veces; `claude-sonnet-4.6`, del 0 % al 62 % en uno de los dominios. Y luego planifican sobre 63 pendientes igualmente.

**Y a tres de ellos les empeoró la planificación.** En despliegue, añadir la aclaración **sube** el error de estado en `claude-haiku-4.5` (12 % → 32 %), `claude-sonnet-4.6` (12 % → 25 %) y `gpt-5.4-mini` (12 % → 20 %). Son números pequeños, sin significación individual, y no voy a reclamar ningún mecanismo. Pero la dirección es la contraria a «gratis»: **darle a un modelo una salvedad le da algo nuevo de lo que hablar, y hablar de ello no es usarlo.**

Esa es la parte que me habría perdido probando un solo modelo. La misma frase de contexto es un arreglo grande, un no-op o una molestia leve según quién la lea.

## ¿Y la excepción es mejor o peor?

Un modelo se comporta distinto de los otros cinco en todas las medidas, lo que invita a la pregunta: ¿`claude-opus-5` es excepcionalmente bueno en esto, o excepcionalmente malo? Es genuinamente las dos cosas, y creo que es una sola propiedad vista por sus dos caras.

Pon el error de estado en fila, por condición:

| tasa de error | sin la aclaración | con ella |
|---|---|---|
| los cinco modelos menores | 0–70 % | 0–56 % |
| **`claude-opus-5`** | **92 % / 20 % — el peor de su columna** | **20 % / 0 % — el mejor** |

En los dos dominios es el *peor* de los seis cuando el material deja el estado ambiguo, y el *mejor* en cuanto el material lo zanja. Sin un hecho que lo restrinja, construye la lectura más natural —esos números son producción terminada— y planifica sobre ella con convicción. Con el hecho delante, actualiza y planifica sobre el nuevo. Los modelos menores se quedan en un intermedio mediocre en los dos casos, porque se comprometen menos con cualquier interpretación.

Eso reconcilia además el resultado del gateway, que si no parece contradictorio. Lo que este modelo usa de forma fiable es lo **explícito**: «te las reescribo», «son ensayos». Lo que exige derivar la consecuencia en dos pasos —*congelado desde julio*, por tanto nada posterior puede invalidar la apertura— no lo usa, y ahí gana la convención del corpus. Gana con más fuerza, de hecho, precisamente porque es el modelo que más elabora.

Ofrecido como interpretación, no como medición. Pero la consecuencia práctica va al contrario de la intuición: **con un modelo más potente, la calidad de tu documento importa más, no menos.** Un modelo pequeño te da algo mediocre casi con independencia de lo que escribieras. Uno grande te devuelve lo que le diste — buena noticia si escribes con cuidado, y mala si el hecho que sostiene todo solo está insinuado.

## No es el reloj

Lo que me devuelve al diagnóstico obvio. Todos los fallos de arriba van de tiempo —precedencia, caducidad, qué ha ocurrido—, así que el arreglo natural es decirle al modelo cuándo es *ahora*. Es además la mitigación que todas las herramientas incorporan por defecto: tu agente casi seguro tiene la fecha de hoy estampada en su prompt de sistema ahora mismo. El mío la tuvo todo el tiempo.

Añadir la fecha explícitamente no movió nada. Ninguna de las cuatro medidas (todas con p > 0,5).

Tampoco las otras dos cosas que probé. Declarar qué son los números no hace que el modelo lea la cláusula del runbook —otro fallo, sin transferencia—. Y la condición E añade, en lenguaje llano, *no inventes restricciones de orden*: sigue en el **96 %**. Puedes escribir la prohibición en el prompt y verla incumplida en diecinueve de cada veinte ejecuciones.

Así que el déficit no es el timestamp. Un calendario te dice dónde cae *ahora*; no te dice nada sobre cuáles de tus hechos están ya fijados, qué relaciones siguen valiendo y a qué regla le caducó la precondición el mes pasado. Esa estructura vive en el documento, y es la parte que no sobrevive a la lectura.

## Qué haría yo

**No escribas una exención: escribe la frase que quieres decir.** Es lo mejor respaldado de todo esto, y es un hábito de documentación, no un truco de prompt. Si una restricción no aplica, no la enuncies para exceptuarla después: la excepción pierde entre el 96 % y el 100 % de las veces en cinco de seis modelos. «B retoma el cálculo de A, pero lo reescribe» se convierte en «B es autocontenida».

**Di qué está congelado, no solo qué está hecho.** El fallo 2 ocurre porque una regla genérica de «esto va al final» le gana a un hecho específico de mi proyecto. «Guiones cerrados desde julio» se lee, aparentemente, como historia; «los guiones no pueden cambiar, así que nada posterior puede invalidar la apertura» enuncia la consecuencia, que es contra lo que había que comprobar la regla.

**Haz que la procedencia sea inseparable del valor.** No una nota en otro sitio diciendo que los números son ensayos, sino una marca que no se pueda copiar dejándosela atrás. En mi proyecto lo que funcionó fue escribir `8:25 †`, donde la daga significa «esta desviación no significa nada», de modo que el número no puede viajar a otra tabla sin su salvedad. Alcance: esto es *diseño de documento*. Declararlo en un prompt solo cambia de forma fiable lo que el modelo repite.

**Deja de esperar que la fecha trabaje**, y no añadas salvedades dando por hecho que son gratis. Las dos son baratas de inyectar y ninguna hace lo que crees.

**Vigila tu propio vocabulario.** La única lección de la anécdota que tiré, y sobrevive precisamente porque no es sobre el modelo: yo llamaba «grabación» a las prácticas cuando daba igual, y dejó de dar igual en cuanto quedó escrito. En un proyecto largo, las palabras flojas acaban commiteadas en un fichero, y lo que está en el fichero pasa a ser el estado del mundo.

## Límites

Dos dominios no son una muestra de dominios, y los dos son *trabajo de ordenar con una ventana por delante*; tareas de diagnóstico o de análisis podrían comportarse de otra forma. Son dieciséis comparaciones, así que con corrección de Bonferroni lo que llamaría confirmado es el resultado de la exención y los dos efectos de procedencia en `claude-opus-5`; el empeoramiento en tres modelos menores y el efecto de la prohibición explícita son indicios, etiquetados como tales arriba. El juez comparte familia de modelos con dos de los sujetos, cosa que arreglaría con un tercer juez la próxima vez: el sesgo favorecería a esa familia, y salió la peor en el fallo 2, así que la dirección es segura.

Y una salvedad de la que este artículo es un ejemplo: todo está medido en **agosto de 2026** y contra esos seis modelos. El fallo que llevo todo el artículo describiendo es el de una afirmación que sobrevive a las condiciones bajo las que se escribió. La mía también lo hará.

---

*Los tres fallos piden arreglos distintos, y por eso creo que merece la pena separarlos. El de leer de menos se arregla escribiendo mejores documentos. El de razonar sobre una premisa caducada no lo pude arreglar de ninguna manera —ni con la fecha, ni con una declaración, ni con una prohibición directa— y es el que peor se les dio a los modelos más potentes.*
