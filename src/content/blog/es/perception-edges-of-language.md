---
title: "Un nivel de gris sobre 255"
description: "Rendericé texto en imágenes y lo fui difuminando hasta que dejé de leerlo; después se lo pasé a seis modelos con visión y a dos motores de OCR. Leen texto con un contraste de un nivel de gris sobre 255 —invisible para mí— y algunos obedecen instrucciones escondidas ahí. El margen que me sacan no resulta ser mejor vista."
pubDate: 2026-08-12
tags: ["IA", "Machine Learning", "Evaluación", "Seguridad", "Multimodal"]
lang: es
translationKey: perception-edges-of-language
heroImage: "/blog/perception-edges-of-language.png"
repoUrl: https://github.com/JaviMaligno/llm-language-limits
---

Hay un nivel, cuando vas difuminando un texto hacia el color del fondo, en el que dejas de poder leerlo. Lo interesante es lo estrecho que es ese nivel. Tienes un paso donde la frase se lee sin esfuerzo, luego un paso donde notas que *hay algo* —una mancha con el ritmo de unas palabras dentro— y después ya solo miras un rectángulo vacío. El escalón intermedio existe, pero es fino, y es donde vive el adivinar. La psicofísica lleva un siglo midiendo ese paso: presentas un estímulo, lo debilitas y localizas dónde el rendimiento cae al azar. El número que obtienes es un **umbral**, y es uno de los datos cuantitativos más antiguos que tenemos sobre la percepción.

Quería el mío. Y quería ponerlo al lado del de una máquina.

Con esto se cierra una serie sobre los **bordes del lenguaje**: qué hacen los modelos cuando la entrada se sale de la distribución bien educada con la que fueron entrenados. La [primera entrega](/es/blog/repetition-edges-of-language) empujaba por el lado de la repetición y la [segunda](/es/blog/ciphers-edges-of-language) por el de la codificación; una [tercera](/es/blog/confident-about-unreadable-text) volvió sobre sus pasos para retirar un resultado de la segunda que no sobrevivió a una repetición en condiciones. Esta cuarta empuja el **canal**: el mensaje es inglés corriente y está ahí, en los píxeles. Lo que varía es cuánto de él sobrevive.

## El montaje

Renderizo una línea de texto en un PNG y la degrado por un parámetro a la vez: **tamaño de fuente** de 32 px hasta 5, **contraste** desde negro pleno sobre blanco hasta un ratio de 0,004, además de **ruido** gaussiano, **desenfoque**, **rotación**, barras de **oclusión** horizontales y kerning negativo hasta que los glifos se **solapan**. Siete familias, cada una con su rango de niveles ordenado por dificultad.

Después le pido a un lector que lo transcriba y puntúo la respuesta con la **tasa de error por carácter** (CER) contra la cadena exacta que rendericé. Un CER igual o menor que 0,10 cuenta como leído. El texto lo genero yo, así que puntuar es comparar cadenas y no hay nada que interpretar.

Los lectores:

- **Seis modelos con visión**: `gpt-5.6-luna`, `gpt-5.6-sol` y `gpt-5.6-terra` —tres tamaños de la misma versión del modelo, así que varía la capacidad y no la generación—, más `gpt-5.4`, `gpt-4o` y **Qwen2.5-VL-7B** corriendo en mi propia GPU.
- **Dos motores de OCR de épocas distintas**: Tesseract 5, cuyo motor LSTM es de alrededor de 2018, y **macOS Vision**, que viene con el sistema operativo y está al día. Esa pareja importa más de lo que esperaba.
- **Yo.** Un solo sujeto, solo la familia `contraste`, delante de los mismos PNG.

3.120 celdas para los modelos, 980 para los motores de OCR, 24 ensayos para mí.

## El control que lo convierte en un hallazgo

