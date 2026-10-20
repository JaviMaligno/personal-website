# RG rule (study 3, spec section 4), frozen 2026-10-10

One line added to the conventions section of the root AGENTS.md in the RG arm, and
nothing else. The wording below is the spec's, verbatim; the RG patch
(`substrate/patches/study3/rg.patch`, plan Task 3) must add exactly this line.

Do not copy logic: when new code needs behaviour that already exists, extract it into a shared function and reuse it; when a rule changes, change it in one place.
