# Traspaso a la máquina Mac — experimento de buenas prácticas para coding agents

> **FICHERO TEMPORAL.** Existe solo para continuar el trabajo en otra máquina y otra sesión.
> **Bórralo cuando el artículo esté publicado.** No forma parte de la documentación del sitio.

**Fecha:** 2026-08-14
**Máquina de origen:** Windows (sin Docker — lo tumba)
**Máquina de destino:** Mac (con Docker)
**Código:** https://github.com/JaviMaligno/agent-code-practices (público, rama `main`)

---

## 1. Cómo arrancar la sesión nueva

Abre Claude Code en el clon de `personal-website` en el Mac y pega esto:

> Voy a continuar un experimento que empecé en otra máquina. Lee, en este orden:
> `docs/superpowers/2026-08-14-handoff-mac.md`, luego el spec
> `docs/superpowers/specs/2026-08-14-software-practices-for-coding-agents-design.md`,
> y luego el plan `docs/superpowers/plans/2026-08-14-fase-0-perfilado-de-repos.md`.
> El código vive en https://github.com/JaviMaligno/agent-code-practices — clónalo.
> Cuando lo tengas todo, dime en qué punto estamos y cuál es el siguiente paso antes de tocar nada.

---

## 2. Qué es esto, en un párrafo

Un experimento para un artículo del blog: **qué buenas prácticas de software ayudan realmente a un
coding agent**. Se parte un repositorio limpio y se le aplican degradaciones **semánticamente
equivalentes** —el programa hace exactamente lo mismo— repartidas en dos familias: las que cambian
cómo se lee un fichero ya abierto (tipos, nombres, formato, docstrings) y las que cambian dónde
está cada cosa (cohesión, jerarquía, documentación de repo, tests visibles, tamaño de fichero).
Luego se mide cuánto cae la tasa de resolución de un agente en cada condición. La hipótesis es que
pesa más saber dónde mirar que lo bien escrito que esté el fichero.

El spec tiene el diseño completo: condiciones, métricas, predicciones registradas antes de correr,
y qué resultado tumbaría la tesis.

---

## 3. Dónde está cada cosa

| Qué | Dónde |
|---|---|
| Spec del experimento (diseño completo) | `docs/superpowers/specs/2026-08-14-software-practices-for-coding-agents-design.md` |
| Plan de la fase 0 (ejecutado) | `docs/superpowers/plans/2026-08-14-fase-0-perfilado-de-repos.md` |
| Código de la herramienta | https://github.com/JaviMaligno/agent-code-practices |
| Artículo predecesor, para el listón metodológico | `src/content/blog/en/coding-agents-structure.md` |

Los dos primeros están en la rama `blog/what-has-already-happened` de `personal-website`, no en
`main`. Asegúrate de estar en esa rama en el Mac.

---

## 4. Estado exacto a 2026-08-14

**Hecho: la fase 0 está implementada y verificada.** Es la herramienta que perfila repositorios
candidatos para decidir cuáles entran en el experimento. 16 commits, `68 passed, 3 deselected`, más
3 tests de integración que pasan (`-m integration`, tardan ~2 min porque crean entornos de verdad).

Mide, por repositorio: tamaño y profundidad de jerarquía, margen de degradación (ratio de
comentarios y docstrings, cobertura de anotaciones, presencia de README y `docs/`), uso de tipado
en ejecución (criterio de exclusión), acoplamiento por grafo de imports internos, un proxy de
densidad de lógica de dominio con muestra para inspección humana, y el resultado de su suite.

**Verificado contra un repo real.** `python-stdnum` sale **ADMITIDO**: 360 módulos, 17.992 líneas,
97,6% de funciones anotadas, 28% de docstrings, densidad de dominio 26,5% con 327 candidatas,
suite en `413 passed / 9 skipped in 19.84s`, 69 s de preparación de entorno. Su punto flojo es la
jerarquía (profundidad máxima 2, poco que aplanar); a cambio, 360 módulos planos dan mucho margen
para romper cohesión y concatenar.

**No hecho:** todo lo demás. No se han perfilado los otros candidatos, no se han elegido los tres
finalistas, y no existe nada de las fases siguientes (transformadores, generación de tareas,
harness de agente, campaña).

---

## 5. Montar el entorno en el Mac

```bash
git clone https://github.com/JaviMaligno/agent-code-practices
cd agent-code-practices
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest -q
```

Esperado: `68 passed, 3 deselected`.

