"""Block 6M-2D compatibility residuals at the C transition.

The residual vector is intentionally independent from solver certification:
it checks whether the memory state delivered by B->C lies on the Santos
elevation manifold required by the corrected C->D RHS.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import pi
import numpy as np

from .geometry import tubing_area
from .initial_conditions import initial_stage_1
from .parameters import GLIParameters
from .stage_bc_common import (
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
    I_VGI,
    I_VL,
    I_Y,
)
from .stage_cd_common import _cd_terms_santos, simulate_stage_c_to_d_common
from .reservoir import reservoir_inflow_from_pt1


@dataclass(frozen=True)
class CompatibilityResidual:
    name: str
    equation: str
    value: float
    scale: float
    normalized: float
    units: str
    classification: str
    must_hold_during_bc: bool
    can_change_at_c: bool
    interpretation: str


@dataclass(frozen=True)
class CompatibilityAuditC:
    residuals: tuple[CompatibilityResidual, ...]
    max_normalized: float
    compatible: bool
    liquid_inventory_m3: float
    gas_eos_pressure_pa: float
    state_classification: dict[str, str]


STATE_CLASSIFICATION = {
    "m_c": "variable dinamica continua",
    "m_g": "variable dinamica continua",
    "rho_g": "variable dinamica continua",
    "P_g/P_t1": "variable dinamica continua",
    "v_g/v_B": "variable dinamica continua con cierre algebraico v_B=a v_l+b",
    "v_f": "variable dinamica continua; tambien restringida por 4.1.39",
    "y": "variable dinamica continua/geometrica",
    "m_film": "variable dinamica continua/geometrica",
    "h_B": "variable dinamica continua",
    "h_L": "variable dinamica continua",
    "v_l": "variable dinamica continua",
    "V_gi": "condicion de evento/transicion C",
    "fallback": "variable diagnostica/ledger",
    "producido": "variable diagnostica",
}


def _geom(params: GLIParameters, state: np.ndarray):
    D = params.geometry.tubing_diameter_m
    r = D / 2.0
    At = tubing_area(D)
    y = float(state[I_Y])
    Ab = pi * (r - y) ** 2
    Af = At - Ab
    return r, At, Ab, Af


def compatibility_residuals_c(
    params: GLIParameters,
    state: np.ndarray,
    *,
    target_vgi_std_m3: float | None = None,
    tolerance: float = 1e-6,
) -> CompatibilityAuditC:
    """Build R_C from Santos constraints shared by B->C and C->D."""
    ini = initial_stage_1(params)
    rho_l = ini["rho_l"]
    g = params.gas
    r, At, Ab, Af = _geom(params, state)
    hb = float(state[I_HB])
    hl = float(state[I_HL])
    vl = float(state[I_VL])
    vg = float(state[I_VG])
    vf = float(state[I_VF])
    y = float(state[I_Y])
    mg = float(state[I_MG])
    rho = float(state[I_RHO])
    pg = float(state[I_PG])
    qres = reservoir_inflow_from_pt1(params, pg, rho_l).rate_m3_s
    d, _, _ = _cd_terms_santos(state, params, True)

    Vg = Ab * hb
    peos = mg * g.z_t1 * g.gas_constant_j_mol_k * g.temp_t1_k / (
        g.gas_molar_mass_kg_mol * max(Vg, 1e-18)
    )
    film_geom = Af * hb
    slug_geom = At * (hl - hb)
    liquid_inventory = slug_geom + float(state[I_MFILM]) / rho_l + float(state[I_FB]) + float(state[I_PROD])

    items: list[CompatibilityResidual] = []

    def add(name, equation, value, scale, units, classification, must_hold, can_change, interpretation):
        scale = max(abs(scale), 1e-18)
        items.append(
            CompatibilityResidual(
                name,
                equation,
                float(value),
                float(scale),
                float(abs(value) / scale),
                units,
                classification,
                bool(must_hold),
                bool(can_change),
                interpretation,
            )
        )

    add(
        "slug_mass_algebraic",
        "4.1.39: A_t v_l - A_f v_f - A_B v_B = 0",
        At * vl - Af * vf - Ab * vg,
        max(abs(At * vl), abs(Af * vf), abs(Ab * vg), 1e-12),
        "m3/s",
        "cierre algebraico",
        True,
        False,
        "Debe ser transportado por B->C; imponerlo en C seria una proyeccion de velocidades con memoria.",
    )
    add(
        "bubble_velocity_closure",
        "4.1.49: v_B - a v_l - b = 0",
        vg - params.coefficients.bubble_velocity_a * vl - 0.35 * (9.80665 * params.geometry.tubing_diameter_m) ** 0.5,
        max(abs(vg), 1.0),
        "m/s",
        "cierre algebraico",
        True,
        False,
        "La relacion Brown debe cumplirse durante la elevacion, no solo despues de C.",
    )
    add(
        "film_mass_geometry",
        "4.1.29/4.1.35: m_f/rho_l - A_f h_B = 0",
        float(state[I_MFILM]) / rho_l - film_geom,
        max(abs(film_geom), 1e-12),
        "m3",
        "cierre geometrico",
        True,
        False,
        "La pelicula es inventario geometrico; no debe compensarse con fallback en C.",
    )
    add(
        "gas_eos",
        "EOS: P_t1 - m_g ZRT/(M A_B h_B) = 0",
        pg - peos,
        max(abs(peos), 1.0),
        "Pa",
        "cierre constitutivo",
        True,
        False,
        "Gas, densidad y presion tienen memoria y deben llegar integrados a C.",
    )
    add(
        "gas_density_geometry",
        "rho_g - m_g/(A_B h_B) = 0",
        rho - mg / max(Vg, 1e-18),
        max(abs(rho), 1.0),
        "kg/m3",
        "cierre constitutivo",
        True,
        False,
        "Equivalente dimensional de masa/densidad de gas.",
    )
    add(
        "event_c_volume",
        "C: V_gi - V_gi,target = 0",
        0.0 if target_vgi_std_m3 is None else float(state[I_VGI]) - target_vgi_std_m3,
        max(abs(target_vgi_std_m3 or float(state[I_VGI])), 1.0),
        "m3 std",
        "condicion de evento/transicion",
        True,
        True,
        "En C solo cambia el control de la valvula motora; no justifica reinicializar estados.",
    )
    add(
        "kinematic_hB",
        "4.1.33: dh_B/dt - v_B = 0",
        float(d[I_HB]) - vg,
        max(abs(vg), 1.0),
        "m/s",
        "restriccion diferencial",
        True,
        False,
        "La cinemática debe ser la misma a ambos lados de C.",
    )
    add(
        "kinematic_hL",
        "4.1.32: dh_L/dt - v_l = 0",
        float(d[I_HL]) - vl,
        max(abs(vl), 1.0),
        "m/s",
        "restriccion diferencial",
        True,
        False,
        "El aporte del reservorio entra por el balance, no sumando q_res/A_t a h_L en C->D.",
    )
    add(
        "film_mass_differential",
        "4.1.35: 2pi(r-y)h_B dy/dt + A_f v_f - q_res = 0",
        2 * pi * (r - y) * hb * float(d[I_Y]) + Af * vf - qres,
        max(abs(qres), abs(Af * vf), 1e-12),
        "m3/s",
        "restriccion diferencial",
        True,
        False,
        "Si falla en C, B->C no transporto la ecuacion de pelicula requerida.",
    )
    add(
        "slug_mass_differential",
        "d/dt(4.1.39)=0 bajo el RHS corregido",
        At * float(d[I_VL])
        - (2 * pi * (r - y) * float(d[I_Y])) * vf
        - Af * float(d[I_VF])
        + (2 * pi * (r - y) * float(d[I_Y])) * vg
        - Ab * float(d[I_VG]),
        max(abs(At * float(d[I_VL])), abs(Af * float(d[I_VF])), 1e-12),
        "m3/s2",
        "restriccion diferencial",
        True,
        False,
        "La derivada del cierre tambien debe anularse para no crear salto dinamico.",
    )
    add(
        "position_order",
        "0 < h_B <= h_L <= H",
        max(0.0, -hb) + max(0.0, hb - hl) + max(0.0, hl - params.geometry.valve_depth_m),
        max(params.geometry.valve_depth_m, 1.0),
        "m",
        "factibilidad fisica",
        True,
        False,
        "Orden geometrico de burbuja y golfada.",
    )
    add(
        "film_thickness_bounds",
        "0 < y < r",
        max(0.0, -y) + max(0.0, y - r),
        max(r, 1e-12),
        "m",
        "factibilidad fisica",
        True,
        False,
        "El espesor de pelicula es geometrico.",
    )

    max_norm = max(x.normalized for x in items)
    compatible = bool(max_norm <= tolerance)
    return CompatibilityAuditC(
        tuple(items),
        max_norm,
        compatible,
        liquid_inventory,
        peos,
        STATE_CLASSIFICATION,
    )


def compare_c_states(params: GLIParameters, inherited_result, compatible_result):
    """Return compatibility audits for current and Santos-compatible B->C states."""
    target = getattr(inherited_result, "target_volume_std_m3", None)
    current = compatibility_residuals_c(params, inherited_result.final_state, target_vgi_std_m3=target)
    candidate = compatibility_residuals_c(params, compatible_result.final_state, target_vgi_std_m3=target)
    return current, candidate


def corrected_cd_from_compatible_bc(params: GLIParameters, compatible_bc, **kwargs):
    """Run C->D corrected RHS from a compatibility-certified B->C result."""
    return simulate_stage_c_to_d_common(
        params,
        stage_b_c_common=compatible_bc,
        rhs_mode="santos_corrected",
        **kwargs,
    )
