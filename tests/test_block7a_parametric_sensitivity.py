from gli.audit_block7a_parametric import (
    SensitivityScenario,
    audit_sensitivity_scenario,
    run_block7a_local_sensitivity,
)


def test_block7a_keeps_commercial_domain_uncertified():
    audit = run_block7a_local_sensitivity(scenarios=(), max_step_s=1.0)

    assert audit.commercial_domain_certified is False
    assert "No define todavía un dominio comercial validado" in audit.statement
    assert audit.results[0].scenario_id == "santos_reference"
    assert audit.results[0].status == "certified_reference"
    assert audit.results[0].failed_contracts == ()


def test_small_pressure_and_slug_perturbations_close_a_to_f_contracts():
    scenarios = (
        SensitivityScenario(
            "injection_pressure_minus_5pct",
            "injectionPressure",
            "Presión de inyección -5%",
            multiplier=0.95,
        ),
        SensitivityScenario(
            "injection_pressure_plus_5pct",
            "injectionPressure",
            "Presión de inyección +5%",
            multiplier=1.05,
        ),
        SensitivityScenario(
            "slug_length_minus_5pct",
            "slugLength",
            "Longitud de golfada -5%",
            multiplier=0.95,
        ),
        SensitivityScenario(
            "slug_length_plus_5pct",
            "slugLength",
            "Longitud de golfada +5%",
            multiplier=1.05,
        ),
    )

    audit = run_block7a_local_sensitivity(scenarios=scenarios, max_step_s=1.0)

    assert audit.failed_scenarios == ()
    assert set(audit.observed_stable_scenarios) == {s.scenario_id for s in scenarios}
    assert audit.max_residual_normalized < 1e-8
    for result in audit.results[1:]:
        assert result.status == "local_stability_observed"
        assert result.validation_level_candidate == "certified"
        assert result.terminal_event == "F_FILM_VELOCITY_ZERO"
        assert result.failed_contracts == ()
        assert result.event_times_s["F_FILM_VELOCITY_ZERO"] > result.event_times_s["E_SLUG_BASE_REACHED_SURFACE"]
        assert "no certificación comercial global" in result.interpretation


def test_single_axis_result_records_tested_value_and_relative_change():
    result = audit_sensitivity_scenario(
        SensitivityScenario(
            "api_plus_2deg",
            "api",
            "API +2 grados",
            absolute_delta=2.0,
        ),
        max_step_s=1.0,
    )

    assert result.base_value == 40.0
    assert result.tested_value == 42.0
    assert result.relative_change_percent == 5.0
    assert result.status == "local_stability_observed"
    assert result.max_residual_normalized < 1e-8
