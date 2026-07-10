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


def test_small_design_matrix_can_become_validated_range_candidate_but_not_commercial_domain():
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
    assert audit.validated_range_candidate is True
    assert audit.failed_scenarios == ()
    assert audit.provisional_scenarios == ()
    assert audit.scenario_count == 3
    assert audit.max_residual_normalized < 1e-8
    assert "No reemplaza validación con casos independientes" in audit.statement
    assert audit.results[0].status == "certified_reference"
    assert all(r.status == "validated_range_candidate" for r in audit.results[1:])
