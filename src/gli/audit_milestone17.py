"""Reproducible M1.7 numerical report; stdout JSON, no repository writes."""
from __future__ import annotations

import json
from math import pi

import numpy as np

from .audit_block6m4_ef import build_corrected_e_state
from .initial_conditions import GRAVITY_M_S2 as G, initial_stage_1
from .reservoir import reservoir_inflow_from_pt1
from .stage_de_dynamic import simulate_stage_d_to_e
from .stage_de_santos import stage3_factors, simulate_stage3


def run_milestone17_audit():
    p, ab, bc, cd_common, cd, new = build_corrected_e_state(max_step_s=.5)
    old = simulate_stage_d_to_e(p, stage_c_d=cd, rhs_mode="milestone16_reference", max_step_s=.5)
    td = float(ab.opening_time_s+bc.event_c_time_s+cd_common.event_d_time_s)
    H, D = p.geometry.valve_depth_m, p.geometry.tubing_diameter_m
    rl = initial_stage_1(p)["rho_l"]

    def state(result):
        y = (float(result.film_thickness_m[-1]) if result.film_thickness_m is not None
             else D/2-np.sqrt((D/2)**2-result.film_volume_m3[-1]/(H*pi)))
        return dict(Pc1_pa=float(result.p_c1_pa[-1]), Pc2_pa=float(result.p_c2_pa[-1]),
            Pt1_pa=float(result.p_tubing_pa[-1]), casing_mass_kg=float(result.annulus_mass_kg[-1]),
            gas_mass_kg=float(result.bubble_mass_kg[-1]), rho_g_kg_m3=float(result.gas_density_kg_m3[-1]),
            v_g_m_s=float(result.v_b_m_s[-1]), v_f_m_s=float(result.film_velocity_m_s[-1]),
            y_m=float(y), qres_m3_s=reservoir_inflow_from_pt1(p, result.p_tubing_pa[-1], rl).rate_m3_s,
            produced_m3=float(result.produced_volume_m3[-1]), film_m3=float(result.film_volume_m3[-1]),
            reservoir_ledger_m3=float(result.reservoir_accumulated_m3[-1]))

    gas = p.gas
    rs = p.operating.surface_tubing_pressure_pa*gas.gas_molar_mass_kg_mol/(gas.z_ts*gas.gas_constant_j_mol_k*gas.temp_ts_k)
    kt3 = gas.z_t3*gas.gas_constant_j_mol_k*gas.temp_t3_k/gas.gas_molar_mass_kg_mol
    old_rho_eos = .5*(old.p_tubing_pa[-1]/kt3+rs)
    s = new.canonical_states
    algebraic_pt2 = np.array([row[3]-row[2]*row[8]*(G+stage3_factors(p,row[2],row[4],row[10])[0]*row[4]**2/(2*D)) for row in s.T])
    ktc = gas.z_tc*gas.gas_constant_j_mol_k*(gas.temp_c1_k+gas.temp_c2_k)/(2*gas.gas_molar_mass_kg_mol)
    casing_inventory = p.geometry.annulus_cross_area_m2*H*(s[15]+s[16])/(2*ktc)
    rates = [reservoir_inflow_from_pt1(p,pt,rl).rate_m3_s for pt in s[3]]
    convergence = []
    for step in (1., .5, .25):
        result = new if step == .5 else simulate_stage3(p, cd, max_step_s=step)
        convergence.append(dict(max_step_s=step, t_E_s=None,
            closure_elapsed_s=result.glv_closure_time_s, terminal_state=state(result),
            remaining_slug_m=float(H-result.h_b_m[-1])))
    return dict(status="BLOCKED_BY_SOURCE", source_status="NOT_SOURCE_CERTIFIED_A_TO_E",
        t_D_s=td, identity_D_max_absolute_error=float(np.max(abs(s[:14,0]-cd.canonical_states[:,-1]))),
        canonical_D=s[:14,0].tolist(),
        milestone16=dict(GLV_open_D=False, closure="forced at D; not a mechanical event",
            t_E_s=td+old.event_e_time_s, duration_DE_s=old.event_e_time_s, E=state(old),
            stage42=dict(h_l_m=0., basis="historical limiting assumption only", Pt3_pa=float(old.p_tubing_pa[-1]),
                rho_inventory_kg_m3=float(old.gas_density_kg_m3[-1]), rho_EOS_kg_m3=float(old_rho_eos),
                EOS_relative_residual=float(abs(old.gas_density_kg_m3[-1]-old_rho_eos)/old_rho_eos),
                hydrostatic_residual_pa=0., compatible=False)),
        milestone17=dict(GLV_open_D=bool(new.valve_open[0]), GLV_rate_D_kg_s=float(new.gl_mass_rate_kg_s[0]),
            t_GLV_close_s=td+new.glv_closure_time_s, D_to_close_s=new.glv_closure_time_s,
            t_E_s=None, duration_DE_s=None, close_to_E_s=None, E=None, GLV_at_E=None, stage42=None,
            terminal_reason=new.terminal_reason, at_closure=state(new), source_diagnostics=new.source_diagnostics),
        balances=dict(gas_relative=new.gas_balance_relative_error, liquid_relative=new.liquid_balance_relative_error,
            maximum_eq27_algebraic_drift_pa=float(np.max(abs(s[14]-algebraic_pt2))),
            maximum_casing_eq6_inventory_offset_kg=float(np.max(abs(s[0]-casing_inventory))),
            inventory_relative=new.source_diagnostics["gas_inventory_relative_error"],
            eos_relative=new.source_diagnostics["eos_relative_error"]),
        convergence=dict(scope="D to GLV closure ONLY; E is unavailable", runs=convergence),
        reservoir=dict(valid=new.reservoir_inflow_valid, min_rate_m3_s=min(rates), max_rate_m3_s=max(rates)),
        peak_velocities_m_s=dict(old_gas=float(np.max(abs(old.v_b_m_s))),new_gas=float(np.max(abs(new.v_b_m_s))),
            old_film=float(np.max(abs(old.film_velocity_m_s))),new_film=float(np.max(abs(new.film_velocity_m_s))),
            old_slug=float(np.max(abs(old.v_l_m_s))),new_slug=float(np.max(abs(new.v_l_m_s)))),
        downstream=dict(EF_ran=False, FG_ran=False, G_reached=False, t_F_s=None, t_G_s=None),
        warning="HIGH_VELOCITY_PLAUSIBILITY_REVIEW_PENDING")


if __name__ == "__main__":
    print(json.dumps(run_milestone17_audit(), indent=2, allow_nan=False))
