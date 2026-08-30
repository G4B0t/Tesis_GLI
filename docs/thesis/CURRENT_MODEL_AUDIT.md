# Auditoría del estado actual del modelo GLI

Fecha de corte: 2026-08-29. Ramas auditadas: `feature/gli-thesis-completion`, creadas desde `test` en ambos repositorios. Esta auditoría no modifica ecuaciones, solvers, API ni interfaz.

## 1. Estado Git y procedencia

| Repositorio | Base exacta de `test` | Remoto | Estado al iniciar |
|---|---|---|---|
| Backend `D:\UPB\Tesis_GLI` | `85225c799470278d74a14c65c5ebcc3bafa953b2` — “Allow Vercel frontend CORS” | `git@github.com-G4B0t:G4B0t/Tesis_GLI.git` | limpio |
| Frontend `D:\UPB\Tesis_GLI_FE` | `41f1b776b20909e32d53ab47db0e363861436207` — “feat: localize physical scope and clarify cycle time” | `git@github.com-G4B0t:G4B0t/Tesis_GLI_FE.git` | limpio |

En el cierre de la auditoría ambas ramas muestran upstream `origin/feature/gli-thesis-completion`. No se hizo `pull`, merge, rebase ni cambio de rama base durante la revisión.

## 2. Arquitectura encontrada

### Backend

- `src/gli/parameters.py`: dataclasses congeladas para geometría, fluidos, gas, válvulas, operación y coeficientes.
- `src/gli/initial_conditions.py`: condiciones iniciales del caso Santos.
- `src/gli/stage1_dynamic.py`: tramo A→B.
- `src/gli/stage_bc_common.py`: tramo B→C compatible con Santos.
- `src/gli/stage_cd_common.py`: tramo C→D, incluido el enclavamiento de cierre de GLV.
- `src/gli/stage_de_dynamic.py`: producción D→E.
- `src/gli/stage_ef_dynamic.py`: descompresión E→F.
- `src/gli/events.py`, `geometry.py`, `fluids.py`, `valves.py`, `fallback.py`: eventos y cierres físicos compartidos.
- `src/gli/audit_block6m5_af.py`: encadena y certifica internamente A→F.
- `src/gli_api/simulation_service.py`: adaptador/orquestador de API; explícitamente termina en F.
- `src/gli/reference_cases.py` y `validation_reference.py`: caso Santos y referencias digitalizadas; Liao es una comprobación parcial y separada.
- `src/gli/audit_block7a_sensitivities.py` y `audit_block7b_design_matrix.py`: sensibilidad local OAT y matriz de diseño; no son un optimizador.

La ruta de producción usa `scipy.integrate.solve_ivp` con `Radau` en las etapas rígidas. `src/gli/solver.py` contiene RK4, pero no es el integrador que gobierna el encadenamiento productivo A→F. Esto difiere del RK4 anunciado en el perfil de tesis y debe justificarse metodológicamente como una decisión para un sistema híbrido rígido, no ocultarse.

### API y persistencia

FastAPI expone salud, alcance físico, casos de referencia, simulación, timeline, eventos, series, escenarios, validación y persistencia. La persistencia admite SQLite/MySQL. `simulation_service.build_parameters()` mezcla entradas de usuario con valores por defecto para casing, áreas de válvulas y temperaturas; por ello la API todavía no recibe una definición completa y trazable de pozo.

### Frontend

- `src/services/simulationApi.ts`: cliente de la API.
- `src/models/Simulation/index.ts`: tipos limitados a A_B…E_F y terminal F.
- `src/pages/Simulation/index.tsx`: orquestación de formulario, simulación, guardado y vistas.
- Vistas: dashboard, timeline, charts, scenarios, diagnostics, units, certification y data.
- Componentes de gráficas basados en Recharts.

La UI está bien organizada para visualizar el resultado existente, pero contiene textos que llaman “ciclo completo” y “certificado” a un alcance A→F. Lugares principales: `src/pages/Simulation/constants.ts`, `SimulationFormView.tsx`, `ChartsView.tsx`, `DashboardView.tsx`, `helpers.ts` y mensajes de `index.tsx`. No se corrigieron en esta auditoría.

## 3. Entornos reproducidos

### Backend

El README menciona `.venv`, pero esa carpeta no existe. El entorno reproducible disponible es Conda `gli311`:

- Python 3.11.15; pip 26.1.2.
- FastAPI 0.139.0; Pydantic 2.13.4; Uvicorn 0.51.0.
- NumPy 2.4.6; SciPy 1.17.1; pandas 3.0.3; Matplotlib 3.11.0.
- pytest 9.1.1; PyMySQL 1.2.0; python-dotenv 1.2.2.

Solo existe `requirements.txt` y sus dependencias no están fijadas. No hay `pyproject.toml`, lockfile, Pipfile ni lock de uv. Desde la raíz, `python -m pytest -ra` produjo 30 errores de importación y no recolectó pruebas porque el layout `src` no está configurado. Con `PYTHONPATH=src`, se recolectaron y aprobaron **135/135 pruebas** en 211.35 s. La primera falla es un defecto de configuración reproducible, no una falla del modelo.

### Frontend

