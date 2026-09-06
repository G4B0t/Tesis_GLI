# Milestone 1.7 — diagnóstico técnico de ejecución

## Dictamen

**BLOCKED_BY_SOURCE**. Se ejecutó la reconciliación hasta la condición de
parada autorizada por el prompt; NO se completó físicamente D→E ni A→G.
El tramo disponible conserva el estado D, mantiene transferencia GLV y usa
4.1.53 sin piso de longitud. Cierra GLV con **181.107955 m de golfada remanente**.
No se sustituye ese cierre por E y no se inventa la columna inferior.

Existe además un defecto previo de implementación: el flujo GLV de Stage 2
es un proxy, no la correlación 4.1.13/.15. El resultado no demuestra que el
modelo original de Santos falle: caracteriza la trayectoria con el estado y
los cierres upstream actualmente heredados. Los residuos de conservación que
pasan no convierten esa trayectoria en SOURCE_CERTIFIED_A_TO_E.

La lectura visual directa del PDF, siguiendo el procedimiento de inspección
PDF, fundamentó la separación entre evento físico E y bloqueo de fuente;
no se modificó el PDF ni el Perfil Gabriel Torrejon DOCX.

## 1–4. Baseline, repositorio y ejecución

1. Branch: `feature/gli-thesis-completion`.
2. Commit antes y después: `65b39ceba686dc08a9c825a369f7002e553d534c`.
3. Working tree ANTES de M1.7: limpio. En la continuación solicitada ya
   contenía los cambios de este hito; se preservaron. Sin commit, push, merge
   ni cambio de rama. Sin edición frontend, despliegue, main/test o G→H.
4. Baseline medido, no heredado: **156 collected, 156 passed, 0 failed,
   0 skipped, 185.47 s**. Entorno real: `gli311`, Python 3.11.15, pytest 9.1.1,
   `PYTHONPATH=src`; corrida inicial mediante `conda run -n gli311`.

Log previo: `65b39ce`, `4dc101d`, `51f9876`, `85225c7`, `b31f6be`.
Las advertencias de Git sobre lectura del ignore global y conversión LF/CRLF
no equivalen a fallos de pruebas ni a cambios del estado Git.

## 5–6. Inventario de archivos M1.7

Creado:

- `src/gli/stage_de_santos.py`: sistema Stage 3, continuidad y diagnóstico de bloqueo.
- `src/gli/audit_milestone17.py`: reporte reproducible JSON por stdout.
- `tests/test_stage_de_santos_source.py`: 24 casos nuevos ejecutados.
- `docs/thesis/STAGE_DE_SANTOS_EQUATION_CONTRACT.md`: contrato previo al RHS.
- `docs/thesis/milestone_1_7_results.json`: resultados reproducibles sin redondeo manual.
- `docs/thesis/MILESTONE_1_7_REPORT.md`: este informe.
- `docs/thesis/THESIS_WRITING_MAP.md`: vínculo técnico con futura redacción.

Modificado:

- `src/gli/stage_cd_dynamic.py`, `stage_cd_common.py`: exponer matriz canónica,
  sin modificar las ecuaciones Stage 2.
- `src/gli/stage_de_dynamic.py`: seleccionar ruta nueva; M1.6 queda solo
  como `milestone16_reference`, no como solución científica.
- `src/gli/stage_ef_dynamic.py`: gate con altura/procedencia y memoria explícitas;
  se conservan las siete ecuaciones de Stage 4.2.
- `src/gli/audit_block6m3_de.py`, `audit_block6m4_ef.py`,
  `audit_block6m5_af.py`, `audit_milestone15.py`, `audit_stage_fg.py`:
  auditar el estado disponible, sin sustituir F histórico por F físico.
- `src/gli_api/main.py`, `simulation_service.py`, `scenario_service.py`,
  `timeline_service.py`: alcance, terminal real y métricas de ciclo incompleto.
- `tests/test_api_frontend_contract.py`, `test_api_physical_scope.py`,
  `test_audit_stage_fg.py`, `test_block6m3_de_audit.py`,
  `test_block6m4_ef_audit.py`, `test_block6m5_af_certification.py`,
  `test_block7a_parametric_sensitivity.py`, `test_block7b_design_matrix.py`,
  `test_block7c_api_design_classification.py`, `test_milestone15_diagnostic.py`,
  `test_stage_ef_santos_stage42.py`, `test_timeline_contract.py`.
