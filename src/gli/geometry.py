"""Geometry helper functions for the GLI model."""

from math import pi


def tubing_radius(tubing_diameter_m: float) -> float:
    """Return tubing internal radius."""

    return tubing_diameter_m / 2.0


def tubing_area(tubing_diameter_m: float) -> float:
    """Cross-sectional area of the tubing."""

    radius = tubing_radius(tubing_diameter_m)
    return pi * radius**2


def annulus_area(casing_inner_diameter_m: float, tubing_outer_diameter_m: float) -> float:
    """Cross-sectional area of the annulus between casing and tubing."""

    casing_area = pi * (casing_inner_diameter_m / 2.0) ** 2
    tubing_area_outer = pi * (tubing_outer_diameter_m / 2.0) ** 2
    return casing_area - tubing_area_outer


def gas_bubble_area(tubing_diameter_m: float, liquid_film_thickness_m: float) -> float:
    """Area occupied by the gas bubble inside the tubing.

    Santos, eq. 4.1.24:
    A_B = pi (r - y)^2
    """

    radius = tubing_radius(tubing_diameter_m)
    return pi * (radius - liquid_film_thickness_m) ** 2


def liquid_film_area(tubing_diameter_m: float, liquid_film_thickness_m: float) -> float:
    """Area occupied by the liquid film.

    A_f = A_t - A_B
    """

    return tubing_area(tubing_diameter_m) - gas_bubble_area(
        tubing_diameter_m,
        liquid_film_thickness_m,
    )


def annulus_volume(annulus_cross_area_m2: float, valve_depth_m: float) -> float:
    """Volume of the annular gas column down to the gas-lift valve."""

    return annulus_cross_area_m2 * valve_depth_m
