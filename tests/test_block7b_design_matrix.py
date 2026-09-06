from gli.audit_block7b_design_matrix import (
    MatrixScenario,
    default_design_matrix,
    default_parameter_bands,
    run_block7b_design_matrix,
)


def test_default_design_matrix_contains_base_bounds_and_selected_corners():
    scenarios = default_design_matrix()
    ids = {s.scenario_id for s in scenarios}

    assert "santos_reference" in ids
    assert "injectionPressure_low" in ids
    assert "injectionPressure_high" in ids
    assert "slugLength_low" in ids
    assert "slugLength_high" in ids
    assert "injectionPressure_low__slugLength_low" in ids
    assert "valveDepth_high__tubingDiameter_high" in ids
    assert "bsw_low__api_high" in ids
    assert len(scenarios) == 29


def test_parameter_bands_are_local_and_traceable():
    bands = {band.field: band for band in default_parameter_bands()}

    assert bands["injectionPressure"].low_value == bands["injectionPressure"].base_value * 0.95
    assert bands["injectionPressure"].high_value == bands["injectionPressure"].base_value * 1.05
    assert bands["tubingDiameter"].low_value == bands["tubingDiameter"].base_value * 0.98
    assert bands["tubingDiameter"].high_value == bands["tubingDiameter"].base_value * 1.02
    assert bands["bsw"].low_value == 45.0
    assert bands["bsw"].high_value == 55.0
    assert "Bloque 7A" in bands["api"].basis


def test_design_matrix_stops_when_reference_source_gate_fails():
    scenarios = (
        MatrixScenario("santos_reference", "Caso base", {}),
        MatrixScenario("pressure_slug_low_corner", "Presión y golfada bajas", {
            "injectionPressure": 6.966 * 0.95,
            "slugLength": 412.5 * 0.95,
        }),
        MatrixScenario("pressure_slug_high_corner", "Presión y golfada altas", {
            "injectionPressure": 6.966 * 1.05,
            "slugLength": 412.5 * 1.05,
        }),
    )

    audit = run_block7b_design_matrix(scenarios=scenarios, max_step_s=1.0)

    assert audit.commercial_domain_certified is False
    assert audit.validated_range_candidate is False
    assert audit.failed_scenarios == (
        "santos_reference",
        "pressure_slug_low_corner",
        "pressure_slug_high_corner",
    )
    assert audit.provisional_scenarios == ()
    assert audit.scenario_count == 3
    assert audit.max_residual_normalized == 1.0
    assert all(result.status == "failed" for result in audit.results)
    assert all(
        result.failed_contracts == ("de_event_e", "de_source_certification", "physical_f_state_unavailable")
        for result in audit.results
    )
