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


def _weaker(tmp, wrap):
    work = world_b.materialize(T, tmp / "w")
    weak = "theorem myRev_append (xs : List α) : xs = xs := by rfl\n"
    (work / "Main.lean").write_text(T["prelude"] + wrap(T["statement"]) + "\n" + weak, encoding="utf-8")
    return world_b.judge(T, work, [])


def test_statement_hidden_in_comment_or_namespace_is_not_true(tmp_path):
    for i, wrap in enumerate([lambda s: "-- " + s, lambda s: "/- " + s + " -/"]):
        g = _weaker(tmp_path / str(i), wrap)
        assert g["E0"] and not g["statement_intact"] and not g["truth"] and not g["E1"]
    g = _weaker(tmp_path / "ns", lambda s: "namespace Foo\n" + s + " := by\n" + T["proofs"][0] + "end Foo")
    assert g["E0"] and not g["truth"]


def test_sorry_flag_and_json_serialisable_axioms(tmp_path):
    assert world_b.judge(T, write(tmp_path / "s", "  sorry\n"), [])["sorry"]
    g = world_b.judge(T, write(tmp_path / "r", T["proofs"][0]), [])
    json.dumps(g)


def test_tactic_tokens():
    assert world_b.tactics(T["proofs"][0]) == ["induction", "simp", "simp"]
    # A literal proof: the task's other references were re-authored by Astra and change shape.
    assert world_b.tactics("  induction xs with\n  | nil => rw [myRev]\n  | cons x xs ih => rw [myRev, ih]\n") == ["induction", "rw", "rw"]


def test_unclosed_namespace_shadowing_prelude_is_not_intact():
    ns = T["prelude"] + "\nnamespace Foo\ndef myRev (_ : List α) : List α := []\n" + T["statement"] + " := by\n  simp [myRev]\n"
    assert not world_b.statement_intact(T, ns)


def test_proof_body_matches_exact_name_and_stops_at_next_declaration():
    aux = "theorem " + T["name"] + "_aux (xs : List α) : xs ++ [] = xs := by\n  rw [List.append_nil]\n"
    later = "\ntheorem later (xs : List α) : xs = xs := by\n  rfl\n"
    txt = T["prelude"] + "\n" + aux + T["statement"] + " := by\n" + T["proofs"][0] + later
    assert world_b.tactics(world_b.proof_body(T, txt)) == world_b.tactics(T["proofs"][0])
