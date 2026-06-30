---
title: "De Artefacto de Claude a PWA en Producción: Construyendo VitaminD Explorer"
description: "Cómo una pregunta simple sobre la síntesis de vitamina D se convirtió en un artefacto de Claude, y después en una PWA completa con visualizaciones D3.js, notificaciones push y 6 idiomas."
pubDate: 2026-04-29
tags: ["Claude", "PWA", "Next.js", "D3.js", "Side Project"]
lang: es
translationKey: from-artifact-to-pwa-vitamind
heroImage: "/blog/from-artifact-to-pwa-vitamind.png"
---

Todo empezó con una pregunta simple: **¿puedo sintetizar vitamina D hoy en Londres?**

> **Pruébala ya → [VitaminD Explorer](https://getvitamind.app)** — gratuita y open source. Esta es la historia de cómo llegó hasta ahí.

Había estado leyendo sobre cómo la latitud, la estación y el tipo de piel determinan si la luz solar puede realmente activar la producción de vitamina D. La ciencia es clara — por debajo de cierto [ángulo de elevación solar](https://en.wikipedia.org/wiki/Solar_zenith_angle) (~45–50°), la radiación UVB es demasiado débil para la síntesis, sin importar cuánto tiempo pases al aire libre. Pero calcular *cuándo* se abre esa ventana para una ciudad concreta en un día concreto requiere cálculos con [declinación solar](https://en.wikipedia.org/wiki/Position_of_the_Sun#Declination_of_the_Sun), ángulos horarios y trigonometría esférica.

Así que se lo pregunté a Claude.

## El Artefacto que lo Empezó Todo

Claude no se limitó a responder la pregunta — generó un [artefacto interactivo](https://claude.ai/public/artifacts/e1377c30-3b83-47bd-938f-6e107c21231a) con una curva de elevación solar, un slider para el día del año y una línea de umbral mostrando cuándo era posible la síntesis. Usaba la [fórmula de Spencer de 1971](https://doi.org/10.1016/0038-092X(71)90055-1) para la declinación solar y la ecuación del tiempo, proyectado en un gráfico SVG limpio.

Esperaba un párrafo con algunos números. En vez de eso obtuve un prototipo funcional.

Jugué con él unos minutos — recorriendo el año, viendo cómo la ventana de síntesis se expandía en verano y desaparecía en invierno — y pensé: *esto es realmente útil*. No solo para mí, sino para cualquiera viviendo en latitudes altas preguntándose si merece la pena salir a tomar el sol por la vitamina D.

Ahí fue cuando decidí construirlo de verdad.

## De Juguete a Producto: Las Decisiones Técnicas

### Next.js App Router como Base

Elegí Next.js 16 con App Router. La app necesitaba interactividad en cliente (gráficos D3, geolocalización, animaciones) pero también rutas API en servidor (proxy de datos meteorológicos, envío de notificaciones push, búsqueda de ciudades). App Router te da ambas cosas en un solo proyecto sin tener que unir servicios separados.

### D3.js sobre Canvas: Rendimiento sobre Comodidad

El artefacto original usaba SVG para todo. Eso funciona para un solo gráfico, pero yo quería tres visualizaciones: una curva solar diaria, un mapa mundial interactivo y un heatmap de latitud × día del año (130 latitudes × 365 días = 47.450 celdas).

SVG no aguanta eso en móvil. Así que migré a renderizado Canvas con una capa SVG superpuesta para elementos interactivos — tooltips, zonas de clic, controles de umbral. El mapa mundial usa una proyección equirectangular con pan y pinch-to-zoom, renderizando 195 países desde TopoJSON en cada frame. El escalado por device pixel ratio lo mantiene nítido en pantallas Retina.

La contrapartida es complejidad. Canvas implica transformaciones de coordenadas manuales, detección de clics y gestión de redibujado. Pero era necesario — solo el heatmap habría creado 47K nodos DOM como rectángulos SVG.

### Las Matemáticas de la Vitamina D: No Solo Ángulos Solares

El artefacto solo calculaba *cuándo* era posible la síntesis. Yo quería responder *cuánto tiempo necesitas estar fuera* para una dosis concreta — digamos, 1000 UI.

Esto requería modelar la fotobiología real. La velocidad depende de:

- **UVI** (índice UV a la hora actual)
- **Tipo de piel** ([escala Fitzpatrick](https://en.wikipedia.org/wiki/Fitzpatrick_scale) I–VI, cada uno con una [MED](https://en.wikipedia.org/wiki/Minimal_erythema_dose) diferente — Dosis Eritematosa Mínima)
- **Área corporal expuesta** (cara y manos vs. camiseta y pantalón corto)
- **Edad** (la eficiencia de síntesis cae ~1,3% por año después de los 20, según [Holick et al. 1989](https://doi.org/10.1016/S0140-6736(89)92611-4))

Y, fundamentalmente, no es lineal. La [previtamina D3](https://en.wikipedia.org/wiki/Previtamin_D3) no simplemente se acumula — se [fotodegrada](https://en.wikipedia.org/wiki/Photodegradation) bajo UVB continuado en compuestos inertes (lumisterol y taquisterol). Este es el mecanismo de protección contra sobredosis del cuerpo, y significa que hay un techo en cuánta puedes producir por sesión.

Lo modelé como una exponencial saturante:

$$
UI(t) = UI_{sat} \cdot \left(1 - e^{-\frac{R \cdot t}{UI_{sat}}}\right)
$$

Donde $UI_{sat}$ es el techo de fotodegradación (19.200 UI para cuerpo completo a 1 MED, según [Holick 1982](https://doi.org/10.1126/science.6281884), escalado por área y edad) y `R` es la tasa de producción basada en las tablas MED de [Dowdy et al. 2010](https://doi.org/10.1111/j.1365-2133.2010.09888.x). A dosis bajas, coincide con la regla lineal de Holick. A dosis más altas, los rendimientos decrecientes entran en juego. El modelo concuerda con [Young et al. 2021](https://doi.org/10.1073/pnas.2015867118) (n=75, validación in-vivo).

### Datos Meteorológicos Reales: Open-Meteo

La geometría solar te da estimaciones de cielo despejado, pero las nubes importan enormemente. Una cobertura nubosa del 70% puede reducir los UVB un 60%. Integré la [API de Open-Meteo](https://open-meteo.com/) para índice UV y cobertura nubosa por hora — sin API key, gratis para uso no comercial.

La parte delicada: el índice UV de Open-Meteo *ya incluye la cobertura nubosa*. Si aplicas una penalización por nubes encima, la cuentas doble. Pillé este bug al notar que los tiempos de exposición en días nublados eran absurdamente altos. La corrección: aplicar el factor de nubes solo a las estimaciones teóricas (geometría solar), nunca a los datos reales de la API.

## Por Qué una PWA y No una App Nativa

Esta fue una decisión deliberada. Una calculadora de vitamina D necesita funcionar en cualquier dispositivo — iOS, Android, escritorio — y soy un desarrollador solo. Construir y mantener apps nativas para dos plataformas más una versión web estaba descartado.

Las [PWAs](https://en.wikipedia.org/wiki/Progressive_web_app) cierran la mayoría de la brecha que antes importaba:

- **Instalación**: "Añadir a pantalla de inicio" funciona en iOS y Android — sin app store, sin proceso de revisión, sin 99$/año de Apple Developer
- **Notificaciones push**: Soportadas en Android desde 2015 y [en iOS desde 16.4](https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/) (marzo 2023) — el último gran bloqueante desapareció
- **Offline**: Los service workers cachean todo lo necesario para la funcionalidad básica
- **Actualizaciones**: Despliegas en Vercel, los usuarios obtienen la nueva versión en la siguiente visita — sin fricción de "por favor actualiza la app"

Lo que *no* tienes: tracking de ubicación en segundo plano, integraciones con apps de salud (Apple Health, Google Fit), y presencia en la App Store para descubrimiento. Los dos primeros podrían importar para futuras funcionalidades (integración con wearables, tracking diario automático). El tercero es una desventaja real de distribución — la gente busca en app stores, no en la web.

Por ahora, el tradeoff compensa claramente. Si la app crece hasta necesitar APIs nativas (wearables, datos de salud), un enfoque híbrido con [Capacitor](https://capacitorjs.com/) o un wrapper nativo fino alrededor de la web app existente sería el siguiente paso natural — no una reescritura.

### Soporte Offline

Una calculadora de vitamina D es más útil cuando ya estás fuera — potencialmente sin señal. El service worker cachea todas las páginas y assets estáticos en la instalación, con estrategia network-first para contenido dinámico y una página de fallback offline.

### Notificaciones Push

Esta fue la funcionalidad que la hizo sentir más como una "app de verdad." Un cron de Vercel se ejecuta diariamente a las 8 AM UTC, obtiene datos UV reales para la ubicación guardada de cada suscriptor, calcula su ventana de síntesis personalizada y envía una notificación Web Push:

> *"Londres · 12 min para 1000 UI · Mejor hora: 13:00 (UVI 4.5) · Ventana: 11:00–15:00"*

La implementación usa claves VAPID con la librería `web-push`, y las suscripciones se almacenan en Supabase. Una trampa que me costó 53 días de notificaciones push rotas: `echo "$KEY" | vercel env add` añade un salto de línea que Vercel almacena literalmente dentro de la clave VAPID. La solución es `printf '%s'` en lugar de `echo`. Un comportamiento sutil de shell que corrompió silenciosamente una clave criptográfica.

## Seis Idiomas y 5.000+ Ciudades

La app soporta inglés, español, francés, alemán, ruso y lituano mediante `next-intl`. Cada fichero de idioma tiene ~480 líneas cubriendo etiquetas de UI, descripciones de tipos de piel Fitzpatrick y un FAQ educativo completo sobre la ciencia de la vitamina D.

La búsqueda de ciudades combina una base de datos integrada de 50+ ciudades principales con búsqueda full-text en Supabase (`pg_trgm`) sobre el dataset de 200K+ ciudades de GeoNames. Los nombres de ciudades están localizados — "Londres" en español, "Лондон" en ruso.

## Lo Que Aprendí

**Los artefactos de Claude están infravalorados como herramientas de prototipado.** El artefacto no era un mockup ni un diagrama — era código funcional con matemáticas solares reales. Esa ventaja inicial me permitió centrarme en decisiones de producto (¿qué visualizaciones? ¿qué flujo de usuario?) en vez de re-derivar trigonometría esférica.

**Canvas con D3 merece la pena para visualizaciones densas en datos.** Si renderizas menos de 1.000 elementos, quédate con SVG. Más allá de eso, Canvas es la única forma de mantener la fluidez en móvil.

**Las notificaciones push en PWA son sorprendentemente potentes y sorprendentemente frágiles.** La spec de Web Push funciona bien, pero la superficie operacional (claves VAPID, timing del cron, limpieza de suscripciones, manejo de errores para apps desinstaladas) es mayor de lo que el código sugiere.

**La fotobiología es más compleja que "sal 15 minutos."** La diferencia entre Fitzpatrick I (piel clara, céltica) y VI (pigmentación profunda) es un factor de 6× en MED. La exposición del área corporal importa más de lo que la gente piensa — solo cara y manos (10% del cuerpo) puede requerir 5× más tiempo que camiseta y pantalón corto (25%).

## Pruébala

**[VitaminD Explorer](https://getvitamind.app)** es gratuita, open source y funciona en cualquier dispositivo. Busca tu ciudad, configura tu tipo de piel y exposición, y mira exactamente cuándo y cuánto tiempo necesitas para tu vitamina D diaria.

El [artefacto original de Claude](https://claude.ai/public/artifacts/e1377c30-3b83-47bd-938f-6e107c21231a) sigue vivo si quieres ver dónde empezó todo.

---

*Construida con Next.js 16, D3.js, Supabase y Vercel. [Código en GitHub](https://github.com/JaviMaligno/vitamind).*
