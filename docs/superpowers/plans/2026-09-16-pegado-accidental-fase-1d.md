# Fase 1d: la similaridad sobre el brazo con señal — plan de implementación

> **SUPERSEDIDO (2026-09-16).** El muestreo que describe este documento
> —doce posiciones exactas del ranking, 288 celdas, banco N1 de 44, los tres
> modelos viendo cada pegote— se descartó por falta de potencia (16 % para la
> caída de 9 puntos) antes de correrse: no hay ninguna tirada con este
> diseño. Lo sustituye
> [`2026-09-16-pegado-accidental-fase-1d-bandas.md`](2026-09-16-pegado-accidental-fase-1d-bandas.md),
> que muestrea por bandas y da un modelo por estímulo, y es el que declara la
> cabecera de la tanda. Lo que se conserva vigente de aquí es todo lo que no
> es el muestreo: la puerta de D12, las hipótesis, la familia de Holm y el
> control de composición por señal.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Averiguar si el parecido entre el pegote y la conversación cambia la probabilidad de que el modelo **dude de la intención** cuando el pegote se delata solo.

**Architecture:** El mismo barrido de doce posiciones de la Fase 1b, corrido sobre el banco **N1** en vez del N0. No hay runner nuevo: `run_phase1b` se parametriza por nivel, porque la única diferencia real es de qué banco sale el pegote. El análisis reutiliza `curve.py` y añade las dos hipótesis primarias de esta tanda a la familia de Holm.

**Tech Stack:** Python 3.12, `numpy`, `pytest`. Jueces por gateway y Vertex, operativos desde la Fase 1a.

**Spec de origen:** [`../specs/2026-09-14-pegado-accidental-fase-1-design.md`](../specs/2026-09-14-pegado-accidental-fase-1-design.md)
**Resultados que lo condicionan:** [Fase 1a](../specs/2026-09-15-pegado-accidental-fase-1a-resultados.md) · [Fase 1b](../specs/2026-09-15-pegado-accidental-fase-1b-resultados.md)
**Correcciones vigentes:** [`../specs/2026-09-13-pegado-accidental-correcciones.md`](../specs/2026-09-13-pegado-accidental-correcciones.md) (D1–D18)

---

## Por qué esta tanda y no la 1c

El spec preveía como tercera tanda la **1c**: los ocho modelos evaluados sobre el
mismo eje. Dos resultados la desplazan.

**La Fase 1a convirtió el contraste por familia en resultado, no en hipótesis.**
`gpt-5.6-luna` no contempla el error ni una vez en 96 conversaciones; Opus pone
19 de los 25 G. Lo que 1c añadiría es si los otros seis modelos se parecen a uno
o a otro — interesante, pero ya no es la pregunta del artículo.

**La Fase 1b cerró el eje sobre el brazo neutro.** Con un pegote sin señal, el
parecido no predice nada: las tres hipótesis planas, y el eje abarcaba de 0,109 a
0,453 de coseno, así que no fue por estrechez. Queda abierta la pregunta que sí
importa: **en el brazo donde los modelos SÍ dudan, ¿el parecido ayuda o estorba?**

Esa es esta tanda. El pegote lleva su señal dentro —va dirigido a otra persona,
está cortado, responde a algo que nadie preguntó, presupone una conversación que
no existe— y lo que se barre es cuánto se parece al tema en curso.

## Lo que ya está medido y no se vuelve a pagar

- **El eje de N1 es suficiente pero más estrecho que el de N0**: rangos de coseno
  por celda entre 0,219 y 0,369, mediana 0,290, ninguna celda por debajo del
  0,15 de D12. Medido en la Fase 1a sobre los 16 prefijos. La puerta se vuelve a
  comprobar antes de gastar, pero se espera GO.
