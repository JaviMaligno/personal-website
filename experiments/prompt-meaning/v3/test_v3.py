import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import analyze
import bank
import protocol
import run
import storage


def fixture_config():
    return {"models": [dict(id=m, model="fixture-"+m, transport="openai",
        endpoint="https://example.invalid/completions", max_tokens=8192, key_env="FIXTURE_KEY")
        for m in ("gpt-sol", "claude-opus")]}


class StudyTests(unittest.TestCase):
    def test_bank_and_incomplete_suite(self):
        tasks = bank.build_bank()
        self.assertEqual(len(tasks), 4)
        for t in tasks:
            self.assertEqual(len(t["cases"]), 20)
            seen = [c for c in t["cases"] if c["visible"]]
            self.assertEqual(len(seen), 6)
            self.assertEqual({a:sum(c["expected"]==a for c in seen) for a in ("allow","review","deny")},
                             {"allow":2,"review":2,"deny":2})
            self.assertTrue(all(c["expected"] == c["simplified"] for c in seen))
            self.assertGreater(sum(c["separating"] for c in t["cases"]), 0)

    def test_intervention_and_isolation(self):
        a = {"term":"Scoped approval", "guide":"Scoped approval: apply scoped approval after checks."}
        text, count = protocol.rename(a)
        self.assertEqual(count, 2)
        self.assertEqual(text,"velun protocol: apply velun protocol after checks.")
        self.assertEqual(protocol.rename({"term":"missing", "guide":"No local name."}), (None, 0))
        for t in bank.build_bank():
            guide = {"term":"fixture", "guide":"fixture: " + t["rules"]}
            prompt = protocol.handoff_prompt(t, guide, [])
            for c in t["cases"]:
                if not c["visible"]:
                    self.assertNotIn('"id": "'+c["id"]+'"', prompt)
            execution = protocol.execution_prompt(t, guide["guide"], t["cases"], 1)
            self.assertNotIn('"expected"', execution)
            self.assertNotIn('"simplified"', execution)
        with self.assertRaises(ValueError):
            protocol.strict_json('{"x":1,"x":2}')
        with self.assertRaises(ValueError):
            protocol.strict_json('{"decisions":{}} extra note')

    def test_complete_pipeline_and_distinct_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/"runs"; root.mkdir()
            cfg = Path(tmp)/"config.json"; storage.write(cfg, fixture_config())
            run.init(root, cfg)
            data = run.manifest(root)
            tasks = {t["id"]:t for t in data["tasks"]}
            drift_id = next(c["id"] for c in tasks["approval"]["cases"] if c["separating"])
            for stage in run.STAGES:
                plan = run.plan(root, data, stage)

                def fake_complete(model, prompt):
                    j = next(j for j in plan["jobs"] if j["model_id"] == model["id"] and j["prompt"] == prompt)
                    t = tasks[j["task_id"]]
                    if stage in ("source", "handoff"):
                        marker = "Received guide. " if stage == "handoff" else "Source guide. "
                        text = json.dumps({"term":"fixture concept", "guide":marker + "fixture concept: " + t["rules"]})
                    else:
                        cases = [c for c in t["cases"] if stage == "final" or c["visible"]]
                        labels = {c["id"]: c["expected"] for c in cases}
                        if stage == "final" and j["chain_id"] == "approval--gpt-sol" and model["id"] == "gpt-sol":
                            if j["variant"] in ("received", "renamed"):
                                labels[drift_id] = next(c["simplified"] for c in cases if c["id"] == drift_id)
                        if stage == "final" and j["chain_id"] == "recovery--gpt-sol" and model["id"] == "gpt-sol" and j["variant"] == "renamed":
                            labels["c00"] = "allow"
                        text = json.dumps({"decisions": labels})
                        if stage == "final" and j["chain_id"] == "retry--claude-opus" and model["id"] == "claude-opus" and j["variant"] == "renamed" and j["repetition"] == 0:
                            text += " note"
                    return dict(status="ok", text=text, truncated=False, usage={"input_tokens":10,"output_tokens":10})

                with patch.object(run.transport, "complete", fake_complete):
                    run.perform(root, data, stage, True, 160)
                    # Completed output, including invalid JSON, is never silently retried.
                    self.assertEqual(run.perform(root, data, stage, True, 0), 0)
            out = Path(tmp)/"export"
            run.export(root, out)
            exported = storage.read(out/"data.json")
            self.assertEqual(len(exported["records"]), 160)
            report = analyze.analyze(exported)
            self.assertEqual(len(report["stable_drift"]), 1)
            self.assertTrue(report["stable_drift"][0]["matches_simplification"])
            self.assertEqual(len(report["stable_rename_effects"]), 1)
            self.assertEqual(len(report["invalid"]), 1)
            self.assertTrue(all(c["both_initial_visible_pass"] for c in report["chains"]))
            self.assertNotIn("endpoint", exported["models"][0])
            final = exported["plans"]["final"]["jobs"][0]
            hist = storage.read(storage.job_path(root, final))
            hist["attempts"][-1]["status"] = "interrupted"
            storage.write(storage.job_path(root, final), hist)
            with self.assertRaisesRegex(ValueError, "Unfinished transport"):
                run.completed_plan(root, "final")


if __name__ == "__main__":
    unittest.main()
