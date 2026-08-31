# Contrato API–frontend — alcance fuente hasta E

Estado vigente desde Milestone 1.6. No requiere cambios de código frontend,
pero corrige la semántica científica publicada por el backend.

- Backend local: `http://localhost:8000`.
- Frontend Vite permitido por CORS: `http://localhost:5173`.
- Caso: `caseId="santos-gli-50-70-80"`.
- Estado físico: `NOT_SOURCE_CERTIFIED_A_TO_F`.
- Evento terminal publicado: `E_SLUG_BASE_REACHED_SURFACE`.
- `validationLevel`: `failed` en una simulación; `provisional` en el endpoint
  estático de alcance.

La causa es la incompatibilidad del estado gaseoso terminal D→E con Santos
4.1.83/.88/.90. El backend no publica puntos E→F construidos mediante
proyección.

## Endpoints

| Método | Ruta | Uso |
|---|---|---|
| `GET` | `/api/health` | Conectividad. |
| `GET` | `/api/physical-scope` | Alcance, evento terminal y limitaciones. |
| `GET` | `/api/reference-cases` | Casos y clasificación bibliográfica. |
| `POST` | `/api/simulations` | Ejecutar y persistir la trayectoria fuente hasta E. |
| `GET` | `/api/simulations/{id}` | Recuperar simulación. |
| `GET` | `/api/simulations/{id}/timeline?interval_s=2.0` | Timeline A→E. |

Los alias sin `/api` permanecen por compatibilidad.

## Respuesta vigente

```json
{
  "validationLevel": "failed",
  "terminalEvent": "E_SLUG_BASE_REACHED_SURFACE",
  "caseId": "santos-gli-50-70-80",
  "physicalScope": "NOT_SOURCE_CERTIFIED_A_TO_F: ...",
  "points": []
}
```

El último punto cumple `stage="D_E"` y `t=metrics.duration`.

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
5. `E_SLUG_BASE_REACHED_SURFACE`

El último elemento de la serie remuestreada tiene:

```json
{
  "stage": "D_E",
  "exactEvent": "E_SLUG_BASE_REACHED_SURFACE"
}
```

## Fixture histórico

`docs/api/examples/santos_a_f_certified_response.json` queda congelado como
snapshot de Milestone 1.5 para detectar cambios numéricos y construir la tabla
comparativa. Ya no representa la respuesta vigente ni una certificación de
fuente. No debe usarse como contrato actual del frontend.

## Limitaciones

- B→C, C→D y D→E conservan sus gates numéricos previos.
- Stage 4.2 tiene RHS exacto y pruebas de residuos, pero el caso base no puede
  inicializarlo por identidad.
- F→G requiere `h_l(F)`, `P_t1(F)`, `P_t3(F)`, densidad media, masa gaseosa y
  `V_lower(F)` explícitos; no reconstruye espacio desde ledgers.
- No se implementó G→H ni se modificó el frontend.
