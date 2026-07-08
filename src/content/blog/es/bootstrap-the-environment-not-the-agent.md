---
title: "Prepara el Entorno, No al Agente"
description: "Por qué los repositorios que se ejecutan en cloud workspaces y sesiones de IA necesitan un bootstrap reproducible para dependencias de sistema, tests y builds."
pubDate: 2026-07-08
tags: ["Agentes IA", "Cloud", "Automatización", "DevEx", "Claude Code"]
lang: es
translationKey: bootstrap-the-environment-not-the-agent
heroImage: "/blog/bootstrap-cloud-environments.png"
repoUrl: "https://github.com/JaviMaligno/code-world-models"
---

Hace poco me encontré repitiendo el mismo ciclo con Claude Code en una sesión remota:

1. Pedirle que hiciera un cambio.
2. Ver cómo intentaba ejecutar el build o los tests.
3. Ver fallar el entorno porque faltaba una dependencia del sistema.
4. Decirle: "usa `apt-get` e instala esto".
5. Repetirlo en la siguiente sesión limpia.

El problema no era Claude. Tampoco era LaTeX, Python o el build en sí. El problema era que una parte del conocimiento operativo del proyecto vivía en una conversación, no en el repo.

En mi caso concreto, el repo era [Code World Models](https://github.com/JaviMaligno/code-world-models). El proyecto tiene tests Python, pero también compila un paper en LaTeX. En mi laptop todo estaba instalado. En CI también, porque el workflow de GitHub Actions instalaba TeX Live antes de compilar. Pero una sesión remota de Claude Code arrancaba como un entorno nuevo y no tenía por qué saber que `pdflatex` era parte real del contrato del repo.

La solución fue pequeña: un hook de inicio de sesión que prepara el entorno antes de que el agente lo necesite.

Pero el principio es más grande: **prepara el entorno, no al agente**.

## El Antipatrón: Dependencias en el Prompt

Cuando trabajamos localmente, acumulamos estado sin darnos cuenta. Tenemos paquetes del sistema, CLIs, credenciales, caches, extensiones, fuentes, navegadores, binarios y toolchains que no aparecen en `package.json`, `pyproject.toml` o `requirements.txt`.

Ese estado se vuelve invisible porque el proyecto "funciona en mi máquina".

En entornos cloud, ese supuesto se rompe. Y con agentes de IA se rompe antes, porque el agente intenta cerrar el loop completo:

- cambia código;
- ejecuta tests;
- compila docs;
- abre navegadores;
- genera screenshots;
- publica artefactos;
- verifica el resultado final.

Si falta un binario, el agente suele hacer lo razonable: diagnosticar, buscar una instalación, probar de nuevo. Pero eso consume tiempo, tokens y atención. Peor aún: si la solución queda solo en el chat, no mejora el siguiente entorno.

Decirle a un agente "instala TeX Live antes de compilar" es memoria operacional manual. Ponerlo en el repo es infraestructura.

## El Caso Real: LaTeX y Python en un Entorno Remoto

En Code World Models, el paper vive en `docs/paper/main.tex` y se valida con un script:

```bash
bash scripts/check_latex.sh
```

En CI, la dependencia estaba declarada en `.github/workflows/ci.yml`:

```yaml
- name: Install TeX Live
  run: |
    sudo apt-get update
    sudo apt-get install -y --no-install-recommends \
      texlive-latex-base texlive-latex-recommended texlive-latex-extra \
      texlive-fonts-recommended texlive-science texlive-bibtex-extra biber
```

Eso protegía GitHub Actions, pero no necesariamente una sesión remota de trabajo.

Así que añadí un hook `SessionStart` para Claude Code:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/session-start.sh"
          }
        ]
      }
    ]
  }
}
```

Y el script hace tres cosas importantes:

```bash
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

echo '{"async": true, "asyncTimeout": 300000}'

if ! command -v pdflatex >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y --no-install-recommends \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-latex-extra \
    texlive-fonts-recommended
fi

