"""Scientific audit and internal A->G orchestration for Santos stage 4.3."""
from __future__ import annotations

from dataclasses import dataclass

from .audit_block6m5_af import run_corrected_a_to_f_chain
from .base_case import santos_50_70_80
from .stage_fg_dynamic import HIGH_VELOCITY_WARNING, StageFGResult, simulate_stage_f_to_g


@dataclass(frozen=True)
class StageFGAudit:
    ready_for_review: bool
    terminal_event: str
    t_f_s: float
    t_g_s: float
    duration_fg_s: float
    failed_contracts: tuple[str, ...]
    gas_balance_normalized_residual: float
    liquid_balance_normalized_residual: float
    scientific_warning: str
    result: StageFGResult


def run_corrected_a_to_g_chain(
    params=None,
    *,
    af_max_step_s: float = 0.5,
    fg_max_step_s: float = 0.5,
    fg_rtol: float = 1.0e-8,
    fg_atol: float = 1.0e-10,
) -> tuple:
    p = params or santos_50_70_80()
    p, ab, bc, cd_common, cd, de, ef = run_corrected_a_to_f_chain(
        p, max_step_s=af_max_step_s
    )
    fg = simulate_stage_f_to_g(
        p,
        stage_e_f=ef,
        max_step_s=fg_max_step_s,
        rtol=fg_rtol,
        atol=fg_atol,
    )
    return p, ab, bc, cd_common, cd, de, ef, fg


def run_stage_fg_audit(params=None, *, af_max_step_s: float = 0.5, fg_max_step_s: float = 0.5) -> StageFGAudit:
    _p, ab, bc, cd_common, _cd, de, ef, fg = run_corrected_a_to_g_chain(
        params,
        af_max_step_s=af_max_step_s,
        fg_max_step_s=fg_max_step_s,
    )
    t_f = float(
        ab.opening_time_s
        + bc.event_c_time_s
        + cd_common.event_d_time_s
        + de.event_e_time_s
        + ef.event_f_time_s
    )
    failed: list[str] = []
    if not fg.event_g_reached:
        failed.append("event_g_not_reached")
    if not fg.event_direction_verified:
        failed.append("event_g_direction")
    if not fg.continuity_passed:
        failed.append("f_initial_continuity")
    if not fg.physical_bounds_passed:
        failed.append("physical_bounds")
    if fg.gas_balance_normalized_residual > 1.0e-8:
        failed.append("gas_balance")
    if fg.liquid_balance_normalized_residual > 1.0e-8:
        failed.append("liquid_balance")
    if float(fg.film_returned_volume_m3[-1]) <= 0.0:
        failed.append("film_did_not_return")
    if not fg.reservoir_inflow_valid:
        failed.append("reservoir_ipr_invalid_reverse_flow")
    if abs(float(fg.produced_liquid_volume_m3[-1] - fg.produced_liquid_volume_m3[0])) > 1.0e-12:
        failed.append("surface_liquid_production_during_fg")
    return StageFGAudit(
        ready_for_review=not failed,
        terminal_event=fg.event_identifier,
        t_f_s=t_f,
        t_g_s=t_f + fg.event_g_time_s,
        duration_fg_s=fg.event_g_time_s,
        failed_contracts=tuple(failed),
        gas_balance_normalized_residual=fg.gas_balance_normalized_residual,
        liquid_balance_normalized_residual=fg.liquid_balance_normalized_residual,
        scientific_warning=HIGH_VELOCITY_WARNING,
        result=fg,
    )
