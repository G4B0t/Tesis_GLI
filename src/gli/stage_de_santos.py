"""Santos Table 5.1 Stage 3, with identity D and explicit source gates.

The preserved upstream GLV correlation is audited against 4.1.13/.15.
A materially pre-E closure has no published two-slug transition in the
inspected source and stops the certified path, without inventing E.
"""
from math import exp, pi, sqrt

import numpy as np
from scipy.integrate import solve_ivp

from .block6p_parameters import FrictionClosure, friction_factor
from .geometry import tubing_area
from .initial_conditions import GRAVITY_M_S2 as G, initial_stage_1
from .reservoir import reservoir_inflow_from_pt1
from .stage_bc_dynamic import _gas_lift_mass_rate
from .stage1_dynamic import state_from_mass, standard_gas_density
from .valves import gas_lift_valve_resultant_force

# First fourteen slots are the unchanged Stage-2 canonical vector.
MC, MG, RHO, PT1, VB, VF, Y, MFILM, HB, DISPLACEMENT, VL, VGI, FB, PROD = range(14)
PT2, PC1, PC2, RHOC1, RHOC2, VRES, TRANSFER = range(14, 21)
EQUATIONS = (6, 9, 17, 18, 19, 26, 28, 32, 35, 40, 48, 50, 53)


def stage3_factors(params, rho, vb, vl):
    from .stage_ef_dynamic import default_stage_ef_parameters
    D = params.geometry.tubing_diameter_m
    rl = initial_stage_1(params)["rho_l"]
    fc = FrictionClosure(default_stage_ef_parameters().roughness)
    fg = friction_factor(max(rho*abs(vb)*D/1.1e-5, 1e-12), D, fc)[0]
    fl = friction_factor(max(rl*abs(vl)*D/params.fluids.liquid_viscosity_pa_s, 1e-12), D, fc)[0]
    return fg, fl


def source_glv_rate(params, pc2, pt1):
    """4.1.13/.15 diagnostic, in kg/s, including critical pressure ratio."""
    if pc2 <= pt1:
        return 0.0
    k = params.valves.adiabatic_constant
    x = max(pt1/pc2, (2/(k+1))**(k/(k-1)))
    q = (0.04842*params.valves.gas_lift_cd*params.valves.port_area_m2*pc2
         / sqrt(params.fluids.gas_relative_density*params.gas.temp_c2_k)
         * sqrt(2*k/(k-1)*(x**(2/k)-x**((k+1)/k))))
    return q*standard_gas_density(params)


def stage3_initial_state(params, cd):
    if cd.canonical_states is None:
        raise ValueError("Stage 3 requires the canonical Stage-2 state; no D reconstruction permitted")
    state = np.zeros(21)
    state[:14] = cd.canonical_states[:, -1]
    casing = state_from_mass(state[MC], params)
    fg, _ = stage3_factors(params, state[RHO], state[VB], state[VL])
    # Algebraic Pt2 as evaluated immediately before D, no state projection.
    state[PT2] = state[PT1]-state[RHO]*state[HB]*(G+fg*state[VB]**2/(2*params.geometry.tubing_diameter_m))
    state[PC1:RHOC2+1] = [cd.p_c1_pa[-1], cd.p_c2_pa[-1], casing["rho_c1"], casing["rho_c2"]]
    return state


