import pytest

from gli.audit_block6m5_af import run_block6m5_audit
from gli_api.schemas import SimulationInputs
from gli_api.simulation_service import build_parameters, simulate


@pytest.fixture(scope="module")
def audit():
    return run_block6m5_audit(max_step_s=0.5)


def test_corrected_a_to_f_chain_is_certified(audit):
    assert audit.certified
    assert audit.validation_level_candidate == "certified"
    assert audit.terminal_event == "F_FILM_VELOCITY_ZERO"
    assert audit.failed_contracts == ()
    assert audit.max_residual_normalized < 1e-8


def test_events_are_ordered_a_to_f(audit):
    assert list(audit.event_times_s) == [
        "A_INITIAL_STATE",
        "B_GAS_LIFT_VALVE_OPENS",
        "C_MOTOR_VALVE_CLOSES",
        "D_SLUG_TOP_REACHED_SURFACE",
        "E_SLUG_BASE_REACHED_SURFACE",
        "F_FILM_VELOCITY_ZERO",
    ]
    times = list(audit.event_times_s.values())
    assert times[0] == 0.0
    assert all(b > a for a, b in zip(times, times[1:]))


def test_balances_and_valves_close_in_certification(audit):
    by_name = {r.name: r for r in audit.residuals}
    for name in (
        "bc_certified",
        "cd_certified",
        "de_event_e",
        "de_gas_balance",
        "de_liquid_balance",
        "de_glv_closed",
        "ef_certified",
        "ef_gas_balance",
        "ef_liquid_balance",
        "ef_glv_closed",
        "terminal_f_velocity",
    ):
        assert by_name[name].status == "ok"


def test_api_f_time_matches_audit_with_api_resolution_and_documents_coarse_step_difference(audit):
    inputs = SimulationInputs(
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
    result = simulate(inputs)
    params = build_parameters(inputs)
    api_resolution_audit = run_block6m5_audit(params, max_step_s=None)
    api_params_coarse_audit = run_block6m5_audit(params, max_step_s=0.5)
    assert result.points[-1].t == pytest.approx(
        api_resolution_audit.event_times_s["F_FILM_VELOCITY_ZERO"],
        abs=1e-9,
    )
    coarse_f = api_params_coarse_audit.event_times_s["F_FILM_VELOCITY_ZERO"]
    api_f = result.points[-1].t
    assert abs(api_f - coarse_f) < 1e-6
    internal_base_case_f = audit.event_times_s["F_FILM_VELOCITY_ZERO"]
    assert abs(api_f - internal_base_case_f) == pytest.approx(0.2585271498665, rel=1e-6)
    assert audit.certified and api_resolution_audit.certified and api_params_coarse_audit.certified