- **Las señales SÍ se ordenan por coseno, y hay que controlarlo.** Era el riesgo
  serio de este diseño —si las cuatro señales se separan a lo largo del eje, un
  efecto de posición es un efecto de señal disfrazado— y una versión anterior de
  este plan lo daba por descartado comparando la **separación entre las medias**
  de las cuatro señales (0,055) con la **dispersión dentro** de cada señal
  (0,226). Los dos números son correctos y la comparación no vale: un rango de 4
  medias y una media de rangos de ~24 observaciones no son el mismo estadístico,
  y un rango crece con `n`. Sobre esas mismas 96 filas, la sd entre medias es
  0,023 y la sd dentro 0,070, y un ANOVA de un factor da **F(3,92) = 3,15,
  eta² = 0,093, p = 0,029**: las señales difieren en coseno.

| Señal | n | Coseno medio | Rango |
|---|---|---|---|
| `dirigido` | 24 | 0,275 | 0,196 – 0,378 |
| `presupone` | 24 | 0,272 | 0,157 – 0,374 |
| `cortado` | 26 | 0,245 | 0,108 – 0,374 |
| `responde` | 22 | 0,219 | 0,144 – 0,385 |

  Y lo decisivo no es la distribución marginal, porque **el barrido no la
  muestrea**: muestrea doce puestos fijos del ranking. Reconstruyendo los 16
  rankings N1 desde el campo `ranking` de las filas de 1a y aplicando
  `sweep_index(p, 44)` sobre el plan real (`plan_phase1b(20260916,
  level="N1")`), la composición por posición es **17 de 24 `cortado` en la
  posición 0** y **cero `cortado` contra 12 `dirigido` en la 11**. Mitad baja
  {`cortado` 58, `responde` 41, `presupone` 27, `dirigido` 18} contra mitad alta
  {`presupone` 53, `dirigido` 48, `cortado` 23, `responde` 20}: chi² = 44,4 con
  3 gl.

  Magnitud propagada sobre G con las tasas por señal de 1a en N1 (`dirigido`
  4/22, `presupone` 3/23, `cortado` 4/26, `responde` 8/22): **la composición
  sola mueve la tasa esperada +2,2 puntos agregada y +7,4 en `gpt-5.6-sol-tst`**
  entre la posición 0 y la 11, del mismo orden que el listón de 9 puntos de la
  puerta. En esta tanda la deriva va hacia ARRIBA, o sea **en contra de H4**, que
  predice bajada: enmascara el resultado primario en vez de fabricarlo. Pero nada
  en el diseño garantiza ese signo —con la señal de más G arriba en vez de abajo,
  la misma composición habría fabricado una subida que se leería como refutación
  fuerte— así que el control no es opcional y va en el código, no en la prosa:
  `curve.signal_confound` cuelga de todo `trend_report` y dice cuánto de la curva
  predice la mezcla por sí sola, y `curve.by_signal` da la curva DENTRO de cada
  señal. `by_kind` no cubre esto: controla por género (`artifact_kind`), no por
  señal.

- **El suelo de ruido entre réplicas**, medido en la Fase 1a: 0,87 sobre la
  etiqueta A–G en N1, y por conjunto binario hay que medirlo (Task 1, Paso 1).

## Global Constraints

- **Un solo brazo: N1**, los 44 artefactos de `data/artifacts-n1/`. N0 entra solo como referencia ya pagada (Fases 1a y 1b); no se vuelve a correr.
- **Los mismos tres modelos**: `gpt-5.6-sol-tst`, `gpt-5.6-luna-tst`, `claude-opus-5`.
- **Los 16 prefijos siguen en disco** y no se vuelven a pagar.
- **Rúbrica v2 sin cambios.** Tocarla obligaría a reclasificar 1a y 1b para poder comparar.
- **Juez primario `gpt-5.5-tst`** para todas las tasas reportadas. `gemini-2.5-flash` corre como segundo juez solo para el acuerdo entre jueces.
- **El juez NO es fiable para F** (auditoría de la Fase 1b: el autor confirmó tres F que el juez llamaba B). Si alguna cifra de esta tanda depende de F, va con etiquetas humanas o no va.
- **`JUDGE_MAX_TOKENS = 4000`**: los jueces razonan y el razonamiento gasta del mismo presupuesto.
- **Fallo como dato** (D6) y **nada de `temperature`/`budget_tokens` en Claude 5** (D9).
- **Endpoint y proyecto por variable de entorno** (D17).

