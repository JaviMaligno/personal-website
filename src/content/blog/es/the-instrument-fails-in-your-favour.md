---
title: "El instrumento falla a tu favor"
description: "En tres estudios, todos los instrumentos de medida que construí fallaron al menos una vez — y todos los fallos apuntaban hacia el resultado que yo esperaba. Sobre por qué 'mídelo' es un consejo incompleto, y lo que cuesta de verdad construir la referencia."
pubDate: 2026-09-04
tags: ["IA", "Evaluación", "Investigación", "Ingeniería"]
lang: es
translationKey: the-instrument-fails-in-your-favour
heroImage: "/blog/the-instrument-fails-in-your-favour.png"
linkedinLinks:
  - label: "Agentes de código y trabajo en equipo — el estudio sobre CooperBench"
    url: https://github.com/JaviMaligno/CooperBench/tree/experiment/structural-conditions
  - label: "Harness de sesgo del juez y juicios en bruto"
    url: https://github.com/JaviMaligno/personal-website/tree/main/experiments/judge-bias
  - label: "Repo semilla del cross-check entre sesiones"
    url: https://github.com/JaviMaligno/cross-session-crosscheck
---

El consejo estándar sobre adoptar herramientas de IA es dejar de discutir y medir. Dale a cada opción las mismas tareas representativas, mide tiempo hasta el merge, tasa de defectos, retrabajo, esfuerzo de revisión, y convierte una preferencia en una decisión respaldada por evidencia. Estoy de acuerdo, lo sigo dando, y es lo que hice en tres estudios distintos este año.

Esto es lo que nadie pone en el mismo párrafo: **aquello con lo que mides también es software sin verificar.** En esos tres estudios, todos los instrumentos que construí fallaron al menos una vez. Todos los fallos apuntaban hacia el resultado que yo ya esperaba. Y todos se cazaron igual: yendo a mirar la cosa misma en vez de lo que mi herramienta decía de ella.

No es una confesión, es un patrón con un mecanismo, y el mecanismo es barato de contrarrestar en cuanto le ves la forma.

## 1. El instrumento hereda tu hipótesis

Cuando leí [un corpus de cinco días de mensajes entre sesiones de código en paralelo](/es/blog/what-agents-say-to-each-other), una de las cosas que quería era el protocolo de exclusión mutua: una sesión dice *espera, estoy en ese fichero*, la otra dice *adelante*. Escribí un detector léxico para encontrarlo. Dio 19 secuencias candidatas de las que solo 5 llegaban al final, y anoté la conclusión que se sigue de ahí: el protocolo **se abre mucho más de lo que se cierra**. Los agentes empiezan a coordinarse y no terminan. Era una buena frase y encajaba con la historia que estaba contando sobre el seguimiento.

Recontado sobre las categorías codificadas, hay **3** peticiones de espera reales, y **las 3 se cierran**. Las otras 16 eran falsos positivos: entraba cualquier mensaje que contuviera *espera*, *aguanta* o *adelante*, incluidos mensajes que no eran peticiones. La conclusión corregida apunta al revés: cuando ese protocolo se abre de verdad, se cierra siempre.

Fíjate en lo que hizo el detector. Le di una consulta con forma de hipótesis —búscame las palabras que usa este comportamiento— y me devolvió una respuesta con forma de hipótesis. Una regla léxica no distingue una petición de la mención de una petición, así que contó menciones, y las menciones son exactamente lo que abunda en un corpus donde las sesiones hablan *sobre* coordinarse. El instrumento no falló al azar. Falló a lo largo del eje que me interesaba.

El scorer del mismo estudio se rompió igual. Comparaba lo que una sesión **afirmaba** en su informe contra el estado **publicado**, y marcó un episodio como afirmación falsa. No lo era: esa sesión había publicado un artefacto incoherente y lo **declaraba** en sus notas. No sostenía ninguna creencia falsa. El scorer solo leía el campo `released:` e ignoraba la divulgación, así que habría inflado exactamente la cifra que perseguía el artículo entero. El arreglo fue una categoría aparte para el defecto declarado, más la admisión de que la única regla léxica que queda en la puntuación es una regla léxica.

