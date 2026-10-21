---
title: "La regla estaba en la otra rama"
description: "Las prácticas de un equipo viven en la checklist de un repo, en la wiki de la organización, en las convenciones de un proyecto y en la cabeza de la gente. Hice delivery-loop para escribirlas donde aplican y mantenerlas al día. Una ejecución real mostró por qué importa lo segundo: la regla que debía frenar un merge estaba al día en una rama y faltaba en la copia con la que arrancaron los agentes."
pubDate: 2026-11-17
tags: ["Agentes de IA", "Claude Code", "Codex", "Entrega de software", "Experiencia de desarrollo"]
lang: es
translationKey: the-rule-was-on-the-other-branch
heroImage: "/blog/the-rule-was-on-the-other-branch.png"
repoUrl: "https://github.com/JaviMaligno/delivery-loop"
---

<style>
.dl-fig { margin: 2rem 0; }
.dl-fig svg { width: 100%; height: auto; display: block; background: #1a1a24; border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; }
.dl-fig figcaption { font-size: 0.9rem; color: #94a3b8; margin-top: 0.6rem; }
</style>

En todos los equipos en los que he trabajado, las prácticas están repartidas por una docena de sitios. La checklist de PR vive en un repositorio. La regla de quién promociona a producción vive en una página de la wiki de toda la organización. La rama en la que integra un proyecto es una convención de ese proyecto, a veces escrita y a veces no. El comando de tests está en un README, salvo que se haya mudado a un Makefile. Y buena parte vive solo en la cabeza de quien lleva más tiempo allí.

Las personas se apañan porque lo absorben durante meses. Un agente empieza cada sesión sin nada de eso, o con una copia que alguien pegó en un prompt y que se quedó vieja a la semana. Me encontraba una y otra vez los mismos fallos: trabajo rehecho porque se olvidaba una rama anterior, «desplegado» entendido como «sirviendo», un ticket cerrado sin pruebas y las mismas cinco preguntas sobre mi entorno al empezar cada sesión.

Así que hice [delivery-loop](https://github.com/JaviMaligno/delivery-loop), un plugin que lleva una tarea desde su origen (un ticket, un documento de requisitos, una petición) hasta un cambio integrado, verificado en vivo en un entorno de pruebas, traspasado para su promoción y cerrado. El bucle en sí es la parte fácil. La que me importa es cómo aprende las prácticas del sitio donde se ejecuta y cómo las mantiene al día cuando cambian.

## Cada práctica tiene su nivel

El núcleo del plugin no nombra ninguna herramienta. Dice qué recibe cada fase, qué produce y qué evidencia demuestra que está hecha. Todo lo específico de un entorno va en un perfil, y los perfiles van por capas:

<figure class="dl-fig">
<svg viewBox="0 0 600 300" role="img" aria-label="Cuatro niveles de perfil apilados de lejano a cercano: valores por defecto del plugin, usuario, organización o proyecto, y repositorio. Cada nivel guarda prácticas distintas, gana el más cercano y lo marcado como invariante no se puede relajar por debajo.">
  <g font-family="ui-sans-serif,system-ui,sans-serif">
    <rect x="40" y="24" width="370" height="50" rx="8" fill="#22222e" stroke="rgba(255,255,255,0.1)"/>
    <text x="58" y="47" fill="#e2e8f0" font-size="15" font-weight="600">Por defecto</text>
    <text x="58" y="65" fill="#94a3b8" font-size="12">clases de autoridad, invariantes, metodología</text>
    <rect x="40" y="88" width="370" height="50" rx="8" fill="#22222e" stroke="rgba(255,255,255,0.1)"/>
    <text x="58" y="111" fill="#e2e8f0" font-size="15" font-weight="600">Usuario</text>
    <text x="58" y="129" fill="#94a3b8" font-size="12">tu máquina, tus accesos, tu autonomía</text>
    <rect x="40" y="152" width="370" height="50" rx="8" fill="#22222e" stroke="rgba(255,255,255,0.1)"/>
    <text x="58" y="175" fill="#e2e8f0" font-size="15" font-weight="600">Organización / proyecto</text>
    <text x="58" y="193" fill="#94a3b8" font-size="12">tracker, convenciones de CI, revisores, quién promociona</text>
    <rect x="40" y="216" width="370" height="50" rx="8" fill="#1f2a2c" stroke="#2dd4bf"/>
    <text x="58" y="239" fill="#5eead4" font-size="15" font-weight="600">Repositorio</text>
    <text x="58" y="257" fill="#94a3b8" font-size="12">ramas, comandos de test, URLs de entornos</text>
    <line x1="440" y1="40" x2="440" y2="250" stroke="#64748b" stroke-width="2"/>
    <path d="M432 240 L440 254 L448 240 Z" fill="#64748b"/>
    <text x="456" y="120" fill="#e2e8f0" font-size="13">lejos → cerca</text>
    <text x="456" y="140" fill="#94a3b8" font-size="12">gana el cercano</text>
    <text x="456" y="176" fill="#fbbf24" font-size="12">[invariant]</text>
    <text x="456" y="194" fill="#94a3b8" font-size="12">no se relaja</text>
    <text x="456" y="210" fill="#94a3b8" font-size="12">por debajo</text>
  </g>
</svg>
<figcaption>Cada práctica se escribe una vez, en el nivel donde es verdad. Gana el nivel más cercano, salvo los invariantes como «producción no se toca», que ningún nivel inferior puede relajar.</figcaption>
</figure>

Esto refleja dónde viven ya las prácticas. «La promoción a producción la hace el equipo X» es verdad para toda la organización, así que va en el perfil de la organización. «Este repo integra en `develop`, no en `main`» es verdad para un repositorio, así que va ahí. Nada se copia a cada repo y nada está en el plugin.

Eso último es lo que permite que el mismo bucle funcione en cualquier sitio. El repo público solo lleva perfiles de ejemplo ficticios; los reales de mi empresa viven en un repo privado de esa empresa. El mismo plugin funciona, sin cambios, en Claude Code y en Codex.

## Escribirlas sin un cuestionario

Nadie rellena un perfil de cuarenta campos, así que casi todo lo hace una skill llamada `census`. Primero detecta: el remote de git y la protección de ramas, la configuración de CI y qué jobs corren en cada evento, los runners de tests, la configuración de despliegue, las herramientas y servidores MCP que tiene la sesión. Solo pregunta lo que la detección no resuelve, una vez y con una respuesta recomendada. Cada dato se escribe en su nivel, con su origen y la fecha en que se comprobó.

Una regla se ganó su sitio enseguida: un procedimiento copiado de un documento no es un procedimiento verificado. Antes de que `census` escriba «se promociona mergeando la rama A en B», comprueba que el remote y la rama existen y que el push avanzaría sin conflicto. Si el procedimiento documentado no funciona, escribe el que sí funciona, con la evidencia.

## Mantenerlas al día

Un perfil que era correcto al escribirlo se queda viejo solo. Me pasó lo mismo cuando [audité las memorias que guarda mi agente](/es/blog/the-memory-that-was-true): las obsoletas nunca fueron falsas al escribirse, describían un estado que caducó. Por eso el perfil se trata como algo que hay que volver a comprobar, no como algo de lo que fiarse:

- Al empezar cada tarea, una comprobación barata compara el perfil con lo que muestra el repo: remote, rama por defecto, protección, configuración de despliegue, checks obligatorios. Si algo no cuadra, se actualiza ese dato en su nivel y se deja una línea en el informe.
- Cualquier dato con más de 30 días se vuelve a verificar antes de que el bucle se apoye en él.
- Cuando el perfil y otra fuente no coinciden, gana la fuente fechada más reciente, la vieja se corrige donde vive y el cambio queda registrado. Sin fecha o con la misma fecha: pregunta. Una nota antigua que manda hacer las pruebas con una cuenta compartida pierde frente a una regla más nueva que exige una nominativa.
- Los datos de estructura no tienen margen. Un repositorio que se movió de carpeta conservaba en su perfil un enlace fechado, marcado como verificado y ya falso, así que rutas y enlaces se recomprueban siempre.
- Los perfiles se vuelven a combinar al entrar en integración y en verificación en vivo, porque las reglas pueden cambiar a mitad de tarea.

Esa es toda la idea: escribir cada práctica donde aplica y dar por hecho que va a cambiar.

## Una ejecución real, en el otro harness

Llevaba un par de días usando el plugin con Claude Code. Luego lo instalé en Codex CLI (0.163, con gpt-6.1-sol en esfuerzo medio) y le di un ticket real del trabajo con una sola instrucción: impleméntalo. El ticket pedía que el contrato publicado de la API de un [servicio de clasificación que mantengo](/es/projects/compliance-classifier) coincidiera con lo que el servicio emite de verdad, en cinco puntos.

En trece minutos pasó de la fase 0 a la 6, con cada paso en su registro de la tarea:

- **Inicio.** Dimensionó la tarea como una feature, creó un worktree aislado y eligió `develop` en lugar de un `main` desfasado porque es donde integra de verdad el repo, dejando la decisión escrita.
- **Spec y huecos.** Convirtió el ticket en cinco requisitos con IDs estables y registró siete decisiones. Una de ellas descartaba un campo a propósito: el schema prometía un valor que el formateador nunca emite, así que en vez de documentarlo, el cambio borra la declaración muerta y explica por qué.
- **Plan.** Un segundo agente revisó el plan antes de escribir código.
- **Implementación.** Escribió primero los tests de contrato que fallan (14 en rojo, 4 en verde) y después la implementación, en commits ligados a los IDs de requisito.
- **Revisión e integración.** Una revisión independiente, la PR abierta y 199 tests en verde.

Y entonces se paró.

## La parada

El repositorio tiene una checklist de PR, y una de sus reglas pide que una persona dé fe de que ha revisado y validado el código generado por IA antes de que salga. Codex lo registró como decisión D0.7, dejó esa casilla sin marcar y me pidió revisión en lugar de mergear. Sus propias palabras en la decisión: una revisión automática no puede sustituir a la atestación de una persona.

La regla no era nueva: llevaba dos semanas y media en la rama de integración. Los dos tickets anteriores del mismo repositorio habían pasado por el mismo plugin con Claude Code a lo largo del día anterior, y los dos se mergearon sin ella. Parece una diferencia entre agentes. No lo es, y la causa real es más útil.

Las tres ejecuciones se lanzaron desde el mismo directorio, mi checkout principal del repositorio, que estaba en una rama de principios de mes. Sus ficheros de instrucciones son anteriores a la regla: ninguno menciona la checklist de PR. Luego el bucle trabaja en un worktree nuevo sobre la rama de integración, donde las instrucciones están al día y la regla está. Así que todas las ejecuciones arrancaron con la misma copia desfasada de las prácticas del repositorio, y las actuales estaban a un directorio de distancia.

Lo que cambió fue si el agente fue a leerlas. Durante la fase 0, Codex abrió el fichero de instrucciones del worktree buscando sus reglas de desarrollo, tests y flujo de trabajo, encontró la regla de revisión y, más tarde, leyó la propia checklist antes de escribir D0.7. Nada en el plugin se lo pedía. Las ejecuciones con Claude trabajaron en la misma rama sin releer esos ficheros; en una de ellas, las instrucciones del worktree entraron por primera vez en el contexto 94 minutos después del merge.

<figure class="dl-fig">
<svg viewBox="0 0 600 270" role="img" aria-label="Todas las ejecuciones arrancaron desde un checkout en una rama vieja cuyos ficheros de instrucciones no tenían la regla de revisión. El trabajo se hizo en un worktree sobre la rama de integración, donde la regla existía. Codex releyó las instrucciones del worktree en la fase 0 y se paró antes del merge; las ejecuciones con Claude no las releyeron y mergearon.">
  <g font-family="ui-sans-serif,system-ui,sans-serif">
    <rect x="30" y="24" width="250" height="62" rx="8" fill="#22222e" stroke="rgba(255,255,255,0.15)"/>
    <text x="155" y="48" fill="#e2e8f0" font-size="14" font-weight="600" text-anchor="middle">Checkout de arranque</text>
    <text x="155" y="68" fill="#94a3b8" font-size="12" text-anchor="middle">rama vieja · sin la regla</text>
    <rect x="320" y="24" width="250" height="62" rx="8" fill="#1f2a2c" stroke="#2dd4bf"/>
    <text x="445" y="48" fill="#5eead4" font-size="14" font-weight="600" text-anchor="middle">Worktree de la tarea</text>
    <text x="445" y="68" fill="#94a3b8" font-size="12" text-anchor="middle">rama de integración · con la regla</text>
    <path d="M282 55 L316 55" stroke="#64748b" stroke-width="2"/>
    <path d="M308 49 L318 55 L308 61 Z" fill="#64748b"/>
    <rect x="30" y="130" width="250" height="44" rx="8" fill="#22222e" stroke="rgba(255,255,255,0.1)"/>
    <text x="155" y="157" fill="#e2e8f0" font-size="13" text-anchor="middle">Codex: relee en la fase 0</text>
    <rect x="320" y="130" width="250" height="44" rx="8" fill="#22222e" stroke="rgba(255,255,255,0.1)"/>
    <text x="445" y="157" fill="#e2e8f0" font-size="13" text-anchor="middle">Claude Code (2): no relee</text>
    <path d="M155 174 L155 204" stroke="#2dd4bf" stroke-width="2"/>
    <path d="M445 174 L445 204" stroke="#64748b" stroke-width="2" stroke-dasharray="5 4"/>
    <rect x="30" y="206" width="250" height="44" rx="8" fill="#1f2a2c" stroke="#2dd4bf"/>
    <text x="155" y="233" fill="#5eead4" font-size="13" text-anchor="middle">se para y pide revisión</text>
    <rect x="320" y="206" width="250" height="44" rx="8" fill="#2a2418" stroke="#f59e0b"/>
    <text x="445" y="233" fill="#fbbf24" font-size="13" text-anchor="middle">mergea sin la regla</text>
  </g>
</svg>
<figcaption>La regla existía y estaba al día. Que se aplicara dependió de si el agente releía las prácticas de la rama en la que de verdad trabajaba.</figcaption>
</figure>

Quiero ser cuidadoso con lo que esto demuestra. Es una ejecución contra dos, no una comparación de modelos, y no lo leería como «Codex es más prudente»: leyó el fichero correcto una vez, por iniciativa propia, sin que el bucle le diera motivo. Era un hueco de mi bucle, y es justo el problema del que va este artículo. El plugin vuelve a comprobar su propio perfil al empezar cada tarea, pero no relee los ficheros de instrucciones del repositorio desde la rama donde se hace el trabajo. La práctica estaba escrita en el sitio correcto y al día; los agentes simplemente arrancaron con una copia anterior. Así que el arreglo fue a la fase 0, junto a la comprobación del perfil, no a una regla sobre checklists. Desde la versión 0.7.1, cuando la sesión se lanzó desde un checkout en una rama que no es la de integración ni la de producción, la fase 0 lee los ficheros de instrucciones del agente, y lo que importan, desde el workspace nuevo, sigue esos y registra de qué fichero y de qué rama salieron. No he vuelto a lanzar un ticket desde entonces, así que ese comportamiento está publicado, pero aún no probado en vivo.

Cuando aprobé el merge, el bucle registró la aprobación con un matiz: permiso para mergear, no una atestación de revisión línea a línea. Es exactamente la diferencia que la regla existe para proteger, y ahora está escrita con mi nombre y la fecha.

## Discrepar con evidencia

Tras la parada, una revisión externa encontró tres problemas, que volvieron a la misma sesión de Codex. Reprodujo dos de ellos con tests que fallaban antes de cambiar nada. Una de las instrucciones que le llegaron pedía que el enum publicado de motivos fuera literalmente igual a una constante del código. Codex comprobó antes el código fuente y vio que el servicio emite un valor más, `content_filtered`, desde una segunda ruta. Dejó escrito en el registro que la igualdad literal «excluiría un valor real», publicó el conjunto completo y volvió a pasar la suite entera (6.609 tests), corrigiendo de paso una entrada de deuda conocida que había quedado desfasada.

Es el comportamiento que más quiero del bucle, por encima de cualquier fase concreta. La decisión no es el gusto del agente contra el mío: es un motivo escrito, con la evidencia al lado, que puedo leer y revocar.

## Lo que encontró la comprobación en vivo

Tras el merge, el bucle comprobó que la build publicó la imagen con el nombre exacto que esperaba, mirando el manifiesto y su digest en el log de la build en lugar del veredicto de la build. Mergeó la subida de versión en el repositorio de configuración del entorno de pruebas y esperó a que las dos réplicas sirvieran ese commit exacto antes de dar la integración por hecha.

Después, la fase 7 recorrió los requisitos uno a uno contra el servicio desplegado. Los puntos sobre el contrato publicado pasaron contra el Swagger que sirve el despliegue, idéntico byte a byte al fichero mergeado. La ruta rara, el filtro de contenido, pasó con sondas deterministas sobre el módulo desplegado, y el log dice claramente que no se disparó ningún filtro real del proveedor. Una llamada HTTP real devolvió 200 con el servicio absteniéndose al agotar su tiempo de investigación, registrado como «no es una prueba de acierto». Los datos de prueba vivían en un tenant reservado para esa QA, y su caché se borró y se comprobó vacía al terminar.

Entonces una comparación recursiva de una respuesta real contra el contrato publicado encontró dos campos anidados que el servicio ya devolvía y el contrato no declaraba. El aprobado anterior de ese punto venía de fixtures; el bucle lo marcó como sustituido por el fallo contra la respuesta real.

Volvió por su cuenta a las fases 4 a 6. Primero tres tests en rojo, luego el arreglo, que solo declara lo que ya se emitía, y después una revisión independiente. Mientras tanto, una PR ajena había movido la rama de integración y el fast-forward protegido se paró. El bucle hizo un merge de prueba, integró con un merge commit para no perder ese trabajo y repitió los tests sobre el resultado, incluidos los del cambio ajeno. Reapuntó el cambio de configuración al nuevo commit y archivó la evidencia de la primera pasada antes de repetirla.

Ahí está la ejecución mientras escribo esto: la imagen corregida espera en cola a que haya un runner para la build, y el cambio de configuración sigue sin mergear a propósito, porque no se despliega nada sin un manifiesto verificado. La promoción más allá del entorno de pruebas la hace otro equipo de mi organización, así que la fase 8 terminará en un traspaso explícito, con el motivo, el responsable y el material preparado, en lugar de un paso que se salta.

La fase 7 también tiene que decir lo que no pudo medir. Un criterio que solo mostrará el tráfico real, o que una caída dejó sin comprobar, se marca 🔄 con su causa y una espera fechada, y el ticket sigue abierto hasta medirlo. Nunca se marca como superado con una nota: un criterio sin medir anotado así se lee como un aprobado para quien repasa el informe en diagonal.

## Comprobar el entorno antes de fiarse de él

Las prácticas son la mitad de lo que el bucle tiene que saber de un sitio. La otra mitad es el entorno: las cuentas, herramientas y conexiones que va a usar la tarea. Estas fallan de una forma que un perfil no detecta, porque parecen bien cuando preguntas por ellas.

Configurado no es autenticado, autenticado no es expuesto en la sesión, y expuesto no es que funcione. Una herramienta que aparecía como conectada devolvió `invalid_grant` en su primera llamada real. `gh auth status` decía una cuenta de GitHub mientras los comandos corrían con otra que no veía el repositorio; la cuenta que de verdad se usa es la que devuelve `gh api user`. Una pestaña del navegador seguía mostrando el entorno de pruebas con la VPN caída, porque una página ya cargada no prueba que haya acceso. Un linter local una versión mayor por detrás del CI pasó una comprobación que luego el CI suspendió.

Por eso la fase 0 empieza con una comprobación previa. Cada capacidad que va a usar la tarea se prueba con una llamada real, y las herramientas locales de comprobación corren en la versión que fija el repositorio o el CI. Lo que falla se plantea en una sola ronda, ofreciendo el sustituto que se aceptó la vez anterior, y la respuesta se guarda para que la siguiente ejecución no vuelva a preguntar. Sin ella, los problemas de configuración aparecen de uno en uno a mitad de la tarea.

La misma regla vale en el otro extremo. Un despliegue marcado «SUCCESS» no dice qué commit se está sirviendo; lo que cuenta es el SHA que reporta la plataforma, o un contenido que solo produce el cambio. Por eso la ejecución de arriba esperó a que los dos pods sirvieran el commit exacto.

En Codex, el entorno necesitó dos cosas, ninguna de ellas un cambio en el plugin: un sandbox con red para el merge, el despliegue y las comprobaciones en vivo, y un servidor MCP para el tracker y el host del código. Encontró esas herramientas por su cuenta.

Lo que no hace es inventarse prácticas. Las lee, las escribe en su nivel, las vuelve a comprobar y se para cuando una lo pide. Si una práctica solo existe en la cabeza de alguien, el bucle preguntará una vez. Si existe en una rama que el agente no ha releído, pasa lo de esta ejecución, y por eso releer es la parte que más me importa.

---

*[delivery-loop en GitHub](https://github.com/JaviMaligno/delivery-loop) (MIT). Se instala en Claude Code con `claude plugin marketplace add JaviMaligno/delivery-loop`, o en Codex con `codex plugin marketplace add JaviMaligno/delivery-loop`. Más de lo que empaqueto para agentes en [Plugins y Skills](/es/skills).*
