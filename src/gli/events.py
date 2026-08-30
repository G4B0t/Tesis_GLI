"""Event functions that control transitions between GLI stages."""


EVENT_G_GAS_PRESSURE_BACK_TO_INITIAL = "G_GAS_PRESSURE_BACK_TO_INITIAL"


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
    """Signed Santos F->G event residual.

    Santos stage 4.3 ends when the gas pressure at the bottom of the well
    returns to its initial value.  A positive residual is expected throughout
    final decompression and the physical transition G is a descending
    zero-crossing.
    """

    return current_pressure_pa - initial_pressure_pa
