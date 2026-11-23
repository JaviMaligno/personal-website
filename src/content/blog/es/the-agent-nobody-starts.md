---
title: "Automatizar de verdad: el agente que nadie arranca"
description: "Automatizar de verdad con agentes empieza cuando nadie tiene que abrir una sesión: un agente se ejecuta en remoto en cuanto ocurre algo. Lo difícil es elegir qué puede hacer sin ti, dispararlo justo cuando hace falta y darle los accesos que tú tienes sin el riesgo."
pubDate: 2026-12-20
tags: ["Agentes de IA", "Automatización", "Claude Code", "Orquestación de agentes"]
lang: es
translationKey: the-agent-nobody-starts
heroImage: "/blog/the-agent-nobody-starts.png"
---

<style>
.anb-fig{background:#1a1a24;border:1px solid rgba(255,255,255,.1);border-radius:1rem;padding:1rem;margin:2rem 0}
.anb-fig svg{display:block;width:100%;height:auto;font-family:Inter,-apple-system,system-ui,sans-serif}
.anb-fig figcaption{color:#94a3b8;font-size:.85rem;line-height:1.55;margin:1rem .25rem .25rem;text-align:center}
</style>

Antes de irse unas semanas, una amiga dejó su casa al cuidado de una vecina. No le dio una lista de tareas, le dio tres cosas. Un juego de llaves: la puerta y el cuarto de la caldera, no el cajón de los papeles. Una nota en la nevera: si salta la alarma de la caldera, se rearma así; si llega algo del banco, apártalo; si hay una gotera, llámame. Y un mensaje cada noche, de dos líneas: todo tranquilo, o esto es lo que ha pasado.

La vecina no tuvo que preguntarle nada. Ella no tuvo que mirar el móvil por la casa. Lo difícil se había hecho antes de irse: elegir qué llaves dar, escribir qué alarma merecía una llamada y cuál no, y acordar qué diría el mensaje de la noche.

Así es automatizar con agentes de verdad, y casi todo lo que hoy llamamos automatización aún no ha llegado ahí.

## La automatización que todavía te necesita

**Si tienes que estar delante de tu dispositivo para que el agente arranque, el que automatiza el trabajo no es el agente: eres tú.** Llega una notificación, o un email, o un fallo de CI. Lo ves, abres el portátil, inicias una sesión, explicas el contexto, esperas, compruebas. El agente ha tecleado, pero el ciclo ha pasado por tu atención, y lo que cuesta ese ciclo no son los minutos de la sesión. Es la interrupción: el foco que pierdes en lo que estabas haciendo, y ese estado de fondo de estar de guardia para tus propios procesos. Hacerlo desde el móvil no lo arregla; solo hace que te lleves tu atención contigo a otra parte.

En [La interfaz subió de nivel](/es/blog/the-interface-moved-up) describí el último paso de esa evolución como aquel en el que el humano ya no arranca el trabajo. Este artículo va de lo que hace falta para vivir de verdad ahí. En las últimas semanas he ido pasando cada vez más trabajo a agentes que nadie lanza: en el trabajo, rutinas que despliegan y verifican cambios, rutinas que revisan logs y alertas de producción y pipelines agénticas en Bitbucket; en mis proyectos, rutinas en varios repositorios, una diaria para mis propias métricas, un agente en el CI de un bot de trading en Polymarket y rutinas que curan mis playlists. Las herramientas cambian. Las dificultades son las mismas tres cada vez.

## Lo que existe hoy

**Hay dos familias de herramientas, y solo una te saca del ciclo.** La primera se ejecuta dentro de una sesión que has abierto tú; la segunda abre la sesión por ti.

| Herramienta | Se dispara con | Se ejecuta en | ¿Necesita que abras una sesión? |
|---|---|---|---|
| [Hooks de Claude Code](https://code.claude.com/docs/es/hooks) | Eventos dentro de una sesión: antes de una herramienta, al parar, al arrancar | Tu máquina, dentro de tu sesión | Sí |
| [Rutinas de Claude](https://code.claude.com/docs/es/routines) | Un horario, una llamada a la API, un evento de GitHub | La nube de Anthropic | No |
| [Automatizaciones de Codex](https://openai.com/es-ES/academy/codex-automations/) | Un horario, hilos recurrentes | La app de Codex; en local necesita el portátil despierto | No, si la máquina está encendida |
| [Dots de ChatGPT](https://openai.com/index/devday-2026-recap/) | Agentes persistentes que siguen trabajando entre conversaciones | Su propio ordenador en la nube, con apps conectadas | No |
| A medida: cron, launchd, un job de CI que llama a `claude -p` o `codex exec` | Lo que puedas programar | Tu servidor, tu portátil, tus runners de CI | No |

Los hooks valen mucho y los uso bastante, pero hacen una sesión más fiable; no la eliminan. Son la capa determinista: pasar el formateador tras cada edición, bloquear un comando, inyectar contexto al arrancar. La segunda familia es la de este artículo. Las rutinas son la versión más directa en el mundo de Claude: un prompt guardado, un repositorio, unos conectores y un disparador. Las automatizaciones de Codex llevan la misma idea al lado de OpenAI, con la salvedad que da su propia guía para las ejecuciones locales: el portátil tiene que estar despierto. Los dots, que OpenAI anunció a finales de septiembre, van un paso más allá: un agente que persiste, con su propio ordenador y sus propias apps, y una revisión automática de cualquier acción que pueda tocar tus cuentas. Y cuando nada de eso encaja, un programador de tareas y una llamada a un agente sin interfaz hacen el trabajo; mi rutina diaria de métricas es un job de `launchd` en mi Mac que abre una sesión en segundo plano porque el modo sin interfaz no tiene una herramienta que necesita.

La lista estará desfasada en tres meses. Lo que hace falta para que cualquiera de ellas funcione, no.

<figure class="anb-fig">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 400" role="img" aria-label="Una ejecución desatendida en cuatro etapas. Un evento (un horario, una issue, un merge, un email) activa el disparador. El primer paso es una guarda que comprueba las precondiciones y para si no se cumplen. Después el agente trabaja dentro de un entorno preparado de conectores, acceso al repositorio y credenciales con el mínimo privilegio. Cada ejecución acaba en una de tres salidas: un resumen si ha ido bien, un escalado al humano si hace falta criterio y una alerta si ha fallado.">
  <defs><marker id="anb-arrow-es" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10Z" fill="#94a3b8"/></marker></defs>
  <rect x="20" y="30" width="160" height="70" rx="10" fill="#203237" stroke="#2dd4bf"/>
  <text x="100" y="58" text-anchor="middle" fill="#5eead4" font-size="15" font-weight="600">Evento</text>
  <text x="100" y="80" text-anchor="middle" fill="#e2e8f0" font-size="12">horario · issue · merge · email</text>
  <path d="M184 65H216" stroke="#94a3b8" stroke-width="2" marker-end="url(#anb-arrow-es)"/>
  <rect x="220" y="30" width="160" height="70" rx="10" fill="#362e23" stroke="#f59e0b"/>
  <text x="300" y="58" text-anchor="middle" fill="#fbbf24" font-size="15" font-weight="600">Guarda</text>
  <text x="300" y="80" text-anchor="middle" fill="#e2e8f0" font-size="12">¿esto sigue aplicando?</text>
  <path d="M384 65H416" stroke="#94a3b8" stroke-width="2" marker-end="url(#anb-arrow-es)"/>
  <rect x="420" y="30" width="160" height="70" rx="10" fill="#283240" stroke="#94a3b8"/>
  <text x="500" y="58" text-anchor="middle" fill="#f8fafc" font-size="15" font-weight="600">Agente</text>
  <text x="500" y="80" text-anchor="middle" fill="#e2e8f0" font-size="12">hace el trabajo y lo comprueba</text>
  <path d="M300 104V126" stroke="#94a3b8" stroke-width="2" stroke-dasharray="4 4" marker-end="url(#anb-arrow-es)"/>
  <text x="310" y="120" fill="#94a3b8" font-size="12">para y dice por qué</text>
  <rect x="20" y="140" width="560" height="78" rx="10" fill="#1f2937" stroke="#475569"/>
  <text x="300" y="166" text-anchor="middle" fill="#cbd5e1" font-size="14" font-weight="600">Entorno preparado</text>
  <text x="300" y="190" text-anchor="middle" fill="#e2e8f0" font-size="12">conectores · acceso al repositorio · las herramientas del trabajo</text>
  <text x="300" y="208" text-anchor="middle" fill="#e2e8f0" font-size="12">mínimo privilegio · intermediarios de solo lectura para lo que no debe tocar</text>
  <path d="M500 104V136" stroke="#94a3b8" stroke-width="2" marker-end="url(#anb-arrow-es)"/>
  <path d="M110 222V262" stroke="#94a3b8" stroke-width="2" marker-end="url(#anb-arrow-es)"/>
  <path d="M300 222V262" stroke="#94a3b8" stroke-width="2" marker-end="url(#anb-arrow-es)"/>
  <path d="M490 222V262" stroke="#94a3b8" stroke-width="2" marker-end="url(#anb-arrow-es)"/>
  <rect x="20" y="268" width="180" height="96" rx="10" fill="#1c3326" stroke="#4ade80"/>
  <text x="110" y="296" text-anchor="middle" fill="#86efac" font-size="15" font-weight="600">Resumen</text>
  <text x="110" y="320" text-anchor="middle" fill="#e2e8f0" font-size="12">qué hizo, con pruebas</text>
  <text x="110" y="340" text-anchor="middle" fill="#94a3b8" font-size="12">se lee cuando te viene bien</text>
  <rect x="210" y="268" width="180" height="96" rx="10" fill="#362e23" stroke="#f59e0b"/>
  <text x="300" y="296" text-anchor="middle" fill="#fbbf24" font-size="15" font-weight="600">Escalado</text>
  <text x="300" y="320" text-anchor="middle" fill="#e2e8f0" font-size="12">hace falta una decisión</text>
  <text x="300" y="340" text-anchor="middle" fill="#94a3b8" font-size="12">solo lo que es tuyo</text>
  <rect x="400" y="268" width="180" height="96" rx="10" fill="#3a2226" stroke="#f87171"/>
  <text x="490" y="296" text-anchor="middle" fill="#fca5a5" font-size="15" font-weight="600">Alerta</text>
  <text x="490" y="320" text-anchor="middle" fill="#e2e8f0" font-size="12">falló o no se oyó</text>
  <text x="490" y="340" text-anchor="middle" fill="#94a3b8" font-size="12">alta, y con la causa</text>
</svg>
<figcaption>Las tres cosas de la vecina, como proceso: la nota decide cuándo actuar y cuándo parar, las llaves son el entorno y el mensaje de la noche es una de tres salidas.</figcaption>
</figure>

## Un lunes por la mañana

**Dos rutinas se dispararon con una hora de diferencia, y las dos hicieron lo correcto sin mí.** La primera, a las ocho, tenía un trabajo que si no habría hecho yo en mi mesa: mergear la pull request que subía nuestro gateway de LLM a una versión sin las vulnerabilidades que había encontrado un escaneo de seguridad, esperar al despliegue, verificarlo y cerrar el ticket. El agente en la nube no llega al clúster, al que solo se accede por la VPN de la empresa, así que la verificación pasó por otro agente: el [agente de DevOps de solo lectura que construí para Slack](/es/blog/building-a-production-devops-agent), que ejecuta `kubectl` dentro de los clústeres. La rutina publicó cinco comandos exactos, fue leyendo el hilo y comprobó cinco condiciones sobre las respuestas: la imagen nueva en todas las réplicas, pods en marcha sin reinicios, migraciones de la base de datos aplicadas, sin errores de arranque, peticiones reales respondidas con un 200. Como no encontró tráfico en los últimos diez minutos, le pidió al bot una vez más los últimos treinta, tal y como decían sus instrucciones. Después comentó los valores en el ticket, lo pasó por las dos transiciones hasta cerrado, se dio cuenta de que al cerrarlo se había borrado el asignado y lo volvió a poner, y me mandó un mensaje con lo hecho y lo que quedaba a mano. Quince minutos de principio a fin. A la mañana siguiente empezaba sobre ese gateway un lote grande de un cliente, así que las instrucciones también decían cómo tenía que ser un mensaje urgente, y con qué vuelta atrás.

La segunda rutina, a las nueve, tenía que activar una regla en un entorno de pruebas y cerrar otro ticket. Tardó 27 segundos. Leyó el ticket, lo encontró ya cerrado (alguien lo había cerrado días antes) y se paró ahí, como decía su primer paso, con un mensaje contándome lo que había encontrado y lo que tendría que hacer si seguía queriendo el cambio. Lo quería, así que lo mergeé desde una sesión. Esa segunda ejecución es la que más me gusta. Entre el día en que escribí la rutina y el día en que se disparó, el mundo había cambiado, y la rutina se dio cuenta.

## El primer reto: qué puedes delegar

**La pregunta no es si el agente puede hacer la tarea. Es si aceptarías el resultado solo con su resumen.** Eso cambia la elección. La primera rutina podía mergear en un entorno que sirve tráfico de producción porque el merge era reversible (la vuelta atrás estaba escrita en sus instrucciones), la verificación era concreta y ajena al agente, y el resultado volvía como valores que yo podía comprobar en un minuto. Una tarea cuyo resultado querría rehacer yo después de leer el resumen no está lista para una rutina; está lista para una sesión.

Hay unos cuantos criterios que me han aguantado:

- **Reversible, o comprobado antes de ser irreversible.** Mergear un cambio de configuración que se puede revertir, sí. Mandarle un email a un cliente, todavía no.
- **El «hecho» lo define algo de fuera del agente.** Una comprobación de un bot dentro del clúster, un build que pasa, un test que corre. «Creo que funciona» no es una condición de cierre.
- **Las precondiciones, escritas como primer paso.** Todas mis rutinas empiezan comprobando que el mundo sigue como estaba cuando las escribí, y paran si no.
- **Lo determinista, primero.** Cuando la cola de publicación de este blog empezó a fallar su ensayo diario, miré los 21 fallos que tenía detrás. La mayoría tenían una causa mecánica, y esos fueron al CI como tests y arreglos. Solo lo que necesita criterio (dos artículos que editan el mismo fichero de formas distintas, por ejemplo) va a la rutina que ahora se dispara cuando falla el ensayo. El agente es para lo que un script no puede decidir.

## El segundo reto: dispararse justo cuando hace falta

**Un disparador demasiado amplio despierta al agente para nada; uno demasiado estrecho deja pasar el momento.** La primera versión de esa rutina de publicación escuchaba las issues nuevas y los comentarios nuevos del repositorio, porque el informe del fallo vive en una issue y quería que reaccionara también a lo que se añadiera después. En GitHub, los comentarios en pull requests cuentan como comentarios de issue, así que la rutina se despertaba unas cinco veces al día para no encontrar nada que hacer. La reduje a issues abiertas y cambié el ensayo para que cada fallo abra una issue nueva. Ahora se dispara una vez por fallo.

Aun así, el disparador no es toda la decisión. El primer paso de la rutina es una guarda: ¿hay una issue de fallo abierta, y su última entrada es del ensayo y no de la propia rutina? Sin eso, el informe de la rutina sería un evento nuevo y se contestaría a sí misma. **El disparador acota el momento; la guarda decide.** Esa separación es la que reutilizaría en cualquier sitio donde el evento sea ruidoso.

Los horarios y los eventos de código son los casos fáciles, porque el evento y la intención coinciden. Una PR mergeada significa que ha habido un merge. Los difíciles son los humanos. Un email de un cliente puede ser una petición de cambio, una pregunta que necesita respuesta, una aprobación, un agradecimiento, o las cuatro cosas en un mismo párrafo. ¿Cuáles deberían despertar a un agente que actúa, cuáles producir un borrador para mí y cuáles son solo información? Un agente puede clasificarlo, pero clasificarlo con la precisión que hace falta para actuar sin nadie delante es otra cosa: un «¿podrías mirar…?» mal leído se convierte en una acción que nadie ha pedido. Donde estoy hoy con esto es en la misma separación, un nivel más arriba. Un disparador amplio y un primer paso que solo clasifica y reparte: actuar en lo que es inequívoco y reversible, redactar lo que es comunicación y dejar el resto en una lista que leo cuando yo elijo, no cuando llega.

## El tercer reto: un entorno que pueda lo que puede tu portátil

**Un agente desatendido solo puede hacer lo que su entorno le deja, y en tu portátil eso es mucho más de lo que recuerdas.** En mi máquina, una sesión hereda años de configuración: CLIs con sesión iniciada, claves SSH, la VPN, tokens en un llavero, un navegador con mis sesiones. En la nube, la rutina empieza sin nada de eso. Cada capacidad hay que darla de forma explícita: los conectores del gestor de tickets y del chat, el acceso al repositorio (en GitHub, a través de la app instalada en ese repositorio concreto, y en la cuenta correcta: mi primer intento se ejecutó bajo una organización del trabajo que no tenía acceso a mi GitHub personal) y las herramientas que necesita el trabajo, declaradas en el repositorio y no en el prompt, que es el argumento de [Prepara el entorno, no al agente](/es/blog/bootstrap-the-environment-not-the-agent).

Ese carácter explícito es también el modelo de seguridad, y el motivo para no replicar tu portátil entero. La rutina del gateway podía mergear una pull request en un repositorio, y nada en sus instrucciones le permitía tocar ningún otro ticket, rama o entorno. Nunca tuvo credenciales del clúster: se lo preguntaba a un bot que solo puede leer. Tenía prohibido mostrar o pedir un secreto. El mínimo privilegio deja de ser un eslogan cuando tienes que escribir cada permiso, porque cada uno que das es uno que tendrás que defender el día que una rutina haga algo que no esperabas. El fallo contrario es igual de real: un entorno tan cerrado que el agente se para a medias y te devuelve el trabajo, que es justo la sesión que querías evitar.

## Lo que te llega de vuelta

**Cuando funciona, lo que lees es un resumen, no una sesión.** Todas mis rutinas acaban contándome lo que han hecho, con las pruebas: los valores que comprobaron, los enlaces, lo que queda a mano. Cuando va bien, lo leo cuando me viene bien. Cuando hace falta una decisión, lo dice y para. Cuando falla, el mensaje empieza por URGENTE y dice qué hacer.

Hay un fallo que un resumen no puede contar: la ejecución que nunca ocurre. Una rutina que no se dispara produce silencio, y el silencio se parece muchísimo a «todo tranquilo». Para eso mantengo un segundo canal que no depende del agente: los workflows de CI me avisan por Telegram cuando fallan, y mantendré ese aviso en el ensayo de publicación hasta ver un fallo real pasar por la rutina y salir arreglado.

La confianza, además, se construye a base de ejecuciones, no de diseño. Aquel lunes, lo primero que hice fue preguntarle a una sesión si había salido todo, cuando la respuesta ya estaba en mis mensajes. Es el mismo patrón que el de [verificar el resultado en lugar de releer el camino](/es/blog/results-oriented-programming): empiezas comprobándolo todo, y paras cuando las pruebas han acertado suficientes veces.

## Decidir qué timbres te despiertan

La nota de la vecina era corta, y esa era la gracia. No intentaba describir todas las situaciones. Decía qué llaves, qué alarmas y qué contar, y el resto lo dejaba en sus manos.

Ese es el trabajo de automatizar de verdad. No un prompt mejor ni un agente más listo, sino tres decisiones tomadas de antemano: qué puede hacer sin tu atención, qué exactamente lo despierta y qué se le permite tocar. Cuando aciertan, lo que ganas no son los minutos que ahorra el agente. Son todos los momentos en los que no tuviste que estar, y la atención que guardaste para lo que solo puedes decidir tú, que es [el único recurso que no se paraleliza](/es/blog/build-vs-buy-attention).

---

*Herramientas mencionadas: [Hooks de Claude Code](https://code.claude.com/docs/es/hooks) · [Rutinas de Claude Code](https://code.claude.com/docs/es/routines) · [Automatizaciones de Codex](https://openai.com/es-ES/academy/codex-automations/) · [Resumen del DevDay 2026 de OpenAI (dots)](https://openai.com/index/devday-2026-recap/).*