- `docs/thesis/SANTOS_TRACEABILITY_MATRIX.md`, `IMPLEMENTATION_PLAN_AH.md`,
  `STAGE_EF_SANTOS_EQUATION_CONTRACT.md`, `docs/API_FRONTEND_CONTRACT.md`.

## 7–9. Fuente, ecuaciones y mapa D

7. Santos: páginas impresas 29, 31–46, 47–52, 117, 131; páginas PDF = impresa
   +19. Tabla 4.1 (PDF48), Tabla 5.1 (PDF136), Tablas 5.6–5.7 (PDF150).
   Se inspeccionaron las páginas escaneadas, no solo comentarios del código.
   Perfil Gabriel Torrejon: contexto académico de implementación, conservación
   y verificación antes de calibración; no autoridad alternativa de ecuaciones.
8. Conjunto confirmado: **4.1.6, .9, .17, .18, .19, .26, .28, .32, .35,
   .40, .48, .50, .53**. Stage 3 reemplaza .46 por .53; usa la presión Pt2
   de momento gaseoso y pérdida superficial `0.3*v_l²`, sin calibración.
9. Primeros 14 componentes:
   `[m_c,m_g,rho_g,P_t1,v_B,v_f,y,m_film,h_B,desplazamiento_l,v_l,V_gi,V_fb,V_prod]`.
   Copia exacta D−→D+: error máximo **0.0**. La GLV se transporta como control.
   Se añaden `[P_t2,P_c1,P_c2,rho_c1,rho_c2,V_res,M_transfer]`:
   presiones/densidades algebraicas se inicializan como en D−; los últimos
   dos son ledgers locales, no inventarios físicos reconstruidos.
   El desplazamiento canónico continúa .32/.40, pero el tope físico publicado
   queda fijo en z_v durante producción. Esa interpretación está explicitada
   en el contrato; no se presenta el desplazamiento fuera del pozo como tope.

La EOS de .48 usa Pt1 deliberadamente: Santos p.43 rechaza la alternativa de
densidad promedio .47 por su comportamiento. No se reemplazó .48 por la EOS
espacial de Stage 4.2 para forzar compatibilidad al final.

## 10–17. GLV y comparación M1.6 frente a M1.7

Tiempos absolutos desde A; presiones absolutas. **ND** = no disponible, no cero.
La tercera columna es estado de cierre pre-E, NO un nuevo E.

| Magnitud | M1.6 histórico en E | M1.7 en E | M1.7 en cierre pre-E |
|---|---:|---:|---:|
| t_D, s | 509.849089816 | 509.849089816 | — |
| GLV abierta en D | no, forzada | sí, heredada | — |
| m_dot_GLV(D), kg/s | 0 | 0.197318713692 | — |
| t_GLV_close, s | forzado en D; no evento | 538.413916327 | — |
| t_E, s | 533.629275414 | ND | — |
| duración completa D→E, s | 23.780185598 | ND | — |
| P_c1, Pa | 5517345.62840 | ND | 5466664.45708 |
| P_c2, Pa | 6209553.45875 | ND | 6152513.81254 |
| P_t1, Pa | 4953631.02478 | ND | 6101918.45686 |
| m_c, kg | 675.403281172 | ND | 669.199169320 |
| m_g, kg | 103.615005693 | ND | 109.819117544 |
| rho_g, kg/m3 | 40.339428029 | ND | 49.690398664 |
| v_g, m/s | 71.850927418 | ND | 3.513101679 |
| v_f, m/s | 57.555407315 | ND | 1.424811529 |
| y, m | 0.001832560232 | ND | 0.002064094822 |
| q_res, m3/s | 0.000391495091 | ND | 0.000255971097 |
| película, m3 | 0.416149533006 | ND | 0.409419396317 |
| producido, m3 | 0.516194173754 | ND | 0.157537914793 |

