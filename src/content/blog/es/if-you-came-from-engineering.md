---
title: "Si vienes de la ingeniería"
description: "Ya sabes comprobar trabajo a escala: tests, CI, pipelines. Lo único es que no estás aplicando nada de eso al agente. Estás comprobando lo que produce a ojo, justo lo que llevas toda una carrera aprendiendo que no funciona."
pubDate: 2026-08-14
tags: ["IA", "Vibe Coding", "Software", "Ingeniería", "Mentoría"]
lang: es
translationKey: if-you-came-from-engineering
heroImage: "/blog/if-you-came-from-engineering-es.png"
---

Las personas a las que más les cuesta trabajar con agentes no son las que no los entienden. En mi experiencia, son las que mejor entienden el software.

Revisan cada línea. Dan instrucciones mucho más precisas de lo que exige el trabajo. Dividen el trabajo en piezas lo bastante pequeñas como para inspeccionarlas y después las inspeccionan todas. Y cuando preguntas por qué, la respuesta es alguna versión de *porque lleva mi nombre* — que es exactamente lo correcto y era exactamente lo correcto hace cinco años. No quince. Estos hábitos son recientes, eran correctos cuando los adquirimos y se quedaron anticuados más rápido que cualquier otra cosa que hayamos tenido que desaprender.

Me incluyo. Yo hacía todo esto y todavía hay días en los que me descubro haciéndolo.

Es la imagen especular de [lo que le ocurre a quien empieza desde cero](/es/blog/if-youre-starting-from-zero). Ellos delegan por encima de su nivel y entregan lo que no pueden comprobar. Nosotros delegamos *por debajo* del nuestro y nos negamos a entregar lo que sí podríamos.

Los dos acaban yendo despacio, pero siguiendo curvas distintas. La suya es rápida hasta que deja de serlo: avanza y avanza, hasta que algo se rompe sin que tengan forma de diagnosticarlo y todo se detiene. La nuestra nunca llega a ser rápida: no hay precipicio, solo un impuesto constante que pagamos cada día.

Y solo una de las dos parece diligencia, que es lo que la hace más difícil de corregir. Nadie va a llevarte aparte para sugerirte que revises menos.

## Lo que ya sabes y no estás usando

Esto es lo que hace tan extraño este fallo en particular: resolviste este problema hace años.

No revisas el trabajo de un compañero leyendo cada línea que escribió. Tienes tests. Tienes CI. Tienes un pipeline que dice que no antes de que tenga que hacerlo una persona. Llevas toda una carrera aprendiendo que verificar a ojo no escala y construyendo la maquinaria que lo sustituyó.

Y entonces un agente produce un cambio y tú lo lees línea por línea.

Esa es la brecha: **aplicar un método de verificación que ya sabemos que no basta al único colaborador que produce trabajo más rápido de lo que podría hacerlo cualquier persona.** Los mecanismos a los que recurriríamos por instinto con un compañero están ahí mismo.

En la práctica, esto es lo que le doy yo a un agente para no tener que comprobar a mano:

- **Tests**, para que detrás de «terminado» haya algo.
- **CI**, para que la comprobación ocurra tanto si me acuerdo de ejecutarla como si no.
- **Skills basadas en especificaciones**, para que lo que construye se compruebe contra lo que se pidió y no contra mi humor de ese día.
- **Herramientas de navegador** — yo uso Claude en Chrome — para que pueda manejar la aplicación en marcha y volver con capturas que enseñen que funciona, en vez de decirme que funciona.

Lo último es lo que más se acerca a un desbloqueo de verdad. «Está hecho» y «aquí tienes una captura haciendo lo que pediste» son categorías distintas de afirmación, y producir la segunda no le cuesta nada al agente.

### Pero los tests los escribe el agente

Esta es la primera objeción que plantea todo el mundo y merece una respuesta directa: si los tests vienen de quien escribió el código, ¿qué has ganado exactamente?

Has ganado que **el test ha pasado de ser algo que escribes en código a algo que describes con palabras.** Sigues especificando el comportamiento; solo que lo dices en una frase en vez de en un fixture. «Un usuario que no ha iniciado sesión no recibe nada de este endpoint» es una especificación que puedes escribir, leer y discutir sin tocar un framework de testing, y es el ancla contra la que se comprueban tanto el código como el test.

Por eso tampoco supone la amenaza que parece un test escrito para pasar sin más. Cuando lo que pediste está por escrito, un test que no comprueba nada se detecta en segundos. El fallo no consiste en que se te cuele un test falso, sino en que nunca dijiste qué debía hacer aquello.

El residuo que se queda la persona no es la inspección. Es **la sospecha**: notar que algo huele mal, que un número cambió cuando no debía, que el arreglo llegó demasiado rápido. Te quedas el juicio. Delegas el mirar.

