# Design: página de mentoría (`/mentoring`)

Date: 2026-08-04
Branch: `feat/mentoring-page`
Status: aprobado en brainstorming (segmento = no técnico dentro de empresa;
oferta en tres niveles; precios "desde" + contacto; EN como versión principal)

## Propósito

Dar destino al tráfico de la serie de artículos sobre habilidades para vibe
coding, cuya primera pieza —
[`what-you-still-need-to-know-to-ship`](../../../src/content/blog/en/what-you-still-need-to-know-to-ship.md)
— se publicó el 2026-08-03. Sin esta página, cada pieza quema su pico de
atención sin ningún sitio al que llevar al lector interesado.

Decisión de orden: **la página va antes que las piezas 2 y 3**. El motivo no es
el tráfico (argumento débil), sino que las piezas 2 y 3 son rampas *por perfil*
y la mentoría también se vende *por perfil*. Con la oferta ya escrita, cada
artículo sabe a quién habla y qué le ofrece al final. Al revés, la oferta acaba
adaptándose a lo que ya se publicó.

Ver también memoria `website-mentoring-teaching-section` y el spec de la serie,
`2026-08-02-vibe-coding-skills-series-design.md`.

## El activo que la sostiene

No se vende "mentoría de IA" — eso lo vende todo el mundo y no se puede evaluar
antes de comprar. Se vende **un sistema concreto, publicado y verificable**: el
bucle de cuatro fases, las doce categorías más una, y los tres niveles. El
artículo está fuera; cualquiera puede leerlo y juzgar si le sirve antes de
hablar con Javi. La página debe apoyarse en eso, no esconderlo.

De ahí el entregable que hace comprable el taller: **el equipo sale con el mapa
de su propio proyecto** — qué casillas están vacías, quién cubre cada una, y qué
se cubre primero. Es un diagnóstico, no un curso. Esa palabra es la que lo hace
aprobable por quien firma.

## Segmento: quién aprende y quién paga

**Aprende: el no técnico dentro de una empresa.** Producto, operaciones,
marketing, finanzas, gente de datos. Están construyendo sus propias herramientas
con agentes, conectadas a sistemas y datos reales de la compañía, y no tienen
ninguna de las trece categorías.

Resuelve tres tensiones que el planteamiento anterior (vender a "equipos") no
resolvía:

- el alumno es no técnico, que es donde el sistema aporta y donde el contenido
  de Javi pega;
- lo paga la empresa, así que el ticket no depende del bolsillo de un
  particular;
- **no hay resistencia de ego**. No se le dice a un ingeniero que no sabe; se le
  da a alguien de negocio algo que nunca se le enseñó y que sabe que no sabe.

**Paga: quien responde del riesgo.** CTO, responsable de datos, dirección. A ese
no se le vende formación: se le vende que su gente de negocio está montando
cosas conectadas a datos reales sin saber que "tener login" y "estar protegido"
son cosas distintas. El técnico del equipo suele ser aliado, no obstáculo: es
quien hereda el problema.

**El individuo sigue abierto** — quien transiciona de carrera, emprende en
solitario o quiere probar. No es el objetivo de negocio: es captación, prueba
social y fuente de casos reales, que hoy es una muestra que el propio artículo
califica de pequeña e informal.

**El equipo técnico NO está excluido.** El sistema aplica a los dos fallos, por
arriba y por abajo. Lo que hay es un **orden de salida**: se arranca por el no
técnico porque la venta es más fácil y el hueco más evidente. El equipo técnico
es un segundo producto que llega con la pieza 3, no un descarte.

## Mercado: internacional y online primero

No solo España. **UK e internacional como mínimo**, y el formato preferido es
**online**, que es donde el alcance compensa.

Consecuencias:

1. **La versión inglesa de la página es la principal**, la española la
   secundaria. Al revés que en el resto del sitio.
2. **FUNDAE deja de ser el eje.** La formación in-company es bonificable en
   España (100% para empresas de 6-9 trabajadores, 75% de 10-49, 60% de 50-249),
   lo que puede dejar el coste real del taller cerca de cero para el cliente
   español. Pero exige impartir a través de entidad acreditada y cumplir sus
   trámites — **decisión de negocio pendiente, no un checkbox**. En la página
   entra como nota para clientes españoles, nunca como vertebrador.

## La oferta

**1. Sesión individual — la puerta abierta.** 60-90 min, uno a uno, sobre su
proyecto real. Sale con su vector y sus casillas vacías.

**2. Taller de equipo — el producto.** Un día (o media jornada) con el equipo no
técnico que ya construye. Entregable: el mapa de su proyecto.

**3. Acompañamiento — la continuación.** Sesiones periódicas mientras construyen
de verdad, revisando su trabajo real. No se vende en frío; se vende al final del
taller.

