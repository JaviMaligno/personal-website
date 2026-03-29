---
title: "Playwright CLI vs Scripts: Cómo Deben Testear los Agentes de IA"
description: "Por qué la mayoría de los tests con IA deberían ser scripts reproducibles, no exploración con CLI — y cómo usar cada enfoque eficazmente, basado en experiencia real de automatización de despliegues."
pubDate: 2026-03-29
tags: ["Agentes IA", "Playwright", "Testing", "Automatización", "Productividad"]
lang: es
translationKey: playwright-cli-vs-scripts-ai-agents
heroImage: "/blog/playwright-cli-vs-scripts-ai-agents.png"
---

Hay un patrón creciente en el desarrollo agéntico: darle un navegador a un agente de IA y dejar que se las apañe. Herramientas como Playwright CLI, browser-use y el computer use de Claude Code facilitan apuntar un LLM a una web y decir "testea esto."

Funciona. Hasta que deja de funcionar.

Tras meses construyendo un sistema automatizado de despliegue de microservicios donde los agentes de IA despliegan, configuran y verifican servicios end-to-end, he llegado a un modelo mental claro sobre cuándo usar Playwright CLI (interactivo, guiado por LLM) vs scripts estándar de Playwright (determinísticos, reproducibles). La distinción importa más de lo que la mayoría piensa.

## Los Dos Modos

### Playwright CLI: Modo Exploración

El CLI es conversacional. El agente navega, toma snapshots, lee el DOM, decide qué hacer. Cada interacción es una llamada al LLM.

```bash
# El agente abre una página, toma snapshot, lee el YAML, decide la siguiente acción
playwright-cli -s=verify open https://app.example.com --headed
playwright-cli -s=verify snapshot
playwright-cli -s=verify click e{ref-del-snapshot}
playwright-cli -s=verify fill e{ref-input} "término de búsqueda"
```

