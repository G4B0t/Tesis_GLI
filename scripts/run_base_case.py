"""Run a small base-case initialization check.

This script does not solve the full GLI cycle yet. It verifies that the
parameters and initial-condition formulas are connected correctly.
"""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from gli.parameters import (  # noqa: E402
    FluidProperties,
    GLIParameters,
    GasProperties,
    Geometry,
    ModelCoefficients,
    OperatingConditions,
    ValveParameters,
)
from gli.simulation import prepare_initial_cycle  # noqa: E402


def build_demo_parameters() -> GLIParameters:
    """Create temporary parameters until we load the Santos base case."""

    return GLIParameters(
        geometry=Geometry(
            tubing_diameter_m=0.0603,
            casing_inner_diameter_m=0.1397,
            annulus_cross_area_m2=0.0124,
            valve_depth_m=1800.0,
            initial_slug_length_m=90.0,
        ),
        fluids=FluidProperties(
            api=35.0,
            bsw_percent=20.0,
            gas_relative_density=0.65,
        ),
        gas=GasProperties(
            gas_molar_mass_kg_mol=0.029 * 0.65,
            temp_c1_k=300.0,
            temp_c2_k=330.0,
            temp_t1_k=330.0,
            temp_t3_k=300.0,
            temp_ts_k=300.0,
        ),
        valves=ValveParameters(
            bellows_area_m2=0.0005,
            port_area_m2=0.0001,
            rv=0.75,
        ),
        operating=OperatingConditions(
            surface_tubing_pressure_pa=1.5e6,
            injection_pressure_pa=8.0e6,
            pto_over_pvo=0.85,
            reservoir_liquid_rate_m3_s=2.0e-5,
        ),
        coefficients=ModelCoefficients(),
    )


def main() -> None:
    """Print initial values for stage 1 and stage 2."""

    params = build_demo_parameters()
    initial = prepare_initial_cycle(params)

    print("Stage 1 initial values")
    for key, value in initial["stage_1"].items():
        print(f"  {key}: {value:.6g}")

    print("\nStage 1 control")
    for key, value in initial["stage_1_control"].items():
        print(f"  {key}: {value:.6g}")

    print("\nStage 2 initial values")
    for key, value in initial["stage_2"].items():
        print(f"  {key}: {value:.6g}")


if __name__ == "__main__":
    main()
