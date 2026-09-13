---
title: "Indexado no es mostrado: un mes plano en cero con todas las métricas en verde"
description: "Un sitio pierde el 98,7 % de sus impresiones de un día para otro y se queda ahí un mes. Sin acción manual, sin desindexación, 3.180 páginas indexadas y subiendo. Qué descartaron los números, qué replantearon y qué sigo sin poder explicar."
pubDate: 2026-09-21
tags: ["SEO", "Datos", "Producto", "Investigación"]
lang: es
translationKey: indexed-is-not-served
heroImage: "/blog/indexed-is-not-served.png"
linkedinLinks:
  - label: "El sitio en cuestión"
    url: "https://getvitamind.app"
---

El 15 de agosto [VitaminD Explorer](https://getvitamind.app) sirvió 879
impresiones en la Búsqueda de Google. El 16 de agosto sirvió 35. No se ha
recuperado: un mes después va entre 8 y 40 impresiones al día, con esencialmente
cero clics.

Es una calculadora de vitamina D solar: dada una ubicación real y un tipo de
piel real, calcula si el sol de ahí fuera puede sintetizar vitamina D ahora
mismo, cuántos minutos harían falta y qué meses del año es posible en esa
latitud. Esa pregunta tiene una respuesta distinta en cada ciudad y cada mes,
por eso el sitio carga unos cuantos miles de páginas — y por eso es un espécimen
útil para este post mortem.

Todos los indicadores de salud que yo tenía estuvieron en verde todo el tiempo.
Sin acción manual. Sin desindexación: el recuento de indexadas *subió*, de 3.170
páginas a 3.180. Sitemap enviado, leído y aceptado, 3.636 URLs, última lectura
tres días antes de que yo mirara. Googlebot sigue viniendo, sin errores de host.
Posición media 9,9, que es donde había estado siempre.

Esto es el post mortem de un diagnóstico, no de un arreglo. Sigo sin saber la
causa. Lo que sí tengo es un conjunto de medidas que mataron varias
explicaciones cómodas, y una distinción que antes no tenía: **estar indexado,
ser rastreado y ser mostrado son tres monedas distintas, y se puede ser rico en
la primera y estar en quiebra en la tercera.**

## El agregado lo escondió trece días

El primer error no fue analítico, fue ergonómico. Todos los informes que miraba
eran totales de 28 o de 90 días. "119 clics en tres meses" se lee como un sitio
pequeño que crece despacio.

Abrir la serie diaria enseñaba otra cosa: esos 119 clics están casi todos
concentrados entre el 21 de julio y el 14 de agosto, con días de hasta 15.
Después, la línea está plana en el suelo. Habían pasado trece días antes de que
nadie mirara la *forma* de la serie en vez de su suma.

Un agregado no distingue una tendencia que sube de una muerta que solía subir.
Escrito así parece obvio. No lo es cuando la vista por defecto del panel es un
total y vas con prisa.

## La caída de cerca

| Día | Impresiones | Clics |
|---|---|---|
| 14 ago | 1.427 | 5 |
| 15 ago | 879 | 3 |
| **16 ago** | **35** | 1 |
| 17 ago – 10 sep | 8–40 al día | ~0 |

Un solo día, −96 %, permanente. Esa forma importa: una caída estacional baja en
pendiente, una rotura técnica suele salir en los informes de error, y una
reclasificación algorítmica conmuta.

## Las explicaciones que murieron en la comprobación siguiente

En una tarde produje tres causas seguras. Las tres quedaron falsadas, dos de
ellas por mí, en cuestión de horas:

- **"Es la actualización antispam."** La de Google empezó el 18 de agosto. La
  caída es el 16. Dos días *antes*, no después.
- **"Es el cambio de títulos que desplegué el 15 a las 22:06."** La inspección
  de URL decía que Google había rastreado esas páginas por última vez el 26 de
  julio y el 3 de agosto. No había visto el cambio siquiera. Yo había afirmado
  como causa un despliegue que el rastreador nunca llegó a buscar.
- **"Es estacional, se mueren las consultas de agosto."** Las páginas de
  septiembre ya acumulaban impresiones antes del corte, y el desplome es
  idéntico en tres idiomas cuyos patrones estacionales no lo son.

La disciplina que sobrevive a esto vale más que cualquiera de las tres
hipótesis: **no produzcas una cuarta explicación solo porque se murió la
tercera.** Un desplome sin explicar es un estado aceptable. Una explicación
equivocada sobre la que ya has empezado a actuar, no.

## La medida que lo replanteó

Comparando el 17 ago – 10 sep contra la ventana equivalente anterior al corte,
por familia de URL — cada familia es la misma plantilla en un idioma distinto,
por ejemplo [amanecer y atardecer en Madrid en septiembre](https://getvitamind.app/amanecer/madrid/septiembre):

| Familia | Impresiones antes | Después | Posición |
|---|---|---|---|
| `/sunrise/` (en) | 14.300 | 347 | 9,0 → 21,6 |
| `/amanecer/` (es) | 15.400 | 111 | 12,0 → 13,8 |
| `/sonnenaufgang/` (de) | 4.850 | 43 | 8,4 → 11,3 |
| **Sitio entero** | **36.900** | **488** | **9,4 → 20,2** |

Mira las dos columnas juntas. Las impresiones caen un 98,7 %. La posición cae
entre 2 y 12 puestos. No son el mismo suceso.

Si un sitio se deslizara en el ranking, las impresiones decaerían más o menos en
proporción a los puestos perdidos: sigues apareciendo, más abajo. Aquí el sitio
conserva su posición *donde todavía aparece*, y deja de aparecer en casi todo lo
demás. Las consultas distintas que lo devuelven pasaron de cuatro cifras a 159
en 28 días.

Eso no es un problema de ranking. Es un problema de **elegibilidad**: el sitio
dejó de entrar en el conjunto de candidatos de la cola larga. Y no lo habría
visto desde el titular de "posición media", que mezcla las dos cosas en un solo
número.

## Tres monedas, no una

Quince días después de la caída publiqué un pequeño conjunto de páginas nuevas:
un hub que responde a [cuánto tiempo al sol hace falta para la vitamina D](https://getvitamind.app/cuanto-sol-vitamina-d),
con una variante por tipo de piel, en seis idiomas. Dos semanas más tarde las
comprobé una a una, y los estados merecen citarse literalmente:

- Hub en español: **indexada**, al día siguiente de publicarla.
- Alemán: **"Rastreada: actualmente sin indexar"** — buscada, evaluada,
  descartada.
- Ruso: **"Descubierta: actualmente sin indexar"** — conocida, nunca buscada.
- Inglés, francés y lituano: **"Google no reconoce esta URL"** — ni siquiera
  descubiertas.

Las seis están en el mismo sitemap. El sitemap se leyó, con éxito, tres días
antes de estas comprobaciones. Google tenía la lista y no pensaba ir a buscarlas.

Entonces pedí indexación a mano. La página rusa pasó de "descubierta, nunca
rastreada" a **"La URL está en Google"** en minutos.

Ahí está la lección entera, en un experimento. El contenido no estaba siendo
rechazado: cuando se le pidió, Google lo buscó y lo indexó al instante. Lo que
faltaba era **demanda de rastreo**, las ganas de ir a mirar. Tres cosas
distintas que la palabra "indexado" colapsa en una:

1. **Descubierta** — Google tiene la URL.
2. **Rastreada** — Google ha gastado una petición en ella.
3. **Mostrada** — Google la pone delante de alguien.

Un panel que dice 3.180 páginas indexadas te está hablando de las monedas 1 y 2.
No dice nada de la 3, que es la única en la que hay usuarios.

## El número que invalida el consejo habitual

Ya puestos, una cosa más, medida sobre 33.000 impresiones y 1.000 páginas antes
del desplome:

| Banda | Págs | Impresiones | Clics | CTR |
|---|---|---|---|---|
| Posiciones 6-10 | 637 | 22.852 | 68 | **0,30 %** |
| Posiciones 11-20 | 253 | 10.273 | 32 | **0,31 %** |

Pasar de la página dos a la página uno no compró nada. No "menos de lo
esperado": nada, con dos decimales, sobre una muestra suficiente para verlo. El
CTR esperado en posiciones 6-10 es de varios por ciento; esto está un orden de
magnitud por debajo.

Todo consejo de SEO sobre el que yo pueda actuar está denominado en posiciones.
En este sitio, con esta forma de resultado, la posición no es convertible en
clics en absoluto. Lo que significa que la respuesta honesta a "cómo conseguimos
más tráfico" nunca fue "posiciona mejor", y que un año de trabajo dirigido a
posicionar habría rendido cero — medible, antes de hacerlo.

## Lo que me llevo

- **Mira la forma de la serie antes que el total.** Un agregado no distingue
  "creciendo" de "muerto, antes crecía". Abre la gráfica diaria primero,
  siempre.
- **Separa ranking de elegibilidad.** Si las impresiones caen mucho más deprisa
  que la posición, no es que te superen, es que no te consideran. Tienen causas
  distintas y arreglos distintos.
- **No dejes que "indexado" sustituya a "mostrado".** Comprueba descubierta,
  rastreada y mostrada como tres estados separados. El fallo puede estar en
  cualquiera de ellos, y el recuento de indexadas se ve bien en los tres casos.
- **Comprueba si tu moneda convierte.** Antes de optimizar una métrica, mide
  cuánto vale una unidad. La mía valía cero, y lo enseñaba una sola tabla.

Vuelvo a la causa con una pregunta más limpia que la de partida. No "por qué
cayó el tráfico", sino "por qué este dominio dejó de ser considerado". Todavía
no tengo la respuesta, y prefiero decir eso a suministrar una cuarta historia.

Mientras tanto la cosa sigue funcionando, que es la parte que la búsqueda nunca
midió: [getvitamind.app](https://getvitamind.app) responde a la pregunta del sol
para tu ubicación y tu tipo de piel, sin cuenta y sin instalar nada, y hay un
[servidor MCP](https://getvitamind.app/connect) si prefieres preguntárselo a tu
asistente.
