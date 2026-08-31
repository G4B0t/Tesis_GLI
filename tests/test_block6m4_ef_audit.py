import pytest

from gli.audit_block6m4_ef import run_block6m4_audit
from gli_api.schemas import SimulationInputs
from gli_api.simulation_service import simulate


@pytest.fixture(scope="module")
def audit():
    return run_block6m4_audit(max_step_s=0.5)


def test_current_ef_cannot_receive_corrected_e_without_projection(audit):
    assert not audit.can_receive_without_projection
    assert audit.ef_exception is None
    assert "v_f_memory" in audit.failed_contracts
    assert "v_g_memory" in audit.failed_contracts
    assert "produced_ledger_continuity" in audit.failed_contracts
    assert "liquid_inventory_continuity" in audit.failed_contracts


def test_ef_preserves_only_static_e_inventories_and_pressure(audit):
    by_name = {r.name: r for r in audit.residuals}
    assert by_name["rho_g_continuity"].status == "ok"
    assert by_name["m_g_continuity"].status == "ok"
    assert by_name["P_t1_continuity"].status == "ok"
    assert by_name["y_geometry_continuity"].status == "ok"
    assert by_name["m_film_continuity"].status == "ok"
    assert by_name["gas_geometry_eos_consistency"].status == "ok"


def test_ef_dynamic_memory_and_ledgers_are_blocking_contracts(audit):
    by_name = {r.name: r for r in audit.residuals}
    assert by_name["v_f_memory"].status == "fail"
    assert by_name["v_f_memory"].normalized > 1e-2
    assert "reconstruye v_f" in by_name["v_f_memory"].interpretation
    assert by_name["v_g_memory"].status == "fail"
    assert by_name["v_g_memory"].normalized > 1.0
    assert by_name["fallback_ledger_continuity"].status == "fail"
    assert by_name["produced_ledger_continuity"].status == "fail"
    assert by_name["produced_ledger_continuity"].value < 0.0


def test_event_f_contract_is_not_certified(audit):
    by_name = {r.name: r for r in audit.residuals}
    assert not audit.event_f_reached
    assert audit.event_f_time_s is None
    assert by_name["event_f_descending"].status == "fail"


def test_glv_remains_closed_in_audited_ef_path(audit):
    by_name = {r.name: r for r in audit.residuals}
    assert by_name["glv_closed_no_reopen"].status == "ok"
    assert by_name["glv_closed_no_reopen"].value == 0.0


def test_exact_stage42_rejects_incompatible_e_without_projection(audit):
    assert not audit.corrected_certified
    assert not audit.corrected_event_f_reached
    assert audit.corrected_event_f_time_s is None
    assert audit.corrected_failed_contracts == (
        "stage42_eos_E",
        "stage42_eos_volume_domain",
    )
    assert "NOT_SOURCE_CERTIFIED_A_TO_F" in audit.corrected_initial_state_source


def test_stage42_e_boundary_passes_hydrostatics_but_fails_eos(audit):
    by_name = {r.name: r for r in audit.corrected_residuals}
    for name in ("stage42_h_l_E", "stage42_hydrostatic_E", "stage42_inventory_E"):
        assert by_name[name].status == "ok"
        assert by_name[name].normalized < 1e-8
    assert by_name["stage42_eos_E"].status == "fail"
    assert by_name["stage42_eos_E"].normalized == pytest.approx(0.7255764980, rel=1e-8)
    assert by_name["stage42_eos_volume_domain"].status == "fail"


def test_public_api_is_not_promoted_when_stage42_source_gate_fails():
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
    assert result.validationLevel == "failed"
    assert result.terminalEvent == "E_SLUG_BASE_REACHED_SURFACE"
    assert "NOT_SOURCE_CERTIFIED_A_TO_F" in result.physicalScope
    assert result.points[-1].stage == "D_E"
