"""Coupled elevation stage C->D with motor valve closed."""

from dataclasses import dataclass
from math import sqrt

import numpy as np
from scipy.integrate import solve_ivp

from .fallback import fallback_rate_m3_s
from .geometry import tubing_area
from .initial_conditions import GRAVITY_M_S2, initial_stage_1
from .parameters import GLIParameters
from .stage1_dynamic import state_from_mass
from .stage_bc_dynamic import (
    StageBCResult,
    _historical_glv_proxy_mass_rate,
    simulate_stage_b_to_c,
)
from .valves import gas_lift_valve_resultant_force


@dataclass(frozen=True)
class StageCDResult:
    time_s: np.ndarray
    annulus_mass_kg: np.ndarray
    bubble_mass_kg: np.ndarray
    h_b_m: np.ndarray
    h_l_m: np.ndarray
    v_b_m_s: np.ndarray
    v_l_m_s: np.ndarray
    film_thickness_m: np.ndarray
    film_volume_m3: np.ndarray
    fallback_volume_m3: np.ndarray
    fallback_rate_m3_s: np.ndarray
    p_c1_pa: np.ndarray
    p_c2_pa: np.ndarray
    p_tubing_pa: np.ndarray
    p_bottom_pa: np.ndarray
    gl_mass_rate_kg_s: np.ndarray
    valve_force_n: np.ndarray
    valve_open: np.ndarray
    event_d_reached: bool
    event_d_time_s: float
    gas_balance_relative_error: float
    liquid_balance_relative_error: float
    canonical_states: np.ndarray | None = None
    bubble_friction_factor: float | None = None


def simulate_stage_c_to_d(
    params: GLIParameters,
    *,
    stage_b_c: StageBCResult | None = None,
    max_time_s: float = 400.0,
    max_step_s: float = 0.2,
    rtol: float = 1e-7,
    atol: float = 1e-9
) -> StageCDResult:
    """Continue the exact final C state until the slug top reaches surface D."""
    bc = stage_b_c or simulate_stage_b_to_c(params)
    if not bc.event_c_reached:
        raise ValueError("Stage B->C must reach C")
    initial = initial_stage_1(params)
    gas = params.gas
    area_t = tubing_area(params.geometry.tubing_diameter_m)
    y0 = np.array(
        [
            bc.annulus_mass_kg[-1],
            bc.bubble_mass_kg[-1],
            bc.h_b_m[-1],
            bc.h_l_m[-1],
            bc.slug_velocity_m_s[-1],
            0.0,
        ],
        dtype=float,
    )

    def values(state):
        m_c, m_b, h_b, h_l, v_l, v_fallback = state
        casing = state_from_mass(float(m_c), params)
        slug_length = max(h_l - h_b, 0.0)
        total_liquid = area_t * params.geometry.initial_slug_length_m
        film_volume = max(total_liquid - v_fallback - area_t * slug_length, 0.0)
        film_area = film_volume / max(h_b, 1e-12)
        film_area = float(np.clip(film_area, 0.0, 0.95 * area_t))
        area_b = area_t - film_area
        radius = params.geometry.tubing_diameter_m / 2
        film_y = radius - sqrt(max(radius**2 - film_area / np.pi, 0.0))
        volume_b = max(area_b * h_b, 1e-12)
        p_b = (
            m_b
            * gas.z_t1
            * gas.gas_constant_j_mol_k
            * gas.temp_t1_k
            / (gas.gas_molar_mass_kg_mol * volume_b)
        )
        # After opening, tubing-side force uses the instantaneous Pt1=Pb;
        # Pto is only the opening-condition value used at B.
        force = gas_lift_valve_resultant_force(
            casing["p_c2"],
            initial["p_bt"],
            p_b,
            params.valves.rv,
            params.valves.bellows_area_m2,
        )
        is_open = force >= -1e-6
        m_gl = (
            _historical_glv_proxy_mass_rate(
                casing["p_c2"], p_b, casing["rho_c2"], params
            )
            if is_open
            else 0.0
        )
        b = 0.35 * sqrt(GRAVITY_M_S2 * params.geometry.tubing_diameter_m)
        v_b = max(0.0, params.coefficients.bubble_velocity_a * v_l + b)
        p_bottom = p_b + initial["rho_l"] * GRAVITY_M_S2 * max(
            (params.geometry.perforation_depth_m or params.geometry.valve_depth_m)
            - params.geometry.valve_depth_m,
            0.0,
        )
        q_fallback = fallback_rate_m3_s(
            params.geometry.tubing_diameter_m,
            film_y,
            initial["rho_l"],
            params.fluids.liquid_viscosity_pa_s,
            film_volume,
        )
        return (
            casing,
            film_y,
            area_b,
            slug_length,
            p_b,
            p_bottom,
            force,
            is_open,
            m_gl,
            v_b,
            film_volume,
            q_fallback,
        )

    def rhs(_t, state):
        m_c, m_b, h_b, h_l, v_l, v_fallback = state
        x = values(state)
        slug_length = x[3]
        p_b = x[4]
        m_gl = x[8]
        v_b = x[9]
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
        return [-m_gl, m_gl, v_b, v_l, acceleration, x[11]]

    def event_d(_t, state):
        return state[3] - params.geometry.valve_depth_m

    event_d.terminal = True
    event_d.direction = 1.0
    sol = solve_ivp(
        rhs,
        (0, max_time_s),
        y0,
        events=event_d,
        dense_output=True,
        max_step=max_step_s,
        rtol=rtol,
        atol=atol,
    )
    reached = bool(sol.t_events[0].size)
    end = float(sol.t_events[0][0]) if reached else float(sol.t[-1])
    times = np.linspace(0, end, max(2, int(np.ceil(end / max_step_s)) + 1))
    states = sol.sol(times)
    derived = [values(states[:, i]) for i in range(states.shape[1])]
    p_c1 = np.array([x[0]["p_c1"] for x in derived])
    p_c2 = np.array([x[0]["p_c2"] for x in derived])
    film = np.array([x[1] for x in derived])
    p_t = np.array([x[4] for x in derived])
    p_bottom = np.array([x[5] for x in derived])
    forces = np.array([x[6] for x in derived])
    opened = np.array([x[7] for x in derived])
    m_gl = np.array([x[8] for x in derived])
    vb = np.array([x[9] for x in derived])
    film_volume = np.array([x[10] for x in derived])
    fallback = states[5]
    fallback_rate = np.array([x[11] for x in derived])
    total_gas = states[0] + states[1]
    gas_error = float(np.max(np.abs(total_gas - total_gas[0])) / max(total_gas[0], 1.0))
    liquid = []
    for i, x in enumerate(derived):
        liquid.append(
            area_t * (states[3, i] - states[2, i]) + film_volume[i] + fallback[i]
        )
    target_liquid = area_t * params.geometry.initial_slug_length_m
    liquid_error = float(
        np.max(np.abs(np.array(liquid) - target_liquid)) / target_liquid
    )
    return StageCDResult(
        times,
        states[0],
        states[1],
        states[2],
        states[3],
        vb,
        states[4],
        film,
        film_volume,
        fallback,
        fallback_rate,
        p_c1,
        p_c2,
        p_t,
        p_bottom,
        m_gl,
        forces,
        opened,
        reached,
        end,
        gas_error,
        liquid_error,
    )
