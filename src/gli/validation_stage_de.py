"""Liao/Santos validation targets for slug production D->E."""
from dataclasses import dataclass
from .parameters import GLIParameters
from .stage_de_dynamic import StageDEResult
from .geometry import tubing_area

@dataclass(frozen=True)
class StageEComparison:
    produced_volume_m3: float
    liao_total_volume_m3: float
    recovery: float
    liao_recovery: float
    duration_de_s: float
    santos_visual_duration_de_s: float

def compare_event_e(params: GLIParameters, result: StageDEResult) -> StageEComparison:
    initial = tubing_area(params.geometry.tubing_diameter_m) * params.geometry.initial_slug_length_m
    return StageEComparison(float(result.produced_volume_m3[-1]), 0.387,
                            float(result.produced_volume_m3[-1] / initial), 0.740,
                            result.event_e_time_s, 40.0)
