# Contrato API–frontend — trayectoria parcial M1.7

Estado vigente desde Milestone 1.7. No requiere cambios de código frontend,
pero corrige la semántica científica publicada por el backend.

- Backend local: `http://localhost:8000`.
- Frontend Vite permitido por CORS: `http://localhost:5173`.
- Caso: `caseId="santos-gli-50-70-80"`.
- Estado físico: `NOT_SOURCE_CERTIFIED_A_TO_E`.
- Evento terminal del caso base: `GLV_CLOSE_BEFORE_E_SOURCE_BLOCK`.
- `validationLevel`: `failed` en una simulación; `provisional` en el endpoint
  estático de alcance.

La trayectoria cierra GLV materialmente antes de E y falta una transición
fuente compatible. También se detectó un proxy GLV heredado de Stage 2.
No se publica E por cierre de válvula ni se fabrican estados E/F/G.

## Endpoints

| Método | Ruta | Uso |
|---|---|---|
| `GET` | `/api/health` | Conectividad. |
| `GET` | `/api/physical-scope` | Alcance, evento terminal y limitaciones. |
| `GET` | `/api/reference-cases` | Casos y clasificación bibliográfica. |
| `POST` | `/api/simulations` | Ejecutar y persistir la trayectoria parcial y su bloqueo. |
| `GET` | `/api/simulations/{id}` | Recuperar simulación. |
| `GET` | `/api/simulations/{id}/timeline?interval_s=2.0` | Timeline hasta el terminal realmente reportado. |

Los alias sin `/api` permanecen por compatibilidad.

## Respuesta vigente

Extracto de metadatos; `points` y las demás propiedades se omiten en este
extracto. La respuesta real contiene una serie no vacía.

```json
{
  "validationLevel": "failed",
  "terminalEvent": "GLV_CLOSE_BEFORE_E_SOURCE_BLOCK",
  "caseId": "santos-gli-50-70-80",
  "physicalScope": "NOT_SOURCE_CERTIFIED_A_TO_E: SOURCE_AMBIGUITY_GLV_CLOSE_BEFORE_E; E/F/G/H are not manufactured."
}
```

El último punto cumple `stage="D_E"` y `t=metrics.duration`. Esto significa
tramo de producción parcial, NO evento E ni duración de ciclo A→H.

Stages publicados:

1. `A_B`
2. `B_C`
3. `C_D`
4. `D_E`

Eventos publicados:

1. `A_INITIAL_STATE`
2. `B_GAS_LIFT_VALVE_OPENS`
3. `C_MOTOR_VALVE_CLOSES`
4. `D_SLUG_TOP_REACHED_SURFACE`
5. `GLV_CLOSE_BEFORE_E_SOURCE_BLOCK`

El último elemento de la serie remuestreada tiene:

```json
{
  "stage": "D_E",
  "exactEvent": "GLV_CLOSE_BEFORE_E_SOURCE_BLOCK"
}
```

## Fixture histórico

`docs/api/examples/santos_a_f_certified_response.json` queda congelado como
snapshot de Milestone 1.5 para detectar cambios numéricos y construir la tabla
comparativa. Ya no representa la respuesta vigente ni una certificación de
fuente. No debe usarse como contrato actual del frontend.

## Limitaciones

- Las pruebas numéricas anteriores no certifican la correlación fuente GLV.
- Stage 4.2 tiene RHS exacto y pruebas de residuos, pero el caso base no puede
  inicializarlo por identidad.
- F→G requiere `h_l(F)`, `P_t1(F)`, `P_t3(F)`, densidad media, masa gaseosa y
  `V_lower(F)` explícitos; no reconstruye espacio desde ledgers.
- No se implementó G→H ni se modificó el frontend.

## Métricas de ciclo incompleto

El esquema ya permite `EngineeringMetric.value=null`; no cambia su estructura.
`cyclesPerDay`, `estimatedDailyLiquid` y `estimatedDailyInjectedGas` retornan
`null`, con certificación `UNAVAILABLE_INCOMPLETE_CYCLE`. No se calcula
`86400/metrics.duration`. La comparación de escenarios suprime además métricas
diarias numéricas antiguas si no existe H o la simulación está fallida.
`deltaDailyLiquidPercent` queda nulo; no hay recomendación de producción diaria.

Las claves históricas `producedLiquidPerCycle` e `injectedGasPerCycle` se
conservan por compatibilidad, pero sus etiquetas, unidades y certificación
indican acumulados del TRAMO PARCIAL, no resultados por ciclo. Sus unidades son
`m3` y `std m3`; las restantes razones son diagnósticas parciales, no de diseño.
