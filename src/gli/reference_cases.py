"""Immutable, source-scoped GLI reference cases and comparison guards."""
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

@dataclass(frozen=True)
class ReferenceCase:
    case_id: str
    source: str
    classification: str
    inputs: Mapping[str, float | str | None]
    targets: Mapping[str, float]
    allowed_metrics: frozenset[str]

def _case(case_id, source, classification, inputs, targets, metrics):
    return ReferenceCase(case_id, source, classification, MappingProxyType(dict(inputs)),
                         MappingProxyType(dict(targets)), frozenset(metrics))

SANTOS_50_70_80 = _case(
    "santos-gli-50-70-80", "Santos (1997), Tablas 5.5-5.7 y Figuras 5.1-5.4",
    "full_case",
    {"L_over_H":.50,"Pto_over_Pvo":.70,"Vgi_over_Vgref":.80,
     "static_liquid_height_m":825.2980723373487,"initial_slug_length_m":412.64903616867434,
     "valve_depth_m":1480.0,"tubing_nominal_in":2.375,"tubing_id_m":.050673},
    {"event_d_absolute_s":290.0,"event_e_absolute_s":330.0},
    {"event_d_absolute_s","event_e_absolute_s","pc1_kgf_cm2","pwf_kgf_cm2","h_b_m","v_b_m_s","v_l_m_s"})

LIAO_TABLE_5_14 = _case(
    "liao-example-table-5-14", "Liao (1991), values reproduced by Santos (1997), Table 5.14",
    "partial_benchmark",
    {"geometry":None,"operating_point":None,"tubing_id_m":None,"H_m":None,"L_m":None},
    {"final_slug_produced_m3":.309,"entrainment_m3":.077,"total_produced_m3":.387,
     "liquid_recovery":.740,"elevation_time_s":275.0},
    {"final_slug_produced_m3","entrainment_m3","total_produced_m3","liquid_recovery","elevation_time_s"})

REFERENCE_CASES = MappingProxyType({c.case_id:c for c in (SANTOS_50_70_80,LIAO_TABLE_5_14)})

def compare_metric(result_case_id: str, reference_case_id: str, metric: str,
                   value: float) -> tuple[float,float]:
    if result_case_id != reference_case_id:
        raise ValueError(f"Cross-case comparison forbidden: {result_case_id} != {reference_case_id}")
    case=REFERENCE_CASES[reference_case_id]
    if metric not in case.allowed_metrics or metric not in case.targets:
        raise ValueError(f"Metric {metric!r} is not allowed for {reference_case_id}")
    target=case.targets[metric]
    return value,target

