"""HTTP API for the GLI backend."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .database import get_simulation, list_simulations
from .schemas import (
    SimulationInputs,
    SimulationResult,
    SimulationSummary,
    StoredSimulation,
    ValidationReference,
)
from .simulation_service import save_simulation_run, simulate
from .validation_reference import get_gli_conventional_reference


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
    ],
    allow_origin_regex=r"http://(127\.0\.0\.1|localhost):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    """Return a small status payload for frontend connection checks."""

    return {"status": "ok"}


@app.get("/validation/gli-convencional", response_model=ValidationReference)
def gli_conventional_validation_reference() -> ValidationReference:
    """Return Santos reference charts and tables for GLI convencional."""

    return get_gli_conventional_reference()


@app.post("/simulate", response_model=SimulationResult)
def run_simulation(inputs: SimulationInputs) -> SimulationResult:
    """Run the current GLI simulation preview without saving it."""

    return simulate(inputs)


@app.post("/simulations", response_model=SimulationResult)
def create_simulation(inputs: SimulationInputs) -> SimulationResult:
    """Run and save a GLI simulation."""

    return save_simulation_run(inputs)


@app.get("/simulations", response_model=list[SimulationSummary])
def recent_simulations(limit: int = 20) -> list[SimulationSummary]:
    """Return recent simulations saved in the configured database."""

    return list_simulations(limit=limit)


@app.get("/simulations/{simulation_id}", response_model=StoredSimulation)
def saved_simulation(simulation_id: int) -> StoredSimulation:
    """Return a saved simulation by id."""

    simulation = get_simulation(simulation_id)
    if simulation is None:
        raise HTTPException(status_code=404, detail="Simulation not found")

    return simulation
