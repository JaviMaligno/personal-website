# Discriminating refinement-boundary check

Added while the main review calls were running, after reading the generated
handoffs but BEFORE reading their review decisions. This is a supplementary
test motivated by an observed omission, not part of the original pre-call bank.
Keep its results separate. No main-run source, prompt or response is modified.

The original p15 rejects marking *any* imperfect artifact evidence-capped at zero
iterations. That is underdetermined as a diagnostic of the missing loop-entry
condition: a reviewer can reject it simply because some imperfect artifacts
have failures INSIDE the allowed set, a condition the handoffs DO retain.

The supplement pins the initial accuracy, failure source IDs, allowed set, and
iteration budget. Two paired tests put every attributable failure OUTSIDE the
allowed set, varying only whether a loop iteration is available; two controls
cover an allowed failure and an already perfect artifact. Expectations come
from the existing `refine_capped` code. There are no infra errors in these cases.

One completed dose chain, four contexts, two executor models, two fresh calls
each: 16 calls. Use the same original dossier and exact first/last handoffs.
Opaque replacement remains identical in context and proposals. Same providers,
settings, no automatic retries, and no selection based on review outcomes.
The context-compression observation motivating the probe is itself post-generation
and must not be represented as preregistered before handoff generation.

Budget announced before these calls: 3–6 minutes, less than $2 reference total.
