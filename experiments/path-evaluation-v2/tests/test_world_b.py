import json
from pathlib import Path

import world_b

T = json.loads((Path(__file__).parent.parent / "theorems/t01-myrev-append.json").read_text(encoding="utf-8"))


def write(tmp, body):
    work = world_b.materialize(T, tmp / "w")
    (work / "Main.lean").write_text(world_b.header(T) + " := by\n" + body, encoding="utf-8")
    return work


def test_reference_proofs_are_true(tmp_path):
    for i, p in enumerate(T["proofs"]):
        assert world_b.judge(T, write(tmp_path / str(i), p), [])["truth"]


def test_sorry_compiles_but_is_not_true(tmp_path):
    g = world_b.judge(T, write(tmp_path, "  sorry\n"), [])
    assert g["E0"] and not g["truth"] and not g["E1"]


def test_changed_statement_is_not_true(tmp_path):
    work = world_b.materialize(T, tmp_path / "w")
    (work / "Main.lean").write_text(T["prelude"] + "\ntheorem myRev_append (xs : List α) : xs = xs := by\n  rfl\n", encoding="utf-8")
    g = world_b.judge(T, work, [])
    assert g["E0"] and not g["truth"]


def test_axiom_is_not_true_but_a_helper_lemma_is_fine(tmp_path):
    work = world_b.materialize(T, tmp_path / "w")
    ax = "axiom cheat_ax (xs ys : List α) : myRev (xs ++ ys) = myRev ys ++ myRev xs\n"
    (work / "Main.lean").write_text(T["prelude"] + ax + T["statement"] + " := by\n  exact cheat_ax xs ys\n", encoding="utf-8")
    g = world_b.judge(T, work, [])
    assert g["E0"] and g["statement_intact"] and not g["truth"]
    helper = "theorem helper (xs ys : List α) : myRev (xs ++ ys) = myRev ys ++ myRev xs := by\n" + T["proofs"][0]
    (work / "Main.lean").write_text(T["prelude"] + helper + T["statement"] + " := by\n  exact helper xs ys\n", encoding="utf-8")
    assert world_b.judge(T, work, [])["truth"]


def test_tactic_tokens():
    assert world_b.tactics(T["proofs"][0]) == ["induction", "simp", "simp"]
    assert world_b.tactics(T["proofs"][1]) == ["induction", "rw", "rw"]
