"""Valve flow and control equations for GLI."""

from math import sqrt


def gas_lift_valve_bellows_pressure(
    tubing_pressure_open_pa: float,
    casing_pressure_open_pa: float,
    area_ratio_rv: float,
) -> float:
    """Pressure in the gas-lift valve dome/bellows.

    Santos, eq. 5.1:
    P_bt = P_vo (1 - R_v) + P_to R_v
    """

    return casing_pressure_open_pa * (1.0 - area_ratio_rv) + tubing_pressure_open_pa * area_ratio_rv


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
) -> float:
    """Gas rate through the surface motor valve.

    Santos, eq. 4.1.12. This is kept in the original empirical form.
    Units depend on the equation constants used by Santos.
    """

    pressure_ratio = downstream_pressure_pa / upstream_pressure_pa
    pressure_term = downstream_pressure_pa / upstream_pressure_pa - pressure_ratio**2
    if pressure_term <= 0:
        return 0.0
    return (
        1.5136e-6
        * cv
        * upstream_pressure_pa
        / sqrt(gas_relative_density * gas_temperature_k)
        * sqrt(pressure_term)
    )


def bubble_velocity(liquid_slug_velocity_m_s: float, coefficient_a: float, tubing_diameter_m: float) -> float:
    """Gas bubble velocity from the liquid slug velocity.

    Santos, eqs. 4.1.49 and 4.1.51:
    v_B = a v_l + b
    b = 0.35 sqrt(gD)
    """

    gravity_m_s2 = 9.80665
    b = 0.35 * sqrt(gravity_m_s2 * tubing_diameter_m)
    return coefficient_a * liquid_slug_velocity_m_s + b