---

## Las hipótesis, antes de mirar

**Primarias — la familia que corrige Holm (2 hipótesis × 3 modelos = 6 pruebas):**

- **H4 — `contempla que sea un error` (G) BAJA con el coseno.** La predicción
  tiene mecanismo: la señal del pegote es intrínseca, pero el modelo solo la usa
  si algo le hace mirar. Cuanto más encaja el pegote con el tema, menos motivo
  para mirar, y la señal se pasa por alto. Base de la Fase 1a en N1: 20,4 %.
- **H5 — G es MAYOR en las conversaciones largas.** La Fase 1a lo insinuó sin
  potencia: 6/47 con dos turnos previos contra 13/46 con diez. El mecanismo es el
  contrario del anterior: más contexto previo es más superficie contra la que el
  pegote desentona. Aquí se cruza longitud con posición, así que se contrasta con
  ~137 conversaciones por longitud.

**Secundarias — se reportan, no se declaran significativas.** Las tres de la Fase
1b (menciona el salto, puente confabulado, ejecuta en silencio) sobre este brazo,
para poder poner las dos tandas una al lado de la otra. Van fuera de la familia
de Holm **y el informe lo dice**: entran como descripción, no como contraste.

**Y una pregunta descriptiva, sin hipótesis:** ¿qué señal aguanta mejor el
parecido? Tabla de dos columnas (mitad baja / mitad alta), no cuatro curvas.
**Con el denominador de cada celda a la vista, que no es el mismo**: la versión
anterior de este plan suponía «~34 observaciones por señal y mitad del eje» y no
las hay —`dirigido` pone 18 en la mitad baja y `cortado` 23 en la alta, y en la
posición 11 `cortado` no aparece ni una vez—, así que las cuatro señales no ven
el mismo eje y la tabla no se puede leer como si lo vieran. Sale de
`curve.by_signal`, que lleva el `n` de cada mitad dentro.

---

## Estructura de ficheros

| Fichero | Responsabilidad |
|---|---|
| `src/wrongpaste/run_phase1b.py` | **Modificar.** `plan_phase1b` y `main` aceptan `level`. Sin runner nuevo: la única diferencia real es de qué banco sale el pegote. |
| `tests/test_run_phase1b.py` | **Modificar.** Que el barrido sobre N1 lleve la señal en la fila y que los identificadores no choquen con los de 1b. |
| `src/wrongpaste/curve.py` | **Modificar.** `PRIMARY_HYPOTHESES` deja de ser una constante única: cada tanda declara la suya, y el suelo de ruido binario de N1 se añade medido. Y el control de composición por señal (`signal_confound`, `by_signal`), sin el cual la curva de N1 no se puede leer. |
| `tests/test_curve.py` | **Modificar.** Que una familia mal declarada falle, y que una composición de señales desequilibrada no pase por curva. |

---

### Task 1: El suelo de ruido de N1 y la familia de esta tanda

**Files:**
- Modify: `src/wrongpaste/curve.py`
- Test: `tests/test_curve.py`

**Interfaces:**
- Produces: `REPLICATE_AGREEMENT_BY_MEMBER` ampliado con la entrada de `{"G"}` en N1; `HYPOTHESIS_FAMILIES: dict[str, dict[str, frozenset[str]]]`; `primary_family_report(rows, family, ...)`.

- [ ] **Paso 1: Medir el acuerdo binario entre réplicas para G en N1**

No se inventa: se mide sobre los datos de la Fase 1a, igual que se midieron los
tres de la Fase 1b.

