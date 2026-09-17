# Fase 2 del pegado accidental — plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** poder correr el piloto de la Fase 2 —cinco brazos de reparación colgados de las reacciones ya pagadas de la tanda 1d, con tarea verificable aguas abajo y recuento de fuga— con su potencia declarada antes de gastar.

**Architecture:** los cuatro brazos pareados se generan continuando transcripciones guardadas con `resume_post_turns`, que ya existe; lo nuevo es el turno literal de reparación (etiqueta `repair`, ya reservada en `USER_HIDDEN_TAGS`), el turno literal de tarea, el verificador numérico y la prueba pareada. El quinto brazo —(0) sin pegote— es una tanda corta aparte porque no comparte base con ninguno.

**Tech Stack:** Python 3.12, `.venv/bin/python`, pytest. Sin dependencias nuevas: la prueba pareada es McNemar en forma cerrada con `math.erfc`, igual que Cochran-Armitage en `curve.py`.

**Spec:** [`../specs/2026-09-17-pegado-accidental-fase-2-design.md`](../specs/2026-09-17-pegado-accidental-fase-2-design.md)

**Repo:** `~/Documents/repos/llm-wrong-paste` (público). Todos los caminos son relativos a él.

## Global Constraints

- **Ningún test llama a un modelo de verdad.** Los que necesitan una respuesta la
  falsean con `monkeypatch` sobre `chat`, como los de `test_judging_ejes.py`.
- **Los fallos son datos, no excepciones** (D6): `ok | http_error | timeout |
  refusal | empty | truncated | harness_error`, y `DONE_STATUSES = {"ok",
  "refusal", "truncated"}`.
- **Los comentarios y docstrings van en español**, y explican *por qué*, no
  *qué*: es el estilo de todo el repo y el material del que salen los artículos.
- **`MIN_POWER = 0,80` sobre `DECLARED_DROP = 0,09`**, y las familias de Holm son
  las dos del §7 del spec. Ninguna tanda se compra sin la potencia declarada por
  delante.
- **Nada de recuentos del diseño escritos a mano.** El repo ya se quemó con un
  predicado que exigía «1.152» contra un plan que decía «1.152» mientras el
  diseño estaba en 1.344: los dos rancios a la vez, el test pasando en vacío.
  Todo número de celdas se deriva del plan.
- **Etiquetas de mensaje**: `paste`, `repair` (nueva, ya reservada), `task`
  (nueva), `post`, `user_sim`, `assistant`.

## Estructura de ficheros

| Fichero | Responsabilidad |
|---|---|
| `src/wrongpaste/tasks.py` | **nuevo.** Extraer números de un texto en español y decidir si la tarea está acertada. Puro, sin red. |
| `data/topics/*.md` (8) | Se rellena el hueco D13: `task`, `expected`, `verifier`. |
| `src/wrongpaste/repair.py` | **nuevo.** Los cinco brazos y su texto literal. |
| `src/wrongpaste/conversation.py` | `continue_with_repair`, hermana de `continue_after_paste`. |
| `src/wrongpaste/leak.py` | **nuevo.** Fuga de entidades por turno y binaria por conversación. |
| `src/wrongpaste/curve.py` | `mcnemar`, `paired_power`, `HYPOTHESIS_FAMILIES_F2`. |
| `src/wrongpaste/run_phase2.py` | **nuevo.** Muestreo de bases, plan, presupuesto, puertas, tirada y reanudación. |
| `src/wrongpaste/run_phase2_control.py` | **nuevo.** El brazo (0), sin pegote. |

---

### Task 1: El verificador numérico

**Files:**
- Create: `src/wrongpaste/tasks.py`
- Test: `tests/test_tasks.py`

