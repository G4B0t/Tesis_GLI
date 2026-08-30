# Plan técnico para completar A→H y ciclos estabilizados

Principio rector: preservar contratos verificables, permitir correcciones científicas trazadas en A→F y no exponer un “ciclo completo” hasta que A→H supere continuidad, conservación y plausibilidad.

## Arquitectura objetivo mínima

```text
WellDefinition -> adapter SI -> GLIParameters
                              |
                              v
AB -> BC -> CD -> DE -> EF -> FG -> GH = CycleResult
 ^                                      |
 |------------- H_to_next_A ------------|
                 |
                 v
simulate_cycles / simulate_until_stabilized
```

Cada `StageResult` debe contener tiempo, matriz de estado, muestras derivadas, evento terminal, diagnóstico de solver y un ledger de masa/volumen. `CycleResult` concatena sin duplicar fronteras y conserva resultados por etapa.

## Hito 1 — F→G, descompresión fase III — SUPERADO POR HITO 1.5

### Archivos creados

- `src/gli/stage_fg_dynamic.py`
- `src/gli/audit_stage_fg.py`
- `tests/test_stage_fg_dynamic.py`
- `tests/test_audit_stage_fg.py`

### Archivos modificados

- `src/gli/events.py`: residual firmado e identificador de G.
- `src/gli/stage_ef_dynamic.py`: ledger derivado `q_res·t`, sin cambiar la integración A→F.
- `docs/thesis/SANTOS_TRACEABILITY_MATRIX.md` y este documento.

No fue necesario modificar `extended_continuity.py`: la continuidad específica F→G vive en `stage_fg_dynamic.py` y su auditoría, evitando ampliar el contrato público A→F.

### Estado, algebraicas e interfaces implementadas

- Estado: `rho_gt3`, `P_t3`, `P_t1`, `h_l`, `y`, más ledgers de retorno, reservorio y gas descargado.
- Algebraicas: `q_f`, `v_gs`, `v_g`, densidad inferior por EOS, áreas, presión de fondo, fricción y `q_res(P_wf)`.
- Entrada: `GLIParameters` + estado terminal F tipado.
- Salida: resultado F→G y estado terminal G.

### Pruebas de aceptación ejecutadas

- Derivadas finitas y sin NaN dentro del dominio.
- Evento G ocurre en dirección física y no en `t=0` por tolerancia mal planteada.
- Continuidad exacta en F para estados e inventarios.
- Residuo de 4.1.94, 4.1.97, 4.1.107 y cierre EOS escalado.
- Conservación gas/líquido bajo refinamiento de tolerancia y `max_step`.
- Prueba de degeneraciones: película pequeña, afluencia cero, proximidad de área singular.
- No regresión: suite A→F idéntica.

Configuración aprobada: `solve_ivp(method="Radau")`, `rtol=1e-8`, `atol=1e-10`, `max_step=0.5 s`, horizonte de seguridad 1200 s. Evento G terminal, dirección `−1`. Una corrida estricta (`rtol=1e-9`, `atol=1e-11`, `max_step=0.25 s`) reprodujo tiempo y estados terminales con diferencias relativas del orden de 1e-12.

Las conclusiones antiguas de raíz G y `q_res` constante quedan reemplazadas por el Hito 1.5.

## Hito 1.5 — reconciliación pre-G→H — IMPLEMENTADO / NOT_READY_FOR_GH

- Mapa de presiones creado antes de editar ecuaciones.
- IPR lineal dinámica en SI conectada a B→G donde corresponde.
- Caudal negativo sin clipping, con clasificación explícita.
- Evento G reemplazado por el residual de momento de 4.1.98–4.1.102.
- Evento histórico conservado como diagnóstico no terminal.
- Experimento de 10,000 s: una raíz legacy y ninguna raíz corregida.
- La transformación espacial F produce flujo inverso inválido durante 32.737 s.
- A→F conserva sus contratos; F→G conserva masa, pero no alcanza una frontera G admisible.

Gate: no comenzar Hito 2 hasta resolver conjuntamente la representación espacial E→F/F, la presión `P_t1/P_wb` y la existencia de una raíz G finita sin calibración artificial.

## Hito 2 — G→H, alimentación

### Archivos exactos a crear

- `src/gli/stage_gh_dynamic.py`
- `src/gli/audit_stage_gh.py`
- `tests/test_stage_gh_dynamic.py`
- `tests/test_audit_stage_gh.py`

### Archivos exactos a modificar

- `src/gli/events.py`: agregar evento `liquid_column_back_to_initial_length`.
- `src/gli/extended_continuity.py`: transferencia G→H y cierre del ledger del ciclo.