```bash
cd ~/Documents/repos/llm-wrong-paste
.venv/bin/python - <<'EOF'
import json, collections, sys
sys.path.insert(0,'src')
from wrongpaste.rubric import MENTIONS_JUMP
rows=[json.loads(l) for l in open('runs/phase1a/20260914T135814.jsonl',encoding='utf-8') if l.strip()][1:]
ver=[json.loads(l) for l in open('runs/phase1a/verdicts-20260914T135814.jsonl',encoding='utf-8') if l.strip()]
cat={v['conversation_id']:v['category'] for v in ver if v['judge_model']=='gpt-5.5-tst' and v['status']=='ok'}
pares=collections.defaultdict(dict)
for r in rows:
    if r['paste_level']!='N1' or r['status']!='ok': continue
    c=cat.get(r['conversation_id'])
    if c: pares[(r['model_id'],r['topic_id'],r['n_turns'],r['artifact_id'])][r['replicate_idx']]=c
comp={k:v for k,v in pares.items() if len(v)==2}
for nom, pred in (('G', lambda c: c=='G'), ('menciona el salto', lambda c: c in MENTIONS_JUMP)):
    ig=sum(1 for v in comp.values() if pred(v[0])==pred(v[1]))
    print(f'{nom:<20} {ig}/{len(comp)} = {ig/len(comp):.3f}')
EOF
```

Anotar el número que salga: es el umbral de la puerta de esta tanda.

- [ ] **Paso 2: Escribir el test de la familia declarada**

```python
# tests/test_curve.py (añadir)
def test_cada_tanda_declara_su_propia_familia():
    """Una familia global para todas las tandas corrige por pruebas que esta
    tanda no ha corrido, y deja fuera las que sí."""
    from wrongpaste.curve import HYPOTHESIS_FAMILIES

    assert "1b" in HYPOTHESIS_FAMILIES and "1d" in HYPOTHESIS_FAMILIES
    assert set(HYPOTHESIS_FAMILIES["1b"]) == {
        "H1 menciona el salto", "H2 puente confabulado", "H3 ejecuta en silencio"}
    assert set(HYPOTHESIS_FAMILIES["1d"]) == {"H4 contempla el error"}


def test_el_informe_de_familia_corrige_por_el_tamano_declarado(monkeypatch):
    """Seis pruebas y no nueve: Holm tiene que ver la familia de ESTA tanda."""
    from wrongpaste.curve import HYPOTHESIS_FAMILIES, primary_family_report

    filas = [_fila(p, "G" if p < 4 else "A", model=m)
             for m in ("gpt-5.6-sol-tst", "gpt-5.6-luna-tst", "claude-opus-5")
             for p in range(12) for _ in range(2)]
    rep = primary_family_report(filas, family=HYPOTHESIS_FAMILIES["1d"])
    assert rep["family_size"] == 3, "1 hipótesis x 3 modelos"


def test_el_suelo_binario_de_G_esta_medido_y_no_inventado():
    from wrongpaste.curve import replicate_agreement
    assert replicate_agreement({"G"}) is not None
```

- [ ] **Paso 3: Correr y ver fallar**

Run: `.venv/bin/python -m pytest tests/test_curve.py -k familia -v`
Expected: FAIL con `ImportError: cannot import name 'HYPOTHESIS_FAMILIES'`

- [ ] **Paso 4: Implementar**

```python
# src/wrongpaste/curve.py — sustituye a PRIMARY_HYPOTHESES
# Cada tanda declara SU familia. Una familia global corregiría por pruebas que
# esta tanda no ha corrido y dejaría fuera las que sí: Holm necesita ver
# exactamente el conjunto que se contrastó, ni uno más ni uno menos.
HYPOTHESIS_FAMILIES: dict[str, dict[str, frozenset[str]]] = {
    "1b": {
        "H1 menciona el salto": MENTIONS_JUMP,
        "H2 puente confabulado": frozenset({"E"}),
        "H3 ejecuta en silencio": frozenset({"A"}),
    },
    # La Fase 1d tiene UNA hipótesis de conjunto —G— y una segunda, H5, que no
    # es un conjunto distinto sino el mismo partido por longitud: se contrasta
    # con el mismo `member` sobre dos subconjuntos de filas, así que entra en la
    # familia como dos pruebas más por modelo al construir el informe.
    "1d": {"H4 contempla el error": ENTERTAINS_ERROR},
}

PRIMARY_HYPOTHESES = HYPOTHESIS_FAMILIES["1b"]  # compatibilidad con la Fase 1b
```

