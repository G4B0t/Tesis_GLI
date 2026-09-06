from gli.audit_milestone15 import run_milestone15_diagnostic


def test_reconciliation_blocks_fg_without_reintroducing_legacy_reconstruction():
    audit = run_milestone15_diagnostic(safety_horizon_s=1200.0, fg_max_step_s=1.0)
    assert audit.status == "BLOCKED_BY_SOURCE"
    assert audit.legacy.root_times_s == ()
    assert audit.corrected.root_times_s == ()
    assert audit.corrected.residual_at_horizon_pa is None
    assert audit.reverse_flow_interval_s is None
    assert audit.minimum_raw_reservoir_rate_m3_s is None
    assert audit.gas_balance_normalized_residual is None
    assert audit.liquid_balance_normalized_residual is None
    assert audit.stage42_eos_density_relative_residual is None
    assert "F->G was not run" in audit.blocking_reason
