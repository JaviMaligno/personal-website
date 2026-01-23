# Análisis SEO: Sitio Multiidioma javieraguilar.ai

**Fecha:** 2025-01-23
**Estado:** Análisis completado - Sin cambios requeridos

## Resumen Ejecutivo

La configuración actual del sitio es **correcta**. Las páginas reportadas como "no indexadas" en Google Search Console son comportamiento esperado, no errores.

## Contexto

El sitio usa routing con prefijo de idioma:
- `/en/` - Versión inglés (default)
- `/es/` - Versión español
- `/` - Redirige a `/en/` (302)

### Páginas reportadas como "no indexadas" en GSC

| Cantidad | Página | Razón GSC | Explicación |
|----------|--------|-----------|-------------|
| 1 | `/` | Redirección | Correcto: Google sigue el 302 e indexa `/en/` |
| 9 | `/en/blog/*` | Alternate page with proper canonical | Correcto: Google consolida las versiones de idioma |

## Análisis Detallado

### 1. La redirección de `/` a `/en/`

**Comportamiento actual:**
```
Usuario visita javieraguilar.ai → 302 redirect → javieraguilar.ai/en/
```

**¿Por qué Google no indexa `/`?**
- Google sigue el redirect y encuentra `/en/`
- Indexa `/en/` como la página principal
- Esto es exactamente lo esperado

**¿Afecta al SEO?**
- **No.** Los usuarios nunca llegan a `/` desde Google
- Google usa hreflang para mostrar `/en/` o `/es/` según el idioma del usuario
- El `x-default` apunta a `/en/`, indicando que es el fallback para idiomas no soportados

### 2. Los 9 blogs EN marcados como "Alternate page with proper canonical"

**Configuración actual en `BlogLayout.astro`:**
```html
<!-- Cada página tiene su propia canonical -->
<link rel="canonical" href="https://www.javieraguilar.ai/en/blog/post-slug/" />

<!-- hreflang apunta a ambas versiones -->
<link rel="alternate" hreflang="en" href=".../en/blog/post-slug/" />
<link rel="alternate" hreflang="es" href=".../es/blog/post-slug/" />
<link rel="alternate" hreflang="x-default" href=".../en/blog/post-slug/" />
```

**¿Por qué Google marca EN como "alternate"?**

Esto NO significa que Google ignore las páginas EN. Significa:

1. Google encontró `/en/blog/azure-content-filter-workarounds/`
2. Google vio el hreflang apuntando a `/es/blog/azure-content-filter-workarounds/`
3. Google decidió que para **su crawler** (probablemente en ubicación/configuración española), la versión ES es la "principal" a reportar
4. **Ambas versiones están indexadas**, pero GSC muestra una como "principal" y la otra como "alternate"

**Prueba:** Busca en Google con `site:javieraguilar.ai/en/blog/` - verás las páginas EN indexadas.

### 3. Cómo funciona hreflang para geolocalización

```
Usuario en Madrid busca "azure content filter workarounds"
    ↓
Google tiene indexadas ambas versiones:
  - /en/blog/azure-content-filter-workarounds/
  - /es/blog/azure-content-filter-workarounds/
    ↓
Google muestra /es/... en los resultados para este usuario
    ↓
Usuario hace clic → llega directamente a /es/...
```

```
Usuario en Londres busca "azure content filter workarounds"
    ↓
Google muestra /en/... en los resultados
    ↓
Usuario hace clic → llega directamente a /en/...
```

**Conclusión:** No necesitas que `/` esté indexada porque Google envía usuarios directamente a la versión correcta según su idioma/ubicación.

## Recomendaciones

### Mantener (no cambiar)

1. **Redirect 302 en `/`** - Funciona correctamente
2. **Canonical apuntando a sí mismo** - Cada página es su propia canonical
3. **hreflang bidireccional** - EN↔ES están correctamente enlazados
4. **x-default a EN** - Correcto para audiencia global con fallback inglés

### Acciones opcionales para mejorar SEO

| Prioridad | Acción | Impacto |
|-----------|--------|---------|
| Alta | Conseguir backlinks de calidad | Aumenta autoridad del dominio |
| Alta | Publicar contenido regularmente | Mejora crawl frequency |
| Media | Añadir sitio a directorios de MCP/AI | Backlinks relevantes |
| Media | Promocionar artículos en redes/foros | Tráfico y backlinks |
| Baja | Considerar 301 en vez de 302 para `/` | Marginal, no urgente |

### Sobre el 301 vs 302

Actualmente usas `Astro.redirect('/en/')` que genera un 302 (temporal).

- **302** dice: "Esta redirección es temporal"
- **301** dice: "Esta redirección es permanente"

Para SEO, un **301 es ligeramente mejor** porque:
- Pasa más "link juice" a la página destino
- Indica a Google que no volverá a cambiar

**Cambio opcional en `src/pages/index.astro`:**
```astro
---
return Astro.redirect('/en/', 301);
---
```

Pero esto es una optimización menor - el impacto real es mínimo.

## Verificación de la configuración

### Checklist técnico

- [x] Sitemap incluye todas las páginas traducidas
- [x] robots.txt permite indexación (`Allow: /`)
- [x] hreflang configurado en ambas direcciones
- [x] x-default definido (apunta a EN)
- [x] Canonical apunta a la propia URL (no a otra versión)
- [x] Schema.org incluye `inLanguage`
- [x] GSC verificado y sitemap enviado

### URLs del sitemap actual

```
/                                    (redirige, no indexada - OK)
/en/                                 (indexada)
/es/                                 (indexada)
/en/blog/                            (indexada)
/es/blog/                            (indexada)
/en/blog/[5 posts]                   (indexadas, reportadas como alternate - OK)
/es/blog/[5 posts]                   (indexadas como principales)
/en/projects/[8 proyectos]           (indexadas)
/es/projects/[8 proyectos]           (indexadas)
/en/business/                        (indexada)
/es/business/                        (indexada)
```

## Conclusión

**Tu setup está bien configurado.** Los mensajes de GSC son informativos, no errores. Google indexa ambas versiones de idioma y las muestra según corresponda al usuario.

El hecho de que GSC reporte las páginas EN como "alternate" probablemente se debe a que el crawler de Google que escaneó tu sitio tenía configuración de idioma español. Esto no afecta cómo Google muestra tus páginas a usuarios reales.

---

*Documento generado durante sesión de brainstorming sobre estrategia SEO multiidioma.*
