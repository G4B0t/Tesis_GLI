"""Block 6M-3 audit for the D->E production stage.

This module deliberately does not certify or reconnect D->E.  It measures the
legacy D->E implementation against the Santos stage-3 transition requirements
after the 6M-2D corrected B->C->D chain.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from math import pi, sqrt
import numpy as np

from .base_case import santos_50_70_80
from .geometry import tubing_area
from .initial_conditions import initial_stage_1
from .stage1_dynamic import simulate_stage_1
from .stage_bc_common import simulate_stage_b_to_c_common
from .stage_cd_common import (
    I_FB,
    I_HB,
    I_HL,
    I_MFILM,
    I_MG,
    I_PG,
    I_PROD,
    I_RHO,
    I_VF,
    I_VG,
    I_VL,
    I_Y,
    common_to_stage_cd_result,
    simulate_stage_c_to_d_common,
)
from .stage_de_dynamic import simulate_stage_d_to_e


@dataclass(frozen=True)
class ResidualD:
    name: str
    equation: str
    value: float
    scale: float
    normalized: float
    units: str
    status: str
    interpretation: str


@dataclass(frozen=True)
class Block6M3Audit:
    event_d_time_s: float
    event_e_time_s: float
    produced_volume_m3: float
    legacy_liquid_balance_error: float
    corrected_inventory_residual_m3: float
    reservoir_missing_m3: float
    glv_open_at_d: bool
    glv_open_any_de: bool
    glv_mass_rate_start_kg_s: float
    corrected_event_e_time_s: float
    corrected_produced_volume_m3: float
    corrected_liquid_balance_error: float
    corrected_reservoir_residual_m3: float
    corrected_glv_open_any: bool
    corrected_film_velocity_jump_m_s: float
    max_residual_normalized: float
    corrected_max_residual_normalized: float
    certified: bool
    corrected_certified: bool
    residuals: tuple[ResidualD, ...]
    corrected_residuals: tuple[ResidualD, ...]


def _areas(params, y):
    D = params.geometry.tubing_diameter_m
    r = D / 2.0
    At = tubing_area(D)
    Ab = pi * (r - y) ** 2
    Af = At - Ab
    return r, At, Ab, Af


def liquid_inventory_common(params, state) -> float:
    rho_l = initial_stage_1(params)["rho_l"]
    At = tubing_area(params.geometry.tubing_diameter_m)
    return (
        At * (float(state[I_HL]) - float(state[I_HB]))
        + float(state[I_MFILM]) / rho_l
        + float(state[I_FB])
        + float(state[I_PROD])
    )


def compatibility_residuals_d(params, cd_common, de_legacy) -> tuple[ResidualD, ...]:
    """Residual vector at D and over D->E for Santos stage 3."""
    sD = cd_common.final_state
    ini = initial_stage_1(params)
    rho_l = ini["rho_l"]
    gas = params.gas
    H = params.geometry.valve_depth_m
    r, At, Ab, Af = _areas(params, float(sD[I_Y]))
    Vg = Ab * float(sD[I_HB])
    peos = float(sD[I_MG]) * gas.z_t1 * gas.gas_constant_j_mol_k * gas.temp_t1_k / (
        gas.gas_molar_mass_kg_mol * max(Vg, 1e-18)
    )
    current_inventory = (
        de_legacy.slug_volume_m3
        + de_legacy.film_volume_m3
        + de_legacy.fallback_volume_m3
        + de_legacy.produced_volume_m3
    )
    expected_with_reservoir = current_inventory[0] + params.operating.reservoir_liquid_rate_m3_s * de_legacy.time_s
    expected_no_reservoir = np.full_like(current_inventory, current_inventory[0])
    missing_reservoir = float(expected_with_reservoir[-1] - current_inventory[-1])

    items: list[ResidualD] = []

    def add(name, equation, value, scale, units, status, interpretation):
        scale = max(abs(scale), 1e-18)
        items.append(
            ResidualD(
                name,
                equation,
                float(value),
                float(scale),
                float(abs(value) / scale),
                units,
                status,
                interpretation,
            )
        )

    add(
        "top_boundary",
        "Etapa 3: h_l = z_v = H",
        float(sD[I_HL]) - H,
        H,
        "m",
        "ok",
        "El evento D fija el tope de la golfada en superficie.",
    )
    add(
        "gas_eos_D",
        "P_t1 - m_g ZRT/(M A_B h_B) = 0",
        float(sD[I_PG]) - peos,
        peos,
        "Pa",
        "ok",
        "Masa, densidad y presión de gas llegan cerradas desde C->D.",
    )
    add(
        "film_geometry_D",
        "m_f/rho_l - A_f h_B = 0",
        float(sD[I_MFILM]) / rho_l - Af * float(sD[I_HB]),
        max(Af * float(sD[I_HB]), 1e-12),
        "m3",
        "ok",
        "La película en D es geométrica y continua.",
    )
    add(
        "slug_mass_D",
        "4.1.40: A_t v_l - A_f v_f - A_B v_B = 0",
        At * float(sD[I_VL]) - Af * float(sD[I_VF]) - Ab * float(sD[I_VG]),
        max(abs(At * float(sD[I_VL])), abs(Af * float(sD[I_VF])), abs(Ab * float(sD[I_VG])), 1e-12),
        "m3/s",
        "ok",
        "La restricción de masa de etapa 3 llega satisfecha desde C->D corregido.",
    )
    add(
        "memory_vf_missing",
        "Transferencia D: v_f debe continuar como estado",
        float(de_legacy.fallback_volume_m3[0]) - float(sD[I_VF]),
        max(abs(float(sD[I_VF])), 1.0),
        "m/s vs m3",
        "fail",
        "El legado usa el ledger de fallback como estado escalar; no transporta v_f.",
    )
    add(
        "memory_rho_missing",
        "Transferencia D: rho_g debe continuar como estado",
        float(sD[I_RHO]) - float(sD[I_MG]) / max(Ab * float(sD[I_HB]), 1e-18),
        max(abs(float(sD[I_RHO])), 1.0),
        "kg/m3",
        "ok",
        "rho_g existe en el vector común, pero el contrato legado D->E no la expone.",
    )
    add(
        "reservoir_stage3",
        "Santos etapa 3: q_res sigue acumulándose en la película",
        float(np.max(np.abs(current_inventory - expected_with_reservoir))),
        max(abs(expected_with_reservoir[-1]), 1.0),
        "m3",
        "fail",
        "El inventario legado no aumenta con q_res durante toda la descarga.",
    )
    add(
        "legacy_balance_metric",
        "Balance D->E debe usar inventario en D, no solo A_t L inicial",
        float(de_legacy.liquid_balance_relative_error),
        1.0,
        "adim.",
        "fail",
        "La métrica heredada compara contra el volumen inicial de golfada y queda inválida tras B->D con q_res.",
    )
    add(
        "glv_boundary",
        "D->E: GLV no debe reabrir sin evento mecánico/histéresis compatible",
        float(de_legacy.gl_mass_rate_kg_s[0]),
        max(abs(float(de_legacy.gl_mass_rate_kg_s[0])), 1e-12),
        "kg/s",
        "fail" if bool(de_legacy.valve_open[0]) else "ok",
        "El legado permite GLV abierta al inicio de D->E; debe enclavarse/cerrarse antes de certificar.",
    )
    add(
        "event_E",
        "E: h_B - H = 0",
        float(de_legacy.h_b_m[-1] - H),
        H,
        "m",
        "ok",
        "El evento geométrico E sí se detecta.",
    )
    return tuple(items)


def corrected_residuals_d(params, cd_common, de_corrected) -> tuple[ResidualD, ...]:
    """Residual vector for the parallel corrected D->E route."""
    sD = cd_common.final_state
    ini = initial_stage_1(params)
    rho_l = ini["rho_l"]
    r, At, Ab, Af = _areas(params, float(sD[I_Y]))
    inventory = (
        de_corrected.slug_volume_m3
        + de_corrected.film_volume_m3
        + de_corrected.fallback_volume_m3
        + de_corrected.produced_volume_m3
    )
    if de_corrected.reservoir_accumulated_m3 is None:
        raise ValueError("corrected D->E result must expose its dynamic reservoir ledger")
    expected = inventory[0] + de_corrected.reservoir_accumulated_m3
    vf0 = float(de_corrected.film_velocity_m_s[0]) if de_corrected.film_velocity_m_s is not None else float("nan")
    rho0 = float(de_corrected.gas_density_kg_m3[0]) if de_corrected.gas_density_kg_m3 is not None else float("nan")
    residuals = []

    def add(name, equation, value, scale, units, status, interpretation):
        scale = max(abs(scale), 1e-18)
        residuals.append(ResidualD(name, equation, float(value), float(scale), float(abs(value)/scale), units, status, interpretation))

    vf_scale = max(abs(float(sD[I_VF])), 1.0)
    add("vf_memory", "v_f(D+) - v_f(D-) = 0", vf0 - float(sD[I_VF]), vf_scale, "m/s",
        "ok" if abs(vf0 - float(sD[I_VF])) / vf_scale <= 1e-6 else "fail",
        "La ruta corregida transporta v_f como estado inicial de película.")
    add("rho_memory", "rho_g(D+) - rho_g(D-) = 0", rho0 - float(sD[I_RHO]), max(abs(float(sD[I_RHO])), 1.0), "kg/m3",
        "ok" if abs(rho0 - float(sD[I_RHO]))/max(abs(float(sD[I_RHO])),1.0) <= 1e-8 else "fail",
        "La densidad de gas se conserva en la frontera D.")
    add("reservoir_balance", "I_liq(t) - [I_D + q_res t] = 0", float(np.max(np.abs(inventory - expected))), max(abs(expected[-1]), 1.0), "m3",
        "ok" if float(np.max(np.abs(inventory - expected))) <= 1e-8 else "fail",
        "El inventario total usa el volumen correcto en D más aporte de reservorio.")
    add("glv_latched_closed", "m_glv(D->E) = 0", float(np.max(np.abs(de_corrected.gl_mass_rate_kg_s))), 1.0, "kg/s",
        "ok" if not bool(de_corrected.valve_open.any()) and float(np.max(np.abs(de_corrected.gl_mass_rate_kg_s))) <= 1e-12 else "fail",
        "La GLV queda cerrada/enclavada en la ruta corregida.")
    add("event_E", "h_B(E)-H=0", float(de_corrected.h_b_m[-1] - params.geometry.valve_depth_m), params.geometry.valve_depth_m, "m",
        "ok" if de_corrected.event_e_reached else "fail",
        "El evento terminal E se detecta en la base de la golfada.")
    add("film_geometry_E", "film_volume(E) >= 0", min(float(np.min(de_corrected.film_volume_m3)), 0.0), max(float(np.max(de_corrected.film_volume_m3)), 1.0), "m3",
        "ok" if np.all(de_corrected.film_volume_m3 >= -1e-10) else "fail",
        "La película permanece positiva durante D->E corregido.")
    return tuple(residuals)


def run_block6m3_audit(max_step_s: float = 0.5) -> Block6M3Audit:
    params = santos_50_70_80()
    ab = simulate_stage_1(params, max_step_s=max_step_s)
    bc = simulate_stage_b_to_c_common(
        params, stage_a_b=ab, max_step_s=max_step_s, rhs_mode="santos_compatible"
    )
    cd_common = simulate_stage_c_to_d_common(
        params, stage_b_c_common=bc, max_step_s=max_step_s, rhs_mode="santos_corrected"
    )
    cd_legacy_view = common_to_stage_cd_result(cd_common, params)
    de = simulate_stage_d_to_e(params, stage_c_d=cd_legacy_view, max_step_s=max_step_s)
    de_corrected = simulate_stage_d_to_e(
        params, stage_c_d=cd_legacy_view, max_step_s=max_step_s,
        rhs_mode="santos_corrected")
    residuals = compatibility_residuals_d(params, cd_common, de)
    corrected_residuals = corrected_residuals_d(params, cd_common, de_corrected)
    current_inventory = de.slug_volume_m3 + de.film_volume_m3 + de.fallback_volume_m3 + de.produced_volume_m3
    expected_with_reservoir = current_inventory[0] + params.operating.reservoir_liquid_rate_m3_s * de.time_s
    corrected_inventory = (
        de_corrected.slug_volume_m3 + de_corrected.film_volume_m3
        + de_corrected.fallback_volume_m3 + de_corrected.produced_volume_m3)
    if de_corrected.reservoir_accumulated_m3 is None:
        raise ValueError("corrected D->E result must expose its dynamic reservoir ledger")
    corrected_expected = corrected_inventory[0] + de_corrected.reservoir_accumulated_m3
    max_norm = max(r.normalized for r in residuals)
    corrected_max_norm = max(r.normalized for r in corrected_residuals)
    certified = bool(
        de.event_e_reached
        and max_norm < 1e-6
        and not bool(de.valve_open.any())
        and de.gas_balance_relative_error < 1e-6
    )
    corrected_certified = bool(
        de_corrected.event_e_reached
        and corrected_max_norm < 1e-6
        and de_corrected.gas_balance_relative_error < 1e-6
        and de_corrected.liquid_balance_relative_error < 1e-8
        and not bool(de_corrected.valve_open.any())
    )
    return Block6M3Audit(
        cd_common.event_d_time_s,
        de.event_e_time_s,
        float(de.produced_volume_m3[-1]),
        de.liquid_balance_relative_error,
        float(current_inventory[-1] - current_inventory[0]),
        float(expected_with_reservoir[-1] - current_inventory[-1]),
        bool(cd_common.glv_open[-1]),
        bool(de.valve_open.any()),
        float(de.gl_mass_rate_kg_s[0]),
        de_corrected.event_e_time_s,
        float(de_corrected.produced_volume_m3[-1]),
        de_corrected.liquid_balance_relative_error,
        float(np.max(np.abs(corrected_inventory - corrected_expected))),
        bool(de_corrected.valve_open.any()),
        float(abs(de_corrected.film_velocity_m_s[0] - cd_common.final_state[I_VF])),
        max_norm,
        corrected_max_norm,
        certified,
        corrected_certified,
        residuals,
        corrected_residuals,
    )


def audit_summary(max_step_s: float = 0.5):
    audit = run_block6m3_audit(max_step_s=max_step_s)
    out = asdict(audit)
    out["residuals"] = [asdict(r) for r in audit.residuals]
    return out


if __name__ == "__main__":
    import json

    print(json.dumps(audit_summary(), indent=2))
