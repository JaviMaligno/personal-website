from wheresball.baselines import default_baselines
from wheresball.dataset import generate_items
from wheresball.harness import (
    BaselineSystem,
    MockVLMClient,
    ResponseCache,
    evaluate,
    run_matrix,
)
from wheresball.schema import Condition, Knowledge, Masking, TemporalContext

CONDITIONS = [
    Condition(TemporalContext.SINGLE_FRAME, Knowledge.NEUTRAL, Masking.NATURAL),
    Condition(TemporalContext.MULTI_FRAME, Knowledge.INFORMED, Masking.NATURAL),
]


def test_cache_roundtrip(tmp_path):
    cache = ResponseCache(tmp_path / "cache")
    item = generate_items(4, seed=0)[0]
    condition = CONDITIONS[0]
    client = MockVLMClient(seed=0)
    pred = client.predict(item, condition, "prompt")
    assert cache.get(client.model_id, item.item_id, condition, "v1") is None
    cache.put(client.model_id, item.item_id, condition, "v1", pred)
    assert cache.get(client.model_id, item.item_id, condition, "v1") == pred
    # Different prompt version → cache miss.
    assert cache.get(client.model_id, item.item_id, condition, "v2") is None
    assert len(cache) == 1


def test_run_matrix_uses_cache(tmp_path):
    items = generate_items(6, seed=1)
    cache = ResponseCache(tmp_path / "cache")
    systems = [MockVLMClient(seed=1)]
    rows1 = run_matrix(items, systems, CONDITIONS, cache=cache)
    rows2 = run_matrix(items, systems, CONDITIONS, cache=cache)
    assert rows1 == rows2
    assert len(rows1) == len(items) * len(CONDITIONS)
    assert len(cache) == len(rows1)


def test_end_to_end_report_structure():
    items = generate_items(40, seed=2)
    systems = [BaselineSystem(b) for b in default_baselines()] + [MockVLMClient(seed=2)]
    rows = run_matrix(items, systems, CONDITIONS[:1])
    report = evaluate(rows, items, bootstrap_replicates=200)

    assert set(report["systems"]) == {s.model_id for s in systems}
    condition_key = CONDITIONS[0].key
    for per_condition in report["systems"].values():
        entry = per_condition[condition_key]
        assert entry["error"]["n"] == len(items)
        lo, hi = entry["error_median_ci95"]
        assert lo <= entry["error"]["median"] <= hi
        assert set(entry["pck"]) == {0.02, 0.05, 0.10}
        assert "possession" in entry["by_stratum"]
    # Pairwise comparisons cover all system pairs.
    n = len(systems)
    assert len(report["comparisons"][condition_key]) == n * (n - 1) // 2


def test_informative_geometry_beats_random():
    """On synthetic data the player-based baselines must beat pure chance —
    the sanity check that the whole pipeline measures what it should."""
    items = generate_items(80, seed=3)
    systems = [BaselineSystem(b) for b in default_baselines()]
    rows = run_matrix(items, systems, CONDITIONS[:1])
    report = evaluate(rows, items, bootstrap_replicates=200)
    condition_key = CONDITIONS[0].key
    medians = {
        system: per_condition[condition_key]["error"]["median"]
        for system, per_condition in report["systems"].items()
    }
    assert medians["B1_centroid"] < medians["B0_random"]
    assert medians["B2_velocity_centroid"] < medians["B0_random"]
