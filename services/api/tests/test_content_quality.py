from __future__ import annotations

from app.services.learning import default_scenarios, scenario_scripts


def test_scenario_catalog_quality_guardrails() -> None:
    scenarios = default_scenarios()
    ids = [item.id for item in scenarios]
    assert len(scenarios) >= 20
    assert len(ids) == len(set(ids))
    assert any("job" in sid for sid in ids)
    assert any("travel" in sid for sid in ids)
    assert any("relocation" in sid for sid in ids)


def test_scenario_scripts_minimum_quality() -> None:
    scripts = scenario_scripts()
    for scenario_id, steps in scripts.items():
        assert len(steps) >= 3, f"{scenario_id} has too few steps"
        for step in steps:
            assert len(step.expected_keywords) >= 2
            assert step.tip.strip() != ""
