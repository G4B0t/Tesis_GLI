"""Traceable Block 5V audit of geometry and liquid-volume definitions."""
from dataclasses import dataclass
from math import pi
from .parameters import GLIParameters
from .stage_cd_dynamic import StageCDResult
from .stage_de_dynamic import StageDEResult

@dataclass(frozen=True)
class Block5VAudit:
    nominal_tubing_in: float
    model_id_m: float
    model_id_in: float
    H_m: float
    L_m: float
    initial_volume_m3: float
    slug_at_d_m3: float
    produced_de_m3: float
    film_e_m3: float
    fallback_e_m3: float
    recovery_model: float
    inferred_liao_initial_m3: float
    inferred_santos_initial_m3: float
    same_case_confirmed: bool
    may_advance_to_block6: bool

def audit_block5v(params: GLIParameters, cd: StageCDResult, de: StageDEResult) -> Block5VAudit:
    diameter=params.geometry.tubing_diameter_m
    area=pi*diameter**2/4
    initial=area*params.geometry.initial_slug_length_m
    # Table 5.14: Liao total/recovery and Santos total/recovery imply their own
    # initial inventories; neither equals the {50,70,80} inventory in this model.
    liao_initial=0.387/0.740
    santos_initial=0.330/0.610
    return Block5VAudit(2.375,diameter,diameter/0.0254,
        params.geometry.valve_depth_m,params.geometry.initial_slug_length_m,initial,
        float(de.slug_volume_m3[0]),float(de.produced_volume_m3[-1]),
        float(de.film_volume_m3[-1]),float(de.fallback_volume_m3[-1]),
        float(de.produced_volume_m3[-1]/initial),liao_initial,santos_initial,
        False,False)