def stage3_derivatives(params, s, glv_open=True):
    """Literal Stage-3 differential system; defined only for positive slug length."""
    geo, gas = params.geometry, params.gas
    D, H = geo.tubing_diameter_m, geo.valve_depth_m
    r = D/2
    At = tubing_area(D)
    Ab, Af = pi*(r-s[Y])**2, At-pi*(r-s[Y])**2
    L = H-s[HB]
    if L <= 0 or s[HB] <= 0 or not 0 < s[Y] < r or s[RHO] <= 0:
        raise ValueError("Stage 3 outside its pre-E geometric domain")
    ini = initial_stage_1(params)
    rl, vb, vf, vl, rho, hb = ini["rho_l"], s[VB], s[VF], s[VL], s[RHO], s[HB]
    fg, fl = stage3_factors(params, rho, vb, vl)
    force = gas_lift_valve_resultant_force(s[PC2], ini["p_bt"], s[PT1], params.valves.rv, params.valves.bellows_area_m2)
    # Identical correlation and valve mechanics to D-minus. Its source defect
    # is reported independently and prevents unconditional source certification.
    mgv = _gas_lift_mass_rate(s[PC2], s[PT1], s[RHOC2], params) if glv_open else 0.0
    qr = reservoir_inflow_from_pt1(params, s[PT1], rl)
    d = np.zeros(21)
    d[MC], d[MG], d[TRANSFER] = -mgv, mgv, mgv
    ktc = gas.z_tc*gas.gas_constant_j_mol_k*(gas.temp_c1_k+gas.temp_c2_k)/(2*gas.gas_molar_mass_kg_mol)
    ratio = exp(G*H/ktc)
    d[PC1] = 2*ktc*d[MC]/(geo.annulus_cross_area_m2*H*(1+ratio))
    d[PC2] = ratio*d[PC1]
    d[RHOC1] = d[PC1]*gas.gas_molar_mass_kg_mol/(gas.z_c1*gas.gas_constant_j_mol_k*gas.temp_c1_k)
    d[RHOC2] = d[PC2]*gas.gas_molar_mass_kg_mol/(gas.z_c2*gas.gas_constant_j_mol_k*gas.temp_c2_k)
    d[HB], d[DISPLACEMENT] = vb, vl
    d[Y] = (qr.rate_m3_s-Af*vf)/(2*pi*(r-s[Y])*hb)
    dAb = -2*pi*(r-s[Y])*d[Y]
    d[RHO] = (mgv-rho*(Ab*vb+hb*dAb))/(Ab*hb)
    d[PT1] = gas.z_t1*gas.gas_constant_j_mol_k*gas.temp_t1_k/gas.gas_molar_mass_kg_mol*d[RHO]
    # 4.1.53, without any minimum physical slug length.
    d[VL] = (-vl**2+(Af/At)*vf**2+(Ab/At)*vb**2
             +(s[PT2]-params.operating.surface_tubing_pressure_pa)/rl
             -G*L-fl*vl**2*L/(2*D)-0.3*vl**2)/L
    d[VB] = params.coefficients.bubble_velocity_a*d[VL]
    d[VF] = (At*d[VL]-Ab*d[VB]+dAb*(vf-vb))/Af
    d[PT2] = (d[PT1]-(fg*vb**2*hb/(2*D)+hb*G)*d[RHO]
              -fg*rho*vb*hb*d[VB]/D-(fg*rho*vb**2/(2*D)+rho*G)*vb)
    d[MFILM] = rl*(-hb*dAb+Af*vb)
    d[PROD], d[VRES] = At*vl, qr.rate_m3_s
    return d, dict(force=force, mgv=mgv, qres=qr.rate_m3_s,
                   inflow_valid=qr.physically_valid, fg=fg, fl=fl,
                   source_mgv=source_glv_rate(params, s[PC2], s[PT1]) if glv_open else 0.0)


