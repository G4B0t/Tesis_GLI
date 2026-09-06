"""Slug-production stage D->E with an explicit surface discharge boundary."""

from dataclasses import dataclass
from math import pi, sqrt

import numpy as np
from scipy.integrate import quad, solve_ivp

from .fallback import fallback_rate_m3_s
from .geometry import tubing_area
from .initial_conditions import GRAVITY_M_S2, initial_stage_1
from .parameters import GLIParameters
from .reservoir import reservoir_inflow_from_pt1
from .stage1_dynamic import state_from_mass
from .stage_bc_dynamic import _historical_glv_proxy_mass_rate
from .stage_cd_dynamic import StageCDResult, simulate_stage_c_to_d
from .valves import gas_lift_valve_resultant_force


@dataclass(frozen=True)
class StageDEResult:
    time_s: np.ndarray
    annulus_mass_kg: np.ndarray
    bubble_mass_kg: np.ndarray
    h_b_m: np.ndarray
    h_l_m: np.ndarray
    v_b_m_s: np.ndarray
    v_l_m_s: np.ndarray
    liquid_rate_m3_s: np.ndarray
    produced_volume_m3: np.ndarray
    slug_volume_m3: np.ndarray
    film_volume_m3: np.ndarray
    fallback_volume_m3: np.ndarray
    p_c1_pa: np.ndarray
    p_c2_pa: np.ndarray
    p_tubing_pa: np.ndarray
    p_bottom_pa: np.ndarray
    gl_mass_rate_kg_s: np.ndarray
    valve_force_n: np.ndarray
    valve_open: np.ndarray
    event_e_reached: bool
    event_e_time_s: float | None
    gas_balance_relative_error: float
    liquid_balance_relative_error: float
    film_velocity_m_s: np.ndarray | None = None
    gas_density_kg_m3: np.ndarray | None = None
    reservoir_inflow_valid: bool = True
    reservoir_accumulated_m3: np.ndarray | None = None
    canonical_states: np.ndarray | None = None
    film_thickness_m: np.ndarray | None = None
    glv_closure_time_s: float | None = None
    integration_end_time_s: float | None = None
    terminal_reason: str = "LEGACY_REFERENCE"
    source_certified: bool = False
    lower_liquid_height_m: np.ndarray | None = None
    lower_liquid_height_source: str | None = None
    gas_pressure_at_liquid_top_pa: np.ndarray | None = None
    source_diagnostics: dict | None = None


