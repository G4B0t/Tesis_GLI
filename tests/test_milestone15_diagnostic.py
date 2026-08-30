from gli.audit_milestone15 import run_milestone15_diagnostic


def test_reconciliation_keeps_legacy_root_but_blocks_gh_without_momentum_root():
    audit = run_milestone15_diagnostic(safety_horizon_s=1200.0, fg_max_step_s=1.0)
    assert audit.status == "NOT_READY_FOR_GH"
    assert len(audit.legacy.root_times_s) == 1
    assert audit.corrected.root_times_s == ()
    assert audit.corrected.residual_at_horizon_pa > 0.0
    assert audit.reverse_flow_interval_s is not None
    assert audit.minimum_raw_reservoir_rate_m3_s < 0.0
    assert audit.gas_balance_normalized_residual <= 1e-8
    assert audit.liquid_balance_normalized_residual <= 1e-8
