import pytest

from gli.base_case import santos_50_70_80
from gli.block6m2d_compatibility import compatibility_residuals_c
from gli.stage1_dynamic import simulate_stage_1
from gli.stage_bc_common import simulate_stage_b_to_c_common
from gli.stage_cd_common import simulate_stage_c_to_d_common


@pytest.fixture(scope="module")
def chains():
    p = santos_50_70_80()
    a = simulate_stage_1(p, max_step_s=0.5)
    inherited = simulate_stage_b_to_c_common(p, stage_a_b=a, max_step_s=0.5)
    compatible = simulate_stage_b_to_c_common(
        p, stage_a_b=a, max_step_s=0.5, rhs_mode="santos_compatible"
    )
    return p, inherited, compatible


def test_inherited_c_state_exposes_santos_residuals(chains):
    p, inherited, _ = chains
    audit = compatibility_residuals_c(
        p, inherited.final_state, target_vgi_std_m3=inherited.target_volume_std_m3
    )
    by_name = {r.name: r for r in audit.residuals}
    assert inherited.certified
    assert not audit.compatible
    assert by_name["slug_mass_algebraic"].normalized > 1e-2
    assert by_name["film_mass_geometry"].normalized > 1e-1
    assert not by_name["slug_mass_algebraic"].can_change_at_c


def test_santos_compatible_bc_transports_c_restrictions(chains):
    p, _, compatible = chains
    audit = compatibility_residuals_c(
        p, compatible.final_state, target_vgi_std_m3=compatible.target_volume_std_m3
    )
    assert compatible.certified
    assert audit.compatible
    assert audit.max_normalized < 1e-6
    assert audit.state_classification["V_gi"] == "condicion de evento/transicion C"


def test_corrected_cd_from_inherited_state_remains_rejected(chains):
    p, inherited, _ = chains
    cd = simulate_stage_c_to_d_common(
        p, stage_b_c_common=inherited, max_step_s=0.5, rhs_mode="santos_corrected"
    )
    assert not cd.certified
    assert cd.liquid_balance_relative_error > 1e-2


def test_corrected_cd_from_compatible_c_state_is_certified(chains):
    p, _, compatible = chains
    cd = simulate_stage_c_to_d_common(
        p, stage_b_c_common=compatible, max_step_s=0.5, rhs_mode="santos_corrected"
    )
    assert cd.certified
    assert cd.event_d_reached
    assert cd.gas_balance_relative_error < 1e-6
    assert cd.liquid_balance_relative_error < 2e-8
    assert cd.eos_relative_error < 1e-5
