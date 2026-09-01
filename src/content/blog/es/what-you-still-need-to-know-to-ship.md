---
title: "Lo que todavía necesitas saber para lanzar algo real"
description: "Hoy puedes construir software sin escribir una línea. Lo que queda no es programar: es una forma de trabajar y una lista de cosas que tienes que saber que existen o nunca se te ocurrirá preguntar. Aquí están las dos."
pubDate: 2026-08-03
tags: ["IA", "Vibe Coding", "Software", "Ingeniería", "Mentoría"]
lang: es
translationKey: what-you-still-need-to-know-to-ship
heroImage: "/blog/what-you-still-need-to-know-to-ship-es.png"
---

La gente que construye software hoy no aprendió toda a construir software. Algunos vienen de marketing, de operaciones, de llevar un negocio pequeño, de nada técnico en absoluto. Describen lo que quieren, un agente lo construye y funciona. Esa parte es real y no va a desaparecer.

También es real que una porción de ellos está publicando cosas con la base de datos abierta de par en par, la clave de la API metida en el paquete que descarga el navegador y ninguna forma de volver a la versión que funcionaba el martes pasado. No por descuido. Porque nadie les dijo que esas eran categorías de cosa que existen.

Ese es el hueco de verdad, y es más pequeño y más raro que "aprende a programar".

## El techo: no puedes preguntar por un espacio que no sabes que está ahí

Todos los fallos que he visto, en mí y en la gente a la que he enseñado, llevan al mismo sitio. No a una habilidad que falta. A una *categoría* que falta.

No necesitas saber cómo funciona la autenticación. Necesitas saber que tener una pantalla de login y estar protegido son dos cosas distintas, porque en el momento en que lo sabes puedes preguntar, y el agente se encarga del resto. Si no lo sabes, nunca preguntarás, y el agente no lo va a sacar por su cuenta. Los agentes responden bien a las preguntas. Son mucho peores diciéndote qué pregunta tendrías que haber hecho.

De esto escribí desde el otro lado en [¿Cuánto deberías seguir sabiendo?](/es/blog/how-much-should-you-still-know) — la versión del ingeniero, donde delegas conocimiento que antes sostenías y tienes que averiguar de qué sigues respondiendo. Este artículo es el mismo muro desde la dirección contraria: no qué puedes permitirte olvidar, sino qué nunca aprendiste y ahora no puedes saltarte.

Conviene decir de dónde sale esto. La mayor parte de mi enseñanza ha sido con compañeros técnicos, que es otro problema y casi otro artículo. Con gente no técnica mi muestra es más pequeña y más informal — amigos, sobre todo, y ese momento en que alguien se encuentra con una terminal por primera vez. El resto viene de construir así yo mismo, y de lo que he ido cazándoles a los agentes por el camino.

Hay dos cosas que entender, y son independientes. Una es una forma de trabajar. La otra es un mapa.

## Parte uno: el bucle

Especificar → construir → comprobar → corregir. Y otra vez.

No hay nada nuevo en esto. Es spec/develop/test, la forma en que se hace software desde hace décadas. Si vienes de algo técnico lo tienes en los huesos y puedes saltarte esta sección. Si no vienes de ahí, es genuinamente nuevo, y su ausencia es la mayor diferencia entre alguien que lanza algo y alguien que tiene un historial de chat muy largo.

El fallo por defecto cuando no está no es dramático. Pides, recibes, te lo crees, pides lo siguiente. Nada comprueba nada. Parece progreso justo hasta que intentas enseñárselo a alguien.

**El agente está en las cuatro fases**, que es lo que despista. Te ayuda a especificar. Construye. Ejecuta comprobaciones y te dice dónde mirar. Propone el arreglo. ¿Entonces qué queda? La pregunta útil no es dónde está el agente — está siempre — sino qué residuo humano deja cada fase:

- **Especificar** — la intención es tuya. El agente escribirá lo que quieres mucho mejor que tú. No sabe qué quieres.
- **Construir** — no queda nada. Se delega por completo.
- **Comprobar** — el agente ejecuta cosas y reporta. Lo que sigue siendo tuyo es saber *qué categorías hay que comprobar siquiera*, y dar algo por bueno.
- **Corregir** — tampoco queda nada. Corregir es volver a construir, y lo hace el agente. Cuando un fallo te lleva a decidir que aquello hay que rehacerlo entero o tirarlo, eso no es corregir: es volver a Especificar con otra intención.

