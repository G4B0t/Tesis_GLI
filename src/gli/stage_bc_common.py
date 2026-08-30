"""Block 6M-1 candidate B->C integrator on the canonical memory vector.

Kept parallel to the legacy solver until certification.  No coefficient is
calibrated against the legacy event time.
"""
from dataclasses import dataclass
from math import pi, sqrt
import numpy as np
from scipy.integrate import solve_ivp
from .common_state_be import CommonStateBE
from .geometry import tubing_area
from .initial_conditions import GRAVITY_M_S2, initial_stage_1
from .parameters import GLIParameters
from .reference_gas import injected_gas_target_std_m3
from .stage1_dynamic import Stage1Result, simulate_stage_1, standard_gas_density, state_from_mass
from .stage_bc_dynamic import StageBCResult, _gas_lift_mass_rate
from .valves import motor_valve_gas_rate
from .block6p_parameters import FrictionClosure, friction_factor
from .stage_ef_dynamic import default_stage_ef_parameters
from .reservoir import reservoir_inflow_from_pt1

I_MC,I_MG,I_RHO,I_PG,I_VG,I_VF,I_Y,I_MFILM,I_HB,I_HL,I_VL,I_VGI,I_FB,I_PROD=range(14)

@dataclass(frozen=True)
class StageBCCommonResult:
    time_s:np.ndarray; states:np.ndarray; event_c_reached:bool; event_c_time_s:float
    target_volume_std_m3:float; gas_balance_relative_error:float
    liquid_balance_relative_error:float; eos_relative_error:float
    initial_assumption:str; certified:bool
    @property
    def final_state(self): return self.states[:,-1]

def common_to_stage_bc_result(result:StageBCCommonResult,params:GLIParameters)->StageBCResult:
    """Compatibility adapter for provisional legacy C->D; no state reset at C."""
    s=result.states;n=s.shape[1];pc1=np.empty(n);pc2=np.empty(n);mgl=np.empty(n);qm=np.empty(n)
    rho_std=standard_gas_density(params)
    for i in range(n):
        casing=state_from_mass(float(s[I_MC,i]),params);pc1[i]=casing['p_c1'];pc2[i]=casing['p_c2']
        mgl[i]=_gas_lift_mass_rate(casing['p_c2'],s[I_PG,i],casing['rho_c2'],params)
        qm[i]=motor_valve_gas_rate(casing['p_c1'],params.operating.injection_pressure_pa,params.fluids.gas_relative_density,params.gas.temp_c1_k,params.valves.motor_valve_cv)
    return StageBCResult(result.time_s,s[I_MC],s[I_MG],s[I_HB],s[I_HL],s[I_VL],s[I_Y],pc1,pc2,s[I_PG],qm,mgl,s[I_VGI],result.target_volume_std_m3,result.event_c_reached,result.event_c_time_s,result.gas_balance_relative_error,result.liquid_balance_relative_error)

def initial_state_b(params:GLIParameters,ab:Stage1Result,seed_height_m=1e-3,seed_film_fraction=.0199,initial_vf_m_s=0.,enforce_santos_slug_constraint=False):
    """B state: Santos bubble birth plus explicit, sensitivity-ready seeds."""
    ini=initial_stage_1(params);g=params.gas;At=tubing_area(params.geometry.tubing_diameter_m);r=params.geometry.tubing_diameter_m/2
    y=r*(1-sqrt(1-seed_film_fraction));Ab=pi*(r-y)**2;Af=At-Ab;V=Ab*seed_height_m
    mg=ini['p_to']*g.gas_molar_mass_kg_mol*V/(g.z_t1*g.gas_constant_j_mol_k*g.temp_t1_k)
    rho=mg/V;mc=float(ab.annulus_gas_mass_kg[-1]-mg);hl=params.geometry.initial_slug_length_m+(Ab/At)*seed_height_m
    vl=.0152;vb=params.coefficients.bubble_velocity_a*vl+.35*sqrt(GRAVITY_M_S2*params.geometry.tubing_diameter_m)
    if enforce_santos_slug_constraint:
        initial_vf_m_s=(At*vl-Ab*vb)/max(Af,1e-18)
    mf=ini['rho_l']*Af*seed_height_m;rho_std=standard_gas_density(params);vgi=float((ab.annulus_gas_mass_kg[-1]-ab.annulus_gas_mass_kg[0])/rho_std)
    return np.array([mc,mg,rho,ini['p_to'],vb,initial_vf_m_s,y,mf,seed_height_m,hl,vl,vgi,0.,0.])

