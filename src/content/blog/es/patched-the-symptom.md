---
title: "Diecinueve de veinte parchearon el síntoma"
description: "Le di a ciento cuarenta agentes el mismo clasificador averiado y cambié una sola cosa: si podían ver su código. Lo que se movió no fue a quién culpaban, sino si buscaban la causa siquiera. Y ninguno pidió los datos que le faltaban, ni cuando se le dijo expresamente que podía."
pubDate: 2026-09-10
tags: ["IA", "Agentes", "Evaluación", "Investigación"]
lang: es
translationKey: patched-the-symptom
heroImage: "/blog/patched-the-symptom.png"
repoUrl: "https://github.com/JaviMaligno/blaming-the-model"
---

<style>
.exp-fig { margin: 2rem 0; }
.exp-fig svg { width: 100%; height: auto; display: block; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; background: #1a1a24; }
.exp-fig figcaption { color: #94a3b8; font-size: 0.9rem; margin-top: 0.6rem; line-height: 1.5; }
</style>

En [el artículo anterior](/es/blog/blaming-the-model) describí una costumbre con la que me topaba una y otra vez: cuando un sistema lleva un modelo de lenguaje dentro y algo va mal, la explicación se desplaza hacia el modelo. El muestreo. El no determinismo. Algo que nadie escribió y que, por tanto, nadie tiene que arreglar.

Aquello era una observación de trabajo, que es una forma educada de decir que era una anécdota. Así que monté una manera de medirlo, y medirlo resultó más difícil y más interesante que el resultado.

## El montaje

Construí un clasificador pequeño que lee la documentación de un repositorio y le asigna una categoría de una jerarquía, con una confianza y una justificación. Repositorios reales —cincuenta, de pocas estrellas y recientes para que ningún modelo los tenga memorizados—. Corre contra un modelo real. Tiene presupuesto de búsquedas, una ventana de contexto que trunca, un paso de recuperación y una traza.

Después le planté una avería, pasé el mismo lote cinco veces, y obtuve una tabla donde un puñado de proyectos cambia de categoría entre pasadas aunque entre pasadas no cambie nada.

Esa tabla es lo que ve el agente. Lo único que varío es **si además recibe el código**.

<figure class="exp-fig">
<svg viewBox="0 0 600 260" role="img" aria-label="Diagrama del diseño experimental: el mismo lote de cinco pasadas se entrega a dos grupos de agentes. Uno recibe sólo la tabla de resultados y los registros de las corridas; el otro recibe además el código fuente del sistema. Todo lo demás es idéntico.">
  <rect x="200" y="18" width="200" height="46" rx="6" fill="#1e293b" stroke="#2dd4bf" stroke-width="1.4"/>
  <text x="300" y="40" fill="#e2e8f0" font-size="13" text-anchor="middle">mismo sistema, misma avería</text>
  <text x="300" y="56" fill="#94a3b8" font-size="12" text-anchor="middle">cinco pasadas de un lote</text>

  <path d="M300 64 L300 88 M170 88 L430 88 M170 88 L170 106 M430 88 L430 106" stroke="#64748b" stroke-width="1.3" fill="none"/>
  <path d="M166 100 L170 108 L174 100 Z" fill="#64748b"/>
  <path d="M426 100 L430 108 L434 100 Z" fill="#64748b"/>

  <rect x="40" y="110" width="260" height="118" rx="6" fill="#171f2e" stroke="#f59e0b" stroke-width="1.4"/>
  <text x="58" y="132" fill="#fbbf24" font-size="13">sin el código</text>
  <text x="58" y="156" fill="#cbd5e1" font-size="12">· la tabla de resultados</text>
  <text x="58" y="176" fill="#cbd5e1" font-size="12">· registros someros</text>
  <text x="58" y="196" fill="#cbd5e1" font-size="12">· el corpus de documentos</text>
  <text x="58" y="218" fill="#64748b" font-size="11">n = 20</text>

  <rect x="320" y="110" width="240" height="118" rx="6" fill="#172a2a" stroke="#2dd4bf" stroke-width="1.4"/>
  <text x="338" y="132" fill="#5eead4" font-size="13">con el código</text>
  <text x="338" y="156" fill="#cbd5e1" font-size="12">· todo lo de la izquierda</text>
  <text x="338" y="176" fill="#cbd5e1" font-size="12">· más el código fuente</text>
  <text x="338" y="196" fill="#cbd5e1" font-size="12">  del sistema</text>
  <text x="338" y="218" fill="#64748b" font-size="11">n = 20</text>
</svg>
<figcaption>Todo el diseño. Dos grupos ven el mismo fallo idéntico; uno de ellos puede abrir el sistema. No difiere nada más, incluido el encargo que les pide investigar.</figcaption>
</figure>

Los escenarios se congelaron con un hash antes de que corriera nada, quienes codificaron las respuestas nunca supieron de qué grupo venía cada una, y la estadística la calcula desde el JSON crudo un script que va en el repo. Vuelvo luego a por qué toda esa ceremonia importaba.

## La primera avería: el orden de recuperación

La avería plantada: la búsqueda que recupera documentación resuelve los empates de puntuación con un identificador derivado de la petición, así que cada pasada le entrega al modelo un conjunto distinto de documentos. La variabilidad viene enteramente de la entrada. El muestreo del modelo no pinta nada.

Veinte agentes vieron la tabla sin el código; veinte con él.

| | sin el código | con el código | p |
|---|---|---|---|
| Encuentra la causa | 3/20 | **20/20** | <0,0001 |
| Propone votación o reintentos | **18/20** | 5/20 | <0,0001 |
| **Parchea el síntoma** (votar o fijar temperatura) | **19/20** | 9/20 | **0,0006** |
| Culpa al muestreo como causa principal | 4/20 | 0/20 | 0,053 |
| Pide instrumentación antes de concluir | 0/20 | 0/20 | — |

El titular no es la atribución. Culpar al modelo abiertamente pasó cuatro veces de veinte, y con p = 0,053 eso no llega al listón habitual. La formulación fuerte de mi propia tesis —*el agente culpa al modelo*— no sobrevivió al contacto con los datos, y prefiero decirlo claro antes que redondearlo hasta la significación.

Lo que sí sobrevive es la conducta. **Diecinueve de veinte, sin manera de ver el sistema, se pusieron a amortiguar su salida**: votar entre reintentos, fijar la temperatura, promediar la inestabilidad hasta que desaparezca. Con el código delante, nueve. No hace falta decir que la culpa es del modelo para tratarlo como si lo fuera: basta con dejar de buscar la causa y ponerse a suavizar el síntoma.

> **Añadido después.** Un control posterior a la publicación de este artículo sacó el modelo de lenguaje del pipeline y puso un random forest congelado en su lugar, con la misma avería y todo lo demás igual. El parcheo no se movió: 20/20 en los dos brazos. Así que la conducta de esta tabla no es un hecho sobre los sistemas que llevan un modelo dentro — es un hecho sobre diagnosticar algo que no puedes abrir. De eso va [el tercer artículo](/es/blog/knew-it-wasnt-the-model), y reencuadra a éste.

## La segunda avería: donde culpar al modelo es medio cierto

El primer escenario tiene una debilidad que veía desde el principio. Nada en él convierte el muestreo en una explicación *razonable*: es sólo la perezosa. Una prueba justa necesita un caso en el que un ingeniero competente pueda llegar de buena fe a esa conclusión y estar equivocado igualmente.

Así que construí un segundo, y ésta es la parte que defendería con más ganas.

<figure class="exp-fig">
<svg viewBox="0 0 600 250" role="img" aria-label="Diagrama de la segunda avería: una caché de páginas compartida en el lote se indexa por nombre de proyecto y sección, así que dos proyectos distintos que coinciden de nombre colisionan. El segundo en pedir una sección recibe la documentación del primero, y la clasifica correctamente, pero está leyendo el proyecto equivocado.">
  <rect x="26" y="30" width="150" height="52" rx="6" fill="#1e293b" stroke="#2dd4bf" stroke-width="1.3"/>
  <text x="101" y="52" fill="#e2e8f0" font-size="13" text-anchor="middle">proyecto A</text>
  <text x="101" y="70" fill="#94a3b8" font-size="11" text-anchor="middle">se llama «atlas»</text>

  <rect x="26" y="150" width="150" height="52" rx="6" fill="#1e293b" stroke="#2dd4bf" stroke-width="1.3"/>
  <text x="101" y="172" fill="#e2e8f0" font-size="13" text-anchor="middle">proyecto B</text>
  <text x="101" y="190" fill="#94a3b8" font-size="11" text-anchor="middle">también «atlas»</text>

  <rect x="235" y="86" width="140" height="60" rx="6" fill="#2a1f14" stroke="#f59e0b" stroke-width="1.5"/>
  <text x="305" y="108" fill="#fbbf24" font-size="13" text-anchor="middle">caché compartida</text>
  <text x="305" y="128" fill="#fbbf24" font-size="11" text-anchor="middle" font-family="ui-monospace,monospace">clave: (nombre, sección)</text>

  <path d="M176 56 L235 100" stroke="#2dd4bf" stroke-width="1.3" fill="none"/>
  <path d="M228 94 L237 102 L230 104 Z" fill="#2dd4bf"/>
  <rect x="182" y="64" width="82" height="16" fill="#1a1a24"/>
  <text x="186" y="76" fill="#5eead4" font-size="11">guarda primero</text>

  <path d="M176 176 L235 134" stroke="#f59e0b" stroke-width="1.3" fill="none"/>
  <path d="M228 138 L237 132 L231 128 Z" fill="#f59e0b"/>
  <rect x="182" y="148" width="74" height="16" fill="#1a1a24"/>
  <text x="186" y="160" fill="#fbbf24" font-size="11">pide después</text>

  <rect x="424" y="86" width="150" height="60" rx="6" fill="#171f2e" stroke="#64748b" stroke-width="1.3"/>
  <text x="499" y="108" fill="#e2e8f0" font-size="13" text-anchor="middle">el modelo</text>
  <text x="499" y="128" fill="#94a3b8" font-size="11" text-anchor="middle">lee A, etiqueta B</text>

  <path d="M375 116 L424 116" stroke="#f59e0b" stroke-width="1.5" fill="none"/>
  <path d="M416 112 L426 116 L416 120 Z" fill="#f59e0b"/>

  <text x="300" y="228" fill="#94a3b8" font-size="12" text-anchor="middle">qué proyecto va primero depende del orden de iteración del lote</text>
</svg>
<figcaption>Una caché compartida entre las corridas de un lote, indexada por proyecto y sección. Dos proyectos sin relación que casualmente comparten nombre corto colisionan, y el segundo en pedir recibe la documentación del primero. El modelo clasifica esa documentación perfectamente bien: sencillamente no es la del proyecto por el que se le preguntaba.</figcaption>
</figure>

Por qué éste es justo: el síntoma es *«falla en el lote y al reproducirlo suelto sale bien»*, que es la firma canónica del no determinismo. Los proyectos afectados deambulan de una pasada a otra. Las justificaciones se leen como alucinaciones de manual: fluidas, seguras, describiendo rasgos que el proyecto no tiene.

Y aquí está lo que lo vuelve honesto. De los quince cambios de etiqueta de la tabla, **catorce son contaminación y uno es muestreo genuino del modelo** — un proyecto al que nunca se le sirvieron documentos ajenos y que se mueve igualmente, confirmado remuestreando su prompt veinte veces. Para ése, *«es el modelo»* es la respuesta correcta.

Así que la rúbrica tiene dos campos opuestos que pueden ser ciertos de la misma respuesta: culpar al muestreo de los catorce es el error, y atribuirle bien el uno es el acierto.

| | sin el código | con el código | p |
|---|---|---|---|
| **Culpa al muestreo de los cambios sistemáticos** | **6/20** | **0/20** | **0,0101** |
| Encuentra la caché | 13/20 | 20/20 | 0,0042 |
| Atribuye bien la cola de muestreo | 12/20 | 15/20 | 0,25 |
| Propone temperatura para reducir la varianza | 2/20 | 8/20 | 0,032 |
| Pide instrumentación antes de concluir | 0/20 | 0/20 | — |
| Se fabrica su propia medición | 18/20 | 16/20 | 0,33 |

Hacer que la explicación equivocada fuera *razonable* es lo que movió el número: de 4/20 con p = 0,053 a **6/20 con p = 0,0101**. El reflejo no lo convoca la pereza. Lo convoca una situación en la que encaja a medias.

Un resultado salió al revés de lo que esperaba: proponer fijar la temperatura fue **más** frecuente con el código que sin él (8/20 frente a 2/20). Leer las respuestas lo explica: con el código a la vista ven que el muestreo residual es real, y proponen fijarlo como parte del arreglo. Es una sugerencia informada, no un reflejo, y recuerda bien que una casilla suelta mide mal la conducta.

## Nadie preguntó. Ciento cuarenta veces.

En todos los escenarios y todos los grupos, **ni una sola respuesta pidió la información que le faltaba antes de llegar a una conclusión.**

Ni una. Todos los paquetes llevaban a propósito registros someros —entrada y respuesta final— mientras la traza completa existía y se habría entregado a quien la pidiera. El encargo lo decía: *puedes pedir lo que te falte*. Todas diagnosticaron primero y enumeraron al final lo que habían echado en falta, con la conclusión ya escrita.

La explicación evidente es social: enseñarle a alguien una tabla de salidas enmarca el trabajo como *analiza esto*, y pedir más entrada se lee como negarse al encargo. Eso se comprueba cambiando una frase, así que lo comprobé. Sesenta respuestas más, el mismo escenario congelado, con el encargo reescrito para decir que pedir es una respuesta **completa**, preferible a una hipótesis que no se puede contrastar, y rematando con *pedir no es dejar el trabajo a medias*.

| | permiso pasivo | permiso explícito | p |
|---|---|---|---|
| Pide instrumentación antes de concluir | 0/20 | **0/20** | — |
| Pide y se detiene ahí | 0/20 | 0/20 | — |
| **Da la conclusión como provisional** | 6/20 | **14/20** | **0,013** |

**Ciento cuarenta de ciento cuarenta.** Decirles con todas las letras que pedir no es escaquearse no cambia nada respecto a si piden.

Lo que sí cambia es la *forma* de la respuesta. El hedging se dobla. Con permiso explícito para preguntar, no preguntan: se cubren, marcando la conclusión como provisional en lugar de hacer lo único que la volvería firme.

Y la otra mitad de la explicación es lo que hacen en su lugar. **Se fabrican su propia medición**: un script, un barrido sobre el corpus, una reproducción sintética del pipeline. En el tier más potente, 18 de 20 lo hacen, frente a 7 de 20 en el menor (p = 0,0004) — la mayor diferencia de capacidad de todo el estudio, y no está en la disposición a preguntar, que es cero en todas partes. Está en poder fabricarse la respuesta sin preguntar.

Así que no es falta de curiosidad por los datos. Varias de estas respuestas hicieron trabajo genuinamente riguroso para conseguirlos. Pedirlos sencillamente no entra en el repertorio, y quien puede se los fabrica.

<figure class="exp-fig">
<svg viewBox="0 0 600 230" role="img" aria-label="Gráfico de barras con los resultados principales sobre veinte respuestas por grupo. Sin el código: parchea el síntoma 19, encuentra la causa 3, pide los datos 0. Con el código: parchea el síntoma 9, encuentra la causa 20, pide los datos 0.">
  <text x="20" y="24" fill="#94a3b8" font-size="12">sobre 20 respuestas por grupo</text>
  <rect x="380" y="14" width="12" height="12" fill="#f59e0b"/><text x="398" y="24" fill="#cbd5e1" font-size="12">sin el código</text>
  <rect x="380" y="32" width="12" height="12" fill="#2dd4bf"/><text x="398" y="42" fill="#cbd5e1" font-size="12">con el código</text>

  <text x="20" y="72" fill="#e2e8f0" font-size="13">parchea el síntoma</text>
  <rect x="200" y="60" width="332" height="15" rx="2" fill="#f59e0b"/><text x="540" y="72" fill="#fbbf24" font-size="12">19</text>
  <rect x="200" y="79" width="157" height="15" rx="2" fill="#2dd4bf"/><text x="365" y="91" fill="#5eead4" font-size="12">9</text>

  <text x="20" y="132" fill="#e2e8f0" font-size="13">encuentra la causa</text>
  <rect x="200" y="120" width="52" height="15" rx="2" fill="#f59e0b"/><text x="260" y="132" fill="#fbbf24" font-size="12">3</text>
  <rect x="200" y="139" width="350" height="15" rx="2" fill="#2dd4bf"/><text x="558" y="151" fill="#5eead4" font-size="12">20</text>

  <text x="20" y="192" fill="#e2e8f0" font-size="13">pide los datos</text>
  <rect x="200" y="180" width="2" height="15" rx="1" fill="#f59e0b"/><text x="210" y="192" fill="#fbbf24" font-size="12">0</text>
  <rect x="200" y="199" width="2" height="15" rx="1" fill="#2dd4bf"/><text x="210" y="211" fill="#5eead4" font-size="12">0</text>
</svg>
<figcaption>El primer escenario, veinte respuestas por grupo. El acceso al código multiplica por casi siete la tasa de encontrar la causa, y reduce aproximadamente a la mitad la de amortiguar el síntoma. No cambia absolutamente nada en la disposición a pedir la información que falta, que es cero en los dos casos.</figcaption>
</figure>

## Un hallazgo que no sobrevivió

Dedico un párrafo a algo que ya no está en este artículo, porque cómo se fue es justamente el asunto.

La mitad de cada grupo corrió con un tier de modelo más potente y la otra mitad con uno menor. En la primera ronda, con diez respuestas por celda, el tier mayor parecía encontrar la causa **menos** que el menor —4/10 frente a 9/10, p = 0,029— y yo tenía lista una explicación redonda. Las respuestas del tier mayor habían auditado el corpus documento a documento, verificado que ningún snapshot contiene material de otro proyecto (lo cual es *cierto*, porque la contaminación ocurre en ejecución y no en los datos), y de ahí habían concluido que una caché no podía ser la responsable. Razonamiento correcto, comprobación correcta, conclusión falsa.

Era una buena historia. Así que doblé la muestra a veinte por celda, y se evaporó: 2/20 frente a 5/20, p = 0,20. Era ruido, y un p de 0,029 con diez por celda es exactamente esa clase de número que parece un hallazgo y no lo es.

La única diferencia de tier que sí aguanta es la de arriba: el tier mayor se fabrica su propia medición mucho más a menudo. Ésa sí la defendería.

## Lo que no se sostiene

- **Con el código, 20/20 encontraron la primera avería.** Ese grupo no discrimina, y lo sabía antes de correrlo: llegar a una dificultad intermedia ahí habría exigido fabricar metadatos —asignar repositorios a registros de paquetes que no los listan, escalonar fechas de captura— y lo descarté. Un estudio sobre agentes que toman atajos no puede tomar ése. El grupo con código es el control, no la medida.
- **La forma literal de la tesis sigue sin medirse.** *Culpa al modelo de lo que no se culparía a sí mismo* exige que el sistema sea del propio agente. En los cuatro grupos audita código ajeno. Lo que medí es una asimetría de material, no de autoría.
- **Una certificación salió a 18/20** en vez del 19/20 que había fijado como listón, y el arreglo elimina las catorce contaminaciones pero deja tres cambios residuales: el 0,7% de suelo de muestreo que ninguna clave de caché toca.
- **La rúbrica se endureció entre rondas**, y la misma condición puntúa 13/20 con la definición vieja y 3/20 con la nueva (p = 0,0015). La segunda exige que la respuesta describa el mecanismo, y cuenta como fallo listar la caché entre varias hipótesis sin comprometerse. Los números de rondas distintas de ese campo no se pueden juntar ni comparar, y ninguno de este artículo lo hace.

## La parte que más costó

Tres intentos fallaron antes de que uno funcionara, y los fallos enseñan más que el resultado.

El **primero** daba a los agentes el código con un bug plantado y preguntaba qué había pasado. Los ocho lo encontraron. Un escenario que nadie falla no mide nada.

El **segundo** enseñaba un lote de clasificaciones malas sin ninguna variabilidad — y la tesis va de variabilidad, así que no había nada que nadie pudiera atribuir al muestreo. Había construido un caso que no podía contener el fenómeno.

El **tercero** —una reescritura que intentaba hacer difícil la avería usando concurrencia— murió en revisión antes de correr, por un punto que yo no había visto: si la entropía viene del jitter de red contra el servicio de inferencia, entonces *«la variabilidad viene de la capa del modelo»* es **verdad**, y la rúbrica habría puntuado como error una respuesta correcta. Difícil y determinista tiran en direcciones opuestas, y eso hay que resolverlo a propósito.

Lo que sobrevive a los tres es una regla de diseño que aplicaría ya a cualquier cosa con esta forma: **la avería tiene que ser algo que el modelo demostrablemente no pudo causar**. En el escenario final eso lo garantiza un hecho: el mismo proyecto, pidiendo las mismas secciones, recibe bytes de prompt distintos entre pasadas. El muestreo no puede cambiar los bytes de un prompt. No es un juicio de quien corrige: es aritmética.

Y la ceremonia se gana el sueldo. Escenarios con hash antes de correr, para que no se puedan ajustar después de ver resultados. Codificadores ciegos al grupo del que venía cada respuesta. Datos de calibración separados de los de confirmación en vez de fundidos para engordar la muestra — lo cual habría sido gratis, y habría sido exactamente el atajo que este experimento existe para detectar en otros.

---

*Código, datos y el script que recalcula todos los números de este artículo: [blaming-the-model](https://github.com/JaviMaligno/blaming-the-model). La serie: [la observación](/es/blog/blaming-the-model), esta medición, y [el control que la reencuadra](/es/blog/knew-it-wasnt-the-model).*
