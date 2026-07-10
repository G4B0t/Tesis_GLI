import pytest

from gli.units import ATMOSPHERIC_PRESSURE_PA, fahrenheit_to_kelvin, inch_to_m, kgf_cm2_gauge_to_pa_absolute


def test_source_unit_conversions_are_explicit():
    assert inch_to_m(1.0) == pytest.approx(0.0254)
    assert fahrenheit_to_kelvin(80.0) == pytest.approx(299.8166666667)
    assert kgf_cm2_gauge_to_pa_absolute(0.0) == pytest.approx(ATMOSPHERIC_PRESSURE_PA)
