"""Validation helpers for stage A->B against Santos Figure 5.1."""

from dataclasses import dataclass
from math import sqrt

from .stage1_dynamic import Stage1Result
from .units import KGF_CM2_TO_PA

SANTOS_FIGURE_5_1_AB = ((0.0, 54.0), (18.0, 58.8))


@dataclass(frozen=True)
class Figure51Comparison:
    simulated_a_kgf_cm2: float
    simulated_b_kgf_cm2: float
    reference_a_kgf_cm2: float
    reference_b_kgf_cm2: float
    pressure_rmse_kgf_cm2: float
    simulated_b_time_s: float
    reference_b_time_s: float


def compare_figure_5_1_ab(result: Stage1Result) -> Figure51Comparison:
    """Compare simulated A/B endpoints with visually digitized Fig. 5.1."""
    simulated_a = float(result.p_c1_pa[0] / KGF_CM2_TO_PA)
    simulated_b = float(result.p_c1_pa[-1] / KGF_CM2_TO_PA)
    reference_a = SANTOS_FIGURE_5_1_AB[0][1]
    reference_b = SANTOS_FIGURE_5_1_AB[1][1]
    rmse = sqrt(((simulated_a-reference_a)**2 + (simulated_b-reference_b)**2) / 2.0)
    return Figure51Comparison(simulated_a, simulated_b, reference_a,
        reference_b, rmse, result.opening_time_s,
        SANTOS_FIGURE_5_1_AB[1][0])
