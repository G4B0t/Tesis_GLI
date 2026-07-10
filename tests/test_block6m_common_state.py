from gli.common_state_be import *

def sample(): return CommonStateBE(10,2,20,3,.2,.001,5,2e6,100,500,2,.1,.2)

def test_c_and_d_only_change_controls_not_memory():
    s=sample();b=BoundaryControlBE('B_C',True,False);c=BoundaryControlBE('C_D',False,False);d=BoundaryControlBE('D_E',False,True)
    assert transfer_without_reset(s,b,c) is s
    assert transfer_without_reset(s,c,d) is s

def test_e_cannot_be_certified_without_integrated_vf_vg_rho():
    assert not certify_integrated_e(integrated_fields={'gas_mass_kg'},continuity_error=0,
        gas_balance_error=0,liquid_balance_error=0,positive=True,converged=True)

def test_certification_gate_accepts_only_complete_quality_state():
    f={'gas_density_kg_m3','gas_velocity_m_s','film_velocity_m_s','gas_mass_kg','film_thickness_m','film_mass_kg'}
    assert certify_integrated_e(integrated_fields=f,continuity_error=1e-10,gas_balance_error=1e-8,liquid_balance_error=1e-8,positive=True,converged=True)
    assert not certify_integrated_e(integrated_fields=f,continuity_error=1e-4,gas_balance_error=1e-8,liquid_balance_error=1e-8,positive=True,converged=True)