**Interfaces:**
- Consumes: nada.
- Produces: `numbers_in(text: str) -> list[float]`,
  `parse_expected(raw: str) -> float`,
  `check_task(answer: str, expected: float) -> TaskResult`,
  `task_ok(answer: str, expected: float) -> bool`,
  `TaskResult` (dataclass: `ok: bool`, `found: list[float]`, `expected: float`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_tasks.py
"""El verificador de la tarea aguas abajo.

Lo que se prueba no es que sepa leer un número: es que sepa leer un número
ESPAÑOL sin confundir el separador de millares con la coma decimal, porque el
tema `huerto-balcon` tiene los dos en la misma respuesta.
"""
import pytest

from wrongpaste.tasks import numbers_in, parse_expected, task_ok


@pytest.mark.parametrize("texto, esperado, quiero", [
    # El caso que obliga a todo lo demás: 28.800 cm3 y 28,8 litros juntos.
    ("El volumen es 80 x 20 x 18 = 28.800 cm3, o sea 28,8 litros.", 28.8, True),
    ("El volumen es 28.800 cm3.", 28.8, False),
    # El otro: 3.300 segundos en total contra 330 por kilómetro.
    ("Son 3.300 segundos en total, es decir 330 s/km.", 330, True),
    ("La carrera entera son 3300 segundos.", 330, False),
    # Las dos grafías del millar valen; las dos del decimal también.
    ("Te sobran 4.920 litros.", 4920, True),
    ("Te sobran 4920 litros.", 4920, True),
    ("Suman 40,44 EUR", 40.44, True),
    ("Suman 40.44 EUR", 40.44, True),
    # Redondear es fallar: si el modelo dice «unos 40», no ha hecho la cuenta.
    ("Suman unos 40 EUR", 40.44, False),
    # Un intermedio no cuenta como respuesta.
    ("Los pasos son 2,7 + 3,15 + 1,6.", 7.45, False),
])
def test_el_verificador_lee_numeros_espanoles(texto, esperado, quiero):
    assert task_ok(texto, esperado) is quiero


def test_sin_numero_reconocible_es_fallo():
    """Una respuesta que se va por las ramas no es media respuesta."""
    assert task_ok("Depende de la tarifa que tengas contratada.", 40.44) is False


def test_el_esperado_se_lee_con_coma_decimal():
    """Los ficheros de tema están en español y escriben `expected: 40,44`."""
    assert parse_expected("40,44") == pytest.approx(40.44)
    assert parse_expected("4.920") == pytest.approx(4920)
    assert parse_expected("330") == pytest.approx(330)


def test_los_numeros_se_devuelven_en_orden_de_aparicion():
    """`found` va al JSONL: sirve para releer a mano por qué una fila falló."""
    assert numbers_in("primero 12, luego 3,5 y al final 1.000") == [12, 3.5, 1000]


def test_un_separador_de_tres_digitos_sin_mas_grupos_es_millar():
    """«1.025 euros» son mil veinticinco, no uno coma cero dos cinco."""
    assert numbers_in("Son 1.025 euros") == [1025]


def test_un_separador_de_dos_digitos_es_decimal():
    """«40.44» no puede ser un millar: los millares van de tres en tres."""
    assert numbers_in("Suman 40.44") == [40.44]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_tasks.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'wrongpaste.tasks'`

- [ ] **Step 3: Write the implementation**

```python
# src/wrongpaste/tasks.py
"""Decide si la respuesta del modelo acierta la tarea verificable del tema.

**Por qué extrae y normaliza en vez de buscar el número esperado.** El enfoque
obvio —montar un regex de «4.920» que además acepte «4920» y no acepte
«49.200»— se probó sobre once respuestas de muestra y falló en tres. Construir
esa expresión es un problema más difícil que el que resuelve.

**La trampa que hay que respetar es española.** «28.800» son veintiocho mil
ochocientos y «28.8» son veintiocho coma ocho, y el tema `huerto-balcon` los
tiene los dos en la misma respuesta: el volumen en centímetros cúbicos y el
resultado en litros. La regla que los separa: un separador seguido de
EXACTAMENTE tres dígitos, con más grupos de tres delante o detrás, es de
millares; cualquier otro es decimal.

**Redondear es fallar.** «Unos 40 euros» no cuenta como 40,44. No es severidad
gratuita: la comparación de la Fase 2 es entre brazos con la misma tarea, así
que una regla dura baja los cinco brazos por igual y no puede fabricar una
diferencia. Lo que sí podría es aplastar la escala, y para eso está el brazo (0)
del piloto, que mide el acierto sin pegote antes de comprar nada.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Un número con separadores de millares (uno o más grupos de tres) y decimal
# opcional, o un número llano con decimal opcional. El orden de las alternativas
# importa: la primera tiene que poder ganar, o «1.025» se leería como «1».
_NUM = re.compile(r"\d{1,3}(?:[.,  ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?")

# La forma completa «grupos de tres + decimal opcional», para decidir si los
# separadores de un token son de millares.
_MILES = re.compile(r"(\d{1,3}(?:[.,]\d{3})+)([.,]\d+)?")

# Margen de comparación. No es tolerancia de redondeo —redondear es fallar—:
# es el epsilon de coma flotante, para que 0,45*6+0,35*9+0,20*8 case con 7,45.
_EPS = 1e-9


@dataclass(frozen=True)
class TaskResult:
    """El veredicto de la tarea y el rastro para poder releerlo a mano."""

    ok: bool
    found: list[float]
    expected: float


def numbers_in(text: str) -> list[float]:
    """Todos los números del texto, normalizados, en orden de aparición."""
    out: list[float] = []
    for token in _NUM.findall(text):
        token = token.replace(" ", "").replace(" ", "")
        miles = _MILES.fullmatch(token)
        if miles:
            entero = re.sub(r"[.,]", "", miles.group(1))
            decimal = miles.group(2).replace(",", ".") if miles.group(2) else ""
            token = entero + decimal
        else:
            token = token.replace(",", ".")
        try:
            out.append(float(token))
        except ValueError:
            # Un token que el regex aceptó y float no: se ignora en vez de
            # reventar. Esto corre sobre texto de un modelo, no sobre datos.
            continue
    return out


def parse_expected(raw: str) -> float:
    """El `expected` del fichero de tema, que está escrito en español."""
    numeros = numbers_in(raw)
    if len(numeros) != 1:
        raise ValueError(
            f"`expected` tiene que ser UN número y {raw!r} da {numeros}: un "
            "esperado ambiguo convierte el verificador en una opinión"
        )
    return numeros[0]


def check_task(answer: str, expected: float) -> TaskResult:
    """El veredicto completo, con los números que se encontraron."""
    found = numbers_in(answer)
    return TaskResult(
        ok=any(abs(n - expected) < _EPS for n in found),
        found=found,
        expected=expected,
    )


def task_ok(answer: str, expected: float) -> bool:
    return check_task(answer, expected).ok
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_tasks.py -q`
Expected: PASS (13 tests)

- [ ] **Step 5: Commit**

```bash
git add src/wrongpaste/tasks.py tests/test_tasks.py
git commit -m "Verificador numérico de la tarea, con la trampa del millar español"
```

---

### Task 2: Las ocho tareas en disco

**Files:**
- Modify: `data/topics/carrera-10k.md`, `elegir-camara.md`, `elegir-colegio.md`, `factura-luz.md`, `hacer-pan.md`, `huerto-balcon.md`, `mudanza.md`, `viaje-japon.md`
- Test: `tests/test_topics_tasks.py`

**Interfaces:**
- Consumes: `tasks.parse_expected` (Task 1), `topics.load_topics` (ya existe).
- Produces: los ocho `Topic` con `task`, `expected` y `verifier` no nulos.

El parser de `topics.py` **no hay que tocarlo**: lee `task:`, `expected:` y
`verifier:` del cuerpo con `split(":", 1)`, así que un texto de tarea con dos
puntos dentro se lee entero. `verifier: numero` nombra la estrategia; el valor
va en `expected`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_topics_tasks.py
"""El hueco D13, ya relleno.

Estos tests no comprueban que el fichero tenga texto: recalculan las ocho
cuentas y comprueban las tres condiciones que el spec le exige a una tarea. Una
tarea mal escrita es un resultado falso, no un fallo ruidoso.
"""
import pytest

from wrongpaste.tasks import numbers_in, parse_expected
from wrongpaste.topics import load_topics

# La cuenta de cada tema, escrita aquí a mano y a propósito: si el valor
# esperado del fichero se editara sin recalcular, este test lo caza. Los
# intermedios son los que un modelo escribe por el camino.
CUENTAS = {
    "carrera-10k":    (55 * 60 / 10,                 [55, 10, 3300]),
    "elegir-camara":  (35 * 1.5,                     [35, 1.5]),
    "elegir-colegio": (.45 * 6 + .35 * 9 + .20 * 8,  [2.7, 3.15, 1.6, 6, 9, 8]),
    "factura-luz":    (4.6 * .08 * 30 + 210 * .14,   [11.04, 29.4, 4.6, 30, 210]),
    "hacer-pan":      (500 * .70,                    [500, 0.7]),
    "huerto-balcon":  (80 * 20 * 18 / 1000,          [80, 20, 18, 1600, 28800]),
    "mudanza":        (6000 - 18 * 60,               [18, 60, 1080, 6000]),
    "viaje-japon":    ((12 * 9500 + 50000) / 160,    [12, 9500, 50000, 114000, 164000, 160]),
}


@pytest.fixture(scope="module")
def temas():
    return {t.id: t for t in load_topics()}


def test_los_ocho_temas_tienen_tarea(temas):
    """El hueco D13 deja de estar a None: sin esto no hay Fase 2."""
    sin = [tid for tid, t in temas.items() if not (t.task and t.expected and t.verifier)]
    assert not sin, f"temas sin tarea verificable: {sin}"


def test_hay_una_cuenta_declarada_por_tema(temas):
    """Si se añade un tema y no se le escribe la cuenta aquí, salta."""
    assert set(CUENTAS) == set(temas)


@pytest.mark.parametrize("tid", sorted(CUENTAS))
def test_el_esperado_del_fichero_es_la_cuenta_recalculada(temas, tid):
    valor, _ = CUENTAS[tid]
    assert parse_expected(temas[tid].expected) == pytest.approx(valor)


@pytest.mark.parametrize("tid", sorted(CUENTAS))
def test_el_resultado_no_coincide_con_ningun_intermedio(temas, tid):
    """Condición 2 del spec: si el resultado es un paso intermedio del cálculo
    natural, el verificador acierta viendo al modelo pensar en voz alta."""
    valor, intermedios = CUENTAS[tid]
    choca = [i for i in intermedios if abs(i - valor) < 1e-9]
    assert not choca, f"{tid}: el resultado {valor} es también un intermedio"


@pytest.mark.parametrize("tid", sorted(CUENTAS))
def test_el_resultado_es_distintivo(temas, tid):
    """Condición 3: al menos tres dígitos. Un «5» aparece en cualquier respuesta
    y convertiría el acierto en ruido."""
    valor, _ = CUENTAS[tid]
    digitos = sum(c.isdigit() for c in f"{valor:g}")
    assert digitos >= 3, f"{tid}: {valor} tiene {digitos} dígitos, es poco distintivo"


@pytest.mark.parametrize("tid", sorted(CUENTAS))
def test_el_enunciado_lleva_dentro_todos_los_datos(temas, tid):
    """La tarea no puede depender de nada dicho antes en la conversación: si
    dependiera, el prefijo —que varía— entraría en la variable dependiente."""
    _, intermedios = CUENTAS[tid]
    en_enunciado = set(numbers_in(temas[tid].task))
    # Los datos de entrada son los intermedios que NO son resultados de operar.
    faltan = [i for i in intermedios if i in (55, 10, 35, 1.5, 6, 9, 8, 4.6, 30,
                                              210, 500, 80, 20, 18, 60, 12,
                                              9500, 50000, 160)
              and i not in en_enunciado]
    assert not faltan, f"{tid}: el enunciado no trae {faltan}"


@pytest.mark.parametrize("tid", sorted(CUENTAS))
def test_el_verificador_declarado_existe(temas, tid):
    assert temas[tid].verifier == "numero"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_topics_tasks.py -q`
Expected: FAIL en `test_los_ocho_temas_tienen_tarea` con los ocho temas listados.

- [ ] **Step 3: Rellenar los ocho ficheros**

En cada `data/topics/<id>.md`, sustituir el bloque de tres líneas comentadas del
hueco D13 por las tres líneas reales. El comentario explicativo se reescribe
para que diga lo que ahora es verdad. Ejemplo completo para `factura-luz.md`:

```markdown
# Hueco D13, relleno en la Fase 2: la tarea verificable del tema. El resultado
# no cambia por el pegote, así que cualquier caída de acierto es contaminación.
# Los tres datos del enunciado van dentro del propio enunciado: si dependieran
# de algo dicho antes, el prefijo —que varía— entraría en la variable medida.
task: Antes de seguir, échame una cuenta: tengo 4,6 kW de potencia contratada a 0,08 € por kW y día, el periodo son 30 días, y he consumido 210 kWh a 0,14 € el kWh. ¿Cuánto suman el término de potencia y el de energía, sin impuestos?
expected: 40,44
verifier: numero
```

Los otros siete, con el texto exacto de la tabla del §5.2 del spec:

| Tema | `expected` |
|---|---|
| `carrera-10k` | `330` |
| `elegir-camara` | `52,5` |
| `elegir-colegio` | `7,45` |
| `hacer-pan` | `350` |
| `huerto-balcon` | `28,8` |
| `mudanza` | `4.920` |
| `viaje-japon` | `1.025` |

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_topics_tasks.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add data/topics tests/test_topics_tasks.py
git commit -m "Hueco D13 relleno: ocho tareas verificables, recalculadas en los tests"
```

---

### Task 3: Los cinco brazos

**Files:**
- Create: `src/wrongpaste/repair.py`
- Test: `tests/test_repair.py`

**Interfaces:**
- Consumes: `topics.Topic`.
- Produces: `ARMS: tuple[str, ...]` = `("a", "b", "c", "d")`, `CONTROL_ARM = "0"`,
  `PAIRED_ARMS`, `repair_text(arm: str, topic: Topic) -> str | None`,
  `ARM_LABEL: dict[str, str]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_repair.py
"""Los textos de reparación.

Son literales a propósito (§4 del spec original): si variaran por celda, no
compararíamos reparaciones sino parejas. Estos tests son los que impiden que
alguien los «mejore» sin darse cuenta de lo que rompe.
"""
import pytest

from wrongpaste.repair import ARMS, CONTROL_ARM, PAIRED_ARMS, repair_text
from wrongpaste.topics import load_topics


@pytest.fixture(scope="module")
def tema():
    return {t.id: t for t in load_topics()}["factura-luz"]


def test_el_brazo_sin_reparacion_no_tiene_texto(tema):
    """(a) es «el usuario sigue como si nada»: el turno lo escribe el usuario
    simulado, no un literal. Devolver cadena vacía lo haría pasar por un turno
    de reparación vacío."""
    assert repair_text("a", tema) is None


def test_la_reparacion_escueta_es_dos_palabras(tema):
    assert repair_text("b", tema) == "Ignóralo."


def test_la_reparacion_explicada_nombra_el_tema(tema):
    """(c) se diferencia de (b) exactamente en el contexto; si no nombrara el
    tema, las dos variantes serían la misma con más letras."""
    texto = repair_text("c", tema)
    assert "era para otro chat" in texto
    assert tema.id.replace("-", " ") in texto.lower() or "luz" in texto.lower()


def test_el_pivote_afirma_lo_contrario_que_la_escueta(tema):
    """El control decisivo: (b) dice «esto no va aquí» y (d) «esto sí va aquí».
    Si se parecieran, el contraste no probaría nada."""
    assert repair_text("d", tema) == "Sí, hablemos de eso."


def test_solo_c_depende_del_tema():
    """(b) y (d) tienen que ser idénticos en las ocho conversaciones, o la
    comparación entre temas mezclaría el texto con el tema."""
    temas = load_topics()
    for arm in ("b", "d"):
        textos = {repair_text(arm, t) for t in temas}
        assert len(textos) == 1, f"el brazo {arm} cambia de texto según el tema"
    assert len({repair_text("c", t) for t in temas}) == len(temas)


def test_el_control_sin_pegote_no_esta_entre_los_pareados():
    """(0) no cuelga de ninguna base: meterlo en PAIRED_ARMS haría que el
    muestreo intentara parearlo y el análisis lo contara como pareja."""
    assert CONTROL_ARM not in PAIRED_ARMS
    assert set(PAIRED_ARMS) == set(ARMS)


def test_un_brazo_inventado_se_rechaza(tema):
    with pytest.raises(ValueError, match="brazo"):
        repair_text("z", tema)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_repair.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'wrongpaste.repair'`

- [ ] **Step 3: Write the implementation**

```python
# src/wrongpaste/repair.py
"""Los cinco brazos de la Fase 2 y su texto literal.

**Por qué son literales.** El §4 del spec original: el turno del pegote y el de
reparación son texto idéntico para todas las celdas. Si variaran, no estaríamos
comparando modelos ni reparaciones sino parejas modelo-redacción.

**Por qué (a) devuelve None y no cadena vacía.** En (a) el usuario no repara: el
turno +1 lo escribe el usuario simulado siguiendo con el tema, sin ver el pegote
(`user_visible_history`). Una cadena vacía se colaría como un mensaje de usuario
en blanco y el brazo pasaría a medir «qué hace el modelo ante un mensaje vacío»,
que no es la pregunta.

**Por qué (d) existe.** «Ignóralo» y «Sí, hablemos de eso» son instrucciones
OPUESTAS sobre el mismo texto. Un modelo que lea la intención tiene que
responder distinto. Si no distingue, la conclusión no es que la reparación no
funcione: es que el modelo no está procesando lo que el usuario le pide.
"""

from __future__ import annotations

from .topics import Topic

# Los cuatro que cuelgan de la misma base y se comparan pareados.
ARMS: tuple[str, ...] = ("a", "b", "c", "d")
PAIRED_ARMS: tuple[str, ...] = ARMS

# El quinto no cuelga de ninguna base —una conversación sin pegote no comparte
# nada con una que lo tiene—, así que corre aparte y se compara sin parear.
CONTROL_ARM = "0"

ARM_LABEL: dict[str, str] = {
    "a": "nada",
    "b": "escueta",
    "c": "explicada",
    "d": "pivote",
    CONTROL_ARM: "sin pegote",
}

# De qué habla cada tema, en una frase corta para el hueco de (c). Se escribe
# aquí y no en el fichero del tema porque es material del turno de reparación,
# no del tema: el fichero describe una conversación, no una frase de reparación.
ASUNTO: dict[str, str] = {
    "carrera-10k": "la carrera de 10k",
    "elegir-camara": "la cámara",
    "elegir-colegio": "el colegio",
    "factura-luz": "la factura de la luz",
    "hacer-pan": "el pan",
    "huerto-balcon": "el huerto del balcón",
    "mudanza": "la mudanza",
    "viaje-japon": "el viaje a Japón",
}


def repair_text(arm: str, topic: Topic) -> str | None:
    """El mensaje de usuario del turno +1, o None si el brazo no repara."""
    if arm == "a":
        return None
    if arm == "b":
        return "Ignóralo."
    if arm == "c":
        asunto = ASUNTO.get(topic.id)
        if not asunto:
            raise ValueError(
                f"el tema {topic.id!r} no tiene asunto declarado y la variante "
                "(c) lo necesita: sin él (c) sería (b) con más letras"
            )
        return f"Ignóralo, era para otro chat. Seguimos con lo {asunto}."
    if arm == "d":
        return "Sí, hablemos de eso."
    raise ValueError(f"brazo desconocido: {arm!r}; los válidos son {ARMS}")
```

Nota sobre la concordancia de (c): `ASUNTO` incluye el artículo, y la plantilla
dice «Seguimos con lo {asunto}», que suena mal con «la factura». Corregir la
plantilla a `f"Ignóralo, era para otro chat. Seguimos con {asunto}."` y ajustar
el test en consecuencia; la cadena exacta es la que fija el test.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_repair.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/wrongpaste/repair.py tests/test_repair.py
git commit -m "Los cinco brazos de la Fase 2 y sus textos literales"
```

---

### Task 4: El turno de reparación y el de tarea

**Files:**
- Modify: `src/wrongpaste/conversation.py`
- Test: `tests/test_continue_with_repair.py`

**Interfaces:**
- Consumes: `repair.repair_text`, `tasks.check_task`, `conversation.user_visible_history`, `conversation.next_user_turn`, `clients.chat`.
- Produces: `continue_with_repair(model_id, transcript, topic, arm, request_params_out=None, max_tokens=MAX_TOKENS, user_max_tokens=USER_MAX_TOKENS, user_replies_out=None) -> RepairOutcome`, con
  `RepairOutcome(indices: list[int], usages: list[dict], replies: list[Reply], task_answer: str, task_result: TaskResult)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_continue_with_repair.py
"""Los tres turnos posteriores de la Fase 2.

Lo que se prueba es la FORMA de la conversación, que es lo que hace comparables
los brazos: tres respuestas del modelo evaluado en todos ellos, y la tarea
siempre en la misma posición.
"""
import pytest

import wrongpaste.conversation as conv
from wrongpaste.clients import Reply
from wrongpaste.topics import load_topics


@pytest.fixture
def tema():
    return {t.id: t for t in load_topics()}["factura-luz"]


@pytest.fixture
def base():
    """Una conversación que ya ha recibido el pegote y ha reaccionado."""
    return [
        {"role": "user", "content": "Me ha llegado la factura al doble.", "tag": "user_sim"},
        {"role": "assistant", "content": "Vamos a mirarla.", "tag": "assistant"},
        {"role": "user", "content": "Marta, te paso la receta", "tag": "paste"},
        {"role": "assistant", "content": "No tengo constancia de eso.", "tag": "assistant"},
    ]


def _respuestas(monkeypatch, textos, user_texto="¿Y los tramos horarios?"):
    """Encadena respuestas fijas al modelo evaluado y al usuario simulado."""
    restantes = list(textos)

    def fake_chat(model_id, messages, **kw):
        return Reply(text=restantes.pop(0), usage={}, raw={}, stop_reason="stop")

    monkeypatch.setattr(conv, "chat", fake_chat)
    monkeypatch.setattr(conv, "next_user_turn",
                        lambda *a, **k: (user_texto, Reply(text=user_texto, usage={},
                                                           raw={}, stop_reason="stop")))


def test_los_brazos_con_reparacion_meten_el_texto_literal(monkeypatch, base, tema):
    _respuestas(monkeypatch, ["vale", "Suman 40,44 EUR", "sigo"])
    conv.continue_with_repair("m", base, tema, "b")
    reparacion = [m for m in base if m.get("tag") == "repair"]
    assert [m["content"] for m in reparacion] == ["Ignóralo."]


def test_el_brazo_a_no_mete_ningun_turno_de_reparacion(monkeypatch, base, tema):
    """Si (a) tuviera un mensaje `repair`, mediría lo mismo que (b)."""
    _respuestas(monkeypatch, ["sigo", "Suman 40,44 EUR", "sigo"])
    conv.continue_with_repair("m", base, tema, "a")
    assert not [m for m in base if m.get("tag") == "repair"]


def test_los_cuatro_brazos_dejan_tres_respuestas_del_evaluado(monkeypatch, tema):
    """La forma tiene que ser la misma o las posiciones no son comparables."""
    for arm in ("a", "b", "c", "d"):
        t = [{"role": "user", "content": "hola", "tag": "user_sim"},
             {"role": "assistant", "content": "hola", "tag": "assistant"},
             {"role": "user", "content": "pegote", "tag": "paste"},
             {"role": "assistant", "content": "reacción", "tag": "assistant"}]
        _respuestas(monkeypatch, ["uno", "Suman 40,44 EUR", "tres"])
        out = conv.continue_with_repair("m", t, tema, arm)
        nuevas = [t[i] for i in out.indices if t[i]["role"] == "assistant"]
        assert len(nuevas) == 3, f"brazo {arm}"


def test_la_tarea_va_siempre_en_el_segundo_turno(monkeypatch, base, tema):
    """La fuga decae con los turnos: comparar el acierto de un brazo en +2 con
    el de otro en +3 mediría la distancia al pegote, no la reparación."""
    _respuestas(monkeypatch, ["vale", "Suman 40,44 EUR", "sigo"])
    out = conv.continue_with_repair("m", base, tema, "c")
    tareas = [i for i in out.indices if base[i].get("tag") == "task"]
    assert len(tareas) == 1
    usuarios = [i for i in out.indices if base[i]["role"] == "user"]
    assert usuarios.index(tareas[0]) == 1, "la tarea no es el segundo turno de usuario"


def test_la_tarea_se_verifica_contra_el_esperado_del_tema(monkeypatch, base, tema):
    _respuestas(monkeypatch, ["vale", "Suman 40,44 EUR", "sigo"])
    out = conv.continue_with_repair("m", base, tema, "b")
    assert out.task_result.ok is True
    assert out.task_answer == "Suman 40,44 EUR"


def test_una_tarea_fallada_se_registra_con_los_numeros_que_dijo(monkeypatch, base, tema):
    """`found` es lo que permite releer a mano por qué una fila falló."""
    _respuestas(monkeypatch, ["vale", "Serán unos 40 euros", "sigo"])
    out = conv.continue_with_repair("m", base, tema, "b")
    assert out.task_result.ok is False
    assert out.task_result.found == [40]


def test_el_usuario_simulado_no_ve_ni_el_pegote_ni_la_reparacion(monkeypatch, base, tema):
    """Si los viera, podría comentarlos y el turno +3 se convertiría en otra
    reparación, distinta en cada celda."""
    visto = {}

    def fake_next(model_id, topic, history, **kw):
        visto["tags"] = [m.get("tag") for m in history]
        return "sigo", Reply(text="sigo", usage={}, raw={}, stop_reason="stop")

    monkeypatch.setattr(conv, "next_user_turn", fake_next)
    restantes = ["vale", "Suman 40,44 EUR", "sigo"]
    monkeypatch.setattr(conv, "chat", lambda *a, **k: Reply(
        text=restantes.pop(0), usage={}, raw={}, stop_reason="stop"))

    conv.continue_with_repair("m", base, tema, "b")
    assert "paste" not in visto["tags"]
    assert "repair" not in visto["tags"]


def test_el_modelo_evaluado_si_recibe_el_transcript_completo(monkeypatch, base, tema):
    """La contaminación que se mide es la suya: ocultarle el pegote sería medir
    otra cosa."""
    vistos = []
    restantes = ["vale", "Suman 40,44 EUR", "sigo"]

    def fake_chat(model_id, messages, **kw):
        vistos.append([m.get("tag") for m in messages])
        return Reply(text=restantes.pop(0), usage={}, raw={}, stop_reason="stop")

    monkeypatch.setattr(conv, "chat", fake_chat)
    monkeypatch.setattr(conv, "next_user_turn",
                        lambda *a, **k: ("sigo", Reply(text="sigo", usage={},
                                                       raw={}, stop_reason="stop")))
    conv.continue_with_repair("m", base, tema, "b")
    assert all("paste" in tags for tags in vistos)


def test_un_brazo_invalido_revienta_antes_de_llamar_a_nadie(base, tema):
    with pytest.raises(ValueError, match="brazo"):
        conv.continue_with_repair("m", base, tema, "z")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_continue_with_repair.py -q`
Expected: FAIL con `AttributeError: module 'wrongpaste.conversation' has no attribute 'continue_with_repair'`

- [ ] **Step 3: Write the implementation**

Añadir a `src/wrongpaste/conversation.py`, junto a `continue_after_paste`:

```python
@dataclass(frozen=True)
class RepairOutcome:
    """Lo que dejan los tres turnos posteriores de la Fase 2.

    `indices` son los de **todos** los mensajes añadidos, usuario y asistente,
    en orden, por el mismo motivo que en `continue_after_paste`: el recuento de
    fuga se hace por turno, y dejar fuera los de usuario obligaría al análisis a
    recalcular posiciones.
    """

    indices: list[int]
    usages: list[dict]
    replies: list[Reply]
    task_answer: str
    task_result: TaskResult


def continue_with_repair(
    model_id: str,
    transcript: list[dict],
    topic: Topic,
    arm: str,
    request_params_out: dict | None = None,
    max_tokens: int = MAX_TOKENS,
    user_max_tokens: int = USER_MAX_TOKENS,
    user_replies_out: list[Reply] | None = None,
) -> RepairOutcome:
    """Los tres turnos posteriores de la Fase 2, con el brazo `arm`.

    **La forma es la misma en los cuatro brazos y eso es el diseño**: turno de
    reparación (o de usuario simulado en el brazo (a)), turno de tarea, turno de
    usuario simulado. Tres respuestas del modelo evaluado en todos ellos, y la
    tarea siempre en la misma posición, porque la fuga decae con los turnos y
    comparar el acierto de un brazo en +2 con el de otro en +3 mediría la
    distancia al pegote en vez de la reparación.

    Muta `transcript` in place.
    """
    if arm not in ARMS:
        raise ValueError(f"brazo desconocido: {arm!r}; los válidos son {ARMS}")
    if not topic.task or not topic.expected:
        raise ValueError(
            f"el tema {topic.id!r} no tiene tarea verificable: la Fase 2 no "
            "puede correr sobre un tema con el hueco D13 vacío"
        )

    indices: list[int] = []
    usages: list[dict] = []
    replies: list[Reply] = []

    def _turno(contenido: str, tag: str) -> Reply:
        indices.append(len(transcript))
        transcript.append({"role": "user", "content": contenido, "tag": tag})
        reply = chat(model_id, list(transcript), max_tokens=max_tokens,
                     request_params_out=request_params_out)
        indices.append(len(transcript))
        transcript.append({"role": "assistant", "content": reply.text,
                           "tag": "assistant"})
        usages.append(reply.usage)
        replies.append(reply)
        return reply

    def _turno_de_usuario_simulado(tag: str) -> Reply:
        texto, user_reply = next_user_turn(
            USER_MODEL, topic, user_visible_history(transcript),
            max_tokens=user_max_tokens,
        )
        if user_replies_out is not None:
            user_replies_out.append(user_reply)
        return _turno(texto, tag)

    # +1: la reparación, o el usuario siguiendo a lo suyo en el brazo (a).
    texto_reparacion = repair_text(arm, topic)
    if texto_reparacion is None:
        _turno_de_usuario_simulado("post")
    else:
        _turno(texto_reparacion, "repair")

    # +2: la tarea, literal e idéntica en los cinco brazos.
    reply_tarea = _turno(topic.task, "task")

    # +3: el usuario sigue. Aquí se ve si la fuga persiste más allá del turno
    # que la reparación toca directamente.
    _turno_de_usuario_simulado("post")

    return RepairOutcome(
        indices=indices,
        usages=usages,
        replies=replies,
        task_answer=reply_tarea.text,
        task_result=check_task(reply_tarea.text, parse_expected(topic.expected)),
    )
```

Imports nuevos al principio del módulo: `from .repair import ARMS, repair_text`
y `from .tasks import TaskResult, check_task, parse_expected`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_continue_with_repair.py -q`
Expected: PASS (9 tests)

- [ ] **Step 5: Run the whole suite, to catch what this broke**

Run: `.venv/bin/python -m pytest -q --ignore=tests/test_smoke_live.py`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/wrongpaste/conversation.py tests/test_continue_with_repair.py
git commit -m "Los tres turnos posteriores de la Fase 2, con la tarea en posición fija"
```

---

### Task 5: La fuga de entidades

**Files:**
- Create: `src/wrongpaste/leak.py`
- Test: `tests/test_leak.py`

**Interfaces:**
- Consumes: `artifacts.entity_hits`.
- Produces: `leak_by_turn(transcript, indices, entities) -> list[dict]`,
  `leaked(turns) -> bool`, `leak_report(rows) -> dict`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_leak.py
"""El recuento de fuga, que es la variable primaria de la Fase 2."""
import pytest

from wrongpaste.leak import leak_by_turn, leaked, leak_report


@pytest.fixture
def transcript():
    return [
        {"role": "user", "content": "Ignóralo.", "tag": "repair"},
        {"role": "assistant", "content": "Claro, olvido lo de Marta.", "tag": "assistant"},
        {"role": "user", "content": "¿Cuánto suma?", "tag": "task"},
        {"role": "assistant", "content": "Suman 40,44 EUR.", "tag": "assistant"},
        {"role": "user", "content": "¿Y los tramos?", "tag": "post"},
        {"role": "assistant", "content": "Los tramos son tres.", "tag": "assistant"},
    ]


def test_solo_cuentan_las_respuestas_del_modelo(transcript):
    """El turno de reparación del USUARIO no puede contar como fuga: lo escribe
    el arnés, no el modelo. Contarlo haría que (c) —que nombra el tema— fugara
    por construcción."""
    turnos = leak_by_turn(transcript, list(range(6)), ["Marta", "receta"])
    assert len(turnos) == 3
    assert [t["turn"] for t in turnos] == [1, 2, 3]


def test_la_fuga_se_localiza_en_el_turno(transcript):
    turnos = leak_by_turn(transcript, list(range(6)), ["Marta", "receta"])
    assert turnos[0]["hits"] == ["Marta"]
    assert turnos[1]["hits"] == []
    assert turnos[2]["hits"] == []


def test_la_binaria_es_alguna_entidad_en_algun_turno(transcript):
    turnos = leak_by_turn(transcript, list(range(6)), ["Marta"])
    assert leaked(turnos) is True
    assert leaked(leak_by_turn(transcript, list(range(6)), ["Iberdrola"])) is False


def test_prometer_olvidar_nombrando_cuenta_como_fuga(transcript):
    """El oso blanco tiene que poder verse: «olvido lo de Marta» repite la
    entidad mientras promete olvidarla, y eso ES la fuga que se persigue."""
    assert leaked(leak_by_turn(transcript, list(range(6)), ["Marta"])) is True


def test_una_fila_sin_entidades_no_entra_en_el_denominador():
    """Un artefacto sin entidades no puede fugar: contarlo como «no fugó» es
    meter una propiedad del banco en el numerador."""
    filas = [
        {"arm": "b", "entities": ["Marta"], "leaked": True},
        {"arm": "b", "entities": [], "leaked": False},
    ]
    r = leak_report(filas)
    assert r["por_brazo"]["b"] == {"n": 1, "fugan": 1, "tasa": 1.0}


def test_el_informe_reparte_por_brazo():
    filas = [
        {"arm": "a", "entities": ["x"], "leaked": False},
        {"arm": "a", "entities": ["x"], "leaked": True},
        {"arm": "b", "entities": ["x"], "leaked": True},
    ]
    r = leak_report(filas)
    assert r["por_brazo"]["a"]["tasa"] == 0.5
    assert r["por_brazo"]["b"]["tasa"] == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_leak.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'wrongpaste.leak'`

- [ ] **Step 3: Write the implementation**

`leak_by_turn` recorre los `indices` en orden, se queda con los mensajes cuyo
`role` es `assistant`, los numera desde 1 y llama a `entity_hits` sobre cada uno.
`leaked` es `any(t["hits"] for t in turns)`. `leak_report` agrupa por `arm`
descartando las filas con `entities` vacío, y devuelve `{"por_brazo": {arm:
{"n","fugan","tasa"}}, "por_turno": {...}}`. Docstrings con el porqué de cada
decisión, en particular los dos que los tests fijan: que el turno de usuario no
cuenta, y que una fila sin entidades sale del denominador.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_leak.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/wrongpaste/leak.py tests/test_leak.py
git commit -m "Recuento de fuga de entidades por turno y por conversación"
```

---

### Task 6: La prueba pareada y su potencia

**Files:**
- Modify: `src/wrongpaste/curve.py`
- Test: `tests/test_curve.py` (añadir casos)

**Interfaces:**
- Consumes: `math.erfc` (ya usado por `cochran_armitage`).
- Produces: `mcnemar(b: int, c: int) -> dict` con `{"b","c","z","p","diff","ci"}`,
  `paired_power(n, p_base, delta, rho) -> float`,
  `paired_n_for_power(p_base, delta, rho, power=MIN_POWER) -> int`,
  `HYPOTHESIS_FAMILIES_F2: dict[str, tuple[str, ...]]`.

- [ ] **Step 1: Write the failing test**

```python
# añadir a tests/test_curve.py
"""La prueba pareada de la Fase 2.

Pareada porque los cuatro brazos cuelgan de la misma conversación: el prefijo,
el artefacto y la reacción al pegote son los mismos, y lo único que cambia es el
texto de reparación. Una prueba sin parear tiraría esa información y pediría una
tanda mucho más cara para la misma potencia.
"""

def test_mcnemar_solo_mira_los_pares_discordantes():
    """Los pares que coinciden no aportan información sobre la diferencia: si
    entraran, dos brazos idénticos con n enorme darían p pequeño."""
    assert curve.mcnemar(b=10, c=10)["p"] == pytest.approx(1.0, abs=1e-6)
    a = curve.mcnemar(b=30, c=10)
    assert a["p"] < 0.01


def test_la_direccion_del_efecto_va_en_el_signo():
    """`diff` positivo = el segundo brazo fuga más que el primero. Sin signo,
    «ignóralo contamina más» y «contamina menos» darían el mismo número."""
    assert curve.mcnemar(b=30, c=10)["diff"] > 0
    assert curve.mcnemar(b=10, c=30)["diff"] < 0


def test_sin_discordancias_no_hay_prueba():
    """b = c = 0 es «los dos brazos hicieron exactamente lo mismo en todos los
    pares». Devolver p = 1 es correcto; dividir por cero no."""
    r = curve.mcnemar(b=0, c=0)
    assert r["p"] == 1.0 and r["z"] == 0.0


def test_la_potencia_pareada_sube_con_la_correlacion():
    """Es el motivo de todo el diseño: si parear no subiera la potencia, colgar
    los brazos de la misma base sería solo una forma de ahorrar el turno del
    pegote."""
    floja = curve.paired_power(n=300, p_base=0.30, delta=0.09, rho=0.0)
    fuerte = curve.paired_power(n=300, p_base=0.30, delta=0.09, rho=0.6)
    assert fuerte > floja


def test_el_tamano_necesario_baja_con_la_correlacion():
    assert (curve.paired_n_for_power(0.30, 0.09, rho=0.6)
            < curve.paired_n_for_power(0.30, 0.09, rho=0.0))


def test_la_potencia_de_la_fase_2_se_calcula_sobre_la_caida_declarada():
    """`DECLARED_DROP` es del proyecto, no de la fase: escribir 0,09 a mano aquí
    lo desincronizaría en silencio el día que cambie."""
    assert curve.paired_power(n=400, p_base=0.30,
                              delta=curve.DECLARED_DROP, rho=0.5) > 0


def test_las_familias_de_holm_de_la_fase_2_son_las_del_spec():
    """Si una hipótesis se cayera de su familia, su p dejaría de corregirse y
    el umbral de significación se relajaría sin que nadie lo decidiera."""
    f = curve.HYPOTHESIS_FAMILIES_F2
    assert f["fuga"] == ("H6", "H7", "H8")
    assert f["acierto"] == ("H9", "H10", "H11", "H12")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_curve.py -q -k "mcnemar or pareada or paired or holm_de_la_fase_2"`
Expected: FAIL con `AttributeError: module 'wrongpaste.curve' has no attribute 'mcnemar'`

- [ ] **Step 3: Write the implementation**

McNemar en forma cerrada con corrección de continuidad:
`z = (|b - c| - 1) / sqrt(b + c)`, signo de `b - c`, `p = erfc(|z| / sqrt(2))`.
Con `b + c == 0`, devolver `z = 0.0, p = 1.0` sin dividir.
`diff = (b - c) / n_pares` y su IC 95 % por el método de Wald sobre la
diferencia de proporciones pareadas.

`paired_power(n, p_base, delta, rho)`: la varianza de la diferencia pareada es
`p1(1-p1) + p2(1-p2) - 2*rho*sqrt(p1(1-p1)*p2(1-p2))` con `p2 = p_base + delta`;
de ahí `z_beta = delta*sqrt(n)/sqrt(var) - 1.96` y la potencia por la normal
acumulada (que ya existe en el módulo para `trend_power`; reutilizarla, no
reescribirla).

`paired_n_for_power`: el menor `n` entero con `paired_power(n, ...) >= power`,
por búsqueda al alza desde 10 con tope de 100.000 y error si no converge.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_curve.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/wrongpaste/curve.py tests/test_curve.py
git commit -m "McNemar y potencia pareada, con las familias de Holm de la Fase 2"
```

---

### Task 7: El muestreo de bases y el plan

**Files:**
- Create: `src/wrongpaste/run_phase2.py`
- Test: `tests/test_run_phase2.py`

**Interfaces:**
- Consumes: `run_phase1d.read_run_header`, `run_judging.load_rows`, `curve.paired_n_for_power`, `repair.ARMS`.
- Produces: `MASTER_SEED_F2 = 20260917`, `MIN_POWER` (reexportado de `curve`,
  para que el runner y la puerta no tengan dos umbrales), `sample_bases(rows, n_bases, seed) -> list[dict]`,
  `plan_phase2(bases) -> list[dict]`, `call_budget_f2(plan) -> dict`,
  `check_design_power_f2(plan, p_base, rho) -> dict`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_run_phase2.py
"""El muestreo de bases y el plan de la Fase 2."""
import pytest

from wrongpaste import run_phase2 as r2
from wrongpaste.repair import ARMS


def _fila(cid, banda, g, tema="factura-luz", status="ok"):
    return {"conversation_id": cid, "stratum": banda, "topic_id": tema,
            "status": status, "judge_duda": g}


@pytest.fixture
def filas():
    out = []
    for banda in range(4):
        for i in range(20):
            out.append(_fila(f"c{banda}-{i}", banda, i % 2 == 0))
    return out


def test_el_muestreo_reparte_las_bases_entre_las_cuatro_bandas(filas):
    """Si las bandas quedaran desiguales, la estratificación exploratoria por
    similaridad nacería sesgada y no habría forma de arreglarla después."""
    bases = r2.sample_bases(filas, n_bases=20, seed=r2.MASTER_SEED_F2)
    por_banda = {}
    for b in bases:
        por_banda[b["stratum"]] = por_banda.get(b["stratum"], 0) + 1
    assert set(por_banda) == {0, 1, 2, 3}
    assert set(por_banda.values()) == {5}


def test_el_muestreo_equilibra_dudo_y_no_dudo(filas):
    """La otra covariable de la base. Sin equilibrarla, «¿repara mejor el que ya
    lo había notado?» dependería del azar del muestreo."""
    bases = r2.sample_bases(filas, n_bases=20, seed=r2.MASTER_SEED_F2)
    dudaron = sum(1 for b in bases if b["judge_duda"])
    assert dudaron == 10


def test_el_muestreo_es_reproducible(filas):
    a = r2.sample_bases(filas, n_bases=20, seed=r2.MASTER_SEED_F2)
    b = r2.sample_bases(filas, n_bases=20, seed=r2.MASTER_SEED_F2)
    assert [x["conversation_id"] for x in a] == [x["conversation_id"] for x in b]


def test_solo_se_muestrean_filas_ok(filas):
    """Una fila que falló en la parte 1 no tiene una reacción completa de la que
    colgar: continuarla produciría turnos colgando de un agujero."""
    filas.append(_fila("roto", 0, True, status="timeout"))
    bases = r2.sample_bases(filas, n_bases=20, seed=r2.MASTER_SEED_F2)
    assert "roto" not in {b["conversation_id"] for b in bases}


def test_cada_base_genera_los_cuatro_brazos(filas):
    bases = r2.sample_bases(filas, n_bases=20, seed=r2.MASTER_SEED_F2)
    plan = r2.plan_phase2(bases)
    assert len(plan) == len(bases) * len(ARMS)
    for base in bases:
        brazos = {c["arm"] for c in plan
                  if c["base_id"] == base["conversation_id"]}
        assert brazos == set(ARMS)


def test_el_identificador_de_celda_lleva_base_y_brazo(filas):
    """Sin eso, la reanudación no puede saltar una celda hecha sin releer todo."""
    plan = r2.plan_phase2(r2.sample_bases(filas, 20, r2.MASTER_SEED_F2))
    ids = {c["conversation_id"] for c in plan}
    assert len(ids) == len(plan)
    c = plan[0]
    assert c["base_id"] in c["conversation_id"] and c["arm"] in c["conversation_id"]


def test_el_presupuesto_se_deriva_del_plan_y_no_se_escribe_a_mano(filas):
    """El repo ya se quemó con un recuento a mano que se quedó rancio a la vez
    que el plan y pasaba en vacío."""
    plan = r2.plan_phase2(r2.sample_bases(filas, 20, r2.MASTER_SEED_F2))
    b = call_budget = r2.call_budget_f2(plan)
    assert b["evaluated_model_calls"] == len(plan) * 3
    # (a) gasta dos turnos de usuario simulado; (b)(c)(d) solo uno.
    brazos_a = sum(1 for c in plan if c["arm"] == "a")
    assert b["simulated_user_calls"] == brazos_a * 2 + (len(plan) - brazos_a)


def test_la_puerta_de_potencia_se_calcula_sobre_las_bases_y_no_sobre_las_celdas(filas):
    """En un diseño pareado la unidad es la BASE. Contar celdas cuadruplicaría
    la n y declararía una potencia que no existe."""
    plan = r2.plan_phase2(r2.sample_bases(filas, 20, r2.MASTER_SEED_F2))
    r = r2.check_design_power_f2(plan, p_base=0.30, rho=0.5)
    assert r["n_bases"] == 20
    assert r["n_bases"] != len(plan)


def test_una_potencia_por_debajo_del_minimo_se_declara_y_no_se_esconde(filas):
    plan = r2.plan_phase2(r2.sample_bases(filas, 20, r2.MASTER_SEED_F2))
    r = r2.check_design_power_f2(plan, p_base=0.30, rho=0.0)
    assert r["power"] < r2.MIN_POWER
    assert r["ok"] is False
    assert "bases" in r["message"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_run_phase2.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'wrongpaste.run_phase2'`

- [ ] **Step 3: Write the implementation**

`sample_bases` filtra `status == "ok"`, agrupa por `(stratum, judge_duda)` y
toma `n_bases // 8` de cada uno de los ocho estratos, ordenando cada estrato por
`blake2b(conversation_id + seed)` como hace `band_order` en `run_phase1d` —el
mismo mecanismo, para que el muestreo sea reproducible sin `random`—. Si
`n_bases` no es múltiplo de 8, error: un muestreo desequilibrado es peor que uno
que no corre.

`plan_phase2` produce una celda por `(base, arm)` con
`conversation_id = f"{base_id}--{arm}"`, y copia de la base `stratum`,
`topic_id`, `artifact_id`, `artifact_entities` y `judge_duda`.

`call_budget_f2` cuenta 3 llamadas al evaluado por celda, 2 al usuario simulado
en el brazo (a) y 1 en los demás, **todo derivado del plan**.

`check_design_power_f2` calcula `n_bases` como el número de `base_id` distintos
—no el de celdas— y llama a `curve.paired_power`; devuelve `ok`, `power`,
`n_bases`, `min_detectable` y un `message` que, cuando no llega, dice cuántas
bases harían falta según `paired_n_for_power`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_run_phase2.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/wrongpaste/run_phase2.py tests/test_run_phase2.py
git commit -m "Muestreo de bases, plan y puerta de potencia de la Fase 2"
```

---

### Task 8: La tirada

**Files:**
- Modify: `src/wrongpaste/run_phase2.py`
- Test: `tests/test_run_phase2_main.py`

**Interfaces:**
- Consumes: `run_phase1d._record_from_row`, `run_phase1d.check_failure_streak`, `run_phase1d.failure_streak_after`, `run_phase1d.credential_notice`, `run_phase1d.gcloud_token_expiry`, `conversation.continue_with_repair`, `leak.leak_by_turn`.
- Produces: `main(run_path, out, n_bases, seed, p_base, rho) -> dict`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_run_phase2_main.py
"""La tirada de la Fase 2: cabecera, reanudación, guardas y fila.

El `harness` es el mismo patrón de `tests/test_run_phase1d.py:547`: se doblan
las puertas de red y se apunta `chat` / `embed` a una función que revienta, para
que una llamada real por un camino sin doblar salga como fallo del test y no
como una factura.
"""
import json

import pytest

from wrongpaste import conversation as conv
from wrongpaste import run_phase2 as r2
from wrongpaste.clients import Reply
from wrongpaste.repair import ARMS

BASE_RUN_ID = "20260916T163736"


def _base_jsonl(path, n_bases=8):
    """Un fichero de parte 1 falso, con cabecera y n_bases filas `ok`."""
    cabecera = {"run_id": BASE_RUN_ID, "post_turns": 0, "models": ["m"],
                "schema_version": 1}
    lineas = [json.dumps(cabecera, ensure_ascii=False)]
    for i in range(n_bases):
        lineas.append(json.dumps({
            "conversation_id": f"c{i}", "stratum": i % 4, "status": "ok",
            "topic_id": "factura-luz", "model_id": "m",
            "artifact_id": f"a{i}", "artifact_entities": ["Marta"],
            "judge_duda": i % 2 == 0, "request_params": {},
            "transcript": [
                {"role": "user", "content": "hola", "tag": "user_sim"},
                {"role": "assistant", "content": "hola", "tag": "assistant"},
                {"role": "user", "content": "Marta, te paso esto", "tag": "paste"},
                {"role": "assistant", "content": "no me consta", "tag": "assistant"},
            ],
        }, ensure_ascii=False))
    path.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return path


@pytest.fixture
def harness(tmp_path, monkeypatch):
    """Respuestas fijas para el evaluado y el usuario simulado."""
    monkeypatch.setattr(conv, "chat", lambda model_id, messages, **kw: Reply(
        text="Suman 40,44 EUR y lo de Marta lo dejo.", usage={}, raw={},
        stop_reason="stop"))
    monkeypatch.setattr(conv, "next_user_turn", lambda *a, **k: (
        "sigo con la factura", Reply(text="sigo con la factura", usage={},
                                     raw={}, stop_reason="stop")))
    return tmp_path


def _leer(path):
    lineas = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()
              if l.strip()]
    return lineas[0], lineas[1:]


def test_la_cabecera_declara_de_que_tanda_cuelga(harness):
    """Sin eso, las filas no dicen de qué reacciones salieron y la procedencia
    se pierde (D5). El `code_sha` de la base es el del código que compró la
    reacción; estos turnos los genera otro commit."""
    base = _base_jsonl(harness / "base.jsonl")
    out = harness / "f2.jsonl"
    r2.main(base, out, n_bases=8, p_base=0.30, rho=0.5)
    cabecera, _ = _leer(out)
    assert cabecera["base_run"]["source_run_id"] == BASE_RUN_ID
    assert cabecera["base_run"]["code_sha"]
    assert cabecera["arms"] == list(ARMS)


def test_la_fila_lleva_el_brazo_la_fuga_y_el_acierto(harness):
    base = _base_jsonl(harness / "base.jsonl")
    out = harness / "f2.jsonl"
    r2.main(base, out, n_bases=8, p_base=0.30, rho=0.5)
    _, filas = _leer(out)
    assert set(filas[0]) >= {"arm", "base_id", "leaked", "leak_by_turn",
                             "task_ok", "task_found", "part1_status"}
    assert filas[0]["part1_status"] == "ok"
    # La respuesta falsa dice «lo de Marta», que es la entidad del artefacto.
    assert filas[0]["leaked"] is True
    assert filas[0]["task_ok"] is True


def test_cada_base_produce_sus_cuatro_brazos(harness):
    base = _base_jsonl(harness / "base.jsonl")
    out = harness / "f2.jsonl"
    r2.main(base, out, n_bases=8, p_base=0.30, rho=0.5)
    _, filas = _leer(out)
    assert len(filas) == 8 * len(ARMS)
    por_base = {}
    for f in filas:
        por_base.setdefault(f["base_id"], set()).add(f["arm"])
    assert all(b == set(ARMS) for b in por_base.values())


def test_reanudar_salta_las_celdas_hechas_y_no_las_bases(harness, monkeypatch):
    """La unidad de la reanudación es la CELDA. Si saltara bases enteras, una
    caída a mitad de los cuatro brazos dejaría la base incompleta para siempre
    y el análisis pareado la tiraría."""
    base = _base_jsonl(harness / "base.jsonl")
    out = harness / "f2.jsonl"
    r2.main(base, out, n_bases=8, p_base=0.30, rho=0.5)
    _, primeras = _leer(out)

    # Se borra un brazo de una base y se reanuda: tiene que rehacerse solo ese.
    quitado = primeras[2]
    quedan = [f for f in primeras if f["conversation_id"] != quitado["conversation_id"]]
    cabecera, _ = _leer(out)
    out.write_text("\n".join([json.dumps(cabecera, ensure_ascii=False)]
                             + [json.dumps(f, ensure_ascii=False) for f in quedan])
                   + "\n", encoding="utf-8")

    hechas = []
    original = r2.continue_with_repair
    monkeypatch.setattr(r2, "continue_with_repair",
                        lambda *a, **k: (hechas.append(a[3]), original(*a, **k))[1])
    resumen = r2.main(base, out, n_bases=8, p_base=0.30, rho=0.5)
    assert resumen["skipped"] == len(quedan)
    assert len(hechas) == 1


def test_la_guarda_de_racha_tambien_para_esta_tirada(harness, monkeypatch):
    """La misma que la 1d y por el mismo incidente: doce celdas seguidas
    fallando no son un bache, son una avería."""
    from wrongpaste.run_phase1d import ConsecutiveFailuresError

    monkeypatch.setattr(conv, "chat", lambda *a, **k: (_ for _ in ()).throw(
        RuntimeError("gateway caído")))
    base = _base_jsonl(harness / "base.jsonl", n_bases=8)
    out = harness / "f2.jsonl"
    with pytest.raises(ConsecutiveFailuresError, match="12 celdas seguidas"):
        r2.main(base, out, n_bases=8, p_base=0.30, rho=0.5)
    # Y las filas que fallaron están escritas: reanudar las reintenta.
    _, filas = _leer(out)
    assert len(filas) == 12
    assert all(f["status"] != "ok" for f in filas)


def test_el_aviso_de_credencial_se_imprime_antes_de_la_primera_celda(harness, capsys):
    base = _base_jsonl(harness / "base.jsonl")
    out = harness / "f2.jsonl"
    r2.main(base, out, n_bases=8, p_base=0.30, rho=0.5)
    salida = capsys.readouterr().out
    assert "--- credencial:" in salida
    assert salida.index("--- credencial:") < salida.index("c0--a")


def test_la_puerta_de_potencia_salta_antes_de_gastar(harness, monkeypatch):
    """Es el error que costó la Fase 1b: correr y descubrir después que la
    potencia era del 11 %."""
    llamado = []
    monkeypatch.setattr(r2, "continue_with_repair",
                        lambda *a, **k: llamado.append(1))
    base = _base_jsonl(harness / "base.jsonl")
    out = harness / "f2.jsonl"
    with pytest.raises(ValueError, match="potencia"):
        r2.main(base, out, n_bases=8, p_base=0.30, rho=0.0)
    assert not llamado, "se gastó una llamada antes de comprobar la potencia"
    assert not out.exists(), "la puerta dejó un fichero a medias"


def test_una_tanda_base_que_no_es_de_parte_1_se_rechaza(harness):
    """Una cabecera con post_turns distinto de 0 significa que esas filas ya
    llevan turnos posteriores: colgarles tres más daría filas con el doble de
    texto que otras y el recuento de fuga saldría sobre bases distintas."""
    base = harness / "base.jsonl"
    _base_jsonl(base)
    lineas = base.read_text(encoding="utf-8").splitlines()
    cab = json.loads(lineas[0]); cab["post_turns"] = 2
    base.write_text("\n".join([json.dumps(cab)] + lineas[1:]) + "\n",
                    encoding="utf-8")
    with pytest.raises(ValueError, match="post_turns"):
        r2.main(base, harness / "f2.jsonl", n_bases=8, p_base=0.30, rho=0.5)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_run_phase2_main.py -q`
Expected: FAIL

- [ ] **Step 3: Write the implementation**

`main` sigue la estructura de `run_phase1d.main`: lee la cabecera de la tanda
base (exigiendo `post_turns == 0`), muestrea las bases, construye el plan, pasa
la puerta de potencia, imprime el aviso de credencial sobre **lo que queda**,
y recorre el plan reconstruyendo cada transcripción con `_record_from_row` y
continuándola con `continue_with_repair`. Reutiliza `failure_streak_after` /
`check_failure_streak` tal cual. La fila lleva `part1_status` por el mismo
motivo que en `resume_post_turns`: el `status` de la fila pasa a ser el de la
conversación entera, y sin `part1_status` una fila juzgable de la parte 1 saldría
del denominador por algo posterior al estímulo.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q --ignore=tests/test_smoke_live.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/wrongpaste/run_phase2.py tests/test_run_phase2_main.py
git commit -m "Tirada de la Fase 2, con las guardas de la 1d reutilizadas"
```

---

### Task 9: El brazo (0), sin pegote

**Files:**
- Create: `src/wrongpaste/run_phase2_control.py`
- Test: `tests/test_run_phase2_control.py`

**Interfaces:**
- Consumes: `prefixes` (los 16 ya en disco), `topics`, `tasks.check_task`,
  `run_phase2.MASTER_SEED_F2` (reexportado como `ctl.MASTER_SEED_F2`: dos
  semillas maestras distintas harían irreproducible la mitad de la fase).
- Produces: `main(out, n, seed) -> dict`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_run_phase2_control.py
"""El brazo (0): la conversación que nunca recibió el pegote.

Es la única línea base posible para el acierto en la tarea. Sin él sólo se podría
decir que unos brazos aciertan más que otros, que es una frase mucho más pequeña
que «el pegote degrada la tarea».
"""

import json

import pytest

from wrongpaste import run_phase2_control as ctl
from wrongpaste.repair import CONTROL_ARM


def _leer(path):
    lineas = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()
              if l.strip()]
    return lineas[0], lineas[1:]


@pytest.fixture
def salida(harness):
    """Una tirada de control de 8 conversaciones, con la red doblada."""
    out = harness / "control.jsonl"
    ctl.main(out, n=8, seed=ctl.MASTER_SEED_F2)
    return _leer(out)


def test_el_control_no_tiene_ningun_mensaje_de_pegote(salida):
    """Si lo tuviera, dejaría de ser el control."""
    _, filas = salida
    for f in filas:
        assert not [m for m in f["transcript"] if m.get("tag") == "paste"]


def test_el_control_pone_la_tarea_en_la_misma_posicion(salida):
    """La tarea va en +2 en los cinco brazos. Comparar el acierto de un brazo
    en +2 con el de otro en +3 mediría la distancia al final del prefijo."""
    _, filas = salida
    for f in filas:
        usuarios = [m for m in f["transcript"] if m["role"] == "user"]
        tarea = [i for i, m in enumerate(usuarios) if m.get("tag") == "task"]
        assert len(tarea) == 1
        assert tarea[0] == len(usuarios) - 2, "la tarea no es el penúltimo turno"


def test_el_control_usa_los_mismos_prefijos_y_temas(salida):
    """Si usara otros, la diferencia de acierto mezclaría «había pegote» con
    «era otra conversación»."""
    from wrongpaste.topics import load_topics

    _, filas = salida
    temas = {t.id for t in load_topics()}
    assert {f["topic_id"] for f in filas} <= temas
    assert all(f["prefix_id"] for f in filas)


def test_el_control_no_cuelga_de_ninguna_base(salida):
    """No es pareado y la fila no puede fingir que lo es: un `base_id` con valor
    haría que el análisis lo emparejara con algo."""
    _, filas = salida
    assert all(f.get("base_id") is None for f in filas)
    assert {f["arm"] for f in filas} == {CONTROL_ARM}


def test_el_control_verifica_la_tarea_igual_que_los_demas(salida):
    """Mismo verificador o la línea base mediría otra cosa que los brazos."""
    _, filas = salida
    assert all("task_ok" in f and "task_found" in f for f in filas)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_run_phase2_control.py -q`
Expected: FAIL

- [ ] **Step 3: Write the implementation**

Reaprovecha el generador de prefijos existente, no añade turno de pegote, mete
el turno de tarea en la misma posición relativa y escribe la fila con
`arm: "0"`, `base_id: None`, `task_ok` y `task_found`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q --ignore=tests/test_smoke_live.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/wrongpaste/run_phase2_control.py tests/test_run_phase2_control.py
git commit -m "Brazo (0): la línea base de acierto sin pegote"
```

---

### Task 10: El análisis del piloto

**Files:**
- Create: `src/wrongpaste/analysis_phase2.py`
- Test: `tests/test_analysis_phase2.py`

**Interfaces:**
- Consumes: `curve.mcnemar`, `curve.paired_n_for_power`, `curve.holm`, `leak.leak_report`.
- Produces: `pilot_report(rows_f2, rows_control) -> dict` con las cuatro cifras que decide el piloto (§7 del spec) y el tamaño recomendado para la tanda principal.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_analysis_phase2.py
"""Lo que el piloto tiene que contestar, y que decide si se compra la tanda."""
import pytest

from wrongpaste.analysis_phase2 import pilot_report


def _fila(base, arm, fuga, acierto=True):
    return {"base_id": base, "arm": arm, "status": "ok", "part1_status": "ok",
            "entities": ["Marta"], "leaked": fuga, "task_ok": acierto}


def _tanda(fugas_por_brazo, n=40):
    """n bases completas, con la tasa de fuga pedida para cada brazo."""
    filas = []
    for i in range(n):
        for arm, tasa in fugas_por_brazo.items():
            filas.append(_fila(f"b{i}", arm, i < round(tasa * n)))
    return filas


CONTROL = [{"arm": "0", "base_id": None, "status": "ok", "task_ok": i % 10 != 0}
           for i in range(40)]


def test_el_informe_da_las_cinco_cifras_del_piloto():
    """Son las del §7 del spec, y ninguna se puede omitir: el tamaño de la
    tanda principal sale de ellas."""
    r = pilot_report(_tanda({"a": .3, "b": .4, "c": .2, "d": .4}), CONTROL)
    assert set(r) >= {"tasa_fuga_a", "rho_entre_brazos", "acierto_control",
                      "fuga_trivial", "tarea_utilizable", "n_bases_recomendadas"}


def test_una_fuga_trivial_se_declara_en_vez_de_dimensionar_sobre_ella():
    """Si (a) fuga en el 2 %, no hay rango donde una reparación pueda mover
    nada, y dimensionar sobre esa tasa daría un número enorme y sin sentido."""
    r = pilot_report(_tanda({"a": .02, "b": .02, "c": .02, "d": .02}), CONTROL)
    assert r["fuga_trivial"] is True
    assert r["n_bases_recomendadas"] is None


def test_un_acierto_pegado_al_suelo_en_el_control_para_la_fase():
    """Si el brazo sin pegote ya falla la tarea, la tarea está mal escrita y el
    acierto no puede medir contaminación: el número saldría, y significaría
    «mi verificador no entiende las respuestas»."""
    suelo = [dict(f, task_ok=False) for f in CONTROL]
    r = pilot_report(_tanda({"a": .3, "b": .4, "c": .2, "d": .4}), suelo)
    assert r["tarea_utilizable"] is False


def test_la_correlacion_se_mide_entre_brazos_de_la_MISMA_base():
    """Medirla entre bases distintas daría la correlación de dos muestras
    independientes, que es cero por construcción, y tiraría todo el diseño.

    Aquí (a) y (b) fugan exactamente en las mismas bases: la correlación tiene
    que salir 1, y solo sale 1 si se emparejó por `base_id`."""
    filas = []
    for i in range(40):
        fuga = i < 12
        filas += [_fila(f"b{i}", "a", fuga), _fila(f"b{i}", "b", fuga),
                  _fila(f"b{i}", "c", fuga), _fila(f"b{i}", "d", fuga)]
    assert pilot_report(filas, CONTROL)["rho_entre_brazos"] == pytest.approx(1.0)


def test_una_base_incompleta_no_entra_y_se_cuenta_aparte():
    """Un par necesita los dos brazos. Contar una base de tres brazos como si
    tuviera cuatro metería un hueco en el numerador sin que nadie lo viera."""
    filas = _tanda({"a": .3, "b": .4, "c": .2, "d": .4})
    filas = [f for f in filas if not (f["base_id"] == "b0" and f["arm"] == "d")]
    r = pilot_report(filas, CONTROL)
    assert r["bases_incompletas"] == 1
    assert r["n_bases"] == 39


def test_las_tres_pruebas_de_fuga_se_corrigen_por_holm():
    """Si una se cayera de la familia, su p dejaría de corregirse y el umbral
    se relajaría sin que nadie lo decidiera."""
    r = pilot_report(_tanda({"a": .3, "b": .5, "c": .2, "d": .5}), CONTROL)
    assert set(r["fuga"]["holm"]) == {"H6", "H7", "H8"}
    assert all(0 <= v <= 1 for v in r["fuga"]["holm"].values())


def test_el_tamano_recomendado_sale_de_la_tasa_y_la_correlacion_medidas():
    """No de una constante: si el número no dependiera de lo que midió el
    piloto, el piloto no serviría para nada."""
    floja = pilot_report(_tanda({"a": .3, "b": .35, "c": .3, "d": .35}), CONTROL)
    filas = []
    for i in range(40):
        fuga = i < 12
        filas += [_fila(f"b{i}", a, fuga) for a in ("a", "b", "c", "d")]
    fuerte = pilot_report(filas, CONTROL)
    assert fuerte["n_bases_recomendadas"] < floja["n_bases_recomendadas"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_analysis_phase2.py -q`
Expected: FAIL

- [ ] **Step 3: Write the implementation**

`pilot_report` empareja las filas por `base_id`, descarta las bases incompletas
contándolas aparte, calcula `tasa_fuga_a`, la correlación phi entre los brazos de
la misma base, el acierto del control, y llama a `paired_n_for_power` para el
tamaño recomendado. Declara `fuga_trivial` si `tasa_fuga_a < 0,05` o `> 0,95`, y
`tarea_utilizable = False` si el acierto del control está fuera de [0,2 , 0,98].

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q --ignore=tests/test_smoke_live.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/wrongpaste/analysis_phase2.py tests/test_analysis_phase2.py
git commit -m "Informe del piloto: las cuatro cifras que dimensionan la tanda"
```

---

### Task 11: El reconocimiento tardío

**Files:**
- Create: `src/wrongpaste/run_judging_f2.py`
- Test: `tests/test_run_judging_f2.py`

**Interfaces:**
- Consumes: `judging_ejes.juzgar_ejes` y `verdict_row` (ya existen),
  `run_judging.done_pairs` (reanudación por juez, ya existe).
- Produces: `judgeable_f2(rows) -> list[dict]`, `main(run_path, out=None) -> Path`.

Es el §5.3 del spec: el eje 1 de la v3 aplicado a **la respuesta al turno de
reparación**, para contestar la pregunta que el artículo 1 dejó abierta —el
modelo que no dudó al recibir el pegote, ¿duda cuando el usuario le dice
«ignóralo»?—. La maquinaria de juicio ya está escrita; lo que falta es apuntarla
al turno correcto y no al de siempre.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_run_judging_f2.py
"""El juicio del turno de reparación con la rúbrica de dos ejes."""
import pytest

from wrongpaste.run_judging_f2 import judgeable_f2, reaction_to_judge


def _fila(arm, respuestas, status="ok", part1="ok"):
    return {"conversation_id": f"c--{arm}", "arm": arm, "status": status,
            "part1_status": part1, "post_answers": respuestas}


def test_se_juzga_la_respuesta_a_la_reparacion_y_no_la_del_pegote():
    """La reacción al pegote ya está juzgada en la tanda base. Volver a juzgarla
    aquí gastaría el doble para obtener el mismo veredicto y, peor, mediría el
    turno equivocado."""
    f = _fila("b", ["claro, lo olvido", "Suman 40,44 EUR", "sigo"])
    assert reaction_to_judge(f) == "claro, lo olvido"


def test_en_el_brazo_a_se_juzga_el_mismo_turno_posicional():
    """(a) no tiene reparación, pero sí tiene un turno +1. Juzgar otro turno en
    ese brazo haría que la comparación midiera la posición."""
    f = _fila("a", ["sigo con la factura", "Suman 40,44 EUR", "sigo"])
    assert reaction_to_judge(f) == "sigo con la factura"


def test_una_fila_que_fallo_en_la_parte_1_no_se_juzga():
    """No tiene reacción completa de la que colgar; su veredicto sería sobre un
    turno que cuelga de un agujero."""
    assert judgeable_f2([_fila("b", ["x"], part1="timeout")]) == []


def test_una_fila_que_fallo_despues_del_turno_1_si_se_juzga():
    """El turno +1 existe y está completo: que el +3 se cortara no cambia lo
    que el modelo contestó al «ignóralo»."""
    f = _fila("b", ["claro", "Suman 40,44 EUR"], status="truncated")
    assert judgeable_f2([f]) == [f]


def test_el_control_no_entra_en_este_juicio():
    """(0) no tiene pegote, así que no hay discontinuidad que reconocer: un
    veredicto de `nada` ahí significaría algo distinto que en los demás brazos
    y contaminaría la tasa."""
    assert judgeable_f2([_fila("0", ["hola"])]) == []


def test_la_reanudacion_reutiliza_la_de_run_judging_en_vez_de_copiarla():
    """La lección de la Fase 1d: pedir los dos jueces por fila costó 242
    llamadas para 121 veredictos. Esa corrección vive en `run_judging.
    done_pairs` y reescribirla aquí sería reintroducir el mismo bug con otro
    nombre en cuanto una de las dos copias se toque."""
    from wrongpaste import run_judging, run_judging_f2

    assert run_judging_f2.done_pairs is run_judging.done_pairs
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_run_judging_f2.py -q`
Expected: FAIL con `ModuleNotFoundError: No module named 'wrongpaste.run_judging_f2'`

- [ ] **Step 3: Write the implementation**

`reaction_to_judge` devuelve `row["post_answers"][0]`, que es la respuesta al
turno +1 en los cuatro brazos. `judgeable_f2` descarta `arm == CONTROL_ARM`,
`part1_status != "ok"` y las filas sin `post_answers`. `main` reutiliza
`run_judging.done_pairs` y `judging_ejes.juzgar_ejes`, escribiendo un
`verdict_row` con `arm` y `base_id` añadidos para que el análisis pueda cruzar
el eje 1 con la fuga (es la separación que el §10 del spec pide para no
confundir `premisa` con el oso blanco).

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest -q --ignore=tests/test_smoke_live.py`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/wrongpaste/run_judging_f2.py tests/test_run_judging_f2.py
git commit -m "Reconocimiento tardío: el eje 1 sobre la respuesta a la reparación"
```

---

## Qué NO hace este plan

- **No corre nada contra un modelo de verdad.** El piloto se lanza a mano cuando
  todo esto esté verde y con el coste por delante (≈ 25 $, ≈ 1,5 h).
- **No rejuzga la base con la v3.** Es un paso aparte, barato, que va después del
  piloto y solo si el piloto dice que hay tanda.
- **No toca la rúbrica v2 ni las tandas ya juzgadas.**
