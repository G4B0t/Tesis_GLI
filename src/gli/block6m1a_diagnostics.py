"""Term-by-term diagnostics for the parallel B->C common-state candidate."""
from dataclasses import dataclass,asdict
from math import pi
import numpy as np
from .geometry import tubing_area
from .initial_conditions import GRAVITY_M_S2,initial_stage_1
from .block6p_parameters import FrictionClosure,friction_factor
from .stage_ef_dynamic import default_stage_ef_parameters
from .stage_bc_common import *
from .reservoir import reservoir_inflow_from_pt1

VF_PHYSICAL_LIMIT_M_S=10.0

@dataclass(frozen=True)
class FilmMomentumTerms:
    gravity_m_s2:float; pressure_gradient_m_s2:float; wall_shear_m_s2:float
    interfacial_shear_m_s2:float; inertia_m_s2:float; area_m_s2:float
    total_m_s2:float; reynolds_film:float; hydraulic_diameter_m:float
    darcy_factor:float

def film_geometry(diameter_m,y_m):
    r=diameter_m/2;af=pi*(2*r*y_m-y_m*y_m);pwet=2*pi*r+2*pi*(r-y_m)
    return af,4*af/pwet

def decompose_film_momentum(state,params)->FilmMomentumTerms:
    ini=initial_stage_1(params);D=params.geometry.tubing_diameter_m;r=D/2
    rho,pg,vg,vf,y=state[I_RHO],state[I_PG],state[I_VG],state[I_VF],state[I_Y]
    af,dh=film_geometry(D,y);rho_l=ini['rho_l'];mu=params.fluids.liquid_viscosity_pa_s
    re=max(rho_l*abs(vf)*dh/mu,1e-12);fc=FrictionClosure(default_stage_ef_parameters().roughness)
    # Exact laminar limit avoids evaluating the all-regime expression at Re≈0.
    ff=64/re if re<2300 else friction_factor(re,dh,fc)[0]
    fg,_=friction_factor(max(rho*abs(vg)*2*(r-y)/1.1e-5,1e-12),2*(r-y),fc)
    tau_i=fg*rho*vg*vg/8;tau_w=ff*rho_l*vf*abs(vf)/8
    gravity=-GRAVITY_M_S2
    pressure=(pg-ini['p_t3'])/(rho_l*params.geometry.valve_depth_m)
    wall=-tau_w*(2*pi*r)/(rho_l*max(af,1e-15))
    interface=tau_i*(2*pi*(r-y))/(rho_l*max(af,1e-15))
    qres=reservoir_inflow_from_pt1(params,float(pg),rho_l).rate_m3_s
    vres=qres/max(af,1e-15)
    inertia=-(vf*vf-vres*vres)/params.geometry.valve_depth_m
    # Obtain dy/dt from the same unmodified common RHS so the moving-area
    # contribution is audited with the exact state convention.
    dy=rhs_bc_common(0.,state,params)[I_Y]
    area=-2*pi*(r-y)*vf*dy/max(af,1e-15)
    total=gravity+pressure+wall+interface+inertia+area
    return FilmMomentumTerms(gravity,pressure,wall,interface,inertia,area,total,re,dh,ff)

def liquid_inventory_terms(state,params):
    At=tubing_area(params.geometry.tubing_diameter_m);rho_l=initial_stage_1(params)['rho_l']
    slug=At*(state[I_HL]-state[I_HB]);film=state[I_MFILM]/rho_l
    return {"slug_m3":slug,"film_m3":film,"fallback_m3":state[I_FB],"produced_m3":state[I_PROD],"total_m3":slug+film+state[I_FB]+state[I_PROD]}

def instantaneous_liquid_residual(state,derivative,params):
    At=tubing_area(params.geometry.tubing_diameter_m);rho_l=initial_stage_1(params)['rho_l']
    # The ledger is included only because the same rate is removed from film:
    # it represents the receiving compartment, never duplicated mass.
    inventory_rate=At*(derivative[I_HL]-derivative[I_HB])+derivative[I_MFILM]/rho_l+derivative[I_FB]+derivative[I_PROD]
    qres=reservoir_inflow_from_pt1(params,float(state[I_PG]),rho_l).rate_m3_s
    return {"inventory_rate_m3_s":inventory_rate,"reservoir_rate_m3_s":qres,"residual_m3_s":inventory_rate-qres,
            "moving_slug_boundary_m3_s":At*(derivative[I_HL]-derivative[I_HB]),"film_geometry_m3_s":derivative[I_MFILM]/rho_l,
            "fallback_ledger_m3_s":derivative[I_FB],"produced_m3_s":derivative[I_PROD]}

def diagnose_result(result,params,limit=VF_PHYSICAL_LIMIT_M_S):
    idx=np.flatnonzero(np.abs(result.states[I_VF])>limit);i=int(idx[0]) if idx.size else None
    if i is None:return {"first_out_of_range":None}
    s=result.states[:,i];d=rhs_bc_common(float(result.time_s[i]),s,params)
    return {"first_out_of_range":{"index":i,"time_s":float(result.time_s[i]),"vf_m_s":float(s[I_VF]),"limit_m_s":limit,
        "momentum_terms":asdict(decompose_film_momentum(s,params)),"liquid_rate_terms":instantaneous_liquid_residual(s,d,params)}}
