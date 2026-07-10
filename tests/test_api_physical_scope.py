from gli_api.schemas import SimulationInputs
from gli_api.simulation_service import simulate
import pytest

def test_api_declares_certified_a_to_f_scope():
    inputs=SimulationInputs(
        tubingDiameter=0.050673,valveDepth=1480.0,slugLength=412.5,
        surfaceTubingPressure=0.788,injectionPressure=6.966,
        api=40.0,bsw=50.0,gasRelativeDensity=0.7,
        casingPressureOpenRatio=0.7,projectName='QA',projectistName='QA',
    )
    result=simulate(inputs)
    assert result.terminalEvent=='F_FILM_VELOCITY_ZERO'
    assert result.physicalScope.startswith('A_TO_F certified:')
    assert 'E_TO_F santos_corrected' in result.physicalScope
    assert result.validationLevel == 'certified'
    assert result.points[-1].stage=='E_F'
    assert abs(result.points[-1].slugVelocity) < 1e-6
    assert result.points[-1].producedVolume>0.0
    assert result.points[-1].gasRate>=0.0
