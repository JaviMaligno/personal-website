---
title: "Probado, certificado, barrido, muestreado"
description: "Un paper de sesenta páginas donde las demostraciones escritas, los teoremas comprobados por el kernel, los certificados exactos por cajas y el muestreo a secas se imprimen todos con la misma cara. Cuatro etiquetas, una por afirmación, y el caso que me hizo insistir en ellas: un certificado que daba verde justo en la configuración de la que dependía la prueba."
pubDate: 2026-10-09
tags: ["Matemáticas", "Verificación", "Investigación", "IA"]
lang: es
translationKey: proved-certified-swept-sampled
heroImage: "/blog/proved-certified-swept-sampled.png"
repoUrl: https://github.com/JaviMaligno/calamares
linkedinLinks:
  - label: "Preprint"
    url: "https://arxiv.org/abs/2609.15554"
linkedinSummary: |
  Una afirmación de un paper puede estar respaldada por una demostración escrita, por un teorema comprobado por el kernel de Lean, por aritmética racional exacta en toda una región, o por «muestreé diez millones de puntos y no se rompió nada». Las cuatro se imprimen igual: una frase que suena verdadera.

  Así que en mi último preprint cada afirmación lleva una etiqueta que dice cuál de las cuatro es — probado, certificado por cajas, barrido en malla, muestreado — y un mapa que empareja cada afirmación computacional con el script que hay detrás. No un visto bueno para el paper: una etiqueta por afirmación.

  No empecé siendo tan disciplinado. Lo que me convenció fue un certificado que escribí para un lema, y que un revisor adversario refutó tres veces.

  La versión dos fue la instructiva. Ya era racional-dirigida, sin comparaciones en coma flotante en el test de aceptación — salvo por una tolerancia de 1e-12. Y la configuración de la que depende todo el lema es exactamente tangente: ahí el margen de factibilidad es cero. Una tolerancia en un punto así no introduce un error pequeño. Cambia la respuesta. El certificado decía «cabe» justo en la configuración donde la pregunta es delicada, y lo habría seguido diciendo para siempre, porque no había nada roto.

  La versión cuatro no asume ningún hecho en coma flotante: aritmética racional exacta, resto de Lagrange alternante para la serie, y el arcoseno de la librería usado como un oráculo al que se consulta y no se cree.

  El revisor cazó además algo que yo no habría visto: una afirmación mía marcada como «demostrada» que solo lo estaba en parte de su rango. La etiqueta estaba mal, y una etiqueta equivocada es peor que una débil, porque se cree.

  Tus tests, tus tipos, tus pruebas de propiedad y la lectura atenta que hiciste un domingo son cuatro clases distintas de evidencia, y el CI las pinta todas del mismo verde. ¿Cuál de tus afirmaciones está demostrada, y cuál solo lleva un rato sin que nadie la refute?
---

Una afirmación de un paper puede estar respaldada por cosas muy distintas.

Puede tener una demostración escrita. Puede tener un teorema que ha comprobado el kernel de Lean. Puede tener un certificado que recorrió toda una región con aritmética racional exacta sin usar ni una sola vez un número en coma flotante. O puede tener un «muestreé diez millones de configuraciones y ninguna la rompió».

Las cuatro se imprimen igual: una frase en tipografía con remates que suena verdadera. Y la cuarta vale muchísimo menos que la primera, de una forma que ninguna cantidad de seguridad en la prosa puede arreglar.

Mi último preprint — el del [empaquetamiento de aros anidados en una sartén](/es/blog/count-the-rings) — tiene sesenta páginas en las que aparecen las cuatro, a veces en la misma página. Así que cada afirmación lleva una **etiqueta epistémica** que dice cuál es: `probado`, `certificado por cajas`, `barrido en malla` o `muestreado`. No un visto bueno para el paper. Una etiqueta por afirmación, y un apéndice que empareja cada afirmación computacional con el script que la respalda.

![Una escalera de cuatro etiquetas, cada peldaño más estrecho que el de arriba. Probado: una demostración escrita, la máquina solo la recomprueba. Certificado por cajas: aritmética racional exacta en todo el dominio. Barrido en malla: comprobado en una malla, mudo entre los puntos. Muestreado: no se halló contradicción en las muestras tomadas.](/blog/proved-certified-swept-sampled.png)

