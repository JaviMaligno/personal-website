---
title: "La regla estaba en la otra rama"
description: "Las prácticas de un equipo viven en el checklist de un repo, una wiki de la organización, una convención del proyecto y la cabeza de la gente. delivery-loop escribe cada una una vez, en el nivel donde es verdad: lo de la organización se comparte, lo tuyo se escribe una vez y lo de cada repo viaja con el repo."
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

Todos los equipos con los que he trabajado guardan sus prácticas en una docena de sitios. El checklist de las PR vive en un repositorio. Quién promueve a producción está en una página de la wiki de toda la organización. La rama en la que integra un proyecto es una convención de ese proyecto. El comando de tests está en un README, salvo que se haya movido a un Makefile. Y buena parte solo vive en la cabeza de quienes llevan más tiempo.

Las personas lo absorben en meses. Un agente empieza cada sesión sin nada de eso, o con una copia que alguien pegó en un prompt y que se quedó vieja a la semana siguiente.

[delivery-loop](https://github.com/JaviMaligno/delivery-loop) es un plugin para Claude Code y Codex que lleva una tarea desde su ticket hasta un cambio verificado en un entorno de pruebas y traspasado. Llevar una tarea hasta el final no es nuevo por sí solo. Lo que hace que funcione en más de un sitio es de dónde saca el agente las prácticas del sitio donde trabaja, cómo se comparten entre quienes lo usan y cómo se mantienen al día sin que nadie tenga que mantenerlas.

## El bucle, fase a fase

Primero, qué hace el bucle. Una tarea pasa por diez fases; una pequeña se salta la especificación, las preguntas abiertas y el plan.

<figure class="dl-fig">
<svg viewBox="0 0 600 270" role="img" aria-label="Las diez fases del bucle en cuatro grupos: entender (arranque, especificación, huecos, plan), construir (implementar, revisar), demostrar (integrar hasta que el entorno de pruebas sirve el commit exacto, verificación en vivo con evidencia por requisito) y traspasar (promover o traspasar, cerrar el ticket).">
  <g font-family="ui-sans-serif,system-ui,sans-serif" text-anchor="middle">
    <g fill="#22222e" stroke-width="1.5">
      <rect x="20" y="30" width="100" height="62" rx="8" stroke="#94a3b8"/>
      <rect x="134" y="30" width="100" height="62" rx="8" stroke="#94a3b8"/>
      <rect x="248" y="30" width="100" height="62" rx="8" stroke="#94a3b8"/>
      <rect x="362" y="30" width="100" height="62" rx="8" stroke="#94a3b8"/>
      <rect x="476" y="30" width="100" height="62" rx="8" stroke="#2dd4bf"/>
      <rect x="20" y="146" width="100" height="62" rx="8" stroke="#2dd4bf"/>
      <rect x="134" y="146" width="100" height="62" rx="8" stroke="#f59e0b"/>
      <rect x="248" y="146" width="100" height="62" rx="8" stroke="#f59e0b"/>
      <rect x="362" y="146" width="100" height="62" rx="8" stroke="#e2e8f0"/>
      <rect x="476" y="146" width="100" height="62" rx="8" stroke="#e2e8f0"/>
    </g>
    <g fill="#e2e8f0" font-size="14" font-weight="600">
      <text x="70" y="56">0 arranque</text>
      <text x="184" y="56">1 spec</text>
      <text x="298" y="56">2 huecos</text>
      <text x="412" y="56">3 plan</text>
      <text x="526" y="56" font-size="13">4 implementar</text>
      <text x="70" y="172">5 revisar</text>
      <text x="184" y="172">6 integrar</text>
      <text x="298" y="172">7 en vivo</text>
      <text x="412" y="172">8 promover</text>
      <text x="526" y="172">9 cerrar</text>
    </g>
    <g fill="#94a3b8" font-size="11">
      <text x="70" y="76">¿hecho? tamaño</text>
      <text x="184" y="76">puntos con ID</text>
      <text x="298" y="76">dudas abiertas</text>
      <text x="412" y="76">plan revisado</text>
      <text x="526" y="76">tests primero</text>
      <text x="70" y="192">segunda opinión</text>
      <text x="184" y="192">sirve ese SHA</text>
      <text x="298" y="192">evidencia por ID</text>
      <text x="412" y="192">o traspaso</text>
      <text x="526" y="192">ticket, limpieza</text>
    </g>
    <g stroke="#64748b" stroke-width="1.5" fill="none">
      <path d="M120 61 L132 61"/><path d="M234 61 L246 61"/><path d="M348 61 L360 61"/><path d="M462 61 L474 61"/>
      <path d="M120 177 L132 177"/><path d="M234 177 L246 177"/><path d="M348 177 L360 177"/><path d="M462 177 L474 177"/>
      <path d="M526 92 L526 119 L70 119 L70 144"/>
    </g>
    <g font-size="12">
      <rect x="60" y="234" width="10" height="10" rx="2" fill="none" stroke="#94a3b8"/><text x="108" y="243" fill="#94a3b8">entender</text>
      <rect x="180" y="234" width="10" height="10" rx="2" fill="none" stroke="#2dd4bf"/><text x="226" y="243" fill="#5eead4">construir</text>
      <rect x="290" y="234" width="10" height="10" rx="2" fill="none" stroke="#f59e0b"/><text x="338" y="243" fill="#fbbf24">demostrar</text>
      <rect x="400" y="234" width="10" height="10" rx="2" fill="none" stroke="#e2e8f0"/><text x="448" y="243" fill="#e2e8f0">traspasar</text>
    </g>
  </g>
</svg>
<figcaption>Diez fases en cuatro grupos. Una tarea pequeña pasa del arranque directamente a implementar.</figcaption>
</figure>

- **Entender.** Comprueba si el trabajo ya está hecho (un ticket marcado como pendiente puede estar en producción por una PR que nunca lo citó), crea un espacio de trabajo aislado y dimensiona la tarea. Convierte el ticket o el documento en puntos con IDs estables, separa lo que solo puede decidir una persona y escribe un plan que otro agente revisa antes de tocar código.
- **Construir.** Primero los tests, luego el cambio, en commits ligados a los IDs; después una revisión independiente con los revisores que diga el perfil.
- **Demostrar.** Tras el merge, espera a que el entorno de pruebas sirva ese commit exacto, no a que el despliegue diga que ha ido bien. Luego comprueba cada ID contra el entorno desplegado. Siempre que haya algo que ver, la evidencia es visual: capturas o una grabación, que se suben al ticket. Una API o una cola llevan en su lugar una respuesta real.
- **Traspasar.** La promoción a producción o, cuando es cosa de otro, un traspaso explícito con el material preparado. Después el ticket pasa a hecho con su evidencia, y se limpian ramas, espacios de trabajo y datos de prueba.

Casi cada uno de esos pasos se apoya en una práctica del sitio: qué estado del ticket significa «en revisión», quién revisa, en qué rama se integra, cómo llega un cambio al entorno de pruebas, quién promueve. Para eso están los perfiles.

## Cada práctica se escribe una vez, en su nivel

El núcleo del plugin no nombra ninguna herramienta. Todo lo propio de un sitio va en un perfil, y los perfiles van por niveles que reflejan dónde viven ya las prácticas. «La promoción a producción es del equipo de plataforma» es verdad para toda la organización, así que va en el perfil de la organización. «Este repo integra en `develop`» es verdad para un repositorio, así que va ahí. Nada se copia en cada repo y nada está en el plugin.

<figure class="dl-fig">
<svg viewBox="0 0 600 340" role="img" aria-label="Cinco niveles de perfil de lejos a cerca: valores por defecto, que se actualizan con el plugin; usuario, que cada persona escribe una vez; organización, compartido y mantenido en un solo sitio; proyecto, compartido e instalado solo por quien trabaja en él; repositorio, versionado en el repo y actualizado con él. Gana el nivel más cercano, salvo las invariantes.">
  <g font-family="ui-sans-serif,system-ui,sans-serif">
    <text x="40" y="22" fill="#94a3b8" font-size="12">nivel</text>
    <text x="330" y="22" fill="#94a3b8" font-size="12">lo escribe · se actualiza</text>
    <rect x="30" y="32" width="540" height="50" rx="8" fill="#22222e" stroke="rgba(255,255,255,0.1)"/>
    <text x="48" y="55" fill="#e2e8f0" font-size="15" font-weight="600">Por defecto</text>
    <text x="48" y="72" fill="#94a3b8" font-size="12">invariantes, autoridad, método</text>
    <text x="330" y="62" fill="#e2e8f0" font-size="13">el plugin · en cada versión</text>
    <rect x="30" y="92" width="540" height="50" rx="8" fill="#22222e" stroke="rgba(255,255,255,0.1)"/>
    <text x="48" y="115" fill="#e2e8f0" font-size="15" font-weight="600">Usuario</text>
    <text x="48" y="132" fill="#94a3b8" font-size="12">cuentas, máquina, herramientas, autonomía</text>
    <text x="330" y="122" fill="#e2e8f0" font-size="13">tú · una vez</text>
    <rect x="30" y="152" width="540" height="50" rx="8" fill="#2a2418" stroke="#f59e0b"/>
    <text x="48" y="175" fill="#fbbf24" font-size="15" font-weight="600">Organización</text>
    <text x="48" y="192" fill="#94a3b8" font-size="12">tracker, revisores, política de CI, quién promueve</text>
    <text x="330" y="182" fill="#e2e8f0" font-size="13">repo compartido · una PR, para todos</text>
    <rect x="30" y="212" width="540" height="50" rx="8" fill="#2a2418" stroke="#f59e0b"/>
    <text x="48" y="235" fill="#fbbf24" font-size="15" font-weight="600">Proyecto</text>
    <text x="48" y="252" fill="#94a3b8" font-size="12">entornos, releases, identidad de pruebas</text>
    <text x="330" y="242" fill="#e2e8f0" font-size="13">repo compartido · si trabajas en él</text>
    <rect x="30" y="272" width="540" height="50" rx="8" fill="#1f2a2c" stroke="#2dd4bf"/>
    <text x="48" y="295" fill="#5eead4" font-size="15" font-weight="600">Repositorio</text>
    <text x="48" y="312" fill="#94a3b8" font-size="12">ramas, comandos de test, despliegue, URLs</text>
    <text x="330" y="302" fill="#e2e8f0" font-size="13">el propio repo · en cada pull</text>
  </g>
</svg>
<figcaption>Los niveles se combinan de lejos a cerca y gana el más cercano, salvo las invariantes como «nunca se prueba contra producción», que ningún nivel inferior puede relajar. Los niveles en ámbar son los compartidos: los escribe una vez quien lo sabe, para todos.</figcaption>
</figure>

## Pensado para compartirse

Esto es lo que hace que merezca la pena montarlo. Una organización guarda sus perfiles en un repositorio privado: el nivel de organización y un perfil por proyecto. Una persona nueva instala el plugin, ejecuta un script y recibe el perfil de la organización más los de los proyectos cuyos repos tiene de verdad. Nada más.

Lo que le queda es poco, y casi todo se escribe una vez:

- **Su perfil de usuario.** Sus cuentas, los límites de su máquina, la herramienta de navegador que usa. Se escribe una vez, se queda para siempre y nunca forma parte de un fichero compartido: el CI del repo compartido comprueba que ningún perfil compartido tenga datos personales.
- **Cada repo nuevo.** La primera ejecución en un repo sin perfil detecta lo que puede (remote, protección de ramas, jobs de CI, runners de tests, configuración de despliegue) y pregunta solo lo que la detección no resuelve, una vez y con una respuesta recomendada. El resultado se versiona en el repo, así que el siguiente compañero que haga pull lo tiene sin ejecutar nada. En el repositorio de un cliente, ese mismo perfil se queda en local, dentro de `.git`, para que nunca llegue al cliente.

Nadie vuelve a aprender la organización. Cuando una regla cambia para todos, cambia en un sitio con una PR y todos la reciben en la siguiente instalación. Cuando un repo cambia su rama de integración, el perfil de ese repo cambia con él.

## El mismo plugin, dos organizaciones

Lo uso en dos organizaciones que trabajan de forma muy distinta. En una, la rama de integración es `develop`, un cambio llega al entorno de pruebas subiendo una versión en un repositorio de configuración aparte, y la promoción más allá es de otro equipo. En la otra, varios proyectos de cliente tienen cada uno sus entornos y su proceso de release, las revisiones incluyen agentes de revisión propios de la empresa, y los repositorios de cliente nunca deben recibir nuestros ficheros.

El núcleo es el mismo en las dos, sin cambios, en Claude Code y en Codex. Cada una de esas diferencias es una línea en un perfil, en su nivel. El repo público solo lleva perfiles de ejemplo ficticios; los reales viven en el repo privado de cada organización.

## Mantenerlas al día

Un perfil que era correcto al escribirlo se queda viejo solo, igual que [las memorias que guarda mi agente](/es/blog/the-memory-that-was-true): nunca fueron falsas al escribirse, describían un estado que caducó. Por eso el perfil se trata como algo que hay que volver a comprobar, no como algo de lo que fiarse:

- Al empezar cada tarea, una comprobación barata compara el perfil con lo que muestra el repo. Si algo no cuadra, se actualiza ese dato en su nivel y se deja una línea en el informe.
- Cualquier dato con más de 30 días se vuelve a verificar antes de que el bucle se apoye en él.
- Cuando el perfil y otra fuente no coinciden, gana la fuente fechada más reciente, y la vieja se corrige donde vive, así que el arreglo llega a todos los que comparten ese nivel.
- Los perfiles se vuelven a combinar a mitad de tarea, porque las reglas pueden cambiar mientras el trabajo está en curso.

## La regla estaba en la otra rama

Mantener las prácticas al día es solo la mitad. El agente además tiene que leer las vigentes, y ahí una ejecución real me sorprendió.

Un repositorio en el que trabajo había añadido una regla a su checklist de PR: una persona tiene que dar fe de que ha revisado cualquier código generado por IA antes de que salga. Una ejecución se paró antes del merge y me pidió esa revisión. Dos ejecuciones anteriores en el mismo repositorio habían mergeado sin ella. La regla estaba vigente y en el sitio correcto, la rama de integración. Pero las tres sesiones se habían lanzado desde un checkout en una rama más antigua, cuyos ficheros de instrucciones son anteriores a la regla. Después el trabajo se hacía en un worktree nuevo sobre la rama de integración. La ejecución que se paró releyó allí las instrucciones; las otras trabajaron con la copia con la que habían empezado.

<figure class="dl-fig">
<svg viewBox="0 0 600 200" role="img" aria-label="Las sesiones empiezan desde un checkout en una rama antigua cuyos ficheros de instrucciones no tienen la regla de revisión. El trabajo se hace en un worktree sobre la rama de integración, donde la regla existe. Una ejecución que relee las instrucciones del worktree se para antes del merge; una que se queda con la copia del arranque mergea sin la regla.">
  <g font-family="ui-sans-serif,system-ui,sans-serif">
    <rect x="30" y="24" width="250" height="62" rx="8" fill="#22222e" stroke="rgba(255,255,255,0.15)"/>
    <text x="155" y="48" fill="#e2e8f0" font-size="14" font-weight="600" text-anchor="middle">Checkout de arranque</text>
    <text x="155" y="68" fill="#94a3b8" font-size="12" text-anchor="middle">rama antigua · sin la regla</text>
    <rect x="320" y="24" width="250" height="62" rx="8" fill="#1f2a2c" stroke="#2dd4bf"/>
    <text x="445" y="48" fill="#5eead4" font-size="14" font-weight="600" text-anchor="middle">Worktree de la tarea</text>
    <text x="445" y="68" fill="#94a3b8" font-size="12" text-anchor="middle">rama de integración · con la regla</text>
    <path d="M282 55 L316 55" stroke="#64748b" stroke-width="2"/>
    <path d="M308 49 L318 55 L308 61 Z" fill="#64748b"/>
    <path d="M155 88 L155 124" stroke="#64748b" stroke-width="2" stroke-dasharray="5 4"/>
    <path d="M445 88 L445 124" stroke="#2dd4bf" stroke-width="2"/>
    <rect x="30" y="126" width="250" height="50" rx="8" fill="#2a2418" stroke="#f59e0b"/>
    <text x="155" y="148" fill="#fbbf24" font-size="13" text-anchor="middle">se queda con la copia inicial</text>
    <text x="155" y="166" fill="#94a3b8" font-size="12" text-anchor="middle">mergea sin la regla</text>
    <rect x="320" y="126" width="250" height="50" rx="8" fill="#1f2a2c" stroke="#2dd4bf"/>
    <text x="445" y="148" fill="#5eead4" font-size="13" text-anchor="middle">relee en el worktree</text>
    <text x="445" y="166" fill="#94a3b8" font-size="12" text-anchor="middle">se para y pide revisión humana</text>
  </g>
</svg>
<figcaption>La regla existía y estaba vigente. Que se aplicara dependía de qué copia de las prácticas estaba leyendo el agente.</figcaption>
</figure>

Así que ya no se deja al azar: cuando una sesión se lanzó desde una rama distinta de la de integración o la de producción, el plugin lee los ficheros de instrucciones del repositorio desde el espacio de trabajo donde se hace el trabajo y deja constancia de qué rama vienen.

## Menos preguntas por el camino

Unos perfiles compartidos y al día son también lo que permite que el bucle avance sin pararse a preguntar. Antes de empezar, prueba con una llamada real cada capacidad que va a usar la tarea, porque configurado no es autenticado y autenticado no es que funcione: una herramienta que aparece como conectada puede fallar en su primera llamada, y `gh auth status` puede decir una cuenta mientras los comandos corren con otra. Lo que falla se plantea en una sola ronda, y la respuesta se guarda en su nivel para que nadie vuelva a preguntar. Lo que queda para una persona son las decisiones que de verdad son suyas: una decisión de negocio, un texto que verá el cliente, la revisión de la que esa regla tiene que dar fe.

---

*[delivery-loop en GitHub](https://github.com/JaviMaligno/delivery-loop) (MIT). Se instala en Claude Code con `claude plugin marketplace add JaviMaligno/delivery-loop`, o en Codex con `codex plugin marketplace add JaviMaligno/delivery-loop`. Más de lo que empaqueto para agentes en [Plugins y Skills](/es/skills).*
