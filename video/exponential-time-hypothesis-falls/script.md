# The Exponential Time Hypothesis Fell Twice — article video (EN) · script draft v1 (PENDING APPROVAL)

Article: exponential-time-hypothesis-falls (javieraguilar.ai, EN/ES, pubDate 2026-10-28).
Vertical 9:16, target ~55-58 s, 140 spoken words. The article explains two results by OpenAI and
Anthropic, not an experiment of mine: the proofs are never presented as mine. ES lines are
written alongside so the Spanish cut can follow once a Spanish voice is picked.

Built ahead of approval at Javier's request (urgent publication): timeline, two bespoke
components and stills exist, narration is NOT generated (no Cartesia key in the cloud session).
Any change to the lines below is cheap: edit `src/timeline.ts`, re-lint, re-run stills.

## Central visual idea: the wall and the minus sign

One graph runs through the middle of the video. First it is the hard formula: a ring of clause
nodes so tangled that a cut swept around it always lights up many crossing links (the wall).
Then one rectangle of the grid is pulled out of it: two crossing links (x = v, y = u) split into
a "row" piece and a "column" piece, each cheap in one direction, with a minus sign between the
worlds of counting and deciding. Everything else is library components.

| # | Narration (EN) | Narration (ES) | Visual | Component | Source sentence |
|---|---|---|---|---|---|
| 1 | Two AI labs just refuted the same famous hypothesis, hours apart. | Dos laboratorios de IA acaban de refutar la misma hipótesis famosa, con horas de diferencia. | Hook card | intro | "On 26 October two papers appeared within hours of each other."; "Both were found by an internal model." |
| 2 | Since the 1980s, every 3-SAT algorithm has needed exponential time. | Desde los ochenta, todo algoritmo para 3-SAT ha necesitado tiempo exponencial. | Bars: brute force 2ⁿ | `BarCompare` | "Trying all 2^n assignments always works. The game since the 1980s has been to beat that" |
| 3 | Clever ideas shrank the base. Never to one. | Ideas ingeniosas rebajaron la base. Nunca a uno. | Bars 1.334ⁿ, 1.308ⁿ grow, shorter | `BarCompare` | "Schöning's random walk got 1.334^n in 1999, PPSZ and Hertli's analysis got 1.308^n"; "the base never got close to 1." |
| 4 | In 1999 that became a bet: the Exponential Time Hypothesis. | En 1999 eso se convirtió en una apuesta: la hipótesis del tiempo exponencial. | Counter 800+ (starts on line 5) | `Counter` | "In 1999 Russell Impagliazzo and Ramamohan Paturi turned that experience into a hypothesis" |
| 5 | Over 800 papers rest on it. | Más de 800 artículos se apoyan en ella. | Counter reaches "800+", label "papers rest on ETH" | `Counter` | "more than 800 papers proving at least one result only under ETH or something that implies it" |
| 6 | The wall: hard formulas can't be split without cutting too many links. | El muro: las fórmulas difíciles no se pueden partir sin cortar demasiados enlaces. | Tangled ring of nodes; a dashed cut sweeps round, the crossing links glow amber at every angle; label "every cut: many bits" | bespoke `ExpanderCut` | "every way of splitting the nodes into two halves of comparable size is crossed by a constant fraction of all the edges"; "This is the wall." |
| 7 | Both labs count the solutions instead, so terms can cancel. | Los dos cuentan las soluciones, para que los términos puedan cancelarse. | Key line "Count, don't decide." | `KeyQuote` | "They count them, exactly"; "Once negative numbers are allowed in the middle of the computation, two expensive pieces can cancel into a cheap one." |
| 8 | Claude's proof uses an identity from 1818, from the octonions. | La prueba de Claude usa una identidad de 1818, de los octoniones. | Rectangle x, y / u, v with two crossing diagonals, "6 bits"; small "1818 · octonions" tag | bespoke `CrossingRewrite` (beat 0) | "One of them does it with an identity a Danish mathematician wrote down in 1818."; "the table of signs of the multiplication of the octonions" |
| 9 | Two crossing links become pieces that are cheap one way or the other. | Dos enlaces cruzados se convierten en piezas baratas en una dirección o en la otra. | The crossing splits into "row choice · 3 bits" + "column choice · 3 bits (columns)", a ± between them | bespoke `CrossingRewrite` (beat 1) | "Neither term means anything combinatorially, they take negative values, and only their sum is a count. But each term is cheap in one direction." |
| 10 | Each level shrinks the exponent by eleven twelfths, as low as you like. | Cada nivel encoge el exponente en once doceavos, tan bajo como quieras. | Bars: level 0 "1", level 2 "0.94", level 5 "0.73", level 10 "0.47" | `BarCompare` | "One level shrinks the exponent by a factor of 11/12. Repeat it and the exponent goes to zero: the paper's bound is e_ℓ ≤ 1.12 (11/12)^ℓ"; figure values from that bound |
| 11 | OpenAI's proof deforms the problem, solves the easy cases, and interpolates back. | La de OpenAI deforma el problema, resuelve los casos fáciles e interpola de vuelta. | Flow: "Deform: H(T)" → "Easy points T = 1…Q" → "Interpolate: H(0) = count" | `FlowDiagram` | "deform the problem, then interpolate back"; "At those points the expensive problem becomes cheap."; "you read off H(0)" |
| 12 | No faster solvers: it only wins past 10^10,000 variables. | Sin solvers más rápidos: solo gana pasadas 10^10.000 variables. | Tiles "10^10,000 variables" / "P vs NP untouched" | `StatGrid` | "beats the 2^n of brute force only once n > 10^{10 000}"; "P vs NP is untouched." |
| 13 | Two labs, the same week, the same bound. The hypothesis is false. | Dos laboratorios, la misma semana, la misma cota. La hipótesis es falsa. | Key line "ETH is false. Twice." | `KeyQuote` | "Two labs, the same week, the same bound."; "ETH is false, twice, independently, with formal proofs, pending the human review that is now under way." |
| 14 | (no narration) | | Outro card ~2 s: AGILabs badge, javieraguilar.ai, article title | outro | |

**Word count (EN):** 11 + 10 + 8 + 10 + 6 + 12 + 10 + 10 + 13 + 13 + 12 + 9 + 12 = **136 words**
("10^10,000" spoken "ten to the ten thousand"), about 55 s at ~2.5 words/s plus the silent
outro.

## Hedges kept from the article

- Row 13 says "false" without "pending review" for length; the article's own closing bullet
  carries the hedge. If Javier prefers, swap row 13 for "Two labs, the same week, the same
  bound. Now the humans check it." (12 words).
- The exponent bars are the article's bound (Figure 4), not measured values.

## Spoken forms

- "10^10,000" → "ten to the ten thousand".
- "3-SAT" → "three sat".
- "1818" → "eighteen eighteen"; "1999" → "nineteen ninety-nine" (TTS usually gets these; listed
  in case it does not).
