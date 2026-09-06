"""Valve flow and control equations for GLI."""

from math import sqrt

from .parameters import GLIParameters


def santos_standard_gas_density(params: GLIParameters) -> float:
    """Gas density at the declared standard state for Santos 4.1.14/.15."""
    gas = params.gas
    return (
        gas.standard_pressure_pa
        * gas.gas_molar_mass_kg_mol
        / (gas.gas_constant_j_mol_k * gas.standard_temperature_k)
    )


def santos_glv_mass_rate(
    casing_pressure_pa: float,
    tubing_pressure_pa: float,
    params: GLIParameters,
) -> float:
    """Santos 4.1.13/.15 GLV mass flow, kg/s.

    Equation 4.1.13 supplies the subcritical nozzle expression.  Below its
    stationary critical pressure ratio the value is held at that maximum,
    which is the physically continuous critical-flow extension of the same
    expression.  The calculation is central so B->C, C->D and D->E cannot
    switch GLV correlations at a stage boundary.
    """
    if casing_pressure_pa <= tubing_pressure_pa:
        return 0.0
    k = params.valves.adiabatic_constant
    if k <= 1.0:
        raise ValueError("Santos GLV adiabatic constant must exceed one")
    ratio = tubing_pressure_pa / casing_pressure_pa
    critical_ratio = (2.0 / (k + 1.0)) ** (k / (k - 1.0))
    effective_ratio = max(ratio, critical_ratio)
    flow_term = (
        2.0
        * k
        / (k - 1.0)
        * (effective_ratio ** (2.0 / k) - effective_ratio ** ((k + 1.0) / k))
    )
    volumetric_rate = (
        0.04842
        * params.valves.gas_lift_cd
        * params.valves.port_area_m2
        * casing_pressure_pa
        / sqrt(params.fluids.gas_relative_density * params.gas.temp_c2_k)
        * sqrt(max(flow_term, 0.0))
    )
    return volumetric_rate * santos_standard_gas_density(params)


def gas_lift_valve_bellows_pressure(
    tubing_pressure_open_pa: float,
    casing_pressure_open_pa: float,
    area_ratio_rv: float,
) -> float:
    """Pressure in the gas-lift valve dome/bellows.

    Santos, eq. 5.1:
    P_bt = P_vo (1 - R_v) + P_to R_v
    """

    return (
        casing_pressure_open_pa * (1.0 - area_ratio_rv)
        + tubing_pressure_open_pa * area_ratio_rv
    )


def gas_lift_valve_resultant_force(
    casing_pressure_at_valve_pa: float,
    bellows_pressure_pa: float,
    tubing_pressure_open_pa: float,
    area_ratio_rv: float,
    bellows_area_m2: float,
) -> float:
    """Resultant force used to decide if the gas-lift valve opens.

    Santos, eq. 5.13:
    rF = [(P_c2 - P_bt) - (P_c2 - P_to) R_v] A_b

    In the text, the valve opens when this value reaches zero.
    """

    return (
        (casing_pressure_at_valve_pa - bellows_pressure_pa)
        - (casing_pressure_at_valve_pa - tubing_pressure_open_pa) * area_ratio_rv
    ) * bellows_area_m2


def motor_valve_gas_rate(
    downstream_pressure_pa: float,
    upstream_pressure_pa: float,
    gas_relative_density: float,
    gas_temperature_k: float,
    cv: float,
    critical_pressure_ratio: float = 0.5,
) -> float:
    """Standard gas rate through the surface motor valve/choke.

    Santos, eq. 4.1.10: q_gi = 1.5136e-6 Cv P_gi /
    sqrt(d_g T) * sqrt(r-r^2). Pressures are Pa(a), temperature is K,
    and the result is standard m3/s. Below the critical ratio, ``r`` is
    clamped so choked flow does not decrease unphysically.
    """

    pressure_ratio = downstream_pressure_pa / upstream_pressure_pa
    if pressure_ratio >= 1.0:
        return 0.0
    effective_ratio = max(pressure_ratio, critical_pressure_ratio)
    pressure_term = effective_ratio - effective_ratio**2
    return (
        1.5136e-6
        * cv
        * upstream_pressure_pa
        / sqrt(gas_relative_density * gas_temperature_k)
        * sqrt(pressure_term)
    )


def bubble_velocity(
    liquid_slug_velocity_m_s: float, coefficient_a: float, tubing_diameter_m: float
) -> float:
    """Gas bubble velocity from the liquid slug velocity.

    Santos, eqs. 4.1.49 and 4.1.51:
    v_B = a v_l + b
    b = 0.35 sqrt(gD)
    """

    gravity_m_s2 = 9.80665
    b = 0.35 * sqrt(gravity_m_s2 * tubing_diameter_m)
    return coefficient_a * liquid_slug_velocity_m_s + b
