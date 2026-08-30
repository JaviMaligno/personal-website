# Fase 2 — Resultados: B2, B3 y B4, con la dosis medida

**Fecha:** 2026-08-19
**Plan:** [`../plans/2026-08-17-fase-2-familia-b-jerarquia.md`](../plans/2026-08-17-fase-2-familia-b-jerarquia.md)
**Spec:** [`2026-08-14-software-practices-for-coding-agents-design.md`](2026-08-14-software-practices-for-coding-agents-design.md), §4.2 y §3.6.3
**Fase 1:** [`2026-08-17-fase-1-resultados.md`](2026-08-17-fase-1-resultados.md)
**Código:** https://github.com/JaviMaligno/agent-code-practices — 140 commits, `345 passed`

---

## 1. Qué hay implementado

Siete transformaciones registradas: **A1, A2, A3, A4** (fase 1) y **B2, B3, B4** (esta). Faltan B1
(cohesión) y B5 (tamaño), que parten y fusionan módulos y van en un plan aparte.

Más dos piezas de núcleo que la familia B necesitaba y la A no:

- **El entorno instala las dependencias, no el repo.** Aplanar la jerarquía invalida una instalación
  editable (§5.6), así que el árbol se pone al alcance de pytest por ruta. Las dependencias se leen
  del `pyproject`, del `setup.cfg` y del `setup.py` —parseado, nunca ejecutado—, porque python-stdnum
  no tiene `pyproject.toml` y devolvía la lista vacía.
- **El mapa de identidad sigue movimientos entre módulos.** `TransformResult` lleva ahora un mapa
  módulo→módulo, igual que ya llevaba el de renombrados. Sin eso, en cuanto B2 renombra un fichero,
  todos sus símbolos se caían del manifiesto y la métrica de localización (§5.4.2) se quedaba sin
  datos, en verde.

---

## 2. Equivalencia verificada

Cada celda: suite del original y del transformado, ejecutadas en contenedor y comparadas en tests que
pasan, fallan, dan error y se saltan.

| Celda | Dosis real | Suite original | Suite transformada |
|---|---|---|---|
| pint × B2 | 126 ficheros | 2.024p / 730s | **idéntica** |
| sqlglot × B2 | 229 ficheros | 1.231p | **idéntica** |
| pint × B4 | suite entera fuera | 2.024p / 730s | **idéntica** |
| sqlglot × B4 | suite entera fuera | 1.231p | **idéntica** |

La columna de dosis no es decoración: dos celdas de la primera verificación estaban **equivalentes y
a cero** —árbol byte a byte idéntico al original— y nadie lo vio hasta que alguien hizo `diff -rq`.
Un test verde que no puede fallar ocupa el sitio del que sí comprobaría algo.

---

## 3. La dosis real, repo por repo

Medido sobre los cuatro repositorios. B2 aplica en dos de ellos, y en los otros dos **la dosis cero
es la respuesta correcta**, no un defecto:

| | B2 | B3 | B4 |
|---|---|---|---|
| python-stdnum | **cero, correcto** | 245 ficheros de docs, 0 docstrings de módulo | 170 ficheros |
| pint | 67 módulos movidos | 49 ficheros de docs | suite completa |
| sqlglot | 104 módulos movidos | cero: no tiene `docs/` | 126 ficheros |
| holidays | **cero, correcto** | 9 ficheros, README conservado | 309 ficheros |

**Por qué la dosis cero de B2 es correcta en dos repos.** python-stdnum resuelve sus módulos por
cadena (`'stdnum.%s' % cc`) y holidays los construye con f-strings
(`f"holidays.{prefix}.{module_name}"`): 313 de sus 329 módulos son inalcanzables por ruta. Mover esos
ficheros rompería el programa, así que la guarda que lo impide está bien puesta. Poder **distinguir**
esa dosis cero de la que producía un defecto nuestro fue el trabajo más difícil de esta fase, y hay
un test que fija la diferencia.

**Por qué B3 aplica media dosis en dos repos.** python-stdnum lee las docstrings de sus módulos con
`pydoc.getdoc` y tiene un doctest que lo comprueba módulo a módulo; holidays tiene tres tests que
verifican que las tablas de su README listan todos los países. Donde el programa **lee** su
documentación, esa parte no es documentación: es comportamiento, y quitarla rompería la equivalencia.
La dosis perdida se declara.

---

## 4. Lo que enseñó esta fase

**El árbol transformado filtraba lo que las transformaciones acababan de quitar.** `copy_tree` solo
excluía `.git`, así que arrastraba los artefactos del clon: `.pytest_cache/v/cache/nodeids` contiene
literalmente la lista de tests que B4 acaba de esconder, el `SOURCES.txt` del `egg-info` los nombra
otra vez, y un `__pycache__` mantiene vivo el árbol de módulos que B2 acaba de aplanar — además de
impedir que se borren los directorios vacíos, con lo que B2 aparentaba aplicarse sin aplicarse. Hoy
la copia filtra artefactos por nombre y por contenido; el informe HTML de coverage se detecta porque
empotra el fuente entero, no por su nombre, que puede ser cualquiera.

**Una ruta relativa se resuelve dos veces.** Los comandos se lanzan con `cwd=repo`, así que
`docker cp` buscaba la suite guardada **dentro del árbol del que acababa de salir**. Es la tercera
aparición del mismo error en el proyecto —antes fue el entorno virtual en `repo/repo/.acp-venv`— y es
el que dejaba las dos celdas de B4 en `0 passed`.

**Los ficheros de empaquetado también nombran módulos.** B2 movía `pint/pint_convert.py` y dejaba
`[project.scripts] pint-convert = "pint.pint_convert:main"` apuntando al vacío: el repo instalaba,
la suite pasaba y el comando instalado moría con `ModuleNotFoundError`. La equivalencia por tests no
lo detecta, porque ningún test invoca el script.

**Cuatro veces en dos fases, un arreglo verificado solo contra fixtures resultó incompleto al pasarlo
por un repo real.** Es el argumento más sólido a favor de correr el pre-flight §3.6.3 pronto y sobre
los repos de verdad, en vez de al final.

---

## 5. Límites conocidos

- **B2 solo mide en dos de los cuatro repos**, y por razones legítimas en los otros dos. El eje de
  jerarquía se sostiene sobre pint y sqlglot; el artículo tiene que decirlo así.
- **B3 aplica dosis parcial** en python-stdnum y holidays, por lo explicado en §3.
- **B4 y la configuración de pytest**: donde los `addopts` nombran la ruta de la suite, ocultarla
  hacía que pytest abortara antes de colectar nada — el agente no se quedaba sin tests, se quedaba
  sin poder ejecutar pytest. Se ajusta esa ruta al aplicar B4, y queda declarado como una desviación
  de la regla de no tocar los `addopts`.
- **Diez casos de laboratorio** siguen rompiendo A1 o A2 (metaclases escritas de otra forma, nombres
  ensamblados en ejecución, `inspect.signature`). No aparecen en ningún repo del sustrato y se
  declaran en la fase 1.

---

## 6. Lo siguiente

1. **B1 y B5**, que parten y fusionan módulos: colisiones de nombres entre definiciones que acaban en
   el mismo espacio.
2. **La matriz completa de equivalencia** de B2, B3 y B4 sobre los cuatro repos, no solo las cuatro
   celdas verificadas aquí.
3. **El checkpoint del spec §3.6** sigue en pie: sin las nueve transformaciones no hay condición T2
   ni T3 completas.