El paper lo dice en una sola frase, en los agradecimientos, y defendería esa frase por encima de cualquiera de los teoremas: *la garantía matemática de toda afirmación es la demostración escrita y, cuando una prueba delega una identidad, un cálculo simbólico exacto; el flujo de verificación y los barridos numéricos son control de calidad y evidencia, nunca un sustituto de la prueba.*

Este artículo va de lo que me convenció para ponerme así de pedante. No fue un principio. Fue un certificado que me mintió tres veces, y la forma concreta en que mintió.

## La afirmación que parecía certificada

Uno de los lemas de ese paper trata sobre un quinteto de aros, y cerrarlo exige un enunciado del tipo: *en todo este dominio de parámetros de cuatro dimensiones, esta configuración no cabe.* Eso es justo lo que se certifica computacionalmente, porque el dominio es continuo y no hay nada que enumerar.

El primer intento lo hizo como lo hace todo el mundo: subdividir el dominio en cajas, evaluar en cada una, tirar de programación lineal en las ajustadas. Un revisor adversario — otro modelo, al que se le da el enunciado y se le pide que lo rompa — lo refutó a la primera pasada, y la refutación no fue sutil. Las mallas no tenían cota de Lipschitz, así que nada conectaba los valores en los puntos de muestra con los valores intermedios. El programa lineal corría con tolerancias. Y una de las desigualdades necesarias no estaba certificada en absoluto: estaba *muestreada*.

Eso es pelea limpia y arreglo fácil. La segunda versión se escribió racional-dirigida: aritmética exacta en las esquinas, sin comparaciones en coma flotante en el test de aceptación.

También fue refutada, y esta es la parte que justifica el artículo.

## Por qué una tolerancia no es un pecado pequeño

La segunda versión conservaba una tolerancia: `1e-12`. No como comparación, sino como holgura — la anchura de la banda dentro de la cual dos cantidades contaban como iguales.

Ahora bien, la configuración de la que depende todo el lema es el punto áureo, donde los parámetros valen todos $\varphi$. Y en ese punto la configuración es **exactamente tangente**. Los aros se tocan. El margen de factibilidad ahí no es pequeño: es cero.

![Curva esquemática del margen de factibilidad frente a un parámetro de la configuración. La curva sube hasta tocar el cero en un único punto — el punto áureo — y es negativa en todo lo demás. Una banda roja de grosor épsilon rodea la línea del cero, de modo que el punto tangente queda dentro de la banda: la respuesta exacta es «no cabe», y el test con tolerancia responde «cabe».](/blog/proved-certified-swept-sampled-fig-1-es.png)

En un punto donde el margen es cero, una tolerancia no introduce un error pequeño. Cambia la respuesta. La banda de aceptación de grosor $\varepsilon$ se traga la tangencia, y el certificado dice *cabe* justo en la configuración de la que depende la prueba. En todo el resto del dominio la tolerancia es inofensiva, que es lo que la hace tan mala: el test se equivoca solo donde la pregunta es delicada, y no avisa. No peta nada. Nada parece sospechoso. Tienes una ejecución en verde y un lema falso.

Conviene no exagerar la acusación. La tolerancia no volvió falso el lema — el lema es cierto, y el certificado final lo demuestra. Lo que hizo la tolerancia fue convertir el certificado en *no evidencia*. Llevaba todo el rato informando de una propiedad de su propia banda de aceptación en vez de una propiedad de la geometría.

## Lo que cuesta dejar de asumir

La tercera versión reparó la tangencia pero seguía apoyándose en `mpmath` para la trigonometría inversa, así que seguía descansando en que una librería de coma flotante acertara con el arcoseno de números cerca de una tangencia. La cuarta versión quita también eso, y su forma merece describirse porque es en lo que acaba consistiendo «certificado» cuando aprietas:

