---
title: "El pipeline que nadie abría"
description: "Mi pipeline de automatización de fuentes de datos funcionaba, y los desarrolladores para los que lo construimos no querían usarlo. Ahora se convierte en un plugin del agente de código que ya abren cada mañana. Por qué es el cambio correcto."
pubDate: 2026-11-23
tags: ["Agentes IA", "Claude Code", "Herramientas de Desarrollo", "Producto"]
lang: es
translationKey: the-pipeline-nobody-opened
heroImage: "/blog/the-pipeline-nobody-opened.png"
---

En esta web hay un caso de estudio llamado [Data Source Automator](/es/projects/data-source-automator). Le das un registro público y una cadena de agentes investiga la fuente, escribe los requisitos, diseña el contrato de la API, genera el microservicio, lo despliega y lo verifica. Sigo suscribiendo esa página. El pipeline hacía lo que dice.

Y aun así, tras varias iteraciones y rondas de pruebas, el proyecto ha fracasado. No porque generara servicios malos, sino porque los desarrolladores para los que lo construimos no querían usarlo. Así que lo estamos convirtiendo en otra cosa: un plugin para el agente de código que esos mismos desarrolladores ya tienen abierto.

Creo que el motivo del fracaso es más interesante que todo el trabajo técnico, y es el mismo argumento que defendí hace unos meses en [Lleva tu aplicación al agente](/es/blog/bring-your-app-to-the-agent), esta vez aprendido por las malas.

## Funcionar no es lo mismo que usarse

Cuando hablé con los desarrolladores, la queja no era la calidad. Era la fricción. Usar el pipeline significaba salir de su flujo habitual, ir a otra aplicación, darle una fuente, esperar y luego revisar lo que salía. Comparado con cómo ya trabajan, ofrecía menos interactividad y menos información.

Esa comparación es toda la historia. Su flujo habitual no es «escribirlo todo a mano». Su flujo habitual es Claude Code o Codex en una terminal: piden algo, ven qué lee y qué cambia el agente, lo interrumpen cuando se desvía y lo corrigen en el siguiente mensaje. Frente a eso, una plataforma que se lleva la tarea y te devuelve un resultado se siente como un paso atrás, aunque el resultado sea bueno. Ves menos de lo que ha pasado y tienes menos momentos para reconducirlo.

Y además era circular. Cuando algo del resultado fallaba, el arreglo no se hacía en la plataforma: volvían a su editor y a su agente para corregirlo. Les obligábamos a salir de su forma de trabajar para usar el pipeline, y en cuanto algo fallaba, el propio pipeline los devolvía a ella. La plataforma añadía un viaje de ida y vuelta sin quitarles el sitio al que acababan volviendo igualmente.

## Otro framework para escribir código

Visto desde ahí, parte de lo que construimos tiene poco sentido. Los desarrolladores ya usan IA para escribir código. Construir un segundo framework cuyo trabajo también es escribir código es competir con la herramienta que han elegido, no ayudarles con ella. Lo mismo pasa con la fase de requisitos: la gente ya redacta y discute requisitos con Claude, Codex o ChatGPT. Una interfaz aparte para eso es un sitio más al que ir, no uno menos.

Lo valioso nunca fue el framework. Era el conocimiento de cómo se hace este trabajo concreto: cómo investigar un registro, qué tienen que contener los documentos de requisitos, cómo es el contrato con el frontend, qué comprobaciones tiene que pasar un servicio antes de que nadie se fíe de él. Ese conocimiento puede vivir en otro contenedor.

