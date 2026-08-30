"""Santos linear reservoir-inflow closure in strict SI units."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .initial_conditions import GRAVITY_M_S2
from .parameters import GLIParameters
from .units import KGF_CM2_TO_PA

SECONDS_PER_DAY = 86_400.0


class ReservoirInflowStatus(str, Enum):
    VALID_PRODUCTION = "VALID_PRODUCTION"
    ZERO_DRAWDOWN = "ZERO_DRAWDOWN"
    INVALID_REVERSE_FLOW_FOR_LINEAR_IPR = "INVALID_REVERSE_FLOW_FOR_LINEAR_IPR"
    LEGACY_CONSTANT_INPUT = "LEGACY_CONSTANT_INPUT"


@dataclass(frozen=True)
class ReservoirInflow:
    rate_m3_s: float
    raw_rate_m3_s: float
    bottomhole_pressure_pa: float
    drawdown_pa: float
    productivity_index_m3_s_pa: float | None
    status: ReservoirInflowStatus

    @property
    def physically_valid(self) -> bool:
        return self.status in {
            ReservoirInflowStatus.VALID_PRODUCTION,
            ReservoirInflowStatus.ZERO_DRAWDOWN,
            ReservoirInflowStatus.LEGACY_CONSTANT_INPUT,
        }


def productivity_index_m3_day_kgf_cm2_to_si(value: float) -> float:
    """Convert m3/day/(kgf/cm2) to m3/(s Pa)."""

    if value <= 0.0:
        raise ValueError("productivity index must be positive")
    return float(value) / (SECONDS_PER_DAY * KGF_CM2_TO_PA)


def bottomhole_flowing_pressure_pa(
    tubing_pressure_at_glv_pa: float,
    liquid_density_kg_m3: float,
    well_depth_m: float,
    glv_depth_m: float,
) -> float:
    """P_wb = P_t1 + rho_l*g*(H_w-H_gv), with declared locations."""

    if well_depth_m < glv_depth_m:
        raise ValueError("well/perforation depth must not be shallower than GLV depth")
    return float(tubing_pressure_at_glv_pa) + float(liquid_density_kg_m3) * GRAVITY_M_S2 * (
        float(well_depth_m) - float(glv_depth_m)
    )


def linear_productivity_inflow(
    reservoir_pressure_pa: float,
    bottomhole_pressure_pa: float,
    productivity_index_m3_s_pa: float,
) -> ReservoirInflow:
    """Evaluate q_r=PI(P_r-P_wb) without clipping a negative raw rate."""

    if productivity_index_m3_s_pa <= 0.0:
        raise ValueError("SI productivity index must be positive")
    drawdown = float(reservoir_pressure_pa) - float(bottomhole_pressure_pa)
    raw = float(productivity_index_m3_s_pa) * drawdown
    if raw > 0.0:
        status = ReservoirInflowStatus.VALID_PRODUCTION
    elif raw == 0.0:
        status = ReservoirInflowStatus.ZERO_DRAWDOWN
    else:
        status = ReservoirInflowStatus.INVALID_REVERSE_FLOW_FOR_LINEAR_IPR
    return ReservoirInflow(raw, raw, float(bottomhole_pressure_pa), drawdown,
                           float(productivity_index_m3_s_pa), status)


def reservoir_inflow_from_pt1(params: GLIParameters, pt1_pa: float, rho_l: float) -> ReservoirInflow:
    """Evaluate the configured dynamic IPR from instantaneous GLV-depth P_t1.

    The legacy constant remains a compatibility path for manually constructed
    parameter objects. Production base/API parameters always provide Pr and PI.
    """

    pr = params.operating.reservoir_static_pressure_pa
    pi_si = params.operating.productivity_index_m3_s_pa
    if pr is None or pi_si is None:
        q = float(params.operating.reservoir_liquid_rate_m3_s)
        return ReservoirInflow(q, q, float("nan"), float("nan"), None,
                               ReservoirInflowStatus.LEGACY_CONSTANT_INPUT)
    hw = params.geometry.perforation_depth_m
    if hw is None:
        raise ValueError("dynamic reservoir inflow requires perforation_depth_m")
    pwb = bottomhole_flowing_pressure_pa(pt1_pa, rho_l, hw, params.geometry.valve_depth_m)
    return linear_productivity_inflow(pr, pwb, pi_si)
