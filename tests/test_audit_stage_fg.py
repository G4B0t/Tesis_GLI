from __future__ import annotations

import pytest

from gli.audit_block6m5_af import run_block6m5_audit
from gli.audit_stage_fg import run_stage_fg_audit
from gli.stage_fg_dynamic import HIGH_VELOCITY_WARNING


@pytest.fixture(scope="module")
def audits():
    return run_block6m5_audit(max_step_s=0.5), run_stage_fg_audit(
        af_max_step_s=0.5, fg_max_step_s=0.5
    )


def test_a_to_g_audit_stops_before_unavailable_physical_f(audits):
    af, fg = audits
    assert not af.certified
    assert fg.t_f_s is None
    assert fg.result is None


def test_a_to_g_audit_blocks_g_to_h_at_stage42_identity_gate(audits):
    _af, fg = audits
    assert not fg.ready_for_review
    assert fg.status == "NOT_READY_FOR_GH"
    assert fg.terminal_event == "E_SLUG_BASE_REACHED_SURFACE"
    assert fg.failed_contracts == (
        "stage42_initial_state_incompatible",
        "physical_f_state_unavailable",
        "stage_fg_not_run",
    )
    assert fg.t_g_s is None
    assert "NOT_SOURCE_CERTIFIED_A_TO_F" in fg.blocking_reason


def test_a_to_g_audit_reports_balances_and_existing_warning(audits):
    _af, fg = audits
    assert fg.gas_balance_normalized_residual is None
    assert fg.liquid_balance_normalized_residual is None
    assert fg.scientific_warning == HIGH_VELOCITY_WARNING
