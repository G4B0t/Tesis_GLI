"""Fluid property calculations used by the GLI simulator."""


def oil_relative_density_from_api(api: float) -> float:
    """Oil relative density from API gravity.

    Santos, eq. 5.6:
    d_o = 141.5 / (131.5 + API)
    """

    return 141.5 / (131.5 + api)


def liquid_relative_density(
    bsw_percent: float,
    water_relative_density: float,
    oil_relative_density: float,
) -> float:
    """Liquid relative density from water cut and oil density.

    Santos, eq. 5.5:
    d_l = (BSW/100) d_w + (1 - BSW/100) d_o
    """

    water_fraction = bsw_percent / 100.0
    return water_fraction * water_relative_density + (1.0 - water_fraction) * oil_relative_density


def liquid_density(
    bsw_percent: float,
    api: float,
    water_relative_density: float = 1.07,
    water_density_kg_m3: float = 1000.0,
) -> float:
    """Liquid density in kg/m3.

    Santos, eq. 5.4:
    rho_l = d_l rho_w
    """

    oil_density = oil_relative_density_from_api(api)
    density_relative = liquid_relative_density(
        bsw_percent,
        water_relative_density,
        oil_density,
    )
    return density_relative * water_density_kg_m3


def gas_density_real(
    pressure_pa: float,
    molar_mass_kg_mol: float,
    z_factor: float,
    gas_constant_j_mol_k: float,
    temperature_k: float,
) -> float:
    """Gas density from real gas equation of state.

    Form used throughout Santos:
    rho = P M / (Z R T)
    """

    return pressure_pa * molar_mass_kg_mol / (
        z_factor * gas_constant_j_mol_k * temperature_k
    )
