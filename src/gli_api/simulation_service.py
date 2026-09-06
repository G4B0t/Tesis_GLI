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
from gli.design_domain import classify_design_domain
from gli.simulation import prepare_initial_cycle
from gli.stage1_dynamic import simulate_stage_1
from gli.stage_bc_dynamic import simulate_stage_b_to_c
from gli.stage_bc_common import simulate_stage_b_to_c_common, common_to_stage_bc_result
from gli.stage_cd_common import simulate_stage_c_to_d_common, common_to_stage_cd_result
from gli.stage_de_dynamic import simulate_stage_d_to_e
from gli.stage_ef_dynamic import simulate_stage_e_to_f
from gli.reference_cases import REFERENCE_CASES,SANTOS_50_70_80
from gli.reference_gas import injected_gas_target_std_m3, liao_reference_gas_volume_std_m3
from gli.valves import gas_lift_valve_resultant_force
from gli.reservoir import productivity_index_m3_day_kgf_cm2_to_si
from gli.units import kgf_cm2_gauge_to_pa_absolute

from .database import save_simulation as persist_simulation
from .schemas import (
    BalanceError,
    DiagnosticVariable,
    EngineeringMetric,
    SimulationInputs,
    SimulationDiagnostics,
    SimulationMetrics,
    SimulationPoint,
    SimulationResult,
    SimulationValidationRow,
    StageDuration,
)


DEFAULT_CASING_INNER_DIAMETER_M = 0.12573
DEFAULT_BELLOWS_AREA_M2 = pi * (0.0381**2) / 4.0
DEFAULT_PORT_AREA_M2 = pi * (0.0127**2) / 4.0
DEFAULT_VALVE_AREA_RATIO = 0.30
DEFAULT_RESERVOIR_LIQUID_RATE_M3_S = 2.0e-5
MPA_TO_PA = 1_000_000.0
PA_TO_MPA = 1.0 / MPA_TO_PA
KGF_CM2_TO_PA = 98_066.5
SECONDS_PER_DAY = 86_400.0


def cumulative_trapezoid(values, times) -> list[float]:
    """Return cumulative trapezoidal integral for aligned solver arrays."""

    total = 0.0
    cumulative = [0.0]
    for index in range(1, len(times)):
        dt = float(times[index] - times[index - 1])
        total += 0.5 * float(values[index] + values[index - 1]) * dt
        cumulative.append(total)
    return cumulative


def max_or_none(values: list[float]) -> float | None:
    return max(values) if values else None


def safe_divide(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if abs(denominator) > 1.0e-12 else None


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
            perforation_depth_m=inputs.wellDepth,
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
            injected_over_reference_gas_volume=inputs.injectedGasReferenceRatio,
            reservoir_static_pressure_pa=kgf_cm2_gauge_to_pa_absolute(inputs.staticReservoirPressure),
            productivity_index_m3_s_pa=productivity_index_m3_day_kgf_cm2_to_si(inputs.productivityIndex),
        ),
        coefficients=ModelCoefficients(),
    )


