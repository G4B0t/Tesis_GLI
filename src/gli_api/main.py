"""HTTP API for the GLI backend."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .database import get_simulation, list_simulations
from gli.reference_cases import REFERENCE_CASES
from .schemas import (
    SimulationInputs,
    SimulationResult,
    ScenarioComparisonRequest,
    ScenarioComparisonResponse,
    SimulationSummary,
    StoredSimulation,
    ValidationReference,
    EventRecord, SimulationSample, SimulationTimeline,
    PhysicalScopeResponse, ReferenceCaseResponse,
)
from .scenario_service import compare_scenarios
from .simulation_service import save_simulation_run, simulate
from .validation_reference import get_gli_conventional_reference
from .timeline_service import build_timeline


app = FastAPI(
    title="Tesis GLI API",
    description="Backend para la simulacion de Gas Lift Intermitente Convencional.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "https://gli-simulator.vercel.app",
    ],
    allow_origin_regex=r"http://(127\.0\.0\.1|localhost):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


CERTIFIED_SCOPE = (
    "NOT_SOURCE_CERTIFIED_A_TO_E: Stage 3 can stop at a material pre-E GLV closure; "
    "the source transition and upstream GLV correlation remain unresolved."
)
TERMINAL_EVENT = "GLV_CLOSE_BEFORE_E_SOURCE_BLOCK"
CERTIFIED_STAGES = []
EVENT_ORDER = [
    "A_INITIAL_STATE",
    "B_GAS_LIFT_VALVE_OPENS",
    "C_MOTOR_VALVE_CLOSES",
    "D_SLUG_TOP_REACHED_SURFACE",
    "GLV_CLOSE_BEFORE_E_SOURCE_BLOCK",
]
MODEL_LIMITATIONS = [
    "E is not reached in the reconciled base run; F/G/H and daily cycle metrics are unavailable.",
    "Liao Table 5.14 remains a partial benchmark, not a quantitative validation target for this case.",
    "Resolving the D->E spatial gas state is required before Stage 4.2 can start by identity.",
]


@app.get("/health")
@app.get("/api/health")
def health() -> dict:
    """Return a small status payload for frontend connection checks."""

    return {"status": "ok"}


@app.get("/api/physical-scope", response_model=PhysicalScopeResponse)
@app.get("/physical-scope", response_model=PhysicalScopeResponse)
def physical_scope() -> PhysicalScopeResponse:
    return PhysicalScopeResponse(
        physicalScope=CERTIFIED_SCOPE,
        terminalEvent=TERMINAL_EVENT,
        validationLevel="provisional",
        certifiedStages=CERTIFIED_STAGES,
        eventOrder=EVENT_ORDER,
        modelLimitations=MODEL_LIMITATIONS,
    )


@app.get("/api/reference-cases", response_model=list[ReferenceCaseResponse])
@app.get("/reference-cases", response_model=list[ReferenceCaseResponse])
def reference_cases() -> list[ReferenceCaseResponse]:
    return [
        ReferenceCaseResponse(
            caseId=case.case_id,
            source=case.source,
            classification=case.classification,
            inputs=dict(case.inputs),
            targets=dict(case.targets),
            allowedMetrics=sorted(case.allowed_metrics),
        )
        for case in REFERENCE_CASES.values()
    ]


@app.get("/validation/gli-convencional", response_model=ValidationReference)
def gli_conventional_validation_reference() -> ValidationReference:
    """Return Santos reference charts and tables for GLI convencional."""

    return get_gli_conventional_reference()


@app.post("/simulate", response_model=SimulationResult)
@app.post("/api/simulate", response_model=SimulationResult)
def run_simulation(inputs: SimulationInputs) -> SimulationResult:
    """Run the current GLI simulation preview without saving it."""

    return simulate(inputs)

@app.post("/timeline", response_model=SimulationTimeline)
@app.post("/api/timeline", response_model=SimulationTimeline)
def simulation_timeline(inputs: SimulationInputs, interval_s: float = 1.0) -> SimulationTimeline:
    return build_timeline(simulate(inputs), interval_s)

@app.post("/events", response_model=list[EventRecord])
@app.post("/api/events", response_model=list[EventRecord])
def simulation_events(inputs: SimulationInputs) -> list[EventRecord]:
    return build_timeline(simulate(inputs)).events

@app.post("/series", response_model=list[SimulationSample])
@app.post("/api/series", response_model=list[SimulationSample])
def simulation_series(inputs: SimulationInputs, interval_s: float = 1.0) -> list[SimulationSample]:
    return build_timeline(simulate(inputs), interval_s).resampledSeries


@app.post("/scenarios", response_model=ScenarioComparisonResponse)
@app.post("/api/scenarios", response_model=ScenarioComparisonResponse)
def scenario_comparison(request: ScenarioComparisonRequest) -> ScenarioComparisonResponse:
    """Run a manual set of scenarios using the certified solver as engine."""

    return compare_scenarios(request)


@app.post("/simulations", response_model=SimulationResult)
@app.post("/api/simulations", response_model=SimulationResult)
def create_simulation(inputs: SimulationInputs) -> SimulationResult:
    """Run and save a GLI simulation."""

    return save_simulation_run(inputs)


@app.get("/simulations", response_model=list[SimulationSummary])
@app.get("/api/simulations", response_model=list[SimulationSummary])
def recent_simulations(limit: int = 20) -> list[SimulationSummary]:
    """Return recent simulations saved in the configured database."""

    return list_simulations(limit=limit)


@app.get("/simulations/{simulation_id}", response_model=StoredSimulation)
@app.get("/api/simulations/{simulation_id}", response_model=StoredSimulation)
def saved_simulation(simulation_id: int) -> StoredSimulation:
    """Return a saved simulation by id."""

    simulation = get_simulation(simulation_id)
    if simulation is None:
        raise HTTPException(status_code=404, detail="Simulation not found")

    return simulation


def stored_to_result(stored: StoredSimulation) -> SimulationResult:
    return SimulationResult(
        metrics=stored.metrics,
        points=stored.points,
        simulationId=stored.simulationId,
        projectName=stored.projectName,
        projectistName=stored.projectistName,
        createdAt=stored.createdAt,
        physicalScope=CERTIFIED_SCOPE,
        terminalEvent=TERMINAL_EVENT,
        caseId=stored.inputs.caseId,
        referenceClassification=REFERENCE_CASES[stored.inputs.caseId].classification,
        validationLevel="provisional",
        modelLimitations=MODEL_LIMITATIONS,
    )


@app.get("/simulations/{simulation_id}/timeline", response_model=SimulationTimeline)
@app.get("/api/simulations/{simulation_id}/timeline", response_model=SimulationTimeline)
def saved_simulation_timeline(simulation_id: int, interval_s: float = 1.0) -> SimulationTimeline:
    simulation = get_simulation(simulation_id)
    if simulation is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return build_timeline(stored_to_result(simulation), interval_s)
