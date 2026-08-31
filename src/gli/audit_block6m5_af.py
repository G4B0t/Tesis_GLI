"""Block 6M-5 end-to-end A->F certification audit."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from .base_case import santos_50_70_80
from .stage1_dynamic import simulate_stage_1
from .stage_bc_common import simulate_stage_b_to_c_common
from .stage_cd_common import common_to_stage_cd_result, simulate_stage_c_to_d_common
from .stage_de_dynamic import simulate_stage_d_to_e
from .stage_ef_dynamic import audit_stage_42_initial_state, simulate_stage_e_to_f


@dataclass(frozen=True)
class ResidualAF:
    name: str
    value: float
    scale: float
    normalized: float
    status: str
    interpretation: str


@dataclass(frozen=True)
class Block6M5Audit:
    certified: bool
    validation_level_candidate: str
    terminal_event: str
    event_times_s: dict[str, float]
    stage_durations_s: dict[str, float]
    max_residual_normalized: float
    failed_contracts: tuple[str, ...]
    residuals: tuple[ResidualAF, ...]
    source_certification_status: str = "NOT_SOURCE_CERTIFIED_A_TO_F"


def _add(residuals: list[ResidualAF], name: str, value: float, scale: float, tolerance: float, interpretation: str):
    scale = max(abs(float(scale)), 1e-18)
    normalized = abs(float(value)) / scale
    residuals.append(
        ResidualAF(name, float(value), scale, float(normalized),
                   "ok" if normalized <= tolerance else "fail", interpretation)
    )


def run_corrected_a_to_f_chain(params=None, *, max_step_s: float | None = 0.2):
    p = params or santos_50_70_80()
    if max_step_s is None:
        ab = simulate_stage_1(p)
        bc = simulate_stage_b_to_c_common(p, stage_a_b=ab, rhs_mode="santos_compatible")
        cd_common = simulate_stage_c_to_d_common(p, stage_b_c_common=bc, rhs_mode="santos_corrected")
    else:
        ab = simulate_stage_1(p, max_step_s=max_step_s)
        bc = simulate_stage_b_to_c_common(p, stage_a_b=ab, rhs_mode="santos_compatible", max_step_s=max_step_s)
        cd_common = simulate_stage_c_to_d_common(p, stage_b_c_common=bc, rhs_mode="santos_corrected", max_step_s=max_step_s)
    cd = common_to_stage_cd_result(cd_common, p)
    if max_step_s is None:
        de = simulate_stage_d_to_e(p, stage_c_d=cd, rhs_mode="santos_corrected")
    else:
        de = simulate_stage_d_to_e(p, stage_c_d=cd, rhs_mode="santos_corrected", max_step_s=max_step_s)
    # Preserve the Milestone-1.5 trajectory only as a numerical comparison.
    # The exact Stage-4.2 identity map is audited separately below and is the
    # sole authority for source certification.
    ef = simulate_stage_e_to_f(p, stage_d_e=de, rhs_mode="milestone15_corrected", max_step_s=0.01)
    return p, ab, bc, cd_common, cd, de, ef


def run_block6m5_audit(params=None, *, max_step_s: float | None = 0.5) -> Block6M5Audit:
    _p, ab, bc, cd_common, _cd, de, ef = run_corrected_a_to_f_chain(params, max_step_s=max_step_s)
    residuals: list[ResidualAF] = []
    event_times = {
        "A_INITIAL_STATE": 0.0,
        "B_GAS_LIFT_VALVE_OPENS": float(ab.opening_time_s),
        "C_MOTOR_VALVE_CLOSES": float(ab.opening_time_s + bc.event_c_time_s),
        "D_SLUG_TOP_REACHED_SURFACE": float(ab.opening_time_s + bc.event_c_time_s + cd_common.event_d_time_s),
        "E_SLUG_BASE_REACHED_SURFACE": float(ab.opening_time_s + bc.event_c_time_s + cd_common.event_d_time_s + de.event_e_time_s),
        "F_FILM_VELOCITY_ZERO": float(ab.opening_time_s + bc.event_c_time_s + cd_common.event_d_time_s + de.event_e_time_s + ef.event_f_time_s),
    }
    durations = {
        "A_B": float(ab.opening_time_s),
        "B_C": float(bc.event_c_time_s),
        "C_D": float(cd_common.event_d_time_s),
        "D_E": float(de.event_e_time_s),
        "E_F": float(ef.event_f_time_s),
    }
    times = list(event_times.values())
    min_dt = min(np.diff(times))
    _add(residuals, "event_order_A_to_F", 0.0 if min_dt > 0 else -1.0, 1.0, 0.0,
         "Los eventos A, B, C, D, E y F deben estar ordenados estrictamente.")
    _add(residuals, "bc_certified", 0.0 if bc.certified else 1.0, 1.0, 0.0,
         "B->C santos_compatible debe estar certificado.")
    _add(residuals, "cd_certified", 0.0 if cd_common.certified else 1.0, 1.0, 0.0,
         "C->D santos_corrected debe estar certificado.")
    _add(residuals, "de_event_e", 0.0 if de.event_e_reached else 1.0, 1.0, 0.0,
         "D->E santos_corrected debe alcanzar E.")
    _add(residuals, "de_gas_balance", float(de.gas_balance_relative_error), 1.0, 1e-8,
         "Balance de gas acumulado hasta E.")
    _add(residuals, "de_liquid_balance", float(de.liquid_balance_relative_error), 1.0, 1e-8,
         "Balance líquido acumulado hasta E.")
    _add(residuals, "de_glv_closed", float(np.max(de.valve_open.astype(float))), 1.0, 0.0,
         "La GLV debe permanecer cerrada en D->E corregido.")
    stage42_e = audit_stage_42_initial_state(_p, de)
    _add(
        residuals,
        "stage42_e_source_compatibility",
        0.0 if stage42_e.compatible else stage42_e.eos_density_relative_residual,
        1.0,
        1e-6,
        "La identidad E debe satisfacer simultáneamente inventario, 4.1.88 y 4.1.90.",
    )
    _add(residuals, "ef_certified", 1.0, 1.0, 0.0,
         "La trayectoria E->F de Milestone 1.5 es referencia, no Stage 4.2 certificada.")
    _add(residuals, "ef_gas_balance", float(ef.gas_balance_relative_error), 1.0, 1e-8,
         "Balance gas en E->F corregido.")
    _add(residuals, "ef_liquid_balance", float(ef.liquid_balance_relative_error), 1.0, 1e-8,
         "Balance líquido en E->F corregido.")
    _add(residuals, "ef_glv_closed", float(np.max(ef.valve_open.astype(float))), 1.0, 0.0,
         "La GLV no debe reabrir en E->F corregido.")
    _add(residuals, "terminal_f_velocity_reference", float(ef.film_velocity_m_s[-1]), max(abs(float(ef.film_velocity_m_s[0])), 1.0), 1e-8,
         "El F de Milestone 1.5 sigue disponible solo para comparación numérica.")
    failed = tuple(r.name for r in residuals if r.status != "ok")
    max_norm = max((r.normalized for r in residuals), default=0.0)
    certified = not failed
    return Block6M5Audit(
        certified=certified,
        validation_level_candidate="certified" if certified else "provisional",
        terminal_event="F_FILM_VELOCITY_ZERO" if certified else "E_SLUG_BASE_REACHED_SURFACE",
        event_times_s=event_times,
        stage_durations_s=durations,
        max_residual_normalized=float(max_norm),
        failed_contracts=failed,
        residuals=tuple(residuals),
        source_certification_status=("SOURCE_CERTIFIED_A_TO_F" if certified else "NOT_SOURCE_CERTIFIED_A_TO_F"),
    )


def audit_summary(params=None, *, max_step_s: float | None = 0.5) -> dict[str, Any]:
    return asdict(run_block6m5_audit(params, max_step_s=max_step_s))
