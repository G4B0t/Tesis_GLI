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

## Configurar base de datos

Crear un archivo `.env` local a partir de `.env.example`:

```powershell
Copy-Item .env.example .env
```

Variables principales para MySQL:

```text
GLI_DB_DRIVER=mysql
GLI_DB_HOST=127.0.0.1
GLI_DB_PORT=3306
GLI_DB_NAME=tesis_gli
GLI_DB_USER=gabriel
GLI_DB_PASSWORD=tu_password
```

La base se crea automaticamente si el usuario tiene permisos. Tambien se puede
crear manualmente en MySQL Workbench:

```sql
CREATE DATABASE tesis_gli
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
```

La tabla `simulations` se crea automaticamente al ejecutar la primera
simulacion.

## Ejecutar API local

```powershell
D:\UPB\Tesis_GLI\.venv\Scripts\Activate.ps1
uvicorn gli_api.main:app --app-dir src --reload --host 127.0.0.1 --port 8000
```

Endpoints iniciales:

- `GET /health`
- `POST /simulate`
- `GET /simulations`
- `GET /simulations/{simulation_id}`

Si `GLI_DB_DRIVER=sqlite`, las corridas se guardan en SQLite:

```text
data/simulations.sqlite3
```

## Primer objetivo

Implementar primero las condiciones iniciales y la Etapa 1 del GLI:

1. Calcular propiedades iniciales.
2. Simular la inyeccion de gas en el anular.
3. Detectar apertura de la valvula de gas lift.
4. Pasar a condiciones iniciales de Etapa 2.