## Precios

### Datos de mercado investigados (2026-08-04)

**España** — advertencia: casi todas las fuentes son blogs de empresas que
venden estos servicios, con incentivo para inflar. Tratar como **techo
optimista**, no como media.

| Formato | Rango |
|---|---|
| Workshop transversal, 1 jornada | 1.500–3.500 € |
| Programa por departamentos | 4.000–8.000 € |
| Programa completo con seguimiento | 8.000–15.000 € |
| Workshop Claude Code, 2 jornadas para devs | 4.000–5.500 € |
| Workshop presencial por hora | ~200 €/h |
| Formación técnica IT por hora | 50–150 €/h |
| Sesión individual a particular | 40–150 € |

**Reino Unido** — rangos de entrada **más bajos** que los españoles, lo que
confirma el sesgo de las fuentes anteriores.

| Formato | Precio |
|---|---|
| Formación remota, día completo (grupo entero, 6h, preparación incluida) | £580 + IVA |
| La misma presencial | £1.049 + IVA |
| Workshop media jornada presencial, hasta 30 personas, con plan a 30 días | £1.750 |
| Sesión de 60 min, hasta 20 personas | desde £449 + IVA |
| Freelance por día | £400–800 |
| Boutique especializada por día | £1.200–2.500 |

Hallazgos que mandan sobre las cifras concretas:

- **Lo remoto se cobra casi la mitad que lo presencial.** Online da alcance, no
  precio por sesión. A cambio no hay desplazamiento y la preparación se amortiza
  entre clientes.
- **El precio por sesión (grupo entero) gana al precio por persona**, y además
  da el argumento de venta: £1.750 para 30 personas son menos de £60 por cabeza.
  Eso es lo que va en el correo de quien aprueba el gasto.
- **B2B permite facturar entre un 30% y un 50% más** que a particulares por el
  mismo contenido.
- **El precio no debe heredar el rate de ingeniería de Javi** (400 €/día,
  auditoría 150-300 €). Un día de consultoría es tiempo que se vende una vez; un
  taller se prepara una vez y se entrega muchas. El anclaje del comprador no es
  el tiempo del formador, es **lo que cuesta el incidente que se evita**: una
  factura disparada, datos de clientes expuestos, una base de datos borrada sin
  copia. El rate sí encaja en el acompañamiento, que es trabajo continuado.

### Decisión

**Nada de tabla cerrada: "desde" más contacto.** Con dos mercados, dos monedas y
voluntad explícita de negociar, una tabla rígida ata sin dar nada a cambio.

Javi está empezando en esto y prefiere tirar a la baja, lo cual encaja con el
suelo real (más cerca de 600-1.200 € por taller de día que de 1.800-2.500 €).

- Sesión individual: **desde ~90 €**
- Taller online, grupo entero: **desde ~600 €**
- Presencial y acompañamiento: **a consultar**
- **Primer taller a mitad de precio** a cambio de testimonio y permiso para usar
  el caso. No es un truco comercial: es el experimento que fija la tarifa, que
  hoy nadie conoce.

## Estructura de la página

1. **Hero** — le habla a quien firma, no a quien aprende: *"Tu equipo de negocio
   ya está construyendo herramientas conectadas a vuestros datos. Esto es lo que
   necesitan saber para no romper nada."*
2. **El problema en sus términos** — no les falta programar; nadie les dijo qué
   categorías existen. Dos párrafos.
3. **El sistema** — el bucle y el mapa, con las imágenes ya generadas, y enlace
   al artículo completo. Es la sección que hace creíble el resto.
4. **La oferta** — los tres niveles, con el entregable de cada uno.
5. **Qué se lleva el equipo** — el mapa de su proyecto, el vector de cada
   persona, y qué cubrir primero.
6. **Para quién no es** — ver abajo.
7. **CTA** — Calendly, el mismo mecanismo que ya usa `Pricing.astro`.

### "Para quién no es"

Filtros **por objetivo, nunca por perfil** — el sistema sirve a todos los
perfiles, así que excluir por perfil sería falso:

- No es para aprender a programar. Para eso hay bootcamps y son mejores en eso.
- No es para que te construyan el producto. Eso es la consultoría, y es otra
  puerta del mismo sitio.
- No es para obtener una certificación oficial.
- No es formación en una herramienta concreta. Eso está en su documentación,
  gratis.

Cuesta poco y evita las conversaciones que no van a ningún sitio.

## Encaje técnico

- **Páginas nuevas:** `src/pages/en/mentoring/index.astro` y
  `src/pages/es/mentoring/index.astro`, siguiendo el patrón de `business/`.
- **Componentes:** en `src/components/mentoring/`, igual que
  `src/components/business/`.
