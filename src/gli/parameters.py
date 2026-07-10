"""Project parameters for the GLI conventional model.

Values are grouped by topic to keep formulas readable. Domain values use SI;
pressures are absolute unless a name explicitly says otherwise.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Geometry:
    """Well geometry used by the GLI model."""

    tubing_diameter_m: float
    casing_inner_diameter_m: float
    annulus_cross_area_m2: float
    valve_depth_m: float
    initial_slug_length_m: float
    tubing_outer_diameter_m: float | None = None
    casing_outer_diameter_m: float | None = None
    perforation_depth_m: float | None = None
    static_liquid_height_m: float | None = None


@dataclass(frozen=True)
class FluidProperties:
    """Fluid and gas properties used in initial conditions."""

    api: float
    bsw_percent: float
    gas_relative_density: float
    water_relative_density: float = 1.07
    water_density_kg_m3: float = 1000.0
    liquid_viscosity_pa_s: float = 0.003


@dataclass(frozen=True)
class GasProperties:
    """Gas equation-of-state parameters."""

    gas_molar_mass_kg_mol: float
    gas_constant_j_mol_k: float = 8.314462618
    z_c1: float = 1.0
    z_c2: float = 1.0
    z_t1: float = 1.0
    z_t3: float = 1.0
    z_ts: float = 1.0
    z_tc: float = 1.0
    temp_c1_k: float = 300.0
    temp_c2_k: float = 320.0
    temp_t1_k: float = 320.0
    temp_t3_k: float = 300.0
    temp_ts_k: float = 300.0
    standard_pressure_pa: float = 101_325.0
    standard_temperature_k: float = 288.15


@dataclass(frozen=True)
class ValveParameters:
    """Valve and control parameters."""

    bellows_area_m2: float
    port_area_m2: float
    rv: float
    motor_valve_cv: float = 8.5
    gas_lift_cd: float = 0.865
    adiabatic_constant: float = 1.28


@dataclass(frozen=True)
class OperatingConditions:
    """Operating inputs for the simulator."""

    surface_tubing_pressure_pa: float
    injection_pressure_pa: float
    pto_over_pvo: float
    reservoir_liquid_rate_m3_s: float
    initial_slug_over_static_height: float | None = None
    injected_over_reference_gas_volume: float | None = None
    reservoir_static_pressure_pa: float | None = None


@dataclass(frozen=True)
class ModelCoefficients:
    """Empirical coefficients used by Santos."""

    bubble_velocity_a: float = 1.025
    surface_loss_k: float = 0.6
    gas_friction_factor: float = 0.02
    liquid_friction_factor: float = 0.02


@dataclass(frozen=True)
class GLIParameters:
    """All parameters needed by the GLI conventional model."""

    geometry: Geometry
    fluids: FluidProperties
    gas: GasProperties
    valves: ValveParameters
    operating: OperatingConditions
    coefficients: ModelCoefficients
