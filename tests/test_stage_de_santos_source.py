"""Independent residuals of Table 5.1; passing balances is not flow certification."""

from dataclasses import replace
from math import exp, log10, pi, sqrt
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.integrate import simpson

from gli.audit_block6m4_ef import build_corrected_e_state
from gli.initial_conditions import initial_stage_1
from gli.stage_de_santos import (
    simulate_stage3,
    stage3_derivatives,
    stage3_initial_state,
)
from gli.stage_ef_dynamic import (
    audit_stage_42_initial_state,
    default_stage_ef_parameters,
)

G = 9.80665


@pytest.fixture(scope="module")
def chain():
    return build_corrected_e_state(max_step_s=0.5)


def independent_residuals(p, s, d, opened, bubble_friction_factor):
    """No RHS closure helpers used: each source residual has its own scale."""
    (
        mc,
        mg,
        rho,
        pt1,
        vb,
        vf,
        y,
        film,
        hb,
        displacement,
        vl,
        vgi,
        fb,
        prod,
        pt2,
        pc1,
        pc2,
        rc1,
        rc2,
        vr,
        transfer,
    ) = s
    D, H = p.geometry.tubing_diameter_m, p.geometry.valve_depth_m
    r, At = D / 2, pi * D**2 / 4
    Ab = pi * (r - y) ** 2
    Af, L = At - Ab, H - hb
    gas = p.gas
    rl = initial_stage_1(p)["rho_l"]
    roughness = default_stage_ef_parameters().roughness.value

    def friction(re):
        # Independently reproduce the inherited closure, not certify its source.
        a = (2.457 * log10(1 / ((7 / re) ** 0.9 + 0.27 * roughness / D))) ** 16
        b = (37530 / re) ** 16
        return 8 * ((8 / re) ** 12 + (a + b) ** (-1.5)) ** (1 / 12)

    fg = bubble_friction_factor
    fl = friction(rl * abs(vl) * D / p.fluids.liquid_viscosity_pa_s)
    ktc = (
        gas.z_tc
        * gas.gas_constant_j_mol_k
        * (gas.temp_c1_k + gas.temp_c2_k)
        / (2 * gas.gas_molar_mass_kg_mol)
    )
    kc1 = (
        gas.z_c1 * gas.gas_constant_j_mol_k * gas.temp_c1_k / gas.gas_molar_mass_kg_mol
    )
    kc2 = (
        gas.z_c2 * gas.gas_constant_j_mol_k * gas.temp_c2_k / gas.gas_molar_mass_kg_mol
    )
    kt1 = (
        gas.z_t1 * gas.gas_constant_j_mol_k * gas.temp_t1_k / gas.gas_molar_mass_kg_mol
    )
    k = p.valves.adiabatic_constant
    critical = (2 / (k + 1)) ** (k / (k - 1))
    ratio = max(pt1 / pc2, critical) if pc2 > pt1 else 1.0
    rho_std = (
        p.gas.standard_pressure_pa
        * p.gas.gas_molar_mass_kg_mol
        / (p.gas.gas_constant_j_mol_k * p.gas.standard_temperature_k)
    )
    rate = (
        (
            0.04842
            * p.valves.gas_lift_cd
            * p.valves.port_area_m2
            * pc2
            / sqrt(p.fluids.gas_relative_density * p.gas.temp_c2_k)
            * sqrt(2 * k / (k - 1) * (ratio ** (2 / k) - ratio ** ((k + 1) / k)))
            * rho_std
        )
        if opened and pc2 > pt1
        else 0.0
    )
    pwb = pt1 + rl * G * (p.geometry.perforation_depth_m - H)
    qr = p.operating.productivity_index_m3_s_pa * (
        p.operating.reservoir_static_pressure_pa - pwb
    )
    # Values and dimensional normalization scales: kg/s, Pa/s, m/s,
    # m3/s, or m2/s2 as recorded below; never divide by a vanishing residual.
    return {
        6: (
            (d[15] + d[16]) * p.geometry.annulus_cross_area_m2 * H / (2 * ktc) - d[0],
            max(abs(rate), 0.01),
            "kg/s",
        ),
        9: (d[0] + rate, max(abs(rate), 0.01), "kg/s"),
        17: (d[16] - exp(G * H / ktc) * d[15], max(abs(d[16]), 1), "Pa/s"),
        18: (d[15] - kc1 * d[17], max(abs(d[15]), 1), "Pa/s"),
        19: (d[16] - kc2 * d[18], max(abs(d[16]), 1), "Pa/s"),
        26: (
            Ab * hb * d[2]
            + rho * Ab * d[8]
            - 2 * pi * (r - y) * rho * hb * d[6]
            - rate,
            max(abs(rate), 0.01),
            "kg/s",
        ),
        28: (
            d[14]
            - d[3]
            + (fg * vb**2 * hb / (2 * D) + hb * G) * d[2]
            + fg * rho * vb * hb * d[4] / D
            + (fg * rho * vb**2 / (2 * D) + rho * G) * d[8],
            max(abs(d[3]), 1),
            "Pa/s",
        ),
        32: (d[9] - vl, max(abs(vl), 1), "m/s"),
        35: (2 * pi * (r - y) * hb * d[6] + Af * vf - qr, max(abs(qr), 1e-6), "m3/s"),
        40: (At * d[9] - Ab * d[8] - Af * vf, max(abs(At * vl), 1e-6), "m3/s"),
        48: (d[3] - kt1 * d[2], max(abs(d[3]), 1), "Pa/s"),
        50: (
            d[4] - p.coefficients.bubble_velocity_a * d[10],
            max(abs(d[4]), 1),
            "m/s2",
        ),
        53: (
            L * d[10]
            + vl**2
            - Af / At * vf**2
            - Ab / At * vb**2
            - (pt2 - p.operating.surface_tubing_pressure_pa) / rl
            + G * L
            + fl * vl**2 * L / (2 * D)
            + 0.3 * vl**2,
            max(G * L, 1),
            "m2/s2",
        ),
    }