- **i18n:** claves bajo `mentoring` en `src/i18n/en.json` y `es.json`. La
  redacción se escribe primero en inglés (mercado principal) y se traduce.
- **Gancho en la home:** una entrada en `Pricing.astro` que enlace a
  `/mentoring`, para recoger al visitante que llega por la home con otra
  intención.
- **Nav:** decidir si entra. `business` y `skills` hoy no están en `nav`, así que
  no entra por defecto — el tráfico llega por enlace profundo desde los
  artículos.
- **Enlaces desde la serie:** las piezas 2 y 3 nacen con enlace. La pieza 1, ya
  publicada, puede recibirlo en la web (la copia de Dev.to no se actualiza, y es
  la menos importante).

## Estrategia comercial (lo que la página por sí sola no resuelve)

La página es material de apoyo y es barata de hacer, pero **no es el cuello de
botella del negocio**. Lo que sigue es tan parte del diseño como el HTML.

### El canal y el mercado no coinciden

El tráfico de la serie viene de un blog leído por **técnicos**. El segmento
definido es **no técnico dentro de una empresa**, y el comprador es dirección.
Son tres personas distintas: quien lee no es quien aprende ni quien paga. El
"reenvío del técnico a su fundador" es una hipótesis, no un canal probado.

Canales que sí operan en formación B2B, por orden de coste de arranque:

1. **Red propia** — clientes actuales y anteriores, gente a la que Javi ya formó.
   Es la vía más rápida a la primera entrega y a la primera referencia.
2. **LinkedIn**, hablándole al comprador de riesgo y no al lector técnico. Los
   artículos captan al técnico; los posts pueden captar a dirección si el
   encuadre es el riesgo, no la herramienta.
3. **Partners** — consultoras sin capacidad de formación, asociaciones
   empresariales, entidades organizadoras de FUNDAE (que además resuelven la
   acreditación).

### Dos puertas de entrada, no una (revisado 2026-08-06)

Hallazgo al leer un artículo de un CEO de implantación de agentes en grandes
empresas: **el dolor que tiene presupuesto asignado no es el riesgo, es la
productividad que no llegó.** Su caso típico es un directivo que compró licencias
para miles de personas y cuyo equipo sigue yendo a la misma velocidad.

Comparación de las dos puertas:

| | Riesgo | Productividad |
|---|---|---|
| Qué duele | lo que su gente puede estar exponiendo | pagué y no pasó nada |
| Urgencia | hipotética hasta que ocurre | factura reciente |
| Diferenciación | alta, casi nadie lo plantea así | baja, todos prometen productividad |

**Decisión: el hero sigue siendo el de riesgo**, porque es lo que diferencia y
nadie más lo dice así; la productividad entra como **tercera situación** en la
página, que es donde recoge al comprador que llega con esa factura en la mano.
Liderar con productividad convertiría la oferta en una más del montón.

**Dato que conviene no contradecir:** la distribución de uso en una organización
es una barra de pesas — un grupo pequeño la usa a diario y le saca mucho, otro
la usa de vez en cuando y mal, y una parte grande no la ha abierto. Ocurre
incluso con despliegues bien hechos. Consecuencias para la oferta:

1. **El público del taller actual es el grupo intermedio**, el que ya la usa y
   obtiene poco. **Ojo: eso acota el producto, no el mercado.** La primera
   versión de esta nota decía que el 70% "no va a venir a un taller" y de ahí
   concluía que no era público nuestro. Es un salto injustificado, y Javi lo
   cortó: dar por perdido al 70% condena a la empresa al estancamiento y carga al
   30% restante con tirar de todos los demás.
2. **El 70% falla por la misma raíz que el 20%.** No usan la herramienta porque
   no saben qué pedirle — que es la categoría 1 del mapa, el techo. Uno no la
   abre y el otro la usa mal, pero el agujero es idéntico. El sistema ya los
   explica; lo que falta es producto.
3. **No prometer adopción general con este taller.** El filtro de "qué no es
   esto" acota el producto actual, no renuncia al mercado: prometer que un taller
   de diagnóstico convertirá a quien nunca ha abierto la herramienta reproduce la
   decepción que el comprador ya pagó.

### Cuarta línea de oferta: la sesión de arranque (candidata)

Para el 70% que no ha empezado. **El taller de diagnóstico no les sirve, y no por
desinterés: está construido sobre un proyecto que ellos no tienen.** Sin proyecto
no hay casillas que auditar ni miedo que nombrar en el cuestionario.

Forma que sí encajaría:

- **Una hora, no un día.** Su objeción es "no tengo tiempo para esto", así que el
  formato tiene que desmentirla antes que el contenido.
