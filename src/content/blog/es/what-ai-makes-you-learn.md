---
title: "Lo que la IA te obliga a aprender"
description: "Usar bien la IA depende cada vez más de saber cosas que no son técnicas: cómo se entrena un modelo y por qué tira hacia lo más probable, qué evidencia vale para cada tipo de conocimiento, qué responde cada tipo de estudio, cómo se fija una definición. Y por qué acertar respuestas no es lo mismo que tener relación con la verdad."
pubDate: 2026-11-11
tags: ["IA", "Pensamiento Crítico", "Filosofía", "Epistemología"]
lang: es
translationKey: what-ai-makes-you-learn
heroImage: "/blog/what-ai-makes-you-learn.png"
---

Pídele a un modelo de lenguaje que elija un número al azar entre 1 y 10. Con muchísima frecuencia dirá 7. Pídeselo entre 1 y 100 y cada modelo tendrá su favorito: en [unas pruebas con varios modelos](https://www.s-anand.net/blog/llms-random-number-bias/), ChatGPT se quedaba con el 47, Claude 3 Haiku con el 42 y Gemini con el 72. [Un estudio de 2025](https://arxiv.org/abs/2502.19965) lo atribuye a los sesgos de los datos con los que se entrenaron.

No es un fallo curioso. Es la forma más simple de ver cómo funciona por dentro, y explica casi todo lo que conté en [Oráculo o herramienta](/es/blog/oracle-or-tool): por qué la primera respuesta es la convencional, por qué las definiciones derivan hacia el uso popular. Allí defendía que para usar la IA no hace falta saber de todo, sino tener un método. Este artículo trata de lo que hace posible ese método: unas cuantas habilidades, algunas técnicas y la mayoría filosóficas, que la IA vuelve más útiles que nunca.

## Por qué tira hacia lo más probable

Un modelo de lenguaje se entrena para predecir la siguiente palabra de un texto. Se le enseñan cantidades enormes de texto escrito por personas y, mediante un procedimiento llamado descenso de gradiente, se ajustan sus parámetros poco a poco para que se equivoque cada vez menos en esa predicción. El resultado es un modelo que ha aprendido qué suele venir después de qué: la distribución de lo que la gente escribe.

Cuando le preguntas algo, el modelo genera la respuesta eligiendo, palabra a palabra, entre las continuaciones más probables. Y las personas, cuando nos piden un número al azar, también elegimos el 7 mucho más de lo que tocaría. El modelo ha aprendido ese sesgo humano y, al quedarse con lo más probable, lo concentra todavía más.

Después viene una segunda fase de entrenamiento, en la que el modelo se ajusta según las respuestas que las personas valoran mejor. Eso lo vuelve más útil y más educado, pero [reduce la variedad de lo que responde](https://arxiv.org/abs/2310.06452): empuja hacia la respuesta que más gente aprobaría.

Con esto se entienden tres cosas que el usuario nota sin saber por qué:

- **La respuesta convencional.** Sobre nutrición se ha escrito mucho más la recomendación mayoritaria que cualquier alternativa, así que es lo que sale primero.
- **La definición popular.** Si una palabra se usa de forma laxa mil veces por cada vez que se usa con rigor, el modelo tiende al uso laxo, aunque se lo hayas precisado hace tres mensajes.
- **El tono complaciente.** Darte la razón suele valorarse mejor que llevarte la contraria.

Nada de esto lo convierte en inútil. Significa que la respuesta por defecto es la más probable, no la más justificada, y que conseguir la segunda depende de ti.

## Cada conocimiento tiene su evidencia

En el artículo anterior distinguía cinco tipos de conocimiento: formal, experimental, observacional, histórico y personal. Cada uno se apoya en una clase de evidencia distinta, y aquí es donde la IA más tropieza. Dos errores aparecen una y otra vez:

- **Exigir una demostración formal para aceptar un hecho histórico.** Ningún hecho histórico se demuestra como un teorema. Se establece con restos, documentos, testimonios y la convergencia de varias huellas independientes, y eso puede dar un apoyo muy fuerte.
- **Presentar la evidencia empírica como si fuera una necesidad lógica.** Que algo se haya observado siempre no lo convierte en imposible de otra manera.

La lógica interviene en los dos casos. Lo que cambia es cómo se justifican las premisas y con qué fuerza se sigue la conclusión.

Lo he visto en mi propio trabajo. Llevo meses construyendo con IA una ontología, una investigación filosófica sobre qué existe y cómo depende una cosa de otra ([está en un repositorio público](https://github.com/JaviMaligno/god-ontology)). El modelo repetía una y otra vez «esto no demuestra X» ante conclusiones históricas bien apoyadas. Es verdad que no las demostraba: no son de esa clase. Pero esa frase ocupaba el lugar de lo que había que hacer, que era evaluar cuánto apoyo tenían y si alguna alternativa tenía un apoyo comparable. Una alternativa que solo es concebible no pesa lo mismo que una con evidencia detrás.

Lo corregimos y quedó escrito como regla en la metodología del proyecto. Aun así, el mismo fallo volvió a aparecer más tarde, con otra forma: al pasar a una pregunta nueva, el modelo trataba un fundamento que ya estaba justificado como si fuera una simple interpretación pendiente de probar desde cero. Tener la regla por escrito ayuda mucho, pero no garantiza que se aplique. Sigue haciendo falta alguien que sepa reconocer el error.

## Cada estudio responde a una pregunta

Dentro del conocimiento empírico hay además distintos tipos de estudio, y la IA suele citarlos sin decirte cuál es cuál. Es habitual presentarlos como una escalera, con el ensayo aleatorizado arriba y la encuesta abajo. Es más útil verlos como herramientas para preguntas distintas. Ninguno es «el que dice la verdad»: cada uno da un grado de conocimiento distinto, bajo condiciones distintas.

<style>
.wml-fig{background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:1rem;padding:1.25rem 1.25rem .5rem;margin:2rem 0}
.wml-fig svg{display:block;width:100%;height:auto;font-family:'Inter',-apple-system,system-ui,sans-serif}
.wml-fig figcaption{color:#94a3b8;font-size:.85rem;margin:.9rem .25rem;text-align:center;line-height:1.55}
</style>

<figure class="wml-fig">
<svg viewBox="0 0 600 326" role="img" aria-label="Seis tipos de estudio, cada uno con la pregunta que responde bien y su límite: laboratorio, encuesta, cohorte, caso-control, ensayo aleatorizado y metaanálisis. Ninguno es superior en todo; cada uno responde a una pregunta distinta.">
<text x="14" y="26" fill="#94a3b8" font-size="12" font-weight="700" letter-spacing="0.04em">TIPO DE ESTUDIO</text>
<text x="200" y="26" fill="#94a3b8" font-size="12" font-weight="700" letter-spacing="0.04em">RESPONDE BIEN A</text>
<text x="410" y="26" fill="#94a3b8" font-size="12" font-weight="700" letter-spacing="0.04em">SU LÍMITE</text>
<rect x="0" y="44" width="600" height="46" rx="6" fill="rgba(255,255,255,0.04)"/>
<text x="14" y="64" fill="#e2e8f0" font-size="13" font-weight="600">Laboratorio y</text><text x="14" y="80" fill="#e2e8f0" font-size="13" font-weight="600">mecanismos</text>
<text x="200" y="64" fill="#5eead4" font-size="13" font-weight="400">Cómo funciona</text><text x="200" y="80" fill="#5eead4" font-size="13" font-weight="400">una pieza</text>
<text x="410" y="64" fill="#fbbf24" font-size="13" font-weight="400">Cuánto pesa en</text><text x="410" y="80" fill="#fbbf24" font-size="13" font-weight="400">una persona real</text>
<text x="14" y="118" fill="#e2e8f0" font-size="13" font-weight="600">Encuesta</text>
<text x="200" y="110" fill="#5eead4" font-size="13" font-weight="400">Qué se da junto,</text><text x="200" y="126" fill="#5eead4" font-size="13" font-weight="400">en un momento</text>
<text x="410" y="118" fill="#fbbf24" font-size="13" font-weight="400">Qué causa qué</text>
<rect x="0" y="136" width="600" height="46" rx="6" fill="rgba(255,255,255,0.04)"/>
<text x="14" y="164" fill="#e2e8f0" font-size="13" font-weight="600">Cohorte</text>
<text x="200" y="156" fill="#5eead4" font-size="13" font-weight="400">Qué pasa a lo</text><text x="200" y="172" fill="#5eead4" font-size="13" font-weight="400">largo de años</text>
<text x="410" y="164" fill="#fbbf24" font-size="13" font-weight="400">Lo que no se midió</text>
<text x="14" y="210" fill="#e2e8f0" font-size="13" font-weight="600">Caso-control</text>
<text x="200" y="202" fill="#5eead4" font-size="13" font-weight="400">Causas de algo</text><text x="200" y="218" fill="#5eead4" font-size="13" font-weight="400">poco frecuente</text>
<text x="410" y="202" fill="#fbbf24" font-size="13" font-weight="400">Cómo se eligieron</text><text x="410" y="218" fill="#fbbf24" font-size="13" font-weight="400">los casos</text>
<rect x="0" y="228" width="600" height="46" rx="6" fill="rgba(255,255,255,0.04)"/>
<text x="14" y="248" fill="#e2e8f0" font-size="13" font-weight="600">Ensayo</text><text x="14" y="264" fill="#e2e8f0" font-size="13" font-weight="600">aleatorizado</text>
<text x="200" y="248" fill="#5eead4" font-size="13" font-weight="400">Si la intervención</text><text x="200" y="264" fill="#5eead4" font-size="13" font-weight="400">causa el efecto</text>
<text x="410" y="248" fill="#fbbf24" font-size="13" font-weight="400">Duración, dosis y</text><text x="410" y="264" fill="#fbbf24" font-size="13" font-weight="400">población concretas</text>
<text x="14" y="302" fill="#e2e8f0" font-size="13" font-weight="600">Metaanálisis</text>
<text x="200" y="294" fill="#5eead4" font-size="13" font-weight="400">Qué dicen juntos</text><text x="200" y="310" fill="#5eead4" font-size="13" font-weight="400">muchos estudios</text>
<text x="410" y="294" fill="#fbbf24" font-size="13" font-weight="400">Hereda los sesgos</text><text x="410" y="310" fill="#fbbf24" font-size="13" font-weight="400">de lo que combina</text>
</svg>
<figcaption>Ninguno es «el que dice la verdad». Cada diseño responde bien a una pregunta y mal a otra, y lo que importa es cuál es la tuya.</figcaption>
</figure>

Un ensayo aleatorizado es la mejor forma de saber si una intervención causa un efecto, pero suele durar semanas o meses, con una dosis concreta y en una población concreta. Un estudio de cohortes puede seguir a decenas de miles de personas durante décadas, pero no controla todo lo que influye en ellas. Para la pregunta «¿qué le pasa a alguien que sigue esta dieta durante veinte años?» no existe ningún ensayo aleatorizado, y probablemente nunca existirá.

Por debajo hay además una parte estadística que conviene conocer, aunque sea de forma intuitiva:

- **Todo resultado depende de las hipótesis del modelo estadístico** con que se analizó: qué se supuso, qué variables se ajustaron y cuáles no.
- **Que un efecto sea estadísticamente significativo no dice que sea grande.** Con muestras enormes, efectos minúsculos salen significativos.
- **Un riesgo relativo no es un riesgo absoluto.** «Duplica el riesgo» puede significar pasar de 1 entre 10.000 a 2 entre 10.000.

Con esto ya puedes pedirle a la IA lo que importa: qué tipo de estudio respalda cada afirmación, qué pregunta responde ese tipo de estudio y qué supuestos hay detrás. Sobre cómo evaluar el conocimiento cuando estos estudios no bastan, o llegan tarde, escribí un libro entero, [Science Catch-Up](/es/publications).

## Las definiciones derivan

El mismo mecanismo que da el 7 hace que los conceptos converjan hacia lo que más popularmente se entiende por una palabra, no hacia su definición adecuada. En una conversación larga se nota: precisas un término, el modelo lo usa bien un rato y, unos mensajes después, ha vuelto al sentido corriente.

Para manejarlo ayuda distinguir tres cosas que suelen mezclarse:

- **Una estipulación**: «en este texto, X significa esto». Se decide, no se discute.
- **Una descripción del uso**: cómo se usa la palabra de hecho. Se comprueba.
- **Una propuesta sobre la naturaleza de algo**: qué es realmente X. Necesita argumentos.

Ninguna definición demuestra por sí sola que exista lo que define. Y el prestigio de un término tampoco sustituye a una definición que sirva para razonar: en la ontología, el modelo propuso usar un concepto clásico, «perfección ontológica», que resultó demasiado amplio para la distinción que necesitábamos. Hubo que desglosarlo en tres conceptos más precisos.

La herramienta práctica es la misma que en el artículo anterior: escribir las definiciones que importan en un glosario, o en las instrucciones del proyecto, para no tener que repetirlas.

## Acertar no es conocer la verdad

Todo lo anterior gira alrededor de lo mismo. Lo más difícil para una inteligencia artificial es lo que tiene que ver con la verdad, y creo que es precisamente lo que la distingue de la nuestra.

Un modelo sigue patrones. Acumula lo que indican los datos y lo devuelve, sin una noción interna de qué es verdad. A medida que se entrena mejor, aprende a distinguir mejor los tipos de conocimiento, porque aprende mejor cómo los distinguimos nosotros. Eso lo hace más útil. Pero producir respuestas correctas no es lo mismo que tener una relación propia con la verdad.

Mi razón para afirmarlo es teísta, y es la conclusión del trabajo de la ontología, no un añadido:

1. El ser humano está creado a imagen de Dios, y su condición de sujeto racional la recibe de él.
2. Conferir esa condición le corresponde solo a Dios. Tenerla no nos da el poder de conferirla fabricando algo.
3. Una IA es un artefacto construido por seres humanos.
4. Por tanto, fabricar una IA no le da por sí mismo aquello que solo Dios puede dar.

Por eso nuestra razón está orientada a una verdad objetiva que existe y que intentamos alcanzar, y la de la máquina no. El desarrollo completo, con sus objeciones, está en el [repositorio de la ontología](https://github.com/JaviMaligno/god-ontology).

No hace falta compartir este fundamento para sacar la conclusión práctica. Mientras el modelo no tenga una relación propia con la verdad, alguien tiene que tenerla por él. Ese alguien eres tú.

## Por qué la filosofía vuelve a importar

Si juntas todo, la lista de lo que conviene saber para usar bien la IA se parece poco a un curso de programación:

- **Cómo se entrena un modelo**, lo justo para entender por qué tira hacia lo más probable.
- **Epistemología**: qué tipos de conocimiento hay y qué evidencia vale para cada uno.
- **Método científico y estadística básica**: qué pregunta responde cada tipo de estudio y qué supuestos tiene.
- **Definiciones**: cuándo se estipula, cuándo se describe y cuándo hay que argumentar.
- **Una noción de verdad** que no se reduzca a lo que dice la mayoría.

Cuanto más capaces son los modelos, más vale lo que no traen de serie: saber juzgar lo que producen. Esa es una habilidad filosófica, y no hace falta ser filósofo para tenerla. Basta con aprenderla lo suficiente para hacerse las preguntas correctas, y enseñarla a quien tengas cerca.