@pytest.mark.parametrize("equation", [6, 9, 17, 18, 19, 26, 28, 32, 35, 40, 48, 50, 53])
def test_all_stage3_source_residuals(equation, chain):
    p, *_prefix, cd, de = chain
    for index in (0, len(de.time_s) // 2, -1):
        s = de.canonical_states[:, index]
        d, _ = stage3_derivatives(
            p,
            s,
            bool(de.valve_open[index]),
            bubble_friction_factor=cd.bubble_friction_factor,
        )
        value, scale, units = independent_residuals(
            p, s, d, bool(de.valve_open[index]), cd.bubble_friction_factor
        )[equation]
        assert units
        assert abs(value) / scale < 1e-8


def test_d_is_canonical_identity_including_valve_and_flow(chain):
    p, ab, bc, cd_common, cd, de = chain
    np.testing.assert_array_equal(cd.canonical_states, cd_common.states)
    np.testing.assert_array_equal(
        de.canonical_states[:14, 0], cd.canonical_states[:, -1]
    )
    assert de.valve_open[0] == cd.valve_open[-1]
    assert de.gl_mass_rate_kg_s[0] == pytest.approx(cd.gl_mass_rate_kg_s[-1], rel=1e-12)
    with pytest.raises(ValueError, match="canonical"):
        stage3_initial_state(p, replace(cd, canonical_states=None))


def test_glv_rate_is_source_consistent_at_d(chain):
    p, *_, de = chain
    s = de.canonical_states[:, 0]
    k, x = p.valves.adiabatic_constant, s[3] / s[16]
    assert x > (2 / (k + 1)) ** (
        k / (k - 1)
    )  # base is unchoked; no critical extrapolation
    rho_std = (
        p.gas.standard_pressure_pa
        * p.gas.gas_molar_mass_kg_mol
        / (p.gas.gas_constant_j_mol_k * p.gas.standard_temperature_k)
    )
    source_rate = (
        0.04842
        * p.valves.gas_lift_cd
        * p.valves.port_area_m2
        * s[16]
        / sqrt(p.fluids.gas_relative_density * p.gas.temp_c2_k)
        * sqrt(2 * k / (k - 1) * (x ** (2 / k) - x ** ((k + 1) / k)))
        * rho_std
    )
    assert de.source_diagnostics["source_glv_rate_at_d"] == pytest.approx(
        source_rate, rel=1e-12
    )
    assert de.source_diagnostics["glv_rate_at_d"] > 0
    assert de.source_diagnostics["source_glv_rate_at_d"] == pytest.approx(
        de.gl_mass_rate_kg_s[0], rel=1e-12
    )
    assert not de.source_certified


def test_dynamic_closure_retains_continuous_state_and_zeroes_transfer(chain):
    p, *_, de = chain
    assert de.glv_closure_time_s > 0
    assert np.all(de.valve_open[:-1]) and not de.valve_open[-1]
    s = de.canonical_states[:, -1]
    ini = initial_stage_1(p)
    force = (
        (s[16] - ini["p_bt"]) - (s[16] - s[3]) * p.valves.rv
    ) * p.valves.bellows_area_m2
    assert abs(force) < 1e-7
    np.testing.assert_array_equal(s, de.source_diagnostics["closure_state"])
    before, _ = stage3_derivatives(p, s, True)
    after, _ = stage3_derivatives(p, s, False)
    assert before[1] > 0
    np.testing.assert_array_equal(after[[0, 1, 20]], 0.0)
    assert de.gl_mass_rate_kg_s[-1] == 0
    # No post-closure interval is claimed: the unsupported topology is blocked.
    assert de.time_s[-1] == de.glv_closure_time_s


def test_motor_closed_and_no_double_counting_of_liquid(chain):
    p, *_, de = chain
    s = de.canonical_states
    rl = initial_stage_1(p)["rho_l"]
    At = pi * p.geometry.tubing_diameter_m**2 / 4
    Ab = pi * (p.geometry.tubing_diameter_m / 2 - s[6]) ** 2
    np.testing.assert_array_equal(s[11], np.full(s.shape[1], s[11, 0]))
    np.testing.assert_array_equal(s[12], np.full(s.shape[1], s[12, 0]))
    np.testing.assert_allclose(s[7] / rl, (At - Ab) * s[8], rtol=1e-8)
    liquid = (
        (At - Ab) * s[8]
        + At * (p.geometry.valve_depth_m - s[8])
        + s[12]
        + s[13]
        - s[19]
    )
    np.testing.assert_allclose(liquid, liquid[0], rtol=1e-8)


def test_independent_gas_inventory_and_transfer(chain):
    p, *_, de = chain
    s = de.canonical_states
    Ab = pi * (p.geometry.tubing_diameter_m / 2 - s[6]) ** 2
    np.testing.assert_allclose(s[0] + s[1], s[0, 0] + s[1, 0], rtol=1e-12)
    np.testing.assert_allclose(s[1], s[2] * Ab * s[8], rtol=1e-8)
    np.testing.assert_allclose(s[0] - s[0, 0], -s[20], atol=1e-10)
    np.testing.assert_allclose(s[1] - s[1, 0], s[20], atol=1e-10)


def test_dynamic_ipr_and_production_ledgers_independently_integrated(chain):
    p, *_, de = chain
    s = de.canonical_states
    rl = initial_stage_1(p)["rho_l"]
    pwb = s[3] + rl * G * (p.geometry.perforation_depth_m - p.geometry.valve_depth_m)
    qr = p.operating.productivity_index_m3_s_pa * (
        p.operating.reservoir_static_pressure_pa - pwb
    )
    assert np.all(qr > 0)
    assert np.ptp(qr) > 1e-6
    assert simpson(qr, x=de.time_s) == pytest.approx(s[19, -1], abs=1e-9)
    assert simpson(
        pi * p.geometry.tubing_diameter_m**2 / 4 * s[10], x=de.time_s
    ) == pytest.approx(s[13, -1] - s[13, 0], abs=1e-8)


@pytest.mark.parametrize("length", [0.5, 0.1])
def test_exact_53_below_former_floor(length, chain):
    p, *_, de = chain
    s = de.canonical_states[:, 0].copy()
    s[8] = p.geometry.valve_depth_m - length
    _p, *_prefix, cd, _de = chain
    d, _ = stage3_derivatives(p, s, bubble_friction_factor=cd.bubble_friction_factor)
    value, scale, _ = independent_residuals(p, s, d, True, cd.bubble_friction_factor)[
        53
    ]
    assert abs(value) / scale < 1e-8


def test_no_fake_e_and_closure_convergence(chain):
    p, *_, cd, base = chain
    runs = [simulate_stage3(p, cd, max_step_s=step) for step in (1.0, 0.5, 0.25)]
    for result in runs:
        assert not result.event_e_reached and result.event_e_time_s is None
        assert result.terminal_reason == "SOURCE_AMBIGUITY_GLV_CLOSE_BEFORE_E"
        assert result.source_diagnostics["remaining_slug_length_m"] > 100
        assert result.glv_closure_time_s == pytest.approx(
            base.glv_closure_time_s, abs=1e-5
        )
        np.testing.assert_allclose(
            result.canonical_states[:, -1],
            base.canonical_states[:, -1],
            rtol=1e-6,
            atol=1e-8,
        )
    with pytest.raises(ValueError, match="Physical E is unavailable"):
        audit_stage_42_initial_state(p, base)


def synthetic_e(p, *, height=1.0):
    """An analytical fixture, NEVER a manufactured result for the base case."""
    H, r = p.geometry.valve_depth_m, p.geometry.tubing_diameter_m / 2
    y, rho = 0.002, 25.0
    Ab = pi * (r - y) ** 2
    gas = p.gas
    rs = (
        p.operating.surface_tubing_pressure_pa
        * gas.gas_molar_mass_kg_mol
        / (gas.z_ts * gas.gas_constant_j_mol_k * gas.temp_ts_k)
    )
    pt3 = (
        gas.z_t3
        * gas.gas_constant_j_mol_k
        * gas.temp_t3_k
        / gas.gas_molar_mass_kg_mol
        * (2 * rho - rs)
    )
    pt1 = pt3 + initial_stage_1(p)["rho_l"] * G * height
    array = lambda v: np.array([v])
    return SimpleNamespace(
        event_e_reached=True,
        valve_open=array(False),
        lower_liquid_height_m=array(height),
        lower_liquid_height_source="analytic unit fixture",
        film_thickness_m=array(y),
        gas_pressure_at_liquid_top_pa=array(pt3),
        p_tubing_pa=array(pt1),
        bubble_mass_kg=array(rho * Ab * (H - height)),
        gas_density_kg_m3=array(rho),
        film_volume_m3=array((pi * r * r - Ab) * H),
    )


def test_stage42_accepts_consistent_nonzero_lower_height_without_projection(chain):
    p = chain[0]
    e = synthetic_e(p)
    before = e.gas_density_kg_m3.copy()
    audit = audit_stage_42_initial_state(p, e)
    assert audit.compatible and audit.liquid_height_m == 1.0
    np.testing.assert_array_equal(e.gas_density_kg_m3, before)
    e.gas_density_kg_m3 *= 1.01
    assert not audit_stage_42_initial_state(p, e).compatible


def test_stage42_requires_height_provenance_and_preserves_hydrostatic_gate(chain):
    p = chain[0]
    e = synthetic_e(p)
    e.lower_liquid_height_source = None
    with pytest.raises(ValueError, match="source-derived"):
        audit_stage_42_initial_state(p, e)
    e = synthetic_e(p)
    e.gas_pressure_at_liquid_top_pa += 1.0
    assert not audit_stage_42_initial_state(p, e).compatible
