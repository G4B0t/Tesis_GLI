"""Performance metrics for GLI simulation results."""


def gas_liquid_ratio(gas_volume_m3: float, liquid_volume_m3: float) -> float:
    """Gas volume consumed per liquid volume produced."""

    if liquid_volume_m3 == 0:
        return float("inf")
    return gas_volume_m3 / liquid_volume_m3


def percent_error(reference: float, simulated: float) -> float:
    """Simple percent error."""

    if reference == 0:
        return 0.0
    return 100.0 * (simulated - reference) / reference
