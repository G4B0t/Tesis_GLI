"""Block 6M-2 common-state C->D candidate with internal GLV closure."""
from dataclasses import dataclass
from math import pi
from math import exp
import numpy as np
from scipy.integrate import cumulative_simpson, solve_ivp
from .stage_bc_common import *
from .stage_bc_common import _gas_lift_mass_rate
from .initial_conditions import GRAVITY_M_S2,initial_stage_1
from .geometry import tubing_area
from .stage1_dynamic import state_from_mass
from .valves import gas_lift_valve_resultant_force
from .block6p_parameters import FrictionClosure,friction_factor,ScalarParameter,ProvenanceClass
from .stage_ef_dynamic import default_stage_ef_parameters
from .stage_cd_dynamic import StageCDResult
from .reservoir import reservoir_inflow_from_pt1

@dataclass(frozen=True)
class StageCDCommonResult:
    time_s:np.ndarray; states:np.ndarray; glv_open:np.ndarray; glv_mass_rate_kg_s:np.ndarray
    glv_force_n:np.ndarray; closure_reached:bool; closure_time_s:float
    event_d_reached:bool; event_d_time_s:float; gas_balance_relative_error:float
    liquid_balance_relative_error:float; eos_relative_error:float; continuity_error:float
    stiffness_ratio:float; certified:bool
    @property
    def final_state(self): return self.states[:,-1]

def common_to_stage_cd_result(result,params):
    """Legacy-shaped view for provisional D->E; the common state is untouched."""
    s=result.states;n=s.shape[1];pc1=np.empty(n);pc2=np.empty(n);pbot=np.empty(n);qfb=np.empty(n)
    ini=initial_stage_1(params);rho_l=ini['rho_l']
    for i in range(n):
        casing=state_from_mass(float(s[I_MC,i]),params);pc1[i]=casing['p_c1'];pc2[i]=casing['p_c2']
        pbot[i]=s[I_PG,i]+rho_l*GRAVITY_M_S2*max((params.geometry.perforation_depth_m or params.geometry.valve_depth_m)-params.geometry.valve_depth_m,0.)
        qfb[i]=_cd_terms(s[:,i],params,bool(result.glv_open[i]))[0][I_FB]
    return StageCDResult(result.time_s,s[I_MC],s[I_MG],s[I_HB],s[I_HL],s[I_VG],s[I_VL],s[I_Y],s[I_MFILM]/rho_l,s[I_FB],qfb,pc1,pc2,s[I_PG],pbot,result.glv_mass_rate_kg_s,result.glv_force_n,result.glv_open,result.event_d_reached,result.event_d_time_s,result.gas_balance_relative_error,result.liquid_balance_relative_error)

