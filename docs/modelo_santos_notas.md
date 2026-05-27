# Notas del Modelo I: GLI Convencional

Fuente principal: Santos, seccion 4.1 y seccion 5.1.1.

## Enfoque de simulacion

El GLI convencional se simula como un sistema dinamico por etapas. Cada etapa
usa un conjunto diferente de ecuaciones y tiene una condicion de parada que
activa el paso a la etapa siguiente.

## Tabla 5.1: ecuaciones por etapa

| Etapa | Ecuaciones Santos | Variables principales |
|---|---|---|
| 1 | 4.1.6, 4.1.10, 4.1.17, 4.1.18, 4.1.19 | `m_tc`, `P_c1`, `P_c2`, `rho_c1`, `rho_c2` |
| 2 | 4.1.6, 4.1.9, 4.1.17, 4.1.18, 4.1.19, 4.1.26, 4.1.28, 4.1.32, 4.1.35, 4.1.40, 4.1.46, 4.1.48, 4.1.50 | `h_B`, `h_l`, `m_tc`, `P_t1`, `P_t2`, `P_c1`, `P_c2`, `rho_B`, `rho_c1`, `rho_c2`, `v_B`, `v_l`, `y` |
| 3 | Igual a etapa 2, pero con 4.1.53 en lugar de 4.1.46 | Misma base que etapa 2 |
| 4.1 | 4.1.6, 4.1.9, 4.1.17, 4.1.18, 4.1.19, 4.1.57, 4.1.69, 4.1.72, 4.1.73, 4.1.75 | `m_tc`, `P_c1`, `P_c2`, `P_t1`, `rho_c1`, `rho_c2`, `rho_g`, `v_f`, `v_g`, `y` |
| 4.2 | 4.1.76, 4.1.80, 4.1.83, 4.1.84, 4.1.87, 4.1.89, 4.1.90 | `h_l`, `P_t1`, `rho_gt1`, `rho_g`, `v_f`, `v_g`, `y` |
| 4.3 | 4.1.89, 4.1.94, 4.1.97, 4.1.107, 4.1.108 | `h_l`, `P_t1`, `rho_gt1`, `rho_gt3`, `y` |
| 5 | 4.1.94, 4.1.107, 4.1.109 | `h_l`, `P_t1`, `y` |

## Condiciones iniciales de Etapa 1

La etapa 1 inicia con la valvula motora abierta y la valvula de gas lift
cerrada.

- `P_bt`: presion en el domo/fuelle de la valvula.
- `P_to`: presion en el tubo al momento de apertura.
- `P_vo`: presion en el revestimiento al momento de apertura.
- `R_v`: relacion de areas de la valvula.

Ecuaciones implementadas:

| Ecuacion | Uso | Archivo |
|---|---|---|
| 5.1 | `P_bt = P_vo (1 - R_v) + P_to R_v` | `valves.py` |
| 5.2 | `P_to = P_t3 + rho_l g L` | `initial_conditions.py` |
| 5.3 | columna estatica de gas para `P_t3` | `initial_conditions.py` |
| 5.4 | `rho_l = d_l rho_w` | `fluids.py` |
| 5.5 | densidad relativa del liquido | `fluids.py` |
| 5.6 | densidad relativa del aceite por API | `fluids.py` |
| 5.7 | presion `P_c1` en superficie del anular | `initial_conditions.py` |
| 5.8 | densidad `rho_c2` | `fluids.py` |
| 5.9 | densidad `rho_c1` | `fluids.py` |
| 5.10 | masa `m_tc` en el anular | `initial_conditions.py` |
| 5.11 | presion promedio `P_tc` | `initial_conditions.py` |
| 5.12 | temperatura promedio `T_tc` | `initial_conditions.py` |
| 5.13 | fuerza resultante para abrir valvula | `valves.py` |

## Condiciones iniciales de Etapa 2

La etapa 2 inicia cuando abre la valvula de gas lift. Las variables del anular
vienen del final de la etapa 1.

Valores iniciales:

- `h_B = 0.05 L`
- `h_l = (1 + 0.05 A_B / A_t) L`
- `P_t1 = P_to`
- `P_t2 = P_to`
- `rho_B = P_t1 M / (Z_t1 R T_t1)`
- `v_l = 0.0152 m/s`
- `v_B = a v_l + b`
- `y = 0.01 D`

## Eventos de cambio de etapa

| Cambio | Condicion |
|---|---|
| Etapa 1 a 2 | fuerza resultante de valvula llega a cero |
| Etapa 2 a 3 | el tope de la golfada llega a superficie |
| Etapa 3 a 4.1 | la base de la golfada llega a superficie |
| Etapa 4.1 a 4.2 | cierre de la valvula de gas lift |
| Etapa 4.2 a 4.3 | `v_f = 0` |
| Etapa 4.3 a 5 | presion del gas vuelve al valor inicial |
| Etapa 5 a nuevo ciclo | columna liquida recupera longitud inicial |