- **Sin mapa y sin riesgo.** Solo la categoría 1: qué se le puede pedir, con
  ejemplos sacados de **su propio trabajo de esa semana**, y nada de programar.
- **Una única meta medible:** que salgan habiendo hecho una cosa real y útil con
  la herramienta antes de terminar. Eso convierte a un no-usuario; una
  demostración no.
- El mapa viene después, para quien siga.

Argumento comercial además del evidente: es el segmento más grande y nadie lo
ataca bien, porque el discurso dominante ya lo ha dado por irrecuperable.

Pendiente: **un post propio para este grupo**, distinto del resto de la serie —
que hasta ahora habla siempre a quien ya construye.

### Posicionamiento: puerta a la consultoría, no negocio aislado

Un taller de diagnóstico mete a Javi un día entero dentro de una empresa, viendo
sus problemas reales, con dirección delante. Es el mejor origen de proyecto que
existe, y es el modelo clásico de consultora: la formación abre la puerta, el
proyecto la cruza.

**Consecuencia sobre las métricas:** el éxito no son los ingresos por talleres,
son los proyectos que salen de ellos. Con esa métrica, tirar los precios a la
baja no es una concesión: es la estrategia correcta.

### Lo que falta para poder entregar

- **El taller no existe todavía.** Existe el *contenido* (el sistema), pero no
  la agenda, los ejercicios, la plantilla del diagnóstico, ni el método para
  levantar el mapa de un equipo en una sesión. La primera entrega es la que
  produce el único caso, así que no puede improvisarse.
- **Cero prueba social**, que en B2B bloquea. El piloto a mitad de precio está
  escrito pero no ejecutado; la vía rápida es la red propia, no la página.
- **Operativa sin resolver:** facturación a empresas de España y UK, IVA, y
  FUNDAE (que exige entidad acreditada — o se busca partner o esa palanca no
  existe).
- **Capacidad:** cuántos talleres al mes caben sin comerse horas facturables. Si
  son uno o dos, esto es un producto complementario y hay que dimensionarlo como
  tal, no como línea principal.

## Fase 2 — comprometida, no opcional

**Autoevaluación interactiva:** el visitante se puntúa en las trece categorías y
obtiene su vector. Reutiliza íntegro el contenido del mapa.

**No es un adorno: es la herramienta de captación.** Alguien se puntúa, ve sus
casillas vacías, y ahí es donde deja el correo — convierte tráfico anónimo en
contacto, y le da un motivo para escribir que no es "quiero comprar formación".
Comercialmente mueve más que la propia página de oferta, así que su prioridad no
debe fijarse por criterios estéticos.

Se deja fuera del primer lanzamiento solo porque es una funcionalidad y no una
página. Entra inmediatamente después, antes o en paralelo a la pieza 2.

## Refinamientos pendientes del sistema (no tocar el artículo aún)

- **Variables de entorno ≠ secretos.** En la categoría de Secretos, nivel *Con
  soltura*: no todo lo que va en variables de entorno es secreto, y no toda
  configuración debería ir ahí — los feature flags son el caso típico que acaba
  mal colocado. Distinguir secreto de configuración.

Política: **no editar el artículo publicado por un refinamiento suelto.** No
corrige un error, añade matiz, y editarlo desincroniza la copia de Dev.to. Se
acumulan y, si salen dos o tres, se hace una pasada. En la pieza 2 se desarrolla
sin coste.

## Fuentes de precios

- [Javadex — formación IA in-company: formatos y precios 2026](https://www.javadex.es/blog/formacion-ia-in-company-empresas-equipos-precios-2026)
- [Javadex — programa por horas](https://www.javadex.es/blog/formacion-ia-empresas-equipos-bolsa-horas-flexible-2026)
- [Upliora — tarifas consultoría IA España 2026](https://www.upliora.es/blog/tarifas-consultoria-inteligencia-artificial-espana-precios-mercado-2026)
- [tarifaautonomo — tarifa hora formador freelance](https://tarifaautonomo.com/blog/tarifa-hora-formador-espana)
- [LogicRoad — on-site AI training cost UK 2026](https://logicroad.co.uk/blog/how-much-does-on-site-ai-training-cost-uk-2026)
- [Elansio — AI training and consultant costs UK 2026](https://elansio.com/ai-training-cost-uk.html)
- [Nicola Lazzari — AI consultant hourly rate UK 2026](https://nicolalazzari.ai/guides/ai-consultant-pricing-guide-uk)
- [Lakkun — formación bonificada 2026](https://lakkun.es/formacion-bonificada-en-2026-guia-completa-requisitos-limites-y-pasos/)
- [Grupo Futuro — créditos formación bonificada 2026](https://grupofuturo.es/actualizacion-de-los-creditos-para-la-formacion-bonificada-en-2026/)
