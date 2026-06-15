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
    wellDepth: float = Field(gt=0.0, default=1500.0)
    staticReservoirPressure: float = Field(gt=0.0, default=85.2)
    productivityIndex: float = Field(gt=0.0, default=1.0)
    waterRelativeDensity: float = Field(gt=0.0, default=1.07)
    rgl: float = Field(ge=0.0, default=0.0)
    surfaceTemperature: float = Field(gt=0.0, default=80.0)


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


class SimulationValidationRow(BaseModel):
    """Calculated comparison row for Santos table 5.14."""

    parameter: str
    liao: str
    reference: str
    simulator: str


class SimulationResult(BaseModel):
    """Response contract consumed by the React frontend."""

    metrics: SimulationMetrics
    points: List[SimulationPoint]
    simulationId: Optional[int] = None
    projectName: Optional[str] = None
    projectistName: Optional[str] = None
    createdAt: Optional[str] = None
    validationRows: List[SimulationValidationRow] = Field(default_factory=list)


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


class ReferencePoint(BaseModel):
    """One digitized reference point used in Santos validation charts."""

    x: float
    y: float


class ReferenceSeries(BaseModel):
    """One plotted variable in a Santos reference figure."""

    key: str
    label: str
    unit: str
    color: str
    points: List[ReferencePoint]


class ReferenceFigure(BaseModel):
    """Digitized figure from Santos used as validation target."""

    id: str
    title: str
    xLabel: str
    yLabel: str
    note: str
    series: List[ReferenceSeries]


class ReferenceTable(BaseModel):
    """Tabular reference data from Santos."""

    id: str
    title: str
    columns: List[str]
    rows: List[List[str]]


class ValidationReference(BaseModel):
    """Reference package shown by the frontend validation panel."""

    title: str
    subtitle: str
    source: str
    figures: List[ReferenceFigure]
    tables: List[ReferenceTable]