def _cd_terms(state,params,glv_open,roughness_m=None,friction_scale=1.0):
    ini=initial_stage_1(params);g=params.gas;D=params.geometry.tubing_diameter_m;r=D/2;At=tubing_area(D)
    mc,mg,rho,pg,vg,vf,y,mfilm,hb,hl,vl,vgi,fb,prod=state
    Ab=pi*(r-y)**2;Af=At-Ab;V=Ab*hb;casing=state_from_mass(float(mc),params)
    force=gas_lift_valve_resultant_force(casing['p_c2'],ini['p_bt'],pg,params.valves.rv,params.valves.bellows_area_m2)
    mgl=_gas_lift_mass_rate(casing['p_c2'],pg,casing['rho_c2'],params) if glv_open and casing['p_c2']>pg else 0.
    slug=max(hl-hb,1e-9);rho_l=ini['rho_l'];rp=default_stage_ef_parameters().roughness
    if roughness_m is not None: rp=ScalarParameter(roughness_m,'m',ProvenanceClass.INFERRED,'6M-2V controlled sensitivity',roughness_m,roughness_m)
    fc=FrictionClosure(rp)
    ff_l,_=friction_factor(max(rho_l*abs(vl)*D/params.fluids.liquid_viscosity_pa_s,1e-12),D,fc);ff_l*=friction_scale
    dvl=(pg-ini['p_t3']-rho_l*GRAVITY_M_S2*slug-ff_l*.5*rho_l*vl*abs(vl)*slug/D)/(rho_l*slug)
    dvg=params.coefficients.bubble_velocity_a*dvl;dhb=vg;qres=reservoir_inflow_from_pt1(params,pg,rho_l).rate_m3_s;dhl=vl+qres/At
    dy=(At*(vg-vl)-Af*vg)/(max(hb,1e-12)*2*pi*max(r-y,1e-12))
    dmg=mgl;dmc=-mgl;dV=Ab*dhb-2*pi*(r-y)*hb*dy;drho=dmg/V-rho*dV/V
    dpg=g.z_t1*g.gas_constant_j_mol_k*g.temp_t1_k/g.gas_molar_mass_kg_mol*drho
    fg,_=friction_factor(max(rho*abs(vg)*2*(r-y)/1.1e-5,1e-12),max(2*(r-y),1e-12),fc);tau=fg*rho*vg*vg/8
    dhf=max(abs(4*Af/(2*pi*r+2*pi*(r-y))),1e-12);re_f=max(rho_l*abs(vf)*dhf/params.fluids.liquid_viscosity_pa_s,1e-12)
    ff=(64/re_f if re_f<2300 else friction_factor(re_f,dhf,fc)[0])*friction_scale;vres=qres/max(Af,1e-12)
    dvf=(-GRAVITY_M_S2-(vf*vf-vres*vres)/params.geometry.valve_depth_m
        -2*pi*(r-y)*vf*dy/max(Af,1e-12)+2*pi*(r-y)*tau/(max(Af,1e-12)*rho_l)
        -ff*vf*abs(vf)*pi*r/(4*max(Af,1e-12))+(pg-ini['p_t3'])/(rho_l*params.geometry.valve_depth_m))
    dfb=max(-vf*Af,0);dmfilm=rho_l*(2*pi*(r-y)*hb*dy+Af*dhb-dfb)
    deriv=np.array([dmc,dmg,drho,dpg,dvg,dvf,dy,dmfilm,dhb,dhl,dvl,0.,dfb,0.])
    return deriv,force,mgl

