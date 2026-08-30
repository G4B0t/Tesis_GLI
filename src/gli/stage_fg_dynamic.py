"""Santos Model-I stage F->G: phase 4.3, final decompression.

The governing system is Santos 4.1.89, 4.1.94, 4.1.97, 4.1.107 and
4.1.108.  Equations 4.1.24-25, 4.1.95-103 provide the algebraic closures.
No feeding-stage (G->H) equation is implemented here.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import pi, sqrt

import numpy as np
from scipy.integrate import solve_ivp

from .events import (
    EVENT_G_MOMENTUM_EQUILIBRIUM,
    gas_pressure_back_to_initial_residual,
    stage_g_momentum_residual,
)
from .fallback import falling_film_velocity_m_s
from .fluids import gas_density_real
from .geometry import gas_bubble_area, tubing_area
from .initial_conditions import GRAVITY_M_S2, initial_stage_1
from .parameters import GLIParameters
from .stage_ef_dynamic import StageEFResult
from .reservoir import reservoir_inflow_from_pt1


HIGH_VELOCITY_WARNING = "HIGH_VELOCITY_PLAUSIBILITY_REVIEW_PENDING"


@dataclass(frozen=True)
class ContinuityDiagnosticFG:
    name: str
    previous_value: float
    initial_value: float
    units: str
    absolute_error: float
    tolerance: float
    passed: bool


@dataclass(frozen=True)
class StageFGResult:
    time_s: np.ndarray
    bottom_gas_density_kg_m3: np.ndarray
    gas_pressure_at_liquid_top_pa: np.ndarray
    bottom_gas_pressure_pa: np.ndarray
    liquid_height_m: np.ndarray
    film_thickness_m: np.ndarray
    film_volume_m3: np.ndarray
    bottom_liquid_volume_m3: np.ndarray
    film_return_rate_m3_s: np.ndarray
    film_returned_volume_m3: np.ndarray
    reservoir_accumulated_m3: np.ndarray
    produced_liquid_volume_m3: np.ndarray
    fallback_volume_m3: np.ndarray
    mean_gas_density_kg_m3: np.ndarray
    gas_density_at_surface_kg_m3: np.ndarray
    mean_gas_velocity_m_s: np.ndarray
    surface_gas_velocity_m_s: np.ndarray
    gas_mass_kg: np.ndarray
    gas_discharged_mass_kg: np.ndarray
    surface_gas_rate_kg_s: np.ndarray
    bottomhole_flowing_pressure_pa: np.ndarray
    reservoir_rate_m3_s: np.ndarray
    reservoir_inflow_valid: bool
    reservoir_inflow_statuses: tuple[str, ...]
    momentum_residual_pa: np.ndarray
    legacy_pressure_residual_pa: np.ndarray
    legacy_event_times_s: tuple[float, ...]
    event_g_reached: bool
    event_g_time_s: float
    event_identifier: str
    event_direction: float
    event_direction_verified: bool
    gas_balance_absolute_residual_kg: float
    gas_balance_relative_residual: float
    gas_balance_normalized_residual: float
    liquid_balance_absolute_residual_m3: float
    liquid_balance_relative_residual: float
    liquid_balance_normalized_residual: float
    continuity: tuple[ContinuityDiagnosticFG, ...]
    continuity_passed: bool
    physical_bounds_passed: bool
    failed_physical_bounds: tuple[str, ...]
    solver_method: str
    rtol: float
    atol: float
    max_step_s: float
    safety_time_horizon_s: float
    initial_pressure_target_pa: float
    f_previous_mean_pressure_pa: float
    f_transformed_bottom_pressure_pa: float
    initial_state_source: str
    scientific_warning: str


def stage_43_equation_contract_residuals(
    params: GLIParameters,
    result: StageFGResult,
) -> dict[str, float]:
    """Return normalized integral residuals for the five governing equations.

    These checks are deliberately independent of the RHS implementation: they
    reconstruct the conserved/integrated forms from the reported trajectory.
    """

    gas = params.gas
    rho_l = initial_stage_1(params)["rho_l"]
    k_t3 = gas.z_t3 * gas.gas_constant_j_mol_k * gas.temp_t3_k / gas.gas_molar_mass_kg_mol
    returned = result.fallback_volume_m3 - result.fallback_volume_m3[0]
    reservoir = result.reservoir_accumulated_m3 - result.reservoir_accumulated_m3[0]

    film_94 = result.film_volume_m3 + returned
    column_107 = result.bottom_liquid_volume_m3 - returned - reservoir
    eos_108 = result.gas_pressure_at_liquid_top_pa - k_t3 * result.bottom_gas_density_kg_m3
    hydro_89 = (
        result.bottom_gas_pressure_pa
        - result.gas_pressure_at_liquid_top_pa
        - rho_l * GRAVITY_M_S2 * result.liquid_height_m
    )
    gas_97 = result.gas_mass_kg + result.gas_discharged_mass_kg

    def normalized_constant(values: np.ndarray, scale: float) -> float:
        return float(np.max(np.abs(values - values[0])) / max(abs(float(scale)), 1.0e-18))

    return {
        "4.1.89": normalized_constant(hydro_89, result.bottom_gas_pressure_pa[0]),
        "4.1.94": normalized_constant(film_94, result.film_volume_m3[0]),
        "4.1.97": normalized_constant(gas_97, result.gas_mass_kg[0]),
        "4.1.107": normalized_constant(column_107, result.bottom_liquid_volume_m3[-1]),
        "4.1.108": normalized_constant(eos_108, result.gas_pressure_at_liquid_top_pa[0]),
    }


def santos_stage_43_film_return_rate_m3_s(
    film_thickness_m: float,
    tubing_radius_m: float,
    liquid_density_kg_m3: float,
    liquid_viscosity_pa_s: float,
) -> float:
    """Santos 4.1.95, q_f = rho_l*g*(2*pi*r)*y^3/(3*mu_l)."""

    falling_velocity = falling_film_velocity_m_s(
        film_thickness_m,
        liquid_density_kg_m3,
        liquid_viscosity_pa_s,
        GRAVITY_M_S2,
    )
    return 2.0 * pi * tubing_radius_m * film_thickness_m * falling_velocity


def _continuity(
    name: str,
    previous: float,
    initial: float,
    units: str,
    *,
    atol: float = 1.0e-12,
    rtol: float = 1.0e-10,
) -> ContinuityDiagnosticFG:
    error = abs(float(initial) - float(previous))
    tolerance = atol + rtol * max(abs(float(previous)), 1.0)
    return ContinuityDiagnosticFG(
        name=name,
        previous_value=float(previous),
        initial_value=float(initial),
        units=units,
        absolute_error=error,
        tolerance=tolerance,
        passed=error <= tolerance,
    )


def simulate_stage_f_to_g(
    params: GLIParameters,
    *,
    stage_e_f: StageEFResult,
    max_time_s: float = 1200.0,
    max_step_s: float = 0.5,
    rtol: float = 1.0e-8,
    atol: float = 1.0e-10,
    method: str = "Radau",
) -> StageFGResult:
    """Integrate Santos final decompression from the actual terminal F state.

    ``max_time_s`` is only a numerical failure guard. Successful termination
    is exclusively the descending zero-velocity limit of Santos
    4.1.98-4.1.102. The historical ``P_t1-P_to_initial`` root is recorded as a
    non-terminal diagnostic on the same trajectory. The reservoir rate is
    evaluated from instantaneous P_t1 using the configured SI IPR.
    """

    if method != "Radau":
        raise ValueError("F->G is qualified only with scipy solve_ivp/Radau")
    if not stage_e_f.event_f_reached or not stage_e_f.corrected_certified:
        raise ValueError("F->G requires the corrected, certified terminal F state")
    if abs(float(stage_e_f.film_velocity_m_s[-1])) > 1.0e-7:
        raise ValueError("F boundary must satisfy v_f = 0")
    if bool(np.asarray(stage_e_f.valve_open, dtype=bool).any()):
        raise ValueError("GLV must remain closed at F")

    initial = initial_stage_1(params)
    gas = params.gas
    H = float(params.geometry.valve_depth_m)
    D = float(params.geometry.tubing_diameter_m)
    r = D / 2.0
    At = tubing_area(D)
    rho_l = float(initial["rho_l"])
    mu_l = float(params.fluids.liquid_viscosity_pa_s)
    p_surface = float(params.operating.surface_tubing_pressure_pa)
    p_initial = float(initial["p_to"])
    f_g = float(params.coefficients.gas_friction_factor)
    if f_g <= 0.0:
        raise ValueError("Santos gas friction factor must be positive")

    rho_surface = gas_density_real(
        p_surface,
        gas.gas_molar_mass_kg_mol,
        gas.z_ts,
        gas.gas_constant_j_mol_k,
        gas.temp_ts_k,
    )
    k_t3 = gas.z_t3 * gas.gas_constant_j_mol_k * gas.temp_t3_k / gas.gas_molar_mass_kg_mol
    k_t1 = gas.z_t1 * gas.gas_constant_j_mol_k * gas.temp_t1_k / gas.gas_molar_mass_kg_mol

    y0 = float(stage_e_f.film_thickness_m[-1])
    film0 = float(stage_e_f.film_volume_m3[-1])
    fallback0 = float(stage_e_f.fallback_volume_m3[-1])
    produced0 = float(stage_e_f.produced_film_volume_m3[-1])
    reservoir0 = float(stage_e_f.reservoir_accumulated_m3[-1])
    gas_mass0 = float(stage_e_f.gas_mass_kg[-1])
    gas_out0 = float(stage_e_f.gas_mass_kg[0] - stage_e_f.gas_mass_kg[-1])
    Ab0 = gas_bubble_area(D, y0)
    expected_film0 = (At - Ab0) * H
    h0 = (reservoir0 + fallback0) / Ab0
    gas_length0 = H - h0
    mean_rho0 = gas_mass0 / (Ab0 * gas_length0)
    rho_gt3_0 = 2.0 * mean_rho0 - rho_surface  # Santos 4.1.96
    pt3_0 = k_t3 * rho_gt3_0  # Santos 4.1.101
    pt1_0 = pt3_0 + rho_l * GRAVITY_M_S2 * h0  # integral of 4.1.89

    continuity = (
        _continuity("gas_mass", stage_e_f.gas_mass_kg[-1], gas_mass0, "kg"),
        _continuity("film_thickness", stage_e_f.film_thickness_m[-1], y0, "m"),
        _continuity("film_volume", stage_e_f.film_volume_m3[-1], expected_film0, "m3", atol=1e-10),
        _continuity("produced_liquid_ledger", stage_e_f.produced_film_volume_m3[-1], produced0, "m3"),
        _continuity("fallback_ledger", stage_e_f.fallback_volume_m3[-1], fallback0, "m3"),
        _continuity("reservoir_ledger", stage_e_f.reservoir_accumulated_m3[-1], reservoir0, "m3"),
    )
    if not all(item.passed for item in continuity):
        failed = ", ".join(item.name for item in continuity if not item.passed)
        raise ValueError(f"F->G identity continuity failed: {failed}")

    # rho_gt3, P_t3, P_t1, h_l, y, fallback/returned, reservoir, gas-out mass
    state0 = np.array(
        [rho_gt3_0, pt3_0, pt1_0, h0, y0, fallback0, reservoir0, gas_out0],
        dtype=float,
    )

    def algebraic(state: np.ndarray) -> dict[str, float]:
        rho_gt3, pt3, pt1, h_l, y, returned, reservoir, gas_out = map(float, state)
        values = np.asarray(state, dtype=float)
        if not bool(np.all(np.isfinite(values))):
            raise ValueError("F->G state contains NaN or Inf")
        if rho_gt3 <= 0.0 or pt3 <= 0.0 or pt1 <= 0.0:
            raise ValueError("F->G pressure and density must remain positive")
        if y < 0.0 or y >= r:
            raise ValueError("F->G film thickness is outside [0, tubing radius)")
        if h_l < 0.0 or h_l >= H:
            raise ValueError("F->G liquid height is outside [0, valve depth)")
        if returned < -1e-12 or gas_out < -1e-12:
            raise ValueError("F->G fallback/gas cumulative ledgers must remain non-negative")
        Ab = gas_bubble_area(D, y)
        Af = At - Ab
        gas_length = H - h_l
        rho_mean = 0.5 * (rho_gt3 + rho_surface)  # Santos 4.1.96
        q_f = santos_stage_43_film_return_rate_m3_s(y, r, rho_l, mu_l)
        radicand = (2.0 * D / f_g) * (
            (pt3 - p_surface) / (rho_mean * gas_length) - GRAVITY_M_S2
        )
        residual = stage_g_momentum_residual(
            pt3, p_surface, rho_mean, gas_length, GRAVITY_M_S2
        )
        radicand_tolerance = (2.0 * D / f_g) * 10.0 / max(rho_mean * gas_length, 1e-18)
        if radicand < -radicand_tolerance:
            raise ValueError("Santos 4.1.99 left the real gas-velocity domain")
        # Numerical continuation used only while Radau brackets the zero; no
        # post-event state is retained in the reported physical trajectory.
        v_g = sqrt(max(radicand, 0.0))  # Santos 4.1.99
        v_gs = 2.0 * v_g  # Santos 4.1.102-103
        gas_mass = rho_mean * Ab * gas_length
        gas_rate = rho_surface * v_gs * Ab
        inflow = reservoir_inflow_from_pt1(params, pt1, rho_l)
        return {
            "Ab": Ab,
            "Af": Af,
            "gas_length": gas_length,
            "rho_mean": rho_mean,
            "rho_gt1": pt1 / k_t1,
            "q_f": q_f,
            "v_g": v_g,
            "v_gs": v_gs,
            "gas_mass": gas_mass,
            "gas_rate": gas_rate,
            "p_wb": inflow.bottomhole_pressure_pa,
            "q_res": inflow.rate_m3_s,
            "inflow": inflow,
            "momentum_residual": residual,
            "legacy_residual": gas_pressure_back_to_initial_residual(pt1, p_initial),
            "film_volume": Af * H,
            "bottom_volume": Ab * h_l,
        }

    def derivatives(state: np.ndarray) -> tuple[np.ndarray, dict[str, float]]:
        rho_gt3, _pt3, _pt1, h_l, y, _returned, _reservoir, _gas_out = map(float, state)
        a = algebraic(state)
        dy = -a["q_f"] / (2.0 * pi * H * (r - y))  # Santos 4.1.94
        dh = (
            2.0 * pi * (r - y) * h_l * dy + a["q_f"] + a["q_res"]
        ) / a["Ab"]  # Santos 4.1.107
        drho_gt3 = (
            (rho_gt3 + rho_surface) * dh
            + 2.0 * (rho_gt3 + rho_surface) * a["gas_length"] * dy / (r - y)
            - 2.0 * rho_surface * a["v_gs"]
        ) / a["gas_length"]  # Santos 4.1.97
        dpt3 = k_t3 * drho_gt3  # Santos 4.1.108
        dpt1 = dpt3 + rho_l * GRAVITY_M_S2 * dh  # Santos 4.1.89
        return np.array(
            [drho_gt3, dpt3, dpt1, dh, dy, a["q_f"], a["q_res"], a["gas_rate"]],
            dtype=float,
        ), a

    def rhs(_time_s: float, state: np.ndarray) -> np.ndarray:
        return derivatives(state)[0]

    def event_g(_time_s: float, state: np.ndarray) -> float:
        return algebraic(state)["momentum_residual"]

    event_g.terminal = True
    event_g.direction = -1.0
    def legacy_event(_time_s: float, state: np.ndarray) -> float:
        return gas_pressure_back_to_initial_residual(float(state[2]), p_initial)

    legacy_event.terminal = False
    legacy_event.direction = -1.0
    if algebraic(state0)["momentum_residual"] <= 0.0:
        raise ValueError("F state does not precede the Santos momentum-equilibrium G event")
    sol = solve_ivp(
        rhs,
        (0.0, max_time_s),
        state0,
        method=method,
        events=(event_g, legacy_event),
        dense_output=True,
        max_step=max_step_s,
        rtol=rtol,
        atol=atol,
    )
    if not sol.success:
        raise RuntimeError(f"F->G Radau integration failed: {sol.message}")
    reached = bool(sol.t_events[0].size)
    end = float(sol.t_events[0][0]) if reached else float(sol.t[-1])
    times = np.linspace(0.0, end, max(2, int(np.ceil(max(end, max_step_s) / max_step_s)) + 1))
    states = sol.sol(times)
    algebraics = [algebraic(states[:, index]) for index in range(times.size)]
    arr = lambda name: np.asarray([item[name] for item in algebraics], dtype=float)

    gas_mass = arr("gas_mass")
    gas_out = states[7]
    gas_balance = gas_mass + gas_out
    gas_residual = gas_balance - gas_balance[0]
    gas_abs = float(np.max(np.abs(gas_residual)))
    gas_scale = max(abs(float(gas_balance[0])), 1.0e-18)
    gas_rel = gas_abs / gas_scale

    film_volume = arr("film_volume")
    bottom_volume = arr("bottom_volume")
    liquid_balance = film_volume + bottom_volume + produced0 - states[6]
    liquid_residual = liquid_balance - liquid_balance[0]
    liquid_abs = float(np.max(np.abs(liquid_residual)))
    liquid_scale = max(abs(float(film_volume[0] + bottom_volume[0] + produced0)), 1.0e-18)
    liquid_rel = liquid_abs / liquid_scale

    failed_bounds: list[str] = []
    arrays = [states, film_volume, bottom_volume, arr("q_f"), gas_mass, arr("gas_rate")]
    if not all(bool(np.all(np.isfinite(array))) for array in arrays):
        failed_bounds.append("finite_state")
    if bool(np.any(states[0] <= 0.0)):
        failed_bounds.append("positive_bottom_gas_density")
    if bool(np.any(states[1:3] <= 0.0)):
        failed_bounds.append("positive_pressure")
    if bool(np.any(states[4] < 0.0)) or bool(np.any(states[4] >= r)):
        failed_bounds.append("film_thickness_domain")
    if bool(np.any(states[3] < 0.0)) or bool(np.any(states[3] >= H)):
        failed_bounds.append("liquid_height_domain")
    if bool(np.any(film_volume < 0.0)) or bool(np.any(bottom_volume < 0.0)):
        failed_bounds.append("non_negative_liquid_inventory")
    if bool(np.any(gas_mass <= 0.0)):
        failed_bounds.append("positive_gas_inventory")
    if bool(np.any(np.diff(states[5]) < -1.0e-12)):
        failed_bounds.append("monotone_fallback_ledger")
    momentum = arr("momentum_residual")
    legacy = arr("legacy_residual")
    inflows = [item["inflow"] for item in algebraics]
    inflow_valid = bool(all(item.physically_valid for item in inflows))
    inflow_statuses = tuple(dict.fromkeys(item.status.value for item in inflows))
    direction_verified = bool(
        reached
        and times.size >= 2
        and float(momentum[-2]) > float(momentum[-1])
        and abs(float(momentum[-1])) <= max(1.0, rtol * max(abs(float(states[1, -1])), 1.0))
    )
    return StageFGResult(
        time_s=times,
        bottom_gas_density_kg_m3=states[0],
        gas_pressure_at_liquid_top_pa=states[1],
        bottom_gas_pressure_pa=states[2],
        liquid_height_m=states[3],
        film_thickness_m=states[4],
        film_volume_m3=film_volume,
        bottom_liquid_volume_m3=bottom_volume,
        film_return_rate_m3_s=arr("q_f"),
        film_returned_volume_m3=states[5] - states[5, 0],
        reservoir_accumulated_m3=states[6],
        produced_liquid_volume_m3=np.full_like(times, produced0),
        fallback_volume_m3=states[5],
        mean_gas_density_kg_m3=arr("rho_mean"),
        gas_density_at_surface_kg_m3=np.full_like(times, rho_surface),
        mean_gas_velocity_m_s=arr("v_g"),
        surface_gas_velocity_m_s=arr("v_gs"),
        gas_mass_kg=gas_mass,
        gas_discharged_mass_kg=gas_out,
        surface_gas_rate_kg_s=arr("gas_rate"),
        bottomhole_flowing_pressure_pa=arr("p_wb"),
        reservoir_rate_m3_s=arr("q_res"),
        reservoir_inflow_valid=inflow_valid,
        reservoir_inflow_statuses=inflow_statuses,
        momentum_residual_pa=momentum,
        legacy_pressure_residual_pa=legacy,
        legacy_event_times_s=tuple(float(x) for x in sol.t_events[1]),
        event_g_reached=reached,
        event_g_time_s=end,
        event_identifier=EVENT_G_MOMENTUM_EQUILIBRIUM,
        event_direction=-1.0,
        event_direction_verified=direction_verified,
        gas_balance_absolute_residual_kg=gas_abs,
        gas_balance_relative_residual=gas_rel,
        gas_balance_normalized_residual=gas_rel,
        liquid_balance_absolute_residual_m3=liquid_abs,
        liquid_balance_relative_residual=liquid_rel,
        liquid_balance_normalized_residual=liquid_rel,
        continuity=continuity,
        continuity_passed=all(item.passed for item in continuity),
        physical_bounds_passed=not failed_bounds,
        failed_physical_bounds=tuple(failed_bounds),
        solver_method=method,
        rtol=float(rtol),
        atol=float(atol),
        max_step_s=float(max_step_s),
        safety_time_horizon_s=float(max_time_s),
        initial_pressure_target_pa=p_initial,
        f_previous_mean_pressure_pa=float(stage_e_f.tubing_pressure_pa[-1]),
        f_transformed_bottom_pressure_pa=pt1_0,
        initial_state_source=(
            "Identity transfer of F gas mass, film geometry and liquid ledgers from "
            "E->F santos_corrected; Santos 4.1.96 transforms mean gas density to rho_gt3"
        ),
        scientific_warning=HIGH_VELOCITY_WARNING,
    )
