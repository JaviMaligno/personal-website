---
title: "No digas solo «ignóralo»"
description: "Hace dos meses supuse que decirle a un modelo que ignore un pegado accidental podía dejar más residuo que no decir nada. 480 conversaciones pareadas después: lo deja, lo multiplica por seis, y el arreglo no es pedirlo con más énfasis."
pubDate: 2026-10-15
tags: ["IA", "Agentes", "Evaluación", "Claude"]
lang: es
translationKey: dont-just-say-ignore-it
heroImage: "/blog/dont-just-say-ignore-it.png"
repoUrl: "https://github.com/JaviMaligno/llm-wrong-paste"
---

<style>
.ign-fig { margin: 2.5rem 0; }
.ign-fig svg { width: 100%; height: auto; display: block; }
.ign-fig figcaption {
color: #94a3b8; font-size: 0.9rem; line-height: 1.5;
margin-top: 0.75rem; text-align: left;
}
</style>

Al final del [primer artículo de esta serie](/es/blog/that-was-for-another-chat) dejé escrita una sospecha que no podía comprobar:

> Mi sospecha, que los datos aún no han puesto a prueba, es que decirlo puede dejar más residuo que no decir nada.

Es la clase de frase que sale barata de escribir y cara de verificar. Este artículo es la verificación. Es también el último de los tres que prometí, y resulta que la sospecha era correcta — con una corrección que no vi venir y que me parece la mitad más útil.

## La forma del experimento

Lo incómodo de medir una reparación es que necesitas dos conversaciones idénticas hasta el momento de reparar, que se diferencien solo en lo que el usuario escribe después. Si no, comparas reparaciones *y* los accidentes que las precedieron.

Así que no corrí conversaciones nuevas. Reutilicé las 1.339 reacciones de [la tanda anterior](/es/blog/what-gives-a-paste-away) —prefijo, bloque pegado y respuesta del modelo, ya pagadas y ya juzgadas— y le colgué a cada una cuatro continuaciones distintas. Mismo prefijo, mismo artefacto, mismo pegote, misma reacción. Lo único que varía es la frase que el usuario escribe a continuación:

- **(a)** nada. El usuario sigue con el tema original como si el pegote no hubiera existido.
- **(b)** *«Ignóralo.»*
- **(c)** *«Ignóralo, era para otro chat. Seguimos con la factura de la luz.»*
- **(d)** *«Sí, hablemos de eso.»*

La última es el control, y es lo que hace que el diseño valga algo. (b) y (d) son **instrucciones opuestas sobre el mismo bloque de texto**: una dice *esto no va aquí*, la otra dice *sí va*. Si un modelo respondiera igual a las dos, no estaría leyendo la intención del usuario: estaría reaccionando a que el texto esté ahí. Lo metí esperando cazar justo eso.

Lo que mido es la **fuga**: si alguna de las entidades distintivas del artefacto pegado —los nombres, los productos, los lugares que pertenecen a la otra conversación y a nada de esta— reaparece en las respuestas posteriores del modelo. Las entidades se conocen porque el banco de pegotes es mío.

120 bases, cuatro brazos cada una: 480 conversaciones, todas sobre Claude Opus 5.

## El resultado

<figure class="ign-fig">
<svg viewBox="0 0 600 224" role="img" aria-label="Decir «ignóralo» produce fuga de entidades en el 19,2 por ciento de las conversaciones, frente al 3,3 por ciento cuando el usuario no dice nada. Explicar adónde ir a continuación la baja al 8,3 por ciento, y decir «sí, hablemos de eso» da la tasa más baja de las cuatro, un 2,5 por ciento.">
<rect x="0" y="0" width="600" height="224" fill="#1a1a24"/>
<rect x="12" y="10" width="576" height="204" rx="8" fill="none" stroke="rgba(255,255,255,0.1)"/>
<text x="32" y="38" fill="#94a3b8" font-family="ui-monospace,'JetBrains Mono',monospace" font-size="11" letter-spacing="1.2">EL PEGOTE SE CUELA EN LO QUE VIENE DESPUÉS</text>
<text x="32" y="72" fill="#e2e8f0" font-size="13">(a) no decir nada</text>
<rect x="232" y="61" width="50" height="14" rx="2" fill="#64748b"/>
<text x="292" y="73" fill="#94a3b8" font-family="ui-monospace,monospace" font-size="12">3,3 %</text>
<text x="32" y="106" fill="#f8fafc" font-size="13" font-weight="600">(b) «ignóralo»</text>
<rect x="232" y="95" width="292" height="14" rx="2" fill="#f59e0b"/>
<text x="534" y="107" fill="#fbbf24" font-family="ui-monospace,monospace" font-size="12" font-weight="600">19,2 %</text>
<text x="32" y="140" fill="#e2e8f0" font-size="13">(c) + adónde ir</text>
<rect x="232" y="129" width="126" height="14" rx="2" fill="#2dd4bf"/>
<text x="368" y="141" fill="#5eead4" font-family="ui-monospace,monospace" font-size="12">8,3 %</text>
<text x="32" y="174" fill="#e2e8f0" font-size="13">(d) «sí, hablemos»</text>
<rect x="232" y="163" width="38" height="14" rx="2" fill="#2dd4bf"/>
<text x="280" y="175" fill="#5eead4" font-family="ui-monospace,monospace" font-size="12">2,5 %</text>
<line x1="32" y1="192" x2="568" y2="192" stroke="rgba(255,255,255,0.08)"/>
<text x="32" y="207" fill="#94a3b8" font-size="11.5">La orden de descartar el texto produce seis veces el residuo de no mencionarlo.</text>
</svg>
<figcaption>120 conversaciones por brazo, las cuatro colgando del mismo pegote y de la misma reacción. Solo cambia la frase siguiente del usuario.</figcaption>
</figure>