Así que el bucle se parte por la mitad. Dos fases se entregan del todo, dos conservan algo humano — y las dos que desaparecen son exactamente las que la gente llama "programar". Lo que queda es decir qué quieres y saber si lo has conseguido.

Por eso "ya no hace falta saber programar" es a la vez cierto e inútil. Es cierto sobre la mitad del bucle y calla sobre la otra mitad, que es justo la que nunca se le enseñó a nadie.

Fíjate en dónde está comprobar: **dentro del bucle, desde el primer día.** No es un nivel al que llegas, es una fase en la que ya estás. Lo que crece con la experiencia no es *si* compruebas, sino *qué eres capaz de comprobar*. Viene en tres alcances: el agente te dice dónde mirar y miras; compruebas aquello que sabes preguntar; o además sabes si la comprobación valía algo y qué se ha dejado fuera. El primer alcance está disponible para un principiante absoluto en su primera tarde, y basta más veces de lo que parece.

### Tres formas de cazar cosas, ninguna implica leer código

Esta es la parte que la gente da por imposible sin formación técnica, y no lo es. Todo lo que cazo, lo cazo de una de estas tres formas, y sirven para todas las categorías de más abajo.

**Escribirlo en el spec por adelantado.** La más barata, porque no cazas el problema: lo evitas. Si dices desde el principio que estos valores tienen que venir de la base de datos y que nada puede quedar escrito a fuego, no tienes que encontrar el valor escrito a fuego después. Casi todo lo que un agente hace "mal" es una decisión razonable que tomó porque tú no dijiste otra cosa.

**Usar la cosa funcionando.** El código no: la aplicación. Púlsala, tantéala, prueba lo que haría un usuario y luego lo que no debería hacer. Así encontré un endpoint abierto que no debía estarlo: salió probando, no revisando código.

**Preguntar cuando algo huele.** Un número que no cambia nunca cuando debería. Una página que carga sospechosamente rápido. Una pantalla que funciona estando desconectado. No necesitas saber qué está mal para decir "¿por qué esto no cambia nunca?" — y el agente es realmente bueno yendo de ahí a la causa.

Ninguna de las tres exige leer una línea de código. Las tres exigen saber que la categoría existe, que es justo para lo que sirve el mapa.

## Parte dos: el mapa, y cómo leer tu nivel

Para cada categoría hay tres niveles:

**Consciente** — sabes que esta categoría existe y puede fallar. No necesitas saber cómo funciona ni cómo se llama. Necesitas saber que está ahí, porque es lo que te hace preguntar.

**Con soltura** — entiendes el vocabulario, sabes formular la pregunta y sabes si la respuesta tiene sentido. Merece decirse claro: **a este nivel se llega preguntándole al propio agente.** A propósito, con paciencia, una categoría cada vez. Es la formación más barata que existe ahora mismo y casi nadie la usa deliberadamente.

**Con criterio** — tienes una opinión propia y puedes elegir entre opciones.

Dos cosas sobre esto que importan más que los niveles en sí.

**Tu nivel es un vector, no un número.** Nadie está en el mismo peldaño en todo. Puedes tener criterio sobre control de acceso y no tener ni idea de lo que te cuesta el hosting. El perfil sale dentado, y eso es lo normal: es un mapa con agujeros, no una escalera que se sube entera.

Si quieres tu propia versión de ese perfil dentado antes de seguir leyendo, hay una [versión de catorce preguntas de esto](/es/assessment) que lleva unos dos minutos.

**Con criterio es opcional, hasta que deja de serlo.** Puedes lanzar la mayoría de categorías sin formarte nunca una opinión propia. Pero allí donde el proyecto se está jugando algo de verdad, el nivel de arriba deja de ser un lujo: si cobras dinero, necesitas criterio sobre coste; si guardas datos de otras personas, sobre acceso.

![El mapa: trece categorías de riesgo en cinco familias, más una de criterio](/blog/what-you-still-need-to-know-map-es.png)

## Trece categorías, más una

Trece donde las cosas pueden salir mal, y una que es de otra naturaleza. Recórrelas y busca aquellas que no sabías que eran una categoría: esas son tu respuesta.

### El techo

**1. Qué se puede pedir.** Esta va primero porque limita a las otras doce. Si crees que un agente escribe texto, le pedirás que escriba texto, y todo lo de abajo se queda en teoría.

