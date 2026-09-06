import numpy as np
import pytest

from gli.base_case import santos_50_70_80
from gli.geometry import tubing_area
from gli.initial_conditions import initial_stage_1
from gli.reservoir import reservoir_inflow_from_pt1
from gli.stage1_dynamic import simulate_stage_1
from gli.stage_bc_common import (
    I_HB,
    I_HL,
    I_VF,
    I_VG,
    I_VL,
    I_Y,
    simulate_stage_b_to_c_common,
)
from gli.stage_cd_common import _cd_terms_santos, simulate_stage_c_to_d_common


@pytest.fixture(scope="module")
def chain():
    p = santos_50_70_80()
    a = simulate_stage_1(p, max_step_s=0.5)
    b = simulate_stage_b_to_c_common(p, stage_a_b=a, max_step_s=0.5)
    old = simulate_stage_c_to_d_common(p, stage_b_c_common=b, max_step_s=0.5)
    new = simulate_stage_c_to_d_common(
        p, stage_b_c_common=b, max_step_s=0.5, rhs_mode="santos_corrected"
    )
    return p, a, b, old, new


def test_corrected_rhs_separates_kinematics_and_reservoir_feed(chain):
    p, _, b, _, _ = chain
    d = _cd_terms_santos(b.final_state, p, True)[0]
    assert d[I_HL] == pytest.approx(b.final_state[I_VL])
    assert d[I_HB] == pytest.approx(b.final_state[I_VG])


def test_santos_film_mass_equation_4135_closes_instantaneously(chain):
    p, _, b, _, _ = chain
    s = b.final_state
    d = _cd_terms_santos(s, p, True)[0]
    r = p.geometry.tubing_diameter_m / 2
    At = tubing_area(2 * r)
    Ab = np.pi * (r - s[I_Y]) ** 2
    Af = At - Ab
    qres = reservoir_inflow_from_pt1(
        p, float(s[3]), initial_stage_1(p)["rho_l"]
    ).rate_m3_s
    residual = 2 * np.pi * (r - s[I_Y]) * s[I_HB] * d[I_Y] + Af * s[I_VF] - qres
    assert abs(residual) < 1e-12


def test_incompatible_candidate_remains_rejected_after_dynamic_ipr(chain):
    p, a, b, old, new = chain
    assert new.event_d_time_s != pytest.approx(old.event_d_time_s)
    assert not new.certified
    assert new.liquid_balance_relative_error > 1e-1


def test_no_silent_switch_to_candidate_in_api_default(chain):
    _, _, _, old, _ = chain
    assert old.certified
    assert old.event_d_time_s != pytest.approx(422.0498545, rel=2e-7)
