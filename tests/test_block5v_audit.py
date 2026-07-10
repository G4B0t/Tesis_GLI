import pytest
from gli.audit_block5v import audit_block5v
from gli.base_case import santos_50_70_80
from gli.stage_cd_dynamic import simulate_stage_c_to_d
from gli.stage_de_dynamic import simulate_stage_d_to_e

@pytest.fixture(scope='module')
def audit():
    p=santos_50_70_80(); cd=simulate_stage_c_to_d(p,max_step_s=.5); de=simulate_stage_d_to_e(p,stage_c_d=cd,max_step_s=.5)
    return audit_block5v(p,cd,de)

def test_nominal_tubing_is_not_internal_diameter(audit):
    assert audit.nominal_tubing_in==2.375
    assert audit.model_id_in==pytest.approx(1.995,rel=.002)
    assert audit.model_id_in<audit.nominal_tubing_in

def test_case_geometry_and_initial_inventory_are_traceable(audit):
    assert audit.H_m==1480.0 and audit.L_m==pytest.approx(412.6490362)
    assert audit.initial_volume_m3==pytest.approx(.8322,rel=.002)

def test_table_5_14_implies_different_initial_inventories(audit):
    assert audit.inferred_liao_initial_m3==pytest.approx(.52297,rel=1e-4)
    assert audit.inferred_santos_initial_m3==pytest.approx(.54098,rel=1e-4)
    assert abs(audit.initial_volume_m3-audit.inferred_liao_initial_m3)>.30
    assert not audit.same_case_confirmed

def test_inventory_partition_closes_without_coefficient_adjustment(audit):
    total=audit.produced_de_m3+audit.film_e_m3+audit.fallback_e_m3
    assert total==pytest.approx(audit.initial_volume_m3,rel=1e-11)
    assert audit.recovery_model==pytest.approx(audit.produced_de_m3/audit.initial_volume_m3)

def test_validation_gate_blocks_e_to_f(audit):
    assert not audit.may_advance_to_block6