- **Consciente** — un agente construye sistemas enteros que funcionan, no fragmentos de escritura
- **Con soltura** — describir lo que quieres por resultado, pedirle que investigue y proponga antes de construir, y entenderlo cuando dice que algo no se puede o propone otra ruta
- **Con criterio** — qué modelo, qué herramienta, qué hardware. Tema para otro artículo.

**2. Hasta dónde llega.** La otra mitad del techo, y la mitad que nadie menciona. Un agente que solo ve lo que le pegas es una caja de texto muy cara: la capa de integración eres tú, metiendo el contexto a mano y sacando las respuestas igual, y ese coste se paga entero todas las veces — que es la razón por la que se prueban estas herramientas, sale bien, y se dejan en silencio. Arreglarlo casi nunca es desarrollo. Los conectores a los sistemas habituales —repositorio, gestor de tickets, documentación, chat— ya son estándar, e instalar uno es configuración. Lo que cuesta es un permiso, y por eso se atasca donde nada técnico se atascaría. He escrito sobre [el modo de fallo completo aparte](/es/blog/stop-being-the-cable).

- **Consciente** — solo sabe lo que le pegas, y se le puede conectar a lo vuestro
- **Con soltura** — conectar un sistema que importe, y conceder lectura antes que escritura
- **Con criterio** — permisos acotados, saber qué puede hacer por defecto y qué requiere aprobación, y construir un conector cuando no existe

### Dónde está y cómo lo recupero

**3. Dónde vive tu app.** La cuestión del entorno es donde viven los errores realmente feos. Casi nadie borra datos de producción a propósito: los borra creyendo que está en la copia de pruebas. Y la separación que crees tener puede no existir: he tenido pipelines que no distinguían entornos en absoluto, ejecutando CI contra dev y contra prod por igual, sin separación real detrás de los nombres. Me enteré mirando el panel de despliegue, no leyendo configuración — y luego dejé la separación documentada para que siguiera siendo cierta.

La misma pregunta se aplica al propio agente, y ahí es donde pilla a la gente. Las versiones de navegador de estas herramientas no corren en tu ordenador: corren en el de otro, así que no ven tus ficheros, no tienen tus claves ni lo que tengas instalado. "Funcionaba en mi máquina pero no en el navegador" no es inconsistencia; son dos entornos con dos configuraciones.

- **Consciente** — "corre en mi portátil" y "corre en internet" no son lo mismo. Cierra el portátil: ¿sigue vivo? Y la versión de navegador de tu agente tampoco está en tu portátil.
- **Con soltura** — pedir un despliegue, entender la diferencia entre el sitio de pruebas y el real, ejecutar sin bloquearte un comando que te dictan, saber en cuál de los dos estás tocando ahora mismo, y saber qué tipo de cosas se quedan fuera cuando trabajas en la nube — ficheros locales, claves, herramientas instaladas — para saber cuándo tienes que volver a tu propia máquina
- **Con criterio** — dominios, ajustes por entorno, logs del hosting, deshacer un despliegue, elegir dónde corre, y configurar el remoto para que funcione también allí

**4. Código y datos.** Los agentes escriben valores a fuego constantemente: un dato metido en el código que debería salir de la base de datos. Es un atajo razonable cuando el objetivo es que algo funcione, y está mal en el momento en que ese dato tiene que cambiar. Es el caso típico de la primera y la tercera técnica de arriba: decir por adelantado que no pase, y preguntar después cuando un número parece sospechosamente estable.

- **Consciente** — el código se regenera, los datos no; hay datos metidos dentro del código; los datos necesitan copias de seguridad
- **Con soltura** — preguntar dónde se guarda algo y entender la respuesta, saber si la base de datos es local o remota, y confirmar que la copia existe en vez de que alguien la haya mencionado
- **Con criterio** — migraciones, datos de prueba frente a datos reales, restaurar, qué tipo de base de datos y con qué forma

**5. Volver atrás.** "Funcionaba, ahora no, y no sé qué cambió" es el desastre más común de este mundo y el más completamente resuelto. El agente ya hace commits por ti. Lo que falta es que sepas que el rescate existe para poder pedirlo.

- **Consciente** — hay forma de recuperar la versión de ayer y no es Ctrl+Z
- **Con soltura** — pedir un punto de guardado antes de un cambio grande, pedir volver, y mirar el historial para confirmar que ese punto está realmente ahí
- **Con criterio** — ramas, etiquetas, pull requests, leer un diff