Como los brazos están pareados, la prueba correcta es sobre las conversaciones en las que dos brazos discrepan. Las tres comparaciones declaradas sobreviven a la corrección de Holm:

<figure class="ign-fig">
<svg viewBox="0 0 600 214" role="img" aria-label="Las tres comparaciones pareadas son significativas tras la corrección de Holm: decir «ignóralo» añade 15,8 puntos de fuga frente a no decir nada, explicar adónde ir quita 10,8 puntos, y decir «ignóralo» añade 16,7 puntos frente a decir «sí, hablemos de eso».">
<rect x="0" y="0" width="600" height="214" fill="#1a1a24"/>
<rect x="12" y="10" width="576" height="194" rx="8" fill="none" stroke="rgba(255,255,255,0.1)"/>
<text x="32" y="36" fill="#94a3b8" font-family="ui-monospace,'JetBrains Mono',monospace" font-size="11" letter-spacing="1.2">DIFERENCIA PAREADA E INTERVALO 95 %</text>
<line x1="348" y1="50" x2="348" y2="166" stroke="#64748b" stroke-dasharray="3 3"/>
<text x="348" y="182" fill="#94a3b8" font-size="10.5" text-anchor="middle">0</text>
<text x="32" y="76" fill="#e2e8f0" font-family="ui-monospace,monospace" font-size="12">(b) vs (a)</text>
<line x1="399" y1="72" x2="505" y2="72" stroke="#f59e0b" stroke-width="3"/>
<circle cx="452" cy="72" r="4.5" fill="#fbbf24"/>
<text x="515" y="76" fill="#fbbf24" font-family="ui-monospace,monospace" font-size="11">+15,8</text>
<text x="32" y="114" fill="#e2e8f0" font-family="ui-monospace,monospace" font-size="12">(c) vs (b)</text>
<line x1="233" y1="110" x2="318" y2="110" stroke="#2dd4bf" stroke-width="3"/>
<circle cx="276" cy="110" r="4.5" fill="#5eead4"/>
<text x="225" y="114" fill="#5eead4" font-family="ui-monospace,monospace" font-size="11" text-anchor="end">&#8722;10,8</text>
<text x="32" y="152" fill="#e2e8f0" font-family="ui-monospace,monospace" font-size="12">(b) vs (d)</text>
<line x1="409" y1="148" x2="507" y2="148" stroke="#f59e0b" stroke-width="3"/>
<circle cx="458" cy="148" r="4.5" fill="#fbbf24"/>
<text x="517" y="152" fill="#fbbf24" font-family="ui-monospace,monospace" font-size="11">+16,7</text>
<text x="32" y="198" fill="#94a3b8" font-size="11">Ningún intervalo toca el cero. p corregida por Holm: 0,0011, 0,0036, 0,0003.</text>
</svg>
<figcaption>Puntos porcentuales de fuga, medidos dentro de la conversación. Los brazos son los de la primera figura. La fila del medio es la que hay que quedarse: añadir un destino a la misma instrucción quita unos once puntos.</figcaption>
</figure>

## El control contestó una pregunta que no había hecho

Esperaba que (d) fuera el brazo incómodo. Si *«ignóralo»* y *«sí, hablemos de eso»* produjeran la misma conducta, la conclusión honesta habría sido que el modelo no procesa la instrucción, solo reacciona a que el texto esté.

