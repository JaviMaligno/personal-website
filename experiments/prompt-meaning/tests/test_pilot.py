from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import analyze
import bank
import export as exporter
import protocol
import run
import storage
import transport


def response(text, **extra):
    return {"status": "ok", "text": text, "truncated": False, "finish_reason": "stop",
            "usage": {"input_tokens": 10, "output_tokens": 20}, **extra}


class BankTests(unittest.TestCase):
    def test_fixed_bank_and_gold(self):
        b = bank.build_bank()
        self.assertEqual(len(b["tasks"]), 20)
        self.assertEqual(sum(len(t["cases"]) for t in b["tasks"]), 240)
        self.assertEqual(bank.digest(b), bank.digest(bank.build_bank()))
        for task in b["tasks"]:
            self.assertEqual({c["expected"] for c in task["cases"]}, set(bank.ACTIONS))

    def test_boundaries_and_priority_independently(self):
        expense = bank.make_task("expense", 2, "expenses")
        x = {"fraud_confirmed": False, "amount": 150, "receipt": True, "currency_matches": True}
        self.assertEqual(bank.oracle(expense, x), "allow")
        self.assertEqual(bank.oracle(expense, {**x, "amount": 151}), "review")
        self.assertEqual(bank.oracle(expense, {**x, "amount": 600}), "review")
        self.assertEqual(bank.oracle(expense, {**x, "amount": 601, "receipt": False}), "deny")
        retention = bank.make_task("retention", 0, "retention")
        x = dict(legal_hold=False, age_days=30, dependencies=False, approval_required=True, approved=True)
        self.assertEqual(bank.oracle(retention, x), "allow")
        self.assertEqual(bank.oracle(retention, {**x, "age_days": 29}), "deny")
        self.assertEqual(bank.oracle(retention, {**x, "legal_hold": True, "dependencies": True}), "deny")

    def test_input_validation_rejects_coercion_and_extra_fields(self):
        task = bank.build_bank()["tasks"][0]
        x = task["cases"][0]["input"]
        for bad in ({**x, "embargoed": "false"}, {**x, "embargoed": 0}, {**x, "extra": True}):
            with self.assertRaises(ValueError):
                bank.oracle(task, bad)


class ProtocolTests(unittest.TestCase):
    def test_strict_output_no_duplicate_or_missing_ids(self):
        inputs = [{"id": "c01"}, {"id": "c02"}]
        for text in ('{"decisions":{"c01":"allow","c01":"deny","c02":"deny"}}',
                     '{"decisions":{"c01":"allow"}}',
                     '{"decisions":{"c01":"allow","c02":"ALLOW"}}',
                     'Here is JSON: {"decisions":{"c01":"allow","c02":"deny"}}'):
            with self.assertRaises(ValueError):
                protocol.parse_decisions(text, inputs)
        self.assertEqual(protocol.parse_decisions(
            '```json\n{"decisions":{"c01":"allow","c02":"deny"}}\n```', inputs)["c01"], "allow")

    def test_variants_are_exact_and_explicit_comes_from_brief(self):
        task = bank.build_bank()["tasks"][0]
        text = "First use the lattice continuity gate. Then return one action."
        entry = {"term": "lattice continuity gate", "clause": "First use the lattice continuity gate.",
                 "replacement": "orbital texture fence", "rule_ids": ["r1"]}
        v = protocol.variants(text, entry, task)
        self.assertEqual(v["eliminated"], " Then return one action.")
        self.assertEqual(v["explicit"], task["rules"]["r1"] + " Then return one action.")
        self.assertIn("orbital texture fence", v["substituted"])
        with self.assertRaises(ValueError):
            protocol.variants(text + text, entry, task)
        with self.assertRaises(ValueError):
            protocol.variants(text, {**entry, "rule_ids": ["invented-rule"]}, task)

    def test_executor_cannot_see_oracle_or_explanations(self):
        case = bank.controls()[0]
        prompt = protocol.execute_prompt(case, "eliminated", case["task"]["cases"])
        self.assertNotIn('"expected"', prompt)
        self.assertNotIn("Original assignment", prompt)
        self.assertNotIn("Deny if embargoed", prompt)
        self.assertNotIn("control-positive", prompt)