10–13. GLV abierta en D, flujo inicialmente continuo con C→D. Cierre dinámico
por cruce descendente de la fuerza heredada; motor cerrado todo el tramo.
`t_close-t_D=28.5648265115 s`; `t_E-t_close=ND`; GLV(E)=ND.
La transferencia integrada casing→tubing es **6.20411185169 kg**.
En el mismo estado del evento la rama cerrada da dmc=dmg=dMtransfer=0,
sin reset de masas, presión o velocidades. El resultado termina cerrado y
no contiene reapertura. **No se afirma haber simulado el enclavamiento en un
intervalo posterior**: ese intervalo está bloqueado por fuente.

14–17. Los cuatro valores nuevos solicitados en E (t_E, Pt1, mg, rho_g) son
ND. El conflicto EOS histórico no se ha demostrado corregido ni se ha
reevaluado en un nuevo E: no existe ese estado. Se conserva su regresión.

El flujo fuente .13/.15 evaluado independientemente en D es
**0.197813233226 kg/s** frente al proxy **0.197318713692 kg/s**, diferencia
aproximada 0.250%. Cambiar solo después de D destruiría continuidad con el
upstream actual. La reconciliación futura debe ser coherente a ambos lados.
El diagnóstico fuente se verifica en régimen no estrangulado de esta base;
no se certifica aquí la extensión crítica de la correlación.

## 18–21. Conservación, ecuación exacta y convergencia disponible

18. Balance gas total relativo: **1.8242004013e-16**. Transferencia interna
   no crea ni elimina masa; errores casing/tubing frente al ledger:
   **1.74971149e-13 / 6.75015599e-14 kg**.
19. Balance líquido relativo: **3.7933450921e-10**. Se verifica
   `V_slug+V_film+V_fb+V_prod-V_res=constante`, con `V_film=A_f*h_B`;
   el retorno no se suma otra vez como inventario. IPR y producción se
   integran también por cuadratura independiente de las muestras.
   Gas inventario/geométrico: **8.8966954022e-11** relativo; EOS .48:
   **3.3167350081e-15** relativo. Offset casing .6 máximo **3.4106e-13 kg**.
20. El RHS científico divide por `L=z_v-h_B`, sin `max(L,5)` ni equivalente.
   Se prueba .53 a L=0.5 y 0.1 m. El piso histórico permanece únicamente en
   `milestone16_reference` para comparación, nunca en `santos_corrected`.
21. Radau: rtol=1e-8, atol=1e-10; refinamiento max_step=1/.5/.25 s,
   conservando el MISMO D. Convergencia de cierre, no de E:

| max_step, s | t_close−t_D, s | Pt1(cierre), Pa | mg(cierre), kg | rho(cierre), kg/m3 | vf(cierre), m/s |
|---:|---:|---:|---:|---:|---:|
| 1.00 | 28.564826492983 | 6101918.456798 | 109.819117541792 | 49.690398663917 | 1.424811527160 |
| 0.50 | 28.564826511526 | 6101918.456856 | 109.819117544496 | 49.690398664389 | 1.424811528722 |
| 0.25 | 28.564826513661 | 6101918.456862 | 109.819117544787 | 49.690398664440 | 1.424811528520 |

t_E y sus estados son ND en las tres corridas. El cierre aún deja 181.108 m
frente a una guarda numérica de dominio de 1.48e-5 m. No es un cierre casi
simultáneo con E dentro de esta trayectoria.

No se ejecutó convergencia unilateral al evento L=0: el solver expone
`E_LIMIT_NOT_LOCALIZED` si llega a la guarda de dominio, NO E. Esa guarda
vive en eventos, no modifica .53. La localización exacta de E queda pendiente
de resolver antes la física bloqueante, sin proclamar ese gate aprobado.

**Precaución .27/.28:** el RHS integra la forma diferencial publicada .28,
que no incluye df/dt. Con la fricción heredada variable, la relación
algebraica .27 deriva hasta **4042.507254 Pa**. No se ocultó ni se proyectó
Pt2; esta diferencia necesita revisión del cierre de fricción y del upstream.
Los residuos de las 13 ecuaciones pasan con escala física ≤1e-8, pero no
prueban que todos los cierres auxiliares heredados reproduzcan Santos.

## 22–30. Altura inferior y downstream

