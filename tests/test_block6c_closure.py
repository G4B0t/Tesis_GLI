import math
import pytest
from gli.block6c_closure import *

def test_hydraulic_diameter_circular_and_annular():
    d=.0635
    assert hydraulic_diameter(math.pi*d*d/4, math.pi*d) == pytest.approx(d)
    assert annulus_hydraulic_diameter(.14,.0635) == pytest.approx(.0765)

def test_darcy_fanning_equivalence_and_laminar_limit():
    re=1000
    fd=laminar_darcy(re)
    assert fd == pytest.approx(4*(16/re))
    assert darcy_from_fanning(fanning_from_darcy(fd)) == pytest.approx(fd)

def test_reynolds_sign_independent():
    assert reynolds(10,3,.05,1e-5) == reynolds(10,-3,.05,1e-5)

def test_valve_force_has_newtons_and_monotonic_pressure_effects():
    g=ValveGeometry(.001,.0002,10,2)
    f=valve_opening_force(5e6,2e6,3e6,g)
    assert valve_opening_force(5.1e6,2e6,3e6,g) > f
    assert valve_opening_force(5e6,2e6,3.1e6,g) < f

def test_hysteresis_preserves_state_and_direction():
    assert valve_event(-4,True,5,5) is True
    assert valve_event(-5,True,5,5) is False
    assert valve_event(4,False,5,5) is False
    assert valve_event(5,False,5,5) is True
