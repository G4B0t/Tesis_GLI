# Implementación Santos F→G — descompresión final

Estado: **READY_FOR_REVIEW**. Alcance exclusivo: Santos Model I, etapa 4.3. No contiene G→H, multiciclo, calibración, validación de campo ni optimización.

## Fuente y selección de ecuaciones

Fuente primaria: Santos, sección impresa 4.1.4.3, páginas impresas 58–63 (páginas 77–82 del PDF local).

| Ecuación | Papel implementado |
|---|---|
| 4.1.24–25 | `A_B=π(r−y)²`, variación geométrica |
| 4.1.89 | `dP_t1/dt − dP_t3/dt − ρ_l g dh_l/dt = 0` |
| 4.1.94 | balance de película |
| 4.1.95 | retorno laminar `q_f` |
| 4.1.96 | densidad media del gas |
| 4.1.97 | balance de masa del gas |
| 4.1.98–103 | momento/velocidad del gas y EOS superficial/fondo |
| 4.1.104–107 | balance de columna, incluyendo `q_f` y `q_res` |
| 4.1.108 | cierre diferencial `P_t3–ρ_gt3` |

Las ecuaciones rectoras son 4.1.89, 4.1.94, 4.1.97, 4.1.107 y 4.1.108. Las demás son geometría, EOS o cierres algebraicos; no se integran como ecuaciones independientes redundantes.

## Variables

Estado SI:

`[ρ_gt3 kg/m³, P_t3 Pa, P_t1 Pa, h_l m, y m, V_return m³, V_res m³, m_g,out kg]`

Algebraicas: áreas `A_B/A_f`, densidades superficial/media/inferior, `q_f`, velocidades `v_g/v_gs`, masa de gas, película y columna.

Los ledgers identifican procedencia. `V_return` no se suma de nuevo como inventario: el líquido retornado ya está en `A_Bh_l`.

## Mapa F

Se reciben por identidad del resultado E→F corregido: masa de gas, espesor y volumen de película, producido, fallback y reservorio acumulado. E→F expone `V_res=q_res·t` como un ledger derivado; no cambian sus ODE ni eventos.

E→F representa el gas mediante una densidad/presión media uniforme. F→G requiere densidad/presión inferior. Se conserva masa y se aplica 4.1.96:

`ρ_gt3(F)=2m_g/[A_B(z_v−h_l)]−ρ_gs`.

Luego 4.1.101 obtiene `P_t3` y la integral de 4.1.89 obtiene `P_t1`. Por ello 4.9017 MPa (media E→F) y 9.0192 MPa (inferior F→G) no son la misma variable. Esta transformación queda expuesta en el resultado y constituye una limitación de representación de la etapa anterior, no una validación de campo.

## Evento G

`g_G=P_t1−P_to,initial`.

- Signo esperado antes de G: positivo.
- Cero: presión inferior vuelve al valor inicial.
- Dirección: `−1`.
- Terminal: sí.
- Horizonte 1200 s: guard de fallo, nunca condición científica.

## Método

`scipy.integrate.solve_ivp`, Radau, `rtol=1e-8`, `atol=1e-10`, `max_step=0.5 s`. Radau mantiene continuidad con las etapas rígidas existentes y resuelve el acoplamiento EOS–geometría–descarga–evento. No se fuerza RK4.

## Caso Santos 50/70/80

| Magnitud | Resultado base |
|---|---:|
| `t_F` | 526.778244 s |
| `t_G` | 641.639013 s |
| `Δt_FG` | 114.860769 s |
| `P_t1(F)` transformada | 9.019213 MPa |
| `P_t1(G)` | 4.721027 MPa |
| `P_t3(G)` | 2.447143 MPa |
| `h_l(F) / h_l(G)` | 0.222051 / 244.710048 m |
| `y(F) / y(G)` | 3.457173 / 1.955703 mm |
| película retornada | 0.315969 m³ |
| entrada de reservorio FG | 0.103960 m³ |
| película restante G | 0.442994 m³ |
| columna inferior G | 0.420262 m³ |
| fallback acumulado G | 0.315969 m³ |
| gas descargado FG | 60.902116 kg |

El producido superficial permanece en 0.520137 m³ durante FG, como exige la configuración de la fase.

## Balances y convergencia

- Gas: residual absoluto `4.03e-10 kg`; normalizado `4.54e-12`.
- Líquido: residual absoluto `1.03e-11 m³`; normalizado `8.02e-12`.
- Máximo residual integral de ecuaciones: `3.13e-11`.

Corrida estricta: Radau, `rtol=1e-9`, `atol=1e-11`, `max_step=0.25 s`. Diferencias relativas de `t_G`, presiones, altura, película y fallback: menores que `5e-12`. Sus balances normalizados mejoraron a `5.44e-13` gas y `9.49e-13` líquido.

## Pruebas

Quince pruebas focalizadas cubren ecuaciones, cierre 4.1.95, continuidad F, finitud, bounds, evento/dirección G, balances, retorno de película, procedencia `q_res`, convergencia, no mutación A→F, orquestación A→G, determinismo y auditoría.

## Limitaciones

- `q_res` es la entrada constante existente en `OperatingConditions`. Santos 4.1.107 exige el término, pero la ley IPR que lo genera continúa **SOURCE_MISSING**; no se modificó.
- La transformación media→fondo en F muestra una limitación espacial del estado E→F y debe revisarse junto con la futura IPR antes de G→H.
- `HIGH_VELOCITY_PLAUSIBILITY_REVIEW_PENDING` permanece por las velocidades D→E; esta implementación no las modifica.
- Las velocidades de descarga de gas también requieren futura comparación con datos/dominio de correlaciones.
- Este resultado es verificación/reproducción interna, no validación de campo ni ciclo completo.
