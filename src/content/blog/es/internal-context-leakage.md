---
title: "Tu agente no sabe qué es interno: fugas de contexto en flujos con IA"
description: "Los agentes de IA acaban citando feedback interno, nomenclatura de specs y notas de proceso en entregables para clientes. Por qué ocurre, una taxonomía de los tres modos de fallo y las soluciones estructurales que funcionan de verdad."
pubDate: 2026-07-19
tags: ["IA", "Agentes", "Claude Code", "Flujos de trabajo"]
lang: es
translationKey: internal-context-leakage
heroImage: "/blog/internal-context-leakage.png"
linkedinLinks:
  - label: "Relacionado: skills de Claude Code"
    url: "https://www.javieraguilar.ai/es/blog/claude-code-skills-blog-writer"
---

Hay un modo de fallo con el que me tropiezo constantemente al trabajar con agentes de IA, y una vez lo ves ya no puedes dejar de verlo: el agente coge contexto que debía quedarse *dentro* de la sesión de trabajo — información de cliente, nomenclatura interna de specs, mis propias correcciones — y lo escribe directamente en el entregable. Lo que debía *dar forma* al resultado acaba *dentro* del resultado.

Dos ejemplos reales, ambos de mi día a día con Claude Code (aunque he visto lo mismo con Codex, y apostaría a que es universal en agentes).

**La corrección citada.** Estaba escribiendo un artículo con asistencia de IA. El borrador llegó con un título en negativo — algo en la línea de "este artículo no lo escribió la IA". Le di feedback: eso no, primero porque no quiero un titular en negativo, y segundo porque además es falso — la escritura como tal sí la hizo la IA. El agente, obediente, lo quitó del título. Y acto seguido cogió mi corrección, con justificación incluida, y la escribió en el cuerpo del artículo. Mi nota editorial al agente — una instrucción *sobre* el texto — se convirtió en contenido *del* texto.

**El spec filtrado.** Cuando trabajo para clientes mantengo un spec: puntos de funcionalidad numerados, items de feedback, abreviaturas internas para cada línea de trabajo. Cuando le pido al agente que redacte un email de estado, le encanta referirse a esa nomenclatura interna — "según el punto 3.2 del spec de feedback" — en un mensaje dirigido a un cliente que nunca ha visto el spec, no conoce la numeración y no tiene por qué conocerla.

Ninguno de los dos casos es una alucinación. El agente no se inventó nada. Hizo algo más sutil y, en cierto modo, más peligroso: usó fielmente información que tenía — solo que no tenía ni idea de que esa información no era *para* el lector.

## Una taxonomía: tres formas de fuga

En cuanto empecé a coleccionar casos, se ordenaron solos en tres modos de fallo distintos, y no importan igual.

**Tipo 1 — Fuga confidencial.** Información que no puede salir de casa: condiciones de cliente, valoraciones internas, contexto comercial, feedback sincero sobre un tercero. Es el caso grave, y el que la revisión humana suele cazar a tiempo — precisamente *porque* es grave, cualquier cosa que roce lo sensible la leemos con máxima atención antes de que salga. Pero la revisión es la última línea, no la primera; aquí la defensa real es estructural, y es lo más fuerte que puedes hacer — llego a ella más abajo. El agente lo ha intentado, desde luego; simplemente no me lo ha colado. Que no es lo mismo que decir que nunca lo hará.

**Tipo 2 — Referencia ininteligible.** No es confidencial, solo carece de sentido fuera de la sesión: la numeración del spec en el email al cliente, un nombre en clave interno de una línea de trabajo, una abreviatura que solo existe en mis notas. Al lector no le hace daño — lo deja confundido. La comunicación parece descuidada y obliga a una ronda de "perdona, ¿qué es F-12?".

**Tipo 3 — Residuo de proceso.** Andamiaje de la sesión de trabajo que acaba en el producto final: mi corrección citada en el artículo, un "siguiendo tu feedback, he reestructurado esta sección" en un documento, meta-comentarios sobre el propio proceso de redacción. Nada sensible, nada confuso siquiera — simplemente no es *producto*. Es el equivalente en carpintería a entregar el mueble con las mordazas puestas.

