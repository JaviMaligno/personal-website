"""Offline measurement checks. All model responses in this file are synthetic fixtures."""
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import analyze
import bank
import export
import protocol
import run
import storage
import transport
import resume_auth


def answer(text):
    return {"status": "ok", "text": text, "truncated": False,
            "usage": {"input_tokens": 1, "output_tokens": 1}, "latency_s": 0}


class V2Tests(unittest.TestCase):
    def test_auth_recovery_keeps_token_only_in_memory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            secret = "SYNTHETIC_TEST_TOKEN_NOT_A_REAL_CREDENTIAL"
            def check_perform(*args, **kwargs):
                self.assertEqual(transport.credential({"auth": "gcloud"}), secret)
                self.assertEqual(transport.credential({"auth": "gcloud"}), secret)
                self.assertTrue(kwargs["retry_errors"])
            with patch("sys.argv", ["resume_auth.py", "--run", str(root), "--max-calls", "1"]), \
                 patch.object(resume_auth.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout=secret)) as auth, \
                 patch.object(run, "manifest", return_value={}), \
                 patch.object(run, "execution", return_value={"jobs": []}), \
                 patch.object(run, "perform", side_effect=check_perform), \
                 patch.object(transport, "credential", return_value="unused"):
                resume_auth.main()
                auth.assert_called_once()
            self.assertTrue((root / "auth-recovery.json").exists())
            self.assertTrue(all(secret not in p.read_text() for p in root.rglob('*') if p.is_file()))

    def test_synthetic_interventions_and_oracles(self):
        tasks = bank.build_bank()["tasks"]
        self.assertEqual(len(tasks), 4)
        for case in bank.synthetic_cases(tasks):
            v = case["variants"]
            self.assertEqual(v["original"].replace(case["clause"] + "\n", "", 1), v["eliminated"])
            self.assertNotEqual(case["benchmark_expected"]["explicit"],
                                case["benchmark_expected"]["eliminated"])
            self.assertNotIn(case["task"]["rules"][case["omitted_rule"]], v["original"])
            self.assertIn(case["task"]["rules"][case["omitted_rule"]], v["explicit"])
        access = tasks[0]
        x = dict(embargoed=False, consent=True, external=False, confidential=False, owner_approved=False)
        self.assertEqual(bank.oracle(access, x), "review")
        self.assertEqual(bank.partial_oracle(access, x), "allow")

    def test_explainer_does_not_receive_missing_definition(self):
        for case in bank.synthetic_cases(bank.build_bank()["tasks"]):
            slots = protocol.slots(case, "a")
            self.assertNotIn("explicit", slots.values())
            text = protocol.explain_prompt(case, slots)
            self.assertNotIn(case["task"]["rules"][case["omitted_rule"]], text)
            self.assertNotIn("Original assignment", text)
            self.assertNotIn('"expected"', text)
            self.assertIn("undetermined", text)

    def test_full_frozen_lifecycle_and_export(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "run"
            config = Path(temp) / "config.json"
            models = [{"id": mid, "model": mid, "transport": "openai",
                       "endpoint": "https://private.invalid/v1/chat/completions",
                       "key_file": "~/.private-fixture-key", "max_tokens": 8192}
                      for mid in ("a", "b")]
            storage.write(config, {"models": models, "selection_limit": 4, "repetitions": 2})
            run.initialize(root, config)
            data = run.manifest(root)
            with self.assertRaises(ValueError):
                run.generation_jobs(data, root, "revise")
            for stage in ("draft", "revise", "generate"):
                for job in run.generation_jobs(data, root, stage):
                    if stage == "revise":
                        self.assertIn("fixture draft", job["prompt"])
                    if stage == "generate":
                        self.assertIn("fixture revise", job["prompt"])
                    storage.call(root, job, {}, lambda m, p: answer("fixture " + stage))
            run.prepare_review(root, data)
            review = storage.read(root / "review.json")
            review["reviewer"] = "synthetic test fixture"
            for entry in review["entries"]:
                entry.update(decision="excluded", reason="synthetic fixture")
            storage.write(root / "review.json", review)
            run.freeze_selection(root, data)
            selected = run.selection(root, data)
            cases = {c["id"]: c for c in selected["cases"]}
            self.assertEqual(len(cases), 18)
            explanation_jobs = run.explanation_jobs(selected, data)
            self.assertEqual(len(explanation_jobs), 20)
            for job in explanation_jobs:
                case = cases[job["case_id"]]
                rows = []
                for x in case["task"]["cases"]:
                    actions = {slot: case.get("expected_by_variant", {}).get(variant,
                        case.get("benchmark_expected", {}).get(variant,
                        {q["id"]: q["expected"] for q in case["task"]["cases"]}))[x["id"]]
                        for slot, variant in job["slots"].items()}
                    rows.append({"case_id": x["id"], "actions": actions})
                text = json.dumps({"meaning": "fixture", "evidence": "fixture",
                    "comparison": "fixture", "predictions": rows, "probes": []})
                storage.call(root, job, {}, lambda m, p: answer(text))
            run.freeze_predictions(root, data)
            run.prepare_probes(root, data)
            storage.write(root / "probe-review.json", {"reviewer": "fixture", "entries": []})
            run.freeze_execution(root, data)
            jobs = run.execution(root, data)["jobs"]
            self.assertEqual(len(jobs), 176)
            for job in jobs:
                case = cases[job["case_id"]]
                decisions = dict(case.get("expected_by_variant", {}).get(job["variant"],
                    case.get("benchmark_expected", {}).get(job["variant"],
                    {x["id"]: x["expected"] for x in case["task"]["cases"]})))
                # Inject one unstable synthetic action to check repetition diagnostics.
                if job["case_id"] == "synthetic-access-opaque" and job["variant"] == "original" and job["repetition"] == 1 and job["model_id"] == "a":
                    decisions["c01"] = "deny"
                storage.call(root, job, {}, lambda m, p: answer(json.dumps({"decisions": decisions})))
            report = analyze.analyze(root)
            self.assertTrue(report["controls_passed"])
            self.assertTrue(report["policy_benchmarks_passed"])
            self.assertEqual(report["status_counts"], {"valid": 176})
            self.assertTrue(any(c.get("unstable_inputs", 0) for c in report["prediction_comparisons"]))
            self.assertEqual(report["unmodified_prompts"], 8)
            out = Path(temp) / "export"
            export.export(root, out)
            public = (out / "data.json").read_text()
            self.assertNotIn("private.invalid", public)
            self.assertNotIn(".private-fixture-key", public)
            self.assertEqual(len(json.loads(public)["records"]), 220)


if __name__ == "__main__":
    unittest.main()
