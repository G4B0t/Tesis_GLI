"""Conservative design-domain classification for API inputs.

This module contains no simulator calls.  It only compares API-like input
values against the certified Santos reference and the local Block 7B bands.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


DesignValidationLevel = Literal[
    "certified",
    "validated_range_candidate",
    "provisional",
    "failed",
    "out_of_domain",
]


class DesignInputLike(Protocol):
    caseId: str
    tubingDiameter: float
    valveDepth: float
    slugLength: float
    surfaceTubingPressure: float
    injectionPressure: float
    api: float
    bsw: float
    gasRelativeDensity: float
    casingPressureOpenRatio: float
    waterRelativeDensity: float
    surfaceTemperature: float
    injectedGasReferenceRatio: float


@dataclass(frozen=True)
class DesignBand:
    field: str
    base_value: float
    low_value: float
    high_value: float
    unit: str


@dataclass(frozen=True)
class DesignDomainClassification:
    validation_level: DesignValidationLevel
    exact_santos_reference: bool
    inside_local_matrix: bool
    outside_fields: tuple[str, ...]
    statement: str


SANTOS_CASE_ID = "santos-gli-50-70-80"

SANTOS_CERTIFIED_INPUTS: dict[str, float | str] = {
    "caseId": SANTOS_CASE_ID,
    "tubingDiameter": 0.050673,
    "valveDepth": 1480.0,
    "slugLength": 412.5,
    "surfaceTubingPressure": 0.788,
    "injectionPressure": 6.966,
    "api": 40.0,
    "bsw": 50.0,
    "gasRelativeDensity": 0.7,
    "casingPressureOpenRatio": 0.7,
    "waterRelativeDensity": 1.07,
    "surfaceTemperature": 80.0,
    "injectedGasReferenceRatio": 0.8,
}


LOCAL_MATRIX_BANDS: tuple[DesignBand, ...] = (
    DesignBand("injectionPressure", 6.966, 6.966 * 0.95, 6.966 * 1.05, "MPa"),
    DesignBand("slugLength", 412.5, 412.5 * 0.95, 412.5 * 1.05, "m"),
    DesignBand("valveDepth", 1480.0, 1480.0 * 0.95, 1480.0 * 1.05, "m"),
    DesignBand("tubingDiameter", 0.050673, 0.050673 * 0.98, 0.050673 * 1.02, "m"),
    DesignBand("bsw", 50.0, 45.0, 55.0, "%"),
    DesignBand("api", 40.0, 38.0, 42.0, "API"),
)

FIXED_REFERENCE_FIELDS: tuple[str, ...] = (
    "surfaceTubingPressure",
    "gasRelativeDensity",
    "casingPressureOpenRatio",
    "waterRelativeDensity",
    "surfaceTemperature",
    "injectedGasReferenceRatio",
)


def _close(a: float, b: float, *, rel: float = 1e-10, abs_tol: float = 1e-12) -> bool:
    return abs(a - b) <= max(abs_tol, rel * max(abs(a), abs(b), 1.0))


def is_exact_santos_reference(inputs: DesignInputLike) -> bool:
    if inputs.caseId != SANTOS_CASE_ID:
        return False
    for key, expected in SANTOS_CERTIFIED_INPUTS.items():
        if key == "caseId":
            continue
        if not _close(float(getattr(inputs, key)), float(expected)):
            return False
    return True


def classify_design_domain(inputs: DesignInputLike, *, chain_certified: bool) -> DesignDomainClassification:
    if not chain_certified:
        return DesignDomainClassification(
            validation_level="failed",
            exact_santos_reference=False,
            inside_local_matrix=False,
            outside_fields=(),
            statement="La cadena A->F no cerró sus contratos físicos para estos parámetros.",
        )
    if is_exact_santos_reference(inputs):
        return DesignDomainClassification(
            validation_level="certified",
            exact_santos_reference=True,
            inside_local_matrix=True,
            outside_fields=(),
            statement="Caso Santos exacto certificado A->F.",
        )
    if inputs.caseId != SANTOS_CASE_ID:
        return DesignDomainClassification(
            validation_level="out_of_domain",
            exact_santos_reference=False,
            inside_local_matrix=False,
            outside_fields=("caseId",),
            statement="El caso no pertenece al caso Santos con matriz local 7B.",
        )

    outside: list[str] = []
    for field in FIXED_REFERENCE_FIELDS:
        if not _close(float(getattr(inputs, field)), float(SANTOS_CERTIFIED_INPUTS[field])):
            outside.append(field)
    for band in LOCAL_MATRIX_BANDS:
        value = float(getattr(inputs, band.field))
        if value < band.low_value or value > band.high_value:
            outside.append(band.field)
    if outside:
        return DesignDomainClassification(
            validation_level="out_of_domain",
            exact_santos_reference=False,
            inside_local_matrix=False,
            outside_fields=tuple(outside),
            statement=(
                "La simulación cerró numéricamente, pero los parámetros salen de la matriz local "
                "7B; no debe usarse como resultado de diseño validado."
            ),
        )
    return DesignDomainClassification(
        validation_level="validated_range_candidate",
        exact_santos_reference=False,
        inside_local_matrix=True,
        outside_fields=(),
        statement=(
            "Los parámetros están dentro de la matriz local 7B y la cadena A->F cerró. "
            "Clasificación candidata a rango validado; falta validación independiente."
        ),
    )