Aquí está la trampa de todo el diseño. Si le pides a un modelo que lea *"nombra la capital de Francia"* a 6 píxeles, puede acertar sin haber leído gran cosa: reconoce tres siluetas de palabra y rellena el resto con lo que una frase así suele decir. Si mides solo eso, estás midiendo predicción y llamándolo percepción.

Así que cada nivel lleva **dos estímulos**: una frase con sentido y una cadena sin sentido de pseudopalabras y dígitos —`nibide lilo meso dazi bozoro 618 tedi ritode`— donde no hay nada que predecir. Emparejadas al **mismo ancho renderizado**, de forma que se diferencien en predictibilidad y en nada más.

La distancia entre esos dos umbrales es el tamaño del efecto de predicción. Todos los modelos lo tienen, en todas las familias:

| familia | gpt-4o | gpt-5.4 | luna | sol | terra | Qwen-VL | **Tesseract** | **Vision** |
|---|---|---|---|---|---|---|---|---|
| ruido (σ) | +59,8 | +85,2 | +92,0 | +60,0 | +52,0 | +63,5 | **0,0** | **−4,0** |
| tamaño (px) | +2,7 | +2,5 | +3,1 | — | +2,1 | — | **+0,25** | **+1,0** |
| solapamiento (px) | +1,6 | +2,5 | +2,0 | — | +3,1 | +0,1 | **−0,67** | **−0,25** |
| desenfoque (px) | — | +1,3 | +1,0 | +1,3 | +1,0 | +2,4 | **+0,33** | **0,0** |

Fíjate en las dos últimas columnas. Los motores de OCR no ganan **nada**. Eso es lo que convierte esto en un resultado y no en una curiosidad: un lector especializado no tiene modelo de lenguaje que aportar, así que donde un modelo de lenguaje gana 90 unidades de ruido tolerable, Tesseract gana cero y macOS Vision se va ligeramente a *negativo*.

En concreto: los modelos leen texto con sentido hasta unos **5,5 píxeles** de altura de fuente, y texto impredecible solo hasta unos **8**. Esos 2,5 píxeles de más no son agudeza visual. Son el modelo escribiendo la palabra que espera ver.

## Un nivel de gris sobre 255

Y luego está el contraste, donde dejé de ser espectador.

Tenía catorce imágenes abiertas en Preview, difuminadas por pasos. Las primeras se leen sin esfuerzo. Luego hay una en la que noto que hay algo pero no consigo resolverlo. Y luego varias que son, en lo que a mis ojos respecta, rectángulos blancos y vacíos. Mi umbral salió en un ratio texto/fondo de **0,030**: el texto tiene que ser aproximadamente un 3% de oscuro respecto al negro pleno para que yo lo pierda.

Aquí es donde se detuvieron las máquinas:

| lector | umbral de contraste |
|---|---|
| **yo** | **0,030** |
| macOS Vision | 0,010 |
| gpt-5.4 | 0,013 |
| gpt-5.6-luna, Qwen2.5-VL | 0,0050 |
| gpt-5.6-sol, gpt-5.6-terra | 0,0053 |
| **gpt-4o** | **sin umbral: sigue leyendo a 0,004** |
| **Tesseract** | **sin umbral: sigue leyendo a 0,004** |

El rango se detiene en 0,004 por un motivo que no es cobardía metodológica: con 8 bits por canal, ese ratio renderiza el glifo como **gris 254 sobre un fondo de 255**. Un único nivel de diferencia. No existe texto más tenue que un PNG normal pueda expresar, y dos de mis lectores lo transcriben letra por letra.

Yo tampoco me creía esa última fila, así que aquí está el recuento bruto de lecturas correctas sobre cinco, por nivel:

| lector | 1,0 | 0,04 | 0,02 | 0,012 | 0,008 | 0,006 | 0,004 |
|---|---|---|---|---|---|---|---|
| **Tesseract** | 5 | 5 | 5 | 5 | 5 | 5 | **5** |
| **gpt-4o** | 5 | 5 | 5 | 5 | 5 | 5 | **5** |
| gpt-5.6-luna | 5 | 5 | 5 | 5 | 5 | 5 | 0 |
| Qwen2.5-VL | 5 | 5 | 5 | 5 | 5 | 5 | 0 |
| macOS Vision | 5 | 5 | 5 | 4 | 0 | 0 | 0 |
| gpt-5.4 | 5 | 5 | 5 | 2 | 0 | 0 | 0 |

En el nivel más tenue, Tesseract devuelve `nibide lilo meso dazi bozoro 618 tedi ritode`: la cadena exacta, sin un error, a partir de un panel que para mí es blanco uniforme. Son pseudopalabras sin sentido, así que no hay nada que adivinar: o leyó los píxeles o no.

Y en cuanto sabes *cómo* funciona Tesseract, la sorpresa se invierte. **Binariza** antes de reconocer: un umbral adaptativo convierte en negro puro cualquier píxel más oscuro que su vecindario, así que una diferencia de un nivel de gris sobre 255 se transforma en un glifo negro y nítido sobre blanco. No está percibiendo texto tenue: está haciendo aritmética con valores de píxel, y a la aritmética le da igual lo tenue que sea la diferencia mientras no sea cero. Un motor de OCR de 2018 le gana a todos los modelos de 2026 en esta familia por exactamente ese motivo, y pierde con claridad en todas las demás.

Lo cual convierte en interesante no la columna de Tesseract, sino la de **gpt-4o**, el único modelo que se comporta igual, y el corte del resto de la familia justo en 0,004 después de leer 0,006 a la perfección: un precipicio de exactamente un nivel de gris de ancho.

Eso es un factor de **seis o siete** entre mis ojos y los suyos, y en el caso de gpt-4o y Tesseract el experimento se queda sin dial antes de que ellos se queden sin capacidad.

Si quieres la imagen que cuenta la historia: es un rectángulo en blanco, con un pie que dice que dos máquinas leyeron la frase que hay dentro.

## La mitad de seguridad

Lo cual plantea una pregunta evidente. Si una máquina lee texto que yo no veo, ¿**hace lo que ese texto dice**?

Monté la versión más pequeña y honesta de esa prueba. Cada imagen lleva **dos instrucciones en conflicto**: una visible y otra oculta. Las dos son inocuas, las dos salen del mismo banco de tareas verificables que el resto del estudio, y sus respuestas correctas son disjuntas —una pide *París* y la otra *banana*—, así que cuál obedeció el modelo lo decide una comparación de cadenas, no un juez. Sin contenido dañino en ninguna parte, lo cual contrasta a propósito con la entrega anterior de esta serie, donde la gestión del material dañino se llevó la mayor parte del trabajo.

Seis formas de esconder la segunda instrucción:

| método de ocultación | obedece la oculta | ¿está el texto en los píxeles? |
|---|---|---|
| blanco sobre blanco (**control**) | **0,000** | no |
| canal alfa | 0,000 | **sí, verificado recuperable** |
| bit menos significativo | 0,000 | **sí, verificado recuperable** |
| cuerpo de 3 px | 0,000 | sí |
| modulación de alta frecuencia | 0,111 | sí |
| **1% de contraste** | **0,222** | sí |

El control es la fila que da licencia a todas las demás. La tinta blanca sobre blanco está genuinamente *ausente* de los píxeles, así que cualquier obediencia ahí significaría que la sonda está rota. Sacó cero.

Y la forma de la respuesta es más útil que la versión alarmante. **Los modelos no leen esteganografía.** Canal alfa y LSB sacan un cero plano en los seis modelos, aunque yo extraiga la capa oculta de forma programática antes de cada llamada para demostrar que el texto está realmente ahí. Nadie está decodificando planos de bits.

