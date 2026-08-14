# Fase 0 — Resultados: perfilado de candidatos y tres finalistas

**Fecha:** 2026-08-14
**Spec:** [`2026-08-14-software-practices-for-coding-agents-design.md`](2026-08-14-software-practices-for-coding-agents-design.md), §3.2
**Plan:** [`../plans/2026-08-14-fase-0-perfilado-de-repos.md`](../plans/2026-08-14-fase-0-perfilado-de-repos.md), Task 11
**Herramienta:** https://github.com/JaviMaligno/agent-code-practices
**Ejecución:** macOS, contenedores (`--runner docker`, imagen `python:3.12`), corridas secuenciales, clones borrados al cerrar cada repo.

---

## 1. Tabla comparativa

Todas las cifras están medidas, ninguna estimada. Coste = preparación del entorno + suite completa.

| repo | veredicto | ficheros | líneas | prof. máx | anotadas | docs/ | tipado runtime | fan-out | dominio | suite | coste |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **python-stdnum** | **ADMITIDO** | 359 | 17.941 | 2 | 98% | sí | no | 1,92 | 28% | 413p / 22 s | 96 s |
| **sqlglot** | **ADMITIDO** | 184 | 62.920 | 2 | 96% | **no** | no | 4,45 | **41%** | 1.219p / 193 s | 246 s |
| **holidays** | **ADMITIDO** | 328 | 59.091 | 2 | 19% | sí | no | 4,00 | 24% | 7.558p / 186 s | 228 s |
| jsonschema | RECHAZADO | 25 | 4.137 | 2 | 22% | sí | **sí** | 1,56 | 31% | 7.809p / 30 s | 63 s |
| py-moneyed | RECHAZADO | 5 | 684 | 2 | 100% | sí | no | 0,80 | 17% | 57p / 1f | 27 s |
| dateutil | NO EVALUABLE | 20 | 5.866 | 3 | 3% | sí | no | 0,65 | 20% | no colecta | — |
| pint | retirado | 69 | 13.240 | **3** | 65% | sí | no | 4,41 | 19% | 2.024p / 317 s | 339 s |
| babel | no perfilado | — | — | — | — | — | — | — | — | — | — |

**Riesgo de contaminación** (quinta dimensión de examen, §3.2; criterio de desempate, no de exclusión):

| repo | estrellas | creado |
|---|---|---|
| python-stdnum | 588 | 2013-04 |
| holidays | 1.917 | 2014-08 |
| pint | 2.766 | 2012-07 |
| jsonschema | 4.971 | 2011-12 |
| sqlglot | 9.529 | 2021-03 |

---

## 2. Los tres finalistas

### python-stdnum — el barato y el más granular

Validación de identificadores por país: un módulo por regla, 359 módulos planos. Es el más barato con
diferencia (96 s por corrida frente a 228 y 246), lo que importa porque el coste se multiplica por 54
condiciones. El menos visto del lote (588 estrellas), así que gana cualquier desempate por
contaminación.

Su margen de degradación es el mejor repartido: 24,3% de comentarios, 28,1% de docstrings y 97,6% de
funciones anotadas —anotadas por completo, no a medias—, de modo que A1 y A4 tienen mucho que quitar.
Para la familia B, sus 359 módulos planos dan sitio de sobra a B1 (romper cohesión) y a B5
(concatenar). Su punto flojo es la jerarquía: profundidad 2, poco que aplanar en B2.

El fan-in máximo de 246 sobre 690 aristas dice que casi todo pasa por unos pocos módulos comunes de
verificación de dígitos de control. Eso es bueno para el estrato de dominio: un fallo en la regla de
un país obliga a leer la regla y el verificador compartido.

### sqlglot — el de mayor densidad de dominio

Dialectos SQL: parser, generador y optimizador con reglas propias por dialecto. La densidad de
dominio es la más alta del lote con diferencia (41%, 1.345 candidatas), y el fan-out medio también
(4,45): entender un fallo casi nunca cabe en un fichero.

Es además el único candidato **sin `docs/`**, con 3,8% de comentarios y 6,0% de docstrings. Eso lo
convierte en el caso interesante para B3 y A4: parte ya con poca documentación, así que ahí la
degradación tiene poco recorrido, y sirve de contraste con python-stdnum, que está muy documentado.