def rhs_bc_common(_t,s,params:GLIParameters):
    ini=initial_stage_1(params);g=params.gas;D=params.geometry.tubing_diameter_m;r=D/2;At=tubing_area(D)
    mc,mg,rho,pg,vg,vf,y,mfilm,hb,hl,vl,vgi,fb,prod=s
    Ab=pi*(r-y)**2;Af=At-Ab;V=Ab*hb
    casing=state_from_mass(float(mc),params);rho_std=standard_gas_density(params)
    mgl=_gas_lift_mass_rate(casing['p_c2'],pg,casing['rho_c2'],params)
    qm=motor_valve_gas_rate(casing['p_c1'],params.operating.injection_pressure_pa,params.fluids.gas_relative_density,g.temp_c1_k,params.valves.motor_valve_cv)
    slug=max(hl-hb,1e-6);rho_l=ini['rho_l'];fc=FrictionClosure(default_stage_ef_parameters().roughness)
    ff,_=friction_factor(max(rho_l*abs(vl)*D/params.fluids.liquid_viscosity_pa_s,1e-9),D,fc)
    dvl=(pg-ini['p_t3']-rho_l*GRAVITY_M_S2*slug-ff*.5*rho_l*vl*abs(vl)*slug/D)/(rho_l*slug)
    dvg=params.coefficients.bubble_velocity_a*dvl # Santos 4.1.50
    dhb=vg
    # Reservoir influx increases the liquid slug inventory at its moving top.
    qres=reservoir_inflow_from_pt1(params,pg,rho_l).rate_m3_s
    dhl=vl+qres/At
    # Moving-boundary liquid balance: dV_liq/dt=q_res.  Since dhl already
    # contains q_res/At, q_res cancels analytically from the y equation.
    dy=(At*(vg-vl)-Af*vg)/(max(hb,1e-9)*2*pi*max(r-y,1e-9))
    dmg=mgl;dmc=rho_std*qm-mgl;dV=Ab*dhb-2*pi*(r-y)*hb*dy
    drho=dmg/V-rho*dV/V
    dpg=g.z_t1*g.gas_constant_j_mol_k*g.temp_t1_k/g.gas_molar_mass_kg_mol*drho
    fg,_=friction_factor(max(rho*abs(vg)*2*(r-y)/1.1e-5,1e-9),max(2*(r-y),1e-9),fc)
    tau=fg*rho*vg*vg/8
    dhf=max(abs(4*Af/(2*pi*r+2*pi*(r-y))),1e-12)
    re_f=max(rho_l*abs(vf)*dhf/params.fluids.liquid_viscosity_pa_s,1e-12)
    ff=64/re_f if re_f<2300 else friction_factor(re_f,dhf,fc)[0]
    vres=qres/max(Af,1e-12)
    # Santos 4.1.68: upward positive.  vf*|vf| makes wall shear oppose
    # both upward and downward motion without clipping or damping.
    area_term=2*pi*(r-y)*vf*dy/max(Af,1e-12)
    interfacial=2*pi*(r-y)*tau/(max(Af,1e-12)*rho_l)
    wall=ff*vf*abs(vf)*pi*r/(4*max(Af,1e-12))
    inertia=(vf*vf-vres*vres)/max(params.geometry.valve_depth_m,1e-12)
    pressure=(pg-ini['p_t3'])/(rho_l*max(params.geometry.valve_depth_m,1e-12))
    dvf=-GRAVITY_M_S2-inertia-area_term+interfacial-wall+pressure
    # Fallback is a transfer ledger: remove it from film at the same rate at
    # which it is recorded.  It is not a second physical inventory.
    dfb=max(-vf*Af,0);dmfilm=rho_l*(2*pi*(r-y)*hb*dy+Af*dhb-dfb);dprod=0.
    return np.array([dmc,dmg,drho,dpg,dvg,dvf,dy,dmfilm,dhb,dhl,dvl,qm,dfb,dprod])

