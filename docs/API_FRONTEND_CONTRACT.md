# API frontend contract — GLI A→F certificado

Estado congelado para consumo del frontend Vite.

- Backend base URL local: `http://localhost:8000`
- Frontend Vite permitido por CORS: `http://localhost:5173`
- Caso certificado: `caseId="santos-gli-50-70-80"`
- Alcance físico público: `A_TO_F certified`
- Evento terminal público: `F_FILM_VELOCITY_ZERO`
- `validationLevel`: `certified`

No se deben comparar cuantitativamente resultados del caso Santos con el benchmark parcial de Liao Table 5.14.

## Endpoints obligatorios

| Método | Ruta | Uso frontend |
|---|---|---|
| `GET` | `/api/health` | Verificar conexión backend. |
| `GET` | `/api/physical-scope` | Mostrar alcance físico, stages certificados, eventos y limitaciones. |
| `GET` | `/api/reference-cases` | Listar casos disponibles y clasificación de referencia. |
| `POST` | `/api/simulations` | Ejecutar y persistir simulación A→F certificada. |
| `GET` | `/api/simulations/{id}` | Recuperar una simulación persistida. |
| `GET` | `/api/simulations/{id}/timeline?interval_s=2.0` | Recuperar timeline nativo + serie remuestreada. |

Los endpoints antiguos sin prefijo `/api` se mantienen como alias de compatibilidad, pero el frontend debe consumir las rutas `/api/...`.

## Payload mínimo para `POST /api/simulations`

```json
{
  "tubingDiameter": 0.050673,
  "valveDepth": 1480.0,
  "slugLength": 412.5,
  "surfaceTubingPressure": 0.788,
  "injectionPressure": 6.966,
  "api": 40.0,
  "bsw": 50.0,
  "gasRelativeDensity": 0.7,
  "casingPressureOpenRatio": 0.7,
  "projectName": "Santos A-F Certified",
  "projectistName": "Frontend"
}
```

Campos opcionales relevantes:

- `caseId`: por defecto `santos-gli-50-70-80`.
- `waterRelativeDensity`: por defecto `1.07`.
- `surfaceTemperature`: por defecto `80.0` °F.
- `injectedGasReferenceRatio`: por defecto `0.8`.
- `tubingRoughness`, `roughnessSource`, `glvMode`, `glvOpeningPressure`, `glvClosingPressure`, `glvParameterSource`: parámetros explícitos de cierre/documentación.

## Respuesta de simulación

Archivo fixture real:

- `docs/api/examples/santos_a_f_certified_response.json`

Campos de alto nivel garantizados:

```json
{
  "simulationId": 1,
  "validationLevel": "certified",
  "terminalEvent": "F_FILM_VELOCITY_ZERO",
  "caseId": "santos-gli-50-70-80",
  "referenceClassification": "full_case",
  "physicalScope": "A_TO_F certified: ...",
  "metrics": {
    "duration": 527.5042526566479
  },
  "points": []
}
```

`points` es una serie nativa adaptativa concatenada por etapas. El último punto debe cumplir:

- `stage = "E_F"`
- `t = metrics.duration`
- `abs(slugVelocity) < 1e-6`
- `terminalEvent = "F_FILM_VELOCITY_ZERO"` en el objeto de simulación.

## Stages y eventos

Stages públicos, en orden:

1. `A_B`
2. `B_C`
3. `C_D`
4. `D_E`
5. `E_F`

Eventos públicos, en orden:

1. `A_INITIAL_STATE`
2. `B_GAS_LIFT_VALVE_OPENS`
3. `C_MOTOR_VALVE_CLOSES`
4. `D_SLUG_TOP_REACHED_SURFACE`
5. `E_SLUG_BASE_REACHED_SURFACE`
6. `F_FILM_VELOCITY_ZERO`

## Timeline

`GET /api/simulations/{id}/timeline?interval_s=2.0` retorna:

- `nativeSamples`: puntos nativos de la simulación.
- `events`: eventos exactos A→F.
- `segments`: rangos contiguos por stage.
- `resampledSeries`: serie remuestreada para animación web.
- `resampleInterval`: intervalo usado.
- `adaptiveSolverOutputAvailable`: actualmente `false`.

El último elemento de `resampledSeries` debe tener:

```json
{
  "stage": "E_F",
  "exactEvent": "F_FILM_VELOCITY_ZERO"
}
```

## Magnitudes por punto

Cada `SimulationPoint` expone, según etapa:

- `t`: tiempo absoluto [s].
- `pressure`: presión principal [MPa].
- `force`: fuerza diagnóstica [N].
- `gasRate`: caudal de gas de etapa.
- `stage`: `A_B`, `B_C`, `C_D`, `D_E` o `E_F`.
- `annulusPressure`, `bubblePressure`, `bottomPressure`: presiones [MPa].
- `slugTop`, `slugBase`: posiciones [m].
- `filmThickness`: espesor de película [m].
- `bubbleVelocity`, `slugVelocity`: velocidades [m/s].
- `fallbackVolume`, `producedVolume`, `slugVolume`, `filmVolume`: volúmenes [m³].
- `liquidRate`: caudal líquido [m³/s].
- `gasLiftValveOpen`: estado GLV.

Los campos que no aplican a una etapa pueden ser `null`.

## Alcance físico y limitaciones

`GET /api/physical-scope` es la fuente frontend para texto de alcance. El bloque certificado declara:

- B→C: `santos_compatible`.
- C→D: `santos_corrected`.
- D→E: `santos_corrected`.
- E→F: `santos_corrected`.
- Transferencias de estado por identidad.
- Ledgers acumulados de producido/fallback.
- Balances independientes gas/líquido cerrados bajo tolerancia.

Limitaciones visibles:

- Certificado solo para `caseId="santos-gli-50-70-80"` y el set actual de cierres explícitos Santos/Churchill.
- Liao Table 5.14 permanece como benchmark parcial.
- En E→F, entrainment queda representado por el cierre auditado de no intercambio de masa de etapa 4.