Y aquí está la trampa: los tipos 2 y 3 se cuelan *porque* parecen inofensivos. El esfuerzo de revisión se concentra de forma natural en el tipo 1, donde lo que está en juego es evidente. Las fugas inocuas son las que llegan al lector.

## Por qué ocurre (y por qué mejorar el prompt no lo arregla del todo)

La causa raíz es estructural. Un agente LLM opera sobre una única ventana de contexto indiferenciada. Tu spec, tu feedback, el último email del cliente, el borrador en curso — dentro del modelo, todo son tokens con el mismo estatus. No existe una noción nativa de *procedencia* ("esto viene de un documento interno") ni una noción nativa de *audiencia* ("el lector de este email nunca ha visto ese documento").

Mi corrección del título ilustra el mecanismo a la perfección. La instrucción tenía dos partes: una acción (quitar el título en negativo) y una justificación (no quiero ese enfoque, y además es falso). El agente ejecutó la acción *y* trató la justificación como material. Desde la perspectiva del modelo no es descabellado: la justificación era interesante, relevante y estaba ahí mismo, en contexto. Los modelos además están entrenados para atender el feedback de forma visible, y el camino de menor resistencia para "atender" algo suele ser *incorporarlo*, en vez de aplicarlo en silencio y seguir.

Dos factores agravantes:

- **Sesiones largas compartidas.** Cuanto más trabajo haces en una misma sesión — discutir el spec, debatir el feedback, redactar el email — más rico es el contexto interno que convive pegado al entregable, y más probable la contaminación.
- **Estandarizar ayuda, hasta que deja de ayudar.** Para las producciones que repito mucho, he ido codificando el procedimiento en instrucciones y memoria ([skills](/es/blog/claude-code-skills-blog-writer), reglas en CLAUDE.md, plantillas). Eso reduce la tasa de verdad: cuando el agente conoce la forma de un email de cliente, improvisa menos referencias al spec. Pero es mitigación, no prevención — las instrucciones viven en el mismo contexto indiferenciado que todo lo demás, y pierden contra la proximidad lo bastante a menudo como para no poder confiar solo en ellas.

Por eso he acabado pensando en esto como pensamos en seguridad: la exfiltración de datos no se arregla pidiendo las cosas por favor. Se arregla con arquitectura.

## Soluciones estructurales

Estos son los patrones hacia los que estoy convergiendo. El hilo común: dejar de intentar que un agente *recuerde* qué es interno, y en su lugar hacer que sea *imposible o improbable* que el contexto interno llegue al entregable.

### 1. Principio de mínimo contexto

El análogo directo del mínimo privilegio: cada paso del pipeline recibe solo el contexto que necesita. El agente que redacta el email al cliente no hereda la sesión de trabajo entera con el spec y la discusión del feedback — recibe un brief curado: qué comunicar, a quién y en qué tono.

En Claude Code esto sale casi gratis: los subagentes no ven la conversación del padre. Delega la redacción a un subagente con un brief explícito, y el contexto interno físicamente no está ahí para filtrarse. El modo de fallo cambia de "filtró la numeración del spec" a "preguntó por un detalle que no tenía" — que es un modo de fallo mucho mejor, porque es visible.

Para el material confidencial — el caso del Tipo 1 — esta es la regla en su versión más dura y a la vez más barata: no lo cures dentro del brief siquiera. Retenlo por completo, o dale al agente acceso de solo lectura a fuentes que no pueda citar en bloque, de modo que el material pueda informar una decisión aguas arriba sin llegar a estar nunca en el contexto que produce el entregable. Si nunca entra, no hay nada que filtrar — por eso, para la categoría grave, esto gana a cualquier cantidad de vigilancia aguas abajo.