def rhs_bc_santos_compatible(_t,s,params:GLIParameters):
    """B->C form compatible with Santos elevation constraints 4.1.32-4.1.51.

    This is kept parallel to the certified 6M-1B RHS until the C-interface
    residual vector is within tolerance.  It differs from C->D only in the
    annulus boundary condition: the motor valve remains open and the injected
    standard gas volume advances to event C.
    """
    ini=initial_stage_1(params);g=params.gas;D=params.geometry.tubing_diameter_m;r=D/2;At=tubing_area(D)
    mc,mg,rho,pg,vg,vf,y,mfilm,hb,hl,vl,vgi,fb,prod=s
    Ab=pi*(r-y)**2;Af=At-Ab;V=Ab*hb
    casing=state_from_mass(float(mc),params);rho_std=standard_gas_density(params)
    mgl=_gas_lift_mass_rate(casing['p_c2'],pg,casing['rho_c2'],params)
    qm=motor_valve_gas_rate(casing['p_c1'],params.operating.injection_pressure_pa,params.fluids.gas_relative_density,g.temp_c1_k,params.valves.motor_valve_cv)
    rho_l=ini['rho_l'];fc=FrictionClosure(default_stage_ef_parameters().roughness)
    from math import exp
    fg,_=friction_factor(max(rho*abs(vg)*D/1.1e-5,1e-12),D,fc)
    pt2=pg-rho*GRAVITY_M_S2*hb-fg*.5*rho*vg*abs(vg)*hb/D
    H=params.geometry.valve_depth_m
    pt3=params.operating.surface_tubing_pressure_pa*exp(g.gas_molar_mass_kg_mol*GRAVITY_M_S2*max(H-hl,0)/(g.z_t3*g.gas_constant_j_mol_k*g.temp_t3_k))
    L=max(hl-hb,1e-9);fl,_=friction_factor(max(rho_l*abs(vl)*D/params.fluids.liquid_viscosity_pa_s,1e-12),D,fc)
    dvl=(-vl*vl+(Af/At)*vf*vf+(Ab/At)*vg*vg+(pt2-pt3)/rho_l-GRAVITY_M_S2*L-fl*vl*abs(vl)*L/(2*D))/L
    dvg=params.coefficients.bubble_velocity_a*dvl
    dhb=vg;dhl=vl
    qres=reservoir_inflow_from_pt1(params,pg,rho_l).rate_m3_s
    dy=(qres-Af*vf)/(2*pi*max(r-y,1e-12)*max(hb,1e-12))
    dAb=-2*pi*(r-y)*dy;dAf=-dAb
    N=At*vl-Ab*vg;dN=At*dvl-dAb*vg-Ab*dvg
    dvf=(dN*Af-N*dAf)/max(Af*Af,1e-18)
    dmg=mgl;dmc=rho_std*qm-mgl;dV=Ab*dhb+dAb*hb
    drho=dmg/V-rho*dV/V
    dpg=g.z_t1*g.gas_constant_j_mol_k*g.temp_t1_k/g.gas_molar_mass_kg_mol*drho
    dmfilm=rho_l*(hb*dAf+Af*dhb)
    return np.array([dmc,dmg,drho,dpg,dvg,dvf,dy,dmfilm,dhb,dhl,dvl,qm,0.,0.])

