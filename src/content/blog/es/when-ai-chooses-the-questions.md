---
title: "Cuando la IA elija las preguntas"
description: "Resolver problemas abiertos puede abrir preguntas nuevas. Qué ocurre si la IA aprende también a elegirlas, qué valor conserva comprender y qué debería premiar la academia."
pubDate: 2026-09-23
tags: ["IA", "Matemáticas", "Investigación", "Academia"]
lang: es
translationKey: when-ai-chooses-the-questions
heroImage: "/blog/when-ai-chooses-the-questions.png"
linkedinImage: "/blog/when-ai-chooses-the-questions.png"
linkedinLinks:
  - label: "Anuncio de OpenAI"
    url: "https://openai.com/index/advisory-group-on-mathematics-and-ai/"
  - label: "On Proof and Progress in Mathematics"
    url: "https://arxiv.org/abs/math/9404236"
  - label: "Estadísticas mensuales de arXiv"
    url: "https://arxiv.org/stats/monthly_submissions"
---

El 21 de septiembre, OpenAI [anunció que un modelo interno había resuelto más de cien problemas matemáticos abiertos](https://openai.com/index/advisory-group-on-mathematics-and-ai/). Dos semanas antes había [publicado una demostración del problema de Navier–Stokes](https://openai.com/index/navier-stokes-solution/), acompañada de una formalización en Lean. Hay diferencias entre ambos anuncios: del segundo tenemos un argumento que estudiar; el comunicado sobre los cien problemas no incluye su lista ni sus demostraciones. El Instituto Clay, por su parte, [mantiene su proceso de evaluación](https://www.claymath.org/news/navier-stokes-announcement/) del resultado de Navier–Stokes.

Sobre [qué significa el resultado de Navier–Stokes](/es/blog/navier-stokes-blows-up) ya escribí. Ahora me interesa qué ocurre después. Si una IA puede resolver preguntas que llevábamos décadas sin contestar, ¿qué nuevas preguntas podremos hacer? Y si también aprende a elegirlas mejor que nosotros, ¿en qué consistirá participar en las matemáticas?

Para llegar ahí conviene empezar por algo que los titulares suelen dar por supuesto: por qué hay problemas abiertos y por qué algunos nos importan.

## De dónde salen las preguntas

Un problema está abierto cuando no conocemos una solución que responda a su formulación con las garantías exigidas. Eso puede ocurrir porque nos faltan técnicas, porque no hemos encontrado la manera adecuada de plantearlo o porque apenas se ha trabajado en él. La antigüedad de una pregunta dice cuánto tiempo lleva formulada; por sí sola no mide cuánta inteligencia hace falta para contestarla. Y una regularidad observada en millones de ejemplos puede seguir sin ser una demostración de que siempre se cumple.

Tampoco existe un inventario definitivo de todo lo que falta saber. Cada definición permite formular preguntas; cada teorema permite examinar sus hipótesis; cada conexión entre dos campos ofrece cosas que antes ni siquiera sabíamos preguntar. Resolver problemas cambia las condiciones en las que aparecen los siguientes.

Podemos verlo sin recurrir a una gran conjetura. Si una demostración utiliza una condición de simetría, podemos investigar qué parte del resultado sobrevive cuando la quitamos. Si aparece un contraejemplo, podemos intentar identificar qué lo hace fallar y qué casos quedan a salvo. Si el argumento funciona en objetos aparentemente distintos, podemos buscar la estructura que comparten. Una respuesta concreta puede acabar convirtiéndose en una teoría.

Por eso contar preguntas abiertas y preguntas resueltas sería una forma bastante pobre de medir el progreso. Es fácil fabricar variantes de un enunciado. Lo difícil es encontrar una pregunta cuya respuesta cambie lo que somos capaces de entender.

## Quién decide qué merece la pena

Ese juicio no lo emite una autoridad central. Los investigadores proponen problemas; otros deciden dedicarles tiempo; los seminarios, las revistas, los directores de tesis y la financiación amplifican unas direcciones más que otras. Las listas famosas hacen visible una selección. El propio Clay [explica que eligió sus problemas](https://www.claymath.org/news/navier-stokes-announcement/) por su profundidad y por su capacidad de impulsar estructuras y métodos nuevos, con consecuencias que excedieran la pregunta original.

Hay criterios que podemos discutir: cuánto unifica un problema, qué obstáculos permite entender, qué técnicas podría desbloquear, qué aplicaciones sugiere. También intervienen la belleza, la sorpresa y el interés de explorar algo que todavía no tiene utilidad reconocible. Esos criterios pueden entrar en conflicto. Un problema puede ser fértil para un campo y marginal para otro. Y el prestigio de quien lo propone puede conseguirle una atención que otra pregunta igualmente buena no recibe.

El criterio matemático se forma trabajando: viendo qué intentos fracasan, qué hipótesis hacen el trabajo de verdad y qué ideas sobreviven cuando cambiamos el ejemplo. No consiste solo en reconocer nombres famosos.

La IA puede intervenir en todo ese proceso. Puede buscar contraejemplos, comparar casos, sugerir una generalización y ayudar a descubrir que dos resultados expresan algo parecido. Ya hay antecedentes anteriores a los modelos actuales: [un trabajo de Davies y colaboradores publicado en Nature en 2021](https://www.nature.com/articles/s41586-021-04086-x) utilizó aprendizaje automático para detectar relaciones que orientaron nuevas conjeturas y resultados en teoría de nudos y teoría de representaciones. Los matemáticos aportaban la interpretación y el desarrollo de esas pistas. Era una colaboración que ayudaba a formular matemáticas nuevas.

Mi expectativa es que herramientas más capaces amplíen las preguntas que podemos abordar. Una dirección que antes parecía inviable puede volverse investigable si explorar ejemplos o demostrar los lemas preliminares cuesta mucho menos. Pero no hay garantía de que esa capacidad se emplee en las preguntas más fértiles. Un sistema premiado por acumular soluciones tendrá incentivos para elegir problemas que pueda cerrar. Un sistema premiado por impresionar tendrá incentivos para elegir nombres reconocibles. Ninguno de esos objetivos coincide necesariamente con producir comprensión.

## ¿Y si la IA desarrolla su propio criterio?

Y aquí aparece la respuesta tranquilizadora: nosotros pondremos el criterio y la máquina hará el trabajo.

No creo que podamos dar por permanente ese reparto.

Parte del criterio consiste en anticipar consecuencias: qué idea conectará resultados, qué experimento distinguirá dos explicaciones, qué pregunta abrirá una línea de trabajo. No veo una razón suficiente para declarar que una IA nunca podrá aprender a hacer eso. Tampoco basta con que un modelo proponga diez preguntas que suenan sofisticadas para concluir que ya lo hace. La prueba estaría en seguir sus propuestas: comprobar si producen métodos reutilizables, conexiones inesperadas y trabajo posterior que merezca la pena.

Conviene distinguir dos saltos. Uno es aprender a elegir bien según los criterios que ya usamos. Otro es proponer una dirección que esos criterios descarten inicialmente y conseguir que después revisemos nuestro juicio. Ese segundo salto se parece más a desarrollar criterio propio. Reconocerlo exigiría tiempo y resultados; no se demostraría preguntándole al modelo si tiene curiosidad.

Además, la procedencia aprendida de un criterio no lo invalida automáticamente. Nuestro gusto también se forma con lecturas, maestros, ejemplos y recompensas institucionales. La cuestión práctica es si el sistema puede revisar lo aprendido a la luz de lo que descubre, y si sus elecciones siguen teniendo valor fuera de la evaluación para la que fue entrenado.

Incluso en ese escenario quedaría una diferencia entre detectar una dirección matemáticamente prometedora y decidir cuánto queremos invertir en ella, quién tendrá acceso a sus resultados o qué necesidades humanas priorizamos. La capacidad técnica para recomendar un rumbo no concede por sí sola autoridad para fijar los fines. Ahí también importa quién controla el sistema: una agenda elegida por IA puede estar respondiendo a los incentivos de la empresa que la entrena.

## Consumidores de verdades

¿Nos convertiríamos entonces en consumidores de verdades?

Ya consumimos muchas verdades que no hemos descubierto. Casi todo lo que aprende un matemático fue pensado antes por otra persona. Sin embargo, estudiar una demostración puede cambiar profundamente lo que sabe hacer. La autoría nunca ha sido una condición necesaria para adquirir intuición. Que el autor sea una máquina tampoco implica, por sí solo, que el resultado sea imposible de comprender.

Lo que sí importa es la forma en que llega ese resultado. Un certificado de corrección, una explicación y una técnica que puedo reutilizar ofrecen cosas diferentes. Una verificación formal comprueba que una conclusión se sigue de unas definiciones e hipótesis dentro de un sistema. Interpretar qué se ha formalizado y por qué importa requiere otro trabajo. Y aprender a reconocer cuándo conviene usar esa idea exige todavía más.

![Corrección, comprensión y criterio requieren evidencias distintas: demostrar, reutilizar una idea y justificar qué merece estudiarse.](/blog/when-ai-chooses-the-questions-criteria-es.png)

*Una prueba correcta no establece, por sí sola, que alguien haya comprendido la idea ni que elegir ese problema fuera una buena decisión.*

En [On Proof and Progress in Mathematics](https://arxiv.org/abs/math/9404236), Thurston defendía en 1994 que el progreso matemático debía examinarse por lo que permite comprender a las personas. Su ensayo describe la distancia entre una demostración escrita y las distintas maneras de entenderla, así como el esfuerzo necesario para transmitir esas ideas. Esa preocupación precede a los modelos generativos.

Una IA podría ayudar también en esa transmisión: encontrar un caso sencillo, explicar dónde falla una intuición, construir un contraejemplo o buscar otra demostración. La comprensión humana podría crecer gracias a resultados que nadie habría obtenido por su cuenta. Para saber si está ocurriendo, habría que mirar lo que el lector es capaz de hacer después: reconocer una situación nueva, adaptar el argumento, detectar un límite. Sentir que una explicación es clara no basta.

También cabe un escenario más difícil: que encontremos resultados correctos cuyos métodos apenas podamos asimilar, o que la producción avance mucho más deprisa que nuestra capacidad de estudiarla. Podríamos aprovechar algunas consecuencias sin dominar el mecanismo completo. Si además la IA fuera mejor encontrando aplicaciones, el entendimiento humano podría dejar de ser necesario para ciertas partes del progreso técnico.

Eso no lo volvería carente de valor. Entender permite participar en las decisiones, enseñar, discutir y mantener independencia intelectual. Y comprender algo puede ser valioso para quien lo comprende aunque otra inteligencia pudiera hacerlo mejor. No hay que demostrar que aprender nos hace económicamente insustituibles para querer seguir aprendiendo. Pero tampoco conviene prometer que conservar ese valor resolverá por sí solo el problema del empleo académico.

## Qué tendría que premiar la academia

Ahí entra la universidad. Una parte de la formación investigadora consiste en aprender haciendo trabajo que termina en un resultado original. Si ese resultado se puede obtener con mucha menos intervención humana, habrá que evaluar de forma más directa qué ha aprendido el investigador y qué ha aportado. Aumentar el número de publicaciones exigidas conservaría la métrica mientras se deteriora su significado.

La escala ya merece atención. arXiv pasó de [185.692 nuevos envíos en 2022](https://info.arxiv.org/about/reports/2022_arXiv_annual_report.pdf) a [284.486 en 2025](https://info.arxiv.org/about/reports/2025_arXiv_annual_report.pdf): un crecimiento de aproximadamente el 53 %. Y la tendencia continúa en 2026: sumando las [estadísticas mensuales de arXiv](https://arxiv.org/stats/monthly_submissions), entre enero y agosto se registran 230.322 envíos, frente a 181.595 en los mismos ocho meses de 2025, un 26,8 % más. Septiembre sigue incompleto en la fecha de consulta, el 21 de septiembre de 2026.

Son envíos al repositorio en el conjunto de sus disciplinas, no artículos de matemáticas revisados por pares. La serie no aísla el efecto de la IA; el [informe de 2025 identifica el aumento de manuscritos generados con IA](https://info.arxiv.org/about/reports/2025_arXiv_annual_report.pdf) como un reto para la plataforma.

![Nuevos envíos a arXiv de enero a agosto: 120.343 en 2022, 133.741 en 2023, 158.079 en 2024, 181.595 en 2025 y 230.322 en 2026. Todas las disciplinas y el mismo periodo en cada año.](/blog/when-ai-chooses-the-questions-arxiv-es.png)

*Elaboración propia a partir del [CSV mensual de arXiv](https://arxiv.org/stats/get_monthly_submissions), consultado el 21 de septiembre de 2026. Se comparan enero–agosto de cada año: envíos nuevos, no revisiones ni publicaciones con revisión por pares.*

En mi caso, tengo un paper anterior al uso de IA y cuatro posteriores. Es un caso n=1, con trabajos y periodos diferentes. Lo que puedo contar con más precisión está en [mi experiencia investigando con IA](/es/blog/writing-a-research-paper-with-ai): los modelos participan en la planificación, la ejecución y la revisión de la ciencia. El número de documentos terminados no cuenta por sí solo qué preguntas elegí bien, qué errores aprendí a detectar o cuánto valor tienen los resultados.

Por eso creo que el modelo académico que usa el volumen de papers como sustituto de la aportación intelectual está perdiendo su justificación a gran velocidad. Una reforma tendría que dar más peso a contribuciones que se puedan examinar: una pregunta bien motivada, una herramienta reutilizable, una comprobación independiente o una explicación que permita a otros trabajar con una idea. También tendría que reconocer el tiempo dedicado a revisar, ordenar y enseñar lo que se descubre.

La formación necesitaría oportunidades reales de practicar el razonamiento, junto con oportunidades de usar estas herramientas con criterio. Pedir a alguien que adapte una demostración al cambiar una hipótesis dice algo distinto de pedirle que entregue un texto correcto. Si la IA participa, interesa examinar cómo se eligió la pregunta, cómo se verificó la respuesta y qué puede explicar el investigador sobre sus límites.

La [carta de matemáticos publicada el 11 de septiembre](https://mathandai.org/) expresa una preocupación relacionada: usar los problemas abiertos como benchmark puede favorecer la producción de respuestas mientras debilita la comprensión y la formación que esos problemas ayudaban a construir. Me parece una advertencia que merece tomarse en serio. La abundancia de resultados debería venir acompañada de recursos para estudiarlos y transmitirlos, y de acceso a las herramientas con las que se producen.

Lo que me interesa de la IA en matemáticas es hasta dónde puede ampliar nuestra capacidad de preguntar. Primero, ayudándonos a explorar lo que hoy no podemos. Después, quizá proponiendo direcciones que no habríamos sabido valorar de antemano.

Si llega ese segundo momento, nuestro papel no estará garantizado por una incapacidad eterna de la máquina. Dependerá también de lo que decidamos construir alrededor de ella: instituciones que permitan aprender, medios para convertir resultados en ideas compartidas y capacidad para intervenir en los fines de la investigación. Que haya más verdades disponibles será un logro. Que podamos hacerlas nuestras seguirá siendo una tarea.