Salió al revés, y con claridad. La instrucción de **quedarse** con el texto pegado da la fuga más baja de los cuatro brazos —2,5 %—. La de **descartarlo**, la más alta —19,2 %—. La diferencia es de 16,7 puntos y es la más significativa de las tres.

O sea que el modelo lee la intención perfectamente. Eso nunca fue el problema. El problema es el que los experimentos del oso blanco llevan señalando en las personas desde los ochenta: **para ignorar algo hay que sostenerlo.** Pedir el borrado es lo que lo vuelve a poner en juego.

Y (c) cierra el argumento por el otro lado. La misma instrucción de ignorar, pero con un sitio al que ir —*«seguimos con la factura de la luz»*— y la tasa cae del 19,2 % al 8,3 %. Lo que repara la conversación no es pedir el olvido: es suministrar el reemplazo.

## Dónde vive el residuo

<figure class="ign-fig">
<svg viewBox="0 0 600 240" role="img" aria-label="Toda la fuga ocurre en la respuesta del modelo a la propia reparación. En los dos turnos siguientes todos los brazos están en cero o cerca, incluido el que fuga un 19,2 por ciento en la primera respuesta, y una segunda tanda con turno siguiente neutro reproduce los mismos ceros.">
<rect x="0" y="0" width="600" height="240" fill="#1a1a24"/>
<rect x="12" y="10" width="576" height="220" rx="8" fill="none" stroke="rgba(255,255,255,0.1)"/>
<text x="32" y="36" fill="#94a3b8" font-family="ui-monospace,'JetBrains Mono',monospace" font-size="11" letter-spacing="1.2">FUGA POR TURNO</text>
<text x="196" y="58" fill="#94a3b8" font-size="10.5" text-anchor="middle">respuesta a la reparación</text>
<text x="352" y="58" fill="#94a3b8" font-size="10.5" text-anchor="middle">turno siguiente</text>
<text x="474" y="58" fill="#94a3b8" font-size="10.5" text-anchor="middle">el de después</text>
<text x="32" y="88" fill="#e2e8f0" font-size="12.5">(a) nada</text>
<rect x="160" y="78" width="12" height="12" rx="2" fill="#64748b"/>
<text x="180" y="88" fill="#94a3b8" font-family="ui-monospace,monospace" font-size="11">3,3 %</text>
<text x="330" y="88" fill="#64748b" font-family="ui-monospace,monospace" font-size="11">0,0 %</text>
<text x="452" y="88" fill="#64748b" font-family="ui-monospace,monospace" font-size="11">0,8 %</text>
<text x="32" y="122" fill="#f8fafc" font-size="12.5" font-weight="600">(b) «ignóralo»</text>
<rect x="160" y="112" width="66" height="12" rx="2" fill="#f59e0b"/>
<text x="234" y="122" fill="#fbbf24" font-family="ui-monospace,monospace" font-size="11" font-weight="600">19,2 %</text>
<text x="330" y="122" fill="#64748b" font-family="ui-monospace,monospace" font-size="11">0,0 %</text>
<text x="452" y="122" fill="#64748b" font-family="ui-monospace,monospace" font-size="11">0,0 %</text>
<text x="32" y="156" fill="#e2e8f0" font-size="12.5">(c) + destino</text>
<rect x="160" y="146" width="26" height="12" rx="2" fill="#2dd4bf"/>
<text x="194" y="156" fill="#5eead4" font-family="ui-monospace,monospace" font-size="11">7,5 %</text>
<text x="330" y="156" fill="#64748b" font-family="ui-monospace,monospace" font-size="11">0,0 %</text>
<text x="452" y="156" fill="#64748b" font-family="ui-monospace,monospace" font-size="11">0,8 %</text>
<text x="32" y="190" fill="#e2e8f0" font-size="12.5">(d) «sí, hablemos»</text>
<rect x="160" y="180" width="9" height="12" rx="2" fill="#2dd4bf"/>
<text x="177" y="190" fill="#5eead4" font-family="ui-monospace,monospace" font-size="11">2,5 %</text>
<text x="330" y="190" fill="#64748b" font-family="ui-monospace,monospace" font-size="11">0,8 %</text>
<text x="452" y="190" fill="#64748b" font-family="ui-monospace,monospace" font-size="11">0,8 %</text>
<line x1="32" y1="206" x2="568" y2="206" stroke="rgba(255,255,255,0.08)"/>
<text x="32" y="222" fill="#94a3b8" font-size="11.5">Un eco inmediato, no una deriva: repetirlo con turno neutro da los mismos ceros.</text>
</svg>
<figcaption>El efecto está concentrado por completo en la respuesta del modelo a la reparación. Los dos ceros son el residuo y no la pregunta: una segunda tanda de 240 conversaciones, con ese turno siguiente sustituido por una continuación cualquiera, los reproduce.</figcaption>
</figure>

