# Artículo de blog: Build vs Buy en la era de los agentes (la atención como recurso escaso)

**Fecha:** 2026-06-30
**Tipo:** Artículo de blog (EN/ES), publicado vía skill `blog-writer`
**Estado:** Diseño aprobado, pendiente de escritura

## Idea central

Con agentes de código (Claude Code, Codex) construir casi cualquier cosa parece posible, y la
tentación tira fuerte hacia *build*. Llevado al extremo: "el único software que necesitas es la
suscripción a Claude/ChatGPT". Pero ese extremo tiene trampa.

**Tesis:** Los agentes no abarataron el "buy vs build", lo **reescribieron**. Colapsaron el coste de
construir y, al hacerlo, desnudaron qué comprabas en realidad cuando pagabas por software: no el
software en sí, sino (1) la **absorción del mantenimiento**, (2) el **desriesgo de la fase de prueba y
error** de un producto ya construido, y (3) tu **atención** — el único recurso que no se paraleliza.
Puedes lanzar cinco agentes a la vez; no puedes prestar atención a cinco cosas a la vez.

## Postura del autor

**Pro-build con matices.** Construir se ha vuelto la opción por defecto, *especialmente para lo trivial
que se puede dejar rápido en automático* (no captura atención recurrente). No es un manifiesto
triunfalista: los matices (mantenimiento, atención, límites) son parte del argumento, no una nota al
pie.

## Marco de decisión (el esqueleto del artículo)

**Construir cuando:**
1. **Atención baja** — es trivial y, una vez montado, se queda en automático y no te vuelve a pedir
   atención.
2. **El mercado no encaja** — no hay nada que satisfaga tu demanda lo suficiente.

**Comprar / no construir cuando:**
3. **Atención alta / mantenimiento continuo** — quedarías enganchado a mantenerlo indefinidamente; el
   proveedor te vende precisamente cargar él con esa deuda.
4. **Límites** — topes de uso, cosas que no deben correr sin supervisión. Aquí se rompe el extremo del
   "solo necesitas una suscripción".

## Ejemplos a usar (reales, del autor)

- **Sincronizador de calendarios** (personal, hero) — para que cualquiera que vea un calendario vea el
  bloqueo que viene de otro de mis calendarios. Hay herramientas de pago, pero monté un script con
  Claude Code + una rutina que corre regularmente. Caso de disparador 1 (trivial + automático). Contar:
  qué herramientas de pago existen, por qué lo monté yo, cómo es la rutina, qué pasa cuando algo se
  rompe (= mantenimiento, el matiz honesto).
- **VitaminD Explorer / getvitamind.app** (personal) — calculadora de síntesis de vitamina D solar;
  nació como artifact de Claude y acabó siendo PWA. Caso de disparador 2 (no había nada en el mercado
  que me sirviera lo suficiente).
- **Sistemas de monitorización de servicios** (empresarial, puente) — corren automáticamente analizando
  logs y haciendo revisiones de performance / calidad de código. **Matiz importante:** estos sí existen
  en el mercado; el argumento de build aquí NO es falta de encaje, sino la **capa de personalización +
  atención baja (corre solo) + poco esfuerzo** gracias a los agentes. Mismo disparador 1 a escala
  empresa.

## Estructura

1. **Apertura** — anécdota del calendario. La tentación de build con agentes. El extremo retórico:
   "el único software que necesitas es la suscripción".
2. **Qué cambió de verdad** — los agentes reescribieron el buy vs build; al colapsar el coste de
   construir, desnudaron qué comprabas en realidad: mantenimiento + desriesgo + atención (recurso no
   paralelizable).
3. **Cuándo construir** — disparadores 1 (atención baja/automático → calendario) y 2 (sin encaje de
   mercado → VitaminD).
4. **La trampa** — mantenimiento y atención. Y los límites que rompen el "solo una suscripción".
5. **Misma lógica, escala empresa** — desviarse de la línea de negocio vs equipo de herramientas
   internas vs SaaS. Caso de los sistemas de monitorización (personalización + atención baja, no falta
   de encaje). El marco no cambia: ¿quién carga el mantenimiento y quién carga la atención del equipo?
6. **Cierre** — pro-build con matices, sobre todo para lo trivial que se deja en automático.

## Restricciones de voz

- Seguir la memoria `feedback_blog_voice_nuance`: evitar afirmaciones tajantes y hombres de paja sobre
  la trayectoria de Javier. Matiz, no rotundidad.
- Reconocer que el discurso de "muerte del SaaS" a nivel empresarial está trillado; la originalidad está
  en la lente personal y en el marco de la **atención** como recurso escaso (no el coste de construir).
- Bilingüe EN/ES, frontmatter y estructura según `blog-writer`.

## Siguiente paso

Invocar la skill `blog-writer` para redactar el artículo (EN/ES) siguiendo esta estructura.
