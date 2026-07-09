"""Executable helpers for the Block 6M-2D C-compatibility audit."""
from __future__ import annotations

from dataclasses import asdict

from .base_case import santos_50_70_80
from .block6m2d_compatibility import compatibility_residuals_c
from .stage1_dynamic import simulate_stage_1
from .stage_bc_common import simulate_stage_b_to_c_common
from .stage_cd_common import simulate_stage_c_to_d_common


def run_block6m2d_audit(max_step_s: float = 0.5):
    params = santos_50_70_80()
    ab = simulate_stage_1(params, max_step_s=max_step_s)
    inherited = simulate_stage_b_to_c_common(params, stage_a_b=ab, max_step_s=max_step_s)
    compatible = simulate_stage_b_to_c_common(
        params, stage_a_b=ab, max_step_s=max_step_s, rhs_mode="santos_compatible"
    )
    inherited_audit = compatibility_residuals_c(
        params, inherited.final_state, target_vgi_std_m3=inherited.target_volume_std_m3
    )
    compatible_audit = compatibility_residuals_c(
        params, compatible.final_state, target_vgi_std_m3=compatible.target_volume_std_m3
    )
    cd_rejected = simulate_stage_c_to_d_common(
        params, stage_b_c_common=inherited, max_step_s=max_step_s, rhs_mode="santos_corrected"
    )
    cd_certified = simulate_stage_c_to_d_common(
        params, stage_b_c_common=compatible, max_step_s=max_step_s, rhs_mode="santos_corrected"
    )
    return {
        "inherited_bc": inherited,
        "compatible_bc": compatible,
        "inherited_audit": inherited_audit,
        "compatible_audit": compatible_audit,
        "cd_rejected": cd_rejected,
        "cd_certified": cd_certified,
    }


def audit_summary(max_step_s: float = 0.5):
    result = run_block6m2d_audit(max_step_s=max_step_s)
    return {
        "inherited_c_time_s": result["inherited_bc"].event_c_time_s,
        "compatible_c_time_s": result["compatible_bc"].event_c_time_s,
        "inherited_max_R": result["inherited_audit"].max_normalized,
        "compatible_max_R": result["compatible_audit"].max_normalized,
        "cd_rejected_certified": result["cd_rejected"].certified,
        "cd_rejected_liquid_balance": result["cd_rejected"].liquid_balance_relative_error,
        "cd_certified": result["cd_certified"].certified,
        "cd_certified_event_d_s": result["cd_certified"].event_d_time_s,
        "cd_certified_gas_balance": result["cd_certified"].gas_balance_relative_error,
        "cd_certified_liquid_balance": result["cd_certified"].liquid_balance_relative_error,
        "cd_certified_eos": result["cd_certified"].eos_relative_error,
        "residuals_current": [asdict(r) for r in result["inherited_audit"].residuals],
        "residuals_compatible": [asdict(r) for r in result["compatible_audit"].residuals],
    }


if __name__ == "__main__":
    import json

    print(json.dumps(audit_summary(), indent=2))
