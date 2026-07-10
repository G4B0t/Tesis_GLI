"""Block 7B: controlled local design matrix around Santos.

The purpose of this block is to move from one-at-a-time perturbations to a
small, traceable matrix of combined perturbations.  Passing this matrix creates
a *validated range candidate* for engineering review; it still does not declare
commercial certification for arbitrary wells.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import product
from typing import Any, Literal

from gli.audit_block6m5_af import run_block6m5_audit
from gli.audit_block7a_parametric import santos_frontend_inputs
from gli_api.schemas import SimulationInputs
from gli_api.simulation_service import build_parameters


MatrixStatus = Literal[
    "certified_reference",
    "validated_range_candidate",
    "provisional",
    "failed",
]


@dataclass(frozen=True)
class ParameterBand:
    field: str
    label: str
    base_value: float
    low_value: float
    high_value: float
    unit: str
    basis: str


@dataclass(frozen=True)
class MatrixScenario:
    scenario_id: str
    description: str
    values: dict[str, float]


@dataclass(frozen=True)
class MatrixScenarioResult:
    scenario_id: str
    description: str
    values: dict[str, float]
    status: MatrixStatus
    validation_level_candidate: str
    terminal_event: str
    event_times_s: dict[str, float]
    max_residual_normalized: float
    failed_contracts: tuple[str, ...]


@dataclass(frozen=True)
class Block7BDesignMatrixAudit:
    commercial_domain_certified: bool
    validated_range_candidate: bool
    statement: str
    base_case_id: str
    parameter_bands: tuple[ParameterBand, ...]
    scenario_count: int
    failed_scenarios: tuple[str, ...]
    provisional_scenarios: tuple[str, ...]
    max_residual_normalized: float
    results: tuple[MatrixScenarioResult, ...]


def default_parameter_bands() -> tuple[ParameterBand, ...]:
    base = santos_frontend_inputs()
    return (
        ParameterBand(
            "injectionPressure",
            "Presión de inyección",
            base.injectionPressure,
            base.injectionPressure * 0.95,
            base.injectionPressure * 1.05,
            "MPa",
            "Bloque 7A: perturbación local ±5%.",
        ),
        ParameterBand(
            "slugLength",
            "Longitud de golfada",
            base.slugLength,
            base.slugLength * 0.95,
            base.slugLength * 1.05,
            "m",
            "Bloque 7A: perturbación local ±5%.",
        ),
        ParameterBand(
            "valveDepth",
            "Profundidad de válvula",
            base.valveDepth,
            base.valveDepth * 0.95,
            base.valveDepth * 1.05,
            "m",
            "Bloque 7A: perturbación local ±5%.",
        ),
        ParameterBand(
            "tubingDiameter",
            "Diámetro tubing",
            base.tubingDiameter,
            base.tubingDiameter * 0.98,
            base.tubingDiameter * 1.02,
            "m",
            "Bloque 7A: perturbación local ±2%.",
        ),
        ParameterBand(
            "bsw",
            "BSW",
            base.bsw,
            base.bsw - 5.0,
            base.bsw + 5.0,
            "%",
            "Bloque 7A: perturbación local ±5 puntos porcentuales.",
        ),
        ParameterBand(
            "api",
            "Gravedad API",
            base.api,
            base.api - 2.0,
            base.api + 2.0,
            "API",
            "Bloque 7A: perturbación local ±2 grados API.",
        ),
    )


def _scenario_from_values(scenario_id: str, values: dict[str, float]) -> MatrixScenario:
    parts = ", ".join(f"{k}={v:.6g}" for k, v in values.items())
    return MatrixScenario(scenario_id, parts, dict(values))


def default_design_matrix() -> tuple[MatrixScenario, ...]:
    """Return a compact matrix with base, one-axis bounds and selected corners."""

    bands = {b.field: b for b in default_parameter_bands()}
    scenarios: list[MatrixScenario] = [_scenario_from_values("santos_reference", {})]

    for band in bands.values():
        scenarios.append(_scenario_from_values(f"{band.field}_low", {band.field: band.low_value}))
        scenarios.append(_scenario_from_values(f"{band.field}_high", {band.field: band.high_value}))

    paired_fields = (
        ("injectionPressure", "slugLength"),
        ("injectionPressure", "tubingDiameter"),
        ("valveDepth", "tubingDiameter"),
        ("bsw", "api"),
    )
    for left, right in paired_fields:
        for left_side, right_side in product(("low", "high"), repeat=2):
            left_band = bands[left]
            right_band = bands[right]
            values = {
                left: left_band.low_value if left_side == "low" else left_band.high_value,
                right: right_band.low_value if right_side == "low" else right_band.high_value,
            }
            scenarios.append(_scenario_from_values(f"{left}_{left_side}__{right}_{right_side}", values))

    return tuple(scenarios)


def _inputs_for_scenario(base: SimulationInputs, scenario: MatrixScenario) -> SimulationInputs:
    data = base.model_dump()
    data.update(scenario.values)
    data["projectName"] = f"Block 7B {scenario.scenario_id}"
    return SimulationInputs(**data)


def audit_matrix_scenario(
    scenario: MatrixScenario,
    *,
    base_inputs: SimulationInputs | None = None,
    max_step_s: float | None = 1.0,
) -> MatrixScenarioResult:
    base = base_inputs or santos_frontend_inputs()
    tested = _inputs_for_scenario(base, scenario)
    audit = run_block6m5_audit(build_parameters(tested), max_step_s=max_step_s)
    if scenario.scenario_id == "santos_reference":
        status: MatrixStatus = "certified_reference" if audit.certified else "failed"
    elif audit.certified:
        status = "validated_range_candidate"
    elif audit.failed_contracts:
        status = "failed"
    else:
        status = "provisional"
    return MatrixScenarioResult(
        scenario_id=scenario.scenario_id,
        description=scenario.description,
        values=scenario.values,
        status=status,
        validation_level_candidate=audit.validation_level_candidate,
        terminal_event=audit.terminal_event,
        event_times_s=audit.event_times_s,
        max_residual_normalized=audit.max_residual_normalized,
        failed_contracts=audit.failed_contracts,
    )


def run_block7b_design_matrix(
    *,
    scenarios: tuple[MatrixScenario, ...] | None = None,
    max_step_s: float | None = 1.0,
) -> Block7BDesignMatrixAudit:
    selected = scenarios or default_design_matrix()
    base_inputs = santos_frontend_inputs()
    results = tuple(
        audit_matrix_scenario(s, base_inputs=base_inputs, max_step_s=max_step_s)
        for s in selected
    )
    failed = tuple(r.scenario_id for r in results if r.status == "failed")
    provisional = tuple(r.scenario_id for r in results if r.status == "provisional")
    non_reference = [r for r in results if r.scenario_id != "santos_reference"]
    validated_candidate = bool(non_reference) and not failed and not provisional
    max_norm = max((r.max_residual_normalized for r in results), default=0.0)
    return Block7BDesignMatrixAudit(
        commercial_domain_certified=False,
        validated_range_candidate=validated_candidate,
        statement=(
            "La matriz 7B produce un candidato de rango validado local si todos los escenarios "
            "cierran A->F. No reemplaza validación con casos independientes de campo/literatura."
        ),
        base_case_id=base_inputs.caseId,
        parameter_bands=default_parameter_bands(),
        scenario_count=len(results),
        failed_scenarios=failed,
        provisional_scenarios=provisional,
        max_residual_normalized=float(max_norm),
        results=results,
    )


def audit_summary(*, max_step_s: float | None = 1.0) -> dict[str, Any]:
    return asdict(run_block7b_design_matrix(max_step_s=max_step_s))
