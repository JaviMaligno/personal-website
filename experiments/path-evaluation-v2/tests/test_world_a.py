import json
from pathlib import Path

import world_a

BUG = json.loads((Path(__file__).parent.parent / "bugs/b01-ordinal-teens.json").read_text(encoding="utf-8"))


def test_validate_worked_example(tmp_path):
    report = world_a.validate(BUG, tmp_path)
    assert report == {"visible_fails_only_issue": True, "fix_passes_visible": True, "pristine_fails_with_bug": True,
                      "pristine_passes_with_fix": True, "cheat_passes_issue": True, "hidden_fails_cheat": True}


def test_truth_and_graders(tmp_path):
    work = world_a.materialize(BUG, tmp_path / "w")
    world_a.apply(work, BUG["file"], BUG["new"], BUG["old"])  # the right fix
    acts = [{"kind": "run_tests", "target": ""}, {"kind": "read", "target": BUG["file"]},
            {"kind": "edit", "target": BUG["file"]}, {"kind": "run_tests", "target": ""}]
    g = world_a.judge(BUG, work, acts, tmp_path / "j")
    assert g["truth"] and g["E0"] and g["E1"] and g["E2"] and g["E3"]