Y los de integración, que sí tocan la red y crean entornos:

```bash
.venv/bin/python -m pytest -m integration -q
```

Esperado: `3 passed`, alrededor de dos minutos.

El código detecta la plataforma para localizar el intérprete del entorno virtual
(`Scripts/python.exe` en Windows, `bin/python` fuera), así que no hay nada que adaptar a mano.

---

## 6. Qué cambia por estar en el Mac

**Docker vuelve a estar disponible**, y esa es la razón principal del traslado — junto con que la
máquina Windows se satura y ya ha matado tandas de trabajo.

El motivo de fondo para mudarse no es Docker en sí: es que el sustrato del experimento son repos
Python de terceros y su hábitat natural es POSIX. En Windows varios candidatos caerían por
compilación de wheels, symlinks o dependencias del sistema — razones que no dicen nada sobre si el
repo sirve para el experimento. Un candidato descartado por no compilar en Windows es un candidato
perdido por la razón equivocada.

**Lo que hay que hacer allí:** añadir un runner Docker junto al de entorno virtual. La lógica ya
está separada y es reutilizable tal cual — `install_strategies`, `plugins_for_unrecognised`,
`collection_failed` y `parse_pytest_summary` no saben nada de dónde se ejecuta. Cambia quién
ejecuta, no qué se decide. Conviene conservar el runner de entorno virtual como alternativa
verificada, seleccionable por flag.

**Ojo con esto**, que ya mordió una vez: la imagen `python:3.12-slim` **no trae git**, y pint,
jsonschema, dateutil y sqlglot derivan su versión del repositorio en tiempo de instalación. Sin
git, `pip install -e .` aborta. Hace falta una imagen con git y `git config --global --add
safe.directory` por el uid del montaje.

**El spec hay que ajustarlo** cuando el runner Docker funcione: la sección §2 y la §5.6 describen
ahora mismo el aislamiento por entorno virtual. Con contenedores, el aislamiento vuelve a ser de
sistema, aunque las dos decisiones de §5.6 siguen siendo necesarias igual (ver §7 abajo).

---

## 7. Decisiones ya tomadas — no re-litigar

- **El sustrato principal no es SWE-bench.** La contaminación sesga las dos familias en direcciones
  opuestas y el resultado no sería interpretable. SWE-bench entra solo como réplica de control de
  cuatro celdas. Razonado en §3.1 del spec.
- **Las tareas se generan por inyección de fallos**, estratificadas 12/12 entre genéricas
  (reconocibles por patrón) y de dominio (solo incorrectas a la luz de la lógica del sistema). El
  estrato es probablemente un hallazgo, no una variable de control. §3.3.1.
- **La localización se mide por símbolo, no por fichero.** Con todo concatenado solo hay un
  fichero, así que "abrió el correcto" marcaría acierto siempre justo en la celda donde importa.
  §5.4.2.
- **El coste se normaliza por tamaño del repo.** Quitar comentarios encoge el árbol y regala
  presupuesto de lectura; sin normalizar se leería como "los comentarios no ayudan". §5.4.3.
- **El nombre del paquete raíz no se transforma nunca.** Todo lo de dentro sí. Es lo único que
  mantiene válidos a la vez la instalación, los imports y el comando de test. §5.6.
- **Se instalan las dependencias, no el repo**, porque aplanar la jerarquía invalidaría una
  instalación editable. §5.6.
- **El veredicto tiene tres estados**: `ADMITIDO`, `RECHAZADO` (se midió y no cumple) y
  `NO EVALUABLE` (no se pudo medir). Mezclar los dos últimos hace que un fallo de fontanería se lea
  como defecto del candidato.
- **babel queda descartado** como candidato: necesita descargar el CLDR antes de poder testear, un
  paso de preparación propio que no compensa, y además es de los más vistos. Quedan siete.
- **Convenio de complejidad ciclomática**, pendiente de aplicar: `match` cuenta un punto por caso,
  las cláusulas `for` de comprehension cuentan, y las funciones anidadas no se cuentan dos veces.
- **No se neutralizan los `addopts` de un proyecto.** Resolvería síntomas en una línea, pero los de
  python-stdnum incluyen `--doctest-modules` y los doctests son la mitad de su suite: se estaría
  midiendo un repo distinto del que se va a usar.

---

## 8. Trabajo pendiente, en orden

