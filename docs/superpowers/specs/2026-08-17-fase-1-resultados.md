# Fase 1 — Resultados: familia A verificada sobre los tres finalistas

**Fecha:** 2026-08-17
**Plan:** [`../plans/2026-08-15-fase-1-transformadores-familia-a.md`](../plans/2026-08-15-fase-1-transformadores-familia-a.md)
**Spec:** [`2026-08-14-software-practices-for-coding-agents-design.md`](2026-08-14-software-practices-for-coding-agents-design.md), §4 y §3.6.3
**Fase 0:** [`2026-08-14-fase-0-resultados.md`](2026-08-14-fase-0-resultados.md)
**Código:** https://github.com/JaviMaligno/agent-code-practices

---

## 1. Equivalencia: 12 de 12

Cada transformación aplicada por separado sobre cada finalista, con su suite ejecutada en contenedor
y comparada con la del original del mismo repo. Es el pre-flight que el spec §3.6.3 exige antes de
gastar cómputo: una transformación que rompe el repo se lee exactamente igual que un agente que
fracasa.

| Repo | original | A1 tipos | A2 nombres | A3 formato | A4 docs |
|---|---|---|---|---|---|
| python-stdnum | 413p / 9s | = | = | = | = |
| sqlglot | 1.225p | = | = | = | = |
| holidays | 7.558p / 4s | = | = | = | = |

`=` significa idéntico en tests que pasan, fallan, dan error y se saltan. holidays lleva su paso de
l10n (`python scripts/l10n/generate_mo_files.py`) en los dos lados de cada comparación.

---

## 2. La dosis real, que no es la nominal

Ninguna transformación aplica exactamente lo que el spec describe, y las diferencias se declaran
aquí porque van al artículo:

- **A1 no toca las anotaciones del cuerpo de una clase.** Ahí la anotación no describe el atributo,
  lo declara: en un `@dataclass`, quitar `amount: int` deja el constructor sin argumentos. Medido
  sobre los finalistas, esas anotaciones son el 6,5% del total en sqlglot, el 3,7% en holidays y una
  sola en python-stdnum; parámetros y retornos son más del 90%. Tampoco toca la anotación con la que
  despacha `functools.singledispatch`, que es comportamiento y no documentación.
- **A2 renombra definiciones de nivel de módulo, no métodos.** Atribuir `obj.metodo()` a una clase
  exige inferencia de tipos, y equivocarse rompe el repo en silencio. Además excluye los símbolos
  que el repo alcanza por cadena, y los nombres de las funciones de test, porque pytest colecta por
  nombre.
- **A4 conserva los bloques de doctest y borra la prosa.** Decisión del autor: en python-stdnum los
  doctests son media suite, así que borrarlos haría fallar la verificación de equivalencia por
  construcción. La docstring pierde su explicación —que es lo que A4 quiere medir— pero mantiene los
  ejemplos ejecutables. Donde hay doctests, la dosis de A4 es menor. Conserva también los comentarios
  que lee una herramienta y no un lector (`# pragma: no cover`, `# noqa`, `# type: ignore`), el
  shebang y la cookie de codificación: sin eso, la cobertura de python-stdnum caía a 98,23% con
  `fail_under = 100` y tumbaba la suite sin que fallara ningún test.
- **A3 sí implementa el colapso de líneas** con el techo de 400 caracteres del spec, además de las
  líneas en blanco y el espaciado de operadores. No colapsa lo que rompería el programa: el espacio
  alrededor de `in`, `is` y `not in` es sintaxis, igual que la sangría.

---

## 3. Lo que se aprendió del procedimiento

**Los fixtures no bastan para decidir si una transformación es equivalente.** Tres veces en esta
fase un arreglo verificado contra tests sintéticos resultó incompleto al pasarlo por un repo real:
A4 y los doctests, A2 y `getattr`, y la versión derivada del repositorio. La suite de 226 tests
estaba en verde mientras el árbol transformado de sqlglot no se podía ni instalar.

**El árbol transformado no lleva `.git`, y eso tiene consecuencias.** Copiarlo le daría al agente el
historial y, con un `git checkout .`, el código sin transformar: todas las condiciones se volverían
T0. Pero sqlglot, pint, jsonschema y dateutil derivan su versión del repositorio, y sin `.git`
`pip install -e .` aborta — hasta la baseline salía NO EVALUABLE. Se resuelve pasando
`SETUPTOOLS_SCM_PRETEND_VERSION` por entorno a todos los comandos que construyen el proyecto, sin
tocar el `pyproject`, que es parte del árbol que ve el agente.

**Dos fugas cerradas.** El manifiesto de procedencia —con el diccionario completo de A2 y la región
objetivo de cada símbolo— se escribía dentro del árbol que explora el agente. Y el ejecutor de
entorno virtual creaba su `.acp-venv` también dentro, de forma permanente en la campaña, que
reutiliza el entorno por repositorio. Los dos viven ya fuera.

**El mapa de símbolos se reconstruye sobre el árbol transformado** y se casa con el original por
posición estructural, conservando la identidad original como clave. Antes publicaba los rangos del
árbol original, que A1, A3 y A4 desplazan: proyectar las lecturas del agente sobre ese mapa habría
dado localización falsa, y la localización es la hipótesis medida directamente (§5.4.2).

---

## 4. Límites conocidos

Diez casos construidos en laboratorio siguen rompiendo A2 o A1, y no aparecen en ninguno de los tres
finalistas: una metaclase escrita como `ABCMeta` en vez de `type`, un decorador de clase que registra
por `cls.__name__`, `type(self).__name__`, `__qualname__` en lugar de `__name__`, una referencia con
puntos dentro de una cadena, un entry point declarado en `pyproject.toml`, un nombre ensamblado en
ejecución, `inspect.signature` leyendo anotaciones, y un registrador de `singledispatch` ligado antes
a un nombre local.

No se han arreglado a propósito: taparlos uno a uno no converge —no existe la lista completa de
formas en que un programa Python puede alcanzar un nombre por cadena— y el guardarraíl que sí
converge ya está en el diseño, que es esta verificación de equivalencia por repo y condición. Si un
repo futuro cae en alguno de estos casos, la verificación lo dirá y se saca del diccionario lo que
rompa, declarando la dosis real.

---

## 5. Estado

- `226 passed` en unitarios, `12 passed` de integración, `9 passed` en el bloque Docker.
- 44 commits en `main` de `agent-code-practices`.
- Falta la familia B (B1 cohesión, B2 jerarquía, B3 documentación de repo, B4 tests visibles, B5
  tamaño), que mueve ficheros y obliga a que el mapa de símbolos siga reubicaciones y no solo
  renombrados. B2 se medirá sobre pint, único candidato con jerarquía profunda.
