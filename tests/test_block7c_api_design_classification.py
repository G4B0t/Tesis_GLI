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


def test_exact_santos_api_input_remains_certified():
    result = simulate(santos_input())

    assert result.validationLevel == "certified"
    assert result.physicalScope.startswith("A_TO_F certified:")
    assert result.terminalEvent == "F_FILM_VELOCITY_ZERO"


def test_inside_block7b_matrix_is_candidate_not_certified():
    result = simulate(santos_input(injectionPressure=6.966 * 1.03, slugLength=412.5 * 0.98))

    assert result.validationLevel == "validated_range_candidate"
    assert result.terminalEvent == "F_FILM_VELOCITY_ZERO"
    assert result.physicalScope.startswith("A_TO_F validated_range_candidate:")
    assert any("falta validación independiente" in item for item in result.modelLimitations)


def test_outside_block7b_matrix_is_not_a_design_validated_result_even_if_chain_runs():
    result = simulate(santos_input(injectionPressure=6.966 * 1.20))

    assert result.validationLevel == "out_of_domain"
    assert result.terminalEvent == "F_FILM_VELOCITY_ZERO"
    assert result.physicalScope.startswith("A_TO_F out_of_domain:")
    assert any("injectionPressure" in item for item in result.modelLimitations)


def test_design_domain_classifier_reports_outside_fields_without_running_physics():
    inputs = santos_input(api=45.0, bsw=60.0)
    classification = classify_design_domain(inputs, chain_certified=True)

    assert classification.validation_level == "out_of_domain"
    assert classification.exact_santos_reference is False
    assert classification.inside_local_matrix is False
    assert classification.outside_fields == ("bsw", "api")
