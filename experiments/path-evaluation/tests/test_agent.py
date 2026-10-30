from agent import run_episode
from onboarding import TOOLS, OnboardingWorld
from prompts import rewrite_user
from rewrite import RewriteWorld

CLEAN = {"id": "c1", "name": "Ana Ruiz", "identity_ok": True, "sanctions_hit": False,
         "amount": 5000, "risk": "low"}


def scripted(script, text=""):
    turns = iter(script)

    def fake(model, system, msgs, tools):
        names = next(turns)
        return {"status": "ok", "text": text, "usage": {"input_tokens": 10, "output_tokens": 5},
                "tool_calls": [{"id": f"c{i}", "name": n, "input": {}} for i, n in enumerate(names)],
                "raw_kind": "test", "raw": None}
    return fake


def test_episode_runs_until_world_is_done():
    w = OnboardingWorld(CLEAN)
    fake = scripted([["verify_identity", "check_sanctions"], ["approve"], ["log_decision"]])
    out = run_episode({}, w, "sys", "user", TOOLS, call=fake)
    assert out["stop"] == "done" and out["calls"] == 4 and w.truth()


def test_episode_stops_on_text_only_reply():
    out = run_episode({}, OnboardingWorld(CLEAN), "sys", "user", TOOLS, call=scripted([[]], text="I stop."))
    assert out["stop"] == "no_tool_call" and out["calls"] == 0


def test_empty_reply_is_retried_not_taken_as_a_stop():
    w = OnboardingWorld(CLEAN)
    fake = scripted([[], [], ["verify_identity", "check_sanctions"], ["approve"], ["log_decision"]])
    out = run_episode({}, w, "sys", "user", TOOLS, call=fake)
    assert out["stop"] == "done" and w.truth()


def test_persistent_empty_reply_ends_as_empty():
    out = run_episode({}, OnboardingWorld(CLEAN), "sys", "user", TOOLS, call=scripted([[]] * 10))
    assert out["stop"] == "empty_reply" and out["empty_retries"] == 3


def test_episode_respects_call_budget():
    out = run_episode({}, OnboardingWorld(CLEAN), "sys", "user", TOOLS,
                      max_calls=3, call=scripted([["get_policy"]] * 10))
    assert out["stop"] == "budget" and out["calls"] == 3


def test_rewrite_user_prompt_states_hypotheses_and_canonical_forms():
    task = {"start": "(x**2 + x)/x", "target": "1 + x", "assumptions": {"x": "positive", "y": "real"}}
    w = RewriteWorld(task["start"], task["target"], task["assumptions"])
    text = rewrite_user(task, w)
    assert "x > 0" in text and "y is real" in text
    assert "(x + x**2)/x" in text and "x + 1" in text
