---
title: "Construyendo un Servidor MCP para Bitbucket: Conectando LLMs con tu Flujo DevOps"
description: "Cómo construí un servidor MCP completo con 58 herramientas para gestionar repositorios, pull requests y pipelines de Bitbucket mediante lenguaje natural."
pubDate: 2024-12-15
tags: ["MCP", "Bitbucket", "DevOps", "Claude", "IA"]
lang: es
translationKey: mcp-bitbucket
---

Después de buscar un MCP oficial de Atlassian sin encontrarlo, decidí construir el mío propio. Los MCPs comunitarios existentes para Bitbucket eran demasiado limitados—solo operaciones básicas de repositorio, sin soporte para pipelines, sin gestión de despliegues.

Necesitaba algo más completo para mi flujo de trabajo diario.

## Por Qué MCP Importa para DevOps

El Model Context Protocol (MCP) es un estándar que permite a los LLMs interactuar con sistemas externos a través de un conjunto definido de herramientas. En lugar de copiar y pegar entre tu IDE y la interfaz web de Bitbucket, puedes simplemente pedirle a tu asistente de IA que lo gestione.

El cambio de contexto es costoso. Cada vez que dejas tu editor para revisar un pipeline, hacer review de un PR o gestionar permisos de rama, pierdes el foco. MCP elimina esa fricción.

## Lo Que Construí

El [Servidor MCP para Bitbucket](https://github.com/JaviMaligno/mcp-server-bitbucket) expone **58 herramientas** cubriendo toda la API de Bitbucket:

### Pull Requests
- Crear, revisar, aprobar y mergear PRs
- Añadir comentarios inline en líneas específicas
- Ver diffs y comparar ramas

### Pipelines
- Lanzar builds en cualquier rama
- Monitorizar estado y logs de pipelines
- Gestionar variables de CI/CD

### Gestión de Repositorios
- Operaciones CRUD completas
- Restricciones de rama y reglas de protección
- Permisos de usuarios y grupos

### Navegación de Código
- Leer archivos sin clonar el repositorio
- Listar contenidos de directorios
- Comparar commits y ramas

### Despliegues
- Ver entornos de despliegue
- Seguimiento del historial de despliegues

## Casos de Uso Reales

Así es como lo uso a diario:

![MCP Bitbucket en acción con Claude Code](https://www.javieraguilar.ai/blog/mcp-bitbucket-demo.webp)

```
"Muéstrame los PRs abiertos y haz code review del #42"
```

```
"Lanza el pipeline en develop y avísame si falla"
```

```
"Lee el archivo config.py de la rama feature-x"
```

```
"Genera las release notes entre v1.0 y main"
```

El poder no está en ningún comando individual—está en la capacidad de encadenar operaciones naturalmente a través de la conversación.

## Implementación Técnica

El servidor está disponible tanto en TypeScript como en Python:

```bash
# TypeScript
npx mcp-server-bitbucket

# Python
pipx install mcp-server-bitbucket
```

La autenticación usa App Passwords de Bitbucket, que puedes crear en la configuración de tu cuenta. El servidor respeta los límites de tasa y maneja la paginación automáticamente.

## ¿Por Qué Bitbucket?

Aunque GitHub tiene mejor soporte nativo con Claude, muchos equipos enterprise siguen usando Bitbucket. Esta brecha en las herramientas fue exactamente la razón por la que construí esto—y por la que lo he publicado como open source para otros en la misma situación.

## Próximos Pasos

Estoy mejorando continuamente el servidor basándome en patrones de uso reales. Las adiciones recientes incluyen gestión de webhooks, operaciones con tags y mejor manejo de errores.

Si trabajas con Bitbucket y quieres integrarlo con Claude u otros LLMs compatibles con MCP, pruébalo. Las contribuciones y el feedback son bienvenidos.

---

*Echa un vistazo al [repositorio en GitHub](https://github.com/JaviMaligno/mcp-server-bitbucket) o [instala desde npm/PyPI](https://pypi.org/project/mcp-server-bitbucket/).*
