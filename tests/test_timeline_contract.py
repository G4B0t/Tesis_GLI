import pytest
from gli_api.schemas import SimulationInputs
from gli_api.simulation_service import simulate
from gli_api.timeline_service import build_timeline

@pytest.fixture(scope='module')
def timeline():
    i=SimulationInputs(tubingDiameter=.050673,valveDepth=1480,slugLength=412.5,
      surfaceTubingPressure=.788,injectionPressure=6.966,api=40,bsw=50,
      gasRelativeDensity=.7,casingPressureOpenRatio=.7,projectName='QA',projectistName='QA')
    return build_timeline(simulate(i),2.0)

def test_canonical_events_and_order(timeline):
    assert [e.eventId[0] for e in timeline.events]==list('ABCDEF')
    assert all(b.t>a.t for a,b in zip(timeline.events,timeline.events[1:]))
    assert timeline.events[-1].terminal and timeline.events[-1].exact

def test_segments_are_contiguous_and_indexed(timeline):
    assert [s.stage for s in timeline.segments]==['A_B','B_C','C_D','D_E','E_F']
    assert all(s.startIndex<=s.endIndex for s in timeline.segments)

def test_resampling_is_monotonic_and_keeps_terminal_sample(timeline):
    t=[s.t for s in timeline.resampledSeries]
    assert all(b>a for a,b in zip(t,t[1:]))
    assert timeline.resampledSeries[-1].exactEvent=='F_FILM_VELOCITY_ZERO'
    assert timeline.resampleInterval==2

def test_contract_does_not_claim_unavailable_adaptive_output(timeline):
    assert not timeline.adaptiveSolverOutputAvailable

def test_invalid_resampling_interval_is_rejected(timeline):
    from gli_api.timeline_service import build_timeline
    class R: pass
    with pytest.raises(ValueError): build_timeline(R(),0)