Así funciona mi skill `verify-test` en el pipeline del [Data Source Automator](https://www.javieraguilar.ai/es/projects/data-source-automator). Cuando testeo manualmente un microservicio recién desplegado con Claude Code, el agente:

1. Abre la plataforma Verify en un navegador
2. Toma un snapshot (genera un YAML con refs de elementos)
3. Lee el snapshot para encontrar los elementos correctos
4. Rellena formularios, hace clic en botones, navega
5. Evalúa resultados y decide el siguiente paso

Cada paso es una inferencia del LLM. El agente se adapta — si falta un dropdown, investiga. Si la auth caduca, re-loguea. Si los resultados parecen incorrectos, profundiza.

**Esto no es testing. Es exploración.**

### Playwright Scripts: Modo Reproducible

Los scripts son determinísticos. Misma entrada, mismos pasos, mismas aserciones. Sin LLM involucrado en la ejecución.

```typescript
import { test, expect } from "@playwright/test";

test("Verify service search returns results", async ({ page }) => {
  await page.goto("https://app.example.com");
  await page.fill('[data-testid="search-input"]', "ACME Corp");
  await page.click('[data-testid="search-button"]');

  const results = page.locator('[data-testid="result-row"]');
  await expect(results).toHaveCount({ minimum: 1 });

  const firstResult = results.first();
  await expect(firstResult).toContainText("ACME");
});
```

Sin snapshots, sin parsear YAML, sin razonamiento del LLM sobre qué hacer. Solo código.

## Por Qué Importa Esta Distinción para Agentes de IA

Cuando construí el sistema de automatización de despliegues por primera vez, todo usaba el enfoque CLI. El agente LLM:

1. Desplegaba el servicio (git tag, actualización de config-deploy, sync de ArgoCD)
2. Ejecutaba checks de infraestructura (pods, health, swagger, etcd)
3. Abría un navegador vía Playwright CLI
4. Navegaba la UI de la plataforma para configurar y testear el servicio
5. Evaluaba resultados y reportaba

Funcionaba. Pero aparecieron tres problemas rápidamente:

### 1. El consumo de tokens se disparó

Cada interacción con Playwright CLI requiere que el LLM:
- Lea el YAML completo del snapshot (a menudo más de 500 líneas)
- Razone sobre qué elemento interactuar
- Formule el siguiente comando
- Evalúe el resultado

Para un flujo típico de verificación (login → configurar → buscar → validar resultados → verificar detalles), son 15-20 llamadas al LLM con contexto grande. **A escala, testeando más de 50 microservicios, los tokens se quemaban a toda velocidad.**

### 2. La variabilidad mataba la fiabilidad

La misma prueba ejecutada dos veces podía tomar caminos diferentes. El LLM podía:
- Hacer clic en un elemento diferente si el snapshot variaba ligeramente
- Interpretar resultados de forma distinta según el estado de la ventana de contexto
- Confundirse con cambios de UI que no afectaban la funcionalidad

Un test que pasaba el lunes podía fallar el martes — no porque el servicio se rompiera, sino porque el agente razonó diferente.

### 3. Los flujos estables no necesitan razonamiento

Tras las primeras ejecuciones, noté que el patrón de verificación era siempre el mismo:
1. Login (o restaurar estado de auth)
2. Navegar a configuración
3. Configurar autodiscovery
4. Crear una aplicación
5. Ejecutar una búsqueda
6. Validar que los resultados tienen datos
7. Abrir una vista de detalle
8. Capturar screenshots de evidencia

Esto no necesita un LLM. Necesita un script.

## La Arquitectura Final

```
┌─────────────────────────────────────────────────┐
│           Pipeline de Despliegue                 │
│                                                  │
│  Deploy ──► Checks Infra ──► Tests Browser       │
│                                  │               │
│                          ┌──────┴──────┐         │
│                          │             │         │
│                    Playwright     Playwright      │
│                    Scripts        CLI             │
│                    (defecto)    (fallback)        │
│                          │             │         │
│                    Determinístico LLM-driven      │
│                    Rápido        Adaptable         │
│                    Pocos tokens  Muchos tokens     │
│                          │             │         │
│                          └──────┬──────┘         │
│                                 │                │
│                          El LLM recibe           │
│                          solo outputs            │
└─────────────────────────────────────────────────┘
```

**Los scripts van primero.** Manejan el happy path: login, navegar, buscar, asertar, screenshot. El agente LLM orquestador recibe solo la salida del test (pass/fail + screenshots), no el DOM.

**El CLI entra como fallback.** Cuando un script falla inesperadamente — un cambio de UI, un modal nuevo, un elemento que se movió — el agente cambia a modo CLI. Ahora puede explorar, tomar snapshots, razonar sobre qué cambió, y arreglar el problema o reportarlo.

Este es el insight clave: **el LLM no necesita ver cada carga de página y cada árbol DOM. Solo necesita los resultados — y la capacidad de profundizar cuando algo va mal.**

## Ejemplo Real: El Patrón de Tests Generados

En el sistema de demo-video, llevé esto más lejos. Los tests se auto-generan a partir de definiciones de escenas:

```typescript
// scenes/uk-hmrc-supervised-business-register-video-a.ts
// Definiciones de escenas: qué hacer, en qué orden, con qué datos
export const SCENE_CONFIGS = [
  { id: "login", name: "Login to platform" },
  { id: "navigate-settings", name: "Open service configuration" },
  { id: "configure-autodiscovery", name: "Enable the service" },
  { id: "create-application", name: "Create test application" },
  { id: "execute-search", name: "Run company search" },
  { id: "validate-results", name: "Check search results" },
];

// Cada escena es una función: (page: Page) => Promise<void>
export const SCENES: Record<string, (page: Page) => Promise<void>> = {
  "login": async (page) => {
    await page.goto("https://demo1-dev.simplekyc.com");
    // ... pasos determinísticos
  },
  // ...
};
```

El spec generado es puro boilerplate — itera escenas, registra timestamps, guarda output. **Cero intervención del LLM en runtime.**

```typescript
// Auto-generado — no editar manualmente
test("Record UK HMRC Supervised Business Register", async ({ browser }) => {
  const context = await browser.newContext({
    recordVideo: { dir: VIDEO_DIR, size: { width: 1280, height: 720 } },
    viewport: { width: 1280, height: 720 },
  });

  const page = await context.newPage();
  for (const config of SCENE_CONFIGS) {
    const sceneFn = SCENES[config.id];
    await sceneFn(page);
  }
  await context.close();
});
```

El rol del LLM: **escribió** estas escenas inicialmente (usando exploración CLI para entender la UI). Luego se apartó y dejó que los scripts ejecutaran.

## Cuándo Usar Cada Uno

| | Playwright CLI | Playwright Scripts |
|---|---|---|
| **Propósito** | Exploración, debugging, flujos desconocidos | Verificación, regresión, flujos conocidos |
| **Intervención LLM** | Cada paso | Ninguna en runtime |
| **Coste en tokens** | Alto (snapshots + razonamiento por acción) | Casi cero (el agente solo lee output) |
| **Reproducibilidad** | Baja (el LLM puede tomar caminos distintos) | Alta (mismo código, mismos pasos) |
| **Adaptabilidad** | Alta (maneja UI inesperada) | Baja (rompe con cambios de UI) |
| **Velocidad** | Lenta (latencia LLM por paso) | Rápida (velocidad nativa del navegador) |
| **Ideal para** | Primeras ejecuciones, debugging, navegación | Verificación repetida, CI/CD, captura de evidencia |

## El Modelo Mental

Piénsalo como un ingeniero QA humano:

- **Primera vez testeando una feature?** Hace clic por ahí, explora, toma notas. Esto es modo CLI.
- **Escribiendo el test de regresión?** Scriptea los pasos exactos que acaba de explorar. Esto es modo script.
- **El test falla inesperadamente?** Vuelve a exploración manual para entender por qué. Modo CLI otra vez.

Un agente de IA debería funcionar igual. **Explora con el CLI, codifica con scripts, vuelve al CLI cuando los scripts fallan.**

## Directrices Prácticas

1. **Empieza con exploración CLI** cuando el agente de IA encuentre una UI o flujo nuevo. Que haga snapshot, razone, navegue.

2. **Cuando el flujo sea estable** (funciona 3+ veces consistentemente), genera un script de Playwright. El propio agente puede escribirlo — ya conoce los selectores y el flujo de su exploración CLI.

3. **En pipelines automatizados**, siempre usa scripts como runner principal de tests. El LLM orquestador recibe `stdout` (pass/fail, screenshots), no árboles DOM.

4. **Mantén el CLI como fallback**. Cuando un script falle, el agente puede cambiar a modo CLI para diagnosticar: "El botón de búsqueda se movió — déjame tomar un snapshot y encontrarlo."

5. **Nunca pongas tests solo-CLI en CI**. Si tu agente de IA hace 20 llamadas al LLM por ejecución de test en CI, estás pagando por razonamiento que no necesitas.

## Navegación vs Testing

Una distinción más que vale la pena hacer: **la navegación pura es conceptualmente diferente del testing.**

Si un agente de IA necesita navegar la web — investigar un tema, rellenar un formulario, extraer datos de una página — el CLI es la herramienta correcta. Eso no es testing, es interacción. El agente necesita razonar sobre lo que ve.

Pero en el momento en que estás verificando que un flujo conocido produce resultados esperados — eso es testing. Scriptéalo.

---

El patrón es simple: **explora con CLI, verifica con scripts, vuelve al CLI cuando algo rompa.** Tus agentes de IA serán más rápidos, más baratos y más fiables.

*Este enfoque está corriendo en producción para más de 50 despliegues de microservicios. El ahorro en tokens al cambiar verificaciones repetitivas a scripts fue suficientemente significativo como para justificar el refactor en la primera semana.*

---

*Para profundizar en el enfoque basado en scripts — incluyendo grabación de escenas, generación de voz y ensamblaje de vídeo — lee [Hice un Vídeo Demo de Producto Enteramente con IA](https://www.javieraguilar.ai/es/blog/automated-demo-recording-playwright).*