### Quién sale herido si esto falla

**6. Secretos.** No necesitas saber leer un fichero `.env`. Necesitas saber que existe y que las claves van ahí. Lo que no es obvio: sacar una clave del código no la saca del historial del proyecto, y he tenido que limpiar claves de ese historial más de una vez. Hay herramientas que vigilan esto — GitGuardian y similares — y, según lo crítica que sea la clave, formas seguras de pasársela a alguien que no son un mensaje de chat.

Hay una segunda confusión que merece nombrarse, porque va en dirección contraria. No todo lo que vive en variables de entorno es un secreto. Feature flags, tiempos de espera, qué región usar — la configuración se va colando en ese fichero porque es el sitio donde van las cosas, y acaba tratándose con la ceremonia que merece una contraseña mientras las contraseñas de verdad se pierden entre medias. Saber cuáles de tus variables son secretas y cuáles son simple configuración es parte de tener soltura aquí.

- **Consciente** — las claves no viven en el código, viven aparte; una clave que se ha visto una vez ya no es secreta
- **Con soltura** — pedir que una clave salga del código, entender por qué ese fichero no se sube, saber de dónde sale una clave cuando te la piden, saber que una clave de servidor y una clave pública de cliente son animales distintos, y distinguir un secreto de un ajuste que simplemente acabó al lado de uno
- **Con criterio** — rotar una clave filtrada, gestores de secretos, secretos por entorno

**7. Quién puede entrar.** El endpoint abierto de más arriba es esta categoría. Merece repetirse qué hizo el trabajo allí: la comprobación fue barata y llevó un minuto. Saber que era una comprobación que merecía la pena hacer es la parte que no sale gratis.

- **Consciente** — tener login no significa estar protegido
- **Con soltura** — preguntar "¿esto lo puede llamar cualquiera?" y entender la respuesta; autenticación es quién eres, autorización es qué puedes tocar; entrar como un usuario y confirmar que no ves los datos de otro
- **Con criterio** — roles y permisos, seguridad a nivel de fila, tokens, revisar qué está expuesto

**8. Datos de otras personas.** La única categoría con asimetría moral: todo lo demás de esta lista te cuesta dinero o vergüenza, y esta la paga alguien que nunca aceptó tu curva de aprendizaje.

- **Consciente** — si guardas cosas sobre otras personas, el coste de equivocarte no es tuyo
- **Con soltura** — saber qué estás recogiendo y por qué, saber que hay obligaciones legales de por medio, y pedir que lo innecesario ni se guarde
- **Con criterio** — consentimiento, retención, minimización, dónde residen físicamente los datos

### Qué me va a sorprender

**9. Lo que esto cuesta.** Las facturas sorpresa son más frecuentes que las brechas, más fáciles de evitar, y casi nadie las evita, porque "por defecto no hay tope" no es algo que se te ocurra preguntar. Al principio construí sistemas agénticos sin pedir que se registrara el coste en tokens, lo que significó quedarme sin estimación al final y tener que repetir la tanda entera solo para medirla. No medir el coste tiene un coste, y se paga justo en la moneda sobre la que querías informarte. Pedirlo en el spec es gratis.

- **Consciente** — esto genera una factura y por defecto nada la limita
- **Con soltura** — entender la forma de esa factura (uso de modelo y APIs, hosting, base de datos, almacenamiento, tráfico), coste fijo frente a coste por uso, que CPU y GPU no se cobran igual; pedir un tope y mirar el consumo real
- **Con criterio** — alertas, límites propios, protección contra bots, diseñar pensando en el coste

**10. De quién dependes.** Separada del coste porque el fallo no es económico: es que algo que funcionaba deja de existir. He hecho una migración entre plataformas que el agente daba por completa y que se cayó en cuanto intenté tirar solo de la nueva — la vieja seguía sosteniéndolo por debajo, y se convirtió en el respaldo que yo no había planeado. "Migración completa" y "ya se puede apagar lo viejo" son afirmaciones distintas, y solo la segunda se puede comprobar.

- **Consciente** — tu app se apoya en servicios de otros, y esos pueden subir de precio, cambiar o cerrar
- **Con soltura** — saber qué piezas son de otro y cuáles son tuyas, y preguntar qué pasa cuando una desaparece
- **Con criterio** — elegir por acoplamiento y no solo por precio, y tener una salida

