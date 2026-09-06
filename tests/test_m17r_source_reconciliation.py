"""M1.7R regression tests for the source-qualified B--E prefix."""

from inspect import getsource
from math import sqrt

import numpy as np
import pytest

from gli.audit_block6m4_ef import build_corrected_e_state
from gli.initial_conditions import GRAVITY_M_S2
from gli.stage1_dynamic import state_from_mass
from gli.stage_de_santos import stage3_derivatives
from gli.valves import santos_glv_mass_rate


@pytest.fixture(scope="module")
def chain():
    return build_corrected_e_state(max_step_s=0.5)


def independent_santos_glv_rate(params, pc2, pt1):
    """Independent 4.1.13/.15 calculation, including the stated extension."""
    if pc2 <= pt1:
        return 0.0
    k = params.valves.adiabatic_constant
    r_critical = (2.0 / (k + 1.0)) ** (k / (k - 1.0))
    ratio = max(pt1 / pc2, r_critical)
    q_standard = (
        0.04842
        * params.valves.gas_lift_cd
        * params.valves.port_area_m2
        * pc2
        / sqrt(params.fluids.gas_relative_density * params.gas.temp_c2_k)
        * sqrt(2.0 * k / (k - 1.0) * (ratio ** (2.0 / k) - ratio ** ((k + 1.0) / k)))
    )
    rho_standard = (
        params.gas.standard_pressure_pa
        * params.gas.gas_molar_mass_kg_mol
        / (params.gas.gas_constant_j_mol_k * params.gas.standard_temperature_k)
    )
    return q_standard * rho_standard


def test_santos_glv_413_415_subcritical_and_critical_regimes(chain):
    p = chain[0]
    k = p.valves.adiabatic_constant
    r_critical = (2.0 / (k + 1.0)) ** (k / (k - 1.0))
    pc2 = 6.0e6
    subcritical_pt1 = 0.9 * pc2
    critical_pt1 = 0.2 * pc2
    assert santos_glv_mass_rate(pc2, subcritical_pt1, p) == pytest.approx(
        independent_santos_glv_rate(p, pc2, subcritical_pt1), rel=1e-14
    )
    critical_rate = santos_glv_mass_rate(pc2, critical_pt1, p)
    assert critical_rate == pytest.approx(
        independent_santos_glv_rate(p, pc2, critical_pt1), rel=1e-14
    )
    assert critical_rate == pytest.approx(
        santos_glv_mass_rate(pc2, r_critical * pc2, p), rel=1e-14
    )


def test_source_route_uses_one_glv_function_across_b_c_d_e(chain):
    # This guards source-route imports without accepting the historical proxy.
    from gli import stage_bc_common, stage_cd_common, stage_de_santos

    for module in (stage_bc_common, stage_cd_common, stage_de_santos):
        source = getsource(module)
        assert "santos_glv_mass_rate" in source
        assert "_historical_glv_proxy_mass_rate" not in source

    p, _ab, bc, _cd_common, cd, de = chain
    state_b = bc.states[:, 0]
    state_d = de.canonical_states[:, 0]
    casing_b = state_from_mass(float(state_b[0]), p)
    assert santos_glv_mass_rate(casing_b["p_c2"], state_b[3], p) == pytest.approx(
        independent_santos_glv_rate(p, casing_b["p_c2"], state_b[3]), rel=1e-12
    )
    assert cd.gl_mass_rate_kg_s[-1] == pytest.approx(
        independent_santos_glv_rate(p, cd.p_c2_pa[-1], cd.p_tubing_pa[-1]), rel=1e-12
    )
    assert de.gl_mass_rate_kg_s[0] == pytest.approx(
        independent_santos_glv_rate(p, state_d[16], state_d[3]), rel=1e-12
    )


def test_eq27_eq28_use_the_same_frozen_bubble_friction(chain):
    p, _ab, bc, cd_common, cd, de = chain
    assert bc.bubble_friction_factor == pytest.approx(cd_common.bubble_friction_factor)
    assert cd_common.bubble_friction_factor == pytest.approx(cd.bubble_friction_factor)
    assert cd.bubble_friction_factor > 0.0
    s = de.canonical_states
    f_b = cd.bubble_friction_factor
    D = p.geometry.tubing_diameter_m
    eq27_pt2 = s[3] - s[2] * s[8] * (GRAVITY_M_S2 + f_b * s[4] ** 2 / (2.0 * D))
    assert np.max(np.abs(s[14] - eq27_pt2)) < 1e-3
    derivative, _ = stage3_derivatives(
        p, s[:, len(de.time_s) // 2], True, bubble_friction_factor=f_b
    )
    assert np.isfinite(derivative).all()


def test_m17r_prefix_preserves_d_identity_and_internal_gas_transfer(chain):
    _p, _ab, _bc, cd_common, cd, de = chain
    np.testing.assert_array_equal(cd.canonical_states, cd_common.states)
    np.testing.assert_array_equal(
        de.canonical_states[:14, 0], cd.canonical_states[:, -1]
    )
    s = de.canonical_states
    np.testing.assert_allclose(s[0] + s[1], s[0, 0] + s[1, 0], rtol=1e-12)
    np.testing.assert_allclose(s[0] - s[0, 0], -s[20], atol=1e-10)
    np.testing.assert_allclose(s[1] - s[1, 0], s[20], atol=1e-10)
