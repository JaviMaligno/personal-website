---
title: "Escalando tu flujo de trabajo: Equipos de Agentes en Claude Code con tmux"
description: "Cómo coordinar múltiples agentes de IA trabajando en paralelo usando la nueva funcionalidad Agent Teams de Claude Code dentro de una sesión de tmux."
pubDate: 2026-02-07
tags: ["Claude Code", "Agentes IA", "tmux", "Flujo de trabajo"]
lang: es
translationKey: claude-code-agent-teams
heroImage: "/blog/claude-code-agent-teams.png"
---

Recientemente he estado explorando **Agent Teams**, una nueva funcionalidad de Claude Code que te permite coordinar múltiples agentes trabajando en paralelo. Es un cambio radical para tareas que requieren roles distintos o hipótesis competidoras.

En este post, te mostraré mi configuración usando `tmux` en macOS para gestionar un equipo de agentes revisando un ensayo.

## Míralo en acción

Grabé una demo rápida mostrando cómo los agentes interactúan y reportan sus resultados.

<div style="position: relative; padding-bottom: 62.5%; height: 0;"><iframe src="https://www.loom.com/embed/ed936584c30a43bbb47a0ae757fb0341?sid=9b68831f-0402-4fc8-8092-2cb918349071" frameborder="0" webkitallowfullscreen mozallowfullscreen allowfullscreen style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"></iframe></div>

## El caso de uso: Revisión de ensayo multiperspectiva

Tenía un ensayo que necesitaba una revisión exhaustiva. En lugar de pedirle a un solo agente que "revisara todo" (lo que a menudo lleva a feedback genérico), quería asignar roles específicos:
*   **Estilo y Tono**: Verificar la consistencia de la voz.
*   **Estructura**: Asegurar el flujo lógico.
*   **Contenido**: Verificar argumentos y referencias.

Aquí es donde brillan los Agent Teams. Puedes instanciar múltiples "compañeros de equipo", cada uno con un prompt y contexto específico, todos coordinados por un agente "líder".

## La configuración: Claude Code + tmux

Aunque Claude Code funciona bien en una terminal estándar, realmente cobra vida dentro de `tmux`, especialmente para Agent Teams.

1.  **Inicia una sesión de tmux**: Esto te permite dividir paneles y gestionar múltiples instancias de terminal fácilmente.
    ```bash
    tmux new -s agents
    ```
2.  **Lanza Claude Code**:
    ```bash
    claude
    ```
3.  **Inicializa el equipo**:
    Empecé haciendo una lluvia de ideas con Claude sobre la mejor manera de estructurar el equipo. Una vez acordamos los roles, simplemente le dije "start the team" (inicia el equipo).

## Cómo funcionan los Agent Teams

Cuando inicializas un equipo, Claude (el "líder") genera sesiones separadas para cada compañero. En `tmux`, esta visualización es fantástica porque puedes verlos activarse en paneles paralelos (aunque nota: en algunos sistemas, la gestión automática de paneles puede ser complicada, así que podrías necesitar cambiar o redimensionar manualmente).

### Coordinación y Permisos

El agente "Líder" actúa como coordinador. Asigna tareas a los compañeros y estos le reportan.
*   **Ejecución Paralela**: Todos los agentes trabajan al mismo tiempo. Mientras el agente de "Estilo" lee la introducción, el de "Estructura" analiza la conclusión.
*   **Comunicación Inter-Agente**: ¡Pueden hablar entre ellos! Si el agente de Contenido encuentra una referencia faltante que afecta al argumento, puede avisar al agente de Estructura.
*   **Permisos**: Es posible que necesites aprobar permisos de herramientas (como escritura de archivos) para cada agente inicialmente, pero una vez están corriendo, son bastante autónomos.

## Resultados y Reportes

En mi flujo de trabajo, pedí a cada agente que escribiera un informe sobre su dominio específico.
*   Actualizaban su estado en tiempo real.
*   Una vez terminados, "reportaban" a la sesión principal.
*   El agente Líder compilaba entonces sus hallazgos en un resumen final.

## ¿Cuándo usar Agent Teams?

Este flujo de trabajo no es para todo. Si tu tarea es estrictamente secuencial (el Paso B necesita que el Paso A esté 100% terminado), un solo agente podría ser mejor.

**Los Agent Teams son mejores para:**
1.  **Trabajo Paralelizable**: Revisiones de código, refactorizaciones de múltiples archivos o auditorías de contenido exhaustivas.
2.  **Interdependencia**: Donde los agentes podrían necesitar corregirse o informarse mutuamente (ej: "Arreglé la API, por favor actualiza el frontend").
3.  **Tareas basadas en Roles**: Cuando necesitas distintos "expertos" (ej: un "Experto en Seguridad" y un "Experto en Rendimiento" revisando el mismo PR).

## Pensamientos finales

La combinación de `tmux` y los Agent Teams de Claude Code crea una sensación de "centro de comando" muy potente. Transforma la IA de un chatbot a una fuerza laboral coordinada.

Si estás en macOS o Linux, pruébalo. Es un vistazo al futuro de los flujos de trabajo agénticos.
