"""Adapter between API inputs and the GLI calculation package."""

from datetime import datetime, timezone
from math import exp, pi
from typing import List

from gli.parameters import (
    FluidProperties,
    GLIParameters,
    GasProperties,
    Geometry,
    ModelCoefficients,
    OperatingConditions,
    ValveParameters,
)
from gli.simulation import prepare_initial_cycle

from .database import save_simulation as persist_simulation
from .schemas import (
    SimulationInputs,
    SimulationMetrics,
    SimulationPoint,
    SimulationResult,
    SimulationValidationRow,
)


DEFAULT_CASING_INNER_DIAMETER_M = 0.1397
DEFAULT_BELLOWS_AREA_M2 = 0.0005
DEFAULT_PORT_AREA_M2 = 0.0001
DEFAULT_VALVE_AREA_RATIO = 0.75
DEFAULT_RESERVOIR_LIQUID_RATE_M3_S = 2.0e-5
MPA_TO_PA = 1_000_000.0
PA_TO_MPA = 1.0 / MPA_TO_PA
KGF_CM2_TO_PA = 98_066.5
SECONDS_PER_DAY = 86_400.0


def build_parameters(inputs: SimulationInputs) -> GLIParameters:
    """Convert frontend inputs into the backend parameter objects."""

    annulus_cross_area_m2 = pi * (
        DEFAULT_CASING_INNER_DIAMETER_M**2 - inputs.tubingDiameter**2
    ) / 4.0

    return GLIParameters(
        geometry=Geometry(
            tubing_diameter_m=inputs.tubingDiameter,
            casing_inner_diameter_m=DEFAULT_CASING_INNER_DIAMETER_M,
            annulus_cross_area_m2=annulus_cross_area_m2,
            valve_depth_m=inputs.valveDepth,
            initial_slug_length_m=inputs.slugLength,
        ),
        fluids=FluidProperties(
            api=inputs.api,
            bsw_percent=inputs.bsw,
            gas_relative_density=inputs.gasRelativeDensity,
            water_relative_density=inputs.waterRelativeDensity,
        ),
        gas=GasProperties(
            gas_molar_mass_kg_mol=0.029 * inputs.gasRelativeDensity,
            temp_c1_k=300.0,
            temp_c2_k=330.0,
            temp_t1_k=330.0,
            temp_t3_k=300.0,
            temp_ts_k=(inputs.surfaceTemperature - 32.0) * 5.0 / 9.0 + 273.15,
        ),
        valves=ValveParameters(
            bellows_area_m2=DEFAULT_BELLOWS_AREA_M2,
            port_area_m2=DEFAULT_PORT_AREA_M2,
            rv=DEFAULT_VALVE_AREA_RATIO,
        ),
        operating=OperatingConditions(
            surface_tubing_pressure_pa=inputs.surfaceTubingPressure * MPA_TO_PA,
            injection_pressure_pa=inputs.injectionPressure * MPA_TO_PA,
            pto_over_pvo=inputs.casingPressureOpenRatio,
            reservoir_liquid_rate_m3_s=reservoir_liquid_rate(inputs),
        ),
        coefficients=ModelCoefficients(),
    )


def reservoir_liquid_rate(inputs: SimulationInputs) -> float:
    """Estimate reservoir feeding rate from Santos table 5.5 inputs."""

    wellhead_pressure_kgf_cm2 = inputs.surfaceTubingPressure * MPA_TO_PA / KGF_CM2_TO_PA
    drawdown_kgf_cm2 = max(0.0, inputs.staticReservoirPressure - wellhead_pressure_kgf_cm2)
    rate_m3_day = max(0.1, inputs.productivityIndex * drawdown_kgf_cm2)
    return rate_m3_day / SECONDS_PER_DAY


def build_stage_1_preview_points(
    inputs: SimulationInputs,
    initial_stage_1: dict,
    point_count: int = 41,
) -> List[SimulationPoint]:
    """Create a temporary stage-1 curve until the full ODE model is connected."""

    start_pressure_pa = initial_stage_1["p_c2"]
    injection_pressure_pa = inputs.injectionPressure * MPA_TO_PA
    target_pressure_pa = max(start_pressure_pa, injection_pressure_pa * 0.92)
    pressure_gap_pa = max(0.0, target_pressure_pa - start_pressure_pa)
    duration_s = max(60.0, round(pressure_gap_pa / 8500.0 + 120.0))
    points = []

    for index in range(point_count):
        fraction = index / (point_count - 1)
        time_s = fraction * duration_s
        pressure_pa = start_pressure_pa + pressure_gap_pa * (1.0 - exp(-4.0 * fraction))
        force = (target_pressure_pa - pressure_pa) * DEFAULT_BELLOWS_AREA_M2
        gas_rate = max(0.0, (injection_pressure_pa - pressure_pa) * PA_TO_MPA) * 1.8

        points.append(
            SimulationPoint(
                t=time_s,
                pressure=pressure_pa * PA_TO_MPA,
                force=force,
                gasRate=gas_rate,
            )
        )

    return points


