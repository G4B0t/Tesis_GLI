"""Dynamic gas-injection stage A->B for conventional intermittent gas lift."""

from dataclasses import dataclass
from typing import Sequence

import numpy as np
from scipy.integrate import solve_ivp

from .initial_conditions import GRAVITY_M_S2, initial_stage_1
from .parameters import GLIParameters
from .valves import gas_lift_valve_resultant_force, motor_valve_gas_rate


@dataclass(frozen=True)
class Stage1Result:
    """Time history ending at the gas-lift-valve opening event B."""
    time_s: np.ndarray
    annulus_gas_mass_kg: np.ndarray
    p_c1_pa: np.ndarray
    p_c2_pa: np.ndarray
    rho_c1_kg_m3: np.ndarray
    rho_c2_kg_m3: np.ndarray
    standard_gas_rate_m3_s: np.ndarray
    resultant_force_n: np.ndarray
    opened: bool
    opening_time_s: float
    mass_balance_relative_error: float


def casing_pressure_ratio(params: GLIParameters) -> float:
    """Return Pc2/Pc1 from Santos 4.1.17 / basic equation b2."""
    gas = params.gas
    mean_temperature = 0.5 * (gas.temp_c1_k + gas.temp_c2_k)
    exponent = gas.gas_molar_mass_kg_mol * GRAVITY_M_S2 * params.geometry.valve_depth_m / (
        gas.z_tc * gas.gas_constant_j_mol_k * mean_temperature
    )
    return float(np.exp(exponent))


def annulus_mass_coefficient(params: GLIParameters) -> float:
    """Coefficient C_m in m_tc=C_m Pc1 from Santos 4.1.6, 4.1.18-19."""
    gas = params.gas
    ratio = casing_pressure_ratio(params)
    volume = params.geometry.annulus_cross_area_m2 * params.geometry.valve_depth_m
    return volume * gas.gas_molar_mass_kg_mol / (2.0 * gas.gas_constant_j_mol_k) * (
        1.0 / (gas.z_c1 * gas.temp_c1_k)
        + ratio / (gas.z_c2 * gas.temp_c2_k)
    )


def state_from_mass(mass_kg: float, params: GLIParameters) -> dict[str, float]:
    """Recover casing pressures and densities from the conservative state."""
    gas = params.gas
    p_c1 = mass_kg / annulus_mass_coefficient(params)
    p_c2 = p_c1 * casing_pressure_ratio(params)
    return {
        "p_c1": p_c1,
        "p_c2": p_c2,
        "rho_c1": p_c1 * gas.gas_molar_mass_kg_mol / (gas.z_c1 * gas.gas_constant_j_mol_k * gas.temp_c1_k),
        "rho_c2": p_c2 * gas.gas_molar_mass_kg_mol / (gas.z_c2 * gas.gas_constant_j_mol_k * gas.temp_c2_k),
    }


def standard_gas_density(params: GLIParameters) -> float:
    """Gas density at the explicitly declared standard state."""
    gas = params.gas
    return gas.standard_pressure_pa * gas.gas_molar_mass_kg_mol / (
        gas.gas_constant_j_mol_k * gas.standard_temperature_k
    )


def simulate_stage_1(
    params: GLIParameters, *, max_time_s: float = 300.0,
    max_step_s: float = 0.25, rtol: float = 1.0e-8,
    atol: float = 1.0e-10, sample_times_s: Sequence[float] | None = None,
) -> Stage1Result:
    """Integrate A->B and stop at the upward zero crossing of valve force."""
    initial = initial_stage_1(params)
    rho_std = standard_gas_density(params)

    def mass_rate(_time: float, y: np.ndarray) -> list[float]:
        state = state_from_mass(float(y[0]), params)
        q_std = motor_valve_gas_rate(
            state["p_c1"], params.operating.injection_pressure_pa,
            params.fluids.gas_relative_density, params.gas.temp_c1_k,
            params.valves.motor_valve_cv,
        )
        return [rho_std * q_std]

    def opening_event(_time: float, y: np.ndarray) -> float:
        state = state_from_mass(float(y[0]), params)
        return gas_lift_valve_resultant_force(
            state["p_c2"], initial["p_bt"], initial["p_to"],
            params.valves.rv, params.valves.bellows_area_m2,
        )

    opening_event.terminal = True
    opening_event.direction = 1.0
    solution = solve_ivp(
        mass_rate, (0.0, max_time_s), [initial["m_tc"]],
        events=opening_event, dense_output=True, max_step=max_step_s,
        rtol=rtol, atol=atol,
    )
    opened = bool(solution.t_events[0].size)
    opening_time = float(solution.t_events[0][0]) if opened else float(solution.t[-1])
    if sample_times_s is None:
        count = max(2, int(np.ceil(opening_time / max_step_s)) + 1)
        times = np.linspace(0.0, opening_time, count)
    else:
        times = np.asarray(sample_times_s, dtype=float)
        if np.any(times < 0.0) or np.any(times > opening_time + 1.0e-9):
            raise ValueError("sample_times_s must lie inside the simulated A->B interval")

    masses = solution.sol(times)[0]
    states = [state_from_mass(float(m), params) for m in masses]
    p_c1 = np.array([s["p_c1"] for s in states])
    p_c2 = np.array([s["p_c2"] for s in states])
    rho_c1 = np.array([s["rho_c1"] for s in states])
    rho_c2 = np.array([s["rho_c2"] for s in states])
    rates = np.array([
        motor_valve_gas_rate(p, params.operating.injection_pressure_pa,
        params.fluids.gas_relative_density, params.gas.temp_c1_k,
        params.valves.motor_valve_cv) for p in p_c1
    ])
    forces = np.array([
        gas_lift_valve_resultant_force(p2, initial["p_bt"], initial["p_to"],
        params.valves.rv, params.valves.bellows_area_m2) for p2 in p_c2
    ])
    injected_mass = float(np.trapezoid(rho_std * rates, times))
    mass_change = float(masses[-1] - masses[0])
    balance_error = abs(mass_change - injected_mass) / max(abs(mass_change), 1.0e-15)
    return Stage1Result(
        times, masses, p_c1, p_c2, rho_c1, rho_c2, rates, forces,
        opened, opening_time, balance_error,
    )