Y `primary_family_report` pasa a aceptar `family` con `HYPOTHESIS_FAMILIES["1b"]`
por defecto, para que el análisis de la Fase 1b siga dando exactamente lo mismo.

Añadir además a `REPLICATE_AGREEMENT_BY_MEMBER` la entrada `("G",)` con el
número medido en el Paso 1, y su comentario diciendo de dónde sale.

- [ ] **Paso 5: Correr, ver pasar, y comprobar que la Fase 1b no se movió**

```bash
.venv/bin/python -m pytest tests/ -q --ignore=tests/test_smoke_live.py
```
Expected: PASS. Y volver a correr el análisis de la Fase 1b guardado en
`runs/phase1b/` para confirmar que los `p_holm` salen idénticos a los del
documento de resultados: si cambian, la refactorización rompió la comparabilidad.

- [ ] **Paso 6: Commit** (lo hace el orquestador; los subagentes no commitean)

---

### Task 2: El runner, parametrizado por nivel

**Files:**
- Modify: `src/wrongpaste/run_phase1b.py`
- Test: `tests/test_run_phase1b.py`

**Interfaces:**
- Produces: `plan_phase1b(seed, level="N0")`, `main(seed=MASTER_SEED, out=None, measure=True, level="N0")`, `PHASE_BY_LEVEL = {"N0": "1b", "N1": "1d"}`.

- [ ] **Paso 1: Escribir los tests**

```python
# tests/test_run_phase1b.py (añadir)
def test_el_plan_de_n1_tiene_las_mismas_288_celdas():
    plan = plan_phase1b(1, level="N1")
    assert len(plan) == SWEEP_POSITIONS * 8 * len(PHASE1B_MODELS)
    assert {c["paste_level"] for c in plan} == {"N1"}


def test_los_identificadores_de_n1_no_chocan_con_los_de_n0():
    """Las dos tandas viven en el mismo repositorio y se analizan juntas: dos
    filas con el mismo `conversation_id` y distinto banco harían que una
    reanudación diera por hecha una celda de la otra tanda."""
    n0 = {c["conversation_id"] for c in plan_phase1b(1, level="N0")}
    n1 = {c["conversation_id"] for c in plan_phase1b(1, level="N1")}
    assert not (n0 & n1), sorted(n0 & n1)[:3]


def test_la_fila_de_n1_lleva_la_senal_del_pegote(harness, tmp_path):
    """Sin la señal en la fila, la pregunta de qué pista funciona no se puede
    responder después sin volver a abrir el banco."""
    path = rp.main(seed=1, out=tmp_path / "t.jsonl", measure=False, level="N1")
    _, rows = _rows(path)
    assert all(r["paste_level"] == "N1" for r in rows)
    assert all(r["artifact_signal"] for r in rows if r["status"] == "ok")


def test_el_plan_de_n0_no_cambia(harness, tmp_path):
    """Regresión: parametrizar no puede mover la tanda ya pagada."""
    import json as _json
    antes = _json.dumps(plan_phase1b(20260915))
    despues = _json.dumps(plan_phase1b(20260915, level="N0"))
    assert antes == despues
```

- [ ] **Paso 2: Correr y ver fallar**

Run: `.venv/bin/python -m pytest tests/test_run_phase1b.py -k "n1 or no_cambia" -v`
Expected: FAIL con `TypeError: plan_phase1b() got an unexpected keyword argument 'level'`

- [ ] **Paso 3: Implementar**

`plan_phase1b(seed, level="N0")` añade `"paste_level": level` y el
`conversation_id` lleva el prefijo de fase: `p1b-` para N0 y `p1d-` para N1, vía
`PHASE_BY_LEVEL`. `main(..., level="N0")` carga `load_artifacts(level=level)`,
escribe `"phase": PHASE_BY_LEVEL[level]` en la cabecera y guarda en
`runs/phase1d/` cuando el nivel es N1. El resto no se toca.

- [ ] **Paso 4: Correr y ver pasar**

Run: `.venv/bin/python -m pytest tests/test_run_phase1b.py -v`
Expected: PASS

- [ ] **Paso 5: Ensayo en seco contra el banco real**

