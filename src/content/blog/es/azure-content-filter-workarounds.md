---
title: "El Filtro de Contenido de Azure OpenAI: Cuando el Teatro de Seguridad Bloquea el Trabajo Real"
description: "Cómo el filtro de contenido de Azure bloquea herramientas legítimas de automatización basándose en palabras, no en riesgo real—y soluciones simples que exponen el fallo."
pubDate: 2025-10-09
tags: ["IA", "Azure", "OpenAI", "Seguridad", "Function Calling"]
lang: es
translationKey: azure-content-filter-workarounds
---

Mientras construía herramientas de automatización de navegador con Azure OpenAI, descubrí algo frustrante: el filtro de contenido bloquea instrucciones perfectamente seguras basándose en la elección de palabras, no en el riesgo real.

No se trata de evadir medidas de seguridad legítimas. Se trata de un filtro que no puede distinguir entre intención maliciosa y terminología estándar de desarrollo.

## El Problema

Al definir herramientas para function calling, ciertos términos activan el filtro de contenido de Azure incluso cuando el contexto es completamente benigno:

- `run script` → Bloqueado
- `click element` → Bloqueado
- `fill form field` → Bloqueado

Estas son operaciones estándar para cualquier herramienta de automatización de navegador. Playwright, Puppeteer, Selenium—todas usan exactamente esta terminología. Pero el filtro de Azure las trata como amenazas.

## La Solución

La solución es vergonzosamente simple: usar sinónimos neutrales.

| Término Bloqueado | Alternativa Aceptada |
|-------------------|---------------------|
| `run script` | `process dynamic content` |
| `click element` | `activate page item` |
| `fill form field` | `update an input area` |
| `execute code` | `evaluate expression` |
| `inject` | `insert` |

La misma intención con lenguaje neutral pasa instantáneamente.

## Por Qué Importa

Esto revela algo importante sobre cómo funciona el filtro: analiza los nombres y descripciones de las herramientas como parte del prompt. Es coincidencia de patrones sobre palabras clave, no análisis de riesgo real.

Una herramienta llamada `clickElement` que automatiza envíos de formularios es bloqueada. La misma herramienta llamada `activatePageItem` haciendo exactamente lo mismo pasa sin problemas. El filtro no proporciona seguridad adicional—solo obliga a los desarrolladores a usar eufemismos.

## Comparación con Google Gemini

Probé las mismas definiciones de herramientas con los modelos Gemini de Google. Ninguna fricción con el lenguaje procedimental. Las herramientas funcionaron exactamente como se esperaba sin necesidad de sanitizar el vocabulario.

No se trata de que un proveedor sea "menos seguro". Se trata de que Azure implementa teatro de seguridad que incomoda a desarrolladores legítimos mientras proporciona protección real mínima.

## El Problema de Fondo

Cualquiera con intención maliciosa simplemente usará los eufemismos. El filtro no detiene a los malos actores—solo añade fricción para casos de uso legítimos.

La seguridad real viene de:
- Entender el contexto y la intención
- Límites de tasa y monitorización
- Autenticación de usuarios y trazas de auditoría
- Términos de servicio claros con aplicación

El bloqueo por palabras clave es el equivalente en seguridad a prohibir la palabra "cuchillo" en sitios web de cocina.

## Consejos Prácticos

Si estás construyendo herramientas con function calling de Azure OpenAI:

1. **Audita los nombres de tus herramientas** buscando palabras que disparen el filtro antes del despliegue
2. **Usa terminología neutral y abstracta** en las descripciones
3. **Prueba con llamadas reales a la API** pronto—el playground puede comportarse diferente
4. **Documenta las traducciones** para que tu equipo entienda el mapeo

Aquí hay un ejemplo de definición de herramienta sanitizada:

```json
{
  "name": "activatePageItem",
  "description": "Activates an interactive item on the page at the specified coordinates",
  "parameters": {
    "type": "object",
    "properties": {
      "x": { "type": "number", "description": "Horizontal position" },
      "y": { "type": "number", "description": "Vertical position" }
    }
  }
}
```

En lugar de lo más natural:

```json
{
  "name": "clickElement",
  "description": "Clicks an element on the page at the specified coordinates",
  "parameters": { ... }
}
```

## Conclusión

El filtro de contenido de Azure para function calling necesita refinamiento. La coincidencia de patrones sobre palabras clave sin análisis de contexto crea fricción para los desarrolladores mientras proporciona un beneficio de seguridad mínimo.

Hasta que eso cambie, la solución es simple: habla en eufemismos. Tu herramienta de automatización de navegador no "hace clic en botones"—"activa elementos interactivos de la página".

---

*¿Construyendo herramientas de IA que necesitan automatización de navegador? He navegado estas restricciones extensamente. [Contacta conmigo](/es/#contact) si enfrentas desafíos similares.*
