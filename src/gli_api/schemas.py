"""API schemas shared by the GLI endpoints."""

from typing import List, Optional, Literal

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
    injectedGasReferenceRatio: float = Field(gt=0.0, default=0.8)
    caseId: str = Field(default="santos-gli-50-70-80")
    tubingRoughness: float = Field(gt=0.0, default=4.5e-5, description="m; explicit extension input")
    roughnessSource: str = Field(default="bibliographic range; replace with measured pipe data")
    glvMode: Literal["mechanical", "calibrated_threshold"] = "calibrated_threshold"
    glvOpeningPressure: Optional[float] = Field(default=None, description="MPa differential")
    glvClosingPressure: Optional[float] = Field(default=None, description="MPa differential")
    glvParameterSource: str = Field(default="calibrated; case-specific provenance required")


class SimulationMetrics(BaseModel):
    """Main values shown by the frontend."""

    rhoL: float
    pTo: float
    pVo: float
    pBt: float
    duration: float
    vgRef: Optional[float] = None
    vgiTarget: Optional[float] = None


class SimulationPoint(BaseModel):
    """One point of the first preview time series."""

    t: float
    pressure: float
    force: float
    gasRate: float
    stage: Optional[str] = None
    annulusPressure: Optional[float] = None
    bubblePressure: Optional[float] = None
    slugTop: Optional[float] = None
    slugBase: Optional[float] = None
    filmThickness: Optional[float] = None
    bubbleVelocity: Optional[float] = None
    slugVelocity: Optional[float] = None
    bottomPressure: Optional[float] = None
    fallbackVolume: Optional[float] = None
    gasLiftValveOpen: Optional[bool] = None
    liquidRate: Optional[float] = None
    producedVolume: Optional[float] = None
    slugVolume: Optional[float] = None
    filmVolume: Optional[float] = None


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
    physicalScope: str = ""
    terminalEvent: Optional[str] = None
    caseId: str = "santos-gli-50-70-80"
    referenceClassification: str = "full_case"
    validationLevel: Literal["provisional", "certified"] = "provisional"
    modelLimitations: List[str] = Field(default_factory=list)

class SimulationSample(BaseModel):
    t: float
    stage: str
    values: dict[str, float | bool | None]
    exactEvent: Optional[str] = None

class EventRecord(BaseModel):
    eventId: str
    t: float
    stageBefore: Optional[str] = None
    stageAfter: Optional[str] = None
    terminal: bool = False
    exact: bool = True

class StageSegment(BaseModel):
    stage: str
    startTime: float
    endTime: float
    startIndex: int
    endIndex: int

class SimulationTimeline(BaseModel):
    caseId: str
    physicalScope: str
    nativeSamples: List[SimulationSample]
    events: List[EventRecord]
    segments: List[StageSegment]
    resampledSeries: List[SimulationSample]
    resampleInterval: float
    adaptiveSolverOutputAvailable: bool = False


class PhysicalScopeResponse(BaseModel):
    physicalScope: str
    terminalEvent: str
    validationLevel: Literal["provisional", "certified"]
    certifiedStages: List[str]
    eventOrder: List[str]
    modelLimitations: List[str] = Field(default_factory=list)


class ReferenceCaseResponse(BaseModel):
    caseId: str
    source: str
    classification: str
    inputs: dict[str, float | str | None]
    targets: dict[str, float]
    allowedMetrics: List[str]


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
