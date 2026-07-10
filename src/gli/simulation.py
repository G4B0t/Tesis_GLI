"""High-level simulation workflow."""

from .events import gas_lift_valve_opened
from .initial_conditions import initial_stage_1
from .parameters import GLIParameters
from .stages import stage_1_rates
from .stage1_dynamic import simulate_stage_1


def prepare_initial_cycle(params: GLIParameters) -> dict:
    """Calculate initial stage values used to start one GLI cycle."""

    stage_1 = initial_stage_1(params)
    stage_1_control = stage_1_rates(stage_1, params)
    return {
        "stage_1": stage_1,
        "stage_1_control": stage_1_control,
        "stage_1_valve_open": gas_lift_valve_opened(stage_1_control["resultant_force"]),
    }


def run_stage_1(params: GLIParameters, **solver_options):
    """Run the dynamic injection stage A->B with event detection."""
    return simulate_stage_1(params, **solver_options)