- $\arcsin$ se acota por una **serie racional pura**, con $\sin^2$ y $\cos$ encajonados en $\mathbb{Q}$ mediante un resto de Lagrange alternante — así que la cota es un teorema sobre la serie, no una llamada a una librería.
- Toda suma y resta de intervalos usa redondeo dirigido, avanzando un ULP hacia fuera tras cada operación, de modo que el intervalo es una cota exterior de verdad y no una esperanza.
- $\pi$ y $2\pi$ quedan encerrados entre **cotas racionales** demostradas con esa misma serie. Racionales no son, claro; las cotas sí, y cotas es todo lo que el certificado necesita. Uno que mete un float para $\pi$ acaba de asumir parte de lo que está comprobando.
- La `math.asin` de la librería se sigue llamando — como **oráculo al que no se cree**. Propone dónde mirar; decide un bracket con certeza en cada dirección. Si el oráculo mintiera, la búsqueda se ensancharía en vez de aceptar.

El resultado cierra el dominio con cero tolerancias, cero exclusiones y ningún hecho en coma flotante asumido en ninguna parte.

Una cosa cambió bajo ese lema después, y merece decirse en vez de dejar que el lector lo descubra: la segunda versión del paper demuestra el umbral global por una ruta distinta y mucho más corta, así que este quinteto pertenece a un programa de casos especializados que el teorema global ya no necesita como premisa. El certificado sigue siendo correcto y sigue certificando lo que dice certificar. Simplemente ya no sostiene nada — lo que no cambia nada de la lección, y lo cambia todo respecto a cuánto peso conviene ponerle.

![Cuatro paneles en fila, uno por versión del certificado. v1: mallas sin cota de Lipschitz, un LP con tolerancias, una desigualdad solo muestreada. v2: racional-dirigido y aun así refutado, porque la tolerancia de 1e-12 engordaba la variedad tangente en el punto áureo. v3: incorpora el teorema del trío que aportó el refutador, pero aún se apoya en mpmath. v4: serie racional con resto de Lagrange alternante, y arcoseno usado como oráculo al que no se cree.](/blog/proved-certified-swept-sampled-fig-2-es.png)

Y el punto áureo, el que la tolerancia llevaba tapando, acabó cerrándose algebraicamente y no numéricamente. La esquina doble aparente resulta ser un fantasma — una tercera ligadura la vacía — y la esquina real no cabe en la disposición mural, porque el arco inferior se pasa por $1{,}4 \times 10^{-4}$. Ese margen lo es todo: una diezmilésima, en el único sitio donde una banda de `1e-12` venía cantando victoria. El testigo correcto apila el aro pequeño radialmente, y en el punto áureo todas las condiciones caen en identidades exactas en $\mathbb{Q}[\sqrt5]$, con margen $1/\varphi^3$.

## Una etiqueta equivocada es peor que una débil

Las cuatro etiquetas solo sirven si son honestas, y el modo de fallo no es la etiqueta débil. Es la etiqueta demasiado fuerte.

La misma pasada adversaria que mató mi certificado leyó también un borrador sobre sartenes cuadradas, rederivó toda el álgebra exacta — la cuártica, la identidad $b_\square(X) = X - 1$, los polinomios de la escalera — y la confirmó sin excepción. Y entonces encontró lo que yo no había declarado: una afirmación marcada como *demostrada* que solo estaba demostrada para $\alpha \ge 1$. Para $\alpha < 1$ el argumento sencillamente no estaba. Nadie lo había notado porque la etiqueta decía que la cuestión estaba zanjada, y una cuestión zanjada no se vuelve a leer.

Una etiqueta de `muestreado` no es peligrosa. Todo el mundo sabe qué hacer con ella: apoyarse poco, o ir y demostrar la cosa. Un `demostrado` sobre una afirmación que vale en la mitad de su rango es peligroso precisamente porque se cree, y porque sostiene en silencio todo lo que cuelga de él.

La otra mitad de esa honestidad es admitir dónde paraste. Algunas regiones de este paper se declaran **agotadas por coste**: el barrido corrió hasta su presupuesto, cubrió lo que cubrió, y el paper dice que la región no se terminó en lugar de fingir que lo cubierto era el todo. Una afirmación etiquetada como declaración honesta vale más que la misma afirmación etiquetada como demostrada, porque con la primera el lector puede planificar y con la segunda se le engaña.

