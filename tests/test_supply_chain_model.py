import supply_chain_model as scm


def test_eta_minutes():
    assert scm.eta_minutes(30, 60, 0) == 30.0


def test_expected_wait():
    assert scm.expected_wait(20) == 10


def test_occupancy_caps_at_100():
    assert scm.occupancy_percentage(20, 15) == 100.0


def test_confidence_unverified_when_few_reports():
    assert scm.confidence_score(1, 0) <= 0.5


def test_confidence_verified():
    assert scm.confidence_score(4, 3) > 0.5


def test_forecast_demand_uses_history():
    forecast = scm.forecast_demand([100, 200])
    assert forecast > 100


def test_demand_level_very_high_when_no_taxis():
    assert scm.demand_level(float("inf")) == "Very high"


def test_deploy_sends_taxis_to_biggest_shortfall():
    plan = scm.deploy_taxis({"A": (100, 0), "B": (10, 1)}, 1)
    assert plan["A"] == 1
    assert plan["B"] == 0


def test_no_taxis_and_nobody_waiting_is_not_demand():
    assert scm.demand_intensity(0, 0) == 0.0
    assert scm.demand_level(scm.demand_intensity(0, 0)) == "Low"


def test_people_waiting_with_no_taxis_is_very_high():
    assert scm.demand_level(scm.demand_intensity(20, 0)) == "Very high"


def test_heat_map_entry_is_json_safe():
    assert scm.heat_map_entry(20, 0) == (None, "Very high")
    assert scm.heat_map_entry(15, 1) == (1.0, "Moderate")
