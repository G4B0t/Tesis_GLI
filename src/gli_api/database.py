"""Persistence for simulation runs.

The backend uses MySQL when GLI_DB_DRIVER=mysql. SQLite remains available as a
local fallback for quick tests.
"""

import json
import os
import re
import sqlite3
from pathlib import Path
from typing import List, Optional, Protocol

from dotenv import load_dotenv
import pymysql
from pymysql.cursors import DictCursor

from .schemas import (
    SimulationInputs,
    SimulationMetrics,
    SimulationPoint,
    SimulationResult,
    SimulationSummary,
    StoredSimulation,
)


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SQLITE_PATH = ROOT_DIR / "data" / "simulations.sqlite3"
MYSQL_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")

load_dotenv(ROOT_DIR / ".env")


class Repository(Protocol):
    """Storage operations required by the API."""

    def save_simulation(
        self,
        inputs: SimulationInputs,
        result: SimulationResult,
        created_at: str,
    ) -> int:
        """Persist a simulation and return its id."""

    def list_simulations(self, limit: int = 20) -> List[SimulationSummary]:
        """Return recent simulation summaries."""

    def get_simulation(self, simulation_id: int) -> Optional[StoredSimulation]:
        """Return one saved simulation."""


class SQLiteRepository:
    """SQLite fallback repository."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def connect(self) -> sqlite3.Connection:
        """Open SQLite and ensure the schema exists."""

        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
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
        return connection

    def save_simulation(
        self,
        inputs: SimulationInputs,
        result: SimulationResult,
        created_at: str,
    ) -> int:
        """Persist a simulation in SQLite."""

        with self.connect() as connection:
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
                serialized_values(inputs, result, created_at),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def list_simulations(self, limit: int = 20) -> List[SimulationSummary]:
        """Return recent simulations from SQLite."""

        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT id, project_name, projectist_name, created_at, metrics_json
                FROM simulations
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [summary_from_row(row) for row in rows]

    def get_simulation(self, simulation_id: int) -> Optional[StoredSimulation]:
        """Return one SQLite simulation by id."""

        with self.connect() as connection:
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

        return stored_from_row(row)


class MySQLRepository:
    """MySQL repository used for the thesis simulator."""

    def connect(self) -> pymysql.connections.Connection:
        """Open MySQL and ensure the schema exists."""

        database_name = os.getenv("GLI_DB_NAME", "tesis_gli")
        self.ensure_database(database_name)
        connection = pymysql.connect(
            host=os.getenv("GLI_DB_HOST", "127.0.0.1"),
            port=int(os.getenv("GLI_DB_PORT", "3306")),
            user=os.getenv("GLI_DB_USER", "root"),
            password=os.getenv("GLI_DB_PASSWORD", ""),
            database=database_name,
            charset="utf8mb4",
            cursorclass=DictCursor,
            autocommit=False,
        )
        self.initialize(connection)
        return connection

    def ensure_database(self, database_name: str) -> None:
        """Create the configured MySQL database if it does not exist."""

        if not MYSQL_IDENTIFIER_PATTERN.match(database_name):
            raise ValueError("GLI_DB_NAME must contain only letters, numbers and underscores.")

        connection = pymysql.connect(
            host=os.getenv("GLI_DB_HOST", "127.0.0.1"),
            port=int(os.getenv("GLI_DB_PORT", "3306")),
            user=os.getenv("GLI_DB_USER", "root"),
            password=os.getenv("GLI_DB_PASSWORD", ""),
            charset="utf8mb4",
            cursorclass=DictCursor,
            autocommit=True,
        )
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    CREATE DATABASE IF NOT EXISTS `{database_name}`
                    CHARACTER SET utf8mb4
                    COLLATE utf8mb4_unicode_ci
                    """
                )
        finally:
            connection.close()

    def initialize(self, connection: pymysql.connections.Connection) -> None:
        """Create MySQL table if needed."""

        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS simulations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    project_name VARCHAR(120) NOT NULL,
                    projectist_name VARCHAR(120) NOT NULL,
                    created_at VARCHAR(40) NOT NULL,
                    inputs_json JSON NOT NULL,
                    metrics_json JSON NOT NULL,
                    points_json JSON NOT NULL
                ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """
            )
        connection.commit()

    def save_simulation(
        self,
        inputs: SimulationInputs,
        result: SimulationResult,
        created_at: str,
    ) -> int:
        """Persist a simulation in MySQL."""

        connection = self.connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO simulations (
                        project_name,
                        projectist_name,
                        created_at,
                        inputs_json,
                        metrics_json,
                        points_json
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    serialized_values(inputs, result, created_at),
                )
                simulation_id = int(cursor.lastrowid)
            connection.commit()
            return simulation_id
        finally:
            connection.close()

    def list_simulations(self, limit: int = 20) -> List[SimulationSummary]:
        """Return recent simulations from MySQL."""

        connection = self.connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, project_name, projectist_name, created_at, metrics_json
                    FROM simulations
                    ORDER BY id DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = cursor.fetchall()
            return [summary_from_row(row) for row in rows]
        finally:
            connection.close()

    def get_simulation(self, simulation_id: int) -> Optional[StoredSimulation]:
        """Return one MySQL simulation by id."""

        connection = self.connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT *
                    FROM simulations
                    WHERE id = %s
                    """,
                    (simulation_id,),
                )
                row = cursor.fetchone()
            if row is None:
                return None
            return stored_from_row(row)
        finally:
            connection.close()