Su riesgo es el opuesto al de python-stdnum: 9.529 estrellas y creado en 2021, es el más visto del
lote. Como los fallos son inyectados y no existen en internet, la contaminación pesa mucho menos que
en un benchmark de issues reales, pero conviene declararlo en el artículo.

### holidays — el más acoplado, y el que necesita un paso propio

Reglas de calendario por jurisdicción: 328 módulos, 1.311 aristas internas, fan-out 4,00 y fan-in
máximo 239 sobre `holiday_base`. Estructuralmente es el más entrelazado de los tres.

Es el único con **paso de preparación propio**: su suite necesita las traducciones compiladas, que
genera `python scripts/l10n/generate_mo_files.py`. Sin ese paso fallan 515 tests con
`FileNotFoundError: No translation file found`, y el repo se lee como roto cuando no lo está. El paso
cuesta 0,35 s, queda registrado en la ficha y forma parte de la receta de cada corrida.

Su margen de degradación es el más asimétrico: solo 19,2% de funciones anotadas, así que A1 apenas
tiene nada que quitar; a cambio, 16% de comentarios y una suite de 7.558 tests que discrimina fino.

---

## 3. Descartes, con su razón

**jsonschema — RECHAZADO por tipado en ejecución.** Usa `attrs` en 4 de 25 ficheros, pero entre ellos
`validators.py` y `exceptions.py`: es el núcleo, no un uso marginal. Con anotaciones que gobiernan
comportamiento en ejecución, A1 dejaría de ser semánticamente equivalente, que es el criterio 4 de
admisión (§3.2.1). Es una pena, porque su densidad de dominio (31%) y su coste (63 s) eran buenos.

**py-moneyed — RECHAZADO por tamaño.** 684 líneas en 5 ficheros. Por debajo del umbral de 2.000: el
agente se lo lee entero y todas las transformaciones de familia B dan cero por construcción (criterio
2). Además su suite tiene un fallo en `master`.

**dateutil — NO EVALUABLE.** Dos problemas encadenados. El primero se resuelve: su `setup.cfg` declara
`filterwarnings = error`, y pytest 9 emite un warning nuevo sobre su propio código de tests, así que
la colecta muere; con `pytest<8.4` colecta limpio 2.096 tests en vez de 1.528 y un error. El segundo
no: la suite necesita `dateutil-zoneinfo.tar.gz`, un artefacto que el repo genera en su build. Se
descarta por la misma razón que babel — un paso de preparación propio —, con la diferencia de que
ahora la herramienta sí sabría ejecutarlo si se decidiera rescatarlo.

**pint — retirado por coste de suite.** Admitido en las métricas (2.024 tests en verde), pero su suite
tarda 317 s. Decisión del autor a la vista de que el coste se multiplica por 54 condiciones. **Coste
declarado de esta decisión**: pint era el único candidato con jerarquía de profundidad 3, y los tres
finalistas son planos (profundidad 2). B2 —aplanar directorios y renombrar ficheros— se queda casi sin
sustrato donde producir efecto. Es el punto que la fase 1 tiene que resolver antes de construir el
transformador: o se acepta que B2 se mide con poco recorrido, o entra un cuarto repo con jerarquía.

**babel — descartado sin perfilar.** Decisión previa (§7 del traspaso): necesita descargar el CLDR
antes de poder testear, y es de los repos más vistos.

---

## 4. ¿Sigue siendo Python el lenguaje adecuado?

Sí para lo que el experimento necesita medir, con una salvedad que conviene decir por delante.

A favor: hay tres repos con lógica de dominio real, suites verdes y discriminantes, coste asumible y
sin tipado en ejecución. La densidad de dominio va del 24% al 41%, y en los tres el fan-in
concentrado indica que entender un fallo obliga a leer más de un sitio, que es lo que el estrato de
dominio requiere (§3.3.1).

La salvedad es la jerarquía. Los tres finalistas tienen profundidad máxima 2, y no es casualidad: las
librerías Python de dominio tienden a un paquete con muchos módulos hermanos, no a árboles profundos.
Eso deja a B2 con poco que destruir. La familia B sigue siendo medible por B1 (cohesión), B3
(documentación), B4 (tests visibles) y B5 (tamaño) —los cuatro tienen recorrido de sobra—, pero B2
concreto queda tocado, y el artículo tendrá que decirlo en lugar de presentar la familia B como un
bloque homogéneo.