- Node 18.2.0; npm 8.9.0; lockfile npm v2.
- React/React DOM 18.3.1; TypeScript 6.0.3; Vite 5.4.21; plugin React 4.7.0; Recharts 3.8.1.
- `npm run typecheck`: aprobado.
- `npm run build`: aprobado, 2204 módulos; bundle JS 638.11 kB (gzip 190.65 kB), con advertencia de chunk mayor a 500 kB.
- Pruebas frontend: no aplicable; no hay script de test.
- Lint: no aplicable; no hay script de lint.

## 4. Ejecución base A→F

Caso Santos 50/70/80, ruta corregida, `max_step=0.5 s`:

| Evento | Tiempo [s] | Significado |
|---|---:|---|
| A | 0.000000 | apertura de válvula motora/inicio inyección |
| B | 32.640156 | apertura de GLV |
| C | 59.509203 | superficie superior del tapón llega a superficie |
| D | 502.602577 | inicio de producción del tapón |
| E | 526.409286 | superficie inferior del tapón llega a superficie |
| F | 526.778244 | velocidad media de película retorna a cero |

Duraciones: A–B 32.6402 s; B–C 26.8690 s; C–D 443.0934 s; D–E 23.8067 s; E–F 0.3690 s.

Resultados seleccionados:

- Gas estándar inyectado al llegar a C: 129.837 m³ std.
- Volumen líquido producido acumulado en F: 0.520137 m³.
- Volumen de película en F: 0.758962 m³.
- Espesor de película en F: 3.457 mm.
- Presión de tubing superior en F: 4.9017 MPa.
- Máximo residuo normalizado reportado: `3.37e-14`.
- Residuos relativos de balances por etapa entre `0` y `1.26e-8` (salvo A–B gas `7.91e-7`).

La cadena satisface sus contratos numéricos internos y las 135 pruebas. Sin embargo, en D–E aparecen velocidades pico aproximadas de 69.35 m/s para líquido, 71.33 m/s para burbuja y 63.55 m/s para película. Esas magnitudes exigen revisión de plausibilidad física, unidades, pérdidas y correlaciones antes de hablar de validación de campo. El caso base además reporta fallback acumulado cero hasta F: la devolución de película al fondo pertenece precisamente a F→G, tramo ausente.

**Conclusión de lenguaje:** “reproducción interna A–F” o “contrato numérico A–F aprobado” son expresiones defendibles. “Modelo físico validado”, “ciclo completo” y “certificado” no lo son todavía.

## 5. Problema de IPR/afluencia

`gli_api/simulation_service.py::reservoir_liquid_rate()` calcula un caudal constante con `PI × (presión estática de reservorio − presión de tubing en superficie)`. El caso base hace lo equivalente con 85.2 y 7.0 kgf/cm².

El potencial de afluencia debe responder a la presión fluyente de fondo en perforaciones, no a la presión superficial. La forma lineal mínima coherente es:

`q_res(t) = max(0, PI · [P_res − P_wf(t)])`

con unidades consistentes y `P_wf(t)` obtenido del estado dinámico a profundidad de perforaciones. También puede usarse una IPR no lineal si la fuente o los datos lo justifican. El número exacto de una ecuación constitutiva IPR de Santos no quedó identificado en el material extraído: **SOURCE_MISSING** para esa cita puntual. La presión de reservorio, el índice de productividad, la variable `q_res` en balances y la presión de fondo sí están documentados.

## 6. Sensibilidad y optimización actuales

La sensibilidad existente es útil como diagnóstico local:

- OAT: presión de inyección, longitud del tapón, profundidad de válvula, diámetro de tubing, BSW y API.
- Matriz de diseño: combinaciones seleccionadas de esos factores.

No cubre aún dos variables centrales de Santos: volumen de gas inyectado por ciclo y diámetro/asiento de GLV; tampoco explora de forma explícita `Pto/Pvo`. No existe un problema de optimización, restricciones, función objetivo, estimación de costos ni algoritmo de Differential Evolution implementado.

## 7. Vercel, API y variables de entorno

No hay `vercel.json` ni workflows/configuración de rama de Vercel versionados. Que `test` controle el despliegue es una configuración externa del proyecto Vercel y no se pudo verificar desde Git.

`.env.example` está versionado y `.env` está ignorado. Se detectaron nombres de variables, sin exponer valores: `VITE_REACT_APP_BACKEND_URL`, `VITE_REACT_APP_API_DEBUG`, variables Cognito, licencia MUI, puertos y opciones Docker. El cliente prioriza `VITE_REACT_APP_BACKEND_URL`, luego el alias no documentado `VITE_BACKEND_URL`, y finalmente `http://127.0.0.1:8000`; README y ejemplo usan puerto 8008. Debe eliminarse esa divergencia antes de desplegar.

El backend permite CORS para `https://gli-simulator.vercel.app` y localhost mediante lista codificada. Conviene migrar a orígenes permitidos configurables por entorno. Los endpoints frontend usan el prefijo `/api` y son compatibles con las rutas actuales.

## 8. Dictamen

El repositorio ofrece una base A→F técnicamente seria: módulos por etapa, eventos, balances, diagnósticos de rigidez, API, UI y cobertura de pruebas considerable. Su principal riesgo no es “que nada funcione”, sino confundir una reproducción interna parcial con un ciclo GLI estabilizado y validado. La secuencia correcta es terminar F→G y G→H conservando masa y continuidad; validar H→A y ciclos sucesivos; después construir datos, métricas, calibración, validación independiente y, al final, optimización.
