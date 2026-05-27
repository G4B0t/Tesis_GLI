"""Common equations shared by GLI stages."""


def average_pressure(pressure_a_pa: float, pressure_b_pa: float) -> float:
    """Arithmetic average pressure."""

    return 0.5 * (pressure_a_pa + pressure_b_pa)


def average_temperature(temperature_a_k: float, temperature_b_k: float) -> float:
    """Arithmetic average temperature."""

    return 0.5 * (temperature_a_k + temperature_b_k)


def ensure_non_negative(value: float) -> float:
    """Avoid small negative values caused by numerical roundoff."""

    return max(value, 0.0)
