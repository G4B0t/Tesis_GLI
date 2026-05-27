"""Stage equations for the GLI conventional model.

The full Santos model is a staged dynamic system. We start by naming each
stage clearly and then fill the equations step by step.
"""

from typing import Dict

from .parameters import GLIParameters
from .valves import gas_lift_valve_resultant_force, motor_valve_gas_rate


def stage_1_rates(state: Dict[str, float], params: GLIParameters) -> Dict[str, float]:
    """Rates and control values for stage 1.

    Stage 1: gas injection into the annulus.
    - Surface motor valve: open.
    - Gas-lift valve: closed.
    - Stop condition: gas-lift valve opens.
    """

    gas_rate_surface = motor_valve_gas_rate(
        downstream_pressure_pa=state["p_c1"],
        upstream_pressure_pa=params.operating.injection_pressure_pa,
        gas_relative_density=params.fluids.gas_relative_density,
        gas_temperature_k=params.gas.temp_c1_k,
        cv=params.valves.motor_valve_cv,
    )

    resultant_force = gas_lift_valve_resultant_force(
        casing_pressure_at_valve_pa=state["p_c2"],
        bellows_pressure_pa=state["p_bt"],
        tubing_pressure_open_pa=state["p_to"],
        area_ratio_rv=params.valves.rv,
        bellows_area_m2=params.valves.bellows_area_m2,
    )

    return {
        "q_gs": gas_rate_surface,
        "resultant_force": resultant_force,
    }


def stage_2_rates(state: Dict[str, float], params: GLIParameters) -> Dict[str, float]:
    """Placeholder for stage 2 rates.

    Stage 2 will solve the coupled equations for annulus, gas bubble, liquid
    film and liquid slug. The equations are listed in docs/modelo_santos_notas.md.
    """

    raise NotImplementedError("Stage 2 dynamic equations are the next implementation step.")