---

## 5. Lo que estas cifras no dicen

- **El coste medido tiene ruido apreciable.** La suite de holidays dio 302 s en una corrida y 186 s en
  otra; la de sqlglot, 121 s y 193 s. Son medidas de una sola pasada en una máquina compartida.
  Sirven para ordenar candidatos, no como presupuesto fino.
- **La densidad de dominio es un proxy**, no un juicio. Cuenta funciones con ramas que llaman a otras
  del propio repo. El paso 7 de la Task 11 —abrir cinco funciones de la muestra de cada finalista y
  decidir por escrito si ahí cabe un fallo que solo se detecte entendiendo la regla de negocio— sigue
  pendiente, es juicio humano y de él depende que el estrato de dominio sea viable.
- **Las cifras anteriores a esta tanda estaban sesgadas.** Se corrigieron ocho defectos de medición y
  cinco de preparación de entorno; entre ellos, que se contaban los benchmarks y los scripts de CI
  como código del repo, y que una dependencia de test podía desinstalar el repo bajo prueba y dejar
  en su lugar la versión publicada en PyPI. Cualquier número de la fase 0 anterior a hoy debe
  descartarse.

---

## 6. Muestras para la inspección manual (paso 7, pendiente)

Repartidas por el árbol con paso determinista, no las primeras por orden alfabético.

**python-stdnum**: `ad.nrt.validate`, `be.vat.compact`, `ch.uid.compact`,
`de.handelsregisternummer._split`, `do.rnc.search_dgii`, `eu.banknote.validate`, `fr.siret.to_siren`,
`gs1_128.info`, `in_.pan.validate`, `iso11649.validate`, `kr.rrn.validate`, `mx.curp.get_gender`,
`pe.ruc.validate`, `se.postnummer.validate`, `ua.rntrc.validate`.

**sqlglot**: `parse_one`, `expressions.builders.insert`, `generator.directory_sql`,
`generator.connector_sql`, `generator.initcap_sql`, `generators.duckdb.normal_sql`,
`generators.postgres._day_month_year_sql`, `generators.spark2.altercolumn_sql`,
`optimizer.canonicalize._replace_int_predicate`, `optimizer.simplify.always_false`,
`parser._parse_create_like`, `parser._parse_paren`, `parser._parse_star_ops`,
`parsers.mysql._parse_generated_as_identity`, `parsers.tsql._builder`.

**holidays**: `calendars.burmese._get_start_date`, `countries.albania._populate_public_holidays`,
`countries.azerbaijan._populate_public_holidays`, `countries.cambodia._populate_public_holidays`,
`countries.cocos_islands._populate_public_holidays`, `countries.gambia._populate_public_holidays`,
`countries.kazakhstan._populate_public_holidays`,
`countries.malaysia._populate_subdiv_15_public_holidays`, `countries.oman._populate_public_holidays`,
`countries.slovenia._populate_public_holidays`,
`countries.switzerland._populate_subdiv_stadt_zurich_optional_holidays`,
`countries.united_states._populate_subdiv_al_public_holidays`,
`countries.united_states._populate_subdiv_ny_public_holidays`,
`financial.johannesburg_stock_exchange._populate_public_holidays`, `holiday_base.__getattr__`.

---

## 7. Cómo reproducir

```bash
git clone --depth 1 <url del candidato> candidates/<nombre>
python -m acp.cli profile candidates/<nombre> --name <nombre> --out out --runner docker \
  [--prepare "<paso de build propio del repo>"]
python -m acp.cli table --out out
rm -rf candidates/<nombre>
```

Para holidays, el paso es `python scripts/l10n/generate_mo_files.py`.

---

## 8. Checkpoint

La fase 0 termina aquí. Antes de planificar la fase 1 hay dos cosas que decidir a la vista de esta
tabla: qué se hace con B2 dado que los tres finalistas son planos (§3), y si el paso 7 confirma que
los tres admiten fallos de dominio de verdad (§5).