## 2. Los instrumentos heredados traen la hipótesis de otro

Un mes antes había hecho [un experimento sobre si los agentes de código pueden colaborar](/es/blog/coding-agents-structure) encima de CooperBench, de Stanford. Ese eval no lo escribí yo: lo heredé, que parecía la opción segura.

La versión open-source omite un paso que el eval del propio paper sí ejecuta: resolver conflictos de merge triviales con un modelo pequeño antes de declarar el fallo. Así que mi primera tabla puntuaba **cada** conflicto de merge como fallo instantáneo — y el conflicto de merge es la muerte característica de dos agentes trabajando a la vez, que es justo la condición contra la que argumentaba mi artículo. El paso que faltaba empujaba el número en la dirección de mi tesis.

Lo comprobé por los dos lados. Triando a mano los 29 pares con conflicto, **aproximadamente la mitad de los conflictos no son colisiones lógicas reales**: dos agentes añadiendo un import distinto, o un argumento distinto, a la misma línea. Después añadí un resolvedor usando un modelo más fuerte que el del paper, para que la condición concurrente tuviera todas las ventajas, y volví a puntuar sobre tres semillas. Rescató bastantes merges y casi ninguno se convirtió en aprobado: 7% para el modelo débil (sin cambio) y 9% para el fuerte, desde 7%. Una tarea más.

Que es la parte que conviene no pasar de largo. **Arreglar el instrumento no cambió la conclusión.** Pasó lo mismo con un segundo bug: el eval open-source enrutaba el modo de equipo estructurado del paper como si fuera coop libre y fusionaba ambos parches, aplicando dos veces el trabajo del miembro que ya estaba dentro del parche del líder. Lo corregí para puntuar el artefacto que el líder entrega. El número no se movió —siguió en 0%— pero ahora mide lo que dice medir.

Dos condiciones sí puntuaron un **0% falso** por bugs de composición del eval: un parche apilado evaluado contra la base equivocada. Esos los cacé corriendo dos auditorías adversariales independientes sobre las cinco implementaciones de condición y sobre el enrutado del eval. Los números publicados sobrevivieron a esa auditoría, y la auditoría es lo que sacó a la luz el resolvedor de conflictos que faltaba.

Así que la versión honesta de esta sección no es "mis resultados estaban mal". Es: tres defectos de instrumento, dos de los cuales habrían favorecido mi tesis, uno que no cambió nada, y yo no habría podido decirte de antemano cuál era cuál.

## 3. Nadie audita la referencia

La versión más cara de esto no es un detector con un bug. Es un conjunto de referencia que a nadie se le ocurre cuestionar, porque ser la referencia es precisamente lo que lo exime de sospecha.

Un informe externo puntuó [el servicio de clasificación de industria de un cliente](/es/projects/compliance-classifier) con un **54% de acierto sobre 500 empresas**, y debajo la conclusión que se sigue de un número así. Mi primera reacción fue creérmelo: un porcentaje con decimales sobre una muestra de 500 tiene una autoridad que no se cuestiona en la primera lectura.

Revisando los desacuerdos uno a uno apareció un patrón que no encajaba: **las etiquetas del gold set se podían adivinar solo con el nombre de la empresa**, sin mirar la empresa. Si el nombre contenía *logística*, transporte. Si contenía *solar*, energía. Si era un acrónimo o un apellido, alguna categoría genérica de servicios. Una etiqueta predecible desde el nombre lleva información sobre el nombre, no sobre la empresa — y los casos en los que el nombre engaña son precisamente los difíciles, es decir, los únicos que merece la pena medir. El gold set se había generado pegando la lista en un chat de propósito general, de una tacada. [La historia completa es su propio artículo](/es/blog/the-grader-knew-less); la versión corta es que quien puntuaba había investigado menos que el sistema al que puntuaba.

Rehecho a mano, caso por caso, el número defendible era **75% en lectura conservadora y hasta 85% resolviendo las zonas grises a favor**. Unos veinte puntos por encima del informe.