def simulate_stage_d_to_e(
    params: GLIParameters,
    *,
    stage_c_d: StageCDResult | None = None,
    max_time_s: float = 180.0,
    max_step_s: float = 0.1,
    rtol: float = 1e-8,
    atol: float = 1e-10,
    rhs_mode: str = "legacy",
) -> StageDEResult:
    """Continue the exact D state until the slug base reaches the surface.

    At D, hL becomes a fixed outlet boundary at surface pressure.  No state is
    reset: annulus/bubble masses, hB, velocity and fallback all come from C->D.
    """
    cd = stage_c_d or simulate_stage_c_to_d(params)
    if not cd.event_d_reached:
        raise ValueError("Stage C->D must reach D")
    if rhs_mode == "santos_corrected":
        from .stage_de_santos import simulate_stage3

        return simulate_stage3(
            params,
            cd,
            max_time_s=max_time_s,
            max_step_s=max_step_s,
            rtol=rtol,
            atol=atol,
        )
    if rhs_mode == "milestone16_reference":
        return _simulate_stage_d_to_e_milestone16(
            params,
            cd,
            max_time_s=max_time_s,
            max_step_s=max_step_s,
            rtol=rtol,
            atol=atol,
        )
    if rhs_mode != "legacy":
        raise ValueError(f"unknown D->E rhs_mode: {rhs_mode}")
    initial = initial_stage_1(params)
    gas = params.gas
    H = params.geometry.valve_depth_m
    At = tubing_area(params.geometry.tubing_diameter_m)
    Af = cd.film_volume_m3[-1] / max(cd.h_b_m[-1], 1e-12)
    Ab = At - Af
    vf0 = float(cd.fallback_volume_m3[-1])
    total_liquid0 = At * params.geometry.initial_slug_length_m
    y0 = np.array(
        [
            cd.annulus_mass_kg[-1],
            cd.bubble_mass_kg[-1],
            cd.h_b_m[-1],
            cd.v_b_m_s[-1],
            vf0,
            0.0,
        ],
        dtype=float,
    )

    def values(state):
        mc, mb, hb, vb, vfb, vp = state
        casing = state_from_mass(float(mc), params)
        bubble_volume = max(Ab * hb, 1e-12)
        pt = (
            mb
            * gas.z_t1
            * gas.gas_constant_j_mol_k
            * gas.temp_t1_k
            / (gas.gas_molar_mass_kg_mol * bubble_volume)
        )
        force = gas_lift_valve_resultant_force(
            casing["p_c2"],
            initial["p_bt"],
            pt,
            params.valves.rv,
            params.valves.bellows_area_m2,
        )
        opened = force >= -1e-6 and casing["p_c2"] > pt
        mgl = (
            _historical_glv_proxy_mass_rate(
                casing["p_c2"], pt, casing["rho_c2"], params
            )
            if opened
            else 0.0
        )
        film = Af * hb
        thickness = params.geometry.tubing_diameter_m / 2 - sqrt(max(Ab, 0.0) / np.pi)
        qfb = fallback_rate_m3_s(
            params.geometry.tubing_diameter_m,
            thickness,
            initial["rho_l"],
            params.fluids.liquid_viscosity_pa_s,
            film,
        )
        qprod = max((At - Af) * vb - qfb, 0.0)
        vl = qprod / At
        slug = At * max(H - hb, 0.0)
        pwf = pt + initial["rho_l"] * GRAVITY_M_S2 * max(
            (params.geometry.perforation_depth_m or H) - H, 0.0
        )
        return casing, pt, pwf, force, opened, mgl, qfb, qprod, vl, slug, film

    def rhs(_t, state):
        mc, mb, hb, vb, vfb, vp = state
        x = values(state)
        # A finite outlet/control-volume length avoids the nonphysical point-
        # mass singularity as the last part of the slug crosses the wellhead.
        length = max(H - hb, 20.0)
        rho = initial["rho_l"]
        friction = (
            params.coefficients.liquid_friction_factor
            * 0.5
            * rho
            * vb
            * abs(vb)
            * length
            / params.geometry.tubing_diameter_m
        )
        acceleration = (
            x[1] - initial["p_t3"] - rho * GRAVITY_M_S2 * length - friction
        ) / (rho * length)
        return [-x[5], x[5], vb, acceleration, x[6], x[7]]

    def event_e(_t, state):
        return state[2] - H

    event_e.terminal = True
    event_e.direction = 1.0
    sol = solve_ivp(
        rhs,
        (0.0, max_time_s),
        y0,
        events=event_e,
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
    arr = lambda j: np.array([x[j] for x in derived])
    gas_total = states[0] + states[1]
    gas_error = float(np.max(np.abs(gas_total - gas_total[0])) / max(gas_total[0], 1.0))
    inventory = arr(9) + arr(10) + states[4] + states[5]
    liquid_error = float(np.max(np.abs(inventory - total_liquid0)) / total_liquid0)
    pc1 = np.array([x[0]["p_c1"] for x in derived])
    pc2 = np.array([x[0]["p_c2"] for x in derived])
    return StageDEResult(
        times,
        states[0],
        states[1],
        states[2],
        np.full_like(times, H),
        states[3],
        arr(8),
        arr(7),
        states[5],
        arr(9),
        arr(10),
        states[4],
        pc1,
        pc2,
        arr(1),
        arr(2),
        arr(5),
        arr(3),
        arr(4),
        reached,
        end,
        gas_error,
        liquid_error,
    )


def _simulate_stage_d_to_e_milestone16(
    params: GLIParameters,
    cd: StageCDResult,
    *,
    max_time_s: float,
    max_step_s: float,
    rtol: float,
    atol: float,
) -> StageDEResult:
    """Historical Milestone 1.6 reference, NOT the scientific Stage-3 route.

    The legacy public contract is preserved.  This route carries the film
    velocity as memory, accumulates reservoir liquid in the film, closes the GLV
    boundary for the production step, and evaluates the liquid balance against
    the inventory actually present at D plus q_res*t.
    """
    initial = initial_stage_1(params)
    gas = params.gas
    H = params.geometry.valve_depth_m
    D = params.geometry.tubing_diameter_m
    r = D / 2.0
    At = tubing_area(D)
    rho_l = initial["rho_l"]
    yD = float(cd.film_thickness_m[-1])
    AbD = pi * (r - yD) ** 2
    AfD = At - AbD
    hbD = float(cd.h_b_m[-1])
    vgD = float(cd.v_b_m_s[-1])
    vlD = float(cd.v_l_m_s[-1])
    vfD = (At * vlD - AbD * vgD) / max(AfD, 1e-18)
    VgD = max(AbD * hbD, 1e-18)
    rhoD = float(cd.bubble_mass_kg[-1]) / VgD
    ptD = float(cd.p_tubing_pa[-1])
    # mc, mg, rho_g, pt1, vB, vf, y, film_volume, hB, vL, fallback, produced
    y0 = np.array(
        [
            cd.annulus_mass_kg[-1],
            cd.bubble_mass_kg[-1],
            rhoD,
            ptD,
            vgD,
            vfD,
            yD,
            cd.film_volume_m3[-1],
            hbD,
            vlD,
            cd.fallback_volume_m3[-1],
            0.0,
        ],
        dtype=float,
    )

    def geometry(y, hb):
        Ab = pi * (r - y) ** 2
        Af = At - Ab
        Vg = max(Ab * hb, 1e-18)
        return Ab, Af, Vg

    def values(state):
        mc, mg, rho_g, pt1, vg, vf, y, film, hb, vl, fb, prod = state
        Ab, Af, Vg = geometry(y, hb)
        casing = state_from_mass(float(mc), params)
        force = gas_lift_valve_resultant_force(
            casing["p_c2"],
            initial["p_bt"],
            pt1,
            params.valves.rv,
            params.valves.bellows_area_m2,
        )
        # The production-stage candidate is evaluated with the GLV latched
        # closed.  The force remains diagnostic until the mechanical hysteresis
        # model is reintroduced at this boundary.
        opened = False
        mgl = 0.0
        pt2 = pt1 - rho_g * GRAVITY_M_S2 * hb
        pt3 = params.operating.surface_tubing_pressure_pa
        L = max(H - hb, 1e-9)
        slug = At * max(H - hb, 0.0)
        pwf = pt1 + rho_l * GRAVITY_M_S2 * max(
            (params.geometry.perforation_depth_m or H) - H, 0.0
        )
        qprod = max(At * vl, 0.0)
        qfb = max(-Af * vf, 0.0)
        qres = reservoir_inflow_from_pt1(params, pt1, rho_l)
        return (
            casing,
            Ab,
            Af,
            Vg,
            force,
            opened,
            mgl,
            pt2,
            pt3,
            L,
            slug,
            pwf,
            qprod,
            qfb,
            qres,
        )

    def rhs(_t, state):
        mc, mg, rho_g, pt1, vg, vf, y, film, hb, vl, fb, prod = state
        x = values(state)
        Ab, Af, Vg, pt2, pt3, L = x[1], x[2], x[3], x[7], x[8], x[9]
        qres = x[14].rate_m3_s
        # Santos stage 3 keeps h_l fixed at z_v and keeps the same liquid mass
        # relation as stage 2, while adding the surface loss term 0.3*v_l^2 in
        # the momentum equation (4.1.53).
        fl = params.coefficients.liquid_friction_factor
        Leff = max(L, 5.0)
        dvl = (
            -vl * vl
            + (Af / At) * vf * vf
            + (Ab / At) * vg * vg
            + (pt2 - pt3) / rho_l
            - GRAVITY_M_S2 * L
            - fl * vl * abs(vl) * L / (2 * D)
            - 0.3 * vl * vl
        ) / Leff
        dvg = params.coefficients.bubble_velocity_a * dvl
        dhb = vg
        dy = (qres - Af * vf) / (2 * pi * max(r - y, 1e-12) * max(hb, 1e-12))
        dAb = -2 * pi * (r - y) * dy
        dAf = -dAb
        # Differential form of A_t*v_l - A_f*v_f - A_B*v_B = 0.
        N = At * vl - Ab * vg
        dN = At * dvl - dAb * vg - Ab * dvg
        dvf = (dN * Af - N * dAf) / max(Af * Af, 1e-18)
        dmc = 0.0
        dmg = 0.0
        dVg = Ab * dhb + dAb * hb
        drho = dmg / Vg - rho_g * dVg / Vg
        dpt = (
            gas.z_t1
            * gas.gas_constant_j_mol_k
            * gas.temp_t1_k
            / gas.gas_molar_mass_kg_mol
            * drho
        )
        qfb = max(-Af * vf, 0.0)
        dfilm = qres - Af * vf + Af * dhb - qfb
        dprod = max(At * vl, 0.0)
        return np.array(
            [dmc, dmg, drho, dpt, dvg, dvf, dy, dfilm, dhb, dvl, qfb, dprod]
        )

    def event_e(_t, state):
        return state[8] - H

    event_e.terminal = True
    event_e.direction = 1.0
    sol = solve_ivp(
        rhs,
        (0.0, max_time_s),
        y0,
        events=event_e,
        dense_output=True,
        max_step=max_step_s,
        rtol=rtol,
        atol=atol,
        method="Radau",
    )
    reached = bool(sol.t_events[0].size)
    end = float(sol.t_events[0][0]) if reached else float(sol.t[-1])
    times = np.linspace(0.0, end, max(2, int(np.ceil(end / max_step_s)) + 1))
    states = sol.sol(times)
    derived = [values(states[:, i]) for i in range(states.shape[1])]
    arr = lambda j: np.array([x[j] for x in derived])
    pc1 = np.array([x[0]["p_c1"] for x in derived])
    pc2 = np.array([x[0]["p_c2"] for x in derived])
    gas_total = states[0] + states[1]
    gas_error = float(np.max(np.abs(gas_total - gas_total[0])) / max(gas_total[0], 1.0))
    inventory = arr(10) + states[7] + states[10] + states[11]
    qres_values = arr(14)
    qres_values = np.array([item.rate_m3_s for item in qres_values])
    reservoir = np.array(
        [
            quad(
                lambda time: reservoir_inflow_from_pt1(
                    params, float(sol.sol(time)[3]), rho_l
                ).rate_m3_s,
                0.0,
                float(time),
                epsabs=1e-12,
                epsrel=1e-11,
                limit=100,
            )[0]
            for time in times
        ]
    )
    expected_inventory = inventory[0] + reservoir
    liquid_error = float(
        np.max(np.abs(inventory - expected_inventory))
        / max(abs(expected_inventory[-1]), 1e-12)
    )
    inflow_valid = bool(all(item.physically_valid for item in arr(14)))
    return StageDEResult(
        times,
        states[0],
        states[1],
        states[8],
        np.full_like(times, H),
        states[4],
        states[9],
        arr(12),
        states[11],
        arr(10),
        states[7],
        states[10],
        pc1,
        pc2,
        states[3],
        arr(11),
        arr(6),
        arr(4),
        arr(5),
        reached,
        end,
        gas_error,
        liquid_error,
        states[5],
        states[2],
        inflow_valid,
        reservoir,
    )
