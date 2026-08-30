"""Reproducible Santos conventional-GLI base case {50, 70, 80}.

Santos defines the operating point as percentages
{L/H, P_to/P_vo, V_gi/V_gr}.  Therefore {50, 70, 80} means 0.50, 0.70
and 0.80 respectively; it is not the BSW/compressor/temperature triplet.
"""

from math import pi

from .fluids import liquid_density
from .geometry import annulus_area
from .parameters import (
    FluidProperties,
    GasProperties,
    Geometry,
    GLIParameters,
    ModelCoefficients,
    OperatingConditions,
    ValveParameters,
)
from .units import fahrenheit_to_kelvin, inch_to_m, kgf_cm2_gauge_to_pa_absolute
from .reservoir import productivity_index_m3_day_kgf_cm2_to_si

GRAVITY_M_S2 = 9.80665
SECONDS_PER_DAY = 86_400.0


def static_liquid_height(
    reservoir_pressure_pa: float,
    wellhead_pressure_pa: float,
    liquid_density_kg_m3: float,
    maximum_height_m: float,
) -> float:
    """Hydrostatic liquid height H, capped by perforation depth."""

    height = (reservoir_pressure_pa - wellhead_pressure_pa) / (
        liquid_density_kg_m3 * GRAVITY_M_S2
    )
    return min(maximum_height_m, max(0.0, height))


def santos_50_70_80() -> GLIParameters:
    """Build the documented SI parameter set for Santos {50,70,80}."""

    fluids = FluidProperties(
        api=40.0,
        bsw_percent=50.0,
        gas_relative_density=0.70,
        water_relative_density=1.07,
        water_density_kg_m3=1000.0,
    )
    rho_l = liquid_density(
        bsw_percent=fluids.bsw_percent,
        api=fluids.api,
        water_relative_density=fluids.water_relative_density,
        water_density_kg_m3=fluids.water_density_kg_m3,
    )
    p_surface = kgf_cm2_gauge_to_pa_absolute(7.0)
    p_reservoir = kgf_cm2_gauge_to_pa_absolute(85.2)
    perforation_depth_m = 1500.0
    height_m = static_liquid_height(
        p_reservoir, p_surface, rho_l, perforation_depth_m
    )

    # Declared geometry assumptions (not specified completely in Santos 5.5):
    # 5.5-in, 15.5-lb/ft casing -> 4.950-in nominal ID; 2 3/8-in
    # production string -> 2.375-in OD and assumed 1.995-in ID (4.7-lb/ft).
    casing_id_m = inch_to_m(4.950)
    tubing_od_m = inch_to_m(2.375)
    tubing_id_m = inch_to_m(1.995)
    annulus_m2 = annulus_area(casing_id_m, tubing_od_m)

    temperature_k = fahrenheit_to_kelvin(80.0)
    gas = GasProperties(
        gas_molar_mass_kg_mol=0.029 * fluids.gas_relative_density,
        temp_c1_k=temperature_k,
        temp_c2_k=temperature_k,
        temp_t1_k=temperature_k,
        temp_t3_k=temperature_k,
        temp_ts_k=temperature_k,
    )

    valve_od_m = inch_to_m(1.5)
    return GLIParameters(
        geometry=Geometry(
            tubing_diameter_m=tubing_id_m,
            tubing_outer_diameter_m=tubing_od_m,
            casing_inner_diameter_m=casing_id_m,
            casing_outer_diameter_m=inch_to_m(5.5),
            annulus_cross_area_m2=annulus_m2,
            valve_depth_m=1480.0,
            perforation_depth_m=perforation_depth_m,
            static_liquid_height_m=height_m,
            initial_slug_length_m=0.50 * height_m,
        ),
        fluids=fluids,
        gas=gas,
        valves=ValveParameters(
            # Proxies declared for initialization only. Santos table 5.5 does
            # not report bellows/port dimensions or R_v.
            bellows_area_m2=pi * valve_od_m**2 / 4.0,
            # Santos et al. (2001) case example: 1/2-in gas-lift valve seat.
            port_area_m2=pi * inch_to_m(0.5) ** 2 / 4.0,
            # Provisional effective area ratio, consistent with the A-level
            # of Santos Fig. 5.1; the valve datasheet is still required.
            rv=0.30,
        ),
        operating=OperatingConditions(
            surface_tubing_pressure_pa=p_surface,
            injection_pressure_pa=kgf_cm2_gauge_to_pa_absolute(70.0),
            pto_over_pvo=0.70,
            reservoir_liquid_rate_m3_s=(85.2 - 7.0) / SECONDS_PER_DAY,
            initial_slug_over_static_height=0.50,
            injected_over_reference_gas_volume=0.80,
            reservoir_static_pressure_pa=p_reservoir,
            productivity_index_m3_s_pa=productivity_index_m3_day_kgf_cm2_to_si(1.0),
        ),
        coefficients=ModelCoefficients(),
    )
