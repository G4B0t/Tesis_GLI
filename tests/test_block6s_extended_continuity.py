import numpy as np
import pytest
from gli.base_case import santos_50_70_80
from gli.extended_continuity import extended_chain,MAP_C,MAP_D,MAP_E

@pytest.fixture(scope='module')
def chain(): return extended_chain(santos_50_70_80(),.5)

def test_variables_are_born_with_bubble_and_film_in_bc(chain):
    rho,vg,vf,tau,film=chain['bc_trace']
    assert np.all(rho>0) and np.all(vg>=0) and np.all(tau>=0) and np.all(film>=0)

def test_explicit_transfer_maps_forbid_memory_reset():
    assert not MAP_C.forbidden_reset and not MAP_D.forbidden_reset
    assert MAP_E.forbidden_reset==('rho_g','v_g','v_f')
    assert 'gas_density_kg_m3' in MAP_C.continuous and 'film_velocity_m_s' in MAP_D.continuous

def test_density_pressure_and_inventory_positive(chain):
    for key in ('bc_trace','cd_trace','de_trace'):
        rho,vg,vf,tau,*_=chain[key];assert np.all(np.isfinite(rho)) and np.all(rho>0);assert np.all(np.isfinite(vg));assert np.all(tau>=0)
    assert chain['cd'].gas_balance_relative_error<1e-10 and chain['de'].liquid_balance_relative_error<1e-9

def test_c_d_e_order_and_valves(chain):
    bc,cd,de=chain['bc'],chain['cd'],chain['de']
    assert bc.event_c_reached and cd.event_d_reached and de.event_e_reached
    assert bc.event_c_time_s>0 and cd.event_d_time_s>0 and de.event_e_time_s>0
    assert not de.valve_open.any()

def test_extended_trace_convergence():
    p=santos_50_70_80();a=extended_chain(p,1.0);b=extended_chain(p,.5)
    assert abs(a['de'].event_e_time_s-b['de'].event_e_time_s)<1e-3
    assert abs(a['de_trace'][0][-1]-b['de_trace'][0][-1])/b['de_trace'][0][-1]<1e-4
