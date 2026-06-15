"""Santos reference data for the conventional intermittent gas lift model.

The chart curves are visual digitizations from Santos chapter 5. They are meant
as validation targets for shape, stages and event timing while the full dynamic
model is completed. Table 5.14 keeps the numeric comparison reported by Santos.
"""

from .schemas import ReferenceFigure, ReferenceSeries, ReferenceTable, ValidationReference


def series(key: str, label: str, unit: str, color: str, points: list[tuple[float, float]]) -> ReferenceSeries:
    """Build a reference series from compact coordinate tuples."""

    return ReferenceSeries(
        key=key,
        label=label,
        unit=unit,
        color=color,
        points=[{"x": x, "y": y} for x, y in points],
    )


GLI_CONVENTIONAL_REFERENCE = ValidationReference(
    title="Simulacion GLI Convencional",
    subtitle="Referencias Santos para el metodo Gas Lift Intermitente Convencional.",
    source="Santos, capitulo 5: Figuras 5.1 a 5.4, Tablas 5.6, 5.7 y 5.14.",
    figures=[
        ReferenceFigure(
            id="figura-5-1",
            title="Figura 5.1 - Presion del gas en superficie Pc1",
            xLabel="Tiempo [s]",
            yLabel="Presion [kgf/cm2]",
            note="Curva digitalizada visualmente para el pozo base y punto operacional {50,70,80}.",
            series=[
                series(
                    "pc1",
                    "Pc1",
                    "kgf/cm2",
                    "#1f7a8c",
                    [(0, 54.0), (18, 58.8), (55, 62.5), (120, 60.2), (240, 56.8), (320, 54.2), (1400, 54.6)],
                )
            ],
        ),
        ReferenceFigure(
            id="figura-5-2",
            title="Figura 5.2 - Presion de fondo en flujo Pwf",
            xLabel="Tiempo [s]",
            yLabel="Presion [kgf/cm2]",
            note="Referencia de forma de curva para inyeccion, produccion, descompresion y alimentacion.",
            series=[
                series(
                    "pwf",
                    "Pwf",
                    "kgf/cm2",
                    "#6f4e9b",
                    [(0, 48.0), (12, 66.0), (45, 70.5), (210, 66.5), (315, 62.0), (380, 55.0), (500, 20.0), (760, 31.0), (1100, 43.0), (1400, 52.0)],
                )
            ],
        ),
        ReferenceFigure(
            id="figura-5-3",
            title="Figura 5.3 - Posicion del tope hL y base hB de la golfada",
            xLabel="Tiempo [s]",
            yLabel="Altura [m]",
            note="La llegada del tope ocurre cerca de D y la base cerca de E.",
            series=[
                series(
                    "h_l",
                    "hL",
                    "m",
                    "#0f8a65",
                    [(25, 450), (55, 540), (120, 760), (190, 1050), (255, 1320), (290, 1500), (330, 1500)],
                ),
                series(
                    "h_b",
                    "hB",
                    "m",
                    "#b42318",
                    [(25, 0), (75, 220), (140, 520), (205, 830), (265, 1140), (310, 1360), (330, 1500)],
                ),
            ],
        ),
        ReferenceFigure(
            id="figura-5-4",
            title="Figura 5.4 - Velocidades de burbuja vB y golfada vL",
            xLabel="Tiempo [s]",
            yLabel="Velocidad [m/s]",
            note="La velocidad crece rapidamente cuando la base de la golfada se aproxima a superficie.",
            series=[
                series(
                    "v_b",
                    "vB",
                    "m/s",
                    "#8f5f21",
                    [(0, 0.0), (15, 3.8), (45, 4.5), (140, 4.6), (250, 4.6), (290, 4.8), (310, 6.8), (325, 9.5), (335, 12.8)],
                ),
                series(
                    "v_l",
                    "vL",
                    "m/s",
                    "#2563eb",
                    [(0, 0.0), (15, 3.4), (45, 4.0), (140, 4.0), (250, 4.0), (290, 4.2), (310, 6.0), (325, 8.8), (335, 12.0)],
                ),
            ],
        ),
    ],
    tables=[
        ReferenceTable(
            id="tabla-5-6",
            title="Etapas del ciclo de produccion para el metodo GLI",
            columns=["Etapa", "Tramo"],
            rows=[
                ["Inyeccion de gas", "AC"],
                ["Elevacion de la golfada de liquido", "BD"],
                ["Produccion de la golfada de liquido", "DE"],
                ["Descompresion del gas - Fase II", "EF"],
                ["Descompresion del gas - Fase III", "FG"],
                ["Alimentacion", "GH"],
            ],
        ),
        ReferenceTable(
            id="tabla-5-7",
            title="Eventos correspondientes a cada punto en Figuras 5.1 a 5.4",
            columns=["Punto", "Evento"],
            rows=[
                ["A", "Abre-se a valvula motora na superficie"],
                ["B", "Abre-se a valvula de gas lift no fundo do poco"],
                ["C", "Fecha-se a valvula motora na superficie"],
                ["D", "Topo da golfada de liquido chega a superficie"],
                ["E", "Base da golfada chega a superficie"],
                ["F", "Velocidade do filme liquido torna-se igual a zero"],
                ["G", "Concluida a descompressao do gas"],
                ["H", "Altura de liquido inicial restabelecida"],
            ],
        ),
        ReferenceTable(
            id="tabla-5-14",
            title="Comparacion entre Simulacion y los datos de Liao",
            columns=["Parametro", "Liao", "Referencia", "Simulador"],
            rows=[
                ["Volumen da golfada final [m3]", "0.309", "Figura 29", "0.299"],
                ["Volumen producido por entrainment [m3]", "0.077", "Figura 30", "0.030"],
                ["Volumen producido total [m3]", "0.387", "Figura 31", "0.330"],
                ["Recuperacion de liquido [%]", "0.740", "Figura 32", "0.610"],
                ["Tiempo de elevacion [s]", "275", "Figura 33", "289"],
                ["Tiempo de descompresion [s]", "275", "Figura 34", "394"],
                ["Tiempo de ciclo [s]", "1249", "Figura 35", "1253"],
                ["Numero de ciclos", "69", "Figura 36", "69"],
                ["Vazao de liquido [m3/d]", "26.39", "Figura 37", "22.73"],
                ["Vazao de gas [m3/d]", "8500", "Figura 38", "10308"],
                ["Presion media de flujo [kgf/cm2]", "33.33", "Figura 41", "37.83"],
            ],
        ),
    ],
)


def get_gli_conventional_reference() -> ValidationReference:
    """Return Santos validation references for the conventional GLI model."""

    return GLI_CONVENTIONAL_REFERENCE
