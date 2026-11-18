from datetime import date, timedelta

import pytest

from license_pipeline import config, scenarios
from license_pipeline.generate import generate_clean


def test_registry_has_baseline_and_scale():
    assert {"baseline", "scale"} <= set(scenarios.SCENARIOS)


def test_get_scenario_by_name_and_unknown_name():
    assert scenarios.get_scenario("scale").name == "scale"
    with pytest.raises(ValueError, match="unknown scenario"):
        scenarios.get_scenario("nope")


def test_pick_is_deterministic_for_a_date():
    day = date(2026, 11, 19)
    assert scenarios.pick_scenario(day) == scenarios.pick_scenario(day)


def test_pick_covers_every_scenario_over_a_year():
    days = [date(2026, 1, 1) + timedelta(days=i) for i in range(365)]
    seen = {scenarios.pick_scenario(d).name for d in days}
    assert seen == set(scenarios.SCENARIOS)


def test_baseline_matches_the_original_config():
    base = scenarios.get_scenario("baseline")
    assert (base.n_contracts, base.n_usage_seats, base.n_inject) == (
        config.N_CONTRACTS, config.N_USAGE_SEATS, config.INJECT_PER_RULE,
    )


def test_scale_scenario_generates_much_more_data_with_exact_truth_counts():
    scale = scenarios.get_scenario("scale")
    clean = generate_clean(scenario=scale)
    assert len(clean["contracts"]) == scale.n_contracts + 4 * scale.n_inject
    assert len(clean["usage"]) == scale.n_usage_seats
    assert len(clean["ai_seats"]) == scale.n_ai_seats
    truth = clean["ground_truth"]
    for rule in ("renewal_30", "usage_spike", "installs_over_entitlement", "duplicate"):
        assert (truth["rule"] == rule).sum() == scale.n_inject


def test_seed_changes_the_data():
    a = generate_clean(seed=1)["contracts"]["seats_purchased"].tolist()
    b = generate_clean(seed=2)["contracts"]["seats_purchased"].tolist()
    assert a != b