## Verificación que mejora el resultado

Todo esto se lee fácil como control de daños, así que aquí va la otra dirección, que me sorprendió más.

Uno de los lemas difíciles, sobre una derivada que se mantiene por encima de 1 en una frontera de bloqueo, volvió *confirmado*: rederivado desde cero por una ruta distinta, validado en aritmética racional exacta en treinta puntos, contrastado contra diferencias finitas hasta veintinueve decimales, y machacado en mallas adversarias de unos diez millones de puntos sin contraejemplo. Cero refutaciones.

Pero el verificador no se quedó en confirmar. Encontró que una hipótesis de mi borrador — que el parámetro tenía que superar cierto umbral — era **un artefacto de mis coordenadas** y no una restricción real, así que el resultado vale en todas partes. Y encontró que mi constante de cierre era subóptima: donde yo cerraba el argumento en el número áureo, la desigualdad correcta lo cierra en la constante de Tribonacci, que es estrictamente mejor y encaja con otro resultado del paper.

Esa es la parte de la verificación que nadie anuncia. Una pasada cuyo único trabajo es atacar la afirmación te devuelve a veces una afirmación más fuerte que la que escribiste, y cuatro documentos que arrastraban un «módulo este lema» pudieron soltarlo.

## Para qué sirve esto fuera de un paper

No creo que las etiquetas sean cosa de matemáticas. Creo que las matemáticas son solo el sitio donde el desajuste da bastante vergüenza como para forzar el asunto.

Tu suite de tests, tu comprobador de tipos, tus pruebas de propiedad y la lectura atenta que hiciste un domingo son cuatro clases distintas de evidencia, con modos de fallo distintos y regiones mudas distintas — y el CI las pinta todas del mismo verde. Un test que pasa es `muestreado`: dice que no pasó nada en las entradas que elegiste. Una prueba de propiedad con generador se acerca a `barrido en malla`: dice que no pasó nada en una forma de entradas, y calla entre ellas. Un tipo está más cerca de `certificado por cajas`: vale en todo un dominio, para las propiedades que sabe expresar. Y la lectura atenta es la única que llega alguna vez a `probado`, las raras veces en que el argumento cabe en una cabeza.

De ahí salen tres cosas, y son las que yo usaría:

**Sé dónde está la tolerancia.** Todo sistema tiene una — un timeout, un reintento, una comparación de floats, un umbral redondeado, un «aproximadamente igual» en un test. Es invisible en casi todas partes y decisiva justo en la frontera, que es el único sitio donde alguien hace una pregunta difícil. Pregúntate cuáles de tus comprobaciones están en verde gracias a ella.

**Etiqueta la afirmación, no el sistema.** «El servicio está testeado» es la frase que lo esconde todo. «Este invariante lo impone un tipo; ese otro, un test con tres entradas; este tercero nos lo creemos porque lleva un año sin romperse» es la frase que permite a otro decidir en qué apoyarse.

**Deja que algo adversario lo lea sin haberlo escrito.** No un revisor que compartirá tu encuadre: uno que recibe el enunciado solo y tiene el encargo de romperlo. A mí me refutó tres veces un mismo lema, y la cuarta versión es la única que firmaría. También encontró la etiqueta exagerada que yo ya había dejado de ver.

Lo último es la razón de que mis papers lleven ahora un apéndice que nadie ha pedido, emparejando cada afirmación computacional con el script que hay detrás y con un registro por rondas de cada refutación y cada reparación. Es la parte menos lucida del trabajo y la única que permitiría pillarme en un error.

*El preprint está [aquí](https://arxiv.org/abs/2609.15554), el [código, los certificados y los informes de verificación están abiertos](https://github.com/JaviMaligno/calamares), y las matemáticas de las que van esos certificados están en [el artículo compañero](/es/blog/count-the-rings). Una costumbre emparentada, desde otro ángulo: [el instrumento falla a tu favor](/es/blog/the-instrument-fails-in-your-favour).*