**11. Aguantar más de lo que probaste.** Nada durante la construcción te avisa de esto, porque mientras construyes hay exactamente un usuario.

- **Consciente** — funciona con tres usuarios y puede caerse con trescientos
- **Con soltura** — saber que probar y aguantar carga son preguntas distintas, y preguntar qué se rompe primero
- **Con criterio** — medirlo, dimensionarlo, decidir qué merece la pena optimizar

### Cómo sé que sigue bien

**12. Tests, y dónde se rompe.** Tiene que haber tests por una razón poco lucida: sin ellos, toda comprobación que hagas se reduce a pulsar por la aplicación terminada adivinando qué pasó por el medio. Eso es un laberinto, y crece con el proyecto.

- **Consciente** — tiene que haber tests, y "el agente dice que funciona" no es uno
- **Con soltura** — entender qué te dicen cuando hablan de frontend o backend, ejecutar los tests y verlos pasar, y saber dónde buscar un error según de qué lado esté
- **Con criterio** — qué tipo de test para qué riesgo

**13. Que siga funcionando dentro de seis meses.** A medida que un proyecto crece desordenado y sin documentar, **el agente empieza a fallar más.** Ese es el argumento: no la pureza arquitectónica, sino tu propia herramienta volviéndose peor ayudándote. El modo de fallo es concreto y fácil de pasar por alto: la documentación se desactualiza, el agente se la cree entera, y acabas con trabajo muy seguro de sí mismo construido sobre una descripción que dejó de ser cierta hace meses. La documentación solo sigue siendo cierta si algo la revisa contra el código — y ese algo puede ser el propio agente, si se lo pides.

- **Consciente** — el desorden degrada aquello de lo que dependes
- **Con soltura** — pedir documentación, entender la diferencia entre documentación para personas e instrucciones para el agente, y notar cuando el resumen del proyecto ya no cuadra con lo que hace
- **Con criterio** — qué va en instrucciones permanentes y qué en la conversación, y cómo partir el proyecto

### Más una: el criterio

La decimocuarta no es como las otras trece, y por eso va la última y aparte. En las trece, el fallo tiene víctima. Aquí no hay fallo: hay ausencia.

Los agentes son buenos en *funcionar*. Son mediocres en *bueno*. La disposición será razonable, los espacios correctos, los colores los mismos que todo lo demás. Funcionalmente correcto y completamente anónimo. Nadie te va a decir nunca que está mal, porque no lo está.

- **Consciente** — lo que sale por defecto funciona y se parece a todo lo demás
- **Con soltura** — nombrar lo que no te gusta con precisión suficiente para que se corrija
- **Con criterio** — tener una dirección propia y sostenerla

Es también la única sin atajo. En las otras doce, saber que la categoría existe basta para preguntar y dejar que el agente cargue con ella. Aquí tienes que mirar la cosa y decidir que no te gusta, y esa parte no la hace nadie por ti.

## La línea de producción no va de ti

Estuve un rato intentando definir el punto donde un juguete se convierte en software de verdad como un nivel al que llegas. Es un error, y merece la pena decir por qué, porque la versión correcta es más útil.

**Producción no exige que estés en un nivel. Exige que ninguna categoría quede sin comprobar por nadie — ni por ti, ni por un test, ni por un servicio, ni por otra persona — y que sepas cuál es cuál.**

Es la misma conclusión a la que llegué desde el lado de la ingeniería: no hace falta sostener el conocimiento, hace falta sostener el mecanismo. Y sirve igual de bien para quien nunca fue ingeniero. Una categoría cubierta por un test está cubierta. Una categoría cubierta por un servicio que pagas está cubierta. Una categoría que compruebas a mano cada vez está cubierta, de forma cara.

Que es para lo que sirve *Consciente* en realidad. No te permite comprobar nada. Te permite ver que la casilla está **vacía**. Una casilla vacía que conoces es un riesgo gestionado. Una casilla vacía cuya existencia ignoras es lo que acaba en las noticias.

![El mismo proyecto como juguete y como sistema en producción](/blog/what-you-still-need-to-know-toy-vs-production-es.png)

## De dónde vienes

El mapa es el mismo para todos. Qué partes ya tienes, y de qué forma fallas, depende de dónde vengas.

