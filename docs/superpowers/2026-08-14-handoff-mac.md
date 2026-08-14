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

## 4.1 Añadido en el Mac — 2026-08-14, misma fecha

**Los ocho hallazgos abiertos de §9 están cerrados**, cada uno con su test que falló primero.
Los cuatro de severidad media medían mal las dimensiones que deciden la admisión; al arreglar el
del BOM apareció una variante peor que la descrita: `runtime_typing.py` tenía su propio lector, así
que un fichero con marca de orden de bytes que importara pydantic **colaba el repo por el criterio
de exclusión**. De los bajos salieron dos decisiones nuevas: el coste se publica unificado
(entorno + suite) y el tipado en ejecución lleva alcance (`n de m ficheros`), porque un decorador
suelto y un repo construido sobre pydantic no son el mismo candidato.

**El runner Docker funciona y es el ejecutor por defecto** (`--runner docker|venv`). El repo se
**copia** dentro del contenedor en vez de montarse: medido sobre python-stdnum en el mismo
contenedor y con el mismo entorno, 113 s de suite montado frente a 43 s copiado. El perfilado
completo de python-stdnum en contenedor sale ADMITIDO con `413 passed / 9 skipped`, idéntico a
Windows, y **67 s por corrida** (44 de entorno + 23 de suite) frente a los 89 s de Windows.

Estado de la suite: `104 passed`, más `3 passed` de integración con entorno virtual y `3 passed`
de integración con Docker (marcador `docker`, deseleccionable donde no lo haya).

---

## 5. Montar el entorno en el Mac

```bash
git clone https://github.com/JaviMaligno/agent-code-practices
cd agent-code-practices
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest -q
```

Esperado: `104 passed, 6 deselected`.

Y los de integración, que sí tocan la red y crean entornos:

```bash
.venv/bin/python -m pytest -m integration -q   # 3 passed, ~2 min (entorno virtual)
.venv/bin/python -m pytest -m docker -q        # 3 passed, ~1 min (contenedores)
```

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

**Hecho.** El runner Docker convive con el de entorno virtual y es el de por defecto
(`--runner docker|venv`). La predicción se cumplió: `install_strategies`,
`plugins_for_unrecognised`, `collection_failed` y `parse_pytest_summary` no se tocaron — cambia
quién ejecuta, no qué se decide.

**Ojo con esto**, que ya mordió una vez: la imagen `python:3.12-slim` **no trae git**, y pint,
jsonschema, dateutil y sqlglot derivan su versión del repositorio en tiempo de instalación. Sin
git, `pip install -e .` aborta. Por eso la imagen es `python:3.12` a secas, y hay un test de
integración que lo fija: un repo con `setuptools-scm` que no instalaría sin git.

**Lo que no se anticipó:** montar el repo como volumen es carísimo en macOS. Se copia dentro del
contenedor con `docker cp`, y la suite de python-stdnum baja de 113 s a 43 s. El spec ya recoge la
decisión y su medida (§5.6).

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

1. ~~**Runner Docker**~~ — hecho (§4.1). Imagen `python:3.12`, no `slim`, porque trae git.
2. ~~**Hallazgos de severidad media**~~ — hechos, y los de severidad baja también (§4.1).
3. **Perfilar los siete candidatos** y elegir tres finalistas: es la Task 11 del plan de fase 0, con
   babel fuera. Uno cada vez, con limpieza de clones al terminar. El plan está escrito en
   PowerShell y con rutas `C:/Users/...`: hay que traducirlo a zsh y añadir `--runner docker`.
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

## 9. Hallazgos — todos cerrados (2026-08-14, en el Mac)

Salieron de una revisión con tres lentes sobre el código de la fase 0. Ninguno rompía nada de forma
visible — todos devolvían un número plausible y equivocado, que es el modo de fallo peligroso aquí.
Se conserva la lista porque describe qué medía mal la herramienta antes de las cifras que ya se
apuntaron en §4 y §9 con ella.

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

**Consecuencia sobre las cifras de §4.** Las de python-stdnum se midieron con la herramienta
sesgada, así que la ficha buena es la de §4.1: la densidad de dominio sube de 26,5% a 27,6% (340
candidatas en vez de 327) y el ratio de comentarios de 22,7% a 24,3%. El 97,6% de funciones
anotadas no se mueve, pero por una propiedad del repo y no de la métrica: python-stdnum anota de
forma completa, así que exigir todos los parámetros o solo uno da lo mismo. En un candidato con
anotación parcial la diferencia sí aparecerá, y es de las que deciden cuánto puede quitar A1.

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
