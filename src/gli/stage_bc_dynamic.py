"""Coupled conventional-GLI stage B->C (GLV open, motor valve open)."""

from dataclasses import dataclass
from math import pi, sqrt

import numpy as np
from scipy.integrate import solve_ivp

from .geometry import tubing_area
from .initial_conditions import GRAVITY_M_S2, initial_stage_1
from .parameters import GLIParameters
from .reference_gas import injected_gas_target_std_m3
from .stage1_dynamic import (
    Stage1Result,
    simulate_stage_1,
    standard_gas_density,
    state_from_mass,
)
from .valves import (
    motor_valve_gas_rate,
    santos_glv_mass_rate,
)


@dataclass(frozen=True)
class StageBCResult:
    time_s: np.ndarray
    annulus_mass_kg: np.ndarray
    bubble_mass_kg: np.ndarray
    h_b_m: np.ndarray
    h_l_m: np.ndarray
    slug_velocity_m_s: np.ndarray
    film_thickness_m: np.ndarray
    p_c1_pa: np.ndarray
    p_c2_pa: np.ndarray
    p_bubble_pa: np.ndarray
    motor_rate_std_m3_s: np.ndarray
    gl_mass_rate_kg_s: np.ndarray
    injected_volume_std_m3: np.ndarray
    target_volume_std_m3: float
    event_c_reached: bool
    event_c_time_s: float
    gas_balance_relative_error: float
    liquid_balance_relative_error: float


def _liquid_geometry(
    h_b: float, h_l: float, params: GLIParameters
) -> tuple[float, float, float]:
    """Return film thickness, bubble area and slug length from liquid balance."""
    diameter = params.geometry.tubing_diameter_m
    radius = 0.5 * diameter
    area_t = tubing_area(diameter)
    initial_length = params.geometry.initial_slug_length_m
    slug_length = max(h_l - h_b, 1.0e-6)
    if h_b <= 1.0e-9:
        film_area = area_t - area_t * (0.99**2)
    else:
        film_area = area_t * (initial_length - slug_length) / h_b
    film_area = float(np.clip(film_area, 0.0, 0.95 * area_t))
    bubble_area = area_t - film_area
    y = radius - sqrt(max(radius**2 - film_area / pi, 0.0))
    return y, bubble_area, slug_length


def _historical_glv_proxy_mass_rate(
    p_up: float, p_down: float, rho_up: float, params: GLIParameters
) -> float:
    """Historical pre-M1.7R proxy; retained only for reference regressions."""
    if p_up <= p_down:
        return 0.0
    return (
        params.valves.gas_lift_cd
        * params.valves.port_area_m2
        * sqrt(2.0 * rho_up * (p_up - p_down))
    )


