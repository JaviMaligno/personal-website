# Cross-family judge: Opus 5.5 vs GPT-6.1 Sol on 480 chain packets

## Agreement (quadratic-weighted kappa)

| score | kappa | exact | mean Opus | mean Sol |
|---|---|---|---|---|
| reuse | 0.78 | 65% | 3.64 | 3.72 |
| duplication | 0.87 | 70% | 3.01 | 3.12 |
| placement | 0.66 | 57% | 3.99 | 4.29 |
| scope | 0.14 | 33% | 4.19 | 4.91 |
| maintainability | 0.78 | 71% | 3.08 | 3.12 |

## Own-family preference: d = Opus − Sol (maintainability)

| subset | d, Claude-written (n) | d, Codex-written (n) | difference | MW p |
|---|---|---|---|---|
| all | +0.04 (320) | -0.17 (160) | +0.21 | 0.000 |
| Z1 | +0.00 (80) | -0.23 (40) | +0.23 | 0.044 |
| Z2 | +0.05 (80) | -0.33 (40) | +0.38 | 0.001 |
| Z3 | +0.00 (80) | -0.17 (40) | +0.17 | 0.129 |
| Z4 | +0.10 (80) | +0.03 (40) | +0.08 | 0.392 |
| R | -0.05 (64) | -0.25 (32) | +0.20 | 0.055 |
| RG | +0.06 (64) | -0.25 (32) | +0.31 | 0.017 |
| RL | +0.16 (64) | -0.16 (32) | +0.31 | 0.014 |
| RC | +0.05 (64) | -0.09 (32) | +0.14 | 0.265 |
| F | -0.03 (64) | -0.12 (32) | +0.09 | 0.391 |

Sonnet alone vs Codex (same-tier comparison):

| subset | d, Sonnet (n) | d, Haiku (n) | d, Codex (n) |
|---|---|---|---|
| reuse | +0.01 (160) | -0.04 (160) | -0.20 (160) |
| duplication | -0.05 (160) | -0.19 (160) | -0.10 (160) |
| placement | -0.27 (160) | -0.23 (160) | -0.40 (160) |
| scope | -0.78 (160) | -0.58 (160) | -0.79 (160) |
| maintainability | +0.01 (160) | +0.06 (160) | -0.17 (160) |

## H1 re-read with each judge (maintainability, lever arm vs R, all zones)

| agent | arm | Opus arm vs R (p) | Sol arm vs R (p) |
|---|---|---|---|
| claude | RG | 3.09 vs 2.59 (0.0046) | 3.06 vs 2.75 (0.0208) |
| claude | RL | 3.19 vs 2.59 (0.0126) | 3.00 vs 2.75 (0.1796) |
| claude | RC | 3.06 vs 2.59 (0.0167) | 3.09 vs 2.75 (0.0273) |
| claude | F | 3.41 vs 2.59 (0.0000) | 3.38 vs 2.75 (0.0004) |
| claude | RL, Z1+Z3 | 3.69 vs 2.56 (0.0011) | 3.31 vs 2.88 (0.0412) |
| codex | RG | 2.16 vs 2.19 (0.8750) | 2.41 vs 2.44 (0.8078) |
| codex | RL | 2.34 vs 2.19 (0.4276) | 2.50 vs 2.44 (0.6246) |
| codex | RC | 2.59 vs 2.19 (0.0232) | 2.69 vs 2.44 (0.0943) |
| codex | F | 2.78 vs 2.19 (0.0052) | 2.91 vs 2.44 (0.0116) |
| codex | RL, Z1+Z3 | 2.56 vs 2.50 (1.0000) | 2.81 vs 2.75 (0.6932) |
| haiku | RG | 3.78 vs 3.56 (0.1226) | 3.69 vs 3.50 (0.2490) |
| haiku | RL | 3.69 vs 3.56 (0.3815) | 3.56 vs 3.50 (0.6412) |
| haiku | RC | 3.91 vs 3.56 (0.0245) | 3.78 vs 3.50 (0.0449) |
| haiku | F | 3.91 vs 3.56 (0.0340) | 4.00 vs 3.50 (0.0049) |
| haiku | RL, Z1+Z3 | 3.69 vs 3.56 (0.4352) | 3.69 vs 3.31 (0.0707) |
