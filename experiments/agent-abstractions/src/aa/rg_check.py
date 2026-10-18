"""RG (written rule) measures after the study-3 pilot (spec amendment 2026-10-12b, item 7).

The pilot showed that no transcript measure can observe the RG rule being used: Claude
Code (through the variant's ``CLAUDE.md`` -> ``@AGENTS.md``) and Codex load AGENTS.md into
the agent's context themselves, so nobody opens it with a tool call, and the rule was
quoted in 0/48 RG steps. RG compliance is therefore measured by behaviour only
(:data:`RG_COMPLIANCE_MEASURES`). What ``rule_cited`` recorded as ``agents_md_read`` is
renamed ``agents_md_explicit_read``: whether the agent opened AGENTS.md with a tool call,
descriptive and never a manipulation check. ``aa.chain_eval3.rule_cited`` writes the new
key (amendment 2026-10-12c); results evaluated before (runs3-pilot) keep the legacy one,
so readers (``aa tables3``) go through :func:`agents_md_explicit_read` or
:func:`normalise_rule_detail`, which accept both keys, and stored ``result.json`` files
need no re-derivation for the rename.
"""
from __future__ import annotations

from typing import Any

LEGACY_KEY = "agents_md_read"
EXPLICIT_KEY = "agents_md_explicit_read"

# behaviour-only RG compliance: the judge's T2 reuse label and rule-step one_place label
# (primary), and the static T2 label (secondary)
RG_COMPLIANCE_MEASURES = ("t2_reuse", "one_place", "t2_reuses_logic")
# reported descriptively in every arm (R is the baseline), never as a manipulation check
RG_DESCRIPTIVE = ("rule_cited", EXPLICIT_KEY)


def agents_md_explicit_read(detail: dict[str, Any] | None) -> bool | None:
    """Whether the agent opened AGENTS.md with a tool call (``rule_cited_detail``); the
    new key wins over the legacy one; None when neither is recorded."""
    if not detail:
        return None
    v = detail.get(EXPLICIT_KEY, detail.get(LEGACY_KEY))
    return None if v is None else bool(v)


def normalise_rule_detail(detail: dict[str, Any] | None) -> dict[str, Any]:
    """A copy of ``rule_cited_detail`` with the legacy key renamed (input untouched)."""
    out = dict(detail or {})
    if LEGACY_KEY in out:
        legacy = out.pop(LEGACY_KEY)
        out.setdefault(EXPLICIT_KEY, legacy)
    return out
