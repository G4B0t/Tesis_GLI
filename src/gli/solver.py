"""Simple numerical solvers for model development."""

from typing import Callable, List


Vector = List[float]
DerivativeFunction = Callable[[float, Vector], Vector]


def rk4_step(derivatives: DerivativeFunction, t: float, y: Vector, dt: float) -> Vector:
    """One fourth-order Runge-Kutta step."""

    k1 = derivatives(t, y)
    k2 = derivatives(t + 0.5 * dt, _add_scaled(y, k1, 0.5 * dt))
    k3 = derivatives(t + 0.5 * dt, _add_scaled(y, k2, 0.5 * dt))
    k4 = derivatives(t + dt, _add_scaled(y, k3, dt))

    return [
        y_i + dt * (k1_i + 2.0 * k2_i + 2.0 * k3_i + k4_i) / 6.0
        for y_i, k1_i, k2_i, k3_i, k4_i in zip(y, k1, k2, k3, k4)
    ]


def _add_scaled(y: Vector, dy: Vector, scale: float) -> Vector:
    """Return y + scale * dy."""

    return [y_i + scale * dy_i for y_i, dy_i in zip(y, dy)]