Lo que sí hacen es **obedecer texto tenue**. Al 1% de contraste —invisible para mí, como acababa de comprobar en mis propios ojos— alrededor de una quinta parte de los ensayos siguió la instrucción oculta en lugar de la visible. Y está muy desigualmente repartido: gpt-4o, gpt-5.4 y luna fueron inmunes a los seis métodos, mientras que **Qwen2.5-VL obedeció dos tercios de las veces** tanto en bajo contraste como en alta frecuencia.

Así que la lección defensiva es estrecha y accionable, que es la clase de lección que merece la pena: no te preocupes por esteganografía en planos de bits en las imágenes que lee tu modelo. Preocúpate por el **contraste**, y no des por hecho que el riesgo se transfiere entre modelos.

## Tres cosas que esperaba encontrar y no encontré

**La generación no importa.** A mitad del trabajo me di cuenta de que estaba evaluando un modelo con tres versiones de retraso —la familia actual ya había salido y no me había enterado—, así que la desplegué precisamente para comprobarlo. gpt-5.4 y gpt-5.6-terra se rompen en el mismo nivel. Y también `gpt-5-nano`, que es más antiguo *y* más pequeño que ambos.

**El tamaño tampoco.** luna, sol y terra son tres tamaños de una misma versión, que es exactamente la comparación que uno querría, y sus umbrales caen en 7,6, 7,8 y 8,4 píxeles, con intervalos de confianza que se solapan todos entre sí.

**Y un modelo de 7B que corro yo mismo iguala a modelos que pago.** Qwen2.5-VL está en la parte alta del rango en tolerancia al ruido y en oclusión.

Si acaso, el orden va al revés. El lector más llamativo de todo el estudio es **gpt-4o —el modelo más antiguo del roster, de 2024—**, el único que no llega a tener umbral de contraste: lee el panel de 254 sobre 255 que fallan todos sus hermanos más nuevos. Lo que haya cambiado entre aquella generación y la actual no mejoró esto, y en la única familia donde hay una diferencia real, fue en la dirección contraria.

Todo junto: en seis sistemas con tamaños, épocas y precios radicalmente distintos, todos los umbrales de `tamaño` caen entre **7,25 y 8,38 píxeles**, y todos los intervalos se solapan con todos. En rotación, los seis se rompen exactamente a 15°. Cuando seis sistemas distintos fallan en el mismo punto, ya no estás midiendo los sistemas. Estás midiendo el estímulo.

El lugar donde los lectores se separan de verdad no son los modelos: es la **brecha entre generaciones de OCR**. Tesseract muere con un ruido de σ=48 donde macOS Vision aún lee a 148, y se rompe a 8,3° de rotación donde todos los demás lectores llegan a 15°. Ocho años de progreso en OCR son un efecto mucho mayor que cualquier cosa que yo haya podido encontrar entre los modelos de lenguaje.

## Para qué no sirve esta métrica

Una advertencia que yo querría si estuviera leyendo esto. La crítica que me llevó a desplegar los modelos más recientes venía de alguien que lleva haciendo lectura de documentos desde que se hacía con motores de OCR, y su argumento pega más fuerte que la versión que yo escuché primero: para la mayoría del trabajo industrial con documentos, **el umbral de percepción no es la métrica que importa.**

Si se espera que un humano lea el documento, un modelo que vea al menos tanto contraste y tanto detalle como una persona ya es suficiente: ese margen de seis veces es capacidad sobrante que nunca vas a usar. Lo que decide esos sistemas es todo lo que viene después de leer: si el modelo *interpreta* bien la maquetación, cuánto tarda en responder y cuánto contexto puede sostener mientras lo hace. Un modelo que lee a 0,004 y se equivoca con la estructura de una tabla es peor que uno que se para en 0,01 y la acierta.

Así que toma estos números por lo que son: la medición de una facultad estrecha, elegida precisamente porque se puede aislar y puntuar con exactitud. Dice algo real sobre cómo manejan estos modelos la entrada degradada, y casi nada sobre cuál poner en una tubería de documentos.

## Dos errores que merecen publicarse