### Cuándo sigue teniendo sentido leer el código

La mayoría de las veces no lo tiene. Pero «la mayoría» no es «nunca», y la analogía que me resulta útil es el ensamblador.

En algún momento dejamos de leer lo que producía el compilador. No porque se volviera infalible, sino porque comprobarlo dejó de ser el mejor uso de la atención de nadie. Y aun así sigue habiendo dominios en los que se baja a ese nivel: cuando algo es lo bastante crítico para que el coste de equivocarse justifique el tiempo, o cuando hay una cosa concreta que alguien necesita ver con sus propios ojos.

Aquí pasa lo mismo. Los pagos son el ejemplo evidente. Cualquier cosa en la que un error sutil resulte caro y silencioso, cualquier cosa sometida a regulación, cualquier cosa para la que te costaría escribir un test. Esas se han ganado una lectura.

Lo que no se la ha ganado es *entender*. Si quieres saber cómo funciona algo, pedirle al agente que te lo explique es más rápido y mejor que leerlo tú: puede contarte el porqué, algo que el código no puede hacer.

Y hay un movimiento que le gana tanto a leer como a no leer: **hacer que haya menos que leer.** Un cambio que toca seis ficheros porque nadie dijo dónde vivía el código es irrevisable en la práctica, así que se ojea y se mergea. La misma petición, señalando la zona que toca y con una instrucción permanente de mantener los cambios mínimos, vuelve con la mitad de tamaño y se puede leer de verdad en un minuto. Eso es tender vías otra vez: no estás decidiendo si inspeccionas, estás decidiendo cuánto hay que inspeccionar.

Conviene ser honesto sobre el límite, porque es lo único que los tests no cubren: un cambio parásito que no rompe nada. Un valor de configuración alterado sin motivo pasa todos los tests que tengas, y aparece tres semanas después en producción. Ese es justo el caso que caza un diff pequeño y no caza un pipeline en verde — que es un argumento para mantener los diffs pequeños, no para leer los grandes.

## La precisión y la parte que merece la pena conservar

El primer síntoma de delegar por debajo de tu nivel es especificar de más.

Escribes la instrucción como escribirías un ticket para alguien junior: nombras cada fichero, ordenas cada paso, detallas cada caso límite. Funciona. También significa que tú hiciste la mayor parte del razonamiento y que el agente aportó mecanografía.

Pero «deja que decida el cómo» es demasiado tajante y no me lo creo. Si tienes una opinión sobre el enfoque, esa opinión vale algo: es precisamente la razón por la que [tener criterio ocupa lo más alto de la escala](/es/blog/what-you-still-need-to-know-to-ship) en vez de ser un extra agradable. La arquitectura, la forma de la solución y a veces el stack: esas son cosas por las que te corresponde discutir.

La distinción importante está entre el **cómo conceptual** y la **secuencia de pasos**. Qué enfoque, qué equilibrio, qué stack: trae tu opinión, te la has ganado. Qué fichero abrir primero, en qué orden y con qué nombre: ser específico ahí te cuesta justo la contribución por la que estabas pagando.

Y el encuadre más útil no trata de quién decide. Es que **puedes discutir con el agente como con un igual.** Pregunta qué haría. Dile por qué no te gusta la respuesta. Escucha lo que contesta. Propondrá stacks y enfoques que no habías considerado, y acierta con suficiente frecuencia como para que descartarlos por reflejo salga caro. La postura que funciona no es dictar ni tampoco deferir: es dejar que te oriente sin dejar de estar dispuesto a llevarle la contraria.

Hay otra incoherencia relacionada que veo mucho y merece un nombre porque desperdicia dinero además de tiempo: **pedirle tareas minúsculas a un modelo grande y lento.** Si vas a entregar el trabajo en piezas de cinco minutos, usa algo rápido: toda la economía de una tarea pequeña presupone una respuesta rápida. Haz coincidir el tamaño de la petición con la herramienta. Un modelo grande y cuidadoso para el trabajo grande y cuidadoso; algo rápido para las cosas pequeñas. Pagar una latencia prémium por un cambio de una línea es lo peor de ambos mundos, y casi nadie se da cuenta de que lo está haciendo.

## Esperar no es el coste que crees

Esta es la creencia que hay debajo de todo lo demás, y hasta que no cambia nada más lo hace.

Cuando un agente está trabajando y tú estás sentado delante, parece que esperas. Tiempo muerto. Algo que querrías reducir, por eso divides el trabajo en piezas tan pequeñas que la espera nunca es larga y por eso nunca empiezas una segunda cosa mientras la primera sigue en marcha.

Pero ese tiempo no se ha perdido. Se ha **liberado**. Solo parece una espera porque todavía no has metido nada dentro.

