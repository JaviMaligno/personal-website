"""Spec amendment 2026-10-12b, item 7: RG's manipulation check is behaviour only;
``agents_md_read`` is renamed ``agents_md_explicit_read`` and is not a manipulation check."""
from aa import rg_check


def test_explicit_read_reads_new_and_legacy_key():
    assert rg_check.agents_md_explicit_read({"agents_md_explicit_read": True}) is True
    assert rg_check.agents_md_explicit_read({"agents_md_explicit_read": False}) is False
    # result.json written before the rename (runs3-pilot) keeps the legacy key
    assert rg_check.agents_md_explicit_read({"agents_md_read": True}) is True
    assert rg_check.agents_md_explicit_read({"agents_md_read": False}) is False
    # the new key wins when both are present
    assert rg_check.agents_md_explicit_read(
        {"agents_md_read": True, "agents_md_explicit_read": False}) is False


def test_explicit_read_missing_is_none():
    assert rg_check.agents_md_explicit_read({}) is None
    assert rg_check.agents_md_explicit_read(None) is None
    assert rg_check.agents_md_explicit_read({"agents_md_read": None}) is None


def test_normalise_renames_without_mutating():
    legacy = {"rule_quoted": False, "reuse_talk": True, "agents_md_read": True}
    out = rg_check.normalise_rule_detail(legacy)
    assert out == {"rule_quoted": False, "reuse_talk": True, "agents_md_explicit_read": True}
    assert "agents_md_read" in legacy  # input untouched
    assert rg_check.normalise_rule_detail(None) == {}
    already = {"agents_md_explicit_read": False, "rule_quoted": True}
    assert rg_check.normalise_rule_detail(already) == already


def test_registered_measures():
    # behaviour only: the judge's T2 label and one_place, and the static T2 label
    assert rg_check.RG_COMPLIANCE_MEASURES == ("t2_reuse", "one_place", "t2_reuses_logic")
    # descriptive only, never a manipulation check
    assert set(rg_check.RG_DESCRIPTIVE) == {"rule_cited", "agents_md_explicit_read"}
    assert "agents_md_explicit_read" not in rg_check.RG_COMPLIANCE_MEASURES
