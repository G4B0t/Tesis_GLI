import pytest

from gli.audit_block6m5_af import run_block6m5_audit
from gli_api.schemas import SimulationInputs
from gli_api.simulation_service import build_parameters, simulate


@pytest.fixture(scope="module")
def audit():
    return run_block6m5_audit(max_step_s=0.5)


def test_a_to_f_source_certification_is_blocked(audit):
    assert not audit.certified
    assert audit.validation_level_candidate == "provisional"
    assert audit.terminal_event == "GLV_CLOSE_BEFORE_E_SOURCE_BLOCK"
    assert audit.source_certification_status == "NOT_SOURCE_CERTIFIED_A_TO_E"
    assert audit.failed_contracts == ("de_event_e", "de_source_certification", "physical_f_state_unavailable")


def test_milestone15_reference_events_remain_available_for_comparison(audit):
    assert list(audit.event_times_s) == [
        "A_INITIAL_STATE",
        "B_GAS_LIFT_VALVE_OPENS",
        "C_MOTOR_VALVE_CLOSES",
        "D_SLUG_TOP_REACHED_SURFACE",
        "GLV_CLOSE_BEFORE_E_SOURCE_BLOCK",
    ]
    times = list(audit.event_times_s.values())
    assert times[0] == 0.0
    assert all(b > a for a, b in zip(times, times[1:]))


def test_balances_and_valves_close_in_certification(audit):
    by_name = {r.name: r for r in audit.residuals}
    for name in (
        "bc_certified",
        "cd_certified",
        "de_gas_balance",
        "de_liquid_balance",
    ):
        assert by_name[name].status == "ok"
    for name in ("de_event_e", "de_source_certification", "physical_f_state_unavailable"):
        assert by_name[name].status == "fail"


def test_api_stops_at_e_and_matches_source_qualified_event_time(audit):
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
        api_resolution_audit.event_times_s["GLV_CLOSE_BEFORE_E_SOURCE_BLOCK"],
        abs=1e-9,
    )
    assert result.terminalEvent == "GLV_CLOSE_BEFORE_E_SOURCE_BLOCK"
    assert result.points[-1].stage == "D_E"
    assert not audit.certified
    assert not api_resolution_audit.certified
    assert not api_params_coarse_audit.certified
