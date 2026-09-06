"""Block 6M-4A audit for the E->F decompression boundary.

The audit keeps E->F disconnected from the public API.  It answers a narrow
question: is physical E available, source-qualified, and compatible by identity?
Historical reduced trajectories are never substituted for physical E or F.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import pi, sqrt
from typing import Any

import numpy as np

from .base_case import santos_50_70_80
from .geometry import tubing_area
from .initial_conditions import initial_stage_1
from .stage1_dynamic import simulate_stage_1
from .stage_bc_common import simulate_stage_b_to_c_common
from .stage_cd_common import common_to_stage_cd_result, simulate_stage_c_to_d_common
from .stage_de_dynamic import simulate_stage_d_to_e
from .stage_ef_dynamic import audit_stage_42_initial_state, simulate_stage_e_to_f


@dataclass(frozen=True)
class ResidualEF:
    name: str
    contract: str
    value: float
    scale: float
    normalized: float
    units: str
    status: str
    interpretation: str


@dataclass(frozen=True)
class Block6M4Audit:
    event_e_time_s: float | None
    event_f_time_s: float | None
    event_f_reached: bool
    can_receive_without_projection: bool
    ef_exception: str | None
    max_residual_normalized: float
    failed_contracts: tuple[str, ...]
    residuals: tuple[ResidualEF, ...]
    ef_initial_state_source: str | None
    corrected_event_f_time_s: float | None = None
    corrected_event_f_reached: bool = False
    corrected_certified: bool = False
    corrected_max_residual_normalized: float = 0.0
    corrected_failed_contracts: tuple[str, ...] = ()
    corrected_residuals: tuple[ResidualEF, ...] = ()
    corrected_initial_state_source: str | None = None


def _film_thickness_from_volume(params, film_volume_m3: float) -> float:
    radius = params.geometry.tubing_diameter_m / 2.0
    area = film_volume_m3 / params.geometry.valve_depth_m
    return radius - sqrt(max(radius * radius - area / pi, 0.0))


def _add_residual(
    residuals: list[ResidualEF],
    *,
    name: str,
    contract: str,
    value: float,
    scale: float,
    units: str,
    tolerance: float,
    interpretation: str,
    status: str | None = None,
) -> None:
    scale = max(abs(scale), 1e-18)
    normalized = abs(float(value)) / scale
    residuals.append(
        ResidualEF(
            name=name,
            contract=contract,
            value=float(value),
            scale=float(scale),
            normalized=float(normalized),
            units=units,
            status=status or ("ok" if normalized <= tolerance else "fail"),
            interpretation=interpretation,
        )
    )


def build_corrected_e_state(params=None, *, max_step_s: float = 0.2):
    """Run the numerical prefix and Stage 3; the returned result may not reach E."""
    p = params or santos_50_70_80()
    stage_ab = simulate_stage_1(p, max_step_s=max_step_s)
    stage_bc = simulate_stage_b_to_c_common(
        p, stage_a_b=stage_ab, rhs_mode="santos_compatible", max_step_s=max_step_s
    )
    stage_cd_common = simulate_stage_c_to_d_common(
        p, stage_b_c_common=stage_bc, rhs_mode="santos_corrected", max_step_s=max_step_s
    )
    stage_cd = common_to_stage_cd_result(stage_cd_common, p)
    stage_de = simulate_stage_d_to_e(p, stage_c_d=stage_cd, rhs_mode="santos_corrected", max_step_s=max_step_s)
    return p, stage_ab, stage_bc, stage_cd_common, stage_cd, stage_de


def audit_ef_boundary(params=None, *, max_step_s: float = 0.2) -> Block6M4Audit:
    p, _ab, _bc, _cd_common, _cd, de = build_corrected_e_state(params, max_step_s=max_step_s)
    if not de.event_e_reached:
        residual = ResidualEF("physical_e_unavailable", "E: h_B=z_v", float(p.geometry.valve_depth_m-de.h_b_m[-1]),
                              p.geometry.valve_depth_m, float((p.geometry.valve_depth_m-de.h_b_m[-1])/p.geometry.valve_depth_m),
                              "m", "fail", de.terminal_reason)
        return Block6M4Audit(None,None,False,False,de.terminal_reason,
                            residual.normalized,(residual.name,),(residual,),None,
                            corrected_failed_contracts=(residual.name,),corrected_residuals=(residual,),
                            corrected_max_residual_normalized=residual.normalized,
                            corrected_initial_state_source="NOT_SOURCE_CERTIFIED_A_TO_E: " + de.terminal_reason)
    residuals: list[ResidualEF] = []
    try:
        entry = audit_stage_42_initial_state(p, de)
    except ValueError as exc:
        entry = None
        reason = str(exc)
    else:
        reason = "Stage 4.2 identity closures or upstream source certification failed"
    _add_residual(residuals, name="stage42_identity_E", contract="inventory + hydrostatic + EOS + memory",
        value=0. if entry is not None and entry.compatible else 1., scale=1., units="1",
        tolerance=0., interpretation=reason)
    _add_residual(residuals, name="de_source_certification", contract="source-certified E required",
        value=0. if de.source_certified else 1., scale=1., units="1",
        tolerance=0., interpretation="An algebraically compatible state alone does not certify the upstream chain.")
    ef = None
    exception = None
    if all(r.status == "ok" for r in residuals):
        try:
            ef = simulate_stage_e_to_f(p, stage_d_e=de, rhs_mode="santos_corrected", max_step_s=max_step_s)
        except ValueError as exc:
            exception = str(exc)
    _add_residual(residuals, name="physical_f_state", contract="exact Stage 4.2 descending vf=0",
        value=0. if ef is not None and ef.event_f_reached and ef.corrected_certified else 1.,
        scale=1., units="1", tolerance=0., interpretation=exception or "No historical F is substituted.")
    failed = tuple(r.name for r in residuals if r.status != "ok")
    reached = bool(ef is not None and ef.event_f_reached)
    ft = float(ef.event_f_time_s) if reached else None
    source = ef.initial_state_source if ef is not None else None
    maximum = max(r.normalized for r in residuals)
    return Block6M4Audit(float(de.event_e_time_s), ft, reached,
        entry is not None and entry.compatible, exception, maximum, failed,
        tuple(residuals), source, ft, reached, not failed, maximum, failed,
        tuple(residuals), source or reason)


def audit_summary(params=None, *, max_step_s: float = 0.2) -> dict[str, Any]:
    audit = audit_ef_boundary(params, max_step_s=max_step_s)
    return asdict(audit)


def run_block6m4_audit(params=None, *, max_step_s: float = 0.2) -> Block6M4Audit:
    return audit_ef_boundary(params, max_step_s=max_step_s)
