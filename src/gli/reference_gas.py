"""Liao/Santos reference injected-gas volume for intermittent gas lift."""

from .geometry import tubing_area
from .initial_conditions import initial_stage_1
from .parameters import GLIParameters


def liao_reference_gas_volume_std_m3(params: GLIParameters) -> float:
    """Return Vgref at the model standard state.

    Santos (1997, p.130) defines Vgref as the standard volume equivalent to
    the gas mass contained in the tubing at the mean of Pvo and the design
    tubing pressure Ptp.  For conventional IGL, Ptp=Pto.  The conversion uses
    the ideal/real-gas ratio between that mean state and the declared standard
    state.  The original Liao thesis is not publicly available in full; this
    implementation is therefore traced to Santos' explicit definition.
    """

    initial = initial_stage_1(params)
    gas = params.gas
    tubing_volume = tubing_area(params.geometry.tubing_diameter_m) * params.geometry.valve_depth_m
    mean_pressure = 0.5 * (initial["p_vo"] + initial["p_to"])
    mean_temperature = 0.5 * (gas.temp_t1_k + gas.temp_t3_k)
    return (
        mean_pressure
        * tubing_volume
        * gas.z_ts
        * gas.standard_temperature_k
        / (gas.standard_pressure_pa * gas.z_t1 * mean_temperature)
    )


def injected_gas_target_std_m3(params: GLIParameters) -> float:
    """Return Vgi=(Vgi/Vgref)*Vgref for the selected operating point."""

    ratio = params.operating.injected_over_reference_gas_volume
    if ratio is None or ratio <= 0.0:
        raise ValueError("A positive Vgi/Vgref ratio is required")
    return ratio * liao_reference_gas_volume_std_m3(params)