def simulate_stage_b_to_c(
    params: GLIParameters,
    *,
    stage_a_b: Stage1Result | None = None,
    max_time_s: float = 180.0,
    max_step_s: float = 0.05,
    rtol: float = 1.0e-7,
    atol: float = 1.0e-9,
) -> StageBCResult:
    """Integrate B->C and stop when cumulative motor-valve volume reaches Vgi."""
    ab = stage_a_b or simulate_stage_1(params)
    if not ab.opened:
        raise ValueError("Stage A->B must reach valve opening")
    initial = initial_stage_1(params)
    gas = params.gas
    rho_std = standard_gas_density(params)
    target = injected_gas_target_std_m3(params)
    injected_b = float(
        (ab.annulus_gas_mass_kg[-1] - ab.annulus_gas_mass_kg[0]) / rho_std
    )
    seed_h = 1.0e-3
    area_t = tubing_area(params.geometry.tubing_diameter_m)
    seed_y = 0.01 * params.geometry.tubing_diameter_m
    seed_area = pi * (0.5 * params.geometry.tubing_diameter_m - seed_y) ** 2
    seed_volume = seed_area * seed_h
    seed_mass = (
        initial["p_to"]
        * gas.gas_molar_mass_kg_mol
        * seed_volume
        / (gas.z_t1 * gas.gas_constant_j_mol_k * gas.temp_t1_k)
    )
    m_c0 = float(ab.annulus_gas_mass_kg[-1] - seed_mass)
    h_l0 = params.geometry.initial_slug_length_m + (seed_area / area_t) * seed_h
    y0 = np.array([m_c0, seed_mass, seed_h, h_l0, 0.0152, injected_b], dtype=float)

    def values(state):
        m_c, m_b, h_b, h_l, v_l, _ = state
        casing = state_from_mass(float(m_c), params)
        film_y, area_b, slug_length = _liquid_geometry(float(h_b), float(h_l), params)
        volume_b = max(area_b * h_b, 1.0e-12)
        p_b = (
            m_b
            * gas.z_t1
            * gas.gas_constant_j_mol_k
            * gas.temp_t1_k
            / (gas.gas_molar_mass_kg_mol * volume_b)
        )
        rho_up = casing["rho_c2"]
        m_gl = santos_glv_mass_rate(casing["p_c2"], p_b, params)
        q_motor = motor_valve_gas_rate(
            casing["p_c1"],
            params.operating.injection_pressure_pa,
            params.fluids.gas_relative_density,
            gas.temp_c1_k,
            params.valves.motor_valve_cv,
        )
        return casing, film_y, area_b, slug_length, p_b, m_gl, q_motor

    def rhs(_t, state):
        m_c, m_b, h_b, h_l, v_l, _ = state
        casing, film_y, area_b, slug_length, p_b, m_gl, q_motor = values(state)
        rho_l = initial["rho_l"]
        friction = (
            params.coefficients.liquid_friction_factor
            * 0.5
            * rho_l
            * v_l
            * abs(v_l)
            * slug_length
            / params.geometry.tubing_diameter_m
        )
        acceleration = (
            p_b - initial["p_t3"] - rho_l * GRAVITY_M_S2 * slug_length - friction
        ) / (rho_l * slug_length)
        b = 0.35 * sqrt(GRAVITY_M_S2 * params.geometry.tubing_diameter_m)
        v_b = max(0.0, params.coefficients.bubble_velocity_a * v_l + b)
        return [rho_std * q_motor - m_gl, m_gl, v_b, v_l, acceleration, q_motor]

    def event_c(_t, state):
        return state[5] - target

    event_c.terminal = True
    event_c.direction = 1.0
    sol = solve_ivp(
        rhs,
        (0.0, max_time_s),
        y0,
        events=event_c,
        dense_output=True,
        max_step=max_step_s,
        rtol=rtol,
        atol=atol,
    )
    reached = bool(sol.t_events[0].size)
    end = float(sol.t_events[0][0]) if reached else float(sol.t[-1])
    times = np.linspace(0.0, end, max(2, int(np.ceil(end / max_step_s)) + 1))
    states = sol.sol(times)
    derived = [values(states[:, i]) for i in range(states.shape[1])]
    p_c1 = np.array([x[0]["p_c1"] for x in derived])
    p_c2 = np.array([x[0]["p_c2"] for x in derived])
    film = np.array([x[1] for x in derived])
    p_b = np.array([x[4] for x in derived])
    m_gl = np.array([x[5] for x in derived])
    q_m = np.array([x[6] for x in derived])
    total_gas = states[0] + states[1]
    expected = total_gas[0] + rho_std * (states[5] - states[5, 0])
    gas_error = float(
        np.max(np.abs(total_gas - expected))
        / max(abs(total_gas[-1] - total_gas[0]), 1.0)
    )
    liquid_vol = []
    for i, x in enumerate(derived):
        area_b = x[2]
        area_f = area_t - area_b
        liquid_vol.append(
            area_t * (states[3, i] - states[2, i]) + area_f * states[2, i]
        )
    liquid_error = float(
        np.max(
            np.abs(
                np.array(liquid_vol) - area_t * params.geometry.initial_slug_length_m
            )
        )
        / (area_t * params.geometry.initial_slug_length_m)
    )
    return StageBCResult(
        times,
        states[0],
        states[1],
        states[2],
        states[3],
        states[4],
        film,
        p_c1,
        p_c2,
        p_b,
        q_m,
        m_gl,
        states[5],
        target,
        reached,
        end,
        gas_error,
        liquid_error,
    )
