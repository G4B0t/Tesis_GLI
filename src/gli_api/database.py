"""SQLite persistence for simulation runs."""

import json
import os
import sqlite3
from pathlib import Path
from typing import List, Optional

from .schemas import (
    SimulationInputs,
    SimulationMetrics,
    SimulationPoint,
    SimulationResult,
    SimulationSummary,
    StoredSimulation,
)


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = ROOT_DIR / "data" / "simulations.sqlite3"


def database_path() -> Path:
    """Return the configured database path."""

    configured_path = os.getenv("GLI_SIMULATION_DB_PATH")
    if configured_path:
        return Path(configured_path)

    return DEFAULT_DATABASE_PATH


def connect() -> sqlite3.Connection:
    """Open the SQLite database and make sure the schema exists."""

    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    initialize_database(connection)
    return connection


def initialize_database(connection: sqlite3.Connection) -> None:
    """Create tables needed by the simulator."""

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS simulations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT NOT NULL,
            projectist_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            inputs_json TEXT NOT NULL,
            metrics_json TEXT NOT NULL,
            points_json TEXT NOT NULL
        )
        """
    )
    connection.commit()


def save_simulation(
    inputs: SimulationInputs,
    result: SimulationResult,
    created_at: str,
) -> int:
    """Persist a simulation result and return its database id."""

    with connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO simulations (
                project_name,
                projectist_name,
                created_at,
                inputs_json,
                metrics_json,
                points_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                inputs.projectName,
                inputs.projectistName,
                created_at,
                inputs.model_dump_json(),
                result.metrics.model_dump_json(),
                json.dumps([point.model_dump() for point in result.points]),
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


def list_simulations(limit: int = 20) -> List[SimulationSummary]:
    """Return recent simulation summaries."""

    with connect() as connection:
        rows = connection.execute(
            """
            SELECT id, project_name, projectist_name, created_at, metrics_json
            FROM simulations
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    summaries = []
    for row in rows:
        metrics = SimulationMetrics.model_validate_json(row["metrics_json"])
        summaries.append(
            SimulationSummary(
                simulationId=row["id"],
                projectName=row["project_name"],
                projectistName=row["projectist_name"],
                createdAt=row["created_at"],
                pTo=metrics.pTo,
                duration=metrics.duration,
            )
        )

    return summaries


def get_simulation(simulation_id: int) -> Optional[StoredSimulation]:
    """Return one persisted simulation by id."""

    with connect() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM simulations
            WHERE id = ?
            """,
            (simulation_id,),
        ).fetchone()

    if row is None:
        return None

    return StoredSimulation(
        simulationId=row["id"],
        projectName=row["project_name"],
        projectistName=row["projectist_name"],
        createdAt=row["created_at"],
        inputs=SimulationInputs.model_validate_json(row["inputs_json"]),
        metrics=SimulationMetrics.model_validate_json(row["metrics_json"]),
        points=[SimulationPoint.model_validate(point) for point in json.loads(row["points_json"])],
    )
