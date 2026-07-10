"""Digitized Santos Figure 5.1-5.4 targets for terminal event D."""
from dataclasses import dataclass
from .stage1_dynamic import Stage1Result
from .stage_bc_dynamic import StageBCResult
from .stage_cd_dynamic import StageCDResult
from .units import KGF_CM2_TO_PA

@dataclass(frozen=True)
class StageDComparison:
    absolute_time_s:float; reference_time_s:float
    pc1_kgf_cm2:float; reference_pc1_kgf_cm2:float
    pwf_kgf_cm2:float; reference_pwf_kgf_cm2:float
    h_b_m:float; reference_h_b_m:float
    v_l_m_s:float; reference_v_l_m_s:float
    v_b_m_s:float; reference_v_b_m_s:float

def compare_event_d(ab:Stage1Result,bc:StageBCResult,cd:StageCDResult)->StageDComparison:
    """Compare D with visually digitized values; references carry graph uncertainty."""
    return StageDComparison(
        ab.opening_time_s+bc.event_c_time_s+cd.event_d_time_s,290.0,
        float(cd.p_c1_pa[-1]/KGF_CM2_TO_PA),56.0,
        float(cd.p_bottom_pa[-1]/KGF_CM2_TO_PA),65.0,
        float(cd.h_b_m[-1]),1260.0,
        float(cd.v_l_m_s[-1]),4.2,
        float(cd.v_b_m_s[-1]),4.8,
    )
