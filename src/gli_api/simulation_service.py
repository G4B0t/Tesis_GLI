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

from .database import save_simulation as persist_simulation
from .schemas import (
    SimulationInputs,
    SimulationMetrics,
    SimulationPoint,
    SimulationResult,
    SimulationValidationRow,
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
            injected_over_reference_gas_volume=inputs.injectedGasReferenceRatio,
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
    """Run the corrected A->F chain for the fully specified Santos case."""

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
    dynamic_ef = simulate_stage_e_to_f(params, stage_d_e=dynamic_de, rhs_mode="santos_corrected")
    chain_certified = (
        dynamic_bc_common.certified
        and dynamic_cd_common.certified
        and dynamic_de.event_e_reached
        and dynamic_de.gas_balance_relative_error <= 1e-8
        and dynamic_de.liquid_balance_relative_error <= 1e-8
        and not bool(dynamic_de.valve_open.any())
        and dynamic_ef.corrected_certified
        and dynamic_ef.gas_balance_relative_error <= 1e-8
        and dynamic_ef.liquid_balance_relative_error <= 1e-8
        and not bool(dynamic_ef.valve_open.any())
    )
    points = [
        SimulationPoint(
            t=float(t), pressure=float(p * PA_TO_MPA),
            force=float(force), gasRate=float(rate), stage="A_B",
            annulusPressure=float(p * PA_TO_MPA),
        )
        for t, p, force, rate in zip(
            dynamic.time_s, dynamic.p_c1_pa,
            dynamic.resultant_force_n, dynamic.standard_gas_rate_m3_s,
        )
    ]
    for t,p1,p2,pb,rate,h_l,h_b,film in zip(
        dynamic_bc.time_s[1:],dynamic_bc.p_c1_pa[1:],dynamic_bc.p_c2_pa[1:],
        dynamic_bc.p_bubble_pa[1:],dynamic_bc.motor_rate_std_m3_s[1:],
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
        ))
    offset_c=dynamic.opening_time_s+dynamic_bc.event_c_time_s
    for t,p1,p2,pt,pwf,h_l,h_b,v_l,v_b,film,film_v,fb,force,is_open in zip(
        dynamic_cd.time_s[1:],dynamic_cd.p_c1_pa[1:],dynamic_cd.p_c2_pa[1:],
        dynamic_cd.p_tubing_pa[1:],dynamic_cd.p_bottom_pa[1:],dynamic_cd.h_l_m[1:],
        dynamic_cd.h_b_m[1:],dynamic_cd.v_l_m_s[1:],dynamic_cd.v_b_m_s[1:],
        dynamic_cd.film_thickness_m[1:],dynamic_cd.film_volume_m3[1:],dynamic_cd.fallback_volume_m3[1:],
        dynamic_cd.valve_force_n[1:],dynamic_cd.valve_open[1:]
    ):
        points.append(SimulationPoint(
            t=float(offset_c+t),pressure=float(p1*PA_TO_MPA),force=float(force),
            gasRate=0.0,stage="C_D",annulusPressure=float(p1*PA_TO_MPA),
            bubblePressure=float(pt*PA_TO_MPA),bottomPressure=float(pwf*PA_TO_MPA),
            slugTop=float(h_l),slugBase=float(h_b),filmThickness=float(film),
            slugVelocity=float(v_l),bubbleVelocity=float(v_b),filmVolume=float(film_v),fallbackVolume=float(fb),
            gasLiftValveOpen=bool(is_open),
        ))
    offset_d=offset_c+dynamic_cd.event_d_time_s
    for t,p1,pt,pwf,h_l,h_b,v_l,v_b,film,fb,slug,q,vp,force,is_open in zip(
        dynamic_de.time_s[1:],dynamic_de.p_c1_pa[1:],dynamic_de.p_tubing_pa[1:],
        dynamic_de.p_bottom_pa[1:],dynamic_de.h_l_m[1:],dynamic_de.h_b_m[1:],
        dynamic_de.v_l_m_s[1:],dynamic_de.v_b_m_s[1:],dynamic_de.film_volume_m3[1:],
        dynamic_de.fallback_volume_m3[1:],dynamic_de.slug_volume_m3[1:],
        dynamic_de.liquid_rate_m3_s[1:],dynamic_de.produced_volume_m3[1:],
        dynamic_de.valve_force_n[1:],dynamic_de.valve_open[1:]):
        points.append(SimulationPoint(t=float(offset_d+t),pressure=float(p1*PA_TO_MPA),
            force=float(force),gasRate=0.0,stage="D_E",annulusPressure=float(p1*PA_TO_MPA),
            bubblePressure=float(pt*PA_TO_MPA),bottomPressure=float(pwf*PA_TO_MPA),
            slugTop=float(h_l),slugBase=float(h_b),slugVelocity=float(v_l),bubbleVelocity=float(v_b),
            filmVolume=float(film),fallbackVolume=float(fb),slugVolume=float(slug),
            liquidRate=float(q),producedVolume=float(vp),gasLiftValveOpen=bool(is_open)))
    offset_e=offset_d+dynamic_de.event_e_time_s
    annulus_e=float(dynamic_de.p_c1_pa[-1]*PA_TO_MPA)
    for t,pt,vg,vf,y,film,fb,prod,mdot,is_open in zip(
        dynamic_ef.time_s[1:],dynamic_ef.tubing_pressure_pa[1:],
        dynamic_ef.gas_velocity_m_s[1:],dynamic_ef.film_velocity_m_s[1:],
        dynamic_ef.film_thickness_m[1:],dynamic_ef.film_volume_m3[1:],
        dynamic_ef.fallback_volume_m3[1:],dynamic_ef.produced_film_volume_m3[1:],
        dynamic_ef.surface_gas_rate_kg_s[1:],dynamic_ef.valve_open[1:]):
        points.append(SimulationPoint(
            t=float(offset_e+t),pressure=float(pt*PA_TO_MPA),force=0.0,
            gasRate=float(mdot),stage="E_F",annulusPressure=annulus_e,
            bubblePressure=float(pt*PA_TO_MPA),filmThickness=float(y),
            bubbleVelocity=float(vg),slugVelocity=float(vf),filmVolume=float(film),
            fallbackVolume=float(fb),producedVolume=float(prod),liquidRate=0.0,
            gasLiftValveOpen=bool(is_open)))

    created_at = datetime.now(timezone.utc).isoformat()
    metrics = SimulationMetrics(
            rhoL=stage_1["rho_l"],
            pTo=stage_1["p_to"] * PA_TO_MPA,
            pVo=stage_1["p_vo"] * PA_TO_MPA,
            pBt=stage_1["p_bt"] * PA_TO_MPA,
            duration=dynamic.opening_time_s+dynamic_bc.event_c_time_s+dynamic_cd.event_d_time_s+dynamic_de.event_e_time_s+dynamic_ef.event_f_time_s,
            vgRef=liao_reference_gas_volume_std_m3(params),
            vgiTarget=injected_gas_target_std_m3(params),
        )

    domain = classify_design_domain(inputs, chain_certified=chain_certified)
    if domain.validation_level == "certified":
        physical_scope = ("A_TO_F certified: B_TO_C santos_compatible, C_TO_D santos_corrected, "
                          "D_TO_E santos_corrected and E_TO_F santos_corrected are connected with "
                          "identity state transfer, accumulated ledgers and independent gas/liquid balances.")
        model_limitations = [
            "Certified only for the exact Santos frontend/API reference input set.",
            "Liao Table 5.14 remains a partial benchmark, not a quantitative validation target for this case.",
            "E_TO_F entrainment remains represented by the audited Santos no-mass-exchange stage-4 closure in this implementation.",
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
        physical_scope = "A_TO_F failed: corrected chain connected, but at least one certification gate remains open."
        model_limitations = [
            domain.statement,
            "Do not use this run for design decisions.",
        ]

    result = SimulationResult(
        metrics=metrics,
        points=points,
        projectName=inputs.projectName,
        projectistName=inputs.projectistName,
        createdAt=created_at,
        validationRows=[],
        physicalScope=physical_scope,
        terminalEvent="F_FILM_VELOCITY_ZERO" if chain_certified else "E_SLUG_BASE_REACHED_SURFACE",
        caseId=inputs.caseId,
        referenceClassification=REFERENCE_CASES[inputs.caseId].classification,
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
