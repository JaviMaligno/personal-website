"""Frozen, resumable four-stage runner. --live is required for all network calls."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path

import bank
import protocol
import storage
import transport

HERE = Path(__file__).resolve().parent
STAGES = ("source", "visible", "handoff", "final")
MEASUREMENT = ("bank.py", "protocol.py", "run.py", "storage.py", "transport.py", "DESIGN.md")


def sources():
    return {name: bank.digest((HERE / name).read_text()) for name in MEASUREMENT}


def init(root, config_path):
    config = storage.read(config_path)
    models = config["models"]
    assert {m["id"] for m in models} == {"gpt-sol", "claude-opus"} and len(models) == 2
    for m in models:
        transport.validate_model(m)
        assert m["max_tokens"] == 8192
    storage.freeze(root / "manifest.json", dict(created=storage.now(), sources=sources(),
        config={"models": models, "repetitions": 2}, tasks=bank.build_bank()))
    print("Frozen four policies, 80 input records, source hashes and model settings.")


def manifest(root):
    data = storage.frozen(root / "manifest.json")
    if data["sources"] != sources():
        raise ValueError("Measurement source changed since freeze; do not reuse this run")
    return data


def chains(data):
    for task in data["tasks"]:
        for writer in ["gpt-sol", "claude-opus"]:
            yield {"id": task["id"] + "--" + writer, "task": task,
                   "writer": writer,
                   "receiver": "claude-opus" if writer == "gpt-sol" else "gpt-sol"}


def job(stage, chain, model, prompt, **extra):
    return dict(stage=stage, chain_id=chain["id"], task_id=chain["task"]["id"],
                model_id=model, prompt=prompt, **extra)


def parsed_artifact(root, jobs, cid):
    entries = [j for j in jobs if j["chain_id"] == cid]
    if not entries:
        return None
    response = storage.latest(root, entries[0])
    if not response or response["status"] != "ok" or response.get("truncated"):
        return None
    try:
        return protocol.guide(response["text"])
    except (ValueError, TypeError, KeyError):
        return None


def completed_plan(root, stage):
    plan = storage.frozen(root / (stage + ".json"))
    for j in plan["jobs"]:
        response = storage.latest(root, j)
        if not response or response["status"] in ("interrupted", "transport_error"):
            raise ValueError("Unfinished transport attempt in prerequisite stage " + stage)
    return plan


def build_plan(root, data, stage):
    jobs, artifacts = [], {}
    models = [m["id"] for m in data["config"]["models"]]
    src = completed_plan(root, "source") if stage != "source" else None
    vis = completed_plan(root, "visible") if stage in ("handoff", "final") else None
    handed = completed_plan(root, "handoff") if stage == "final" else None
    for chain in chains(data):
        task, cid = chain["task"], chain["id"]
        if stage == "source":
            jobs.append(job(stage, chain, chain["writer"], protocol.source_prompt(task)))
            continue
        original = parsed_artifact(root, src["jobs"], cid)
        artifacts[cid] = {"source": original}
        if stage == "visible" and original:
            cases = [c for c in task["cases"] if c["visible"]]
            for model in models:
                jobs.append(job(stage, chain, model, protocol.execution_prompt(
                    task, original["guide"], cases, [cid, "visible"])))
        elif stage == "handoff" and original:
            feedback = []
            for j in vis["jobs"]:
                if j["chain_id"] != cid:
                    continue
                r = storage.latest(root, j)
                feedback.append({"executor": j["model_id"], "status": r["status"],
                                 "response": r.get("text", ""), "truncated": r.get("truncated", False)})
            jobs.append(job(stage, chain, chain["receiver"],
                            protocol.handoff_prompt(task, original, feedback)))
        elif stage == "final":
            received = parsed_artifact(root, handed["jobs"], cid)
            artifacts[cid]["received"] = received
            variants = {"canonical": task["rules"]}
            if original:
                variants["source"] = original["guide"]
            if received:
                variants["received"] = received["guide"]
                renamed, count = protocol.rename(received)
                artifacts[cid]["rename_occurrences"] = count
                artifacts[cid]["name_retained"] = received["term"] == original["term"]
                if renamed is not None:
                    variants["renamed"] = renamed
            for variant, instructions in variants.items():
                for model in models:
                    for rep in range(2):
                        prompt = protocol.execution_prompt(task, instructions, task["cases"], [cid, rep])
                        jobs.append(job(stage, chain, model, prompt, variant=variant, repetition=rep))
    jobs.sort(key=lambda j: bank.digest(["order-v3", j]))
    return dict(stage=stage, frozen=storage.now(), artifacts=artifacts, jobs=jobs)


def plan(root, data, stage):
    path = root / (stage + ".json")
    if not path.exists():
        storage.freeze(path, build_plan(root, data, stage))
    return storage.frozen(path)


def credentials_in_memory(models):
    original = transport.credential
    cached = {}
    for model in models:
        cached[model["id"]] = original(model)
    transport.credential = lambda model: cached[model["id"]]


def perform(root, data, stage, live, cap, retry_transport=False):
    p = plan(root, data, stage)
    pending = []
    for j in p["jobs"]:
        r = storage.latest(root, j)
        if r is None or (retry_transport and r["status"] in ("interrupted", "transport_error")):
            pending.append(j)
    print(f"{stage}: {len(p['jobs'])} planned, {len(pending)} pending", flush=True)
    if not live:
        return 0
    if len(pending) > cap:
        raise ValueError("Remaining authorised call cap is smaller than this stage")
    models = {m["id"]: m for m in data["config"]["models"]}

    def complete(model, prompt):
        try:
            return transport.complete(model, prompt)
        except Exception as exc:
            # Do not expose exception arguments which may include private routes.
            return {"status": "transport_error", "error": type(exc).__name__}

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {pool.submit(storage.call, root, j, models[j["model_id"]], complete): j for j in pending}
        for i, future in enumerate(as_completed(futures), 1):
            r = future.result()
            j = futures[future]
            print(f"{stage} {i}/{len(pending)} {j['chain_id']} {j['model_id']} "
                  f"{j.get('variant', '')} {r['status']}", flush=True)
    completed_plan(root, stage)
    return len(pending)


def export(root, out):
    data = manifest(root)
    plans = {s: completed_plan(root, s) for s in STAGES}
    fields = {"status", "started", "finished", "attempt", "text", "truncated", "finish_reason",
              "usage", "latency_s", "error"}
    records = []
    for p in plans.values():
        for j in p["jobs"]:
            history = storage.read(storage.job_path(root, j))
            records.append({"job": j, "original_sha256": bank.digest(history),
                "attempts": [{k: v for k, v in a.items() if k in fields} for a in history["attempts"]]})
    public_fields = {"id", "transport", "max_tokens", "temperature", "thinking"}
    payload = {"notice": "Public export; private routes, credentials, provider envelopes and IDs omitted.",
        "created": data["created"], "sources": data["sources"], "tasks": data["tasks"],
        "models": [{k: v for k, v in m.items() if k in public_fields} for m in data["config"]["models"]],
        "plans": plans, "records": records}
    encoded = json.dumps(payload)
    for model in data["config"]["models"]:
        for k in ("endpoint", "billing_project", "key_file", "model"):
            if model.get(k) and model[k] in encoded:
                raise ValueError("Private routing value in export; inspect locally")
    storage.write(out / "data.json", payload, exclusive=True)
    print(f"Exported {len(records)} public call histories.")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["init", "all", "export", *STAGES])
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--config", type=Path)
    p.add_argument("--out", type=Path)
    p.add_argument("--live", action="store_true")
    p.add_argument("--max-calls", type=int, default=0)
    p.add_argument("--retry-transport", action="store_true")
    args = p.parse_args()
    with storage.lock(args.run):
        if args.command == "init":
            if not args.config:
                p.error("--config required")
            init(args.run, args.config)
        elif args.command == "export":
            if not args.out:
                p.error("--out required")
            export(args.run, args.out)
        else:
            data = manifest(args.run)
            if args.live:
                if args.max_calls <= 0:
                    p.error("--max-calls required for live execution")
                print("Obtaining existing credentials serially; tokens remain in process memory only.", flush=True)
                credentials_in_memory(data["config"]["models"])
            remaining = args.max_calls
            for stage in STAGES if args.command == "all" else [args.command]:
                remaining -= perform(args.run, data, stage, args.live, remaining, args.retry_transport)
                if not args.live:
                    break


if __name__ == "__main__":
    main()
