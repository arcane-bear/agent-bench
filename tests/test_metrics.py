from agent_bench.metrics import Metrics, estimate_cost


def test_metrics_derived_fields():
    m = Metrics(prompt_tokens=100, completion_tokens=200, total_s=2.0)
    assert m.total_tokens == 300
    assert m.tokens_per_sec == 100.0
    d = m.to_dict()
    assert d["total_tokens"] == 300
    assert d["tokens_per_sec"] == 100.0


def test_metrics_zero_duration_is_safe():
    m = Metrics(prompt_tokens=10, completion_tokens=10, total_s=0)
    assert m.tokens_per_sec == 0.0


def test_estimate_cost_known_model():
    # gpt-4o-mini: 0.15 / 0.60 per 1M.
    cost = estimate_cost("openai", "gpt-4o-mini", 1_000_000, 1_000_000)
    assert round(cost, 4) == 0.75


def test_estimate_cost_ollama_is_free():
    assert estimate_cost("ollama", "llama3.2", 10_000, 10_000) == 0.0


def test_estimate_cost_unknown_model_is_zero():
    assert estimate_cost("openai", "nonexistent-model", 100, 100) == 0.0
