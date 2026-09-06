from gli.design_domain import classify_design_domain
from gli_api.schemas import SimulationInputs
from gli_api.simulation_service import simulate


def santos_input(**updates) -> SimulationInputs:
    data = dict(
        tubingDiameter=0.050673,
        valveDepth=1480.0,
        slugLength=412.5,
        surfaceTubingPressure=0.788,
        injectionPressure=6.966,
        api=40.0,
        bsw=50.0,
        gasRelativeDensity=0.7,
        casingPressureOpenRatio=0.7,
        projectName="QA",
        projectistName="QA",
    )
    data.update(updates)
    return SimulationInputs(**data)


def test_exact_santos_api_input_is_blocked_by_stage42_source_gate():
    result = simulate(santos_input())

    assert result.validationLevel == "failed"
    assert result.physicalScope.startswith("NOT_SOURCE_CERTIFIED_A_TO_E:")
    assert result.terminalEvent == "GLV_CLOSE_BEFORE_E_SOURCE_BLOCK"


def test_inside_block7b_matrix_cannot_override_source_equation_failure():
    result = simulate(santos_input(injectionPressure=6.966 * 1.03, slugLength=412.5 * 0.98))

    assert result.validationLevel == "failed"
    assert result.terminalEvent == "GLV_CLOSE_BEFORE_E_SOURCE_BLOCK"
    assert result.physicalScope.startswith("NOT_SOURCE_CERTIFIED_A_TO_E:")


def test_outside_block7b_matrix_is_still_blocked_first_by_source_gate():
    result = simulate(santos_input(injectionPressure=6.966 * 1.20))

    assert result.validationLevel == "failed"
    assert result.terminalEvent == "GLV_CLOSE_BEFORE_E_SOURCE_BLOCK"
    assert result.physicalScope.startswith("NOT_SOURCE_CERTIFIED_A_TO_E:")


def test_design_domain_classifier_reports_outside_fields_without_running_physics():
    inputs = santos_input(api=45.0, bsw=60.0)
    classification = classify_design_domain(inputs, chain_certified=True)

    assert classification.validation_level == "out_of_domain"
    assert classification.exact_santos_reference is False
    assert classification.inside_local_matrix is False
    assert classification.outside_fields == ("bsw", "api")
