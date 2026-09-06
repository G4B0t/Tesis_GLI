"""Reproducible M1.7R reconciliation report; stdout JSON, no writes."""

from __future__ import annotations

import json

import numpy as np

from .audit_block6m4_ef import build_corrected_e_state
from .initial_conditions import GRAVITY_M_S2 as G
from .stage_de_santos import simulate_stage3

M17_BASELINE = {
    "t_D_s": 509.849089816,
    "d_to_close_s": 28.564826511526,
    "remaining_slug_m": 181.107955227,
    "glv_rate_D_kg_s": 0.197318713692,
}


def _terminal_state(result):
    s = result.canonical_states[:, -1]
    return {
        "Pc1_pa": float(s[15]),
        "Pc2_pa": float(s[16]),
        "Pt1_pa": float(s[3]),
        "casing_mass_kg": float(s[0]),
        "bubble_mass_kg": float(s[1]),
        "rho_g_kg_m3": float(s[2]),
        "v_b_m_s": float(s[4]),
        "v_f_m_s": float(s[5]),
        "v_l_m_s": float(s[10]),
    }


def run_milestone17r_audit():
    """Run the reconciled prefix and report only the physically available end."""
    p, ab, bc, cd_common, cd, de = build_corrected_e_state(max_step_s=0.5)
    s = de.canonical_states
    t_b = float(ab.opening_time_s)
    t_c = t_b + float(bc.event_c_time_s)
    t_d = t_c + float(cd_common.event_d_time_s)
    f_b = float(cd.bubble_friction_factor)
    D = p.geometry.tubing_diameter_m
    eq27_pt2 = s[3] - s[2] * s[8] * (G + f_b * s[4] ** 2 / (2.0 * D))
    convergence = []
    for max_step_s in (1.0, 0.5, 0.25):
        result = (
            de if max_step_s == 0.5 else simulate_stage3(p, cd, max_step_s=max_step_s)
        )
        convergence.append(
            {
                "max_step_s": max_step_s,
                "d_to_close_s": float(result.glv_closure_time_s),
                "Pt1_close_pa": float(result.p_tubing_pa[-1]),
                "bubble_mass_close_kg": float(result.bubble_mass_kg[-1]),
                "event_E_reached": bool(result.event_e_reached),
            }
        )
    return {
        "milestone": "M1.7R",
        "status": "BLOCKED_BY_SOURCE",
        "source_status": "NOT_SOURCE_CERTIFIED_A_TO_E",
        "basis": {
            "glv": "Santos 4.1.13/.15 central mass-rate function, with declared critical-flow extension",
            "friction": "4.1.28 is differentiated from 4.1.27 without df_B/dt; f_B is seeded at B and frozen B-to-E",
            "source_missing": "The reviewed Santos pages do not state the numerical correlation for f_B.",
        },
        "times_absolute_s": {
            "B": t_b,
            "C": t_c,
            "D": t_d,
            "GLV_close": t_d + float(de.glv_closure_time_s),
            "E": None,
        },
        "source_chain": {
            "B_to_C_reached": bool(bc.event_c_reached),
            "C_to_D_reached": bool(cd_common.event_d_reached),
            "GLV_open_at_D": bool(de.valve_open[0]),
            "GLV_rate_at_D_kg_s": float(de.gl_mass_rate_kg_s[0]),
            "frozen_bubble_friction_factor": f_b,
        },
        "closure_before_E": {
            "D_to_close_s": float(de.glv_closure_time_s),
            "remaining_slug_m": float(p.geometry.valve_depth_m - de.h_b_m[-1]),
            "terminal_state": _terminal_state(de),
            "terminal_reason": de.terminal_reason,
            "E_reached": bool(de.event_e_reached),
        },
        "M17_comparison": {
            "baseline": M17_BASELINE,
            "delta_D_to_close_s": float(
                de.glv_closure_time_s - M17_BASELINE["d_to_close_s"]
            ),
            "delta_remaining_slug_m": float(
                p.geometry.valve_depth_m
                - de.h_b_m[-1]
                - M17_BASELINE["remaining_slug_m"]
            ),
            "delta_GLV_rate_D_kg_s": float(
                de.gl_mass_rate_kg_s[0] - M17_BASELINE["glv_rate_D_kg_s"]
            ),
        },
        "verification": {
            "D_identity_max_abs_error": float(
                np.max(np.abs(s[:14, 0] - cd.canonical_states[:, -1]))
            ),
            "eq27_max_abs_drift_pa": float(np.max(np.abs(s[14] - eq27_pt2))),
            "gas_balance_relative": float(de.gas_balance_relative_error),
            "liquid_balance_relative": float(de.liquid_balance_relative_error),
            "convergence": convergence,
        },
        "downstream": {
            "stage42_executed": False,
            "reason": "Physical E is unavailable; GLV closes materially before E.",
        },
    }


if __name__ == "__main__":
    print(json.dumps(run_milestone17r_audit(), indent=2, allow_nan=False))
