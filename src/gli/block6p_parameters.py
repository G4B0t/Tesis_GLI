"""Explicit Block 6P closure parameters and pure certification functions."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from math import log10
from typing import Literal

from .block6c_closure import ValveGeometry, valve_event, valve_opening_force

class ProvenanceClass(str, Enum):
    MEASURED="measured"; BIBLIOGRAPHIC="bibliographic"; INFERRED="inferred"; CALIBRATED="calibrated"

@dataclass(frozen=True)
class ScalarParameter:
    value: float
    unit: str
    classification: ProvenanceClass
    source: str
    uncertainty_low: float
    uncertainty_high: float
    def __post_init__(self):
        if not self.uncertainty_low <= self.value <= self.uncertainty_high:
            raise ValueError("value outside uncertainty interval")

@dataclass(frozen=True)
class FrictionClosure:
    roughness_m: ScalarParameter
    laminar_max_re: float = 2300.0
    turbulent_min_re: float = 4000.0
    correlation: Literal["churchill_1977"] = "churchill_1977"

def churchill_darcy(re: float, relative_roughness: float) -> float:
    """Churchill (1977) all-regime Darcy factor, Chem. Eng. 84(24), 91-92."""
    if re <= 0 or relative_roughness < 0: raise ValueError("invalid Re or roughness")
    a=(2.457*log10(1/((7/re)**0.9+0.27*relative_roughness)))**16
    b=(37530/re)**16
    return 8*((8/re)**12 + 1/(a+b)**1.5)**(1/12)

def friction_factor(re: float, hydraulic_diameter_m: float, closure: FrictionClosure) -> tuple[float,str]:
    if hydraulic_diameter_m <= 0: raise ValueError("Dh must be positive")
    regime="laminar" if re <= closure.laminar_max_re else ("turbulent" if re >= closure.turbulent_min_re else "transitional")
    return churchill_darcy(re, closure.roughness_m.value/hydraulic_diameter_m),regime

@dataclass(frozen=True)
class MechanicalValveMode:
    bellows_area_m2: ScalarParameter
    port_area_m2: ScalarParameter
    dome_pressure_pa: ScalarParameter
    spring_force_n: ScalarParameter
    preload_force_n: ScalarParameter
    open_spread_n: ScalarParameter
    close_spread_n: ScalarParameter
    mode: Literal["mechanical"]="mechanical"

@dataclass(frozen=True)
class CalibratedThresholdMode:
    opening_pressure_pa: ScalarParameter
    closing_pressure_pa: ScalarParameter
    pressure_signal: Literal["annulus_minus_tubing"]="annulus_minus_tubing"
    mode: Literal["calibrated_threshold"]="calibrated_threshold"
    def __post_init__(self):
        if self.opening_pressure_pa.value < self.closing_pressure_pa.value:
            raise ValueError("opening threshold must be >= closing threshold")

def valve_state_mechanical(mode: MechanicalValveMode, p_annulus: float, p_tubing: float, was_open: bool):
    geom=ValveGeometry(mode.bellows_area_m2.value,mode.port_area_m2.value,mode.spring_force_n.value,mode.preload_force_n.value)
    force=valve_opening_force(p_annulus,p_tubing,mode.dome_pressure_pa.value,geom)
    return valve_event(force,was_open,mode.close_spread_n.value,mode.open_spread_n.value),force

def valve_state_threshold(mode: CalibratedThresholdMode, p_annulus: float, p_tubing: float, was_open: bool):
    signal=p_annulus-p_tubing
    if was_open and signal <= mode.closing_pressure_pa.value: return False,signal
    if not was_open and signal >= mode.opening_pressure_pa.value: return True,signal
    return was_open,signal

def certify_closed_path(mode, annulus_pressures_pa, tubing_pressures_pa, initially_open=True):
    state=initially_open; closed_index=None
    for i,(pc,pt) in enumerate(zip(annulus_pressures_pa,tubing_pressures_pa)):
        state,_=(valve_state_mechanical(mode,pc,pt,state) if mode.mode=="mechanical" else valve_state_threshold(mode,pc,pt,state))
        if not state and closed_index is None: closed_index=i
        if closed_index is not None and state: return {"certified":False,"closed_index":closed_index,"reopened_index":i}
    return {"certified":closed_index is not None and not state,"closed_index":closed_index,"reopened_index":None}

def one_at_a_time_sensitivity(base_value: float, low: float, high: float, response):
    y0=response(base_value); yl=response(low); yh=response(high)
    scale=max(abs(y0),1e-30)
    return {"low":yl,"base":y0,"high":yh,"relative_span":abs(yh-yl)/scale}
