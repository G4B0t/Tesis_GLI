"""Adapter between API inputs and the GLI calculation package."""

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

from .schemas import SimulationInputs, SimulationMetrics, SimulationPoint, SimulationResult


DEFAULT_CASING_INNER_DIAMETER_M = 0.1397
DEFAULT_BELLOWS_AREA_M2 = 0.0005
DEFAULT_PORT_AREA_M2 = 0.0001
DEFAULT_VALVE_AREA_RATIO = 0.75
DEFAULT_RESERVOIR_LIQUID_RATE_M3_S = 2.0e-5
MPA_TO_PA = 1_000_000.0
PA_TO_MPA = 1.0 / MPA_TO_PA


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
        ),
        gas=GasProperties(
            gas_molar_mass_kg_mol=0.029 * inputs.gasRelativeDensity,
            temp_c1_k=300.0,
            temp_c2_k=330.0,
            temp_t1_k=330.0,
            temp_t3_k=300.0,
            temp_ts_k=300.0,
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
            reservoir_liquid_rate_m3_s=DEFAULT_RESERVOIR_LIQUID_RATE_M3_S,
        ),
        coefficients=ModelCoefficients(),
    )


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


def simulate(inputs: SimulationInputs) -> SimulationResult:
    """Run the current backend simulation preview."""

    params = build_parameters(inputs)
    initial_cycle = prepare_initial_cycle(params)
    stage_1 = initial_cycle["stage_1"]
    points = build_stage_1_preview_points(inputs, stage_1)

    return SimulationResult(
        metrics=SimulationMetrics(
            rhoL=stage_1["rho_l"],
            pTo=stage_1["p_to"] * PA_TO_MPA,
            pVo=stage_1["p_vo"] * PA_TO_MPA,
            pBt=stage_1["p_bt"] * PA_TO_MPA,
            duration=points[-1].t,
        ),
        points=points,
    )