**Sin formación técnica**, tu cuello de botella es el techo, no los detalles. Pides menos de lo que podrías porque no sabes qué es pedible. El bucle es genuinamente nuevo. La terminal da un miedo difícil de explicarle a alguien que lleva una década usándola. Y tu fallo característico es delegar *por encima* de tu nivel: entregar cosas que no tienes forma de comprobar y, peor, que no sabes que habría que comprobar.

**Viniendo de ingeniería o de operaciones**, ya tienes el bucle y la mayoría de las doce. Tu fallo es el reflejo del anterior: delegas *por debajo* de tu nivel. Revisas cada línea, das pasos demasiado pequeños y compruebas a mano lo que debería comprobar una máquina. Vas más lento de lo necesario y se siente como diligencia.

Más sobre ambos en los dos próximos artículos.

## Cuánto soltar

Esto es lo que mide todo lo anterior, y no es conocimiento.

**Tu nivel es cuánto puedes entregar sin quedarte ciego.**

Cada peldaño no te deja teclear más, te deja *soltar* más, porque tienes alguna forma de cazarlo si vuelve mal. Consciente significa que notarás que la categoría salió a escena. Con soltura significa que puedes interrogarla. Con criterio significa que puedes llevarle la contraria. En cada paso sube la cantidad que puedes dejar de vigilar sin peligro.

Lo que convierte los dos fallos en el mismo error con el signo cambiado. Delegar por encima de tu nivel es entregar lo que no puedes comprobar. Delegar por debajo es negarte a entregar lo que sí. El arreglo es idéntico en ambas direcciones: encuentra tu peldaño — en cada categoría por separado, porque es un vector — y suelta exactamente tanto como ese peldaño aguante.

No necesitas aprender a programar. Necesitas un bucle, un mapa de lo que existe, y suficiente honestidad sobre qué casillas están vacías.

---

## Todo en una página

| | Consciente | Con soltura | Con criterio |
|---|---|---|---|
| **1. Qué se puede pedir** | los agentes construyen sistemas enteros | describir por resultado, pedir que proponga | modelo, herramienta, hardware |
| **2. Hasta dónde llega** | solo sabe lo que le pegas | conectar un sistema, leer antes que escribir | permisos acotados, por defecto o aprobación |
| **3. Dónde vive** | portátil o internet | desplegar, pruebas o real, ejecutar un comando dado | dominios, ajustes por entorno, deshacer |
| **4. Código y datos** | los datos no se regeneran | dónde se guarda esto, base local o remota | migraciones, restaurar, esquema |
| **5. Volver atrás** | lo de ayer es recuperable | pedir punto de guardado, confirmar que está | ramas, etiquetas, diffs |
| **6. Secretos** | las claves viven fuera del código | fichero de secretos, clave de servidor o de cliente | rotación, gestor de secretos |
| **7. Quién entra** | login ≠ protegido | ¿lo puede llamar cualquiera?, autenticar o autorizar | roles, permisos, tokens |
| **8. Datos de otros** | el daño no lo pagas tú | qué recoges y por qué, deberes legales | consentimiento, retención, residencia |
| **9. Lo que cuesta** | no hay tope por defecto | forma de la factura, pedir un límite | alertas, límites, diseño por coste |
| **10. De quién dependes** | un servicio ajeno puede desaparecer | qué piezas no son tuyas | acoplamiento, plan de salida |
| **11. Aguantar carga** | va con tres usuarios, no con trescientos | probar y aguantar son preguntas distintas | medir, dimensionar, optimizar |
| **12. Tests y fallos** | tiene que haber tests | frontend o backend, ejecutarlos, leer el fallo | qué test para qué riesgo |
| **13. Seis meses después** | el desorden degrada al agente | documentación para personas o para agentes | instrucciones permanentes, estructura |
| **+1. Criterio** | lo que sale por defecto es anónimo | nombrar lo que no te gusta | una dirección propia |

---

**¿Quieres tu propio mapa?** [Responde a las catorce preguntas](/es/assessment) y tendrás esta misma rejilla rellena para tu proyecto, junto con qué hueco conviene cerrar primero.

---

*Este es el primero de tres artículos sobre lo que construir software con agentes exige de verdad. Los dos siguientes recorren el mismo mapa desde los extremos opuestos: uno para quien no tiene formación técnica, otro para quien tiene demasiada y no sabe soltarla. Lectura relacionada: [¿Cuánto deberías seguir sabiendo?](/es/blog/how-much-should-you-still-know).*
