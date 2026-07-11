import json
from pathlib import Path

from fastapi.middleware.cors import CORSMiddleware

from gli_api.main import (
    app,
    create_simulation,
    health,
    physical_scope,
    reference_cases,
    saved_simulation,
    saved_simulation_timeline,
)
from gli_api.schemas import SimulationInputs


def santos_input() -> SimulationInputs:
    return SimulationInputs(
        tubingDiameter=0.050673,
        valveDepth=1480.0,
        slugLength=412.5,
        surfaceTubingPressure=0.788,
        injectionPressure=6.966,
        api=40.0,
        bsw=50.0,
        gasRelativeDensity=0.7,
        casingPressureOpenRatio=0.7,
        projectName="QA Frontend",
        projectistName="QA",
    )


def test_required_api_routes_are_registered():
    routes = {(method, route.path) for route in app.routes if hasattr(route, "methods") for method in route.methods}
    assert ("GET", "/api/health") in routes
    assert ("GET", "/api/physical-scope") in routes
    assert ("GET", "/api/reference-cases") in routes
    assert ("POST", "/api/simulations") in routes
    assert ("GET", "/api/simulations/{simulation_id}") in routes
    assert ("GET", "/api/simulations/{simulation_id}/timeline") in routes


def test_health_and_cors_for_vite_frontend():
    assert health() == {"status": "ok"}
    cors = next(m for m in app.user_middleware if m.cls is CORSMiddleware)
    assert "http://localhost:5173" in cors.kwargs["allow_origins"]
    assert "http://127.0.0.1:5173" in cors.kwargs["allow_origins"]
    assert cors.kwargs["allow_methods"] == ["*"]


def test_physical_scope_and_reference_cases_are_available():
    scope = physical_scope()
    assert scope.validationLevel == "certified"
    assert scope.terminalEvent == "F_FILM_VELOCITY_ZERO"
    assert scope.certifiedStages == ["A_B", "B_C", "C_D", "D_E", "E_F"]
    assert scope.eventOrder[-1] == "F_FILM_VELOCITY_ZERO"
    assert scope.physicalScope.startswith("A_TO_F certified:")

    cases = {case.caseId: case for case in reference_cases()}
    assert cases["santos-gli-50-70-80"].classification == "full_case"
    assert cases["liao-example-table-5-14"].classification == "partial_benchmark"


def test_api_simulation_response_is_certified_a_to_f(monkeypatch, tmp_path):
    monkeypatch.setenv("GLI_DB_DRIVER", "sqlite")
    monkeypatch.setenv("GLI_SIMULATION_DB_PATH", str(tmp_path / "simulations.sqlite3"))
    result = create_simulation(santos_input())
    assert result.validationLevel == "certified"
    assert result.terminalEvent == "F_FILM_VELOCITY_ZERO"
    assert result.physicalScope.startswith("A_TO_F certified:")
    assert result.points[-1].stage == "E_F"
    assert abs(result.points[-1].slugVelocity) < 1e-6
    assert result.metrics.duration == result.points[-1].t
    assert result.diagnostics is not None
    assert abs(sum(stage.duration for stage in result.diagnostics.stageDurations) - result.metrics.duration) < 1e-9
    assert [stage.stage for stage in result.diagnostics.stageDurations] == ["A_B", "B_C", "C_D", "D_E", "E_F"]
    assert result.diagnostics.gasInjectedVolume == result.points[-1].gasInjectedVolume
    assert result.diagnostics.maxMotorValveRate > 0.0
    assert result.diagnostics.maxFilmVelocity > 0.0
    assert result.diagnostics.maxGlvMassRate >= 0.0
    assert all(balance.gasRelativeError is not None for balance in result.diagnostics.balanceErrors)
    assert {variable.name for variable in result.diagnostics.variables} >= {
        "gasInjectedVolume",
        "filmVelocity",
        "motorValveRate",
        "glvMassRate",
        "stageDurations",
    }


def test_saved_simulation_and_timeline_contract(monkeypatch, tmp_path):
    monkeypatch.setenv("GLI_DB_DRIVER", "sqlite")
    monkeypatch.setenv("GLI_SIMULATION_DB_PATH", str(tmp_path / "simulations.sqlite3"))

    created = create_simulation(santos_input())
    simulation_id = created.simulationId
    stored = saved_simulation(simulation_id)
    assert stored.simulationId == simulation_id

    timeline = saved_simulation_timeline(simulation_id, interval_s=2.0)
    assert [event.eventId for event in timeline.events] == [
        "A_INITIAL_STATE",
        "B_GAS_LIFT_VALVE_OPENS",
        "C_MOTOR_VALVE_CLOSES",
        "D_SLUG_TOP_REACHED_SURFACE",
        "E_SLUG_BASE_REACHED_SURFACE",
        "F_FILM_VELOCITY_ZERO",
    ]
    assert [segment.stage for segment in timeline.segments] == ["A_B", "B_C", "C_D", "D_E", "E_F"]
    assert timeline.resampledSeries[-1].exactEvent == "F_FILM_VELOCITY_ZERO"


def test_frozen_frontend_fixture_is_certified_a_to_f():
    fixture = Path("docs/api/examples/santos_a_f_certified_response.json")
    data = json.loads(fixture.read_text(encoding="utf-8"))
    assert data["validationLevel"] == "certified"
    assert data["terminalEvent"] == "F_FILM_VELOCITY_ZERO"
    assert data["physicalScope"].startswith("A_TO_F certified:")
    assert data["points"][-1]["stage"] == "E_F"
    assert data["metrics"]["duration"] == data["points"][-1]["t"]