python -m pip install -e ".[dev]"
```

Primero, no hace nada en local. Mi laptop ya tiene lo que necesita, y no quiero que un hook de agente toque mi máquina sin motivo.

Segundo, arranca de forma asíncrona. La primera versión del hook era síncrona, pero en este repo el build del paper suele ocurrir al final, después de hacer los cambios de código y texto. No necesito bloquear el inicio de la sesión esperando a que termine TeX Live; necesito que esté listo cuando llegue el momento de compilar.

Tercero, es idempotente. Si `pdflatex` ya existe, no reinstala el toolchain.

Cuarto, usa `python -m pip`, no `pip` a secas, para instalar dependencias en el mismo intérprete que luego ejecutará `python -m pytest`. Ese detalle evita una clase muy aburrida de errores donde `pip` y `python` apuntan a entornos distintos.

El resultado no es espectacular. Precisamente por eso es bueno. La siguiente vez que el agente entra en el repo remoto, el entorno se prepara solo y el agente puede gastar su razonamiento en el cambio real.

## Esto No Va Solo de Agentes

El mismo principio aplica a cualquier entorno efímero:

- GitHub Codespaces;
- Dev Containers;
- Gitpod;
- runners de CI;
- sandboxes de Vercel o similar;
- máquinas temporales para demos;
- entornos internos de onboarding;
- sesiones remotas de agentes.

La diferencia con IA es que el coste de no hacerlo se vuelve más visible. Un humano puede recordar "ah, aquí siempre hay que instalar `libpq-dev`". Un agente puede inferirlo, pero no debería tener que redescubrirlo en cada sesión.

Los cloud workspaces convierten el entorno en algo desechable. Los agentes convierten el ciclo build-test-fix en algo mucho más frecuente. Juntos, hacen que la preparación reproducible deje de ser un lujo y se vuelva parte del contrato del repositorio.

## Qué Debería Vivir en el Bootstrap

No todo pertenece al script de inicio. Si metes demasiado, el entorno se vuelve lento, opaco y frágil. Pero hay una categoría clara de cosas que sí encajan:

- paquetes del sistema necesarios para compilar o testear;
- CLIs usadas por scripts del repo;
- navegadores o dependencias nativas para tests end-to-end;
- toolchains documentales como LaTeX, Pandoc o Graphviz;
- instalación editable del paquete local;
- comprobaciones rápidas de versión;
- setup de caches o directorios temporales.

La regla práctica que uso:

**Si el agente, CI o un nuevo desarrollador necesita pedirlo manualmente para ejecutar el flujo básico, debería estar declarado en el repo.**

No necesariamente en un hook de Claude. Puede ser un `devcontainer.json`, un Dockerfile, un script `scripts/bootstrap.sh`, un Makefile, una definición de Nix, un workflow reusable o una combinación. La herramienta exacta importa menos que la propiedad: el repo tiene que saber preparar su propio entorno.

## Un Buen Bootstrap Tiene Seis Propiedades

### 1. Es idempotente

Debe poder ejecutarse muchas veces sin romper nada. Comprueba antes de instalar:

```bash
if ! command -v pdflatex >/dev/null 2>&1; then
  apt-get install ...
fi
```

Los agentes van a reintentar. Los humanos también. Diseña para eso.

### 2. Distingue local de remoto

No todos los entornos necesitan el mismo tratamiento. Mi hook sale inmediatamente si no está en una sesión remota:

```bash
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi
```

Esa condición evita convertir el bootstrap en una fuente de sorpresas locales.

### 3. Reutiliza el contrato de CI

Si CI instala TeX Live, el entorno remoto también debería instalar TeX Live. Si CI corre `pip install -e ".[dev]"`, el agente debería preparar lo mismo. La consistencia importa más que la elegancia.

Lo ideal es no tener dos listas divergentes de paquetes. A veces se puede factorizar en un script común. A veces el workflow de CI y el hook remoto duplican unas pocas líneas. Lo importante es revisar que no se separen semánticamente.

### 4. Elige bien entre síncrono y asíncrono

Hay pasos que pueden correr en background, pero no todos. En mi caso, el hook puede arrancar asíncrono porque el PDF se compila al final del flujo, mucho después del inicio de sesión. Eso no sería aceptable para una dependencia que los tests necesitan en los primeros segundos.

La regla es simple: si el siguiente comando probable depende del setup, hazlo síncrono y falla rápido. Si el setup prepara una herramienta que se usará más tarde, puede ser asíncrono y ahorrarte latencia al arrancar la sesión.

El bootstrap no debe esconder errores que hacen inválido el entorno.

### 5. Falla de forma visible cuando es bloqueante

Asíncrono no significa silencioso. Si una dependencia es obligatoria, el flujo que la usa tiene que fallar con un error claro si el setup no terminó o no pudo completarse. En este caso, `scripts/check_latex.sh` sigue siendo el guard real: cuando llega el momento de compilar, valida que el toolchain existe.

### 6. Es conservador con privilegios y red

Un hook de inicio no es un buen sitio para ejecutar descargas arbitrarias. Evita `curl | bash` salvo que tengas una razón fuerte y controlada. Usa paquetes del sistema cuando sea suficiente. Fija versiones cuando el resultado tenga que ser reproducible. Y separa lo que requiere privilegios de lo que puede vivir en el entorno del usuario.

## El Cambio de Mentalidad

Antes, muchos repos trataban el setup como documentación:

```markdown
Install these things before running the project.
```

Eso era razonable cuando el lector principal era un humano sentado en su máquina principal.

Ahora el lector también puede ser un agente, un runner efímero, un workspace temporal o un colaborador entrando desde otra máquina. Para esos lectores, la documentación no basta. Necesitan un contrato ejecutable.

La pregunta no es "puede el agente descubrir cómo instalar esto?"

Probablemente sí.

La pregunta correcta es: **¿por qué debería descubrirlo cada vez?**

Cada dependencia que vive solo en una conversación es fricción que se repetirá. Cada paso que el repo puede ejecutar por sí mismo es una parte menos del contexto que tienes que cargar en tu cabeza, o en la del agente.

Para equipos que trabajan con IA, esto se vuelve una forma de DevEx: no solo developer experience humana, sino agent experience. El mejor entorno para un agente no es el que más instrucciones tiene en el prompt. Es el que menos explicaciones necesita para llegar a un build honesto.

Prepara el entorno. Deja que el agente trabaje en el problema.