def build_validation_rows(
    inputs: SimulationInputs,
    metrics: SimulationMetrics,
    points: List[SimulationPoint],
) -> List[SimulationValidationRow]:
    """Build dynamic estimates for the comparison table.

    These values are connected to the current preview model. They will be
    replaced by the full Santos cycle outputs as stages 2 to 5 are implemented.
    """

    tubing_area_m2 = pi * inputs.tubingDiameter**2 / 4.0
    initial_slug_volume_m3 = tubing_area_m2 * inputs.slugLength
    pressure_span_mpa = max(point.pressure for point in points) - min(point.pressure for point in points)
    gas_rate_avg = sum(point.gasRate for point in points) / len(points)
    recovery_factor = min(0.95, max(0.20, 0.45 + 0.035 * pressure_span_mpa + 0.004 * gas_rate_avg))
    final_slug_volume_m3 = initial_slug_volume_m3 * recovery_factor
    entrainment_volume_m3 = initial_slug_volume_m3 * min(0.25, 0.02 + 0.004 * gas_rate_avg)
    total_volume_m3 = final_slug_volume_m3 + entrainment_volume_m3
    lift_time_s = max(1.0, metrics.duration * (1.8 + inputs.slugLength / max(inputs.valveDepth, 1.0)))
    decompression_time_s = max(1.0, metrics.duration * (1.4 + inputs.injectionPressure / 10.0))
    feeding_rate_m3_s = reservoir_liquid_rate(inputs)
    feeding_time_s = max(1.0, initial_slug_volume_m3 / feeding_rate_m3_s)
    cycle_time_s = lift_time_s + decompression_time_s + feeding_time_s
    cycles = max(1, round(SECONDS_PER_DAY / cycle_time_s))
    liquid_rate_m3_day = total_volume_m3 * cycles
    injected_gas_m3_day = max(0.0, gas_rate_avg * cycle_time_s * cycles)
    avg_flow_pressure_kgf_cm2 = (
        sum(point.pressure for point in points) / len(points)
    ) * MPA_TO_PA / KGF_CM2_TO_PA

    values = [
        ("Volumen da golfada final [m3]", "0.309", "Figura 29", final_slug_volume_m3),
        ("Volumen producido por entrainment [m3]", "0.077", "Figura 30", entrainment_volume_m3),
        ("Volumen producido total [m3]", "0.387", "Figura 31", total_volume_m3),
        ("Recuperacion de liquido [%]", "0.740", "Figura 32", recovery_factor),
        ("Tiempo de elevacion [s]", "275", "Figura 33", lift_time_s),
        ("Tiempo de descompresion [s]", "275", "Figura 34", decompression_time_s),
        ("Tiempo de ciclo [s]", "1249", "Figura 35", cycle_time_s),
        ("Numero de ciclos", "69", "Figura 36", cycles),
        ("Vazao de liquido [m3/d]", "26.39", "Figura 37", liquid_rate_m3_day),
        ("Vazao de gas [m3/d]", "8500", "Figura 38", injected_gas_m3_day),
        ("Presion media de flujo [kgf/cm2]", "33.33", "Figura 41", avg_flow_pressure_kgf_cm2),
    ]

    return [
        SimulationValidationRow(
            parameter=parameter,
            liao=liao,
            reference=reference,
            simulator=f"{value:.3f}" if isinstance(value, float) and abs(value) < 100 else f"{value:.0f}",
        )
        for parameter, liao, reference, value in values
    ]


def simulate(inputs: SimulationInputs) -> SimulationResult:
    """Run the current backend simulation preview without saving it."""

    params = build_parameters(inputs)
    initial_cycle = prepare_initial_cycle(params)
    stage_1 = initial_cycle["stage_1"]
    points = build_stage_1_preview_points(inputs, stage_1)

    created_at = datetime.now(timezone.utc).isoformat()
    metrics = SimulationMetrics(
            rhoL=stage_1["rho_l"],
            pTo=stage_1["p_to"] * PA_TO_MPA,
            pVo=stage_1["p_vo"] * PA_TO_MPA,
            pBt=stage_1["p_bt"] * PA_TO_MPA,
            duration=points[-1].t,
        )

    result = SimulationResult(
        metrics=metrics,
        points=points,
        projectName=inputs.projectName,
        projectistName=inputs.projectistName,
        createdAt=created_at,
        validationRows=build_validation_rows(inputs, metrics, points),
    )
    return result


def save_simulation_run(inputs: SimulationInputs) -> SimulationResult:
    """Run and persist a simulation in the configured database."""

    result = simulate(inputs)
    created_at = result.createdAt or datetime.now(timezone.utc).isoformat()
    simulation_id = persist_simulation(inputs, result, created_at)
    return result.model_copy(update={"simulationId": simulation_id})
