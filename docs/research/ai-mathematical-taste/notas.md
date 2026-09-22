# Cuando la IA elija las preguntas — notas editoriales

Fecha de contraste: 21 de septiembre de 2026.

Textos vigentes:
- [Español](../../../src/content/blog/es/when-ai-chooses-the-questions.md)
- [English](../../../src/content/blog/en/when-ai-chooses-the-questions.md)

Fuentes primarias:
- [OpenAI, anuncio del 21 de septiembre](https://openai.com/index/advisory-group-on-mathematics-and-ai/).
- [OpenAI, Navier–Stokes, 8 de septiembre](https://openai.com/index/navier-stokes-solution/).
- [Clay, estado de evaluación, 11 de septiembre](https://www.claymath.org/news/navier-stokes-announcement/).
- [Davies et al., Nature, 2021](https://www.nature.com/articles/s41586-021-04086-x).
- [Thurston, 1994](https://arxiv.org/abs/math/9404236).
- [Carta de matemáticos, 11 de septiembre de 2026](https://mathandai.org/).
- [arXiv 2022, página impresa 9](https://info.arxiv.org/about/reports/2022_arXiv_annual_report.pdf).
- [arXiv 2025, páginas impresas 10–11](https://info.arxiv.org/about/reports/2025_arXiv_annual_report.pdf). Incluye el total de 2024.

- [Estadísticas mensuales de arXiv](https://arxiv.org/stats/monthly_submissions) y [CSV oficial](https://arxiv.org/stats/get_monthly_submissions). Copia consultada el 21 de septiembre de 2026: `arxiv-monthly-submissions-2026-09-21.csv`.

Decisiones de rigor:
- La cifra de más de cien es una afirmación de OpenAI. El comunicado no aporta el inventario ni las pruebas.
- Se distingue demostración publicada del proceso de evaluación de Clay; no se presenta un premio concedido.
- arXiv, contexto anual: 185692 envíos nuevos en 2022 y 284486 en 2025; +53.2031536 %.
- Figura actualizada: enero–agosto en todos los años. Totales 2022–2026: 120343, 133741, 158079, 181595, 230322. Cambio 2025–2026: +26.8328 %. Sumas de la columna `submissions` del CSV oficial; ocho meses por año. Septiembre de 2026 se excluye porque está incompleto. Todas las disciplinas. No revisiones, no revisión por pares, no estimación causal de IA.
- El dato personal de un paper antes y cuatro después procede de Javier en esta conversación. No se infieren tiempos iguales, revisión por pares, multiplicador de productividad ni calidad comparable.
- Las predicciones sobre criterio propio son hipótesis argumentadas, no capacidades demostradas por los anuncios.
- La crítica institucional se dirige a usar volumen de publicaciones como sustituto de aportación intelectual.

Contexto incorporado: CLAUDE.md; docs/blog-publishing.md; memoria de Claude blog-article-scope.md; artículos previos sobre Navier–Stokes, investigación asistida y cuánto seguir sabiendo.

Figuras: scripts/blog/when-ai-chooses-the-questions-figures.mjs genera cuatro PNG, con textos por idioma. La comparación de tres capacidades es conceptual; el gráfico de arXiv muestra totales de enero–agosto con eje cero, calculados desde la copia del CSV. Ambos se insertan como PNG para que sobrevivan al cross-posting.

Cabecera: generada con la herramienta integrada image_gen; prompts inicial y de edición en docs/marketing/image-prompts.md. La edición elimina afirmaciones matemáticas inventadas del arte ilustrativo.

Estado editorial: aprobado para programar el 23 de septiembre de 2026. Frontmatter de ambos idiomas ajustado a esa fecha. Rama de publicación: `blog/when-ai-chooses-the-questions`; entrada en `.github/publish-schedule.json` de `main`. La consulta de fuentes y datos conserva su fecha del 21 de septiembre.

Verificación: npm run build completado; ambas páginas presentes en dist/client. Enlaces locales y cinco assets comprobados. Figuras ES inspeccionadas dentro del artículo; figuras EN inspeccionadas en el navegador. Lectura móvil comprobada con viewport de 390 px, sin desbordamiento horizontal en ambas versiones. Vista previa servida desde dist/client en http://127.0.0.1:4321.
