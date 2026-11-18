import pytest

from license_pipeline import evaluate
from license_pipeline.generate import generate, write_raw
from license_pipeline.pipeline import run_pipeline


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    raw_dir = tmp_path_factory.mktemp("raw")
    write_raw(generate(), raw_dir)
    return run_pipeline(raw_dir), evaluate.read_ground_truth(raw_dir)


@pytest.mark.parametrize("kind", ["alert", "dq"])
def test_every_rule_recovers_all_injected_cases_with_no_false_alarms(result, kind):
    out, truth = result
    found = out["alert"] if kind == "alert" else out["dq_issue"]
    scores = evaluate.score(found, truth, kind)
    assert not scores.empty
    assert (scores["recall"] == 1.0).all()
    assert (scores["precision"] == 1.0).all()


def test_all_five_alert_rule_families_are_scored(result):
    out, truth = result
    rules = set(evaluate.score(out["alert"], truth, "alert")["rule"])
    assert rules == {
        "renewal_30", "renewal_60", "renewal_90", "installs_over_entitlement",
        "seat_unused_90d", "usage_spike", "price_change_renewal",
    }


def test_pipeline_returns_curated_tables(result):
    out, _ = result
    assert len(out["fact_contract"]) == 120
    assert {"dq_issue", "alert", "fact_inventory", "dim_product"} <= set(out)


def test_evaluate_main_scores_every_scenario(tmp_path):
    from license_pipeline import scenarios

    path = evaluate.main(tmp_path / "work", tmp_path / "reports", seeds=(1,))
    text = path.read_text()
    assert path.name == "eval_report.md"
    for name in scenarios.SCENARIOS:
        assert f"## Scenario: {name}" in text
    assert "Product name matching" in text and "contracts after quarantine" in text
