import pytest
from gli.block6p_parameters import *

def p(v,u,c,s,lo,hi): return ScalarParameter(v,u,c,s,lo,hi)

def test_churchill_matches_laminar_and_is_positive_all_regimes():
    assert churchill_darcy(1000,0) == pytest.approx(.064,rel=.01)
    closure=FrictionClosure(p(4.5e-5,'m',ProvenanceClass.BIBLIOGRAPHIC,'commercial steel range',1e-6,2e-4))
    assert friction_factor(1000,.05,closure)[1]=='laminar'
    assert friction_factor(3000,.05,closure)[1]=='transitional'
    assert friction_factor(1e5,.05,closure)[1]=='turbulent'
    assert all(friction_factor(re,.05,closure)[0]>0 for re in (100,2300,3000,4000,1e6))

def test_parameter_provenance_and_bounds_are_mandatory():
    with pytest.raises(ValueError): p(2,'m',ProvenanceClass.INFERRED,'x',0,1)

def test_calibrated_threshold_hysteresis_closes_and_never_reopens():
    m=CalibratedThresholdMode(p(2e6,'Pa',ProvenanceClass.CALIBRATED,'fit A-B',1.8e6,2.2e6),p(1e6,'Pa',ProvenanceClass.CALIBRATED,'fit E',.8e6,1.2e6))
    pc=[4e6,3e6,2.5e6,2.2e6,2.0e6];pt=[1e6,1.5e6,1.7e6,1.8e6,1.9e6]
    out=certify_closed_path(m,pc,pt,True)
    assert out['certified'] and out['reopened_index'] is None

def test_mechanical_mode_has_explicit_parameters_and_no_hidden_force():
    b=ProvenanceClass.INFERRED
    m=MechanicalValveMode(p(.001,'m2',b,'drawing pending',.0008,.0012),p(.0002,'m2',b,'drawing pending',.0001,.0003),p(3e6,'Pa',b,'Santos eq 5.1 inference',2.8e6,3.2e6),p(10,'N',b,'datasheet pending',0,20),p(2,'N',b,'datasheet pending',0,5),p(5,'N',b,'assumed spread',0,10),p(5,'N',b,'assumed spread',0,10))
    state,force=valve_state_mechanical(m,1e6,1e6,True)
    assert state is False and force < 0

def test_sensitivity_reports_uncertainty_span():
    out=one_at_a_time_sensitivity(2,1,3,lambda x:x*x)
    assert out=={'low':1,'base':4,'high':9,'relative_span':2.0}
