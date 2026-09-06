"""Current-chain source block; historical M1.6 EOS regression lives in stage42 tests."""
import pytest
from gli.audit_block6m4_ef import run_block6m4_audit


@pytest.fixture(scope="module")
def audit():
    return run_block6m4_audit(max_step_s=0.5)


def test_current_ef_cannot_receive_unavailable_e(audit):
    assert not audit.can_receive_without_projection
    assert audit.ef_exception == "SOURCE_AMBIGUITY_GLV_CLOSE_BEFORE_E"


def test_no_e_time_is_fabricated(audit):
    assert audit.event_e_time_s is None


def test_no_eos_residual_is_invented_for_missing_e(audit):
    assert [r.name for r in audit.residuals] == ["physical_e_unavailable"]


def test_no_reference_f_is_substituted_for_physical_f(audit):
    assert not audit.event_f_reached
    assert audit.event_f_time_s is None


def test_block_retains_physical_slug_gap(audit):
    residual, = audit.residuals
    assert residual.units == "m"
    assert residual.value == pytest.approx(181.1079552, abs=1e-4)
    assert residual.status == "fail"


def test_exact_stage42_is_not_run_without_e(audit):
    assert not audit.corrected_certified
    assert not audit.corrected_event_f_reached
    assert audit.corrected_event_f_time_s is None


def test_source_block_is_exposed_in_corrected_audit(audit):
    assert audit.corrected_failed_contracts == ("physical_e_unavailable",)
    assert "NOT_SOURCE_CERTIFIED_A_TO_E" in audit.corrected_initial_state_source


def test_no_physical_state_source_claimed(audit):
    assert audit.ef_initial_state_source is None
    assert audit.failed_contracts == ("physical_e_unavailable",)
