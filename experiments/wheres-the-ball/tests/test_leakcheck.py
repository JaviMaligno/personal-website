from wheresball.harness.leakcheck import parse_leak_verdict, run_leak_check


class FakeChecker:
    model_id = "fake-checker"

    def __init__(self, replies):
        self.replies = list(replies)

    def complete(self, prompt, images):
        assert "JSON" in prompt
        assert len(images) == 1
        return self.replies.pop(0)


CLEAN = '{"ball_visible": false, "artifact_visible": false, "explanation": "nothing odd"}'
BALL = '{"ball_visible": true, "artifact_visible": false, "explanation": "ball at midfield"}'
ARTIFACT = '{"ball_visible": false, "artifact_visible": true, "explanation": "smudge"}'


def test_verdict_parsing_and_leak_property():
    assert not parse_leak_verdict("a", CLEAN).leaked
    assert parse_leak_verdict("b", BALL).leaked
    assert parse_leak_verdict("c", ARTIFACT).leaked


def test_unparseable_counts_as_leaked():
    verdict = parse_leak_verdict("d", "I think I see something?")
    assert verdict.leaked
    verdict = parse_leak_verdict("e", '{"ball_visible": true}')  # missing field
    assert verdict.leaked


def test_run_leak_check_discard_rate_and_clean_ids():
    checker = FakeChecker([CLEAN, BALL, ARTIFACT, CLEAN])
    report = run_leak_check(
        [("i1", b"png"), ("i2", b"png"), ("i3", b"png"), ("i4", b"png")], checker
    )
    assert report.discard_rate == 0.5
    assert report.clean_ids() == ["i1", "i4"]
