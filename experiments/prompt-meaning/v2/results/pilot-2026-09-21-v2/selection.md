# Selección de prompts naturales

Revisión: Codex, sin anotación humana independiente. Se leyeron los ocho prompts finales antes de ejecutar decisiones.

| Tarea | Escritor | Decisión | Motivo |
|---|---|---|---|
| access-01 | gpt-sol | excluded | The final prompt gives every operative condition explicitly; no underdefined expression survives the handoff. |
| access-01 | claude-opus | excluded | External exposure is immediately tied to confidential AND external; denial and review conditions are fully specified. |
| expense-01 | claude-opus | excluded | Denial versus review and the two denial grounds are explicitly defined; no underdefined operative expression. |
| expense-01 | gpt-sol | excluded | Exact numeric thresholds and currency test replace the earlier currency-conversion caveat; no underdefined operative expression. |
| release-01 | gpt-sol | excluded | Independence and non-substitution of approval and restore are explained with explicit boolean conditions. |
| release-01 | claude-opus | excluded | All checks are explicit. Additional output fields are an output-contract deviation, not an underdefined technical expression. |
| retention-01 | claude-opus | excluded | Floor and absence of obstacles are defined by the explicit 30-day threshold and listed rules. |
| retention-01 | gpt-sol | excluded | Strict precedence, retention threshold and conditional approval are fully specified. |

Los ocho prompts se ejecutan sin modificar aunque se excluyan del subgrupo terminológico.
