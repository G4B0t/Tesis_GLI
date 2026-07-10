"""Unit conversions used at the Santos/source boundary.

The numerical model itself uses SI and absolute pressure.  Values from Santos
are kept in their printed units until they cross this module.
"""

ATMOSPHERIC_PRESSURE_PA = 101_325.0
KGF_CM2_TO_PA = 98_066.5
INCH_TO_M = 0.0254


def kgf_cm2_gauge_to_pa_absolute(value: float) -> float:
    """Convert kgf/cm2(g) to Pa(a)."""

    return value * KGF_CM2_TO_PA + ATMOSPHERIC_PRESSURE_PA


def fahrenheit_to_kelvin(value: float) -> float:
    """Convert degrees Fahrenheit to kelvin."""

    return (value - 32.0) * 5.0 / 9.0 + 273.15


def inch_to_m(value: float) -> float:
    """Convert inches to metres."""

    return value * INCH_TO_M
