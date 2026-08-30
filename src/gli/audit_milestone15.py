"""Reproducible Milestone 1.5 event/IPR reconciliation experiment."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .audit_block6m5_af import run_corrected_a_to_f_chain
from .stage_fg_dynamic import simulate_stage_f_to_g


@dataclass(frozen=True)
class EventCandidateDiagnostic:
    name: str
    equation: str
    root_times_s: tuple[float, ...]
    first_root_s: float | None
    residual_at_horizon_pa: float
    terminal_in_production: bool


@dataclass(frozen=True)
class Milestone15Diagnostic:
    status: str
    safety_horizon_s: float
    legacy: EventCandidateDiagnostic
    corrected: EventCandidateDiagnostic
    reverse_flow_interval_s: tuple[float, float] | None
    minimum_raw_reservoir_rate_m3_s: float
    gas_balance_normalized_residual: float
    liquid_balance_normalized_residual: float


def _zero_crossings(times: np.ndarray, values: np.ndarray) -> tuple[float, ...]:
    roots: list[float] = []
    for index in np.flatnonzero(values[:-1] * values[1:] < 0.0):
        t0, t1 = float(times[index]), float(times[index + 1])
        y0, y1 = float(values[index]), float(values[index + 1])
        roots.append(t0 - y0 * (t1 - t0) / (y1 - y0))
    return tuple(roots)


def run_milestone15_diagnostic(
    params=None,
    *,
    af_max_step_s: float = 0.5,
    fg_max_step_s: float = 1.0,
    safety_horizon_s: float = 10_000.0,
) -> Milestone15Diagnostic:
    p, _ab, _bc, _cdc, _cd, _de, ef = run_corrected_a_to_f_chain(
        params, max_step_s=af_max_step_s
    )
    fg = simulate_stage_f_to_g(
        p,
        stage_e_f=ef,
        max_time_s=safety_horizon_s,
        max_step_s=fg_max_step_s,
    )
    corrected_roots = (fg.event_g_time_s,) if fg.event_g_reached else ()
    q_roots = _zero_crossings(fg.time_s, fg.reservoir_rate_m3_s)
    reverse_interval = None
    if float(fg.reservoir_rate_m3_s[0]) < 0.0:
        reverse_interval = (0.0, q_roots[0] if q_roots else float(fg.time_s[-1]))
    status = "READY_FOR_GH" if fg.event_g_reached and fg.reservoir_inflow_valid else "NOT_READY_FOR_GH"
    return Milestone15Diagnostic(
        status=status,
        safety_horizon_s=float(safety_horizon_s),
        legacy=EventCandidateDiagnostic(
            name="legacy_pressure_recovery",
            equation="P_t1-P_to_initial=0",
            root_times_s=fg.legacy_event_times_s,
            first_root_s=fg.legacy_event_times_s[0] if fg.legacy_event_times_s else None,
            residual_at_horizon_pa=float(fg.legacy_pressure_residual_pa[-1]),
            terminal_in_production=False,
        ),
        corrected=EventCandidateDiagnostic(
            name="momentum_equilibrium",
            equation="P_t3-P_ts-rho_g*g*(H_gv-h_l)=0",
            root_times_s=corrected_roots,
            first_root_s=corrected_roots[0] if corrected_roots else None,
            residual_at_horizon_pa=float(fg.momentum_residual_pa[-1]),
            terminal_in_production=True,
        ),
        reverse_flow_interval_s=reverse_interval,
        minimum_raw_reservoir_rate_m3_s=float(np.min(fg.reservoir_rate_m3_s)),
        gas_balance_normalized_residual=fg.gas_balance_normalized_residual,
        liquid_balance_normalized_residual=fg.liquid_balance_normalized_residual,
    )
