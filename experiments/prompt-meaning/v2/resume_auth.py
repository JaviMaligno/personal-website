"""Resume after local gcloud timeouts; keep the existing session token in memory only.

No prompts, model parameters, endpoints or frozen measurement sources change.
The only override is how often the same existing gcloud login is queried.
Never prints or persists the returned access token.
"""
import argparse
from pathlib import Path
import subprocess

import bank
import run
import storage
import transport


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, type=Path)
    parser.add_argument("--max-calls", required=True, type=int)
    args = parser.parse_args()
    with storage.lock(args.run):
        data = run.manifest(args.run)
        print("Obtaining existing gcloud session credential once; keeping it in process memory only.", flush=True)
        proc = subprocess.run(["gcloud", "auth", "print-access-token"],
                              capture_output=True, text=True, timeout=120)
        if proc.returncode or not proc.stdout.strip():
            raise ValueError("Existing gcloud session credential unavailable")
        token = proc.stdout.strip()
        del proc
        original = transport.credential

        def credential(model):
            return token if model.get("auth") == "gcloud" else original(model)

        transport.credential = credential
        interrupted = []
        for job in run.execution(args.run, data)["jobs"]:
            previous = storage.latest(args.run, job)
            if previous and previous["status"] in {"interrupted", "transport_error"}:
                interrupted.append(bank.digest(job))
        storage.freeze(args.run / "auth-recovery.json", {
            "started": storage.now(), "reason": "Local gcloud credential subprocess exceeded 45 seconds",
            "operation": "Same existing session credential obtained once and retained in process memory only",
            "interrupted_jobs": interrupted, "prompt_model_or_endpoint_changes": False,
            "launcher_sha256": bank.digest(Path(__file__).read_text())})
        run.perform(args.run, data, "execute", live=True, max_calls=args.max_calls, retry_errors=True)


if __name__ == "__main__":
    main()