def simulate_stage_b_to_c_common(params:GLIParameters,*,stage_a_b=None,max_time_s=180,max_step_s=.2,rtol=1e-7,atol=1e-9,seed_height_m=1e-3,seed_film_fraction=.0199,initial_vf_m_s=0.,method="Radau",rhs_mode="current"):
    ab=stage_a_b or simulate_stage_1(params)
    compatible=(rhs_mode=="santos_compatible")
    s0=initial_state_b(params,ab,seed_height_m=seed_height_m,seed_film_fraction=seed_film_fraction,initial_vf_m_s=initial_vf_m_s,enforce_santos_slug_constraint=compatible);target=injected_gas_target_std_m3(params)
    rhs=rhs_bc_santos_compatible if compatible else rhs_bc_common
    def fun(t,s):return rhs(t,s,params)
    def ev(t,s):return s[I_VGI]-target
    ev.terminal=True;ev.direction=1
    # The analytic Jacobian audit at B gives a stiffness ratio 2.23e9.
    # Radau is selected for that documented mathematical reason, not to mask
    # a failed balance or to clip the solution.
    sol=solve_ivp(fun,(0,max_time_s),s0,events=ev,dense_output=True,max_step=max_step_s,rtol=rtol,atol=atol,method=method)
    reached=bool(sol.t_events[0].size);end=float(sol.t_events[0][0]) if reached else float(sol.t[-1]);t=np.linspace(0,end,max(2,int(np.ceil(end/max_step_s))+1));s=sol.sol(t)
    rho_std=standard_gas_density(params);gas=s[I_MC]+s[I_MG];expected=gas[0]+rho_std*(s[I_VGI]-s[I_VGI,0]);ge=float(np.max(abs(gas-expected))/max(abs(gas[-1]-gas[0]),1))
    g=params.gas;D=params.geometry.tubing_diameter_m;r=D/2;Ab=pi*(r-s[I_Y])**2;V=Ab*s[I_HB];peos=s[I_MG]*g.z_t1*g.gas_constant_j_mol_k*g.temp_t1_k/(g.gas_molar_mass_kg_mol*np.maximum(V,1e-12));ee=float(np.max(abs(peos-s[I_PG])/np.maximum(peos,1)))
    At=tubing_area(D);liq=At*(s[I_HL]-s[I_HB])+s[I_MFILM]/initial_stage_1(params)['rho_l']+s[I_FB]+s[I_PROD]
    rho_l=initial_stage_1(params)['rho_l']
    qres=np.array([reservoir_inflow_from_pt1(params,float(x),rho_l).rate_m3_s for x in s[I_PG]])
    native_q=np.array([reservoir_inflow_from_pt1(params,float(x),rho_l).rate_m3_s for x in sol.y[I_PG]])
    native_reservoir=np.concatenate(([0.0],np.cumsum(0.5*(native_q[1:]+native_q[:-1])*np.diff(sol.t))))
    reservoir=np.interp(t,sol.t,native_reservoir)
    expected_liq=liq[0]+reservoir
    le=float(np.max(abs(liq-expected_liq))/max(expected_liq[-1],1e-12))
    physical=bool(np.all(s[I_RHO]>0) and np.all(s[I_PG]>0) and np.all((s[I_Y]>0)&(s[I_Y]<r)) and np.max(abs(s[I_VG]))<20 and np.max(abs(s[I_VF]))<20)
    inflow_valid=bool(all(reservoir_inflow_from_pt1(params,float(x),initial_stage_1(params)['rho_l']).physically_valid for x in s[I_PG]))
    certified=bool(reached and ge<1e-6 and le<1e-6 and ee<1e-5 and physical)
    assumption="B bubble seed h=1e-3 m; film fraction=.0199; vf(B) explicit sensitivity input"
    if compatible:
        assumption="B bubble seed h=1e-3 m; film fraction=.0199; vf(B) from Santos 4.1.39 algebraic slug constraint"
    return StageBCCommonResult(t,s,reached,end,target,ge,le,ee,assumption,certified)