<style>
.pno-fig{background:#1a1a24;border:1px solid rgba(255,255,255,.1);border-radius:1rem;padding:1rem;margin:2rem 0}
.pno-fig svg{display:block;width:100%;height:auto;font-family:Inter,-apple-system,system-ui,sans-serif}
.pno-fig figcaption{color:#94a3b8;font-size:.85rem;line-height:1.55;margin:1rem .25rem .25rem;text-align:center}
</style>

<figure class="pno-fig">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 320" role="img" aria-label="Antes: el desarrollador trabaja en su propio agente de código y tiene que ir a una plataforma aparte, con su propia interfaz, sus agentes y facturación por API, para usar el pipeline. Después: el mismo pipeline corre como plugin dentro del agente del desarrollador, así que hay un único sitio de trabajo.">
  <defs>
    <marker id="pno-arrow-es" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0 0L10 5L0 10z" fill="#64748b"/>
    </marker>
  </defs>
  <g font-size="14" font-weight="600" text-anchor="middle">
    <text x="145" y="24" fill="#fbbf24">Antes</text>
    <text x="455" y="24" fill="#5eead4">Después</text>
  </g>
  <path d="M300 10V310" stroke="rgba(255,255,255,.1)"/>
  <g text-anchor="middle" font-size="12">
    <rect x="95" y="50" width="100" height="36" rx="8" fill="none" stroke="#94a3b8"/>
    <text x="145" y="73" fill="#e2e8f0">Desarrollador</text>
    <rect x="15" y="150" width="120" height="60" rx="8" fill="none" stroke="#2dd4bf"/>
    <text x="75" y="175" fill="#e2e8f0">Su agente</text>
    <text x="75" y="192" fill="#e2e8f0">de código</text>
    <rect x="160" y="150" width="125" height="96" rx="8" fill="none" stroke="#f59e0b"/>
    <text x="222" y="172" fill="#fbbf24" font-weight="600">Nuestra plataforma</text>
    <text x="222" y="194" fill="#94a3b8" font-size="11">su propia UI</text>
    <text x="222" y="212" fill="#94a3b8" font-size="11">sus propios agentes</text>
    <text x="222" y="230" fill="#94a3b8" font-size="11">facturación por API</text>
    <path d="M128 86L82 146" stroke="#64748b" stroke-width="1.5" fill="none" marker-end="url(#pno-arrow-es)"/>
    <path d="M162 86L212 146" stroke="#64748b" stroke-width="1.5" fill="none" marker-end="url(#pno-arrow-es)"/>
    <path d="M135 180H160" stroke="#64748b" stroke-dasharray="3 3"/>
    <text x="145" y="280" fill="#94a3b8" font-size="11">Dos sitios de trabajo.</text>
    <text x="145" y="296" fill="#94a3b8" font-size="11">El segundo pide más y enseña menos.</text>
    <rect x="405" y="50" width="100" height="36" rx="8" fill="none" stroke="#94a3b8"/>
    <text x="455" y="73" fill="#e2e8f0">Desarrollador</text>
    <path d="M455 86V136" stroke="#64748b" stroke-width="1.5" fill="none" marker-end="url(#pno-arrow-es)"/>
    <rect x="325" y="140" width="260" height="116" rx="10" fill="none" stroke="#2dd4bf"/>
    <text x="455" y="162" fill="#e2e8f0">Su agente de código</text>
    <rect x="340" y="174" width="230" height="68" rx="8" fill="rgba(45,212,191,.08)" stroke="#5eead4"/>
    <text x="455" y="194" fill="#5eead4" font-weight="600">plugin</text>
    <text x="455" y="213" fill="#e2e8f0" font-size="11">investigar · requisitos · contrato</text>
    <text x="455" y="230" fill="#e2e8f0" font-size="11">implementar · verificar · publicar</text>
    <text x="455" y="280" fill="#94a3b8" font-size="11">Un solo sitio, su propia suscripción,</text>
    <text x="455" y="296" fill="#94a3b8" font-size="11">correcciones en la misma conversación.</text>
  </g>
</svg>
<figcaption>Las fases no han cambiado. Lo que cambia es dónde corren: dentro de la herramienta que el desarrollador ya usa, no al lado.</figcaption>
</figure>

## Qué aporta el formato plugin

Convertir el pipeline en un [plugin de Claude Code](/es/skills) mantiene las fases y cambia todo lo que las rodea.

**Ninguna factura de API.** El desarrollador ya paga una suscripción de Claude o de Codex, y el plugin corre sobre ella. No hay claves que dar de alta, ni coste por ejecución que justificar, ni una partida aparte para «la automatización». La economía deja de ser un tema de conversación.

**El feedback entra directo.** En la plataforma, corregir algo significaba volver a salir de ella, a sus propias herramientas, para arreglar allí el resultado. Dentro del agente, una corrección es el siguiente mensaje. El desarrollador ve la investigación mientras ocurre, ve qué ficheros está escribiendo el agente y puede pararlo en cuanto algo no cuadra. Es justo la interactividad y la información que decían que faltaban.

**Ninguna interfaz extra.** La conversación es la interfaz. Nadie tiene que aprender dónde están las cosas, tener otra pestaña abierta ni acordarse de que la herramienta existe. La pantalla de revisión que habríamos tenido que diseñar, construir y mantener es la que ya conocen.

**El conocimiento se queda, la fontanería se va.** Las reglas del dominio, el orden de las fases y las comprobaciones que deciden si un servicio está listo siguen ahí, escritas como skills y scripts que el agente sigue. Lo que desaparece es lo que solo teníamos que construir porque ejecutábamos nuestros propios agentes: orquestación, gestión de sesiones, una UI, un backend que lo sostuviera todo. Esa fontanería ya la pone el agente de código.

## El caso de estudio sigue en pie

No lo leo como «el pipeline fue un error». Demostró que el trabajo se podía automatizar de punta a punta, y el plugin hereda todo lo que aprendió. El caso de estudio describe una capacidad, y la capacidad sigue ahí. Lo que falló fue la entrega: lo pusimos en un sitio al que los desarrolladores tenían que ir, cuando ya tenían un sitio en el que estaban.

Por eso el plugin aparece ahora en mi [página de Plugins y Skills](/es/skills) junto a los demás, con las mismas fases que el pipeline original.

## La pregunta que haría antes la próxima vez

En [Lleva tu aplicación al agente](/es/blog/bring-your-app-to-the-agent) escribí que el usuario ya tiene una IA y no quiere otra app. Pensaba en productos de consumo. Resulta que aplica todavía más dentro de una empresa, a los desarrolladores, que son quienes más probablemente viven ya dentro de un agente. Y, como conté en [La interfaz subió de nivel](/es/blog/the-interface-moved-up), ese sitio donde viven no deja de mejorar a la hora de enseñarles lo que importa.

Nada de esto significa que toda herramienta de IA deba ser un plugin. Si quienes la van a usar no trabajan ya dentro de un agente, o el trabajo tiene que correr sin nadie mirando, una plataforma propia puede seguir siendo la decisión correcta. Pero antes de construir una herramienta de IA para gente que ya usa IA a diario, ahora haría primero una pregunta: **¿esto compite con el agente que ya tienen o se enchufa a él?**

Nosotros nos la hicimos tarde. El plugin es la respuesta con la que deberíamos haber empezado.

---

*El plugin es interno, así que el repositorio es privado; sus fases y skills están descritas en la [página de Plugins y Skills](/es/skills). El pipeline original está documentado en el [caso de estudio de Data Source Automator](/es/projects/data-source-automator).*