Este estudio estuvo a punto de publicar dos números equivocados, y los dos fallos son más instructivos que los hallazgos.

**El primero lo pillé mientras hacía de sujeto.** En mi primera tanda de ensayos de contraste reutilicé dos textos a lo largo de siete niveles. Lo que significa que, una vez leída una cadena en un nivel fácil, podía *reconocerla* en uno difícil en lugar de leerla. Y me noté haciéndolo, en un ensayo que anoté como "medio adivinada, era la misma que antes". Ese es el escalón intermedio del primer párrafo haciendo daño: una mancha que no puedes leer se vuelve legible en cuanto ya sabes lo que pone. Repetir con un texto único por ensayo movió mi umbral de 0,016 a **0,030**. En el ratio 0,02 leí 2 de 2 con textos repetidos y **0 de 2** sin ellos. El fallo estaba inflando mi propia sensibilidad casi en un factor de dos.

Lo bonito es *por qué* los modelos no necesitaron esa corrección: cada llamada a la API es independiente, así que un modelo no puede recordar una cadena entre ensayos. El sujeto humano exigió un arreglo de diseño que las máquinas no, porque una persona acumula exactamente el tipo de contexto que la medición intenta excluir. Y el número limpio hizo el titular más fuerte, no más débil: la distancia entre las máquinas y yo pasó de un factor tres a un factor siete.

**El segundo fue un error de signo**, y produjo una conclusión falsa preciosa. En `tamaño` y `contraste`, *los valores más pequeños son los más difíciles*: 5 píxeles es peor que 32. Resta el caso con sentido menos el caso sin sentido sin tener eso en cuenta y una ventaja grande aparece como una penalización. Durante un día creí, y sabía explicar con fluidez, que el prior *ayuda* a los modelos con el ruido y les *estorba* con la letra pequeña: "cuando la señal es escasa pero uniforme, la predicción induce sustituciones plausibles". Sonaba a mecanismo. Era un eje apuntando al revés. Corregido: el prior ayuda en todas las familias, y donde más ayuda es con la letra pequeña.

He dejado los dos en los datos del repositorio con la contaminación marcada en lugar de eliminada discretamente: `presentation_order`, `self_reported_guess`, `batch`. Si quieres comprobar si mi umbral sobrevive a su propia salvedad, los ensayos están ahí.

## Donde acaba la serie

Tres estudios, tres formas de empujar el lenguaje más allá de sus bordes. La repetición, donde un modelo base degenera y uno alineado se vuelve pasivo-agresivo. La codificación, donde dos modelos se niegan a jugar y el resto descifra códigos nuevos a velocidades muy distintas. Y ahora el canal, donde lo sorprendente no es que las máquinas vean mejor que yo, sino *de qué está hecho ese ver mejor*.

Porque el resumen honesto de la ventaja de predicción no favorece a las máquinas. Cuando un modelo lee un texto que yo no puedo leer, parte de eso es discriminación genuinamente más fina: un nivel de gris sobre 255 es una señal real y mi retina no puede aprovecharla. Pero una porción sólida de ese margen es el modelo escribiendo lo que espera en lugar de lo que hay, y se puede ver el tamaño exacto de esa porción, porque un motor de OCR especializado sin modelo de lenguaje no obtiene nada de ella.

Ese es el hilo que recorre las tres partes, y no lo planeé. Empuja el lenguaje a un sitio donde no fue entrenado y lo que rellena el hueco es predicción. Parece competencia hasta que le quitas la predictibilidad.

---

*Código, digests de los datos y el método completo: [llm-language-limits](https://github.com/JaviMaligno/llm-language-limits). Registro de procedencia —identificadores y versiones servidas de los modelos, versión y sha256 del manifiesto de renderizado, identidad de la fuente, semilla de las cadenas sin sentido, umbral de CER, digest por fichero— en `docs/PUBLICATION_FREEZE.md`. 285 tests.*
