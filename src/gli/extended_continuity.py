"""Extended C->E memory contract used before reconnecting stage E->F.

The trace is constructed from the native adaptive stage outputs and carries
the variables which older result contracts discarded at C, D and E.
"""
from dataclasses import dataclass
from math import pi
import numpy as np
from .geometry import tubing_area
from .parameters import GLIParameters
from .stage_bc_dynamic import StageBCResult, simulate_stage_b_to_c
from .stage_cd_dynamic import StageCDResult, simulate_stage_c_to_d
from .stage_de_dynamic import StageDEResult, simulate_stage_d_to_e
from .block6p_parameters import FrictionClosure, friction_factor
from .stage_ef_dynamic import default_stage_ef_parameters

@dataclass(frozen=True)
class ExtendedState:
    annulus_mass_kg: float; gas_mass_kg: float; gas_density_kg_m3: float
    tubing_pressure_pa: float; gas_velocity_m_s: float; film_velocity_m_s: float
    film_thickness_m: float; film_mass_kg: float; interfacial_shear_pa: float
    fallback_volume_m3: float; produced_volume_m3: float

@dataclass(frozen=True)
class TransferMap:
    event: str; source_stage: str; target_stage: str
    continuous: tuple[str,...]; physical_reset: tuple[str,...]; forbidden_reset: tuple[str,...]

MAP_C=TransferMap("C","B_C","C_D",("annulus_mass_kg","gas_mass_kg","gas_density_kg_m3","tubing_pressure_pa","gas_velocity_m_s","film_velocity_m_s","film_thickness_m","film_mass_kg"),("motor_valve_open: true->false",),())
MAP_D=TransferMap("D","C_D","D_E",("annulus_mass_kg","gas_mass_kg","gas_density_kg_m3","tubing_pressure_pa","gas_velocity_m_s","film_velocity_m_s","film_thickness_m","film_mass_kg","fallback_volume_m3"),("surface_boundary: closed->discharge",),())
MAP_E=TransferMap("E","D_E","E_F",("annulus_mass_kg","gas_mass_kg","gas_density_kg_m3","tubing_pressure_pa","gas_velocity_m_s","film_velocity_m_s","film_thickness_m","film_mass_kg","fallback_volume_m3","produced_volume_m3"),("slug_inventory reaches zero",),("rho_g","v_g","v_f"))

def _gradient(values,t):
    return np.gradient(np.asarray(values,dtype=float),np.asarray(t,dtype=float),edge_order=2)

def trace_bc(params:GLIParameters,bc:StageBCResult):
    At=tubing_area(params.geometry.tubing_diameter_m); r=params.geometry.tubing_diameter_m/2
    Af=pi*(2*r*bc.film_thickness_m-bc.film_thickness_m**2);Ab=At-Af
    volume=np.maximum(Ab*bc.h_b_m,1e-12);rho=bc.bubble_mass_kg/volume
    vg=_gradient(bc.h_b_m,bc.time_s)
    film_volume=Af*bc.h_b_m; vf=np.divide(-_gradient(film_volume,bc.time_s),Af,out=np.zeros_like(Af),where=Af>1e-12)
    fg=np.array([friction_factor(max(ro*abs(v)*params.geometry.tubing_diameter_m/1.1e-5,1e-9),params.geometry.tubing_diameter_m,FrictionClosure(default_stage_ef_parameters().roughness))[0] for ro,v in zip(rho,vg)])
    return rho,vg,vf,fg*rho*vg**2/8,film_volume

def trace_cd(params:GLIParameters,cd:StageCDResult):
    At=tubing_area(params.geometry.tubing_diameter_m);r=params.geometry.tubing_diameter_m/2
    Af=pi*(2*r*cd.film_thickness_m-cd.film_thickness_m**2);Ab=At-Af
    rho=cd.bubble_mass_kg/np.maximum(Ab*cd.h_b_m,1e-12);vg=cd.v_b_m_s
    vf=np.divide(-_gradient(cd.film_volume_m3,cd.time_s),Af,out=np.zeros_like(Af),where=Af>1e-12)
    fg=np.array([friction_factor(max(ro*abs(v)*params.geometry.tubing_diameter_m/1.1e-5,1e-9),params.geometry.tubing_diameter_m,FrictionClosure(default_stage_ef_parameters().roughness))[0] for ro,v in zip(rho,vg)])
    return rho,vg,vf,fg*rho*vg**2/8

def trace_de(params:GLIParameters,de:StageDEResult,film_thickness_m:float):
    At=tubing_area(params.geometry.tubing_diameter_m);r=params.geometry.tubing_diameter_m/2
    Af=pi*(2*r*film_thickness_m-film_thickness_m**2);Ab=At-Af
    rho=de.bubble_mass_kg/np.maximum(Ab*de.h_b_m,1e-12);vg=de.v_b_m_s
    vf=np.divide(-_gradient(de.film_volume_m3,de.time_s),Af,out=np.zeros_like(de.time_s),where=Af>1e-12)
    fg=np.array([friction_factor(max(ro*abs(v)*params.geometry.tubing_diameter_m/1.1e-5,1e-9),params.geometry.tubing_diameter_m,FrictionClosure(default_stage_ef_parameters().roughness))[0] for ro,v in zip(rho,vg)])
    return rho,vg,vf,fg*rho*vg**2/8

def extended_chain(params:GLIParameters,max_step_s=.2):
    bc=simulate_stage_b_to_c(params,max_step_s=max_step_s);cd=simulate_stage_c_to_d(params,stage_b_c=bc,max_step_s=max_step_s);de=simulate_stage_d_to_e(params,stage_c_d=cd,max_step_s=max_step_s)
    b=trace_bc(params,bc);c=trace_cd(params,cd);d=trace_de(params,de,float(cd.film_thickness_m[-1]))
    return {"bc":bc,"cd":cd,"de":de,"bc_trace":b,"cd_trace":c,"de_trace":d,"maps":(MAP_C,MAP_D,MAP_E)}