```bash
cd ~/Documents/repos/llm-wrong-paste
.venv/bin/python -c "
import sys, collections; sys.path.insert(0,'src')
from wrongpaste.artifacts import load_artifacts
from wrongpaste.run_phase1b import plan_phase1b, sweep_index, SWEEP_POSITIONS
b=load_artifacts(level='N1'); plan=plan_phase1b(20260916, level='N1')
print('banco N1:', len(b), '| celdas:', len(plan))
print('índices:', [sweep_index(p, len(b)) for p in range(SWEEP_POSITIONS)])
print('longitudes por posición:', {p: dict(collections.Counter(
    c['n_turns'] for c in plan if c['sweep_position']==p)) for p in range(3)})
"
```

Expected: 44 artefactos, 288 celdas, índices repartidos de 0 a 43, y `{2: 12, 10: 12}` en cada posición.

- [ ] **Paso 6: Commit** (lo hace el orquestador)

---

### Task 3: Correr, clasificar, validar y decidir

- [ ] **Paso 1: Comprobar los cinco modelos por su camino real**

Los tres evaluados con `max_tokens=256` y una respuesta visible; los dos jueces
con `judge_all` sobre una fila real. Con `max_tokens=16` un modelo que razona
devuelve vacío y el chequeo miente.

- [ ] **Paso 2: Decir tiempo y coste partidos por proveedor, antes de gastar**

Referencia medida en la Fase 1b: 3 h 08 min para 288 celdas del mismo tamaño.
**Estimación: ≈30 $ de conversaciones (dos tercios gateway/Azure, un tercio
Vertex/GCP) + ≈10 $ de los dos jueces.** Si pasa de 50 $, parar y revisar.

- [ ] **Paso 3: Lanzar, sin buffer y en segundo plano**

```bash
cd ~/Documents/repos/llm-wrong-paste
export WRONGPASTE_GATEWAY_URL="https://litellm.infra.skyc.cloud"
export WRONGPASTE_GCP_PROJECT="data-science-364702"
mkdir -p runs/phase1d
nohup .venv/bin/python -u -c "
import sys; sys.path.insert(0,'src')
from wrongpaste.run_phase1b import main
main(seed=20260916, level='N1')
" > runs/phase1d/run.log 2>&1 &
```

- [ ] **Paso 4: Leer las trazas antes de concluir nada**

```bash
python3 ~/.claude/bin/leer-trazas.py runs/phase1d/<run_id>.jsonl
```

Y cuantificar las pérdidas **por posición y por señal**. Criterio declarado: si
más de un tercio de las no-ok cae en dos posiciones contiguas, o si una señal
pierde más del doble que las otras, el hueco es sistemático y hay que decirlo.

- [ ] **Paso 5: Clasificar con los dos jueces**

`run_judging` sobre el JSONL. Reportar acuerdo entre jueces y uso de Z. **Ojo
con gemini**: su defecto conocido es inflar G, y esta tanda mide G. Las cifras
salen de `gpt-5.5` y el acuerdo con gemini se reporta como control, no como
respaldo.

- [ ] **Paso 6: 60 etiquetas a ciegas + auditoría del autor sobre 10**

`blind_sample(..., strata_keys=("sweep_position", "model_id"))`. La auditoría se
carga hacia **la frontera C/G**, que es la que decide esta tanda, y hacia el
tramo alto del eje. Página de auditoría como las anteriores, con `db`.

- [ ] **Paso 7: Contrastar H4 y H5, y reportar las secundarias**

