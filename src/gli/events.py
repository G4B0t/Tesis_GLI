"""Event functions that control transitions between GLI stages."""


EVENT_G_GAS_PRESSURE_BACK_TO_INITIAL = "G_GAS_PRESSURE_BACK_TO_INITIAL"
EVENT_G_MOMENTUM_EQUILIBRIUM = "G_MOMENTUM_EQUILIBRIUM"


def gas_lift_valve_opened(resultant_force_n: float, tolerance_n: float = 1.0e-6) -> bool:
    """Return True when the gas-lift valve opening condition is reached."""

    # Santos, p. 119: closed for negative resultant force, open for positive.
    return resultant_force_n >= -tolerance_n


def slug_top_reached_surface(slug_top_height_m: float, valve_depth_m: float) -> bool:
    """Return True when the top of the liquid slug reaches the surface."""

    return slug_top_height_m >= valve_depth_m


def slug_base_reached_surface(slug_base_height_m: float, valve_depth_m: float) -> bool:
    """Return True when the base of the liquid slug reaches the surface."""

    return slug_base_height_m >= valve_depth_m


def liquid_film_stopped(liquid_film_velocity_m_s: float, tolerance_m_s: float = 1.0e-6) -> bool:
    """Return True when the liquid film velocity is approximately zero."""

    return abs(liquid_film_velocity_m_s) <= tolerance_m_s


def gas_pressure_back_to_initial(
    current_pressure_pa: float,
    initial_pressure_pa: float,
    tolerance_pa: float = 100.0,
) -> bool:
    """Return True when decompression reaches the initial gas pressure."""

    return abs(current_pressure_pa - initial_pressure_pa) <= tolerance_pa


def gas_pressure_back_to_initial_residual(
    current_pressure_pa: float,
    initial_pressure_pa: float,
) -> float:
    """Legacy pressure-recovery diagnostic; not the current G event.

    The source-consistent terminal candidate used by the corrected route is
    :func:`stage_g_momentum_residual`. This residual is retained only to
    compare historical Milestone-1.5 behavior on the same trajectory.
    """

    return current_pressure_pa - initial_pressure_pa


def stage_g_momentum_residual(
    pressure_at_liquid_top_pa: float,
    surface_tubing_pressure_pa: float,
    mean_gas_density_kg_m3: float,
    gas_column_length_m: float,
    gravity_m_s2: float,
) -> float:
    """Zero-velocity residual implied by Santos 4.1.98-4.1.102."""

    return (
        float(pressure_at_liquid_top_pa)
        - float(surface_tubing_pressure_pa)
        - float(mean_gas_density_kg_m3) * float(gravity_m_s2) * float(gas_column_length_m)
    )
