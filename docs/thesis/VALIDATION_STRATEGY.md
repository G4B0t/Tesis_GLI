# Estrategia de verificación, calibración y validación

## 1. Separación obligatoria de evidencias

| Capa | Pregunta | Evidencia actual | Etiqueta permitida |
|---|---|---|---|
| Verificación numérica | ¿El código resuelve las ecuaciones declaradas? | residuos, balances, eventos, refinamiento, 135 pruebas | `numerically_verified(scope=AF)` |
| Reproducción de referencia | ¿Reproduce resultados publicados con su caso? | Santos; Liao parcial y guardado | `reference_reproduction` |
| Calibración | ¿Qué parámetros se estimaron con datos designados? | no existe | ninguna |
| Validación independiente | ¿Predice datos no usados para ajustar? | no existe | ninguna |

No mezclar estas etiquetas. Una prueba unitaria o coincidencia con el mismo caso usado para coeficientes no es validación independiente.

## 2. Capability levels y comparaciones permitidas

- Nivel A dynamic: presión/caudal vs tiempo, tiempos de eventos, fases y trayectoria.
- Nivel B cycle: duración, gas/ciclo, líquido/ciclo, fallback, presiones extremas.
- Nivel C aggregate: producción e inyección por día, ciclos/día y eficiencia agregada.

Cada reporte debe mostrar nivel, cobertura, variables disponibles, porcentaje de datos válidos y transformaciones. Si falta timestamp o sincronía entre sensores, no interpolar una validación dinámica ficticia.

## 3. Alineación temporal

Modos explícitos:

1. `CLOCK`: timestamps absolutos, solo con relojes sincronizados.
2. `CYCLE_START`: tiempo relativo al inicio observado.
3. `EVENT_WARP`: alinea eventos homólogos; útil para forma de etapa, pero debe reportarse aparte porque elimina error de timing.

Reglas:

- convertir unidades y timezone antes de alinear;
- no extrapolar fuera del solapamiento;
- interpolar la simulación sobre timestamps observados, no “rellenar” mediciones;
- declarar método (lineal/retención) según variable;
- definir `max_gap`; segmentos mayores quedan faltantes;
- reportar métricas de magnitud y error de eventos por separado.

## 4. Métricas

Para pares válidos `s_i`, `o_i`:

- `MAE = mean(|s_i-o_i|)`
- `RMSE = sqrt(mean((s_i-o_i)^2))`
- `MAPE = 100 mean(|(s_i-o_i)/o_i|)` solo cuando `|o_i| >= epsilon`
- `NRMSE = RMSE / scale_obs`

MAPE debe devolver valor + cantidad/porcentaje omitido; nunca dividir por cero ni añadir un epsilon oculto. Para variables que cruzan cero, preferir MAE/RMSE y opcionalmente sMAPE documentado.

La normalización de NRMSE (rango, media absoluta o desviación estándar) debe seleccionarse por variable y quedar en el reporte. Si la escala es cero, NRMSE es indefinido y se informa. Incluir sesgo medio, error relativo de tiempos de eventos y error de balances como diagnósticos complementarios.

## 5. Diseño experimental

### Reproducción Santos

- congelar commit, fuente, parámetros y digitalización;
- ejecutar A→H y multiciclo cuando existan;
- comparar tablas/eventos y curvas con incertidumbre de digitalización;
- no usar esta capa como independencia si el modelo/coeficientes provienen de Santos.

### Calibración

- reservar campañas/ciclos explícitos;
- guardar manifest del dataset y objetivo;
- estimar solo parámetros declarados;
- congelar `calibration_id`, vector, bounds, seed y commit.

### Validación independiente

- usar otro periodo, condición operacional o pozo no empleado en calibración;
- no reajustar tras mirar el resultado;
- reportar todos los casos, incluidos fallos/no convergencias;
- estratificar por BSW, presión, inyección y dominio de calibración.

Si solo hay un dataset pequeño, usar partición temporal o leave-one-cycle/campaign-out, declarando que no equivale a validación externa entre pozos.

## 6. Umbrales

La fuente/perfil exige RMSE/MAPE pero no define umbrales universales de aprobación por variable: **SOURCE_MISSING**. No inventarlos. Presentar intervalos, error instrumental y baseline simple. Los umbrales deben justificarse con resolución de sensores, relevancia operacional y acuerdo metodológico previo.

## 7. Implementación propuesta

Archivos futuros:

- `src/gli_validation/capability.py`
- `src/gli_validation/alignment.py`
- `src/gli_validation/metrics.py`
- `src/gli_validation/experiment.py`
- `src/gli_validation/report.py`
- `tests/validation/test_metrics.py`
- `tests/validation/test_alignment.py`
- `tests/validation/test_data_separation.py`

Un `ValidationReport` debe incluir commit, parámetros, dataset hash, capability, ventanas, máscaras, métricas con unidades, gráficos, warnings y etiqueta de evidencia.

## 8. Pruebas obligatorias

- MAE/RMSE con valores conocidos;
- MAPE con ceros/casi ceros y conteo de exclusión;
- NRMSE con escala nula;
- NaN/missing y `max_gap`;
- ausencia de extrapolación;
- alineación por reloj vs evento claramente distinguible;
- detección de leakage entre calibración y validación;
- invariancia de unidades;
- reporte que no permite etiqueta superior a su capability/evidencia.