def _cd_terms_santos(state,params,glv_open,roughness_m=None,friction_scale=1.0):
    """Santos elevation equations 4.1.32-4.1.51, kept parallel for 6M-2C."""
    ini=initial_stage_1(params);g=params.gas;D=params.geometry.tubing_diameter_m;r=D/2;At=tubing_area(D)
    mc,mg,rho,pt1,vg,vf,y,mfilm,hb,hl,vl,vgi,fb,prod=state
    Ab=pi*(r-y)**2;Af=At-Ab;V=Ab*hb;casing=state_from_mass(float(mc),params)
    # Pt2: pressure at bubble top, Santos 4.1.26; Pt3: gas-column
    # pressure at slug top, using the same isothermal closure as 5.3.
    rp=default_stage_ef_parameters().roughness
    if roughness_m is not None: rp=ScalarParameter(roughness_m,'m',ProvenanceClass.INFERRED,'6M-2C sensitivity',roughness_m,roughness_m)
    fc=FrictionClosure(rp);fg,_=friction_factor(max(rho*abs(vg)*D/1.1e-5,1e-12),D,fc);fg*=friction_scale
    pt2=pt1-rho*GRAVITY_M_S2*hb-fg*.5*rho*vg*abs(vg)*hb/D
    H=params.geometry.valve_depth_m;pts=params.operating.surface_tubing_pressure_pa
    pt3=pts*exp(g.gas_molar_mass_kg_mol*GRAVITY_M_S2*max(H-hl,0)/(g.z_t3*g.gas_constant_j_mol_k*g.temp_t3_k))
    force=gas_lift_valve_resultant_force(casing['p_c2'],ini['p_bt'],pt1,params.valves.rv,params.valves.bellows_area_m2)
    mgl=_gas_lift_mass_rate(casing['p_c2'],pt1,casing['rho_c2'],params) if glv_open and casing['p_c2']>pt1 else 0.
    L=max(hl-hb,1e-9);rho_l=ini['rho_l'];fl,_=friction_factor(max(rho_l*abs(vl)*D/params.fluids.liquid_viscosity_pa_s,1e-12),D,fc);fl*=friction_scale
    # Complete liquid-slug momentum, Santos 4.1.46.
    dvl=(-vl*vl+(Af/At)*vf*vf+(Ab/At)*vg*vg+(pt2-pt3)/rho_l-GRAVITY_M_S2*L-fl*vl*abs(vl)*L/(2*D))/L
    dvg=params.coefficients.bubble_velocity_a*dvl
    dhb=vg;dhl=vl
    qres=reservoir_inflow_from_pt1(params,pt1,rho_l).rate_m3_s
    # Elevation-film mass balance, Santos 4.1.35 (not fixed-zv 4.1.57).
    dy=(qres-Af*vf)/(2*pi*max(r-y,1e-12)*max(hb,1e-12))
    dAb=-2*pi*(r-y)*dy;dAf=-dAb
    # Differential form of At*vl-Af*vf-Ab*vg=0 (4.1.39).
    N=At*vl-Ab*vg;dN=At*dvl-dAb*vg-Ab*dvg;dvf=(dN*Af-N*dAf)/max(Af*Af,1e-18)
    dmg=mgl;dmc=-mgl;dV=Ab*dhb+dAb*hb;drho=dmg/V-rho*dV/V
    dpt1=g.z_t1*g.gas_constant_j_mol_k*g.temp_t1_k/g.gas_molar_mass_kg_mol*drho
    # During elevation fallback is not a separate sink: film inventory is its
    # moving geometric volume Af*hB (4.1.29-4.1.35).
    dfb=0.;dmfilm=rho_l*(hb*dAf+Af*dhb);deriv=np.array([dmc,dmg,drho,dpt1,dvg,dvf,dy,dmfilm,dhb,dhl,dvl,0.,dfb,0.])
    return deriv,force,mgl

def rhs_cd_common(t,state,params,glv_open=True,roughness_m=None,friction_scale=1.0):return _cd_terms(state,params,glv_open,roughness_m,friction_scale)[0]

def _stiffness(state,params):
    f=rhs_cd_common(0,state,params,True);n=len(state);J=np.zeros((n,n))
    for j in range(n):
        h=1e-7*max(abs(state[j]),1);q=state.copy();q[j]+=h;J[:,j]=(rhs_cd_common(0,q,params,True)-f)/h
    w=np.abs(np.linalg.eigvals(J));w=w[w>1e-10];return float(w.max()/w.min())

