"""Canonical physical-state contract for the Block 6M B->E migration."""
from dataclasses import dataclass, fields
from typing import Literal

@dataclass(frozen=True)
class CommonStateBE:
    annulus_mass_kg: float
    gas_mass_kg: float
    gas_density_kg_m3: float
    gas_velocity_m_s: float
    film_velocity_m_s: float
    film_thickness_m: float
    film_mass_kg: float
    tubing_pressure_pa: float
    bubble_base_m: float
    slug_top_m: float
    slug_velocity_m_s: float
    fallback_volume_m3: float
    produced_volume_m3: float

MEMORY_FIELDS=tuple(f.name for f in fields(CommonStateBE))

@dataclass(frozen=True)
class BoundaryControlBE:
    stage: Literal["B_C","C_D","D_E"]
    motor_valve_open: bool
    surface_discharge_open: bool

def transfer_without_reset(state:CommonStateBE, before:BoundaryControlBE,
                           after:BoundaryControlBE)->CommonStateBE:
    if before.stage==after.stage: raise ValueError("transition must change stage")
    return state

def certify_integrated_e(*, integrated_fields:set[str], continuity_error:float,
                         gas_balance_error:float, liquid_balance_error:float,
                         positive:bool, converged:bool)->bool:
    required={"gas_density_kg_m3","gas_velocity_m_s","film_velocity_m_s",
              "gas_mass_kg","film_thickness_m","film_mass_kg"}
    return (required<=integrated_fields and continuity_error<=1e-8 and
            gas_balance_error<=1e-6 and liquid_balance_error<=1e-6 and
            positive and converged)