Pero el gold set no era el único defecto, y los otros son la razón de que este caso esté en un artículo sobre instrumentos y no sobre evaluadores. El comparador era **sensible al orden** (una entidad puede llevar varios códigos; que volvieran en otro orden contaba como error), **ciego a la compatibilidad** (dos códigos pueden ser legítimamente correctos a la vez; uno contaba como acierto y el otro como fallo) y **binario** (fallar la rama entera y fallar una subcategoría dentro de la rama correcta puntuaban igual).

Tres defectos independientes, y **los tres solo podían restar puntos**. Esa es la firma que hay que aprender a reconocer. Cuando todos los defectos de una medición empujan hacia el mismo lado, el número resultante no es simplemente ruidoso: es sesgado, y puedes saber la dirección sin conocer la magnitud. Un instrumento ruidoso te da un intervalo ancho. Uno roto direccionalmente te da una respuesta equivocada con confianza, que es peor, porque nadie replantea una hoja de ruta por un intervalo ancho.

## 4. El instrumento que no está roto y aun así no mide nada

Un cuarto modo de fallo no tiene ningún bug dentro.

Cuando medí [si la identidad de un juez LLM cambia sus veredictos](/es/blog/three-judges-three-rankings), uno de los estadísticos que todo el mundo cita es cuántas veces gana la respuesta más larga. El mío daba 48,6%, 48,6% y 64,6% entre los tres jueces, que parece ausencia casi total de sesgo de longitud. En un piloto anterior dentro de una sola familia, el mismo estadístico daba 80–85%, que parece un sesgo de manual.

**Las dos lecturas están mal, y por el mismo motivo.** En cualquier alineación normal de modelos, longitud y calidad están confundidas: si tus modelos verbosos resultan ser los buenos, el número se infla; si no lo son, se cancela. El estadístico es un accidente de qué modelos incluiste. Controlándolo —mismo modelo, misma tarea, dos variantes que solo difieren en la longitud objetivo, juzgadas sobre un prompt que nunca menciona la longitud— la preferencia sale en **77,8%, 86,1% y 88,9%**. Más fuerte que lo que insinuaba el número sin controlar, y en dirección opuesta a la que la gente supone que corre la confusión. Desglosado por lo que premia la tarea, las que invitan a elaborar salen **27 de 27**, y 45 de 45 sumando los seis jueces del piloto.

El estadístico sin controlar no estaba mal calculado. Estaba bien calculado y no significa nada, que es un defecto más difícil de notar que una excepción.

Ese estudio contiene dos más de estos. La preferencia por uno mismo medida dentro de una sola familia salió +16,7, −14,6 y +4,2 puntos porcentuales: ruido sin dirección, que podría haber publicado tranquilamente como "aquí no hay auto-preferencia". Entre familias es una línea recta: +28,3, +25,0, +21,7, y los tres intervalos excluyen el cero. El piloto no estaba equivocado, estaba ciego por construcción. Y en las tareas subjetivas los tres jueces coinciden con una kappa de Cohen de −0,01, −0,03 y +0,05: azar. Promediar tres jueces que coinciden al nivel del azar no te da una señal robusta; te da una señal aleatoria más suave, con la misma autoridad aparente.

También publiqué un hallazgo de ese piloto que no replicó: que los jueces infieren el objetivo implícito de la tarea y prefieren la respuesta **corta** cuando la tarea premia la concisión. Seis jueces después, uno de los seis había invertido todas y cada una de las veces y arrastraba por debajo del 50% un agregado de tres. La conclusión redonda era un modelo.

## 5. Por qué todos apuntan al mismo sitio

Cinco instrumentos en tres estudios, más un cuarto modo de fallo en el que no hay nada roto. La dirección es la parte que pide explicación, porque unos bugs aleatorios habrían ido para los dos lados.

El mecanismo no es sofisticado: **dejas de buscar cuando el número confirma.** Un resultado que coincide con tu expectativa cierra la investigación, así que un bug que produzca uno de esos nunca se encuentra. Un resultado que la contradice abre una investigación, y esa investigación encuentra el bug que haya. El instrumento no está sesgado. Lo está tu criterio de parada, y es él quien filtra qué defectos llegas a conocer.