### Estado e interfaces

- Estado mínimo: `y`, `h_l`, `P_t1`, con masa/volumen conservativo y algebraicas.
- Ecuaciones obligatorias: 4.1.94, 4.1.95, 4.1.107, 4.1.109.
- `q_res` evaluado con presión dinámica en perforaciones.
- Evento H: `h_l = L_initial`, cruce creciente.

### Pruebas de aceptación

- Continuidad en G sin reinicialización.
- `h_l` crece por suma consistente de formación + película.
- Disminución de inventario de película compatible con aumento de columna.
- Conservación integral de líquido.
- Evento H robusto a refinamiento.
- Estado terminal listo para siguiente ciclo.
- Suite A→G sin regresiones.

## Hito 3 — orquestación A→H

### Archivos a crear

- `src/gli/cycle_simulation.py`
- `src/gli/cycle_state.py`
- `src/gli/audit_cycle_ah.py`
- `tests/test_cycle_ah.py`
- `tests/test_cycle_mass_balance.py`

### Archivos a modificar

- `src/gli/simulation.py`: delegar al nuevo orquestador preservando compatibilidad A→F.
- `src/gli_api/simulation_service.py`: opción explícita de alcance `AF`/`AH`; no cambiar default hasta aprobar A→H.
- `src/gli_api/schemas.py`: etapas FG/GH, evento G/H y diagnósticos.
- `src/gli_api/main.py`: alcance físico honesto.
- pruebas API y de serialización correspondientes.

API interna propuesta:

- `simulate_cycle(parameters, initial_cycle_state, options) -> CycleResult`
- `transfer_h_to_next_a(cycle_result) -> CycleState`
- `simulate_cycles(parameters, initial_state, n_cycles, options) -> MultiCycleResult`
- `simulate_until_stabilized(parameters, initial_state, criterion, max_cycles) -> MultiCycleResult`

## Hito 4 — H→A y régimen estabilizado

### Archivos a crear

- `src/gli/multicycle.py`
- `src/gli/stabilization.py`
- `tests/test_h_to_a_continuity.py`
- `tests/test_multicycle_convergence.py`
- `tests/test_stabilization_criterion.py`

### Transferencia física

Persistir película residual, columna inferior, presiones/densidades, masas de gas y configuración de válvulas. El cambio de control H→A abre la válvula motora para el siguiente ciclo, pero no restablece el pozo al estado del primer ciclo. Separar totales globales de contadores por ciclo.

### Criterio de estabilización

Santos: volumen producido por ciclo ≈ volumen aportado por el reservorio durante el ciclo. Complementar con convergencia del tiempo de ciclo y del estado terminal. La tolerancia, norma y número de ciclos consecutivos son **SOURCE_MISSING**; deben ser parámetros versionados y aprobados, con análisis de sensibilidad.

Pruebas:

- Conservación H(n)→A(n+1).
- Tiempo estrictamente creciente y fronteras no duplicadas.
- Ningún ledger reiniciado indebidamente.
- Convergencia sintética controlada y caso que no converge antes de `max_cycles`.
- Invarianza razonable ante tolerancias del solver.
- Comparación con Figuras 6.7–6.9 sin llamarla validación independiente.

## Hito 5 — plausibilidad y certificación de alcance

Antes de habilitar A→H como default:

- Revisar velocidades extremas D–E y sensibilidad a pérdidas/áreas.
- Verificar unidades de gas estándar vs in situ.
- Auditar IPR y presión de fondo.
- Ejecutar refinamiento temporal por etapa.
- Reportar balances absolutos y relativos con escalas físicas.
- Establecer dominio de aplicación y fallos explícitos.

Renombrar “certified” por `verified_scope` o `numerical_contract_passed`. Una certificación debe identificar alcance (`AF`, `AH`, multiciclo), commit, parámetros, tolerancias, pruebas y fuentes.

## Hito 6 — integración frontend, solo después

Modificar tipos, timeline, textos y vistas para G/H, ciclos y estabilización. Corregir “ciclo completo” en el alcance A→F; añadir badges separados para reproducción, calibración y validación. Este hito no debe anticiparse con datos falsos o etapas vacías.

## Estrategia de compatibilidad

- Mantener funciones y resultados A→F existentes.
- Nuevas etapas en módulos nuevos.
- Feature flag/alcance explícito en API.
- Fixtures doradas A→F para detectar drift numérico.
- No cambiar coeficientes existentes para “hacer pasar” F/G/H.
- Todo cambio de ecuación requiere trazabilidad Santos, prueba y nota metodológica.
