---
title: "Creando un Skill Personalizado para Claude Code: Automatizando la Escritura de Blogs Bilingües"
description: "Cómo construí un skill de Claude Code que estandariza y automatiza la creación de artículos bilingües, asegurando consistencia entre contenido EN/ES."
pubDate: 2026-01-03
tags: ["Claude Code", "IA", "Automatización", "Skills"]
lang: es
translationKey: claude-code-skills-blog-writer
heroImage: "/blog/claude-code-skills.png"
---

Una de las funcionalidades más potentes de Claude Code es su capacidad de aprender tus flujos de trabajo específicos mediante **Agent Skills**. Hoy quiero compartir cómo construí un skill personalizado que automatiza la creación de artículos bilingües para esta web.

## ¿Qué Son los Agent Skills?

Los Agent Skills son una adición reciente al ecosistema de Claude. Según Anthropic, los skills son "carpetas que incluyen instrucciones, scripts y recursos que Claude puede cargar cuando es necesario."

Piensa en ellos como expertise empaquetado. En lugar de explicar tu flujo de trabajo cada vez, lo codificas una vez y Claude lo carga automáticamente cuando es relevante.

Características clave de los skills:

- **Carga Selectiva**: Claude solo accede a un skill cuando es relevante para la tarea
- **Componibles**: Múltiples skills pueden trabajar juntos sin problemas
- **Portables**: Funcionan en Claude apps, Claude Code y la API

En Claude Code específicamente, los skills personalizados están basados en el sistema de archivos—simplemente una carpeta con un archivo `SKILL.md` que Claude descubre automáticamente.

## El Problema: Contenido de Blog Inconsistente

Mi web soporta tanto inglés como español. Cada artículo necesita:

- Frontmatter coincidente en ambos archivos
- Un `translationKey` compartido para enlazar traducciones
- Tags traducidos correctamente (AI → IA, Automation → Automatización)
- Nombres de archivo y ubicaciones consistentes
- Misma fecha de publicación para lanzamiento sincronizado

Antes del skill, tenía que recordar todos estos requisitos cada vez. Los errores eran comunes—translation keys que no coincidían, campos olvidados, formato inconsistente.

## La Solución: Skill blog-writer

Creé un skill en `.claude/skills/blog-writer/SKILL.md` que codifica todas mis convenciones de escritura:

```yaml
---
name: blog-writer
description: Write bilingual blog articles for the personal website.
  Use when creating a new blog post, article, or writing content
  for the blog. Handles EN/ES translations, frontmatter, and
  content structure.
---
```

El skill define:

### Ubicaciones de Archivos
```
src/content/blog/en/[slug].md  # Inglés
src/content/blog/es/[slug].md  # Español
public/blog/[image-name].png   # Imágenes
```

### Frontmatter Requerido
```yaml
---
title: "Título del Artículo"
description: "Descripción SEO"
pubDate: 2025-01-03
tags: ["Tag1", "Tag2"]
lang: es  # o en
translationKey: slug-del-articulo
---
```

### Convenciones de Tags

El skill incluye una tabla de traducción para tags comunes:

| Inglés | Español |
|--------|---------|
| AI | IA |
| Automation | Automatización |
| Development | Desarrollo |
| Architecture | Arquitectura |

## Cómo Funciona en la Práctica

Cuando invoco el skill, Claude automáticamente:

1. Crea ambos archivos EN y ES con `translationKey` coincidente
2. Usa el formato de frontmatter correcto
3. Traduce tags según las convenciones
4. Sigue la estructura de contenido definida
5. Coloca imágenes en el directorio correcto

La invocación es simple:

```
/blog-writer Crear un artículo sobre construir servidores MCP
```

Claude carga el skill, entiende todos los requisitos y produce output consistente cada vez.

## Reutilizando Contenido de LinkedIn

Una funcionalidad que construí específicamente en el skill es la capacidad de convertir posts de LinkedIn en artículos completos. El skill incluye instrucciones para:

1. Obtener el contenido del post original
2. Descargar imágenes asociadas
3. Expandir el formato condensado en secciones comprensivas
4. Mantener la fecha de publicación original por autenticidad
5. Conservar el mensaje central mientras se añade profundidad

Esto maximiza el valor del contenido que ya he creado. Un post de LinkedIn de 200 palabras se convierte en un artículo técnico de 1500 palabras con ejemplos de código, explicaciones expandidas y optimización SEO adecuada.

## Creando Tus Propios Skills

La estructura es directa:

```
.claude/skills/
└── nombre-de-tu-skill/
    └── SKILL.md
```

El archivo `SKILL.md` contiene:

1. **Frontmatter**: Nombre y descripción (cómo Claude decide cuándo cargarlo)
2. **Instrucciones**: Flujo de trabajo detallado, convenciones y ejemplos
3. **Checklists**: Pasos de verificación antes de completar

La descripción en el frontmatter es crucial—determina cuándo Claude considera el skill relevante.

## Por Qué Esto Importa

Los skills representan un cambio en cómo trabajamos con asistentes de IA. En lugar de:

- Repetir instrucciones cada sesión
- Mantener documentación externa
- Detectar inconsistencias en revisión

Codificas tu expertise una vez y te beneficias de ello continuamente.

Para creación de contenido específicamente, esto significa:

- **Consistencia**: Cada artículo sigue la misma estructura
- **Eficiencia**: Sin tiempo gastado recordando convenciones
- **Calidad**: Checklists integrados detectan errores comunes
- **Escala**: Producir más contenido sin sacrificar estándares

## Próximos Pasos

Estoy explorando skills adicionales para otros flujos de trabajo repetitivos—documentación de proyectos, checklists de code review, procedimientos de despliegue. El patrón es el mismo: identificar un flujo que repites, codificarlo como skill y dejar que Claude maneje los detalles.

---

*Aprende más sobre Agent Skills en la [documentación oficial de Anthropic](https://claude.com/blog/skills) o explora el [repositorio de skills](https://github.com/anthropics/skills).*
