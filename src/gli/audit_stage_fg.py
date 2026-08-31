"""Scientific gate between Santos Stage 4.2 and Stage 4.3."""
from __future__ import annotations

from dataclasses import dataclass

from .audit_block6m5_af import run_corrected_a_to_f_chain
from .stage_ef_dynamic import Stage42InitialStateIncompatibility, simulate_stage_e_to_f
from .stage_fg_dynamic import HIGH_VELOCITY_WARNING, StageFGResult, simulate_stage_f_to_g


@dataclass(frozen=True)
class StageFGAudit:
    ready_for_review: bool
    terminal_event: str
    t_f_s: float | None
    t_g_s: float | None
    duration_fg_s: float | None
    failed_contracts: tuple[str, ...]
    gas_balance_normalized_residual: float | None
    liquid_balance_normalized_residual: float | None
    scientific_warning: str
    result: StageFGResult | None
    status: str = "NOT_READY_FOR_GH"
    blocking_reason: str | None = None


def run_corrected_a_to_g_chain(
    params=None,
    *,
    af_max_step_s: float = 0.5,
    fg_max_step_s: float = 0.5,
    fg_rtol: float = 1.0e-8,
    fg_atol: float = 1.0e-10,
) -> tuple:
    """Run A→G only when the exact Stage-4.2 identity gate succeeds."""

    p, ab, bc, cd_common, cd, de, _reference_ef = run_corrected_a_to_f_chain(
        params, max_step_s=af_max_step_s
    )
    ef = simulate_stage_e_to_f(
        p, stage_d_e=de, rhs_mode="santos_corrected", max_step_s=0.01
    )
    fg = simulate_stage_f_to_g(
        p, stage_e_f=ef, max_step_s=fg_max_step_s, rtol=fg_rtol, atol=fg_atol
    )
    return p, ab, bc, cd_common, cd, de, ef, fg


def run_stage_fg_audit(
    params=None,
    *,
    af_max_step_s: float = 0.5,
    fg_max_step_s: float = 0.5,
) -> StageFGAudit:
    """Return a structured upstream block instead of reconstructing F."""

    p, ab, bc, cd_common, _cd, de, _reference_ef = run_corrected_a_to_f_chain(
        params, max_step_s=af_max_step_s
    )
    try:
        ef = simulate_stage_e_to_f(
            p, stage_d_e=de, rhs_mode="santos_corrected", max_step_s=0.01
        )
    except Stage42InitialStateIncompatibility as exc:
        return StageFGAudit(
            ready_for_review=False,
            terminal_event="E_SLUG_BASE_REACHED_SURFACE",
            t_f_s=None,
            t_g_s=None,
            duration_fg_s=None,
            failed_contracts=(
                "stage42_initial_state_incompatible",
                "physical_f_state_unavailable",
                "stage_fg_not_run",
            ),
            gas_balance_normalized_residual=None,
            liquid_balance_normalized_residual=None,
            scientific_warning=HIGH_VELOCITY_WARNING,
            result=None,
            status="NOT_READY_FOR_GH",
            blocking_reason=str(exc),
        )

    fg = simulate_stage_f_to_g(p, stage_e_f=ef, max_step_s=fg_max_step_s)
    t_e = float(
        ab.opening_time_s + bc.event_c_time_s + cd_common.event_d_time_s + de.event_e_time_s
    )
    t_f = t_e + float(ef.event_f_time_s)
    duration_fg = fg.event_g_time_s if fg.event_g_reached else None
    t_g = t_f + duration_fg if duration_fg is not None else None
    failed: list[str] = []
    if not fg.event_g_reached:
        failed.append("event_g_not_reached")
    if not fg.event_direction_verified:
        failed.append("event_g_direction")
    if not fg.continuity_passed:
        failed.append("f_initial_continuity")
    if not fg.physical_bounds_passed:
        failed.append("physical_bounds")
    if not fg.reservoir_inflow_valid:
        failed.append("reservoir_ipr_invalid_reverse_flow")
    return StageFGAudit(
        ready_for_review=not failed,
        terminal_event=fg.event_identifier,
        t_f_s=t_f,
        t_g_s=t_g,
        duration_fg_s=duration_fg,
        failed_contracts=tuple(failed),
        gas_balance_normalized_residual=fg.gas_balance_normalized_residual,
        liquid_balance_normalized_residual=fg.liquid_balance_normalized_residual,
        scientific_warning=HIGH_VELOCITY_WARNING,
        result=fg,
        status="READY_FOR_GH" if not failed else "NOT_READY_FOR_GH",
    )
