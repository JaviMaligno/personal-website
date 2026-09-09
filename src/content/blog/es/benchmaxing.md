---
title: "Benchmaxing: ganar el examen no es hacer mejor el trabajo"
description: "Qué está documentado sobre benchmaxing y qué reveló un pequeño piloto con Opus 5 y Fable 5: fallos compartidos, empates y una intuición que las pruebas no confirmaron."
pubDate: 2026-09-16
tags: ["IA", "Evaluación", "Claude", "Benchmarks"]
lang: es
translationKey: benchmaxing
heroImage: "/blog/benchmaxing.png"
repoUrl: https://github.com/JaviMaligno/benchmaxing-probes
linkedinLinks:
  - label: "The Leaderboard Illusion"
    url: "https://arxiv.org/abs/2504.20879"
---

<style>
.bmx-fig{background:#1a1a24;border:1px solid rgba(255,255,255,.1);border-radius:1rem;padding:1.25rem;margin:2rem 0}
.bmx-fig svg{display:block;width:100%;height:auto;font-family:Inter,system-ui,sans-serif}
.bmx-fig figcaption{color:#94a3b8;font-size:.88rem;line-height:1.55;margin:.9rem 0 0;text-align:center}
</style>

Con Opus 5 me ha pasado algo que también he escuchado a personas con las que hablo directamente: las mejoras en los benchmarks no se corresponden necesariamente con la sensación de estar usando un modelo más inteligente o que trabaje mejor. Algunas tablas lo colocan incluso por encima de Fable, y eso choca con mi experiencia.

Esa percepción merece investigarse. También merece una prueba que pueda contradecirla. Si el artículo empieza dando por demostrado que Anthropic ha optimizado el examen a costa del trabajo real, ya he elegido la respuesta antes de mirar los datos.

Así que hice dos cosas: revisar qué está documentado sobre **benchmaxing** y preparar unas pruebas pequeñas con Opus 5 y Fable 5. El resultado fue menos cómodo que una denuncia: encontré fallos interesantes, pero no la superioridad general de Fable que mi intuición habría sugerido.

## Qué significa optimizar para el examen

Uso *benchmaxing* para referirme a orientar la optimización de un modelo, o la selección de sus resultados, hacia maximizar puntuaciones en evaluaciones. El problema aparece cuando mejorar esa puntuación deja de ser una buena señal de mejorar aquello que necesito. Es una aplicación de los problemas de [Goodhart estudiados por Manheim y Garrabrant](https://arxiv.org/abs/1803.04585): una medida útil puede perder valor como guía bajo una optimización intensa.

Prepararse para un examen puede enseñar la materia. También puede enseñar a reconocer preguntas, dominar un formato o agradar al corrector. La pregunta es cuánto se transfiere a problemas nuevos. Entrenar capacidades que se evalúan en benchmarks puede producir avances reales; una mejora de puntuación no demuestra, por sí sola, ni fraude ni falta de inteligencia.

Hay al menos tres fenómenos que conviene distinguir.

**Familiaridad con la prueba.** [GSM1k](https://arxiv.org/abs/2405.00332) introdujo problemas nuevos comparables a GSM8k y encontró caídas de precisión y señales de sobreajuste en varias familias de modelos. Pero también encontró poca evidencia de sobreajuste en muchos modelos de frontera y generalización en todos los evaluados. El resultado no permite decir que los modelos solo memorizan. Sí permite preguntar cuánto de la nota depende de haber visto algo demasiado parecido.

**Selección favorable de resultados.** Al presentar [Llama 4](https://ai.meta.com/blog/llama-4-multimodal-intelligence/), Meta destacó un Elo de 1417 en LMArena y aclaró que correspondía a una versión experimental de chat. Ese calificativo importa: la cifra de una variante no se traslada automáticamente a otra. [The Leaderboard Illusion](https://arxiv.org/abs/2504.20879) documentó prácticas de pruebas privadas y publicación selectiva; identificó 27 variantes privadas de Meta antes de Llama 4. Un ranking puede distorsionarse cuando solo se ve el resultado elegido, pero no todos los intentos.

**Distancia entre la métrica y el trabajo.** En un [estudio aleatorizado de METR](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/), 16 desarrolladores experimentados completaron 246 tareas: permitir herramientas de IA de principios de 2025 aumentó el tiempo un 19 %, aunque los participantes creían haber ahorrado tiempo. No demuestra benchmaxing, ni describe toda la programación con IA. Demuestra que la productividad necesita medirse directamente. Además, la [actualización de febrero de 2026](https://metr.org/blog/2026-02-24-uplift-update/) detectó sesgos de selección en el estudio posterior y consideró poco fiable su señal. Repetir el 19 % como descripción de los modelos actuales sería una mala lectura de esa evidencia.

## Qué puedo decir de Opus 5

[Anthropic presenta Opus 5](https://www.anthropic.com/news/claude-opus-5) como cercano a Fable 5 y superior en ciertas evaluaciones, como OSWorld 2.0. Su nota de Frontier-Bench especifica una ejecución interna, un entorno concreto, recompensa media sobre cinco intentos por tarea y Opus 4.8 como sustituto ante bloqueos de seguridad. Una puntuación describe esas condiciones; no describe automáticamente cualquier conversación cotidiana.

También hay [testimonios públicos](https://www.reddit.com/r/Anthropic/comments/1v5q1ju/opus_5_first_impressions_vs_fable/) parecidos a mi percepción: un usuario relata diagnósticos equivocados y confusión entre comentarios del código y comportamiento efectivo, y prefiere Fable para investigar. En el mismo hilo hay opiniones favorables a Opus. Mi experiencia, las conversaciones directas y ese hilo son fuentes de hipótesis, no una encuesta representativa.

Que Opus gane ciertas pruebas y Fable resulte más útil en otros trabajos puede ser perfectamente coherente. Resolver un encargo delimitado y descubrir correctamente qué hay que resolver son exigencias distintas. Lo que quería examinar era si esa diferencia aparecía en casos concretos.

## Un piloto que podía salir en contra

Comparé `claude-opus-5` y `claude-fable-5` mediante Claude Code con una suscripción Max, esfuerzo `high` y el mismo límite de 8192 tokens de salida. Los expedientes eran sintéticos, se entregaban completos en el prompt y los modelos no tenían herramientas.

El conjunto reúne **cinco expedientes por modelo**: un caso inicial de doble cobro, dos variantes con efectos externos y workers pausados, una secuencia escrita de cambios de permisos y un análisis numérico con mezclas de tareas distintas. Hubo una ejecución válida por modelo y expediente. Las dos variantes de workers exploran el mismo mecanismo; no son réplicas independientes de toda la experiencia de uso.

Los criterios de la ampliación quedaron guardados antes de ejecutarla. Esos casos se redactaron después de ver el primero, por lo que todo el ejercicio es exploratorio. [Los prompts, respuestas, criterios y comprobación del contraejemplo están disponibles para revisar](https://github.com/JaviMaligno/benchmaxing-probes).

<figure class="bmx-fig">
<svg viewBox="0 0 600 290" role="img" aria-label="Ambos modelos cubren permisos y cálculos; ambos dejan problemas en los diseños frente a fallos.">
<text x="349" y="28" text-anchor="middle" fill="#e2e8f0" font-size="18">Opus 5</text><text x="508" y="28" text-anchor="middle" fill="#e2e8f0" font-size="18">Fable 5</text>
<text x="8" y="84" fill="#e2e8f0" font-size="16">Doble cobro (D1)</text>
<rect x="277" y="60" width="144" height="37" rx="7" fill="none" stroke="#fbbf24" stroke-opacity=".5"/><text x="349" y="84" fill="#fbbf24" font-size="15" text-anchor="middle">Incompleto</text>
<rect x="437" y="60" width="144" height="37" rx="7" fill="none" stroke="#fbbf24" stroke-opacity=".5"/><text x="509" y="84" fill="#fbbf24" font-size="15" text-anchor="middle">Incompleto</text>
<text x="8" y="137" fill="#e2e8f0" font-size="16">Workers pausados (D2/D2b)</text>
<rect x="277" y="113" width="144" height="37" rx="7" fill="none" stroke="#fbbf24" stroke-opacity=".5"/><text x="349" y="137" fill="#fbbf24" font-size="15" text-anchor="middle">Falla la garantía</text>
<rect x="437" y="113" width="144" height="37" rx="7" fill="none" stroke="#fbbf24" stroke-opacity=".5"/><text x="509" y="137" fill="#fbbf24" font-size="15" text-anchor="middle">Falla la garantía</text>
<text x="8" y="190" fill="#e2e8f0" font-size="16">Permisos (D3)</text>
<rect x="277" y="166" width="144" height="37" rx="7" fill="none" stroke="#5eead4" stroke-opacity=".5"/><text x="349" y="190" fill="#5eead4" font-size="15" text-anchor="middle">Cubierto</text>
<rect x="437" y="166" width="144" height="37" rx="7" fill="none" stroke="#5eead4" stroke-opacity=".5"/><text x="509" y="190" fill="#5eead4" font-size="15" text-anchor="middle">Cubierto</text>
<text x="8" y="243" fill="#e2e8f0" font-size="16">Mezcla y coste (D4)</text>
<rect x="277" y="219" width="144" height="37" rx="7" fill="none" stroke="#5eead4" stroke-opacity=".5"/><text x="349" y="243" fill="#5eead4" font-size="15" text-anchor="middle">Cubierto</text>
<rect x="437" y="219" width="144" height="37" rx="7" fill="none" stroke="#5eead4" stroke-opacity=".5"/><text x="509" y="243" fill="#5eead4" font-size="15" text-anchor="middle">Cubierto</text>
</svg>
<figcaption>Lectura cualitativa de los criterios centrales. Una ejecución por modelo y expediente; D2b es una variante, no una repetición idéntica. «Cubierto» no significa perfección ni rendimiento general.</figcaption>
</figure>

El caso inicial ya dio una razón para frenar la intuición. Opus propuso registrar una intención durable antes de efectuar el cobro, aunque dejó incompleto el tratamiento de los estados inciertos. Fable mantuvo un hueco entre el efecto externo y el registro, y trató el doble cobro tras caducar la deduplicación como un riesgo que había que aceptar. Evitar un segundo intento, aun dejando el trabajo pendiente, era una opción que esa respuesta no desarrolló.

## El fallo que compartieron

En los dos casos siguientes hice explícita la prioridad: **no producir dos veces el efecto externo, aunque una operación incierta quede bloqueada**. El proveedor recuerda una clave durante unas horas; los workers pueden caer o quedarse pausados indefinidamente. El proveedor no acepta un mecanismo para invalidar la autoridad de un worker antiguo.

Ambos modelos reconocieron buena parte del problema. Propusieron claves estables, estados persistentes y dejar de reenviar después de un plazo. Pero ambos conservaron reintentos autorizados mientras el worker antiguo podía seguir vivo, confiando en una comprobación local del plazo y en un margen temporal.

La carrera que rompe esa propuesta cabe en cuatro pasos.

<figure class="bmx-fig">
<svg viewBox="0 0 600 220" role="img" aria-label="Un worker pausado puede duplicar el efecto externo después de caducar la deduplicación.">
<line x1="65" y1="112" x2="544" y2="112" stroke="#64748b" stroke-width="3"/><path d="M544 106 L556 112 L544 118" fill="#64748b"/>
<circle cx="70" cy="112" r="7" fill="#e2e8f0"/><text x="70" y="47" fill="#e2e8f0" text-anchor="middle" font-size="16">A comprueba</text><text x="70" y="69" fill="#e2e8f0" text-anchor="middle" font-size="16">y se pausa</text>
<circle cx="222" cy="112" r="7" fill="#5eead4"/><text x="222" y="47" fill="#5eead4" text-anchor="middle" font-size="16">B envía</text><text x="222" y="69" fill="#5eead4" text-anchor="middle" font-size="16">y termina</text>
<circle cx="374" cy="112" r="7" fill="#e2e8f0"/><text x="374" y="47" fill="#e2e8f0" text-anchor="middle" font-size="16">Caduca</text><text x="374" y="69" fill="#e2e8f0" text-anchor="middle" font-size="16">la clave</text>
<circle cx="526" cy="112" r="7" fill="#fbbf24"/><text x="526" y="47" fill="#fbbf24" text-anchor="middle" font-size="16">A despierta</text><text x="526" y="69" fill="#fbbf24" text-anchor="middle" font-size="16">y envía</text>
<text x="222" y="153" fill="#5eead4" font-size="16" text-anchor="middle">Efecto 1</text><text x="526" y="153" fill="#fbbf24" font-size="16" text-anchor="middle">Efecto 2</text>
</svg>
<figcaption>Una comprobación local no impide que A se pause justo después. Si B ya produjo el efecto y la clave ha caducado, el envío tardío de A produce un segundo efecto. Rechazar su escritura en la base de datos llega tarde.</figcaption>
</figure>

A comprueba que todavía puede enviar y se pausa justo después. B toma el relevo, envía y termina. Caduca el recuerdo de la clave en el proveedor. A despierta y envía lo que ya había decidido enviar. El proveedor produce el efecto por segunda vez. Bloquear la escritura de A en la base de datos no deshace una carta impresa o un paquete preparado.

Fable reconoció esa ventana residual; en una respuesta afirmó que el margen la hacía «despreciable, no imposible». Pero el expediente permitía pausas indefinidas y exigía un máximo de un efecto. No había una distribución de pausas que justificase llamarla despreciable. Opus también dejó el hueco: en una variante calificó la comprobación como *best-effort* y después presentó la prevención como garantizable.

Existe una alternativa conservadora bajo esas reglas: conceder de forma durable un único permiso de emisión, no transferirlo ni reenviar una operación que pudo haberse emitido. Si el proceso cae antes del envío, quizá no se produzca nada; el caso permite esa pérdida de progreso automático. Mi [comprobación ejecutable](https://github.com/JaviMaligno/benchmaxing-probes/blob/main/check_counterexample.py) muestra dos efectos con el relevo descrito y uno con el permiso no transferible. Es una simulación de la lógica de sus respuestas, no código que los modelos hayan implementado o ejecutado.

Lo interesante es la distancia entre identificar los conceptos correctos y cerrar la garantía que se está prometiendo. Una respuesta puede mencionar todos los patrones esperables y seguir necesitando una corrección sustancial.

## Los empates también cuentan

En permisos, ambos resolvieron las ocho decisiones centrales: restricciones por tenant y propietario, excepciones acotadas, extremo temporal excluido y ocultación de importes. También detectaron que una caché compartida por tenant podía filtrar datos y que había que revalidar permisos y cambios posteriores.

En el análisis de datos, ambos hicieron los cálculos pedidos y rechazaron la comparación engañosa: un sistema parecía mejor en el agregado porque había recibido muchas más tareas fáciles. También incluyeron el coste de corregir fallos y distinguieron una proyección de una conclusión causal.

Esos casos no separaron a los modelos en los criterios centrales. No los descarté ni seguí aumentando la dificultad hasta conseguir un ganador. Marcan un límite del instrumento: tareas que parecían exigentes resultaron insuficientes para distinguirlos en esta muestra.

## Qué queda de la sospecha

Mi percepción inicial sigue siendo una experiencia válida. **Estas pruebas no la convierten en una demostración de que Opus 5 esté benchmaxeado**, y tampoco establecen que Fable sea mejor en general. No medí sesiones largas, investigación de repositorios ni minutos de supervisión humana. No inspeccioné el entrenamiento de ninguno de los dos modelos.

Sí encontré algo concreto: dos sistemas capaces pueden diagnosticar bien una parte del problema y prometer más de lo que su solución garantiza. En [un trabajo anterior sobre modelos del mundo verificados](/es/blog/verified-world-model-still-loses) exploré otro desajuste entre pasar una comprobación y servir para el uso previsto. El mecanismo no es idéntico, pero la pregunta vuelve a ser qué autoriza realmente la métrica a concluir.

La literatura justifica tomarse en serio el benchmaxing. El piloto obliga a ser más preciso al aplicarlo a un modelo concreto. Para elegir una herramienta, me interesa saber si llega al diagnóstico correcto, conserva las restricciones y reduce las correcciones que tengo que hacer. Una tabla puede aportar evidencia sobre esas capacidades. Cuanto más lejos esté su evaluación de mi trabajo, más falta hace comprobar esa transferencia.

*Nota de método: casos y evaluación elaborados con asistencia de Codex; revisión cualitativa por el mismo asistente, sin evaluación independiente ni ciega. Las diez respuestas comparadas y los límites están en el repositorio de evidencia. Se conservan aparte los intentos de diagnóstico y la calibración truncada, que no cuentan como respuestas comparables.*