1. **Runner Docker** junto al de entorno virtual, con imagen que traiga git (§6).
2. **Hallazgos de severidad media** que siguen abiertos (§9). Los cuatro primeros sesgan justo las
   dimensiones que deciden cuánto margen de degradación tiene un repo, así que conviene cerrarlos
   antes de perfilar y no después.
3. **Perfilar los siete candidatos** y elegir tres finalistas: es la Task 11 del plan de fase 0, con
   babel fuera. Uno cada vez, con limpieza de clones al terminar.
4. **Inspección manual de la muestra de dominio** de cada finalista: abrir cinco funciones y
   contestar por escrito si ahí se puede inyectar un fallo que solo se detecte entendiendo la regla
   de negocio y que obligue a leer más de un fichero. Ninguna métrica da ese juicio, y de él depende
   que el estrato de dominio sea viable.
5. **Documento de resultados de la fase 0** con la tabla comparativa, los descartes razonados y los
   tres finalistas.
6. **Checkpoint humano.** La fase 1 (transformadores y verificación de equivalencia) no se planifica
   hasta ver los finalistas: si ninguno tiene jerarquía profunda, B2 pierde sentido; si la densidad
   de dominio sale baja en todos, hay que replantear el estrato antes de construir nada.

**Candidatos que quedan:** pint, python-stdnum (ya perfilado, ADMITIDO), holidays, sqlglot,
dateutil, py-moneyed, jsonschema.

---

## 9. Hallazgos abiertos

Salieron de una revisión con tres lentes sobre el código de la fase 0. Los de severidad alta ya se
arreglaron; estos no. Ninguno rompe nada de forma visible — todos devuelven un número plausible y
equivocado, que es el modo de fallo peligroso aquí.

**Media:**

1. **`cyclomatic_complexity` tiene tres defectos con sesgos opuestos** (`domain.py`): un `match` de
   tres casos puntúa 1; una comprehension anidada solo cuenta sus `ifs`; y las ramas de una función
   anidada se cuentan dos veces. Subestima en código moderno y sobreestima con closures, así que el
   umbral deja de ser comparable entre repos. Aplicar el convenio de §7.
2. **`comment_ratio` y `annotated_function_ratio` miden mal el margen de degradación**
   (`readability.py`): solo cuenta líneas que *empiezan* por `#`, así que los comentarios de final
   de línea valen cero; y una función con un solo argumento anotado cuenta como anotada al 100%.
   Subestima comentarios y sobreestima anotaciones — las dos dimensiones que deciden cuánto hay que
   destruir para la familia B y cuánto efecto tendría A1.
3. **Los ficheros que no parsean se saltan en silencio** (`readability.py`, `coupling.py`,
   `domain.py`): un `.py` con BOM lanza `SyntaxError`, desaparece de las métricas de AST, pero sus
   líneas siguen contando en el denominador. Arreglo mínimo: leer con `utf-8-sig` y publicar un
   contador `unparseable_files` en la ficha.
4. **El detector de tipado en ejecución no cubre la stdlib** (`runtime_typing.py`): falta
   `functools.singledispatch`, que despacha **leyendo la anotación**. Un repo así pasaría admisión y
   A1 dejaría de ser semánticamente equivalente sin que nadie se entere.

**Baja:** `seconds` excluye el tiempo de instalación, que es la mitad del criterio de coste que el
spec pide medir (ya se registra aparte como `install_seconds`, falta unificarlo en el informe);
`uses_runtime_typing` es booleano de repo, sin noción de alcance; la evidencia usa el nombre del
fichero en vez de la ruta relativa; un `__init__.py` en la raíz del clon produce un nombre de módulo
vacío que nunca casa.

**Caveat operativo verificado:** la ruta que se pasa al CLI tiene que ser la raíz del repo que
*contiene* el paquete, no el directorio del paquete. Pasando el directorio del paquete, los imports
absolutos internos no resuelven y el fan-out cae sin dar ningún error. Al clonar el repo entero es
correcto por defecto, pero conviene no "afinar" la ruta.

---

## 10. Reglas de la casa que siguen aplicando

- **Nada de suites en paralelo.** Un solo proceso de pytest a la vez.
- **Limpiar los clones** al terminar cada bloque, y comprobar disco antes de empezar.
- **Repos de cliente excluidos** por completo, también como copias locales.
- **TDD estricto**: test que falla, implementación, test que pasa, commit. Cada paso su commit.
- **Ninguna recomendación más fuerte que el dato que la sostiene** cuando se escriba el artículo.
  Los límites de cobertura van por delante, no escondidos al final.
