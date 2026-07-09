"""Block 6M-4A audit for the E->F decompression boundary.

The audit keeps E->F disconnected from the public API.  It answers a narrow
question: can the current E->F implementation consume the mathematically
certified E state delivered by the parallel Santos-corrected D->E route without
projection or hidden reconstruction?
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import pi, sqrt
from typing import Any

import numpy as np

from .base_case import santos_50_70_80
from .geometry import tubing_area
from .initial_conditions import initial_stage_1
from .stage1_dynamic import simulate_stage_1
from .stage_bc_common import simulate_stage_b_to_c_common
from .stage_cd_common import common_to_stage_cd_result, simulate_stage_c_to_d_common
from .stage_de_dynamic import simulate_stage_d_to_e
from .stage_ef_dynamic import simulate_stage_e_to_f


@dataclass(frozen=True)
class ResidualEF:
    name: str
    contract: str
    value: float
    scale: float
    normalized: float
    units: str
    status: str
    interpretation: str


@dataclass(frozen=True)
class Block6M4Audit:
    event_e_time_s: float
    event_f_time_s: float | None
    event_f_reached: bool
    can_receive_without_projection: bool
    ef_exception: str | None
    max_residual_normalized: float
    failed_contracts: tuple[str, ...]
    residuals: tuple[ResidualEF, ...]
    ef_initial_state_source: str | None


def _film_thickness_from_volume(params, film_volume_m3: float) -> float:
    radius = params.geometry.tubing_diameter_m / 2.0
    area = film_volume_m3 / params.geometry.valve_depth_m
    return radius - sqrt(max(radius * radius - area / pi, 0.0))


def _add_residual(
    residuals: list[ResidualEF],
    *,
    name: str,
    contract: str,
    value: float,
    scale: float,
    units: str,
    tolerance: float,
    interpretation: str,
    status: str | None = None,
) -> None:
    scale = max(abs(scale), 1e-18)
    normalized = abs(float(value)) / scale
    residuals.append(
        ResidualEF(
            name=name,
            contract=contract,
            value=float(value),
            scale=float(scale),
            normalized=float(normalized),
            units=units,
            status=status or ("ok" if normalized <= tolerance else "fail"),
            interpretation=interpretation,
        )
    )


def build_corrected_e_state(params=None, *, max_step_s: float = 0.2):
    """Run the certified B->C, C->D and parallel corrected D->E chain."""
    p = params or santos_50_70_80()
    stage_ab = simulate_stage_1(p, max_step_s=max_step_s)
    stage_bc = simulate_stage_b_to_c_common(
        p, stage_a_b=stage_ab, rhs_mode="santos_compatible", max_step_s=max_step_s
    )
    stage_cd_common = simulate_stage_c_to_d_common(
        p, stage_b_c_common=stage_bc, rhs_mode="santos_corrected", max_step_s=max_step_s
    )
    stage_cd = common_to_stage_cd_result(stage_cd_common, p)
    stage_de = simulate_stage_d_to_e(p, stage_c_d=stage_cd, rhs_mode="santos_corrected", max_step_s=max_step_s)
    return p, stage_ab, stage_bc, stage_cd_common, stage_cd, stage_de


def audit_ef_boundary(params=None, *, max_step_s: float = 0.2) -> Block6M4Audit:
    p, _ab, _bc, _cd_common, _cd, de = build_corrected_e_state(params, max_step_s=max_step_s)
    residuals: list[ResidualEF] = []
    rho_l = initial_stage_1(p)["rho_l"]
    tubing_area_m2 = tubing_area(p.geometry.tubing_diameter_m)
    film_e = float(de.film_volume_m3[-1])
    y_e = _film_thickness_from_volume(p, film_e)
    gas_density_e = (
        float(de.gas_density_kg_m3[-1])
        if de.gas_density_kg_m3 is not None
        else float("nan")
    )
    film_velocity_e = (
        float(de.film_velocity_m_s[-1])
        if de.film_velocity_m_s is not None
        else float("nan")
    )
    radius = p.geometry.tubing_diameter_m / 2.0
    gas_area_e = pi * (radius - y_e) ** 2
    gas_velocity_scale = max(abs(float(de.v_b_m_s[-1])), 1.0)
    produced_e = float(de.produced_volume_m3[-1])
    fallback_e = float(de.fallback_volume_m3[-1])

    ef = None
    ef_exception: str | None = None
    try:
        ef = simulate_stage_e_to_f(p, stage_d_e=de, max_step_s=max_step_s)
    except Exception as exc:  # pragma: no cover - exercised only when audited model rejects E.
        ef_exception = f"{type(exc).__name__}: {exc}"

    if ef is None:
        _add_residual(
            residuals,
            name="ef_accepts_state",
            contract="simulate_stage_e_to_f(stage_d_e=D->E_santos_corrected) debe iniciar sin proyección",
            value=1.0,
            scale=1.0,
            units="adim.",
            tolerance=0.0,
            status="fail",
            interpretation=ef_exception or "E->F rechazó el estado E corregido.",
        )
        return Block6M4Audit(
            event_e_time_s=float(de.event_e_time_s),
            event_f_time_s=None,
            event_f_reached=False,
            can_receive_without_projection=False,
            ef_exception=ef_exception,
            max_residual_normalized=1.0,
            failed_contracts=tuple(r.name for r in residuals if r.status != "ok"),
            residuals=tuple(residuals),
            ef_initial_state_source=None,
        )

    _add_residual(
        residuals,
        name="rho_g_continuity",
        contract="rho_g(E+) - rho_g(E-) = 0",
        value=float(ef.gas_density_kg_m3[0]) - gas_density_e,
        scale=max(abs(gas_density_e), 1.0),
        units="kg/m3",
        tolerance=1e-8,
        interpretation="La densidad de gas debe pasar de D->E corregido a E->F por identidad.",
    )
    _add_residual(
        residuals,
        name="m_g_continuity",
        contract="m_g(E+) - m_g(E-) = 0",
        value=float(ef.gas_mass_kg[0]) - float(de.bubble_mass_kg[-1]),
        scale=max(abs(float(de.bubble_mass_kg[-1])), 1.0),
        units="kg",
        tolerance=1e-8,
        interpretation="La masa de gas debe conservarse en la transición E.",
    )
    _add_residual(
        residuals,
        name="P_t1_continuity",
        contract="P_t1(E+) - P_t1(E-) = 0",
        value=float(ef.tubing_pressure_pa[0]) - float(de.p_tubing_pa[-1]),
        scale=max(abs(float(de.p_tubing_pa[-1])), 1.0),
        units="Pa",
        tolerance=1e-8,
        interpretation="La presión de tubing inicial de E->F debe ser la presión final de D->E.",
    )
    _add_residual(
        residuals,
        name="v_g_memory",
        contract="v_g(E+) - v_g(E-) = 0 o transición documentada por Santos",
        value=float(ef.gas_velocity_m_s[0]) - float(de.v_b_m_s[-1]),
        scale=gas_velocity_scale,
        units="m/s",
        tolerance=1e-6,
        interpretation=(
            "El E->F vigente recalcula v_g desde descarga superficial; no transporta la "
            "velocidad integrada hasta E."
        ),
    )
    _add_residual(
        residuals,
        name="v_f_memory",
        contract="v_f(E+) - v_f(E-) = 0",
        value=float(ef.film_velocity_m_s[0]) - film_velocity_e,
        scale=max(abs(film_velocity_e), 1.0),
        units="m/s",
        tolerance=1e-6,
        interpretation=(
            "El E->F vigente reconstruye v_f algebraicamente con dv_f/dt=0; eso es una "
            "proyección respecto al estado con memoria entregado por D->E corregido."
        ),
    )
    _add_residual(
        residuals,
        name="y_geometry_continuity",
        contract="y(E+) - y(E-) = 0 por geometría de película",
        value=float(ef.film_thickness_m[0]) - y_e,
        scale=max(abs(y_e), 1e-6),
        units="m",
        tolerance=1e-8,
        interpretation="El espesor inicial se infiere del volumen de película y debe coincidir.",
    )
    _add_residual(
        residuals,
        name="m_film_continuity",
        contract="m_film(E+) - m_film(E-) = 0",
        value=float(ef.film_volume_m3[0]) * rho_l - film_e * rho_l,
        scale=max(abs(film_e * rho_l), 1.0),
        units="kg",
        tolerance=1e-8,
        interpretation="La masa de película debe conservarse en la frontera E.",
    )
    _add_residual(
        residuals,
        name="fallback_ledger_continuity",
        contract="fallback(E+) debe transportar fallback(E-) o documentar reinicio físico",
        value=fallback_e,
        scale=max(abs(fallback_e), 1.0),
        units="m3",
        tolerance=0.0,
        status="fail",
        interpretation=(
            "StageEFResult no expone un ledger de fallback; por tanto el fallback acumulado "
            "hasta E no puede continuar en E->F."
        ),
    )
    _add_residual(
        residuals,
        name="produced_ledger_continuity",
        contract="producido(E+) debe iniciar con el producido acumulado hasta E",
        value=float(ef.produced_film_volume_m3[0]) - produced_e,
        scale=max(abs(produced_e), 1.0),
        units="m3",
        tolerance=1e-8,
        interpretation=(
            "El E->F vigente inicia producido de etapa en cero; no conserva el ledger "
            "acumulado A->E."
        ),
    )
    _add_residual(
        residuals,
        name="glv_closed_no_reopen",
        contract="GLV cerrada en E y sin reapertura durante E->F",
        value=float(np.max(ef.valve_open.astype(float))),
        scale=1.0,
        units="booleano",
        tolerance=0.0,
        interpretation="La ruta E->F auditada mantiene la GLV cerrada.",
    )
    _add_residual(
        residuals,
        name="gas_inventory_balance",
        contract="m_g + integral(m_dot_superficie) = constante",
        value=float(ef.gas_balance_relative_error),
        scale=1.0,
        units="adim.",
        tolerance=1e-6,
        interpretation="Balance interno de gas reportado por el E->F vigente.",
    )
    liquid_e = film_e + produced_e + fallback_e
    liquid_ef_initial = float(ef.film_volume_m3[0]) + float(ef.produced_film_volume_m3[0])
    _add_residual(
        residuals,
        name="liquid_inventory_continuity",
        contract="inventario líquido acumulado(E+) - inventario líquido acumulado(E-) = 0",
        value=liquid_ef_initial - liquid_e,
        scale=max(abs(liquid_e), 1.0),
        units="m3",
        tolerance=1e-8,
        interpretation=(
            "El balance líquido de E->F es local a la etapa y no conserva producido/fallback "
            "acumulados hasta E."
        ),
    )
    descending = False
    if ef.event_f_reached and len(ef.film_velocity_m_s) >= 2:
        descending = bool(ef.film_velocity_m_s[-2] > ef.film_velocity_m_s[-1] >= -1e-8)
    _add_residual(
        residuals,
        name="event_f_descending",
        contract="F: v_f = 0 con cruce descendente",
        value=0.0 if ef.event_f_reached and descending else 1.0,
        scale=1.0,
        units="adim.",
        tolerance=0.0,
        interpretation="El evento terminal F debe ser cruce descendente de la velocidad de película.",
    )
    gas_volume_from_mg = float(de.bubble_mass_kg[-1]) / max(gas_density_e, 1e-18)
    _add_residual(
        residuals,
        name="gas_geometry_eos_consistency",
        contract="m_g/rho_g = A_g H en E",
        value=gas_volume_from_mg - gas_area_e * p.geometry.valve_depth_m,
        scale=max(abs(gas_area_e * p.geometry.valve_depth_m), 1e-12),
        units="m3",
        tolerance=1e-6,
        interpretation="Consistencia geométrica/EOS del estado E recibido.",
    )

    failed = tuple(r.name for r in residuals if r.status != "ok")
    max_norm = max((r.normalized for r in residuals), default=0.0)
    can_receive = not failed and "recovered algebraically" not in ef.initial_state_source.lower()
    return Block6M4Audit(
        event_e_time_s=float(de.event_e_time_s),
        event_f_time_s=float(ef.event_f_time_s) if ef.event_f_reached else None,
        event_f_reached=bool(ef.event_f_reached),
        can_receive_without_projection=bool(can_receive),
        ef_exception=ef_exception,
        max_residual_normalized=float(max_norm),
        failed_contracts=failed,
        residuals=tuple(residuals),
        ef_initial_state_source=ef.initial_state_source,
    )


def audit_summary(params=None, *, max_step_s: float = 0.2) -> dict[str, Any]:
    audit = audit_ef_boundary(params, max_step_s=max_step_s)
    return asdict(audit)


def run_block6m4_audit(params=None, *, max_step_s: float = 0.2) -> Block6M4Audit:
    return audit_ef_boundary(params, max_step_s=max_step_s)
