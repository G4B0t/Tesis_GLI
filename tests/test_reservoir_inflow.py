from __future__ import annotations

import pytest

from gli.base_case import santos_50_70_80
from gli.initial_conditions import initial_stage_1
from gli.reservoir import (
    ReservoirInflowStatus,
    bottomhole_flowing_pressure_pa,
    linear_productivity_inflow,
    productivity_index_m3_day_kgf_cm2_to_si,
    reservoir_inflow_from_pt1,
)
from gli.units import KGF_CM2_TO_PA


def test_productivity_index_conversion_to_strict_si():
    expected = 1.0 / (86_400.0 * KGF_CM2_TO_PA)
    assert productivity_index_m3_day_kgf_cm2_to_si(1.0) == pytest.approx(expected, rel=1e-15)


def test_bottomhole_pressure_uses_pt1_and_declared_depths():
    pwb = bottomhole_flowing_pressure_pa(4.0e6, 900.0, 1500.0, 1480.0)
    assert pwb == pytest.approx(4.0e6 + 900.0 * 9.80665 * 20.0)


def test_negative_raw_ipr_is_reported_without_clipping():
    result = linear_productivity_inflow(5.0e6, 6.0e6, 1.0e-10)
    assert result.raw_rate_m3_s == pytest.approx(-1.0e-4)
    assert result.rate_m3_s == result.raw_rate_m3_s
    assert result.status == ReservoirInflowStatus.INVALID_REVERSE_FLOW_FOR_LINEAR_IPR
    assert not result.physically_valid


def test_santos_base_case_starts_with_valid_dynamic_inflow():
    params = santos_50_70_80()
    initial = initial_stage_1(params)
    result = reservoir_inflow_from_pt1(params, initial["p_to"], initial["rho_l"])
    assert result.status == ReservoirInflowStatus.VALID_PRODUCTION
    assert result.rate_m3_s > 0.0
    assert result.bottomhole_pressure_pa > initial["p_to"]
