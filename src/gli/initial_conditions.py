"""Initial conditions for the GLI conventional model.

The formulas in this file come from Santos, section 5.1.1.
They define the starting values for each simulation stage.
"""

from math import exp
from typing import Dict

from .fluids import gas_density_real, liquid_density
from .geometry import annulus_volume, gas_bubble_area, tubing_area
from .parameters import GLIParameters
from .valves import bubble_velocity, gas_lift_valve_bellows_pressure


GRAVITY_M_S2 = 9.80665


def tubing_pressure_at_valve_initial(
    surface_tubing_pressure_pa: float,
    liquid_density_kg_m3: float,
    gravity_m_s2: float,
    initial_slug_length_m: float,
) -> float:
    """Initial tubing pressure at the gas-lift valve depth.

    Santos, eq. 5.2:
    P_to = P_t3 + rho_l g L
    """

    return surface_tubing_pressure_pa + liquid_density_kg_m3 * gravity_m_s2 * initial_slug_length_m


def surface_tubing_pressure_from_static_gas_column(
    surface_pressure_pa: float,
    molar_mass_kg_mol: float,
    gravity_m_s2: float,
    valve_depth_m: float,
    z_factor: float,
    gas_constant_j_mol_k: float,
    temperature_k: float,
) -> float:
    """Pressure at the top of the liquid slug / tubing surface relation.

    Santos, eq. 5.3:
    P_t3 = P_ts exp(M g z_v / (Z R T))
    """

    exponent = molar_mass_kg_mol * gravity_m_s2 * valve_depth_m / (
        z_factor * gas_constant_j_mol_k * temperature_k
    )
    return surface_pressure_pa * exp(exponent)


def initial_stage_1(params: GLIParameters) -> Dict[str, float]:
    """Build initial values for stage 1.

    Stage 1 starts with the surface motor valve open and the gas-lift valve
    closed. It ends when the gas-lift valve opens.
    """

    geom = params.geometry
    gas = params.gas
    fluids = params.fluids
    valves = params.valves
    operating = params.operating

    rho_l = liquid_density(
        bsw_percent=fluids.bsw_percent,
        api=fluids.api,
        water_relative_density=fluids.water_relative_density,
        water_density_kg_m3=fluids.water_density_kg_m3,
    )

    # Santos, eq. 5.3.
    p_t3 = surface_tubing_pressure_from_static_gas_column(
        surface_pressure_pa=operating.surface_tubing_pressure_pa,
        molar_mass_kg_mol=gas.gas_molar_mass_kg_mol,
        gravity_m_s2=GRAVITY_M_S2,
        valve_depth_m=geom.valve_depth_m,
        z_factor=gas.z_t3,
        gas_constant_j_mol_k=gas.gas_constant_j_mol_k,
        temperature_k=gas.temp_t3_k,
    )

    # Santos, eq. 5.2.
    p_to = tubing_pressure_at_valve_initial(
        surface_tubing_pressure_pa=p_t3,
        liquid_density_kg_m3=rho_l,
        gravity_m_s2=GRAVITY_M_S2,
        initial_slug_length_m=geom.initial_slug_length_m,
    )

    # P_to / P_vo is an input of the simulator.
    p_vo = p_to / operating.pto_over_pvo

    # Santos, eq. 5.1.
    p_bt = gas_lift_valve_bellows_pressure(
        tubing_pressure_open_pa=p_to,
        casing_pressure_open_pa=p_vo,
        area_ratio_rv=valves.rv,
    )

    # Initial P_c2 is equal to the gas-lift valve dome/bellows pressure.
    p_c2 = p_bt

    # Santos, eq. 5.7.
    p_c1 = p_c2 / exp(
        gas.gas_molar_mass_kg_mol
        * GRAVITY_M_S2
        * geom.valve_depth_m
        / (gas.z_tc * gas.gas_constant_j_mol_k * gas.temp_c1_k)
    )

    # Santos, eqs. 5.8 and 5.9.
    rho_c2 = gas_density_real(
        p_c2,
        gas.gas_molar_mass_kg_mol,
        gas.z_c2,
        gas.gas_constant_j_mol_k,
        gas.temp_c2_k,
    )
    rho_c1 = gas_density_real(
        p_c1,
        gas.gas_molar_mass_kg_mol,
        gas.z_c1,
        gas.gas_constant_j_mol_k,
        gas.temp_c1_k,
    )

    # Santos, eqs. 5.10 to 5.12.
    p_tc = 0.5 * (p_c1 + p_c2)
    t_tc = 0.5 * (gas.temp_c1_k + gas.temp_c2_k)
    v_tc = annulus_volume(geom.annulus_cross_area_m2, geom.valve_depth_m)
    m_tc = p_tc * gas.gas_molar_mass_kg_mol * v_tc / (
        gas.z_tc * gas.gas_constant_j_mol_k * t_tc
    )

    return {
        "rho_l": rho_l,
        "p_t3": p_t3,
        "p_to": p_to,
        "p_vo": p_vo,
        "p_bt": p_bt,
        "p_c1": p_c1,
        "p_c2": p_c2,
        "rho_c1": rho_c1,
        "rho_c2": rho_c2,
        "m_tc": m_tc,
    }


def initial_stage_2(params: GLIParameters, final_stage_1: Dict[str, float]) -> Dict[str, float]:
    """Build initial values for stage 2 from the final state of stage 1."""

    geom = params.geometry
    gas = params.gas
    coeffs = params.coefficients

    tubing_diameter = geom.tubing_diameter_m
    liquid_film_thickness = 0.01 * tubing_diameter
    area_tubing = tubing_area(tubing_diameter)
    area_bubble = gas_bubble_area(tubing_diameter, liquid_film_thickness)

    # Santos: h_B = 5 percent of the initial liquid slug length.
    h_b = 0.05 * geom.initial_slug_length_m

    # Santos, eq. 5.14.
    h_l = (1.0 + 0.05 * area_bubble / area_tubing) * geom.initial_slug_length_m

    # Santos: initial P_t1 and P_t2 are taken as P_to.
    p_t1 = final_stage_1["p_to"]
    p_t2 = final_stage_1["p_to"]

    # Santos, eq. 5.15.
    rho_b = gas_density_real(
        p_t1,
        gas.gas_molar_mass_kg_mol,
        gas.z_t1,
        gas.gas_constant_j_mol_k,
        gas.temp_t1_k,
    )

    # Santos adopts this initial liquid slug velocity.
    v_l = 0.0152

    # Santos, eqs. 4.1.49 and 4.1.51.
    v_b = bubble_velocity(v_l, coeffs.bubble_velocity_a, tubing_diameter)

    return {
        "p_c1": final_stage_1["p_c1"],
        "p_c2": final_stage_1["p_c2"],
        "rho_c1": final_stage_1["rho_c1"],
        "rho_c2": final_stage_1["rho_c2"],
        "m_tc": final_stage_1["m_tc"],
        "h_b": h_b,
        "h_l": h_l,
        "p_t1": p_t1,
        "p_t2": p_t2,
        "rho_b": rho_b,
        "v_l": v_l,
        "v_b": v_b,
        "y": liquid_film_thickness,
    }
