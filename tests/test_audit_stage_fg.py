from __future__ import annotations

import pytest

from gli.audit_block6m5_af import run_block6m5_audit
from gli.audit_stage_fg import run_stage_fg_audit
from gli.events import EVENT_G_MOMENTUM_EQUILIBRIUM
from gli.stage_fg_dynamic import HIGH_VELOCITY_WARNING


@pytest.fixture(scope="module")
def audits():
    return run_block6m5_audit(max_step_s=0.5), run_stage_fg_audit(
        af_max_step_s=0.5, fg_max_step_s=0.5
    )


def test_a_to_g_audit_preserves_the_existing_f_boundary(audits):
    af, fg = audits
    assert af.certified
    assert fg.t_f_s == pytest.approx(af.event_times_s["F_FILM_VELOCITY_ZERO"], rel=1.0e-12)


def test_a_to_g_audit_blocks_g_to_h_when_corrected_event_has_no_root(audits):
    _af, fg = audits
    assert not fg.ready_for_review
    assert fg.terminal_event == EVENT_G_MOMENTUM_EQUILIBRIUM
    assert "event_g_not_reached" in fg.failed_contracts
    assert "reservoir_ipr_invalid_reverse_flow" in fg.failed_contracts
    assert fg.t_g_s > fg.t_f_s
    assert "H" not in fg.terminal_event


def test_a_to_g_audit_reports_balances_and_existing_warning(audits):
    _af, fg = audits
    assert fg.gas_balance_normalized_residual <= 1.0e-8
    assert fg.liquid_balance_normalized_residual <= 1.0e-8
    assert fg.scientific_warning == HIGH_VELOCITY_WARNING