Un matiz, y es el que más veces se me escapa: mínimo contexto no significa contexto *famélico*. Un agente fresco no arrastra el exceso interno — bien — pero tampoco arrastra lo que el cliente ya sabe legítimamente: lo que se acordó en la última llamada, lo que se le ha enviado antes, la abreviatura que introdujo el propio cliente. Si lo dejas en ayunas, sobrecompensa — una redacción o revisión ingenua, insegura de qué conoce el lector, vuelve a explicarlo todo y pide aclaraciones que no necesita, y el email converge en algo largo, redundante y ligeramente paternalista. El brief tiene que ser *preciso*: exactamente lo que este lector necesita, ni más ni menos. Y eso significa que el contexto interno que merece la pena guardar no es la numeración del spec — es un registro actualizado de lo que de verdad se le ha comunicado a este cliente. Lleva ese hilo al día, y la misma disciplina que corta la fuga corta también el exceso de explicación. Los dos fallos son en realidad uno solo: falta de precisión sobre la audiencia.

### 2. Revisión en sala limpia

El patrón de dos agentes (o dos sesiones): un *escritor* con todo el contexto interno produce el borrador; un *editor* en sesión limpia — que solo ve el borrador más una descripción de la audiencia — lo revisa con una única pregunta: "¿Hay algo aquí que presuponga contexto que este lector no tiene?"

El editor caza las fugas precisamente porque comparte la ignorancia del lector. Tampoco sabe qué significa "F-12" — así que lo marca. Un editor dentro de la sesión original no puede hacer esto de forma fiable: sabe demasiado, y el conocimiento es exactamente el problema.

### 3. Etiquetado de procedencia

El material interno vive en ubicaciones claramente marcadas — un directorio `internal/`, una sección etiquetada en las notas — con una regla fija en las instrucciones del agente: *el contenido de estas fuentes nunca se cita ni se referencia literalmente en entregables externos; informa, pero no aparece.* Es más débil que aislar el contexto (la regla sigue viviendo en la misma ventana), pero es barato, y da a las pasadas de revisión y a los lints algo mecánico contra lo que comprobar.

### 4. Una barrera determinista, no otro LLM

Para los patrones de fuga recurrentes, el mejor revisor no es un modelo — es un script. Un lint previo al envío que busca en el entregable identificadores de spec, nombres en clave internos, abreviaturas de cliente, palabras clave de proyecto. En Claude Code esto encaja de forma natural en un hook; en cualquier otro sitio, son diez líneas de script en el pipeline.

Es tonto, y esa es la gracia. No se distrae, no se deja convencer por el contexto y no cuesta nada. No cazará una fuga parafraseada — para eso está la sala limpia — pero convierte el vocabulario de fuga *conocido* en una barrera dura en lugar de una esperanza.

### 5. Handoff explícito

La versión más fuerte del mínimo contexto, para entregables de alto riesgo: la versión final se produce en una sesión nueva a partir de un *paquete de entrega* — el borrador, la descripción de la audiencia, las restricciones de estilo — y nada más. La sesión de trabajo y la sesión de producción nunca se mezclan. Es la misma disciplina que separar staging de producción: no porque nadie planee desplegar la build de debug, sino porque los entornos que no pueden tocarse no pueden contaminarse.

## La idea de fondo

Los ejemplos son pequeños — una corrección citada, un número de spec en un email. El patrón no lo es. A medida que los agentes asumen más comunicación externa, la frontera entre *contexto de trabajo* y *entregable* se convierte en una interfaz real, y ahora mismo esa interfaz solo existe en nuestra cabeza. El modelo no la tiene.

Así que no la pongas en el prompt a ver si hay suerte. Ponla en la arquitectura: acota el contexto, aísla las sesiones, pon barreras a la salida. Esta lección en software la aprendimos hace mucho — los componentes que no deben interferir entre sí son los que *separas*, no a los que les pides que se porten bien.

---

*Construyo pipelines de agentes de IA con exactamente este tipo de guardarraíles. Si tu equipo está poniendo agentes delante de clientes, [hablamos](/es/#contact).*