def reservoir_liquid_rate(inputs: SimulationInputs) -> float:
    """Legacy nominal rate retained only for compatibility/report estimates.

    Production ODEs evaluate the SI IPR from instantaneous P_t1. This nominal
    value uses the surface pressure solely as a non-dynamic initialization
    estimate and performs no clipping.
    """

    wellhead_pressure_kgf_cm2 = inputs.surfaceTubingPressure * MPA_TO_PA / KGF_CM2_TO_PA
    drawdown_kgf_cm2 = inputs.staticReservoirPressure - wellhead_pressure_kgf_cm2
    rate_m3_day = inputs.productivityIndex * drawdown_kgf_cm2
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
    """Run the source-qualified chain; expose no uncertified Stage-4.2 points."""

    if inputs.caseId != SANTOS_50_70_80.case_id:
        raise ValueError("Only the fully specified Santos case can be simulated; Liao Table 5.14 is a partial benchmark")
    params = build_parameters(inputs)
    initial_cycle = prepare_initial_cycle(params)
    stage_1 = initial_cycle["stage_1"]
    dynamic = simulate_stage_1(params)
    dynamic_bc_common = simulate_stage_b_to_c_common(params, stage_a_b=dynamic, rhs_mode="santos_compatible")
    if not dynamic_bc_common.certified:
        raise RuntimeError("Certified common B_TO_C segment required")
    dynamic_bc = common_to_stage_bc_result(dynamic_bc_common, params)
    dynamic_cd_common = simulate_stage_c_to_d_common(params, stage_b_c_common=dynamic_bc_common, rhs_mode="santos_corrected")
    if not dynamic_cd_common.certified:
        raise RuntimeError("Certified common C_TO_D segment required")
    dynamic_cd = common_to_stage_cd_result(dynamic_cd_common, params)
    dynamic_de = simulate_stage_d_to_e(params, stage_c_d=dynamic_cd, rhs_mode="santos_corrected")
    dynamic_ef = None
    if dynamic_de.event_e_reached and dynamic_de.source_certified:
        dynamic_ef = simulate_stage_e_to_f(params, stage_d_e=dynamic_de, rhs_mode="santos_corrected")
    if dynamic_de.film_velocity_m_s is None:
        raise RuntimeError("Certified D_TO_E segment must expose film velocity memory")
    chain_certified = (
        dynamic_bc_common.certified
        and dynamic_cd_common.certified
        and dynamic_de.event_e_reached
        and dynamic_de.gas_balance_relative_error <= 1e-8
        and dynamic_de.liquid_balance_relative_error <= 1e-8
        and dynamic_de.source_certified
        and dynamic_ef is not None
        and dynamic_ef.corrected_certified
        and dynamic_ef.gas_balance_relative_error <= 1e-8
        and dynamic_ef.liquid_balance_relative_error <= 1e-8
        and not bool(dynamic_ef.valve_open.any())
    )
    dynamic_gas_injected = cumulative_trapezoid(
        dynamic.standard_gas_rate_m3_s,
        dynamic.time_s,
    )
    points = [
        SimulationPoint(
            t=float(t), pressure=float(p * PA_TO_MPA),
            force=float(force), gasRate=float(rate), stage="A_B",
            annulusPressure=float(p * PA_TO_MPA),
            gasInjectedVolume=float(gas_volume),
            motorValveRate=float(rate),
            glvMassRate=0.0,
        )
        for t, p, force, rate, gas_volume in zip(
            dynamic.time_s, dynamic.p_c1_pa,
            dynamic.resultant_force_n, dynamic.standard_gas_rate_m3_s,
            dynamic_gas_injected,
        )
    ]
    for t,p1,p2,pb,rate,mgl,vgi,h_l,h_b,film in zip(
        dynamic_bc.time_s[1:],dynamic_bc.p_c1_pa[1:],dynamic_bc.p_c2_pa[1:],
        dynamic_bc.p_bubble_pa[1:],dynamic_bc.motor_rate_std_m3_s[1:],
        dynamic_bc.gl_mass_rate_kg_s[1:],dynamic_bc.injected_volume_std_m3[1:],
        dynamic_bc.h_l_m[1:],dynamic_bc.h_b_m[1:],dynamic_bc.film_thickness_m[1:]
    ):
        force=gas_lift_valve_resultant_force(
            p2,stage_1["p_bt"],stage_1["p_to"],params.valves.rv,params.valves.bellows_area_m2
        )
        points.append(SimulationPoint(
            t=float(dynamic.opening_time_s+t),pressure=float(p1*PA_TO_MPA),
            force=float(force),gasRate=float(rate),stage="B_C",
            annulusPressure=float(p1*PA_TO_MPA),bubblePressure=float(pb*PA_TO_MPA),
            slugTop=float(h_l),slugBase=float(h_b),filmThickness=float(film),
            gasInjectedVolume=float(vgi),motorValveRate=float(rate),glvMassRate=float(mgl),
        ))
    offset_c=dynamic.opening_time_s+dynamic_bc.event_c_time_s
    final_gas_injected = float(dynamic_bc.injected_volume_std_m3[-1])
    for t,p1,p2,pt,pwf,h_l,h_b,v_l,v_b,film,film_v,fb,mgl,force,is_open in zip(
        dynamic_cd.time_s[1:],dynamic_cd.p_c1_pa[1:],dynamic_cd.p_c2_pa[1:],
        dynamic_cd.p_tubing_pa[1:],dynamic_cd.p_bottom_pa[1:],dynamic_cd.h_l_m[1:],
        dynamic_cd.h_b_m[1:],dynamic_cd.v_l_m_s[1:],dynamic_cd.v_b_m_s[1:],
        dynamic_cd.film_thickness_m[1:],dynamic_cd.film_volume_m3[1:],dynamic_cd.fallback_volume_m3[1:],
        dynamic_cd.gl_mass_rate_kg_s[1:],dynamic_cd.valve_force_n[1:],dynamic_cd.valve_open[1:]
    ):
        points.append(SimulationPoint(
            t=float(offset_c+t),pressure=float(p1*PA_TO_MPA),force=float(force),
            gasRate=0.0,stage="C_D",annulusPressure=float(p1*PA_TO_MPA),
            bubblePressure=float(pt*PA_TO_MPA),bottomPressure=float(pwf*PA_TO_MPA),
            slugTop=float(h_l),slugBase=float(h_b),filmThickness=float(film),
            slugVelocity=float(v_l),bubbleVelocity=float(v_b),filmVolume=float(film_v),fallbackVolume=float(fb),
            gasLiftValveOpen=bool(is_open),gasInjectedVolume=final_gas_injected,
            motorValveRate=0.0,glvMassRate=float(mgl),
        ))
    offset_d=offset_c+dynamic_cd.event_d_time_s
    for t,p1,pt,pwf,h_l,h_b,v_l,v_b,vf,film,fb,slug,q,vp,mgl,force,is_open in zip(
        dynamic_de.time_s[1:],dynamic_de.p_c1_pa[1:],dynamic_de.p_tubing_pa[1:],
        dynamic_de.p_bottom_pa[1:],dynamic_de.h_l_m[1:],dynamic_de.h_b_m[1:],
        dynamic_de.v_l_m_s[1:],dynamic_de.v_b_m_s[1:],dynamic_de.film_velocity_m_s[1:],
        dynamic_de.film_volume_m3[1:],
        dynamic_de.fallback_volume_m3[1:],dynamic_de.slug_volume_m3[1:],
        dynamic_de.liquid_rate_m3_s[1:],dynamic_de.produced_volume_m3[1:],
        dynamic_de.gl_mass_rate_kg_s[1:],
        dynamic_de.valve_force_n[1:],dynamic_de.valve_open[1:]):
        points.append(SimulationPoint(t=float(offset_d+t),pressure=float(p1*PA_TO_MPA),
            force=float(force),gasRate=0.0,stage="D_E",annulusPressure=float(p1*PA_TO_MPA),
            bubblePressure=float(pt*PA_TO_MPA),bottomPressure=float(pwf*PA_TO_MPA),
            slugTop=float(h_l),slugBase=float(h_b),slugVelocity=float(v_l),bubbleVelocity=float(v_b),
            filmVolume=float(film),fallbackVolume=float(fb),slugVolume=float(slug),
            liquidRate=float(q),producedVolume=float(vp),gasLiftValveOpen=bool(is_open),
            gasInjectedVolume=final_gas_injected,filmVelocity=float(vf),
            motorValveRate=0.0,glvMassRate=float(mgl)))
    de_end = float(dynamic_de.integration_end_time_s if dynamic_de.integration_end_time_s is not None else dynamic_de.time_s[-1])
    offset_e=offset_d+de_end
    annulus_e=float(dynamic_de.p_c1_pa[-1]*PA_TO_MPA)
    for t,pt,vg,vf,y,film,fb,prod,mdot,is_open in (zip(
        dynamic_ef.time_s[1:],dynamic_ef.tubing_pressure_pa[1:],
        dynamic_ef.gas_velocity_m_s[1:],dynamic_ef.film_velocity_m_s[1:],
        dynamic_ef.film_thickness_m[1:],dynamic_ef.film_volume_m3[1:],
        dynamic_ef.fallback_volume_m3[1:],dynamic_ef.produced_film_volume_m3[1:],
        dynamic_ef.surface_gas_rate_kg_s[1:],dynamic_ef.valve_open[1:]) if chain_certified else ()):
        points.append(SimulationPoint(
            t=float(offset_e+t),pressure=float(pt*PA_TO_MPA),force=0.0,
            gasRate=float(mdot),stage="E_F",annulusPressure=annulus_e,
            bubblePressure=float(pt*PA_TO_MPA),filmThickness=float(y),
            bubbleVelocity=float(vg),slugVelocity=float(vf),filmVelocity=float(vf),filmVolume=float(film),
            fallbackVolume=float(fb),producedVolume=float(prod),liquidRate=0.0,
            gasLiftValveOpen=bool(is_open),gasInjectedVolume=final_gas_injected,
            motorValveRate=0.0,glvMassRate=0.0))

    created_at = datetime.now(timezone.utc).isoformat()
    metrics = SimulationMetrics(
            rhoL=stage_1["rho_l"],
            pTo=stage_1["p_to"] * PA_TO_MPA,
            pVo=stage_1["p_vo"] * PA_TO_MPA,
            pBt=stage_1["p_bt"] * PA_TO_MPA,
            duration=float(points[-1].t),
            vgRef=liao_reference_gas_volume_std_m3(params),
            vgiTarget=injected_gas_target_std_m3(params),
        )
    duration = metrics.duration
    stage_durations = [
        StageDuration(stage="A_B", startTime=0.0, endTime=float(dynamic.opening_time_s),
                      duration=float(dynamic.opening_time_s)),
        StageDuration(stage="B_C", startTime=float(dynamic.opening_time_s), endTime=float(offset_c),
                      duration=float(dynamic_bc.event_c_time_s)),
        StageDuration(stage="C_D", startTime=float(offset_c), endTime=float(offset_d),
                      duration=float(dynamic_cd.event_d_time_s)),
        StageDuration(stage="D_E", startTime=float(offset_d), endTime=float(offset_e),
                      duration=de_end),
    ]
    balance_errors = [
        BalanceError(
            stage="A_B",
            gasRelativeError=float(dynamic.mass_balance_relative_error),
            source="Stage1Result.mass_balance_relative_error",
        ),
        BalanceError(
            stage="B_C",
            gasRelativeError=float(dynamic_bc.gas_balance_relative_error),
            liquidRelativeError=float(dynamic_bc.liquid_balance_relative_error),
            source="StageBCResult gas/liquid balance closures",
        ),
        BalanceError(
            stage="C_D",
            gasRelativeError=float(dynamic_cd.gas_balance_relative_error),
            liquidRelativeError=float(dynamic_cd.liquid_balance_relative_error),
            source="StageCDResult gas/liquid balance closures",
        ),
        BalanceError(
            stage="D_E",
            gasRelativeError=float(dynamic_de.gas_balance_relative_error),
            liquidRelativeError=float(dynamic_de.liquid_balance_relative_error),
            source="StageDEResult gas/liquid balance closures",
        ),
    ]
    diagnostic_variables = [
        DiagnosticVariable(
            name="gasInjectedVolume",
            unit="std m3",
            source="A_B trapezoidal integral of motor valve standard gas rate; B_C injected_volume_std_m3 state",
            formula="integral(q_motor_std dt)",
            stage="A_B/B_C",
            certification="Partial upstream numerical gas-injection ledger; not complete-cycle certification.",
        ),
        DiagnosticVariable(
            name="filmVelocity",
            unit="m/s",
            source="StageDEResult.film_velocity_m_s",
            formula="D->E film momentum/memory state",
            stage="D_E",
            certification="Stage 4.2 is withheld until physical E and its identity gate exist.",
        ),
        DiagnosticVariable(
            name="motorValveRate",
            unit="std m3/s",
            source="Stage1Result.standard_gas_rate_m3_s and StageBCResult.motor_rate_std_m3_s",
            formula="surface motor-valve gas-rate correlation",
            stage="A_B/B_C",
            certification="Same rate used by the mass balance of the existing solver.",
        ),
        DiagnosticVariable(
            name="glvMassRate",
            unit="kg/s",
            source="StageBCResult/StageCDResult/StageDEResult.gl_mass_rate_kg_s",
            formula="compressible gas-lift-valve orifice proxy",
            stage="B_C/C_D/D_E",
            certification="Same transfer term used in the stage gas inventories.",
        ),
        DiagnosticVariable(
            name="stageDurations",
            unit="s",
            source="event times from Stage1Result and StageBC/CD/DE results",
            formula="event_end_time - event_start_time",
            stage="A_E_PARTIAL",
            certification="Elapsed partial trajectory to the reported terminal event, not a cycle duration.",
        ),
    ]
    film_velocities = [abs(point.filmVelocity) for point in points if point.filmVelocity is not None]
    motor_rates = [point.motorValveRate for point in points if point.motorValveRate is not None]
    glv_rates = [point.glvMassRate for point in points if point.glvMassRate is not None]
    final_point = points[-1]
    produced_liquid_per_cycle = float(final_point.producedVolume or 0.0)
    fallback_volume = float(final_point.fallbackVolume or 0.0)
    initial_slug_volume = pi * inputs.tubingDiameter**2 / 4.0 * inputs.slugLength
    # No H exists: an elapsed partial trajectory is not a cycle duration.
    cycles_per_day = None
    estimated_daily_liquid = None
    estimated_daily_injected_gas = None
    fallback_denominator = produced_liquid_per_cycle + fallback_volume
    engineering_metrics = [
        EngineeringMetric(
            name="producedLiquidPerCycle",
            label="Liquido producido en el tramo simulado",
            value=produced_liquid_per_cycle,
            unit="m3",
            formula="V_producido_final",
            assumption="Ledger parcial; el evento H no está disponible.",
            source="SimulationPoint.producedVolume en el ultimo punto D_E",
            use="Inspeccionar producción parcial; no representa un ciclo completo.",
            certification="PARTIAL_TRAJECTORY_ONLY; clave histórica conservada por compatibilidad.",
        ),
        EngineeringMetric(
            name="cyclesPerDay",
            label="Ciclos por dia estimados",
            value=cycles_per_day,
            unit="ciclos/d",
            formula="86400 / duracion_ciclo",
            assumption="Operacion repetitiva estable con el mismo ciclo simulado.",
            source="SimulationMetrics.duration",
            use="Estimar frecuencia operativa diaria.",
            certification="Derivado de tiempo de ciclo certificado por eventos B-C-D-E-F.",
        ),
        EngineeringMetric(
            name="estimatedDailyLiquid",
            label="Produccion diaria estimada",
            value=estimated_daily_liquid,
            unit="m3/d",
            formula="V_producido_por_ciclo * ciclos_por_dia",
            assumption="El ciclo simulado se repite sin variacion de reservorio ni condiciones de superficie.",
            source="producedLiquidPerCycle y cyclesPerDay",
            use="Indicador de produccion para comparacion de escenarios.",
            certification="Metrica derivada; no representa garantia de campo sin validacion operacional.",
        ),
        EngineeringMetric(
            name="injectedGasPerCycle",
            label="Gas inyectado por ciclo",
            value=final_gas_injected,
            unit="std m3/ciclo",
            formula="V_gas_inyectado_final",
            assumption="Gas acumulado medido en condicion estandar del modelo.",
            source="SimulationDiagnostics.gasInjectedVolume",
            use="Medir consumo de gas por ciclo GLI.",
            certification="Derivado de la integral certificada de caudal de valvula motor.",
        ),
        EngineeringMetric(
            name="estimatedDailyInjectedGas",
            label="Gas diario estimado",
            value=estimated_daily_injected_gas,
            unit="std m3/d",
            formula="gas_inyectado_por_ciclo * ciclos_por_dia",
            assumption="El ciclo simulado se repite durante 24 horas.",
            source="injectedGasPerCycle y cyclesPerDay",
            use="Comparar demanda diaria de gas de inyeccion.",
            certification="Metrica operacional derivada de outputs certificados.",
        ),
        EngineeringMetric(
            name="gasLiquidRatio",
            label="Relacion gas-liquido inyectado",
            value=safe_divide(final_gas_injected, produced_liquid_per_cycle),
            unit="std m3/m3",
            formula="gas_inyectado_por_ciclo / liquido_producido_por_ciclo",
            assumption="Usa gas inyectado, no gas producido de formacion.",
            source="gasInjectedVolume y producedVolume final",
            use="Indicador de eficiencia de uso de gas.",
            certification="Metrica derivada; debe interpretarse dentro del dominio validado.",
        ),
        EngineeringMetric(
            name="fallbackRatio",
            label="Fraccion fallback",
            value=safe_divide(fallback_volume, fallback_denominator),
            unit="fraccion",
            formula="fallback_final / (fallback_final + producido_final)",
            assumption="Compara liquido no producido contra liquido movilizado observado.",
            source="fallbackVolume y producedVolume final",
            use="Detectar perdida de eficiencia por retorno de pelicula/liquido.",
            certification="Metrica derivada de ledgers de liquido del solver.",
        ),
        EngineeringMetric(
            name="slugRecovery",
            label="Recuperacion de slug inicial",
            value=safe_divide(produced_liquid_per_cycle, initial_slug_volume),
            unit="fraccion",
            formula="V_producido_final / (area_tubing * longitud_slug_inicial)",
            assumption="Referencia contra volumen geometrico inicial de slug.",
            source="SimulationInputs.tubingDiameter, slugLength y producedVolume final",
            use="Evaluar que fraccion del slug inicial se transforma en liquido producido.",
            certification="Metrica derivada geometrica; no agrega fisica nueva.",
        ),
    ]
    for metric in engineering_metrics:
        if metric.name in {"cyclesPerDay", "estimatedDailyLiquid", "estimatedDailyInjectedGas"}:
            metric.assumption = "H no disponible: no existe duración de ciclo A→H."
            metric.certification = "UNAVAILABLE_INCOMPLETE_CYCLE"
            metric.use = "No disponible para recomendaciones ni comparación diaria."
            metric.source = "No disponible: H no fue calculado."
        elif metric.name == "injectedGasPerCycle":
            metric.label = "Gas inyectado en el tramo simulado"
            metric.unit = "std m3"
            metric.certification = "PARTIAL_TRAJECTORY_ONLY; clave histórica conservada por compatibilidad."
            metric.use = "Inspeccionar consumo acumulado del tramo parcial, no por ciclo."
        else:
            metric.certification = "PARTIAL_TRAJECTORY_ONLY; no constituye recomendación de diseño."
    diagnostics = SimulationDiagnostics(
        stageDurations=stage_durations,
        balanceErrors=balance_errors,
        variables=diagnostic_variables,
        engineeringMetrics=engineering_metrics,
        gasInjectedVolume=final_gas_injected,
        maxFilmVelocity=max_or_none(film_velocities),
        maxMotorValveRate=max_or_none(motor_rates),
        maxGlvMassRate=max_or_none(glv_rates),
    )

    domain = classify_design_domain(inputs, chain_certified=chain_certified)
    if domain.validation_level == "certified":
        physical_scope = (
            "SOURCE_CERTIFIED_A_TO_F: all Stage 4.2 source-equation and identity gates passed."
        )
        model_limitations = [
            "Certified only for the exact Santos frontend/API reference input set.",
            "Liao Table 5.14 remains a partial benchmark, not a quantitative validation target for this case.",
            "Certification requires the exact seven-variable Santos Stage 4.2 contract.",
        ]
    elif domain.validation_level == "validated_range_candidate":
        physical_scope = (
            "A_TO_F validated_range_candidate: corrected chain closed inside the Block 7B "
            "local design matrix around Santos. This is not yet a commercial certified domain."
        )
        model_limitations = [
            domain.statement,
            "Requires independent field/literature cases before commercial design certification.",
            "Use for controlled engineering screening, not final design guarantee.",
        ]
    elif domain.validation_level == "out_of_domain":
        physical_scope = (
            "A_TO_F out_of_domain: corrected chain may have produced a numerical trajectory, "
            "but at least one input is outside the Block 7B local matrix."
        )
        model_limitations = [
            domain.statement,
            f"Outside local matrix fields: {', '.join(domain.outside_fields)}.",
            "Result must be treated as exploratory until a sensitivity/validation block covers this region.",
        ]
    else:
        physical_scope = (
            "NOT_SOURCE_CERTIFIED_A_TO_E: " + dynamic_de.terminal_reason
            + "; E/F/G/H are not manufactured."
        )
        model_limitations = [
            domain.statement,
            "Stage 4.2 E->F and Stage 4.3 F->G are withheld from the public trajectory.",
            "Do not use this run for design decisions.",
            "HIGH_VELOCITY_PLAUSIBILITY_REVIEW_PENDING",
            "UNAVAILABLE_INCOMPLETE_CYCLE: daily metrics require a complete A→H cycle.",
        ]

    result = SimulationResult(
        metrics=metrics,
        points=points,
        projectName=inputs.projectName,
        projectistName=inputs.projectistName,
        createdAt=created_at,
        validationRows=[],
        physicalScope=physical_scope,
        terminalEvent=("F_FILM_VELOCITY_ZERO" if chain_certified else
                       "E_SLUG_BASE_REACHED_SURFACE" if dynamic_de.event_e_reached else
                       "GLV_CLOSE_BEFORE_E_SOURCE_BLOCK" if dynamic_de.glv_closure_time_s is not None else
                       dynamic_de.terminal_reason),
        caseId=inputs.caseId,
        referenceClassification=REFERENCE_CASES[inputs.caseId].classification,
        diagnostics=diagnostics,
        validationLevel=domain.validation_level,
        modelLimitations=model_limitations,
    )
    return result


def save_simulation_run(inputs: SimulationInputs) -> SimulationResult:
    """Run and persist a simulation in the configured database."""

    result = simulate(inputs)
    created_at = result.createdAt or datetime.now(timezone.utc).isoformat()
    simulation_id = persist_simulation(inputs, result, created_at)
    return result.model_copy(update={"simulationId": simulation_id})
