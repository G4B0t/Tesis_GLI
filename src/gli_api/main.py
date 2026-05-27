"""HTTP API for the GLI backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .schemas import SimulationInputs, SimulationResult
from .simulation_service import simulate


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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    """Return a small status payload for frontend connection checks."""

    return {"status": "ok"}


@app.post("/simulate", response_model=SimulationResult)
def run_simulation(inputs: SimulationInputs) -> SimulationResult:
    """Run the current GLI simulation preview."""

    return simulate(inputs)
