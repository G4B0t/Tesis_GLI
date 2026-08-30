"""Block 7A: local parametric sensitivity around the certified Santos case.

This module does not extend the certified domain by assertion.  It only runs
small, explicit perturbations around the Santos API input set and reports
whether the already-certified A->F contracts still close numerically.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from gli.audit_block6m5_af import run_block6m5_audit
from gli_api.schemas import SimulationInputs
from gli_api.simulation_service import build_parameters


SensitivityStatus = Literal["certified_reference", "local_stability_observed", "failed"]


@dataclass(frozen=True)
class SensitivityScenario:
    scenario_id: str
    field: str
    label: str
    multiplier: float | None = None
    absolute_delta: float | None = None
    unit: str = ""
    scientific_reason: str = ""


@dataclass(frozen=True)
class SensitivityResult:
    scenario_id: str
    field: str
    label: str
    base_value: float
    tested_value: float
    relative_change_percent: float
    status: SensitivityStatus
    validation_level_candidate: str
    terminal_event: str
    event_times_s: dict[str, float]
    max_residual_normalized: float
    failed_contracts: tuple[str, ...]
    interpretation: str


@dataclass(frozen=True)
class Block7ALocalSensitivityAudit:
    commercial_domain_certified: bool
    statement: str
    base_case_id: str
    max_residual_normalized: float
    failed_scenarios: tuple[str, ...]
    observed_stable_scenarios: tuple[str, ...]
    results: tuple[SensitivityResult, ...]


def santos_frontend_inputs() -> SimulationInputs:
    """Return the frozen frontend/API Santos input set used by the contract."""

    return SimulationInputs(
        tubingDiameter=0.050673,
        valveDepth=1480.0,
        slugLength=412.5,
        surfaceTubingPressure=0.788,
        injectionPressure=6.966,
        api=40.0,
        bsw=50.0,
        gasRelativeDensity=0.7,
        casingPressureOpenRatio=0.7,
        projectName="Santos A-F Certified",
        projectistName="Block 7A",
        waterRelativeDensity=1.07,
        surfaceTemperature=80.0,
        injectedGasReferenceRatio=0.8,
        caseId="santos-gli-50-70-80",
    )


def default_sensitivity_scenarios() -> tuple[SensitivityScenario, ...]:
    """Small local perturbations chosen for first-pass robustness screening."""

    return (
        SensitivityScenario(
            "injection_pressure_minus_5pct", "injectionPressure", "Presión de inyección -5%",
            multiplier=0.95, unit="MPa",
            scientific_reason="Evalúa margen frente a menor energía disponible de gas.",
        ),
        SensitivityScenario(
            "injection_pressure_plus_5pct", "injectionPressure", "Presión de inyección +5%",
            multiplier=1.05, unit="MPa",
            scientific_reason="Evalúa sensibilidad a mayor presión de compresor.",
        ),
        SensitivityScenario(
            "slug_length_minus_5pct", "slugLength", "Longitud de golfada -5%",
            multiplier=0.95, unit="m",
            scientific_reason="Evalúa menor inventario líquido inicial.",
        ),
        SensitivityScenario(
            "slug_length_plus_5pct", "slugLength", "Longitud de golfada +5%",
            multiplier=1.05, unit="m",
            scientific_reason="Evalúa mayor inventario líquido inicial.",
        ),
        SensitivityScenario(
            "valve_depth_minus_5pct", "valveDepth", "Profundidad de válvula -5%",
            multiplier=0.95, unit="m",
            scientific_reason="Evalúa desplazamiento geométrico hacia menor profundidad.",
        ),
        SensitivityScenario(
            "valve_depth_plus_5pct", "valveDepth", "Profundidad de válvula +5%",
            multiplier=1.05, unit="m",
            scientific_reason="Evalúa desplazamiento geométrico hacia mayor profundidad.",
        ),
        SensitivityScenario(
            "tubing_diameter_minus_2pct", "tubingDiameter", "Diámetro tubing -2%",
            multiplier=0.98, unit="m",
            scientific_reason="Evalúa tolerancia local a área de flujo menor.",
        ),
        SensitivityScenario(
            "tubing_diameter_plus_2pct", "tubingDiameter", "Diámetro tubing +2%",
            multiplier=1.02, unit="m",
            scientific_reason="Evalúa tolerancia local a área de flujo mayor.",
        ),
        SensitivityScenario(
            "bsw_minus_5pp", "bsw", "BSW -5 puntos porcentuales",
            absolute_delta=-5.0, unit="%",
            scientific_reason="Evalúa sensibilidad de densidad líquida por menor fracción de agua.",
        ),
        SensitivityScenario(
            "bsw_plus_5pp", "bsw", "BSW +5 puntos porcentuales",
            absolute_delta=5.0, unit="%",
            scientific_reason="Evalúa sensibilidad de densidad líquida por mayor fracción de agua.",
        ),
        SensitivityScenario(
            "api_minus_2deg", "api", "API -2 grados",
            absolute_delta=-2.0, unit="API",
            scientific_reason="Evalúa aceite ligeramente más pesado.",
        ),
        SensitivityScenario(
            "api_plus_2deg", "api", "API +2 grados",
            absolute_delta=2.0, unit="API",
            scientific_reason="Evalúa aceite ligeramente más liviano.",
        ),
    )


def _apply_scenario(base: SimulationInputs, scenario: SensitivityScenario) -> SimulationInputs:
    data = base.model_dump()
    base_value = float(data[scenario.field])
    if scenario.multiplier is not None:
        tested_value = base_value * scenario.multiplier
    elif scenario.absolute_delta is not None:
        tested_value = base_value + scenario.absolute_delta
    else:
        raise ValueError(f"Scenario {scenario.scenario_id} has no perturbation.")
    data[scenario.field] = tested_value
    data["projectName"] = f"Block 7A {scenario.scenario_id}"
    return SimulationInputs(**data)


def audit_sensitivity_scenario(
    scenario: SensitivityScenario,
    *,
    base_inputs: SimulationInputs | None = None,
    max_step_s: float | None = 1.0,
) -> SensitivityResult:
    base = base_inputs or santos_frontend_inputs()
    tested = _apply_scenario(base, scenario)
    base_value = float(base.model_dump()[scenario.field])
    tested_value = float(tested.model_dump()[scenario.field])
    relative_change = 100.0 * (tested_value - base_value) / max(abs(base_value), 1e-18)
    try:
        audit = run_block6m5_audit(build_parameters(tested), max_step_s=max_step_s)
    except ValueError as exc:
        return SensitivityResult(
            scenario_id=scenario.scenario_id,
            field=scenario.field,
            label=scenario.label,
            base_value=base_value,
            tested_value=tested_value,
            relative_change_percent=relative_change,
            status="failed",
            validation_level_candidate="out_of_domain",
            terminal_event="INPUT_DOMAIN_ERROR",
            event_times_s={},
            max_residual_normalized=float("inf"),
            failed_contracts=("input_geometry_domain",),
            interpretation=f"Entrada fuera del dominio geométrico/IPR: {exc}",
        )
    status: SensitivityStatus = "local_stability_observed" if audit.certified else "failed"
    interpretation = (
        "Los contratos A->F cierran para esta perturbación local; esto evidencia estabilidad "
        "numérica local, no certificación comercial global."
        if audit.certified
        else "La cadena corregida no cerró para esta perturbación; requiere diagnóstico antes de uso de diseño."
    )
    return SensitivityResult(
        scenario_id=scenario.scenario_id,
        field=scenario.field,
        label=scenario.label,
        base_value=base_value,
        tested_value=tested_value,
        relative_change_percent=relative_change,
        status=status,
        validation_level_candidate=audit.validation_level_candidate,
        terminal_event=audit.terminal_event,
        event_times_s=audit.event_times_s,
        max_residual_normalized=audit.max_residual_normalized,
        failed_contracts=audit.failed_contracts,
        interpretation=interpretation,
    )


def run_block7a_local_sensitivity(
    *,
    scenarios: tuple[SensitivityScenario, ...] | None = None,
    max_step_s: float | None = 1.0,
) -> Block7ALocalSensitivityAudit:
    base_inputs = santos_frontend_inputs()
    base_audit = run_block6m5_audit(build_parameters(base_inputs), max_step_s=max_step_s)
    base_result = SensitivityResult(
        scenario_id="santos_reference",
        field="caseId",
        label="Caso Santos certificado",
        base_value=0.0,
        tested_value=0.0,
        relative_change_percent=0.0,
        status="certified_reference" if base_audit.certified else "failed",
        validation_level_candidate=base_audit.validation_level_candidate,
        terminal_event=base_audit.terminal_event,
        event_times_s=base_audit.event_times_s,
        max_residual_normalized=base_audit.max_residual_normalized,
        failed_contracts=base_audit.failed_contracts,
        interpretation=(
            "Caso patrón certificado A->F. Es la única certificación estricta actual."
            if base_audit.certified
            else "El caso patrón no cerró; no se puede ejecutar sensibilidad."
        ),
    )
    selected = scenarios or default_sensitivity_scenarios()
    results = [base_result]
    if base_audit.certified:
        results.extend(
            audit_sensitivity_scenario(s, base_inputs=base_inputs, max_step_s=max_step_s)
            for s in selected
        )
    failed = tuple(r.scenario_id for r in results if r.status == "failed")
    observed = tuple(r.scenario_id for r in results if r.status == "local_stability_observed")
    max_norm = max((r.max_residual_normalized for r in results), default=0.0)
    return Block7ALocalSensitivityAudit(
        commercial_domain_certified=False,
        statement=(
            "Bloque 7A es una auditoría de estabilidad local alrededor de Santos. "
            "No define todavía un dominio comercial validado para diseño."
        ),
        base_case_id=base_inputs.caseId,
        max_residual_normalized=float(max_norm),
        failed_scenarios=failed,
        observed_stable_scenarios=observed,
        results=tuple(results),
    )


def audit_summary(*, max_step_s: float | None = 1.0) -> dict[str, Any]:
    return asdict(run_block7a_local_sensitivity(max_step_s=max_step_s))
