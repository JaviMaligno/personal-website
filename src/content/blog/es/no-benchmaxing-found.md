---
title: "No encontré benchmaxing, y las vibes siguen contando"
description: "Hice las dos pruebas que pedía el artículo sobre benchmaxing: problemas públicos de matemáticas frente a variantes nuevas equivalentes, y un director gestionando a sus propios subagentes. Siete modelos, ninguna señal de familiaridad, dos escenarios en techo y un recordatorio: mis pruebas también son benchmarks."
pubDate: 2026-11-26
tags: ["IA", "Evaluación", "Benchmarks", "Agentes"]
lang: es
translationKey: no-benchmaxing-found
heroImage: "/blog/no-benchmaxing-found.png"
repoUrl: https://github.com/JaviMaligno/benchmaxing-probes
linkedinLinks:
  - label: "GSM1k (Zhang et al., 2024)"
    url: "https://arxiv.org/abs/2405.00332"
---

<style>
.nbf-fig{background:#1a1a24;border:1px solid rgba(255,255,255,.1);border-radius:1rem;padding:1.25rem;margin:2rem 0}
.nbf-fig svg{display:block;width:100%;height:auto;font-family:Inter,system-ui,sans-serif}
.nbf-fig figcaption{color:#94a3b8;font-size:.88rem;line-height:1.55;margin:.9rem 0 0;text-align:center}
</style>

[El artículo sobre benchmaxing](/es/blog/benchmaxing) terminaba con dos cabos sueltos. El primero: saber si alguno de estos modelos está benchmaxeado exige una prueba que compare la puntuación de cada modelo en ítems públicos de benchmark con la que saca en variantes nuevas y equivalentes. El segundo: mi sospecha sobre Opus 5 nunca estuvo en las respuestas acotadas, sino en gestionar trabajo a través de agentes, y ninguna de mis pruebas medía eso.

Hice las dos. Ninguna encontró nada. Siete modelos, el mismo harness, y ningún modelo que caiga en variantes que no ha visto ni que falle al delegar en sus propios subagentes. Es un resultado de verdad y lo cuento como tal. Pero mientras leía las tablas volvía una y otra vez a qué pueden decir estas pruebas y qué no, y la respuesta es menos de lo que sugiere un «no» limpio.

## La prueba que pedía el primer artículo

La idea viene de [GSM1k](https://arxiv.org/abs/2405.00332): si un modelo ha visto un benchmark, o algo muy parecido, debería rendir peor en problemas nuevos del mismo tipo que en los publicados. La monté por parejas. Cada ítem público tiene una variante que usa el mismo método pero con otros números y otra respuesta. Cada variante se comprobó dos veces antes de entrar: un script que la resuelve por su cuenta y una resolución a ciegas de un modelo Claude que no vio el original. Las que fallaban cualquiera de las dos comprobaciones quedaban fuera.

Lo que mido no es la caída de cada modelo a secas, porque alguna variante puede ser simplemente más difícil. Es la **caída en exceso**: la caída del modelo menos la caída media de los otros seis. Un modelo que se ha aprendido los ítems públicos debería perder más que el grupo cuando se los cambian. El análisis, el umbral y la corrección por probar siete modelos a la vez quedaron escritos antes de las corridas: un modelo muestra señal solo si su caída en exceso es positiva y sobrevive a una corrección de Holm al 5 %.

El primer banco tenía 120 parejas de AIME 2025 y del nivel 5 de MATH-500, dos corridas por ítem, los siete modelos a través de Claude Code. Los modelos: Opus 5, Fable 5, Kimi K3.1 Pro, Gemini 4 Argon y tres de pesos abiertos: DeepSeek V4 Pro, Qwen3.8 2.4T y GLM 5.3.

Ningún modelo cumplió el criterio. El problema es que casi ninguno tenía margen para caer: cinco de los siete sacaron entre el 96 % y el 100 % en las dos versiones, y Gemini resolvió todas las corridas de todos los ítems. Un modelo al 100 % no puede mostrar una caída por familiaridad por mucho que conozca los ítems.

Así que monté un banco más difícil: 91 parejas de HMMT de febrero de 2024 y 2025 y de CMIMC 2025, problemas de olimpiada recientes en los que los modelos punteros todavía fallan. Esta vez una corrida por ítem, por coste.

<figure class="nbf-fig">
<svg viewBox="0 0 600 490" role="img" aria-label="Caída en exceso en variantes no vistas para siete modelos en dos bancos: ningún intervalo del 95 % cae del lado de una señal de familiaridad.">
<text x="130" y="26" fill="#e2e8f0" font-size="13" font-weight="600">Banco 1: AIME 2025 + MATH-500 (n=120)</text>
<line x1="368.3" y1="36" x2="368.3" y2="208" stroke="#64748b" stroke-dasharray="3 3"/>
<text x="120" y="56" fill="#94a3b8" font-size="12" text-anchor="end">Opus 5</text>
<line x1="338.0" y1="52" x2="394.3" y2="52" stroke="#2dd4bf" stroke-width="2" opacity=".55"/>
<circle cx="366.2" cy="52" r="4.5" fill="#fbbf24"/>
<text x="120" y="80" fill="#94a3b8" font-size="12" text-anchor="end">Fable 5</text>
<line x1="334.8" y1="76" x2="386.7" y2="76" stroke="#2dd4bf" stroke-width="2" opacity=".55"/>
<circle cx="360.8" cy="76" r="4.5" fill="#fbbf24"/>
<text x="120" y="104" fill="#94a3b8" font-size="12" text-anchor="end">Kimi K3.1 Pro</text>
<line x1="340.2" y1="100" x2="411.7" y2="100" stroke="#2dd4bf" stroke-width="2" opacity=".55"/>
<circle cx="377.0" cy="100" r="4.5" fill="#fbbf24"/>
<text x="120" y="128" fill="#94a3b8" font-size="12" text-anchor="end">Gemini 4 Argon</text>
<line x1="346.7" y1="124" x2="386.7" y2="124" stroke="#2dd4bf" stroke-width="2" opacity=".55"/>
<circle cx="366.2" cy="124" r="4.5" fill="#fbbf24"/>
<text x="120" y="152" fill="#94a3b8" font-size="12" text-anchor="end">DeepSeek V4 Pro</text>
<line x1="359.7" y1="148" x2="479.9" y2="148" stroke="#2dd4bf" stroke-width="2" opacity=".55"/>
<circle cx="419.2" cy="148" r="4.5" fill="#fbbf24"/>
<text x="120" y="176" fill="#94a3b8" font-size="12" text-anchor="end">Qwen3.8 2.4T</text>
<line x1="334.8" y1="172" x2="394.3" y2="172" stroke="#2dd4bf" stroke-width="2" opacity=".55"/>
<circle cx="366.2" cy="172" r="4.5" fill="#fbbf24"/>
<text x="120" y="200" fill="#94a3b8" font-size="12" text-anchor="end">GLM 5.3</text>
<line x1="278.4" y1="196" x2="366.2" y2="196" stroke="#2dd4bf" stroke-width="2" opacity=".55"/>
<circle cx="323.9" cy="196" r="4.5" fill="#fbbf24"/>
<text x="130" y="236" fill="#e2e8f0" font-size="13" font-weight="600">Banco difícil: HMMT + CMIMC (n=91)</text>
<line x1="368.3" y1="246" x2="368.3" y2="418" stroke="#64748b" stroke-dasharray="3 3"/>
<text x="120" y="266" fill="#94a3b8" font-size="12" text-anchor="end">Opus 5</text>
<line x1="351.0" y1="262" x2="542.8" y2="262" stroke="#2dd4bf" stroke-width="2" opacity=".55"/>
<circle cx="445.2" cy="262" r="4.5" fill="#fbbf24"/>
<text x="120" y="290" fill="#94a3b8" font-size="12" text-anchor="end">Fable 5</text>
<line x1="339.1" y1="286" x2="501.6" y2="286" stroke="#2dd4bf" stroke-width="2" opacity=".55"/>
<circle cx="418.2" cy="286" r="4.5" fill="#fbbf24"/>
<text x="120" y="314" fill="#94a3b8" font-size="12" text-anchor="end">Kimi K3.1 Pro</text>
<line x1="306.6" y1="310" x2="559.0" y2="310" stroke="#2dd4bf" stroke-width="2" opacity=".55"/>
<circle cx="432.2" cy="310" r="4.5" fill="#fbbf24"/>
<text x="120" y="338" fill="#94a3b8" font-size="12" text-anchor="end">Gemini 4 Argon</text>
<line x1="268.7" y1="334" x2="396.5" y2="334" stroke="#2dd4bf" stroke-width="2" opacity=".55"/>
<circle cx="334.8" cy="334" r="4.5" fill="#fbbf24"/>
<text x="120" y="362" fill="#94a3b8" font-size="12" text-anchor="end">DeepSeek V4 Pro</text>
<line x1="138.7" y1="358" x2="397.6" y2="358" stroke="#2dd4bf" stroke-width="2" opacity=".55"/>
<circle cx="265.4" cy="358" r="4.5" fill="#fbbf24"/>
<text x="120" y="386" fill="#94a3b8" font-size="12" text-anchor="end">Qwen3.8 2.4T</text>
<line x1="263.2" y1="382" x2="406.2" y2="382" stroke="#2dd4bf" stroke-width="2" opacity=".55"/>
<circle cx="334.8" cy="382" r="4.5" fill="#fbbf24"/>
<text x="120" y="410" fill="#94a3b8" font-size="12" text-anchor="end">GLM 5.3</text>
<line x1="253.5" y1="406" x2="444.2" y2="406" stroke="#2dd4bf" stroke-width="2" opacity=".55"/>
<circle cx="348.8" cy="406" r="4.5" fill="#fbbf24"/>
<line x1="151.7" y1="426" x2="151.7" y2="431" stroke="#64748b"/>
<text x="151.7" y="444" fill="#94a3b8" font-size="11" text-anchor="middle">-20</text>
<line x1="260.0" y1="426" x2="260.0" y2="431" stroke="#64748b"/>
<text x="260.0" y="444" fill="#94a3b8" font-size="11" text-anchor="middle">-10</text>
<line x1="368.3" y1="426" x2="368.3" y2="431" stroke="#64748b"/>
<text x="368.3" y="444" fill="#94a3b8" font-size="11" text-anchor="middle">0</text>
<line x1="476.7" y1="426" x2="476.7" y2="431" stroke="#64748b"/>
<text x="476.7" y="444" fill="#94a3b8" font-size="11" text-anchor="middle">+10</text>
<line x1="585.0" y1="426" x2="585.0" y2="431" stroke="#64748b"/>
<text x="585.0" y="444" fill="#94a3b8" font-size="11" text-anchor="middle">+20</text>
<text x="376.3" y="462" fill="#fbbf24" font-size="11">peor en variantes →</text>
<text x="360.3" y="462" fill="#94a3b8" font-size="11" text-anchor="end">← mejor en variantes</text>
<text x="357.5" y="480" fill="#94a3b8" font-size="11" text-anchor="middle">caída en exceso (puntos)</text>
</svg>
<figcaption>Caída en exceso por modelo, con su intervalo bootstrap del 95 %. Ningún intervalo cae del lado «peor en variantes»; el único que no toca el cero, el de GLM en el banco 1, queda del otro lado. En el banco difícil los intervalos son anchos: para algunos modelos no se pueden descartar caídas de 12 a 15 puntos.</figcaption>
</figure>

Misma respuesta. Opus, Fable y Kimi pierden unos puntos más que el grupo en el banco difícil; Gemini, DeepSeek, Qwen y GLM pierden menos o nada, y ninguna diferencia sobrevive a la corrección. Gemini, el modelo cuyas puntuaciones despiertan más sospechas, vuelve a ser el más preciso: 97,8 % en los originales y 98,9 % en las variantes.

Hay dos detalles que merece la pena guardar, porque hablan de comportamiento y no de puntuaciones. En los ítems difíciles, Opus escribía a veces llamadas a herramientas que en ese harness no tenía, en ocasiones con resultados inventados, y paraba sin dar respuesta: así acabaron 34 de sus 182 corridas. Casi toda su caída en bruto viene de ahí, no de respuestas equivocadas. Y el único rastro de familiaridad que vi pasó fuera de la medición: al comprobar una variante de AIME, el resolutor a ciegas contestó con la respuesta del original, leyendo la base nueva de la variante como la del problema público. La variante se descartó por regla. Es un caso, no un dato, pero es justo el mecanismo que busca la prueba.

Lo que significa «sin señal» es estrecho. Para la mayoría de modelos, el primer banco descarta caídas de más de tres o cuatro puntos en estos ítems. No demuestra que ningún modelo se haya ajustado sobre benchmarks públicos. Demuestra que cambiar estos ítems por equivalentes no les cuesta acierto, y con un modelo tan pegado al techo como Gemini, ni siquiera el banco difícil deja mucho sitio para ver algo.

## Donde vive mi sospecha: los subagentes

La segunda prueba apuntaba al trabajo que de verdad describí: una sesión con varias tareas en marcha, subagentes que lanzar y esperar, y resultados que integrar en un solo entregable. Monté un escenario que un modelo no puede hacer cómodamente solo: una revisión de renovación de proveedores con quince carpetas (contratos, facturas línea a línea, registros de incidencias y, a veces, documentos posteriores), unos 400K de material en total.

<figure class="nbf-fig">
<svg viewBox="0 0 600 270" role="img" aria-label="El director lee las reglas comunes y delega quince carpetas de proveedores en subagentes; las reglas que deciden la respuesta están fuera de las carpetas, así que el director tiene que transmitirlas.">
<rect x="10" y="14" width="180" height="84" rx="8" fill="#232331" stroke="rgba(255,255,255,0.1)"/>
<text x="22" y="34" fill="#94a3b8" font-size="11">fuera de las carpetas</text>
<text x="22" y="54" fill="#5eead4" font-size="12" font-family="ui-monospace,'JetBrains Mono',monospace">policy.md</text>
<text x="22" y="71" fill="#5eead4" font-size="12" font-family="ui-monospace,'JetBrains Mono',monospace">finance/fx-2026.csv</text>
<text x="22" y="88" fill="#5eead4" font-size="12" font-family="ui-monospace,'JetBrains Mono',monospace">corporate/notices.md</text>
<line x1="190" y1="56" x2="246" y2="56" stroke="#64748b" stroke-width="1.5" marker-end="url(#nbfa)"/>
<rect x="250" y="34" width="150" height="44" rx="8" fill="#232331" stroke="#fbbf24"/>
<text x="325" y="61" fill="#fbbf24" font-size="13" font-weight="600" text-anchor="middle">director</text>
<defs><marker id="nbfa" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="#64748b"/></marker></defs>
<line x1="325" y1="78" x2="62" y2="134" stroke="#64748b" stroke-width="1.5" marker-end="url(#nbfa)"/>
<line x1="325" y1="78" x2="180" y2="134" stroke="#64748b" stroke-width="1.5" marker-end="url(#nbfa)"/>
<line x1="325" y1="78" x2="298" y2="134" stroke="#64748b" stroke-width="1.5" marker-end="url(#nbfa)"/>
<line x1="325" y1="78" x2="416" y2="134" stroke="#64748b" stroke-width="1.5" marker-end="url(#nbfa)"/>
<line x1="325" y1="78" x2="534" y2="134" stroke="#64748b" stroke-width="1.5" marker-end="url(#nbfa)"/>
<rect x="10" y="136" width="104" height="40" rx="8" fill="#232331" stroke="#2dd4bf"/>
<rect x="128" y="136" width="104" height="40" rx="8" fill="#232331" stroke="#2dd4bf"/>
<rect x="246" y="136" width="104" height="40" rx="8" fill="#232331" stroke="#2dd4bf"/>
<rect x="364" y="136" width="104" height="40" rx="8" fill="#232331" stroke="#2dd4bf"/>
<rect x="482" y="136" width="104" height="40" rx="8" fill="#232331" stroke="#2dd4bf"/>
<text x="62" y="161" fill="#e2e8f0" font-size="12" text-anchor="middle">subagente</text>
<text x="180" y="161" fill="#e2e8f0" font-size="12" text-anchor="middle">subagente</text>
<text x="298" y="161" fill="#e2e8f0" font-size="12" text-anchor="middle">subagente</text>
<text x="416" y="161" fill="#e2e8f0" font-size="12" text-anchor="middle">subagente</text>
<text x="534" y="161" fill="#e2e8f0" font-size="12" text-anchor="middle">subagente</text>
<text x="300" y="198" fill="#94a3b8" font-size="11" text-anchor="middle">15 carpetas: contrato, facturas, incidencias y a veces enmiendas, notas de crédito, borradores</text>
<text x="300" y="232" fill="#fbbf24" font-size="11" text-anchor="middle">trampas: cambio mensual · enmienda anulada por otra posterior · nota de crédito · borradores obsoletos</text>
<text x="300" y="250" fill="#fbbf24" font-size="11" text-anchor="middle">incidencias duplicadas · solo cuentan los P1 confirmados · un proveedor adquirido que no se puede renovar</text>
</svg>
<figcaption>El escenario <code>vendors-hard</code>. Varias de las reglas que deciden la respuesta están fuera de las carpetas, así que un subagente que solo lee la suya se equivoca salvo que el director se las pase o compruebe lo que le devuelve.</figcaption>
</figure>

La tarea pide el coste de cada proveedor en libras, los incidentes P1 que cuentan para su SLA, si lo incumple y los tres proveedores más baratos que se pueden renovar. Las trampas están pensadas para que delegar pueda salir mal. Los costes en euros y dólares se convierten al cambio de cada mes, que está en un fichero de finanzas que no aparece en ninguna carpeta. Una enmienda rebaja un precio y otra posterior la anula. Cuatro carpetas tienen un borrador de resumen con cifras equivocadas. Y un aviso corporativo dice que un proveedor ha sido adquirido por un competidor y no se puede renovar; sin ese aviso estaría entre los tres primeros.

Cada modelo actuó como su propio director con sus propios subagentes, a través de Claude Code, con herramientas de solo lectura. Antes hubo un escenario más pequeño con cinco proveedores. Los resultados, una corrida por modelo:

| Modelo | 5 prov. | 15 prov. | Trampas | En paralelo | Relecturas | Tiempo |
|---|---|---|---|---|---|---|
| Opus 5 | 15/15 | 45/45 | 7/7 | 5 | 8 | 40 min |
| Fable 5 | 15/15 | 45/45 | 7/7 | 5 | 7 | 10,5 min |
| Kimi K3.1 Pro | 15/15 | 45/45 | 7/7 | 15 | 42 | 23 min |
| Gemini 4 Argon | 15/15 | 45/45 | 7/7 | 5 | 35 | 40 min |
| DeepSeek V4 Pro | 15/15 | 45/45 | 7/7 | 5 | 26 | 13 min |
| GLM 5.3 | 15/15 | 45/45 | 7/7 | 15 | 31 | 8,5 min |
| Qwen3.8 2.4T | 15/15 | timeout | — | 5 | 0 | > 60 min |

Seis de siete perfectos, en todos los campos y todas las trampas, con los tres recomendados correctos. Qwen no falló por criterio: cuatro de sus cinco grupos de subagentes terminaron, y en el quinto un subagente anidado seguía sumando a mano unas 300 líneas de facturas cuando se acabó la hora. Es una corrida, así que no sé si se repite.

Lo que cambió fue el proceso. GLM y Kimi lanzaron quince subagentes a la vez, uno por carpeta; el resto agrupó las carpetas de cinco en cinco. Opus y Fable apenas releyeron nada por su cuenta para comprobar a sus subagentes, siete u ocho lecturas, mientras los demás volvieron a los ficheros entre 26 y 42 veces. El tiempo fue de ocho minutos y medio a cuarenta. Con una corrida cada uno, son observaciones, no un ranking. Y ninguna cambió la respuesta.

En acierto, el escenario está en techo, y no hice tres rondas más por modelo para confirmarlo. Tres veces más tablas a 45/45 no cambiarían la conclusión.

## Las vibes ganan a los benchmarks, también a los míos

Esta es la parte que las tablas no dicen por sí solas. Estas dos pruebas también son benchmarks. La de variantes pregunta si la nota en un examen se traslada a un examen equivalente. Es una pregunta sobre exámenes. El escenario agéntico era mi intento de acercarme a donde vive mi percepción, y aun así tiene todo lo que convierte algo en examen: una tarea completamente especificada, las reglas escritas en un fichero, un JSON al final y una clave contra la que corregir. En cuanto escribo la clave, he construido una prueba que los modelos pueden aprobar.

El trabajo real no trae clave. La tarea está mal planteada, o bien planteada sobre lo que no era. Parte del trabajo es descubrir qué preguntar. El contexto llega a trozos, alguien cambia de idea a mitad, y nadie dice cuál de los documentos importa. Lo que noto cuando trabajo horas con un modelo es cómo lee lo que quería decir, cuántas veces tengo que corregirlo, si se da cuenta de que el plan ya no encaja y qué tal es pasarle algo a medio pensar. Nada de eso cabe en un corrector, y no encontrar benchmaxing no dice nada sobre ello.

En ese sentido sigo pensando que las vibes ganan a los benchmarks. No porque las impresiones sean fiables: están sesgadas, son anecdóticas y es fácil engañarlas, y [el primer artículo](/es/blog/benchmaxing) fue en parte un ejercicio de dejar que las pruebas las contradijeran. Pero una impresión sostenida, construida a lo largo de muchas sesiones reales, lleva información que ninguna prueba acotada puede llevar, porque una prueba acotada quita justo la parte difícil de acotar. Una prueba puede descartar cosas: aquí, que estos modelos pierdan acierto en variantes no vistas de estos problemas, o que no sepan delegar una revisión bien especificada. No puede decirme a cuál quiero al lado un martes por la tarde con tres incendios abiertos.

Así que dejo la sospecha donde estaba, con un ajuste. Si Opus 5 es peor en el trabajo que me importa, no es porque se haya aprendido el examen, al menos no en nada que yo haya podido medir. Es más probable que tenga que ver con cómo maneja las partes del trabajo que ningún examen contiene. Medir eso pediría sesiones reales, usuarios reales y una medida de las correcciones que hacen, no otra clave.

---

*Método: todo corrió en Claude Code sin interfaz, con esfuerzo `high`. Opus y Fable usaron la suscripción Max; los otros cinco, el endpoint compatible con Anthropic de OpenRouter. No comprobé que el ajuste de esfuerzo llegue igual a todos los proveedores. Bancos de variantes: criterio preregistrado (caída en exceso positiva, p de Holm < 0,05), intervalos bootstrap por ítem, prueba de permutación por cambio de signo y un análisis de sensibilidad que excluye los ítems donde alguna corrida no dio respuesta en `\boxed{}`, que no cambió nada. Las corridas sin respuesta enmarcada cuentan como fallo. Las variantes y la comprobación a ciegas las escribió un modelo Claude, lo que puede hacerlas algo más fáciles o más cercanas a Claude; la comparación con el grupo solo absorbe un desplazamiento uniforme. APEX 2025 salió del banco difícil por coste. En los escenarios agénticos no había Bash, así que las sumas sobre CSV había que hacerlas razonando; algunas corridas del primer piloto fueron inválidas por el harness y se repitieron, y las inválidas se guardan aparte. Gasto total en OpenRouter: unos 245 USD. Prompts, ítems, respuestas, claves y scripts están en el [repositorio de evidencias](https://github.com/JaviMaligno/benchmaxing-probes).*
