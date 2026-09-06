from gli_api.schemas import SimulationInputs
from gli_api.simulation_service import simulate
import pytest

def test_api_declares_stage42_source_block_and_stops_at_e():
    inputs=SimulationInputs(
        tubingDiameter=0.050673,valveDepth=1480.0,slugLength=412.5,
        surfaceTubingPressure=0.788,injectionPressure=6.966,
        api=40.0,bsw=50.0,gasRelativeDensity=0.7,
        casingPressureOpenRatio=0.7,projectName='QA',projectistName='QA',
    )
    result=simulate(inputs)
    assert result.terminalEvent=='GLV_CLOSE_BEFORE_E_SOURCE_BLOCK'
    assert result.physicalScope.startswith('NOT_SOURCE_CERTIFIED_A_TO_E:')
    assert 'SOURCE_AMBIGUITY_GLV_CLOSE_BEFORE_E' in result.physicalScope
    assert result.validationLevel == 'failed'
    assert result.points[-1].stage=='D_E'
    assert result.points[-1].producedVolume>0.0
