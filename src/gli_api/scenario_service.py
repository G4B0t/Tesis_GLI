"""Scenario comparison service built on top of the certified simulator."""

from .schemas import (
    ScenarioCase,
    ScenarioComparisonRequest,
    ScenarioComparisonResponse,
    ScenarioResult,
    ScenarioSummary,
    SimulationResult,
)
from .simulation_service import simulate


def engineering_value(result: SimulationResult, name: str) -> float | None:
    """Return a named engineering metric from a simulation result."""

    if result.diagnostics is None:
        return None
    for metric in result.diagnostics.engineeringMetrics:
        if metric.name == name:
            return metric.value
    return None


def summarize_scenario(
    scenario: ScenarioCase,
    result: SimulationResult,
    base_daily_liquid: float | None,
) -> ScenarioSummary:
    """Build the compact row used by frontend scenario comparison."""

    daily_liquid = engineering_value(result, "estimatedDailyLiquid")
    if base_daily_liquid and daily_liquid is not None:
        delta_daily_liquid = (daily_liquid - base_daily_liquid) / base_daily_liquid * 100.0
    else:
        delta_daily_liquid = None

    warnings = list(result.modelLimitations)
    if result.validationLevel in {"out_of_domain", "failed"}:
        warnings.insert(0, "Scenario is not valid for engineering recommendation.")

    return ScenarioSummary(
        name=scenario.name,
        description=scenario.description,
        validationLevel=result.validationLevel or "provisional",
        terminalEvent=result.terminalEvent,
        duration=result.metrics.duration,
        producedLiquidPerCycle=engineering_value(result, "producedLiquidPerCycle"),
        estimatedDailyLiquid=daily_liquid,
        injectedGasPerCycle=engineering_value(result, "injectedGasPerCycle"),
        gasLiquidRatio=engineering_value(result, "gasLiquidRatio"),
        fallbackRatio=engineering_value(result, "fallbackRatio"),
        slugRecovery=engineering_value(result, "slugRecovery"),
        cyclesPerDay=engineering_value(result, "cyclesPerDay"),
        deltaDailyLiquidPercent=delta_daily_liquid,
        warnings=warnings,
    )


def compare_scenarios(request: ScenarioComparisonRequest) -> ScenarioComparisonResponse:
    """Run every scenario with the existing solver and return comparable rows."""

    scenario_results: list[ScenarioResult] = []
    base_daily_liquid: float | None = None

    for index, scenario in enumerate(request.scenarios):
        try:
            result = simulate(scenario.inputs)
            if index == 0:
                base_daily_liquid = engineering_value(result, "estimatedDailyLiquid")
            summary = summarize_scenario(scenario, result, base_daily_liquid)
            scenario_results.append(ScenarioResult(summary=summary, result=result))
        except Exception as exc:
            scenario_results.append(
                ScenarioResult(
                    summary=ScenarioSummary(
                        name=scenario.name,
                        description=scenario.description,
                        validationLevel="failed",
                        warnings=["Scenario calculation failed."],
                    ),
                    error=str(exc),
                )
            )

    return ScenarioComparisonResponse(baseName=request.baseName, scenarios=scenario_results)