def simulate_stage_c_to_d_common(params,*,stage_b_c_common=None,stage_a_b=None,max_time_s=800,max_step_s=.2,rtol=1e-7,atol=1e-9,roughness_m=None,friction_scale=1.0,rhs_mode="current"):
    bc=stage_b_c_common or simulate_stage_b_to_c_common(params,stage_a_b=stage_a_b,max_step_s=max_step_s)
    if not bc.certified:raise ValueError('Certified common B->C required')
    s0=bc.final_state.copy();H=params.geometry.valve_depth_m;stiff=_stiffness(s0,params);terms_fn=_cd_terms_santos if rhs_mode=="santos_corrected" else _cd_terms
    def close(t,s):return terms_fn(s,params,True,roughness_m,friction_scale)[1]
    close.direction=-1;close.terminal=True
    def d_event(t,s):return s[I_HL]-H
    d_event.direction=1;d_event.terminal=True
    pre=solve_ivp(lambda t,s:terms_fn(s,params,True,roughness_m,friction_scale)[0],(0,max_time_s),s0,events=(close,d_event),dense_output=True,max_step=max_step_s,rtol=rtol,atol=atol,method='Radau')
    closed=bool(pre.t_events[0].size);d_pre=bool(pre.t_events[1].size)
    tc=float(pre.t_events[0][0]) if closed else float('nan')
    parts=[pre];offset=0.
    if closed and not d_pre:
        sc=pre.y_events[0][0].copy();post=solve_ivp(lambda t,s:terms_fn(s,params,False,roughness_m,friction_scale)[0],(tc,max_time_s),sc,events=d_event,dense_output=True,max_step=max_step_s,rtol=rtol,atol=atol,method='Radau');parts.append(post)
    last=parts[-1];reached=bool(last.t_events[-1].size);end=float(last.t_events[-1][0]) if reached else float(last.t[-1])
    t=np.linspace(0,end,max(2,int(np.ceil(end/max_step_s))+1));s=np.empty((14,len(t)));opened=np.empty(len(t),dtype=bool)
    for i,x in enumerate(t):
        use_pre=(not closed) or x<=tc;s[:,i]=(pre.sol(x) if use_pre else parts[-1].sol(x));opened[i]=use_pre
    terms=[terms_fn(s[:,i],params,bool(opened[i]),roughness_m,friction_scale) for i in range(len(t))];force=np.array([x[1] for x in terms]);mgl=np.array([x[2] for x in terms])
    gas=s[I_MC]+s[I_MG];ge=float(np.max(abs(gas-gas[0]))/max(gas[0],1))
    At=tubing_area(params.geometry.tubing_diameter_m);rho_l=initial_stage_1(params)['rho_l'];liq=At*(s[I_HL]-s[I_HB])+s[I_MFILM]/rho_l+s[I_FB]+s[I_PROD]
    qres=np.array([reservoir_inflow_from_pt1(params,float(x),rho_l).rate_m3_s for x in s[I_PG]])
    native_t=pre.t;native_pg=pre.y[I_PG]
    if len(parts)>1:
        native_t=np.concatenate((native_t,parts[-1].t[1:]));native_pg=np.concatenate((native_pg,parts[-1].y[I_PG,1:]))
    native_q=np.array([reservoir_inflow_from_pt1(params,float(x),rho_l).rate_m3_s for x in native_pg])
    native_reservoir=cumulative_simpson(native_q,x=native_t,initial=0.0)
    reservoir=np.interp(t,native_t,native_reservoir)
    expected=liq[0]+reservoir;le=float(np.max(abs(liq-expected))/max(abs(expected[-1]),1e-12))
    g=params.gas;r=params.geometry.tubing_diameter_m/2;Ab=pi*(r-s[I_Y])**2;peos=s[I_MG]*g.z_t1*g.gas_constant_j_mol_k*g.temp_t1_k/(g.gas_molar_mass_kg_mol*np.maximum(Ab*s[I_HB],1e-12));ee=float(np.max(abs(peos-s[I_PG])/np.maximum(peos,1)))
    ce=float(np.max(abs(s[:,0]-s0))/max(np.max(abs(s0)),1));physical=bool(np.all(s[I_RHO]>0)&np.all(s[I_PG]>0)&np.all(s[I_Y]>0)&np.all(s[I_Y]<r)&(np.max(abs(s[I_VF]))<10)&np.all(s[I_HB]<s[I_HL]+1e-9))
    # A latched closure cannot reopen within C->D.  If the force remains
    # positive up to D, the physically consistent result is that no closure
    # event occurs in this stage (not a certification failure).
    no_reopen=not np.any(opened[np.flatnonzero(~opened)[0]:]) if np.any(~opened) else True
    control_ok=(closed and no_reopen and np.all(mgl[~opened]==0.0)) or ((not closed) and np.all(force>=-1e-8))
    inflow_valid=bool(all(reservoir_inflow_from_pt1(params,float(x),rho_l).physically_valid for x in s[I_PG]))
    certified=bool(reached and control_ok and ge<1e-6 and le<1e-6 and ee<1e-5 and ce<1e-10 and physical)
    return StageCDCommonResult(t,s,opened,mgl,force,closed,tc,reached,end,ge,le,ee,ce,stiff,certified)