22. La frase de p.131 se clasifica **SOURCE_LIMITING_IDEALIZATION**: el texto
   no cuantifica «inmediatamente antes». Tabla 4.1 inicia fase I en E, con
   GLV abierta hasta su cierre; por eso no autoriza usar fase I pre-E con
   GLV cerrada. Para el intervalo material encontrado se declara
   **SOURCE_AMBIGUITY**. No se asigna h_l(E)=0 ni V_res/A_B.
23. El auditor exige E físico, GLV cerrada, h_l con procedencia, Pt3 e y
   explícitos; mantiene simultáneamente inventario, hidrostática, EOS y
   densidad/film por identidad. Un caso analítico de h_l=1 m pasa; una
   perturbación de densidad o hidrostática falla sin proyección.
24–25. Auditoría numérica en E:

| Cierre Stage 4.2 | M1.6 histórico | M1.7 |
|---|---:|---|
| h_l(E), m | 0, hipótesis límite histórica | ND; sin transición física |
| Pt3(E), Pa | 4953631.024777 | ND |
| rho inventario, kg/m3 | 40.339428029185 | ND |
| rho EOS, kg/m3 | 23.377362913293 | ND |
| residuo relativo EOS | 0.725576498034 | NO EVALUABLE, no cero |
| residuo hidrostático, Pa | 0 bajo hipótesis histórica | NO EVALUABLE, no cero |
| compatible | no | no hay entrada E que auditar |

26–30. **E→F no ejecutado; t_F=ND; F→G no ejecutado; G no alcanzado;
t_G=ND.** Inventarios, presiones, alturas, caudales y balances en F/G son ND.
Las siete ecuaciones 4.2, el RHS 4.3 y el residual G se conservan; sus pruebas
analíticas no equivalen a una corrida fuente del caso base. No hay G→H.

## 31–33. IPR, velocidades y API

31. IPR dinámica centralizada sin modificar: q_res mínimo **0.0002470519635**,
   máximo **0.0002559710968 m3/s**, ambos positivos. Reservorio alimenta filme
   durante el tramo Stage 3 integrado; ledger acumulado **0.007173465495 m3**.
32. Se conserva **HIGH_VELOCITY_PLAUSIBILITY_REVIEW_PENDING**. Picos del
   tramo: gas M1.6→M1.7 **71.850927→3.513102 m/s**, película
   **57.555407→1.424812**, golfada **69.857756→3.186707**. Los intervalos no
   son comparables como etapas completas: M1.7 termina antes de E. No se
   afirma resuelta la plausibilidad global ni se ajustaron coeficientes.
33. API: `NOT_SOURCE_CERTIFIED_A_TO_E`, terminal
   `GLV_CLOSE_BEFORE_E_SOURCE_BLOCK`, `validationLevel=failed`.
   Duración = tiempo final del tramo, no tiempo de ciclo. `cyclesPerDay`,
   `estimatedDailyLiquid`, `estimatedDailyInjectedGas` = null,
   `UNAVAILABLE_INCOMPLETE_CYCLE`. Escenarios no presentan comparación diaria
   de un ciclo ausente. Las claves históricas por ciclo quedan rotuladas
   explícitamente como acumulados parciales. Sin cambio de esquema/frontend.
   Se corrigió el ejemplo contradictorio `points: []`: es ahora un extracto
   de metadatos que omite points y explica que la respuesta real no está vacía.

## 34–35. Pruebas y PYTHON QUALITY GATE

34. **24 casos nuevos** en `test_stage_de_santos_source.py` (11 funciones,
   parametrizadas: 13 ecuaciones y dos longitudes, más continuidad/balances,
   cierre, IPR, convergencia y gate 4.2). **32 pruebas existentes modificadas
   o reemplazadas**: 23 funciones conservan nombre y cambian aserciones,
   una cambia nombre, ocho del antiguo auditor EF se reemplazan por ocho
   comprobaciones del bloqueo real. Además se adapta la fixture histórica
   de dos tests Stage 4.2, manteniendo la regresión EOS M1.6 explícita.
   Son 12 archivos de pruebas existentes afectados. No se elimina la
   regresión numérica histórica ni las pruebas de las siete ecuaciones 4.2.

