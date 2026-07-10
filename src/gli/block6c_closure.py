"""Pure, audit-ready closure relations; no E->F time integration."""
from __future__ import annotations
from dataclasses import dataclass
from math import pi

def reynolds(rho: float, speed: float, hydraulic_diameter: float, mu: float) -> float:
    if min(rho, hydraulic_diameter, mu) <= 0: raise ValueError("rho, Dh and mu must be positive")
    return rho*abs(speed)*hydraulic_diameter/mu

def hydraulic_diameter(area: float, wetted_perimeter: float) -> float:
    if min(area, wetted_perimeter) <= 0: raise ValueError("area and perimeter must be positive")
    return 4*area/wetted_perimeter

def annulus_hydraulic_diameter(outer_diameter: float, inner_diameter: float) -> float:
    if not outer_diameter > inner_diameter > 0: raise ValueError("require Do > Di > 0")
    return outer_diameter-inner_diameter

def darcy_from_fanning(fanning: float) -> float:
    if fanning < 0: raise ValueError("factor must be nonnegative")
    return 4*fanning

def fanning_from_darcy(darcy: float) -> float:
    if darcy < 0: raise ValueError("factor must be nonnegative")
    return darcy/4

def laminar_darcy(re: float) -> float:
    if re <= 0: raise ValueError("Re must be positive")
    return 64/re

@dataclass(frozen=True)
class ValveGeometry:
    bellows_area: float
    port_area: float
    spring_force: float = 0.0
    preload_force: float = 0.0

    def __post_init__(self):
        if self.bellows_area <= 0 or not 0 <= self.port_area <= self.bellows_area:
            raise ValueError("invalid effective areas")

def valve_opening_force(p_annulus: float, p_tubing: float, p_dome: float,
                        geometry: ValveGeometry) -> float:
    """Positive force tends to open an unbalanced injection valve.

    Pressure-area bookkeeping is explicit so no port/bellows convention is hidden.
    """
    a_b, a_p = geometry.bellows_area, geometry.port_area
    return (p_annulus*a_p + p_tubing*(a_b-a_p) - p_dome*a_b
            - geometry.spring_force - geometry.preload_force)

def valve_event(force: float, was_open: bool, close_margin: float, open_margin: float) -> bool:
    """Schmitt trigger: preserve state inside hysteresis band."""
    if close_margin < 0 or open_margin < 0: raise ValueError("margins must be nonnegative")
    if was_open and force <= -close_margin: return False
    if (not was_open) and force >= open_margin: return True
    return was_open
