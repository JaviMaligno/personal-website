# The Exponential Time Hypothesis Fell Twice — part 1 of 2: the problem · script draft v1 (PENDING APPROVAL)

Article: exponential-time-hypothesis-falls (javieraguilar.ai, EN/ES, pubDate 2026-10-28).
Vertical 9:16, ~55 s. Part 1 explains the problem with the article's dinner party, ending on the
hook for part 2 (`../exponential-time-hypothesis-falls-2`). Built ahead of approval at Javier's
request; narration not generated yet (no Cartesia key in the cloud session).

| # | Narration (EN) | Narration (ES) | Visual | Component | Source sentence |
|---|---|---|---|---|---|
| 1 | Your friends send conditions for a dinner. Is there one guest list that works? | Tus amigos te mandan condiciones para una cena. ¿Hay una lista de invitados que funcione? | Hook card | intro | "Say you are organising a dinner and your friends have sent conditions."; "is there any guest list that meets every condition at once?" |
| 2-4 | "Ana comes, or Bea doesn't." / "Carlos or Diego, at least one." / "Not Ana, Bea and Carlos together." | (same, ES) | Four friends A B C D; the three condition cards slide in one per line | bespoke `DinnerParty` (intro) | the article's three conditions (figure 1 wording) |
| 5 | Each friend is a yes or a no. Each condition names at most three. | Cada amigo es un sí o un no. Cada condición nombra como mucho a tres. | Yes/no chips under the friends, flickering | `DinnerParty` (intro) | "Each friend is a yes/no decision, and each condition mentions at most three friends." |
| 6 | That's 3-SAT, the reference hard problem of computer science. | Eso es 3-SAT, el problema difícil de referencia de la informática. | "3-SAT" stamp | `DinnerParty` (intro) | "That is 3-SAT."; "That is why it is the reference hard problem of computer science." |
| 7 | Checking a guest list is easy: one pass over the conditions. | Comprobar una lista es fácil: una pasada por las condiciones. | List fills (Ana yes, Bea no, Carlos yes, Diego no), each card ticks green | `DinnerParty` (check) | "checking it is trivial: go through the conditions one by one." |
| 8 | Finding one is hard: every friend you add doubles the lists to try. | Encontrarla es difícil: cada amigo que añades duplica las listas que probar. | Tiles 1,024 / ≈ 1 billion / 31 digits | `StatGrid` | "With n friends there are 2^n possible lists"; figure 1: "1,024", "≈ 1 billion", "a 31-digit number"; "doubles in cost with every friend you add" |
| 9 | About a billion with 30 friends. A 31-digit number with 100. | Unos mil millones con 30 amigos. Un número de 31 cifras con 100. | (same) | `StatGrid` | "with 30 friends, about a billion"; "2^100 is a 31-digit number" |
| 10 | Forty years of clever ideas lowered that growth rate. Never to one. | Cuarenta años de ideas ingeniosas bajaron ese ritmo de crecimiento. Nunca a uno. | Bars 2ⁿ, 1.334ⁿ, 1.308ⁿ | `BarCompare` | "forty years of very clever work never brought the base close to 1." |
| 11 | In 1999 that became a bet: the Exponential Time Hypothesis. | En 1999 eso se convirtió en una apuesta: la hipótesis del tiempo exponencial. | Counter 800+ | `Counter` | "In 1999 Russell Impagliazzo and Ramamohan Paturi turned that experience into a conjecture, the Exponential Time Hypothesis" |
| 12 | Over 800 papers rest on it. | Más de 800 artículos se apoyan en ella. | "800+ papers rest on ETH" | `Counter` | "more than 800 papers proving at least one result only under ETH" |
| 13 | This week, two AI labs proved it false. Part two: how. | Esta semana, dos laboratorios de IA demostraron que es falsa. Segunda parte: cómo. | "This week it fell. Twice." | `KeyQuote` | "On 26 October two papers appeared within hours of each other." |
| 14 | (no narration) | | Outro card | outro | |

Spoken forms: "3-SAT" → "three-SAT".
