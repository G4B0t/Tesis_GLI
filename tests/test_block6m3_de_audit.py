import pytest

from gli.audit_block6m3_de import run_block6m3_audit


@pytest.fixture(scope="module")
def audit():
    return run_block6m3_audit(max_step_s=0.5)


def test_stage_de_legacy_is_not_certified_from_corrected_d(audit):
    assert not audit.certified
    assert audit.corrected_certified
    assert audit.event_e_time_s > 0.0
    assert audit.corrected_event_e_time_s > 0.0
    assert audit.produced_volume_m3 > 0.0
    assert audit.corrected_produced_volume_m3 > audit.produced_volume_m3


def test_residual_vector_identifies_blocking_terms(audit):
    by_name = {r.name: r for r in audit.residuals}
    assert by_name["top_boundary"].normalized < 1e-10
    assert by_name["gas_eos_D"].normalized < 1e-8
    assert by_name["film_geometry_D"].normalized < 1e-8
    assert by_name["slug_mass_D"].normalized < 1e-6
    assert by_name["memory_vf_missing"].status == "fail"
    assert by_name["reservoir_stage3"].status == "fail"
    assert by_name["legacy_balance_metric"].status == "fail"
    assert by_name["glv_boundary"].status == "fail"
    corrected = {r.name: r for r in audit.corrected_residuals}
    assert corrected["vf_memory"].status == "ok"
    assert corrected["reservoir_balance"].status == "ok"
    assert corrected["glv_latched_closed"].status == "ok"
    assert corrected["event_E"].status == "ok"


def test_legacy_liquid_balance_uses_wrong_reference_inventory(audit):
    assert audit.legacy_liquid_balance_error > 0.1
    assert audit.reservoir_missing_m3 > 0.0
    assert audit.corrected_inventory_residual_m3 < audit.reservoir_missing_m3
    assert audit.corrected_liquid_balance_error < 1e-10
    assert audit.corrected_reservoir_residual_m3 < 1e-10


def test_glv_is_open_in_legacy_de_and_blocks_certification(audit):
    assert audit.glv_open_at_d
    assert audit.glv_open_any_de
    assert audit.glv_mass_rate_start_kg_s > 0.0
    assert not audit.corrected_glv_open_any