def simulate_stage3(params, cd, *, max_time_s=180., max_step_s=.1, rtol=1e-8, atol=1e-10):
    """Integrate until E or a source-unsupported pre-E closure.

    A positive numerical endpoint clearance is a solver-domain diagnostic,
    never an E event. Refinement is available to audit the unilateral limit.
    """
    from .stage_de_dynamic import StageDEResult
    s0 = stage3_initial_state(params, cd)
    initially_open = bool(cd.valve_open[-1])
    H, D = params.geometry.valve_depth_m, params.geometry.tubing_diameter_m
    def close(_t, s):
        return stage3_derivatives(params, s, True)[1]["force"]
    close.direction = -1
    close.terminal = True
    # Integration cannot evaluate 4.1.53 on or beyond E. Domain event is
    # explicitly distinct from E; it does not manufacture a terminal state.
    clearance = max(1e-6, H*rtol)
    def domain(_t, s):
        return H-s[HB]-clearance
    domain.direction = -1
    domain.terminal = True
    if not initially_open:
        # No defined source transition for a finite pre-E closed interval.
        t, s, closed, tc = np.array([0.]), s0[:, None], True, 0.0
        message = "GLV_ALREADY_CLOSED_BEFORE_STAGE3"
    else:
        sol = solve_ivp(lambda t,s: stage3_derivatives(params,s,True)[0],
                        (0.,max_time_s),s0,events=(close,domain),method="Radau",
                        dense_output=True,max_step=max_step_s,rtol=rtol,atol=atol)
        t, s = sol.t, sol.y
        closed = bool(sol.t_events[0].size)
        tc = float(sol.t_events[0][0]) if closed else None
        message = ("SOURCE_AMBIGUITY_GLV_CLOSE_BEFORE_E" if closed else
                   "E_LIMIT_NOT_LOCALIZED" if sol.t_events[1].size else
                   "INTEGRATION_HORIZON" if sol.success else "NUMERICAL_FAILURE")
    opened = np.full(len(t), initially_open, dtype=bool)
    if closed:
        opened[-1] = False
    terms = [stage3_derivatives(params,s[:,i],bool(opened[i]))[1] for i in range(len(t))]
    array = lambda key: np.array([x[key] for x in terms])
    At, rl = tubing_area(D), initial_stage_1(params)["rho_l"]
    film = s[MFILM]/rl
    slug = At*(H-s[HB])
    liquid = film+slug+s[FB]+s[PROD]-s[VRES]
    ge = float(np.max(abs(s[MC]+s[MG]-s0[MC]-s0[MG]))/max(s0[MC]+s0[MG],1))
    le = float(np.max(abs(liquid-liquid[0]))/max(abs(liquid[0]),1e-12))
    Ab = pi*(D/2-s[Y])**2
    inventory_error = float(np.max(abs(s[MG]-s[RHO]*Ab*s[HB]))/max(s0[MG],1))
    eos_error = float(np.max(abs(s[PT1]-s[RHO]*params.gas.z_t1*params.gas.gas_constant_j_mol_k*params.gas.temp_t1_k/params.gas.gas_molar_mass_kg_mol))/max(s0[PT1],1))
    diagnostics = dict(terminal_reason=message, remaining_slug_length_m=float(H-s[HB,-1]),
        gas_inventory_relative_error=inventory_error, eos_relative_error=eos_error,
        transfer_casing_error_kg=float(np.max(abs(s[MC]-s0[MC]+s[TRANSFER]))),
        transfer_tubing_error_kg=float(np.max(abs(s[MG]-s0[MG]-s[TRANSFER]))),
        glv_rate_at_d=float(stage3_derivatives(params,s0,initially_open)[1]["mgv"]),
        source_glv_rate_at_d=float(source_glv_rate(params,s0[PC2],s0[PT1])),
        glv_open_at_d=initially_open, motor_valve_open=False,
        equation_numbers=list(EQUATIONS), closure_state=s[:,-1].tolist() if closed else None,
        numerical_clearance_m=clearance)
    pwb = s[PT1]+rl*G*((params.geometry.perforation_depth_m or H)-H)
    return StageDEResult(t,s[MC],s[MG],s[HB],np.full_like(t,H),s[VB],s[VL],At*s[VL],
        s[PROD],slug,film,s[FB],s[PC1],s[PC2],s[PT1],pwb,array("mgv"),array("force"),
        opened,False,None,ge,le,s[VF],s[RHO],bool(np.all(array("inflow_valid"))),s[VRES],
        canonical_states=s,film_thickness_m=s[Y],glv_closure_time_s=tc,
        integration_end_time_s=float(t[-1]),terminal_reason=message,
        source_diagnostics=diagnostics)