Que es exactamente el fallo que dediqué un artículo entero a documentar en los agentes: una sesión que verificó su tag de git con `git ls-remote` y después afirmó el estado del registro sin abrirlo nunca, informando de una publicación que no existía. Lo que predijo el resultado en 10 de 10 episodios no fue nada de lo que la sesión dijo: fue si había ido a mirar. Escribí ese artículo mientras hacía lo mismo con mis propias herramientas. La corrección impresa debajo es un caso más: afirmé que un "hecho" falso se había propagado a un par que esperaba, y al releer los transcripts ninguna de las sesiones de ese brazo tenía canal.

Hay una sola defensa y es aburrida. **Ir a mirar la cosa misma, no lo que tu herramienta dice de ella.** Todos estos se cazaron así: recontando a mano las secuencias del mutex, triando a mano 29 conflictos, abriendo una a una las clasificaciones en disputa, corriendo una sonda de longitud controlada en vez de una correlación. De ahí salen dos hábitos baratos:

- **Intenta reproducir tu referencia con una heurística tonta.** Coge el atributo más superficial de cada caso —el nombre, la primera palabra— y mira si predice las etiquetas del gold set. Si lo hace, tu gold set *es* esa heurística.
- **Audita más fuerte allí donde el resultado te gustó.** Los desacuerdos se investigan solos; las coincidencias no se investigan nunca. Lo que confirmó tu hipótesis previa es donde viven tus bugs sin examinar.

## Lo que cuesta medir de verdad

Lo que lleva a la parte que cambia el consejo en vez de decorarlo.

El coste de una evaluación no es el coste de ejecutarla. Ejecutarla es barato y cada vez lo es más. Los costes son, en orden ascendente: **verificar el instrumento**, que es un proyecto de testing sobre código que nadie trata como producción; **construir la referencia contra la que comparas**, que sigue siendo lenta, humana y aburrida —por eso se están pagando salarios de ingeniería puntera por producir datos etiquetados—; y **montar una comparación multi-proveedor**, que significa varias revisiones de compras, varias evaluaciones de seguridad, altas y bajas de accesos, y alguien haciéndose cargo de las licencias y del gasto mientras dure.

En una organización pequeña, ese último coste puede perfectamente superar la diferencia que la evaluación habría revelado. Y entonces comprometerse con una herramienta que se sabe buena, y gastar el esfuerzo ahorrado en infraestructura de verificación, es la decisión de ingeniería mejor y no la perezosa. La comparación se gana su coste cuando la organización es lo bastante grande como para que domine la diferencia por asiento, o cuando las restricciones descartan opciones de verdad — y entonces merece hacerse bien, que significa presupuestar el instrumento y la referencia, no solo la ejecución.

El consejo que me quedo es más estrecho que "mídelo": **mídelo, y trata la medición como el componente menos fiable del sistema, porque es el único que no está comprobando nadie.** Todo lo demás de tu stack tiene tests, revisión, monitorización y usuarios que se quejan. Tu harness de evaluación tiene un número que pareció plausible y una persona que quería que fuese verdad.

---

*Tres estudios alimentan esta pieza y los tres son públicos: el [fork de CooperBench con las cinco condiciones estructurales](https://github.com/JaviMaligno/CooperBench/tree/experiment/structural-conditions), el [harness de sesgo del juez con los juicios en bruto y los dos informes](https://github.com/JaviMaligno/personal-website/tree/main/experiments/judge-bias) (con el piloto delante, porque el hallazgo retirado es la parte útil) y el [repo semilla del cross-check entre sesiones](https://github.com/JaviMaligno/cross-session-crosscheck). Los artículos: [agentes de código y trabajo en equipo](/es/blog/coding-agents-structure), [tres jueces, tres rankings](/es/blog/three-judges-three-rankings), [lo que los agentes de código se dicen entre ellos](/es/blog/what-agents-say-to-each-other) y [el evaluador sabía menos que el sistema que evaluaba](/es/blog/the-grader-knew-less).*