class StorageTests(unittest.TestCase):
    def test_freeze_is_immutable_and_detects_edits(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "frozen.json"
            storage.freeze(path, {"x": 1})
            with self.assertRaises(FileExistsError):
                storage.freeze(path, {"x": 2})
            envelope = storage.read(path)
            envelope["payload"]["x"] = 2
            storage.write(path, envelope)
            with self.assertRaises(ValueError):
                storage.frozen(path)

    def test_crash_leaves_interrupted_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job = {"prompt": "x"}
            def crash(model, prompt):
                raise KeyboardInterrupt()
            with self.assertRaises(KeyboardInterrupt):
                storage.call(root, job, {}, crash)
            self.assertEqual(storage.latest(root, job)["status"], "interrupted")

    def test_single_writer_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            with storage.lock(tmp):
                with self.assertRaises(ValueError):
                    with storage.lock(tmp):
                        pass
            self.assertFalse((Path(tmp) / ".lock").exists())


class TransportTests(unittest.TestCase):
    def model(self, name="openai"):
        return {"id": "m", "model": "fake", "transport": name,
                "endpoint": "https://api.example.test/v1", "key_env": "PILOT_TEST_KEY", "max_tokens": 200}

    def test_native_payload_and_no_silent_temperature(self):
        with patch.dict(os.environ, {"PILOT_TEST_KEY": "secret-for-test"}):
            headers, payload, _ = transport.request_parts(self.model(), "hello")
            self.assertEqual(payload["max_completion_tokens"], 200)
            self.assertNotIn("temperature", payload)
            self.assertEqual(len(payload["messages"]), 1)
            headers, payload, _ = transport.request_parts(self.model("anthropic"), "hello")
            self.assertEqual(payload["max_tokens"], 200)
            self.assertEqual(headers["anthropic-version"], "2023-06-01")

    def test_endpoint_rejects_embedded_secrets_and_redirects(self):
        for endpoint in ("http://example.test", "https://user:secret@example.test", "https://example.test?key=secret"):
            with self.assertRaises(ValueError):
                transport.validate_model({**self.model(), "endpoint": endpoint})
        self.assertIsNone(transport.NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.test"))

    def test_usage_and_truncation_survive_normalization(self):
        r = transport.normalize(self.model(), {"choices": [{"message": {"content": "x"}, "finish_reason": "length"}],
                                                "usage": {"completion_tokens": 200}, "model": "actual-id"})
        self.assertTrue(r["truncated"])
        self.assertEqual(r["usage"]["completion_tokens"], 200)
        r = transport.normalize(self.model("anthropic"), {"content": [{"type": "text", "text": "x"}],
                                                           "stop_reason": "end_turn", "usage": {"input_tokens": 3}})
        self.assertFalse(r["truncated"])

    def test_example_model_cannot_trigger_live_call(self):
        with self.assertRaises(ValueError):
            transport.request_parts({**self.model(), "model": "REPLACE_WITH_MODEL_ID"}, "x")

    def test_existing_file_and_gcloud_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "credential"
            path.write_text("fixture-key\n")
            model = self.model()
            model.pop("key_env")
            model["key_file"] = str(path)
            headers, _, _ = transport.request_parts(model, "x")
            self.assertEqual(headers["Authorization"], "Bearer fixture-key")
        model = self.model("vertex_anthropic")
        model.pop("key_env")
        model.update(auth="gcloud", thinking={"type": "adaptive"}, billing_project="fixture-project")
        with patch("transport.subprocess.run") as command:
            command.return_value.returncode = 0
            command.return_value.stdout = "fixture-token\n"
            headers, body, _ = transport.request_parts(model, "x")
        self.assertEqual(headers["Authorization"], "Bearer fixture-token")
        self.assertEqual(body["anthropic_version"], "vertex-2023-10-16")
        self.assertNotIn("model", body)
        self.assertNotIn("temperature", body)
        self.assertEqual(body["thinking"], {"type": "adaptive"})

    def test_expired_gcloud_does_not_reveal_stderr(self):
        with patch("transport.subprocess.run") as command:
            command.return_value.returncode = 1
            command.return_value.stderr = "private account data"
            with self.assertRaisesRegex(ValueError, "gcloud authentication unavailable"):
                transport.credential({"auth": "gcloud"})

    def test_http_errors_do_not_leak_bodies_or_keys(self):
        import urllib.error
        error = urllib.error.HTTPError("https://example.test", 401, "secret-for-test", {},
                                       io.BytesIO(b"secret-for-test"))
        with patch.dict(os.environ, {"PILOT_TEST_KEY": "secret-for-test"}), \
                patch("urllib.request.OpenerDirector.open", side_effect=error):
            result = transport.complete(self.model(), "hello")
        self.assertEqual(result["error"], "HTTP 401")
        self.assertNotIn("secret-for-test", json.dumps(result))


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        config = storage.read(run.HERE / "config.example.json")
        config["selection_limit"] = 1
        self.config_path = self.root / "config.json"
        storage.write(self.config_path, config)
        run.initialize(self.root, self.config_path)
        self.data = run.manifest(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def generate(self):
        for job in run.generation_jobs(self.data):
            storage.call(self.root, job, {}, lambda m, p: response(
                "Use the lattice continuity gate. Return one action per record."))

    def select(self):
        self.generate()
        run.prepare_review(self.root, self.data)
        review = storage.read(self.root / "review.json")
        review["reviewer"] = "OFFLINE TEST FIXTURE — not empirical review"
        for i, row in enumerate(review["entries"]):
            row.update(decision="eligible" if i == 0 else "excluded", reason="Synthetic lifecycle fixture",
                       term="lattice continuity gate", clause="Use the lattice continuity gate.",
                       replacement="orbital texture fence", rule_ids=["r1"])
        storage.write(self.root / "review.json", review)
        run.freeze_selection(self.root, self.data)
        return run.selection(self.root, self.data)

    def explain(self, selected, invalid_first=False, misleading=False):
        cases = {c["id"]: c for c in selected["cases"]}
        for i, job in enumerate(run.explanation_jobs(selected, self.data)):
            case = cases[job["case_id"]]
            rows = []
            for x in case["task"]["cases"]:
                actions = {slot: (case["expected_by_variant"][v][x["id"]]
                                 if case["kind"] != "natural" else x["expected"])
                           for slot, v in job["slots"].items()}
                if misleading and case["kind"] == "natural" and x["id"] == "c01":
                    actions[next(s for s, v in job["slots"].items() if v == "eliminated")] = "deny"
                rows.append({"case_id": x["id"], "actions": actions})
            probes = []
            if case["kind"] == "natural":
                probes = [{"input": case["task"]["cases"][0]["input"],
                           "actions": {s: "allow" for s in job["slots"]}, "reason": "fixture duplicate"}]
            raw = json.dumps({"meaning": "Synthetic fixture", "evidence": "fixture", "comparison": "fixture",
                              "predictions": rows, "probes": probes})
            if invalid_first and i == 0:
                raw = "not JSON"
            storage.call(self.root, job, {}, lambda m, p, raw=raw: response(raw))
        run.freeze_predictions(self.root, self.data)
        run.prepare_probes(self.root, self.data)
        review = storage.read(self.root / "probe-review.json")
        review["reviewer"] = "OFFLINE TEST FIXTURE"
        for row in review["entries"]:
            row.update(decision="accept", reason="Fixture validates deduplication")
        storage.write(self.root / "probe-review.json", review)
        run.freeze_execution(self.root, self.data)

    def test_dry_run_no_network_and_cap_resume(self):
        calls = []
        def fake(model, prompt):
            calls.append(prompt)
            return response("fixture")
        run.perform(self.root, self.data, "generate", complete=fake)
        self.assertEqual(calls, [])
        run.perform(self.root, self.data, "generate", True, 2, complete=fake)
        self.assertEqual(len(calls), 2)
        run.perform(self.root, self.data, "generate", True, 1, complete=fake)
        self.assertEqual(len(calls), 3)
        self.assertEqual(len(list((self.root / "calls").glob("*.json"))), 3)

    def test_errors_retry_only_explicitly_and_keep_history(self):
        job = run.generation_jobs(self.data)[0]
        storage.call(self.root, job, {}, lambda m, p: {"status": "transport_error", "error": "HTTP 429"})
        summary = run.perform(self.root, self.data, "generate")
        self.assertEqual(summary["pending"], 39)
        summary = run.perform(self.root, self.data, "generate", retry_errors=True)
        self.assertEqual(summary["pending"], 40)
        storage.call(self.root, job, {}, lambda m, p: response("ok"))
        self.assertEqual(len(storage.read(storage.job_path(self.root, job))["attempts"]), 2)

    def test_review_and_execution_cannot_skip_gates(self):
        with self.assertRaises(ValueError):
            run.prepare_review(self.root, self.data)
        with self.assertRaises(FileNotFoundError):
            run.perform(self.root, self.data, "execute")
        self.generate()
        run.prepare_review(self.root, self.data)
        with self.assertRaises(ValueError):
            run.freeze_selection(self.root, self.data)

    def test_source_changes_block_resume(self):
        with patch("run.source_hashes", return_value={"changed": "yes"}):
            with self.assertRaises(ValueError):
                run.manifest(self.root)

    def test_full_offline_lifecycle_cross_predictions_and_controls(self):
        selected = self.select()
        self.explain(selected)
        execution = run.execution(self.root, self.data)
        cases = {c["id"]: c for c in selected["cases"]}
        natural = selected["cases"][0]
        # Duplicate proposed inputs reuse fixed IDs, never inflate the execution batch.
        self.assertEqual(len(execution["inputs"][natural["id"]]), 12)
        for job in execution["jobs"]:
            case = cases[job["case_id"]]
            decisions = (case["expected_by_variant"][job["variant"]] if case["kind"] != "natural"
                         else {x["id"]: x["expected"] for x in execution["inputs"][case["id"]]})
            storage.call(self.root, job, {}, lambda m, p, d=decisions: response(json.dumps({"decisions": d})))
        report = analyze.analyze(self.root)
        self.assertTrue(report["controls_passed"])
        self.assertTrue(report["complete"])
        self.assertEqual(report["status_counts"], {"valid": 16})
        self.assertEqual(report["invalid_explanations"], 0)
        cross = [r for r in report["prediction_comparisons"] if r["explainer"] != r["executor"]]
        self.assertTrue(cross)
        self.assertTrue(all(r["exact_action_pair_matches"] == r["scorable_pairs"] for r in cross))
        out = self.root / "public-export"
        exporter.export(self.root, out)
        published = (out / "data.json").read_text()
        self.assertNotIn("api.openai.com", published)
        self.assertNotIn("key_env", published)
        self.assertIn("OFFLINE TEST FIXTURE", published)
        with self.assertRaises(ValueError):
            run.perform(self.root, self.data, "explain")
        with self.assertRaises(ValueError):
            run.perform(self.root, self.data, "generate")

    def test_invalid_and_truncated_outputs_never_scored_as_valid(self):
        selected = self.select()
        self.explain(selected, invalid_first=True)
        jobs = run.execution(self.root, self.data)["jobs"]
        storage.call(self.root, jobs[0], {}, lambda m, p: response("{}"))
        storage.call(self.root, jobs[1], {}, lambda m, p: response("{}", truncated=True))
        report = analyze.analyze(self.root)
        self.assertEqual(report["status_counts"]["invalid_output"], 1)
        self.assertEqual(report["status_counts"]["truncated"], 1)
        self.assertEqual(report["invalid_explanations"], 1)
        self.assertFalse(report["complete"])
        self.assertFalse(report["controls_passed"])

    def test_invented_effect_is_not_counted_as_a_successful_prediction(self):
        selected = self.select()
        self.explain(selected, misleading=True)
        execution = run.execution(self.root, self.data)
        case = selected["cases"][0]
        for job in execution["jobs"]:
            if job["case_id"] != case["id"]:
                continue
            d = {x["id"]: x["expected"] for x in execution["inputs"][case["id"]]}
            storage.call(self.root, job, {}, lambda m, p, d=d: response(json.dumps({"decisions": d})))
        report = analyze.analyze(self.root)
        rows = [r for r in report["prediction_comparisons"]
                if r["kind"] == "natural" and r["variant"] == "eliminated" and r["source"] == "fixed"]
        self.assertEqual(len(rows), 4)  # Both explainers crossed with both executors.
        for r in rows:
            self.assertEqual(r["predicted_changes"], 1)
            self.assertEqual(r["observed_changes"], 0)
            self.assertEqual(r["predicted_change_realized_exactly"], 0)
            self.assertEqual(r["exact_action_pair_matches"], 11)
            self.assertEqual(r["always_no_change_baseline_matches"], 12)

    def test_review_cannot_be_reordered_after_generation(self):
        self.generate()
        run.prepare_review(self.root, self.data)
        review = storage.read(self.root / "review.json")
        review["reviewer"] = "FIXTURE"
        review["entries"].reverse()
        storage.write(self.root / "review.json", review)
        with self.assertRaises(ValueError):
            run.freeze_selection(self.root, self.data)


if __name__ == "__main__":
    with contextlib.redirect_stdout(io.StringIO()):
        unittest.main()