Toda la fuga está en la respuesta a la propia reparación. El modelo nombra las entidades de la otra conversación **en el acto mismo de prometer que las olvida** —*«entendido, dejo aparte lo de la factura de Marta»*— y dos turnos después, nada.

Eso hace el hallazgo más pequeño en alcance y más nítido en mecanismo. No es deriva. Es un eco.

La primera vez que miré esos dos ceros no pude usarlos. El turno inmediatamente posterior a la reparación era una pregunta aritmética literal con una sola respuesta correcta —un turno que domina lo que el modelo puede decir—, así que un cero ahí era en parte propiedad de mi instrumento y no del fenómeno.

Así que lo corrí otra vez sin ese turno: las mismas 120 bases, brazos (a) y (b), con el segundo turno sustituido por una continuación cualquiera de la conversación. **El cero aguanta.** Sin que se pregunte nada en particular, la fuga en el turno siguiente sigue siendo del 0,0 % en los dos brazos. El residuo no sobrevive al turno siguiente, sea el que sea.

La repetición replica además el efecto principal sobre otra forma de conversación: 2,5 % frente a 13,3 %, una diferencia pareada de **+10,8 puntos** (p = 0,006). Dos diseños, misma dirección, tamaño parecido.

Ahí salió una cosa que juega en mi contra si nadie la comprueba. Sin la pregunta aritmética el modelo escribe libre y se come el tope de tokens más a menudo —un 12,5 % de celdas cortadas frente al 3,3 % de antes, y desbalanceado: 21 en el brazo que no dice nada y 9 en el que dice *«ignóralo»*—. Una respuesta cortada no puede contener una entidad, y en efecto la fuga es del 0 % en todas y cada una de las celdas cortadas. O sea que el truncado desinfla la medición en vez de inflarla: restringido a las 95 bases en las que los dos brazos terminaron limpios, la diferencia se ensancha a 2,1 % frente a 15,8 %. El número que publico es el conservador.

## Lo que no funcionó

Quería una segunda variable dependiente: ¿la conversación contaminada falla la *tarea*? Cada tema del banco recibió una pregunta verificable con una sola respuesta correcta, escrita antes de correr nada.

Opus sacó 120/120, 120/120, 120/120 y 119/120.

Así que las endurecí: cadenas de varios pasos, cada una con una trampa clásica de su dominio —aplicar el impuesto eléctrico y el IVA en secuencia en vez de sumarlos en un 26 %, cobrar la comisión del banco sobre los euros y no sobre los yenes, olvidar el agua que ya lleva el prefermento—. Volví a correr el control limpio, sin pegote, para calibrar.

24 de 24. Los ocho temas, todas sus repeticiones.

Es un resultado nulo y lo reporto como tal: en este modelo, la contaminación por pegado accidental no llega a una tarea aritmética verificable. Lo que deja abierto es si llegaría a una tarea que dependa del *contexto* en vez del cálculo — y eso es rediseño y no ajuste, porque rompe la regla que me puse de que el enunciado lleve dentro todos sus datos.

## Lo que yo haría

- **No mandes «ignóralo» a secas.** Es lo peor de las cuatro cosas que probé, por un factor de seis frente a no decir nada.
- **Di adónde ir en su lugar.** *«Ignora eso, ventana equivocada — volvemos a la factura»* te cuesta una frase y quita unos once puntos de eco. Es la única recomendación de aquí con una p corregida detrás.
- **No decir nada está bien.** Si puedes seguir con tu pregunta, sigue. Se queda en el 3,3 %, estadísticamente indistinguible del mejor brazo.
- **No leas esto como contaminación duradera.** El eco apareció en la respuesta inmediata y había desaparecido para el turno siguiente, en las dos tandas y fuera cual fuera ese turno. Un intercambio después, se acabó.

Una cosa más, que es la pista más concreta que deja esto y que no afirmo, solo reporto: la fuga tras *«ignóralo»* fue casi el doble cuando el modelo **no** había señalado ya el pegote como raro —25,0 % frente a 13,3 %—. El que no se olió nada es el que peor lleva que le digan que lo olvide.

---

*Con esto se cierra la serie de tres artículos que empezó con [un pegado accidental que nadie cuestionó](/es/blog/that-was-for-another-chat) y siguió con [qué delata uno](/es/blog/what-gives-a-paste-away). Las 480 conversaciones, los cuatro brazos de reparación, los veredictos de los dos jueces y los fallos están en [llm-wrong-paste](https://github.com/JaviMaligno/llm-wrong-paste).*
