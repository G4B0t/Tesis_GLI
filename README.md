# Tesis GLI

Simulacion dinamica del metodo Gas Lift Intermitente Convencional (GLI),
basada en el Modelo I de Santos.

## Estructura

- `src/gli/parameters.py`: parametros fisicos, geometricos y operativos.
- `src/gli/geometry.py`: calculos de areas, radios y volumenes.
- `src/gli/fluids.py`: propiedades de liquidos y gases.
- `src/gli/valves.py`: ecuaciones de caudal y control de valvulas.
- `src/gli/initial_conditions.py`: condiciones iniciales de cada etapa.
- `src/gli/events.py`: condiciones para pasar de una etapa a otra.
- `src/gli/stages.py`: ecuaciones por etapa del ciclo GLI.
- `src/gli/solver.py`: integradores numericos.
- `scripts/run_base_case.py`: corrida base de prueba.

## Activar el entorno virtual

```powershell
D:\UPB\Tesis_GLI\.venv\Scripts\Activate.ps1
```

## Instalar dependencias

```powershell
pip install -r requirements.txt
```

## Primer objetivo

Implementar primero las condiciones iniciales y la Etapa 1 del GLI:

1. Calcular propiedades iniciales.
2. Simular la inyeccion de gas en el anular.
3. Detectar apertura de la valvula de gas lift.
4. Pasar a condiciones iniciales de Etapa 2.