Y hay una cola de cosas que caben ahí. El mantenimiento que sigues posponiendo. La optimización que nunca terminas de justificar como prioridad. Y las partes del trabajo que nunca fueron código: escribir algo como es debido, investigar una decisión en vez de adivinar, hablar con quien haga falta o simplemente pensar hacia dónde va aquello. Eran siempre lo primero que se quedaba fuera, y esta es la primera vez en mucho tiempo que algo te devuelve ese espacio.

Cuando esto se asienta, paralelizar deja de ser una técnica avanzada y se convierte en lo evidente. Mi regla para saber por dónde empezar es aburrida y funciona: **ejecuta cosas en paralelo cuando no toquen los mismos ficheros.** Ya está. Dos funcionalidades en zonas distintas, un refactor aquí y una suite de tests allá. No hace falta coordinación porque no hay nada que coordinar.

Más allá están los worktrees, que permiten ejecutar en paralelo trabajos que sí entrarían en conflicto, pero entonces las integraciones son cosa tuya. Merece la pena cuando el trabajo es lo bastante grande como para justificar esa contabilidad, no antes.

## Higiene de sesión, que nadie explica

La otra cosa que distingue a quien avanza rápido es poco vistosa y casi nunca se comenta: saber cuándo seguir y cuándo empezar de nuevo.

Lo que hago yo en la práctica:

**Tarea nueva, sesión nueva.** Si no está relacionada con lo anterior, el contexto previo es ruido en el mejor de los casos.

**El trabajo relacionado se queda.** Los seguimientos o varias tareas dentro de la misma especificación pueden compartir sesión: el contexto acumulado está haciendo trabajo de verdad.

**Compacta cuando empiece a costarle.** A veces dejo que compacte automáticamente, a veces me lo pide y a veces sencillamente noto que está perdiendo el hilo y lo hago. Acercarse al límite de lo que puede contener — digamos el último quinto — suele ser buen momento en cualquier caso.

Nada de esto es profundo. Pero la diferencia entre quien lo hace y quien no es enorme, y no aparece en ninguna documentación porque no es una funcionalidad. Es un hábito.

## Una salvedad sobre las herramientas

Todo lo anterior presupone que tienes a mano un agente capaz. Esa suposición no sale gratis.

Si trabajas con un asistente de autocompletado, una ventana de chat limitada o un modelo abierto más pequeño, el consejo cambia de forma: dividirás más, construirás tú más andamiaje y te mantendrás más cerca del trabajo. No por reflejo, sino porque la herramienta lo necesita de verdad. Poder cambiarlo muchas veces no depende de ti, y el tema merece su propio artículo en vez de un párrafo aquí.

## Lo que cambia las cosas de verdad

No hay una técnica para la parte de confiar, y he dejado de fingir que la hay. Para mí y para los compañeros a los que he visto pasar por esto, la secuencia fue la misma y no fue intelectual: **lo ves salir bien suficientes veces y dejas de prepararte para el golpe.**

Hay dos cosas que ayudan de verdad. Las herramientas siguen mejorando, así que la misma cantidad de confianza compra más que el año pasado. Y tú mejoras **poniendo los raíles**: construyendo el entorno que hace que el agente haga lo correcto, en vez de comprobar después si lo hizo. Esa es la habilidad. No la confianza: poner los raíles.

Por eso el consejo que le doy a un compañero el primer día suena casi demasiado simple. **No sobreconstruyas el entorno**: empieza con lo que viene por defecto, prueba cosas y mira qué tal va antes de levantar andamiaje a su alrededor. Y **pregunta más**, de verdad más de lo que te resulte natural: resuelve las cosas más rápido de lo que las encontrarías tú, e irte primero a buscar por tu cuenta es el hábito más caro que trajimos con nosotros. Esto entra raro, porque buscar *era* la habilidad. Ya no es la ruta más rápida hacia la misma respuesta.

La incomodidad merece la pena porque esto premia exactamente lo que ya haces. No escribir código: especificar con precisión, construir verificaciones que se ejecutan sin ti y saber de qué sospechar. Esa es la descripción del puesto, y quien llega desde cero no tiene ninguna de las tres. Nuestro techo está más alto que el suyo, detrás de una puerta que mantiene cerrada un hábito que era correcto hasta hace poco.

Así que: **deja de comprobar con los ojos lo que debería comprobar un mecanismo.** Guarda los ojos para los casos que se los ganen. La confianza llega sola cuando los mecanismos empiezan a cargar con el peso.

---

*Tercero de tres artículos sobre lo que construir software con agentes exige de verdad. El primero es [el mapa](/es/blog/what-you-still-need-to-know-to-ship), el segundo es [para quien empieza desde cero](/es/blog/if-youre-starting-from-zero). Si prefieres trabajar esto con tu propio equipo, [eso es lo que hago](/es/mentoring).*
