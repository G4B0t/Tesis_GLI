"""Milestone-1.5 comparison metadata after removing its F reconstruction."""
from __future__ import annotations

from dataclasses import dataclass

from .audit_block6m5_af import run_corrected_a_to_f_chain
from .stage_ef_dynamic import audit_stage_42_initial_state


@dataclass(frozen=True)
class EventCandidateDiagnostic:
    name: str
    equation: str
    root_times_s: tuple[float, ...]
    first_root_s: float | None
    residual_at_horizon_pa: float | None
    terminal_in_production: bool


@dataclass(frozen=True)
class Milestone15Diagnostic:
    status: str
    safety_horizon_s: float
    legacy: EventCandidateDiagnostic
    corrected: EventCandidateDiagnostic
    reverse_flow_interval_s: tuple[float, float] | None
    minimum_raw_reservoir_rate_m3_s: float | None
    gas_balance_normalized_residual: float | None
    liquid_balance_normalized_residual: float | None
    stage42_eos_density_relative_residual: float
    blocking_reason: str


def run_milestone15_diagnostic(
    params=None,
    *,
    af_max_step_s: float = 0.5,
    fg_max_step_s: float = 1.0,
    safety_horizon_s: float = 10_000.0,
) -> Milestone15Diagnostic:
    """Report why the old F→G experiment is no longer executable.

    The historical numeric values remain in the Milestone-1.6 diagnostic
    report. Re-running them would require the ledger-to-height reconstruction
    intentionally removed from production.
    """

    _p, _ab, _bc, _cdc, _cd, de, _reference_ef = run_corrected_a_to_f_chain(
        params, max_step_s=af_max_step_s
    )
    audit = audit_stage_42_initial_state(_p, de)
    reason = (
        "Stage 4.2 cannot create a physical F state by identity; F->G was not run "
        "and no safety horizon is reported as an event time."
    )
    return Milestone15Diagnostic(
        status="NOT_READY_FOR_GH",
        safety_horizon_s=float(safety_horizon_s),
        legacy=EventCandidateDiagnostic(
            name="legacy_pressure_recovery",
            equation="P_t1-P_to_initial=0 (historical diagnostic only)",
            root_times_s=(),
            first_root_s=None,
            residual_at_horizon_pa=None,
            terminal_in_production=False,
        ),
        corrected=EventCandidateDiagnostic(
            name="momentum_equilibrium",
            equation="P_t3-P_ts-rho_g*g*(H_gv-h_l)=0",
            root_times_s=(),
            first_root_s=None,
            residual_at_horizon_pa=None,
            terminal_in_production=True,
        ),
        reverse_flow_interval_s=None,
        minimum_raw_reservoir_rate_m3_s=None,
        gas_balance_normalized_residual=None,
        liquid_balance_normalized_residual=None,
        stage42_eos_density_relative_residual=audit.eos_density_relative_residual,
        blocking_reason=reason,
    )
