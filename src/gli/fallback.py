"""Mechanistic gravity-drainage model for the wall liquid film."""
from math import pi

def falling_film_velocity_m_s(thickness_m: float, density_kg_m3: float,
                              viscosity_pa_s: float, gravity_m_s2: float=9.80665) -> float:
    """Mean laminar Nusselt falling-film velocity, u=rho*g*delta^2/(3*mu)."""
    if thickness_m < 0 or density_kg_m3 <= 0 or viscosity_pa_s <= 0:
        raise ValueError("Positive physical film properties are required")
    return density_kg_m3*gravity_m_s2*thickness_m**2/(3.0*viscosity_pa_s)

def fallback_rate_m3_s(diameter_m: float, thickness_m: float, density_kg_m3: float,
                        viscosity_pa_s: float, available_film_m3: float | None=None) -> float:
    area=pi*((diameter_m/2)**2-max(diameter_m/2-thickness_m,0.0)**2)
    q=area*falling_film_velocity_m_s(thickness_m,density_kg_m3,viscosity_pa_s)
    return max(0.0,q) if available_film_m3 is None or available_film_m3>0 else 0.0
