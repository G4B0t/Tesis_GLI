# Estrategia de calibración

La calibración debe comenzar solo después de A→H, balances y modelo de afluencia. Ajustar ahora podría compensar físicamente etapas ausentes mediante coeficientes no identificables.

## 1. Clasificación de parámetros

| Clase | Ejemplos | Tratamiento |
|---|---|---|
| Medidos | profundidades, diámetros, presión estática, presiones operativas, BSW/API | fijar con incertidumbre; no “calibrar” salvo análisis explícito de error |
| Fuente-definidos | caso Santos, correlaciones elegidas, gravedad específica | fijar para reproducción; cambio crea otro experimento/modelo |
| Empíricos | fricción/roughness, descarga superficial, velocidad de burbuja, pérdidas locales | candidatos si los datos observan su efecto |
| Instalación desconocida | áreas efectivas/Cd/Cv de GLV y válvula motora | medir/datasheet primero; calibrar solo con bounds físicos trazables |
| Estado inicial | presiones/inventarios al iniciar campaña | estimar por asimilación/ventana de warm-up, no confundir con propiedad del pozo |

No calibrar temperaturas/EOS para ocultar errores de masa, ni geometría conocida para corregir una IPR equivocada.

## 2. Parámetros candidatos por prioridad

### Grupo 1 — pérdidas y descarga

- rugosidad efectiva de tubing;
- coeficiente de descarga/pérdida superficial;
- coeficiente de descarga de GLV/motor si no se mide.

El código E→F ya usa rangos internos aproximados de rugosidad `1e-6…2e-4 m` y `Cd` superficial `0.75…0.95`; son candidatos iniciales de ingeniería, no bounds universales. Debe citarse su origen o marcarlos `ASSUMED`.

### Grupo 2 — cierres multifásicos

- coeficiente de velocidad de burbuja;
- factor de película/arrastre si la formulación lo expone;
- pérdidas adicionales justificadas por la instalación.

El coeficiente actual cercano a 1.025 pertenece a la formulación/caso y debe permanecer fijo en reproducción Santos. Solo puede estimarse en un experimento de calibración independiente con observables suficientes.

### Grupo 3 — reservorio

- PI o parámetros IPR, únicamente con `P_wf` y caudal medidos;
- presión estática dentro de su incertidumbre y periodo de vigencia.

Una PI estimada contra presión superficial carece de interpretación física.

Para áreas efectivas, Cv, temperaturas internas y otros defaults no hay bounds documentados suficientes: **SOURCE_MISSING**. No inventarlos; obtener datasheet/medición o ejecutar análisis de incertidumbre claramente etiquetado.

## 3. Observables y función objetivo

Construir residuales por bloques disponibles:

- señales dinámicas: presiones tubing/casing/fondo, caudales;
- tiempos de eventos A…H;
- totales por ciclo: líquido, gas, duración, fallback;
- varios puntos operacionales/ciclos, no una única corrida.

Objetivo recomendado:

`J(theta) = sum_k w_k · loss(r_k / sigma_k) + lambda · regularization(theta)`

`sigma_k` debe ser incertidumbre instrumental o escala predefinida; evita que una variable con números grandes domine. Usar pérdida cuadrática o robusta como elección documentada. Los balances y restricciones físicas deben ser constraints/penalizaciones separadas, no observaciones que el optimizador pueda intercambiar libremente.

## 4. Identificabilidad

Antes de optimizar:

- sensibilidad local escalada y matriz de correlación;
- perfiles de objetivo por parámetro;
- recuperación con datos sintéticos (solo verificación);
- condición/rango de Jacobiano cuando sea aplicable;
- reducir o fijar parámetros altamente correlacionados;
- verificar que cada parámetro afecte un observable disponible.

Reportar intervalos por bootstrap/perfiles o ensamble de soluciones, no solo el mejor vector.

## 5. Algoritmo y reproducibilidad

El simulador es híbrido, con eventos y posibles discontinuidades; Differential Evolution es razonable para búsqueda global acotada. También es costoso y estocástico. Requisitos:

- seed fija y registrada;
- bounds y transformación (lineal/log) versionados;
- misma tolerancia de solver en todas las evaluaciones;
- penalización explícita de no convergencia/dominio inválido;
- checkpoint y cache por hash de parámetros;
- múltiples seeds para evaluar robustez;
- refinamiento local opcional solo tras hallar una cuenca estable.

## 6. Separación de datos

1. Elegir conjunto de calibración antes de ejecutar.
2. Reservar validación temporal/operacional/otro pozo.
3. Guardar hashes y manifiesto.
4. Estimar parámetros.
5. Congelar un `CalibrationArtifact` con commit, fuente, objetivo, bounds, seed, métricas y covarianza/ensamble.
6. Evaluar validación sin reajustar.

Si se cambia una ecuación o clasificación de dato, crear una calibración nueva; no sobrescribir el artefacto anterior.

## 7. Criterios de aceptación

- balances dentro de tolerancia independiente del objetivo;
- solución interior o explicación física para bounds activos;
- parámetros plausibles y trazables;
- recuperación sintética razonable;
- estabilidad entre seeds/submuestras;
- mejora sobre baseline en calibración y desempeño reportado en validación;
- ausencia de degradación sistemática por condición operacional.

Los umbrales cuantitativos requieren incertidumbres y acuerdo de tesis: **SOURCE_MISSING**.

## 8. Archivos futuros

- `src/gli_calibration/parameters.py`
- `src/gli_calibration/objective.py`
- `src/gli_calibration/runner.py`
- `src/gli_calibration/artifact.py`
- `tests/calibration/test_synthetic_recovery.py`
- `tests/calibration/test_parameter_freeze.py`
- `tests/calibration/test_no_validation_leakage.py`

Mantener esta capa fuera de `src/gli` para que la física sea determinista y no dependa de un optimizador.
