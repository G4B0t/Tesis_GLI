# Milestone 1.6 — Stage 4.2 E→F y reconciliación del estado F

## Dictamen

**NOT_READY_FOR_GH**

El sistema exacto de siete variables de Santos Stage 4.2 está implementado y
sus siete residuos diferenciales se verifican independientemente. Sin embargo,
el estado terminal D→E del caso base no puede inicializarlo por identidad: masa
de gas, geometría, `P_t1`, hidrostática 4.1.88 y EOS 4.1.90 son incompatibles.
Por tanto no se integra E→F, no existe un estado F físico corregido y F→G no se
ejecuta para el caso base.

## Auditoría de fuente

- Tabla 4.1: fase II termina en `v_f=0`; fase III continúa hasta completar la
  descompresión.
- Tabla 5.1: Stage 4.2 usa `h_l, P_t1, P_t3, rho_g, v_f, v_g, y` y las ecuaciones
  4.1.76, .80, .83, .84, .87, .89 y .90.
- Tablas 5.6–5.7: el ejemplo base usa `EF` para fase II y `FG` para fase III;
  la fase I no existe.
- Página impresa 52: la columna inferior empieza a acumular fluido de formación
  desde el cierre de la GLV y el filme no se incorpora a ella. De ahí
  `h_l(E)=0` en el ejemplo sin fase I.

El contrato completo está en `STAGE_EF_SANTOS_EQUATION_CONTRACT.md`.

## Incompatibilidad del estado E

Corrida base con `max_step=0.5 s`:

| Magnitud en E | Valor |
|---|---:|
| tiempo absoluto `t_E` | 533.629275414 s |
| `P_t1(E)` | 4.953631025 MPa abs |
| `P_t3(E)` por 4.1.88 y `h_l=0` | 4.953631025 MPa abs |
| `P_wb(E)` | 5.139474190 MPa abs |
| `P_r` | 8.456590800 MPa abs |
| `q_res(E)` | +3.91495091e-4 m³/s |
| `m_g(E)` | 103.615005693 kg |
| `rho_g(E)` por masa/geometría | 40.339428029 kg/m³ |
| `rho_g(E)` por EOS espacial 4.1.90 | 23.377362913 kg/m³ |
| residuo relativo de densidad | 0.725576498 |
| volumen requerido por EOS | 4.432279470 m³ |
| volumen geométrico máximo | 2.568578950 m³ |

La IPR dinámica todavía es válida y productiva en E. El bloqueo no procede de
la IPR: procede del estado gaseoso espacial heredado de D→E. Ajustar `rho_g`
rompería masa; ajustar `P_t3` rompería 4.1.88 o exigiría `h_l<0`; ajustar
`P_t1` rompería continuidad. Ninguna de esas proyecciones está permitida.

## Comparación solicitada

La columna “Milestone 1.5” reproduce los resultados obtenidos antes de retirar
la reconstrucción. “Stage 4.2 corregido” no inventa un F cuando falla la
frontera E.

| Magnitud | Legacy Milestone 1.5 | Stage 4.2 corregido |
|---|---:|---:|
| `t_E` absoluto | 533.629275414 s | 533.629275414 s |
| `t_F` absoluto | 534.028521181 s | no definido |
| `P_t1(F)` | 10.054716592 MPa | no definido |
| `P_t3(F)` | 9.517713545 MPa | no definido |
| `P_wb(F)` | 10.240559757 MPa | no definido |
| `h_l(F)` | 57.790992366 m reconstruidos | no definido |
| `q_res(F)` | -2.10548851e-4 m³/s | no definido |
| filme `V_f(F)` | 0.415906102 m³ | no definido |
| ledger `V_res(F)` | 0.100307294 m³ | no definido |
| `m_g(F)` | 103.581240983 kg | no definido |
| `t_G` | no alcanzado; se reportaba 1200 s por error | no ejecutado |
| evento G alcanzado | no | no ejecutado |
| mínimo `q_res` F→G | -2.10548851e-4 m³/s | no ejecutado |

En 1.5 se calculaba `h_l=(V_res+V_fallback)/A_B`; por construcción eso hacía
`V_lower=V_res` (0.100307294 m³ en F), aunque una magnitud es inventario físico
y la otra es procedencia acumulada. Esa identidad artificial elevaba `P_t1` y
`P_wb` por encima de `P_r`, produciendo IPR negativa. La implementación 1.6
elimina esa conversión y exige `h_l`, `P_t3` y `V_lower` explícitos.

También se eliminó la conversión `rho_gt3=2*rho_mean-rho_surface` usada para
fabricar el estado espacial F. F→G solo puede recalcular `rho_gt3=P_t3/K_t3`
desde el mismo `P_t3` físico recibido.

## Residuos, balances y convergencia

- Los residuos independientes de 4.1.76/.80/.83/.84/.87/.89/.90 pasan con
  tolerancia normalizada `1e-10` en un estado Stage-4.2 físicamente consistente.
- El sistema local 4.1.83/.84 se resuelve como matriz 2x2 escalada; condición
  de la prueba: 1.1064.
- La corrida base no produce balances E→F ni F→G porque se detiene antes de
  integrar un estado inicial inconsistente.
- Una prueba F física sintética, consistente con EOS/hidrostática/inventario,
  confirma transferencia identidad, balances gas/líquido `<=1e-8`, IPR no
  negativa y convergencia al refinar `max_step` de 1.0 a 0.5 s.
- El evento G permanece exactamente
  `P_t3-P_ts-rho_g*g*(H_gv-h_l)=0`. En la prueba sin raíz,
  `event_g_time_s=None` e `integration_end_time_s=1200 s`.

## Trabajo requerido antes de G→H

Debe reconstruirse científicamente el estado gaseoso espacial de D→E (sin
ajustar coeficientes) para que su terminal E entregue simultáneamente masa,
presiones y densidad media compatibles con 4.1.83/.88/.90. Solo después podrá
ejecutarse Stage 4.2, obtenerse F por `v_f=0` y reintentarse F→G.
