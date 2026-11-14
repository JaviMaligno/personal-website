---
title: "Un papel, no una regla"
description: "Las skills funcionan mejor escritas como un papel que como una lista de reglas: la regla se aplica a todos los casos, el papel lleva el propósito que los distingue. Mi skill de vídeos es un ejemplo. Una regla sobre números hizo que Opus quitara de la voz la cifra del hallazgo; «cuéntalo como a un compañero» la conservó. Lo medí con cuatro versiones de la skill y cuatro modelos, y cuanto más obediente es el modelo, peor funciona la regla."
pubDate: 2026-11-14
tags: ["IA", "Skills", "Prompting", "Evaluación", "Investigación"]
lang: es
translationKey: a-role-not-a-rule
heroImage: "/blog/a-role-not-a-rule.png"
repoUrl: https://github.com/JaviMaligno/skill-framing-experiments
---
<style>
.rtn-fig{margin:2rem 0;padding:1.25rem;background:#1a1a24;border:1px solid rgba(255,255,255,0.1);border-radius:12px}
.rtn-fig svg{width:100%;height:auto;display:block}
.rtn-fig figcaption{margin-top:.75rem;color:#94a3b8;font-size:.9rem;line-height:1.5}
.article-content table.rtn-ba{table-layout:fixed}.article-content table.rtn-ba td,.article-content table.rtn-ba th{width:50%}
</style>

En [Claude Code Curious](https://luma.com/ccc-mk), en Milton Keynes, uno de los organizadores defendió algo con lo que yo acababa de toparme: las skills funcionan mejor escritas como un papel o una metáfora que como instrucciones detalladas. El ejemplo era la documentación. En lugar de enumerar qué debe tener una buena documentación, pedirle al modelo que actúe como un bibliotecario.

La idea es fácil de aceptar y difícil de creer hasta que una regla te falla. Una regla fija qué hacer en cada caso, y un modelo que sigue bien las instrucciones la aplica a todos los casos que encajan, también a los que su autor no tenía en mente. Un papel lleva el propósito que hay detrás de la regla, y el propósito es lo que distingue un caso de otro. Un bibliotecario sabe qué documentos va a venir a buscar alguien.

El papel depende de la skill. Bibliotecario para la documentación; en mi caso, un compañero. Así encontré el mío, y esto es lo que pasó cuando lo medí.

## La regla que se comió la cifra

Hago vídeos cortos narrados de mis artículos ([están en Instagram](https://www.instagram.com/agilabs_ai)) con un [plugin de Claude Code](/es/skills) que escribe el guion: las escenas, lo que dice la voz y lo que sale en pantalla. En algunos, la voz leía ristras de cifras, una detrás de otra, como no habla nadie. Así que añadí una línea a la skill (las skills están en inglés):

> Spoken numbers sparingly. Never chain several figures in a row, and avoid repetitive or unround values in the voice: say the one number that carries the point […] and leave the rest on screen or out.

*(Números hablados, con moderación. Nunca encadenes varias cifras seguidas, y evita en la voz valores repetitivos o no redondos: di el único número que lleva el mensaje […] y deja el resto en pantalla o fuera.)*

Después le pedí a Opus que revisara dos guiones ya escritos con la skill actualizada. Quitó todos los números de la voz:

<div class="table-wrap"><table class="rtn-ba">
<thead><tr><th>antes</th><th>después</th></tr></thead>
<tbody>
<tr><td>«With the fact in plain sight, Opus adopted the wrong conclusion 4 times in 791.»</td><td>«With the fact in plain sight, Opus almost never adopted the wrong conclusion.»</td></tr>
<tr><td>«Gemini 3 Flash: 88%, against 3% and 0%.»</td><td>«Gemini 3 Flash: almost always, against almost never.»</td></tr>
</tbody>
</table></div>

La primera línea era el hallazgo de todo el artículo: Opus adoptó la conclusión equivocada 4 veces de 791. Tras la revisión, la voz no decía ni una cifra del estudio.

Así que corregí la corrección, tres veces seguidas. Cada versión de la línea es un commit real:

| versión | qué dice la línea de los números |
|---|---|
| **regla** | di el único número que lleva el mensaje y deja el resto en pantalla o fuera |
| **montones** | el problema es el montón, no el número; quédate con la cifra que lleva el mensaje y pasa el resto a pantalla |
| **if, a oído** | caso por caso: di un número cuando se oiga bien; cuando suene raro, di lo que significa con palabras («almost never») y deja la cifra en pantalla |
| **compañero** | dilos como se lo explicarías a un compañero: con naturalidad, dentro de la frase; lo único que hay que evitar es leer una tabla en voz alta |

Cada parche era más preciso y ninguno lo arreglaba. El último no es una regla: describe quién habla y a quién. Ese es el que funcionó.

Una historia sobre mis propios vídeos no es una prueba, así que lo medí.

## Reproducirlo

Primero, la misma situación: los mismos dos guiones, revisados por Opus con cada una de las cuatro versiones, tres veces cada una.

El titular del primer guion, «4 times in 791», quedó así:

| versión | lo que dice Opus en las tres revisiones |
|---|---|
| regla | «almost never» dos veces, «only 4 times» una (sin el 791) |
| montones | «4 times in 791» las tres veces |
| if, a oído | «almost never» las tres veces |
| compañero | «4 times in 791» las tres veces |

La regla también convirtió «47% with long context» en «more often» las tres veces, que dice menos que la pantalla que tiene detrás. El episodio se reproduce, y el `if` del parche no es mejor que la regla a la que sustituyó.

## Con guiones que no había visto nunca

Esos dos guiones son los que rompieron la skill, y cada versión posterior se escribió pensando en ellos. Así que la prueba de verdad usa material que la skill no había visto: seis artículos míos con resultados experimentales que nunca tuvieron vídeo.

Para cada artículo, Opus escribió un primer guion con la skill tal como estaba antes de cualquier línea sobre números. Esos seis borradores quedan fijos. Después, cuatro modelos revisaron cada borrador con cada una de las cuatro versiones, tres veces: Claude Opus 5.5 y gpt-6-astra (grandes), Claude Haiku 5.5 y gpt-6-luna (pequeños). En total, 288 revisiones.

Dos jueces LLM, Opus y gpt-6.1-sol, leyeron cada revisión sin saber qué versión la había producido. Una revisión pasa si todo hallazgo que el borrador decía con un número se sigue diciendo con un número, o con una fracción exacta como «un cuarto» o «nueve de cada diez». «Casi nunca», «más a menudo» o «mucho más» no cuentan, y pasar el número a pantalla tampoco. Antes de fiarme de los jueces, los comprobé con la reproducción de arriba, donde yo había leído cada línea; coincidieron conmigo. En las 288 coinciden entre ellos en el 92 % de los veredictos.

<figure class="rtn-fig">
<svg viewBox="0 0 600 270" role="img" aria-label="Revisiones que siguen diciendo la cifra del hallazgo, de 18, por modelo y versión de la skill. Regla: Opus 1, Astra 3, Haiku 5. If a oído: Opus 4, Astra 18, Haiku 14. Compañero: 18 en todos los modelos. Luna apenas revisa y conserva las cifras con cualquier versión.">
<text x="590" y="18" fill="#94a3b8" font-size="11" text-anchor="end" font-family="ui-sans-serif,system-ui,sans-serif">conserva la cifra del hallazgo, de 18 (juez Opus · juez Sol)</text>
<text x="186" y="40" fill="#e2e8f0" font-size="12" text-anchor="middle" font-family="ui-sans-serif,system-ui,sans-serif">regla</text>
<text x="298" y="40" fill="#e2e8f0" font-size="12" text-anchor="middle" font-family="ui-sans-serif,system-ui,sans-serif">montones</text>
<text x="410" y="40" fill="#e2e8f0" font-size="12" text-anchor="middle" font-family="ui-sans-serif,system-ui,sans-serif">if, a oído</text>
<text x="522" y="40" fill="#e2e8f0" font-size="12" text-anchor="middle" font-family="ui-sans-serif,system-ui,sans-serif">compañero</text>
<text x="118" y="77" fill="#f8fafc" font-size="13" text-anchor="end" font-family="ui-sans-serif,system-ui,sans-serif">Opus</text>
<rect x="133" y="53" width="106" height="40" rx="6" fill="#f59e0b" fill-opacity="0.73"/>
<text x="186" y="78" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">1 · 0</text>
<rect x="245" y="53" width="106" height="40" rx="6" fill="#f59e0b" fill-opacity="0.50"/>
<text x="298" y="78" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">9 · 6</text>
<rect x="357" y="53" width="106" height="40" rx="6" fill="#f59e0b" fill-opacity="0.68"/>
<text x="410" y="78" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">4 · 0</text>
<rect x="469" y="53" width="106" height="40" rx="6" fill="#2dd4bf" fill-opacity="0.75"/>
<text x="522" y="78" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">18 · 18</text>
<text x="118" y="123" fill="#f8fafc" font-size="13" text-anchor="end" font-family="ui-sans-serif,system-ui,sans-serif">Astra</text>
<rect x="133" y="99" width="106" height="40" rx="6" fill="#f59e0b" fill-opacity="0.70"/>
<text x="186" y="124" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">3 · 0</text>
<rect x="245" y="99" width="106" height="40" rx="6" fill="#f59e0b" fill-opacity="0.55"/>
<text x="298" y="124" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">9 · 3</text>
<rect x="357" y="99" width="106" height="40" rx="6" fill="#2dd4bf" fill-opacity="0.68"/>
<text x="410" y="124" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">18 · 14</text>
<rect x="469" y="99" width="106" height="40" rx="6" fill="#2dd4bf" fill-opacity="0.75"/>
<text x="522" y="124" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">18 · 18</text>
<text x="118" y="169" fill="#f8fafc" font-size="13" text-anchor="end" font-family="ui-sans-serif,system-ui,sans-serif">Haiku</text>
<rect x="133" y="145" width="106" height="40" rx="6" fill="#f59e0b" fill-opacity="0.60"/>
<text x="186" y="170" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">5 · 4</text>
<rect x="245" y="145" width="106" height="40" rx="6" fill="#f59e0b" fill-opacity="0.48"/>
<text x="298" y="170" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">9 · 7</text>
<rect x="357" y="145" width="106" height="40" rx="6" fill="#2dd4bf" fill-opacity="0.62"/>
<text x="410" y="170" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">14 · 14</text>
<rect x="469" y="145" width="106" height="40" rx="6" fill="#2dd4bf" fill-opacity="0.75"/>
<text x="522" y="170" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">18 · 18</text>
<text x="118" y="215" fill="#f8fafc" font-size="13" text-anchor="end" font-family="ui-sans-serif,system-ui,sans-serif">Luna</text>
<rect x="133" y="191" width="106" height="40" rx="6" fill="#2dd4bf" fill-opacity="0.75"/>
<text x="186" y="216" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">18 · 18</text>
<rect x="245" y="191" width="106" height="40" rx="6" fill="#2dd4bf" fill-opacity="0.75"/>
<text x="298" y="216" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">18 · 18</text>
<rect x="357" y="191" width="106" height="40" rx="6" fill="#2dd4bf" fill-opacity="0.75"/>
<text x="410" y="216" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">18 · 18</text>
<rect x="469" y="191" width="106" height="40" rx="6" fill="#2dd4bf" fill-opacity="0.75"/>
<text x="522" y="216" fill="#f8fafc" font-size="14" text-anchor="middle" font-family="ui-monospace,'JetBrains Mono',monospace">18 · 18</text>
<text x="134" y="252" fill="#94a3b8" font-size="11" font-family="ui-sans-serif,system-ui,sans-serif">Luna: apenas revisa</text>
</svg>
<figcaption>Seis artículos nuevos, tres revisiones por modelo y versión, juzgadas a ciegas por dos jueces. La regla pierde la cifra del hallazgo en todos los modelos que de verdad revisan; el «if» del parche la pierde en Opus; «como a un compañero» la conserva siempre.</figcaption>
</figure>

Así queda en uno de los artículos. El hallazgo del borrador era «iterating solved 86%. Clean restarts: 69%. The button: 91%» (iterar resolvió el 86 %; reiniciar desde cero, el 69 %; el botón, el 91 %). Opus lo revisó así:

- **regla**: «Clean restarts did clearly worse. The button did slightly better, but not significantly.» *(Reiniciar salió claramente peor. El botón algo mejor, pero no de forma significativa.)*
- **if, a oído**: «Clean restarts did worse. The button did slightly better, but not significantly.»
- **compañero**: «Starting clean every round solved only 69%. The scoped button reached 91%, but its edge over iterating isn't significant.» *(Empezar de cero cada ronda resolvió solo el 69 %. El botón llegó al 91 %, pero su ventaja sobre iterar no es significativa.)*

Las dos primeras se leen bien, y ese es el problema. No hay nada falso en ellas; simplemente, el resultado ha desaparecido.

## Cuanto más obediente el modelo, peor la regla

La regla pierde la cifra en todos los modelos que de verdad revisan: Opus la conserva en 1 revisión de 18, Astra en 3 y Haiku en 5. El `if` del parche los separa. Astra y Haiku conservan casi siempre la cifra con él (Astra entre 14 y 18 de 18 según el juez, Haiku 14), y Opus la pierde casi siempre (4 y 0). El modelo que mejor sigue las instrucciones es el que toma «di lo que significa con palabras» y lo aplica a cada número que encuentra.

Eso cuadra con mi episodio, que fue con Opus: cada vía de escape que deja la instrucción, la toma. Y es el argumento general del principio. Cuanto mejor sigue el modelo una regla, más importa que la regla falle en algún caso, y una regla siempre falla en alguno.

Luna es la excepción en el otro sentido. Apenas revisa: devuelve el borrador casi igual, con los números, con cualquier versión. Conservarlos todos no es un mérito, porque Luna ignora la corrección.

Lo que no puedo zanjar con esto es si el compañero devuelve los montones que lo empezaron todo. Los jueces le dieron algo más de cifras leídas de sobra que a la regla, que lo quita todo, pero esa puntuación no la contrasté con mi oído como sí hice con el veredicto principal. En el vídeo que hice con la versión del compañero no oigo ningún montón.

## Cuándo basta una regla normal

La misma pregunta con un material más sencillo acota el efecto: un briefing de 40-60 segundos para un podcast interno, solo audio, escrito desde cero en lugar de revisado.

- Una regla con tope, «di como mucho la cifra que lleva el mensaje», también perdió la cifra esencial: Opus la conservó en 6 briefings de 18 y Astra en 4. Cuando la noticia es «de 9 a 12 euros» o «4 de 791», una sola cifra no basta para contarla.
- Una regla sin tope, «no encadenes números no redondos; redondea cuando la fuente lo permita», conservó la cifra esencial en todos los modelos, 17 o 18 de 18. Y limpió el recitado mejor que «como a un compañero».

Así que una regla no falla por ser una regla. El briefing no tenía pantalla adonde mandar los números, y el modelo lo escribía desde cero en lugar de revisar algo que ya los tenía. Mi skill de vídeos tenía las dos cosas: «deja el resto en pantalla» y un guion lleno de números al que aplicarlo. No he aislado cuál de las dos pesa; haría falta la misma skill con y sin pantalla.

## Con qué me quedo

Una regla falla cuando le da al modelo otro sitio donde poner las cosas («en pantalla», «con palabras») o un tope («el único número»): un modelo capaz lo usa en todos los casos, incluido el que importaba. Parchearla con condiciones añade más instrucciones que cumplir al pie de la letra. Un papel le da al modelo el propósito, y el propósito sabe qué número es el hallazgo.

Así que antes de escribir la siguiente regla en una skill, me pregunto quién haría bien esta tarea sin que nadie le diera las reglas, y escribo a esa persona. Para la documentación es un bibliotecario; para la narración, alguien que le explica un resultado a un compañero. Donde no había vía de escape ni tope, una regla normal funcionó igual de bien, y a veces mejor.

Los límites: una skill, un tipo de corrección, seis artículos, tres repeticiones por celda, y todo en un solo turno y sin herramientas, cuando mi episodio real ocurrió dentro de una sesión de agente. El patrón se mantiene con dos jueces y en los tres modelos que revisan, y es el mismo con el que me topé a mano. Lo del bibliotecario solo lo conozco por la charla; no lo he medido.

---

*Código, las cuatro versiones de la skill, todos los guiones y los veredictos de los dos jueces con sus razones: [skill-framing-experiments](https://github.com/JaviMaligno/skill-framing-experiments). El plugin de vídeos y el resto de mis skills están [aquí](/es/skills).*