```bash
.venv/bin/python - <<'EOF'
import sys; sys.path.insert(0,'src')
from wrongpaste.curve import (
    HYPOTHESIS_FAMILIES, primary_family_report, trend_report, by_kind, by_signal)
from wrongpaste.rubric import ENTERTAINS_ERROR
# H4: tendencia de G contra la posición, por modelo
rep = primary_family_report(filas, family=HYPOTHESIS_FAMILIES["1d"])
# Y ANTES de leer ninguna pendiente: cuánto de esa curva predice la mezcla de
# señales por sí sola. `signal_confound` cuelga de cada informe de hipótesis.
for nombre, inf in rep["hypotheses"].items():
    c = inf["signal_confound"]
    print(nombre, "| composición equilibrada:", c["balanced"],
          "| la mezcla sola mueve:", round(c["expected_span"], 3),
          "| observado extremo a extremo:", round(c["observed_delta"], 3))
# H5: G por longitud, con su intervalo
for n in (2, 10):
    sub=[f for f in filas if f["n_turns"]==n]
    g=sum(1 for f in sub if f["judge_category"]=="G")
    print(f"n={n}: {g}/{len(sub)} = {g/len(sub):.3f}")
# descriptivo: qué señal aguanta el parecido, con el `n` de cada mitad delante
desc = by_signal(filas, ENTERTAINS_ERROR)
for senal, sub in desc["by_signal"].items():
    print(senal, sub["halves"])
EOF
```

- [ ] **Paso 8: La puerta de la serie**

Criterio declarado antes de mirar, y con el listón que dejó la Fase 1b:

- **H4 o H5 se sostienen** si sobreviven a Holm **y** mueven la tasa más que el
  suelo binario de G medido en el Paso 1 de la Task 1 **y más de 9 puntos**, que
  es lo que separó a dos tandas de la misma condición en 1a/1b. Ese listón no es
  opcional: un efecto menor que la variación entre tandas no se distingue de
  haber vuelto a tirar.
- **Y una condición más, por la composición**: lo que se compara con ese listón
  es el movimiento observado **descontado el que la mezcla de señales predice
  por sí sola** (`signal_confound["expected_span"]`, estimado a priori en 2,2
  puntos agregados y 7,4 en `gpt-5.6-sol-tst`). Una pendiente que no supere lo
  que la composición ya explica no es un efecto del eje, y en este brazo la
  composición empuja hacia arriba, así que a H4 —que predice bajada— le juega en
  contra: una bajada observada está, si acaso, infraestimada.
- **Si ninguna se sostiene**, lo primero que hay que mirar NO es la conclusión
  sino `null_is_informative` del informe de familia. 288 celdas entre 3 modelos y
  12 posiciones son **8 observaciones por punto y por modelo**, y con las tasas
  base de G medidas en N1 en la Fase 1a (Opus 16/29, sol 3/32, luna 0/32) eso
  **no** ve la caída de 9 puntos que este mismo paso declara relevante: la
  potencia de H4 en Opus es del 2 % con el alfa que paga el `p` más pequeño de
  una familia de seis, y lo que sí vería —al 80 %— es una caída de **56 puntos**.
  Para ver los 9 harían falta ~313 observaciones por punto y modelo, o sea unas
  39 veces esta tanda. Así que:
  - Con `null_is_informative: false` —que es lo que el diseño actual devuelve—
    el resultado que se escribe es **«no lo hemos podido ver»**, con el efecto
    mínimo detectable al lado, igual que la Fase 1b escribió H2 como «sin nada
    que medir». Un nulo sin potencia no es evidencia de ausencia, y publicar
    *«el parecido no importa»* con este n sería certificar como resultado el
    desenlace casi seguro del diseño.
  - Solo con `null_is_informative: true` se puede escribir el resultado fuerte:
    *la conducta de dudar depende de que el pegote lleve una señal dentro, y de
    nada más que hayamos sabido medir* — ni del parecido, ni de la longitud.
- **Si alguna se sostiene**, hay curva que dibujar y el artículo 2 tiene su
  figura principal.

- [ ] **Paso 9: Escribir los resultados y commitear en los dos repos**

---

## Lo que este plan NO cubre

- **La Fase 1c** (los ocho modelos). Después de 1a su motivo cambió: ya no prueba el contraste por familia, lo extiende. Sigue disponible si esta tanda deja preguntas abiertas.
- **La Fase 2** (el turno de reparación), que sigue siendo otro artículo.
- **Una medida fiable de F.** El juez no sirve para eso (auditoría de 1b) y el banco arreglado del §5 de aquellos resultados está pensado justo para provocarla: hace falta un diseño con etiquetas humanas, y no es esta tanda.