def serialized_values(
    inputs: SimulationInputs,
    result: SimulationResult,
    created_at: str,
) -> tuple:
    """Serialize simulation values for SQL storage."""

    return (
        inputs.projectName,
        inputs.projectistName,
        created_at,
        inputs.model_dump_json(),
        result.metrics.model_dump_json(),
        json.dumps([point.model_dump() for point in result.points]),
    )


def summary_from_row(row: sqlite3.Row | dict) -> SimulationSummary:
    """Build a summary schema from a SQL row."""

    metrics = SimulationMetrics.model_validate_json(row["metrics_json"])
    return SimulationSummary(
        simulationId=row["id"],
        projectName=row["project_name"],
        projectistName=row["projectist_name"],
        createdAt=row["created_at"],
        pTo=metrics.pTo,
        duration=metrics.duration,
    )


def stored_from_row(row: sqlite3.Row | dict) -> StoredSimulation:
    """Build a full stored simulation schema from a SQL row."""

    return StoredSimulation(
        simulationId=row["id"],
        projectName=row["project_name"],
        projectistName=row["projectist_name"],
        createdAt=row["created_at"],
        inputs=SimulationInputs.model_validate_json(row["inputs_json"]),
        metrics=SimulationMetrics.model_validate_json(row["metrics_json"]),
        points=[SimulationPoint.model_validate(point) for point in json.loads(row["points_json"])],
    )


def repository() -> Repository:
    """Return repository selected by environment."""

    driver = os.getenv("GLI_DB_DRIVER", "sqlite").lower()
    if driver == "mysql":
        return MySQLRepository()

    configured_path = os.getenv("GLI_SIMULATION_DB_PATH")
    return SQLiteRepository(Path(configured_path) if configured_path else DEFAULT_SQLITE_PATH)


def save_simulation(
    inputs: SimulationInputs,
    result: SimulationResult,
    created_at: str,
) -> int:
    """Persist a simulation result and return its database id."""

    return repository().save_simulation(inputs, result, created_at)


def list_simulations(limit: int = 20) -> List[SimulationSummary]:
    """Return recent simulation summaries."""

    return repository().list_simulations(limit=limit)


def get_simulation(simulation_id: int) -> Optional[StoredSimulation]:
    """Return one persisted simulation by id."""

    return repository().get_simulation(simulation_id)