No se encontraron `pyproject.toml`, `ruff.toml`, `.ruff.toml`, `setup.cfg`,
`tox.ini` ni configuración pre-commit. `requirements.txt` no define Black/Ruff.
No hay Black ni Ruff en gli311, conda base, runtime documental disponible ni
comandos PATH. **Formatter/Black: NO EJECUTADO (no disponible); archivos
reformateados por herramienta: 0. Ruff: NO EJECUTADO (no disponible).**
No se instalaron herramientas ni se aplicaron autofixes científicos.
Esto es un control de calidad pendiente, NO un control aprobado.

Pruebas focalizadas iniciales: **28 passed, 3.13 s**. Tras la inspección del
control de formato/calidad y los últimos ajustes: **52 collected, 52 passed,
0 failed, 0 skipped, 56.54 s**. Incluye auditor DE, 24 casos nuevos, Stage 4.2,
auditores EF/AF y contratos API. La ruta FG base no se ejecutó; la suite
completa conserva sus pruebas unitarias independientes.

35. Suite completa intermedia: **180 collected, 180 passed, 0 failed,
0 skipped, 46.89 s**. Corrida FINAL posterior al control de calidad:
**180 collected, 180 passed, 0 failed, 0 skipped, 211.54 s (0:03:31)**.
`git diff --check` final: exit 0, sin errores de whitespace.
29 archivos existentes modificados y 7 nuevos; HEAD permanece igual.
No se afirma que GitHub CI haya corrido.

Reproducción en PowerShell, desde la raíz BE:

```powershell
$env:PYTHONPATH = 'src'
$env:PYTHONDONTWRITEBYTECODE = '1'
& 'C:\Users\Usuario\miniconda3\envs\gli311\python.exe' -m gli.audit_milestone17
& 'C:\Users\Usuario\miniconda3\envs\gli311\python.exe' -m pytest -ra -p no:cacheprovider
```

Las corridas de trabajo usaron `--basetemp` en el workspace autorizado para
no mezclar temporales con archivos BE. JSON numérico: `milestone_1_7_results.json`.

## THESIS_UPDATE_NOTES

Secciones afectadas: modelo matemático Stage 3, mecánica GLV, condiciones de
transición Stage 3/4, IPR, métodos numéricos, verificación y discusión de
limitaciones. `THESIS_WRITING_MAP.md` vincula fuente, implementación y madurez.

Puede redactarse: conjunto trazado, unidades/signos, cambio .46→.53, mapa de
estado, diferencia entre válvula motora y GLV, pruebas de balances, protección
de dominio y diagnóstico reproducible del bloqueo. Puede mostrarse la tabla
M1.6/M1.7 únicamente como contraste histórico/parcial, no como mejor ajuste.

Pendiente: correlación fuente GLV coherente upstream, fricción/.27/.28,
transición pre-E, h_l(E), E compatible, F/G físicos y ciclo completo. Requiere
validación posterior: parámetros/cierres con procedencia, reproducción
cuantitativa independiente Santos, plausibilidad de velocidades, contraste
experimental/campo. No promover estos resultados a conclusiones de desempeño
diario, optimización o validación de campo. **DOCX final no modificado.**

## 36–39. Ambigüedades, bloqueos y recomendación

36. SOURCE_MISSING/SOURCE_AMBIGUITY: no se identificó en las secciones
   inspeccionadas una transición explícita con columna inferior acumulándose
   y golfada superior aún presente durante un intervalo cerrado material.
   La frase del caso base no cuantifica simultaneidad. Tampoco resuelve el
   tratamiento de df/dt al usar la ecuación diferencial .28 con fricción
   variable. La correlación GLV SÍ existe en la fuente: su proxy upstream es
   un defecto de implementación pendiente, no un dato bibliográfico ausente.
37. Bloqueos: transición pre-E no definida para esta trayectoria, proxy GLV
   heredado, consistencia auxiliar .27/.28 por reconciliar, localización E
   no verificada, ausencia de E/F/G. Black/Ruff pendientes por disponibilidad.
38. Recomendación: revisar estos puntos de fuente y coherencia upstream
   antes de extender la integración; no ajustar PI, fricción ni presión para
   fabricar E. Solo tras E físico y compatible ejecutar los gates exactos
   EF y FG. Detener aquí M1.7; no iniciar M1.8, G→H ni ciclo múltiple.
39. Estado final: **BLOCKED_BY_SOURCE**.
