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
    assert audit.results[0].status == "failed"
    assert audit.results[0].failed_contracts == (
        "stage42_e_source_compatibility",
        "ef_certified",
    )


def test_sensitivity_stops_when_reference_source_gate_is_not_certified():
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

    assert audit.failed_scenarios == ("santos_reference",)
    assert audit.observed_stable_scenarios == ()
    assert audit.max_residual_normalized == 1.0
    assert len(audit.results) == 1
    assert audit.results[0].terminal_event == "E_SLUG_BASE_REACHED_SURFACE"


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
    assert result.status == "failed"
    assert result.validation_level_candidate == "provisional"
    assert result.failed_contracts == ("stage42_e_source_compatibility", "ef_certified")
