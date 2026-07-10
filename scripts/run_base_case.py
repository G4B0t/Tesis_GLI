"""Run a small base-case initialization check.

This script does not solve the full GLI cycle yet. It verifies that the
parameters and initial-condition formulas are connected correctly.
"""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from gli.base_case import santos_50_70_80  # noqa: E402
from gli.simulation import prepare_initial_cycle  # noqa: E402


def main() -> None:
    """Print the block-1 parameter set and stage-1 initial conditions."""

    params = santos_50_70_80()
    initial = prepare_initial_cycle(params)

    print("Stage 1 initial values")
    for key, value in initial["stage_1"].items():
        print(f"  {key}: {value:.6g}")

    print("\nStage 1 control")
    for key, value in initial["stage_1_control"].items():
        print(f"  {key}: {value:.6g}")



if __name__ == "__main__":
    main()
