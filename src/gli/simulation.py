"""High-level simulation workflow."""

from .events import gas_lift_valve_opened
from .initial_conditions import initial_stage_1, initial_stage_2
from .parameters import GLIParameters
from .stages import stage_1_rates


def prepare_initial_cycle(params: GLIParameters) -> dict:
    """Calculate initial stage values used to start one GLI cycle."""

    stage_1 = initial_stage_1(params)
    stage_1_control = stage_1_rates(stage_1, params)
    stage_2 = initial_stage_2(params, stage_1)

    return {
        "stage_1": stage_1,
        "stage_1_control": stage_1_control,
        "stage_1_valve_open": gas_lift_valve_opened(stage_1_control["resultant_force"]),
        "stage_2": stage_2,
    }
