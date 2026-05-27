"""API schemas shared by the GLI endpoints."""

from typing import List, Optional

from pydantic import BaseModel, Field


class SimulationInputs(BaseModel):
    """Inputs received from the React frontend.

    Pressures are sent in MPa because that is easier to read in the UI.
    The domain model converts them to Pa before using the Santos formulas.
    """

    tubingDiameter: float = Field(gt=0.0)
    valveDepth: float = Field(gt=0.0)
    slugLength: float = Field(gt=0.0)
    surfaceTubingPressure: float = Field(gt=0.0)
    injectionPressure: float = Field(gt=0.0)
    api: float = Field(gt=0.0)
    bsw: float = Field(ge=0.0, le=100.0)
    gasRelativeDensity: float = Field(gt=0.0)
    casingPressureOpenRatio: float = Field(gt=0.0)
    projectName: str = Field(min_length=1, max_length=120)
    projectistName: str = Field(min_length=1, max_length=120)


class SimulationMetrics(BaseModel):
    """Main values shown by the frontend."""

    rhoL: float
    pTo: float
    pVo: float
    pBt: float
    duration: float


class SimulationPoint(BaseModel):
    """One point of the first preview time series."""

    t: float
    pressure: float
    force: float
    gasRate: float


class SimulationResult(BaseModel):
    """Response contract consumed by the React frontend."""

    metrics: SimulationMetrics
    points: List[SimulationPoint]
    simulationId: Optional[int] = None
    projectName: Optional[str] = None
    projectistName: Optional[str] = None
    createdAt: Optional[str] = None


class SimulationSummary(BaseModel):
    """Small record used to list previous simulations."""

    simulationId: int
    projectName: str
    projectistName: str
    createdAt: str
    pTo: float
    duration: float


class StoredSimulation(BaseModel):
    """Full persisted simulation record."""

    simulationId: int
    projectName: str
    projectistName: str
    createdAt: str
    inputs: SimulationInputs
    metrics: SimulationMetrics
    points: List[SimulationPoint]
