# The Exponential Time Hypothesis Fell Twice — part 2 of 2: how it fell · script draft v2 (PENDING APPROVAL)

v2: split in two videos at Javier's request. Part 1 (`../exponential-time-hypothesis-falls-1`) now
explains the problem with the dinner party; rows 2-5 below (3-SAT, bases, 1999, 800 papers)
moved there, the hook is new and the wall is told with the dinner's conditions.

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
| 1 | Two AI labs just refuted the Exponential Time Hypothesis. Here is how. | Dos laboratorios de IA acaban de refutar la hipótesis del tiempo exponencial. Así lo hicieron. | Hook card | intro | "On 26 October two papers appeared within hours of each other." |
| 6 | Link two conditions when they share a friend. The wall: hard puzzles can't be split without cutting too many links. | Une dos condiciones cuando comparten un amigo. El muro: los puzles difíciles no se pueden partir sin cortar demasiados enlaces. | Tangled ring; on the second line a cut sweeps round and the crossing links glow | bespoke `ExpanderCut` | "join two dots with a line when they mention the same friend"; "every way of splitting the nodes into two halves of comparable size is crossed by a constant fraction of all the edges" |
| 7 | Both labs count the solutions instead, so terms can cancel. | Los dos cuentan las soluciones, para que los términos puedan cancelarse. | Key line "Count, don't decide." | `KeyQuote` | "They count them, exactly"; "Once negative numbers are allowed in the middle of the computation, two expensive pieces can cancel into a cheap one." |
| 8 | Claude's proof uses an identity from 1818, from the octonions. | La prueba de Claude usa una identidad de 1818, de los octoniones. | Rectangle x, y / u, v with two crossing diagonals, "6 bits"; small "1818 · octonions" tag | bespoke `CrossingRewrite` (beat 0) | "One of them does it with an identity a Danish mathematician wrote down in 1818."; "the table of signs of the multiplication of the octonions" |
| 9 | Two crossing links become pieces that are cheap one way or the other. | Dos enlaces cruzados se convierten en piezas baratas en una dirección o en la otra. | The crossing splits into "row choice · 3 bits" + "column choice · 3 bits (columns)", a ± between them | bespoke `CrossingRewrite` (beat 1) | "Neither term means anything combinatorially, they take negative values, and only their sum is a count. But each term is cheap in one direction." |
| 10 | Each level shrinks the exponent by eleven twelfths, as low as you like. | Cada nivel encoge el exponente en once doceavos, tan bajo como quieras. | Bars: level 0 "1", level 2 "0.94", level 5 "0.73", level 10 "0.47" | `BarCompare` | "One level shrinks the exponent by a factor of 11/12. Repeat it and the exponent goes to zero: the paper's bound is e_ℓ ≤ 1.12 (11/12)^ℓ"; figure values from that bound |
| 11 | OpenAI's proof deforms the problem, solves the easy cases, and interpolates back. | La de OpenAI deforma el problema, resuelve los casos fáciles e interpola de vuelta. | Flow: "Deform: H(T)" → "Easy points T = 1…Q" → "Interpolate: H(0) = count" | `FlowDiagram` | "deform the problem, then interpolate back"; "At those points the expensive problem becomes cheap."; "you read off H(0)" |
| 12 | No faster solvers: it only wins past 10^10,000 variables. | Sin solvers más rápidos: solo gana pasadas 10^10.000 variables. | Tiles "10^10,000 variables" / "P vs NP untouched" | `StatGrid` | "beats the 2^n of brute force only once n > 10^{10 000}"; "P vs NP is untouched." |
| 13 | Two labs, the same week, the same bound. The hypothesis is false. | Dos laboratorios, la misma semana, la misma cota. La hipótesis es falsa. | Key line "ETH is false. Twice." | `KeyQuote` | "Two labs, the same week, the same bound."; "ETH is false, twice, independently, with formal proofs, pending the human review that is now under way." |
| 14 | (no narration) | | Outro card ~2 s: AGILabs badge, javieraguilar.ai, article title | outro | |

**Length (v2):** about 54 s by the template's estimate (`npm run lint` checks it again after TTS).

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
