# Agregación descriptiva

Descriptive counts; cells reuse four policies and their inputs, not independent samples.

## Predicciones

Pares: repeticiones incluidas. Estables: cada input se cuenta una vez por comparación,
solo cuando ambas variantes coinciden consigo mismas entre las dos repeticiones.

| Tipo / etiqueta | Explica → ejecuta | Intervención | Pares evaluables / previstos | Exactos | Abstenciones | Detecta cambio | Sin cambio (referencia) | Exactos / evaluables estables | Inputs inestables |
|---|---|---|---|---|---|---|---|---|---|
| synthetic / suggestive | gpt-sol → gpt-sol | eliminated | 20/96 | 20 | 76 | 20 | 20 | 10/10 | 4 |
| synthetic / suggestive | gpt-sol → gpt-sol | substituted | 0/96 | 0 | 96 | 0 | 0 | 0/0 | 4 |
| synthetic / suggestive | gpt-sol → claude-opus | eliminated | 20/96 | 20 | 76 | 20 | 20 | 10/10 | 1 |
| synthetic / suggestive | gpt-sol → claude-opus | substituted | 0/96 | 0 | 96 | 0 | 0 | 0/0 | 0 |
| synthetic / suggestive | claude-opus → gpt-sol | eliminated | 62/96 | 59 | 34 | 59 | 59 | 29/30 | 4 |
| synthetic / suggestive | claude-opus → gpt-sol | substituted | 62/96 | 59 | 34 | 59 | 59 | 29/30 | 4 |
| synthetic / suggestive | claude-opus → claude-opus | eliminated | 62/96 | 60 | 34 | 60 | 60 | 30/31 | 1 |
| synthetic / suggestive | claude-opus → claude-opus | substituted | 12/96 | 11 | 34 | 11 | 11 | 0/0 | 0 |
| synthetic / opaque | gpt-sol → gpt-sol | eliminated | 0/96 | 0 | 96 | 0 | 0 | 0/0 | 0 |
| synthetic / opaque | gpt-sol → gpt-sol | substituted | 0/96 | 0 | 96 | 0 | 0 | 0/0 | 0 |
| synthetic / opaque | gpt-sol → claude-opus | eliminated | 0/96 | 0 | 96 | 0 | 0 | 0/0 | 0 |
| synthetic / opaque | gpt-sol → claude-opus | substituted | 0/96 | 0 | 96 | 0 | 0 | 0/0 | 0 |
| synthetic / opaque | claude-opus → gpt-sol | eliminated | 72/96 | 72 | 24 | 72 | 72 | 36/36 | 0 |
| synthetic / opaque | claude-opus → gpt-sol | substituted | 72/96 | 72 | 24 | 72 | 72 | 36/36 | 0 |
| synthetic / opaque | claude-opus → claude-opus | eliminated | 12/96 | 12 | 24 | 12 | 12 | 0/0 | 0 |
| synthetic / opaque | claude-opus → claude-opus | substituted | 12/96 | 12 | 24 | 12 | 12 | 0/0 | 0 |
| positive / — | gpt-sol → gpt-sol | eliminated | 4/4 | 4 | 0 | 4 | 2 | 2/2 | 0 |
| positive / — | gpt-sol → claude-opus | eliminated | 4/4 | 4 | 0 | 4 | 2 | 2/2 | 0 |
| positive / — | claude-opus → gpt-sol | eliminated | 4/4 | 4 | 0 | 4 | 2 | 2/2 | 0 |
| positive / — | claude-opus → claude-opus | eliminated | 4/4 | 4 | 0 | 4 | 2 | 2/2 | 0 |
| redundant / — | gpt-sol → gpt-sol | eliminated | 4/4 | 4 | 0 | 4 | 4 | 2/2 | 0 |
| redundant / — | gpt-sol → claude-opus | eliminated | 4/4 | 4 | 0 | 4 | 4 | 2/2 | 0 |
| redundant / — | claude-opus → gpt-sol | eliminated | 4/4 | 4 | 0 | 4 | 4 | 2/2 | 0 |
| redundant / — | claude-opus → claude-opus | eliminated | 4/4 | 4 | 0 | 4 | 4 | 2/2 | 0 |

## Traspasos sin modificar

| Tarea | Escritor | Ejecutor | Correctas / previstas | Válidas |
|---|---|---|---|---|
| expense-01 | gpt-sol | gpt-sol | 24/24 | 24 |
| access-01 | gpt-sol | claude-opus | 24/24 | 24 |
| retention-01 | claude-opus | gpt-sol | 24/24 | 24 |
| access-01 | claude-opus | claude-opus | 24/24 | 24 |
| expense-01 | claude-opus | claude-opus | 24/24 | 24 |
| access-01 | claude-opus | gpt-sol | 24/24 | 24 |
| release-01 | claude-opus | claude-opus | 24/24 | 24 |
| expense-01 | claude-opus | gpt-sol | 24/24 | 24 |
| retention-01 | gpt-sol | claude-opus | 24/24 | 24 |
| release-01 | claude-opus | gpt-sol | 24/24 | 24 |
| release-01 | gpt-sol | claude-opus | 24/24 | 24 |
| expense-01 | gpt-sol | claude-opus | 24/24 | 24 |
| retention-01 | gpt-sol | gpt-sol | 24/24 | 24 |
| access-01 | gpt-sol | gpt-sol | 24/24 | 24 |
| retention-01 | claude-opus | claude-opus | 24/24 | 24 |
| release-01 | gpt-sol | gpt-sol | 24/24 | 24 |
