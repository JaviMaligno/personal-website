"""Standalone handoffs and fresh executions, without explanation scoring."""
import json
import random
import re
from bank import digest


def strict_json(text):
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ValueError("Duplicate key")
            result[k] = v
        return result
    text = text.strip()
    if text.startswith("```json\n") and text.endswith("\n```"):
        text = text[8:-4]
    return json.loads(text, object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Invalid constant")))


def guide(text):
    d = strict_json(text)
    if not isinstance(d, dict) or set(d) != {"term", "guide"}:
        raise ValueError("Expected term and guide")
    if any(not isinstance(v, str) or not v.strip() for v in d.values()):
        raise ValueError("Empty term/guide")
    return d


def decisions(text, cases):
    d = strict_json(text)
    if not isinstance(d, dict) or set(d) != {"decisions"} or not isinstance(d["decisions"], dict):
        raise ValueError("Invalid decision object")
    rows = d["decisions"]
    if set(rows) != {c["id"] for c in cases} or any(v not in ("allow", "deny", "review") for v in rows.values()):
        raise ValueError("Missing/extra IDs or invalid labels")
    return rows


def visible(task):
    return [{"id": c["id"], "input": c["input"], "expected": c["expected"]}
            for c in task["cases"] if c["visible"]]


def source_prompt(task):
    return ("Design a standalone decision guide for another agent. This is a simulation; "
        "take no external actions. Choose one concise local name for the operative concept, "
        "and use that exact name in the guide with enough definition to apply the policy. "
        "The name is being introduced here; do not claim it is industry terminology. "
        "Preserve every condition, exception and precedence. Do not add requirements. "
        "The examples are not exhaustive. Requested guide length: at most 180 words.\n"
        f"Task: {task['context']}\nPolicy: {task['rules']}\nSchema: {json.dumps(task['schema'])}\n"
        f"Existing examples: {json.dumps(visible(task))}\n"
        'Return only {"term":"local name", "guide":"standalone instructions"}.')


def handoff_prompt(task, original, feedback):
    return ("Prepare the next agent's standalone decision guide from the current guide and "
        "the available test report. This is a simulation; take no external actions. "
        "Keep the local name and preserve the policy's conditions, exceptions and precedence. "
        "Do not infer that the examples exhaust the policy. The next agent will only see "
        "your guide, the schema and new records, not this discussion or report. "
        "Requested guide length: at most 80 words.\n"
        f"Task: {task['context']}\nSchema: {json.dumps(task['schema'])}\n"
        f"Current named guide: {json.dumps(original)}\n"
        f"Existing examples with expected labels: {json.dumps(visible(task))}\n"
        f"Observed decisions on those examples: {json.dumps(feedback)}\n"
        'Return only {"term":"local name", "guide":"standalone instructions"}.')


def rename(artifact):
    text, count = re.subn(re.escape(artifact["term"]), "velun protocol", artifact["guide"], flags=re.I)
    if not count or artifact["term"].casefold() == "velun protocol":
        return None, count
    return text, count


def execution_prompt(task, instructions, cases, seed):
    order = list(cases)
    random.Random(digest(seed)).shuffle(order)
    return ("Apply the following agent instructions to independent records. Actions are labels "
        "only; take no external actions.\n"
        f"Instructions: {instructions}\nSchema: {json.dumps(task['schema'])}\n"
        f"Records: {json.dumps([{'id': c['id'], 'input': c['input']} for c in order])}\n"
        'Return only {"decisions":{"id":"action",...}} with every record ID exactly once. '
        "Actions: allow, deny, review. No additional prose.")
