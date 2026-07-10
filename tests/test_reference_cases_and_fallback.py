import pytest
from dataclasses import FrozenInstanceError
from gli.reference_cases import SANTOS_50_70_80,LIAO_TABLE_5_14,compare_metric
from gli.fallback import falling_film_velocity_m_s,fallback_rate_m3_s

def test_reference_cases_are_immutable_and_source_scoped():
    assert SANTOS_50_70_80.classification=='full_case'
    assert LIAO_TABLE_5_14.classification=='partial_benchmark'
    assert LIAO_TABLE_5_14.inputs['geometry'] is None
    with pytest.raises(TypeError): SANTOS_50_70_80.inputs['L_over_H']=.6
    with pytest.raises(FrozenInstanceError): SANTOS_50_70_80.case_id='x'

def test_cross_case_comparison_is_forbidden():
    with pytest.raises(ValueError,match='Cross-case'): compare_metric(SANTOS_50_70_80.case_id,LIAO_TABLE_5_14.case_id,'liquid_recovery',.76)

def test_only_allowed_metrics_can_be_compared():
    value,target=compare_metric(SANTOS_50_70_80.case_id,SANTOS_50_70_80.case_id,'event_d_absolute_s',291)
    assert (value,target)==(291,290)
    with pytest.raises(ValueError,match='not allowed'): compare_metric(SANTOS_50_70_80.case_id,SANTOS_50_70_80.case_id,'total_produced_m3',.6)

def test_nusselt_fallback_is_mechanistic_and_monotonic():
    assert falling_film_velocity_m_s(0,850,.003)==0
    assert falling_film_velocity_m_s(.0004,850,.003)>falling_film_velocity_m_s(.0002,850,.003)>0
    assert fallback_rate_m3_s(.050673,.0003,850,.003)>0
